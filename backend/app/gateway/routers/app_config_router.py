"""App configuration management — read and write config.yaml sections safely."""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.gateway.deps import get_config
from app.gateway.file_lock import interprocess_lock
from deerflow.config.app_config import AppConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Process-local guard for config.yaml read-modify-write cycles. Paired with a
# host-wide interprocess lock (see _config_transaction) and the atomic write in
# _write_yaml, this prevents torn files AND lost updates / duplicate entries,
# including when a second process (parallel dev/CLI session) edits the same file.
_CONFIG_WRITE_LOCK = threading.Lock()

# ── Allowed flat fields that can be patched via UI ────────────────────────────
# Format: "section.field" or "field" for top-level.
# Sections that require restart are excluded (database, checkpointer, run_events, …).
_ALLOWED_PATCHES: dict[str, type] = {
    "log_level": str,
    "token_usage.enabled": bool,
    "title.enabled": bool,
    "title.max_words": int,
    "title.max_chars": int,
    "summarization.enabled": bool,
    "memory.enabled": bool,
    "memory.injection_enabled": bool,
    "memory.debounce_seconds": int,
    "memory.max_facts": int,
    "memory.fact_confidence_threshold": float,
    "memory.max_injection_tokens": int,
    "memory.token_counting": str,
    "subagents.enabled": bool,
    "loop_detection.enabled": bool,
}

# ── Provider templates for new model entries ──────────────────────────────────
_MODEL_TEMPLATES: dict[str, dict[str, Any]] = {
    "openai": {
        "use": "langchain_openai:ChatOpenAI",
        "model": "gpt-4o",
        "api_key": "$OPENAI_API_KEY",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": True,
    },
    "anthropic": {
        "use": "langchain_anthropic:ChatAnthropic",
        "model": "claude-opus-4-5-20251101",
        "api_key": "$ANTHROPIC_API_KEY",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": True,
        "supports_vision": True,
    },
    "deepseek": {
        "use": "deerflow.models.patched_deepseek:PatchedChatDeepSeek",
        "model": "deepseek-chat",
        "api_key": "$DEEPSEEK_API_KEY",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": False,
    },
    "openrouter": {
        "use": "langchain_openai:ChatOpenAI",
        "model": "openai/gpt-4o",
        "api_key": "$OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": False,
    },
    "nvidia": {
        "use": "langchain_openai:ChatOpenAI",
        "model": "meta/llama-3.3-70b-instruct",
        "api_key": "$NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "max_tokens": 4096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": False,
    },
    "groq": {
        "use": "langchain_groq:ChatGroq",
        "model": "llama-3.3-70b-versatile",
        "api_key": "$GROQ_API_KEY",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": False,
    },
    "mistral": {
        "use": "langchain_mistralai:ChatMistralAI",
        "model": "mistral-large-latest",
        "api_key": "$MISTRAL_API_KEY",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": False,
    },
    "google": {
        "use": "langchain_google_genai:ChatGoogleGenerativeAI",
        "model": "gemini-2.0-flash",
        "api_key": "$GEMINI_API_KEY",
        "max_tokens": 8096,
        "timeout": 60,
        "max_retries": 3,
        "supports_thinking": False,
        "supports_vision": True,
    },
    "ollama": {
        "use": "langchain_ollama:ChatOllama",
        "model": "llama3.2",
        "base_url": "http://localhost:11434",
        "max_tokens": 8096,
        "timeout": 120,
        "max_retries": 2,
        "supports_thinking": False,
        "supports_vision": False,
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _resolve_config_path() -> Path:
    return AppConfig.resolve_config_path()


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Atomically write YAML to ``path``.

    Renders to a temporary file in the same directory, flushes+fsyncs it, then
    ``os.replace``s it over the target. ``os.replace`` is atomic on the same
    filesystem, so a crash mid-write can never leave a half-written / truncated
    config.yaml — readers always see either the old or the new file in full.
    """
    content = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        # Never leave a stray temp file behind on failure.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


@contextlib.contextmanager
def _config_transaction(path: Path):
    """Serialize a full read-modify-write cycle on config.yaml.

    Combines a process-local threading lock (cheap, covers concurrent requests in
    one gateway) with a host-wide interprocess lock (covers a second process such
    as a parallel dev/CLI session editing the same file). Together with the atomic
    write in _write_yaml, this prevents both torn files and lost updates.
    """
    with _CONFIG_WRITE_LOCK, interprocess_lock(path):
        yield


def _deep_get(d: dict, key: str) -> Any:
    parts = key.split(".", 1)
    if len(parts) == 1:
        return d.get(parts[0])
    sub = d.get(parts[0])
    if not isinstance(sub, dict):
        return None
    return _deep_get(sub, parts[1])


def _deep_set(d: dict, key: str, value: Any) -> None:
    parts = key.split(".", 1)
    if len(parts) == 1:
        d[parts[0]] = value
        return
    if parts[0] not in d or not isinstance(d[parts[0]], dict):
        d[parts[0]] = {}
    _deep_set(d[parts[0]], parts[1], value)


# ── Schemas ───────────────────────────────────────────────────────────────────


class GeneralConfigResponse(BaseModel):
    log_level: str = "info"
    token_usage_enabled: bool = False
    title_enabled: bool = True
    title_max_words: int = 5
    title_max_chars: int = 50
    summarization_enabled: bool = False
    memory_enabled: bool = True
    memory_injection_enabled: bool = True
    memory_debounce_seconds: int = 30
    memory_max_facts: int = 100
    memory_fact_confidence_threshold: float = 0.7
    memory_max_injection_tokens: int = 2000
    memory_token_counting: str = "tiktoken"
    subagents_enabled: bool = True
    loop_detection_enabled: bool = True


class GeneralConfigPatch(BaseModel):
    log_level: str | None = None
    token_usage_enabled: bool | None = None
    title_enabled: bool | None = None
    title_max_words: int | None = None
    title_max_chars: int | None = None
    summarization_enabled: bool | None = None
    memory_enabled: bool | None = None
    memory_injection_enabled: bool | None = None
    memory_debounce_seconds: int | None = None
    memory_max_facts: int | None = None
    memory_fact_confidence_threshold: float | None = None
    memory_max_injection_tokens: int | None = None
    memory_token_counting: str | None = None
    subagents_enabled: bool | None = None
    loop_detection_enabled: bool | None = None


class ModelEntry(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    provider: str | None = None
    model: str = ""
    use: str = ""
    base_url: str | None = None
    api_key_env: str | None = None
    max_tokens: int = 8096
    timeout: int = 60
    max_retries: int = 3
    supports_thinking: bool = False
    supports_vision: bool = False
    supports_reasoning_effort: bool = False
    input_price_per_mtok: float | None = None
    output_price_per_mtok: float | None = None
    fallback_chain: list[str] = Field(default_factory=list)


class ModelCreateRequest(BaseModel):
    name: str = Field(..., description="Unique identifier (slug)")
    display_name: str | None = None
    description: str | None = None
    provider: str = Field(..., description="Provider template key")
    model: str = Field(..., description="Provider model ID")
    base_url: str | None = None
    api_key_env: str | None = None
    max_tokens: int = 8096
    supports_thinking: bool = False
    supports_vision: bool = False
    input_price_per_mtok: float | None = None
    output_price_per_mtok: float | None = None
    fallback_chain: list[str] = Field(default_factory=list)


class ModelUpdateRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key_env: str | None = None
    max_tokens: int | None = None
    timeout: int | None = None
    max_retries: int | None = None
    supports_thinking: bool | None = None
    supports_vision: bool | None = None
    input_price_per_mtok: float | None = None
    output_price_per_mtok: float | None = None
    fallback_chain: list[str] | None = None


class ModelsConfigResponse(BaseModel):
    models: list[ModelEntry]
    templates: dict[str, dict] = Field(default_factory=dict)


class ConfigWriteResponse(BaseModel):
    success: bool
    message: str
    restart_required: bool = False


# ── General config endpoints ──────────────────────────────────────────────────


@router.get("/config", response_model=GeneralConfigResponse, summary="Get general app config")
async def get_general_config(config: AppConfig = Depends(get_config)) -> GeneralConfigResponse:
    return GeneralConfigResponse(
        log_level=config.log_level or "info",
        token_usage_enabled=config.token_usage.enabled,
        title_enabled=config.title.enabled,
        title_max_words=getattr(config.title, "max_words", 5),
        title_max_chars=getattr(config.title, "max_chars", 50),
        summarization_enabled=config.summarization.enabled,
        memory_enabled=config.memory.enabled,
        memory_injection_enabled=getattr(config.memory, "injection_enabled", True),
        memory_debounce_seconds=getattr(config.memory, "debounce_seconds", 30),
        memory_max_facts=getattr(config.memory, "max_facts", 100),
        memory_fact_confidence_threshold=getattr(config.memory, "fact_confidence_threshold", 0.7),
        memory_max_injection_tokens=getattr(config.memory, "max_injection_tokens", 2000),
        memory_token_counting=getattr(config.memory, "token_counting", "tiktoken"),
        subagents_enabled=getattr(config.subagents, "enabled", True),
        loop_detection_enabled=getattr(config.loop_detection, "enabled", True),
    )


@router.put("/config", response_model=ConfigWriteResponse, summary="Patch general app config")
async def patch_general_config(patch: GeneralConfigPatch) -> ConfigWriteResponse:
    # Map flat patch fields → YAML keys
    mapping = {
        "log_level": "log_level",
        "token_usage_enabled": "token_usage.enabled",
        "title_enabled": "title.enabled",
        "title_max_words": "title.max_words",
        "title_max_chars": "title.max_chars",
        "summarization_enabled": "summarization.enabled",
        "memory_enabled": "memory.enabled",
        "memory_injection_enabled": "memory.injection_enabled",
        "memory_debounce_seconds": "memory.debounce_seconds",
        "memory_max_facts": "memory.max_facts",
        "memory_fact_confidence_threshold": "memory.fact_confidence_threshold",
        "memory_max_injection_tokens": "memory.max_injection_tokens",
        "memory_token_counting": "memory.token_counting",
        "subagents_enabled": "subagents.enabled",
        "loop_detection_enabled": "loop_detection.enabled",
    }

    path = _resolve_config_path()
    with _config_transaction(path):
        try:
            data = _read_yaml(path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Cannot read config.yaml: {exc}") from exc

        changed = 0
        for patch_field, yaml_key in mapping.items():
            value = getattr(patch, patch_field, None)
            if value is not None:
                _deep_set(data, yaml_key, value)
                changed += 1

        if changed == 0:
            return ConfigWriteResponse(success=True, message="No changes to apply.")

        try:
            _write_yaml(path, data)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Cannot write config.yaml: {exc}") from exc

    logger.info("General config patched (%d field(s) updated) → %s", changed, path)
    return ConfigWriteResponse(success=True, message=f"{changed} setting(s) saved. Hot-reload will apply most changes on the next request.")


# ── Models config endpoints ───────────────────────────────────────────────────


def _yaml_model_to_entry(m: dict) -> ModelEntry:
    api_key_raw: str = m.get("api_key", "") or ""
    api_key_env = api_key_raw.lstrip("$") if api_key_raw.startswith("$") else None
    return ModelEntry(
        name=m.get("name", ""),
        display_name=m.get("display_name"),
        description=m.get("description"),
        provider=m.get("provider"),
        model=m.get("model", ""),
        use=m.get("use", ""),
        base_url=m.get("base_url"),
        api_key_env=api_key_env,
        max_tokens=m.get("max_tokens", 8096),
        timeout=m.get("timeout", 60),
        max_retries=m.get("max_retries", 3),
        supports_thinking=m.get("supports_thinking", False),
        supports_vision=m.get("supports_vision", False),
        supports_reasoning_effort=m.get("supports_reasoning_effort", False),
        input_price_per_mtok=m.get("input_price_per_mtok"),
        output_price_per_mtok=m.get("output_price_per_mtok"),
        fallback_chain=m.get("fallback_chain") or [],
    )


@router.get("/models", response_model=ModelsConfigResponse, summary="List models config (full)")
async def list_models_config() -> ModelsConfigResponse:
    try:
        path = _resolve_config_path()
        data = _read_yaml(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raw_models: list[dict] = data.get("models") or []
    entries = [_yaml_model_to_entry(m) for m in raw_models]
    # Provide templates without secrets
    templates = {k: {kk: vv for kk, vv in v.items() if kk != "api_key"} for k, v in _MODEL_TEMPLATES.items()}
    return ModelsConfigResponse(models=entries, templates=templates)


@router.post("/models", response_model=ConfigWriteResponse, summary="Add a model to config.yaml")
async def add_model(req: ModelCreateRequest) -> ConfigWriteResponse:
    path = _resolve_config_path()
    with _config_transaction(path):
        try:
            data = _read_yaml(path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        models: list[dict] = data.get("models") or []
        if any(m.get("name") == req.name for m in models):
            raise HTTPException(status_code=409, detail=f"Model '{req.name}' already exists.")

        template = _MODEL_TEMPLATES.get(req.provider, {})
        entry: dict[str, Any] = {**template}
        entry["name"] = req.name
        if req.display_name:
            entry["display_name"] = req.display_name
        if req.description:
            entry["description"] = req.description
        entry["provider"] = req.provider
        entry["model"] = req.model
        if req.base_url:
            entry["base_url"] = req.base_url
        if req.api_key_env:
            entry["api_key"] = f"${req.api_key_env}"
        entry["max_tokens"] = req.max_tokens
        entry["supports_thinking"] = req.supports_thinking
        entry["supports_vision"] = req.supports_vision
        if req.input_price_per_mtok is not None:
            entry["input_price_per_mtok"] = req.input_price_per_mtok
        if req.output_price_per_mtok is not None:
            entry["output_price_per_mtok"] = req.output_price_per_mtok
        if req.fallback_chain:
            entry["fallback_chain"] = req.fallback_chain

        models.append(entry)
        data["models"] = models

        try:
            _write_yaml(path, data)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Model '%s' added to config.yaml", req.name)
    return ConfigWriteResponse(success=True, message=f"Model '{req.name}' added. Hot-reload will pick it up on the next request.")


@router.put("/models/{model_name}", response_model=ConfigWriteResponse, summary="Edit a model in config.yaml")
async def update_model(model_name: str, req: ModelUpdateRequest) -> ConfigWriteResponse:
    path = _resolve_config_path()
    with _config_transaction(path):
        try:
            data = _read_yaml(path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        models: list[dict] = data.get("models") or []
        idx = next((i for i, m in enumerate(models) if m.get("name") == model_name), None)
        if idx is None:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

        m = models[idx]
        if req.display_name is not None:
            m["display_name"] = req.display_name
        if req.description is not None:
            m["description"] = req.description
        if req.model is not None:
            m["model"] = req.model
        if req.base_url is not None:
            m["base_url"] = req.base_url
        if req.api_key_env is not None:
            m["api_key"] = f"${req.api_key_env}"
        if req.max_tokens is not None:
            m["max_tokens"] = req.max_tokens
        if req.timeout is not None:
            m["timeout"] = req.timeout
        if req.max_retries is not None:
            m["max_retries"] = req.max_retries
        if req.supports_thinking is not None:
            m["supports_thinking"] = req.supports_thinking
        if req.supports_vision is not None:
            m["supports_vision"] = req.supports_vision
        if req.input_price_per_mtok is not None:
            m["input_price_per_mtok"] = req.input_price_per_mtok
        if req.output_price_per_mtok is not None:
            m["output_price_per_mtok"] = req.output_price_per_mtok
        if req.fallback_chain is not None:
            m["fallback_chain"] = req.fallback_chain

        models[idx] = m
        data["models"] = models

        try:
            _write_yaml(path, data)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Model '%s' updated in config.yaml", model_name)
    return ConfigWriteResponse(success=True, message=f"Model '{model_name}' updated.")


@router.delete("/models/{model_name}", response_model=ConfigWriteResponse, summary="Remove a model from config.yaml")
async def delete_model(model_name: str) -> ConfigWriteResponse:
    path = _resolve_config_path()
    with _config_transaction(path):
        try:
            data = _read_yaml(path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        models: list[dict] = data.get("models") or []
        new_models = [m for m in models if m.get("name") != model_name]
        if len(new_models) == len(models):
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found.")

        data["models"] = new_models

        try:
            _write_yaml(path, data)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info("Model '%s' deleted from config.yaml", model_name)
    return ConfigWriteResponse(success=True, message=f"Model '{model_name}' deleted.")


@router.get("/model-templates", summary="List provider templates for new models")
async def list_model_templates() -> dict:
    return {"templates": {k: {kk: vv for kk, vv in v.items() if kk != "api_key"} for k, v in _MODEL_TEMPLATES.items()}}
