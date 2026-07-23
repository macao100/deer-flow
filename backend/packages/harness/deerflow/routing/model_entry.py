"""ModelEntry, Capabilities, ModelCost, and ModelRequirements."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import IntFlag, auto
from typing import TYPE_CHECKING

from deerflow.routing.token_estimation import estimate_tokens


class Capabilities(IntFlag):
    """Capability flags for a model."""
    THINKING = auto()
    VISION = auto()
    TOOLS = auto()
    JSON_MODE = auto()
    STREAMING = auto()
    LARGE_CONTEXT = auto()


@dataclass(frozen=True)
class ModelCost:
    """Cost per 1M tokens."""
    input_price_per_mtok: float
    output_price_per_mtok: float

    def total_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens / 1_000_000) * self.input_price_per_mtok + (output_tokens / 1_000_000) * self.output_price_per_mtok


@dataclass(frozen=True)
class ModelEntry:
    """Immutable registry entry for a model."""
    name: str
    model_id: str
    provider: str
    capabilities: Capabilities
    cost: ModelCost
    max_tokens: int
    priority: int = 1
    fallback_order: tuple[str, ...] = ()
    supports_thinking: bool = False

    def has_capability(self, cap: Capabilities) -> bool:
        return (self.capabilities & cap) == cap


@dataclass(frozen=True)
class ModelRequirements:
    """Requirements for model selection."""
    required: Capabilities
    estimated_input_tokens: int
    estimated_output_tokens: int
    user_message: str = ""

    @classmethod
    def from_message(cls, text: str, estimated_output: int = 4096) -> ModelRequirements:
        """Derive requirements from a user message."""
        required = Capabilities.TOOLS | Capabilities.STREAMING
        est_input = cls._estimate_tokens(text)

        # Check for file references (LARGE_CONTEXT)
        file_pattern = re.compile(r"(?:^|\s|[`\"'])(?:[./]?[\w-]+/)+[\w.-]+\.\w{1,6}(?:[`\"']|$|\s|[:,])")
        if file_pattern.findall(text):
            required |= Capabilities.LARGE_CONTEXT

        # Long/complex messages → THINKING
        if est_input > 2000:
            required |= Capabilities.THINKING

        return cls(
            required=required,
            estimated_input_tokens=est_input,
            estimated_output_tokens=estimated_output,
            user_message=text,
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """CJK-aware token estimation (shared utility)."""
        return estimate_tokens(text)


if TYPE_CHECKING:
    from deerflow.config.app_config import AppConfig

logger = logging.getLogger(__name__)

_PROVIDER_MAP: dict[str, str] = {
    "langchain_openai": "openai",
    "langchain_anthropic": "anthropic",
    "langchain_ollama": "ollama",
    "deerflow.models.patched_deepseek": "deepseek",
    "deerflow.models.patched_openai": "openai",
    "deerflow.models.vllm_provider": "vllm",
    "deerflow.models.claude_provider": "anthropic",
    "deerflow.models.mindie_provider": "mindie",
    "deerflow.models.patched_mimo": "mimo",
    "deerflow.models.patched_minimax": "minimax",
    "deerflow.models.patched_stepfun": "stepfun",
    "langchain_mistralai": "mistral",
}


class ModelRegistry:
    """Registry of available models, built from config.yaml."""

    def __init__(self, entries: dict[str, ModelEntry]) -> None:
        self._entries = entries

    def get(self, name: str) -> ModelEntry | None:
        return self._entries.get(name)

    def filter(self, required: Capabilities, forbidden: Capabilities | None = None) -> list[ModelEntry]:
        """Return entries that satisfy *required* capabilities and have none of *forbidden*."""
        results: list[ModelEntry] = []
        for entry in self._entries.values():
            if not entry.has_capability(required):
                continue
            if forbidden and (entry.capabilities & forbidden):
                continue
            results.append(entry)
        return results

    def list_all(self) -> list[ModelEntry]:
        return list(self._entries.values())

    @classmethod
    def from_config(cls, app_config: AppConfig) -> ModelRegistry:
        """Build the registry from an AppConfig's models list."""
        entries: dict[str, ModelEntry] = {}
        for model_cfg in app_config.models:
            try:
                capabilities = Capabilities.TOOLS | Capabilities.STREAMING

                if getattr(model_cfg, "supports_thinking", False):
                    capabilities |= Capabilities.THINKING
                if getattr(model_cfg, "supports_vision", False):
                    capabilities |= Capabilities.VISION

                max_tokens = getattr(model_cfg, "max_tokens", 0) or 4096
                if max_tokens >= 128_000:
                    capabilities |= Capabilities.LARGE_CONTEXT

                # JSON_MODE: OpenAI models usually support it
                use_path = getattr(model_cfg, "use", "")
                if "openai" in use_path.lower() or "deepseek" in use_path.lower():
                    capabilities |= Capabilities.JSON_MODE

                # Derive provider from use path
                provider = _PROVIDER_MAP.get(use_path.split(":")[0], "unknown")

                # Build cost
                cost = ModelCost(
                    input_price_per_mtok=getattr(model_cfg, "input_price_per_mtok", 0.0) or 0.0,
                    output_price_per_mtok=getattr(model_cfg, "output_price_per_mtok", 0.0) or 0.0,
                )

                # Build fallback order from config
                fallback_raw = getattr(model_cfg, "fallback_chain", None) or []
                fallback_order = tuple(fallback_raw) if isinstance(fallback_raw, list) else ()

                entry = ModelEntry(
                    name=model_cfg.name,
                    model_id=model_cfg.model,
                    provider=provider,
                    capabilities=capabilities,
                    cost=cost,
                    max_tokens=max_tokens,
                    supports_thinking=getattr(model_cfg, "supports_thinking", False),
                    fallback_order=fallback_order,
                )
                entries[entry.name] = entry
            except Exception:
                logger.warning("Failed to build ModelEntry for %r", getattr(model_cfg, "name", "?"), exc_info=True)

        logger.debug("ModelRegistry built: %d entries from config", len(entries))
        return cls(entries)
