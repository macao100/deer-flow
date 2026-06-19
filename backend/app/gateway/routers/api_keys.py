"""API keys management — read (masked) and update .env file."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from dotenv import find_dotenv, set_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.gateway.file_lock import interprocess_lock

logger = logging.getLogger(__name__)

# Serialize .env writes: a process-local lock plus a host-wide interprocess lock
# so two concurrent key updates (even from separate processes) can't interleave
# and corrupt the file.
_ENV_WRITE_LOCK = threading.Lock()

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Keys exposed in the UI, in display order.
_KNOWN_KEYS: list[dict[str, str]] = [
    {
        "env_var": "DEEPSEEK_API_KEY",
        "label": "DeepSeek API Key",
        "provider": "deepseek",
        "placeholder": "sk-...",
        "docs_url": "https://platform.deepseek.com/api_keys",
    },
    {
        "env_var": "OPENAI_API_KEY",
        "label": "OpenAI API Key",
        "provider": "openai",
        "placeholder": "sk-...",
        "docs_url": "https://platform.openai.com/api-keys",
    },
    {
        "env_var": "GEMINI_API_KEY",
        "label": "Google Gemini API Key",
        "provider": "google",
        "placeholder": "AIza...",
        "docs_url": "https://aistudio.google.com/app/apikey",
    },
    {
        "env_var": "TELEGRAM_BOT_TOKEN",
        "label": "Telegram Bot Token",
        "provider": "telegram",
        "placeholder": "123456789:ABC-DEF...",
        "docs_url": "https://core.telegram.org/bots#botfather",
    },
    {
        "env_var": "SERPER_API_KEY",
        "label": "Serper API Key",
        "provider": "serper",
        "placeholder": "...",
        "docs_url": "https://serper.dev",
    },
    {
        "env_var": "TAVILY_API_KEY",
        "label": "Tavily API Key",
        "provider": "tavily",
        "placeholder": "tvly-...",
        "docs_url": "https://app.tavily.com",
    },
    {
        "env_var": "JINA_API_KEY",
        "label": "Jina AI API Key",
        "provider": "jina",
        "placeholder": "jina_...",
        "docs_url": "https://jina.ai",
    },
    {
        "env_var": "OPENROUTER_API_KEY",
        "label": "OpenRouter API Key",
        "provider": "openrouter",
        "placeholder": "sk-or-v1-...",
        "docs_url": "https://openrouter.ai/keys",
    },
    {
        "env_var": "NVIDIA_API_KEY",
        "label": "NVIDIA NIM API Key",
        "provider": "nvidia",
        "placeholder": "nvapi-...",
        "docs_url": "https://build.nvidia.com/nim",
    },
    {
        "env_var": "ANTHROPIC_API_KEY",
        "label": "Anthropic API Key",
        "provider": "anthropic",
        "placeholder": "sk-ant-...",
        "docs_url": "https://console.anthropic.com/settings/keys",
    },
    {
        "env_var": "GROQ_API_KEY",
        "label": "Groq API Key",
        "provider": "groq",
        "placeholder": "gsk_...",
        "docs_url": "https://console.groq.com/keys",
    },
    {
        "env_var": "MISTRAL_API_KEY",
        "label": "Mistral API Key",
        "provider": "mistral",
        "placeholder": "...",
        "docs_url": "https://console.mistral.ai/api-keys",
    },
    {
        "env_var": "FIRECRAWL_API_KEY",
        "label": "Firecrawl API Key",
        "provider": "firecrawl",
        "placeholder": "fc-...",
        "docs_url": "https://www.firecrawl.dev/account",
    },
]

_ALLOWED_ENV_VARS: frozenset[str] = frozenset(k["env_var"] for k in _KNOWN_KEYS)


def _mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return "****" + value[-4:]


class ApiKeyEntry(BaseModel):
    env_var: str
    label: str
    provider: str
    placeholder: str
    docs_url: str
    is_set: bool
    masked_value: str


class ApiKeysResponse(BaseModel):
    keys: list[ApiKeyEntry]


class UpdateApiKeyRequest(BaseModel):
    env_var: str = Field(..., description="Environment variable name")
    value: str = Field(..., description="New value — empty string to clear")


class UpdateApiKeyResponse(BaseModel):
    success: bool
    restart_required: bool
    message: str


@router.get("/api-keys", response_model=ApiKeysResponse, summary="List API keys (masked)")
async def list_api_keys() -> ApiKeysResponse:
    keys = [
        ApiKeyEntry(
            env_var=entry["env_var"],
            label=entry["label"],
            provider=entry["provider"],
            placeholder=entry["placeholder"],
            docs_url=entry["docs_url"],
            is_set=bool(os.environ.get(entry["env_var"])),
            masked_value=_mask(os.environ.get(entry["env_var"])),
        )
        for entry in _KNOWN_KEYS
    ]
    return ApiKeysResponse(keys=keys)


@router.put("/api-keys", response_model=UpdateApiKeyResponse, summary="Update an API key in .env")
async def update_api_key(request: UpdateApiKeyRequest) -> UpdateApiKeyResponse:
    if request.env_var not in _ALLOWED_ENV_VARS:
        raise HTTPException(status_code=400, detail=f"Unknown variable: {request.env_var}")

    env_path = find_dotenv()
    if not env_path:
        env_path = str(Path.cwd() / ".env")
        Path(env_path).touch()

    action = "set" if request.value else "cleared"
    with _ENV_WRITE_LOCK, interprocess_lock(env_path):
        success, _key, _value = set_key(env_path, request.env_var, request.value, quote_mode="never")
        if not success:
            raise HTTPException(status_code=500, detail=f"Could not write {request.env_var} to {env_path}")

        if request.value:
            os.environ[request.env_var] = request.value
        elif request.env_var in os.environ:
            del os.environ[request.env_var]

    # Audit trail — record WHICH key changed, never the value itself.
    logger.info("API key %s via settings UI: %s", action, request.env_var)

    return UpdateApiKeyResponse(
        success=True,
        restart_required=True,
        message=f"{request.env_var} updated. Restart DeerFlow for the change to take full effect.",
    )
