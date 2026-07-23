"""ModelEntry, Capabilities, ModelCost, and ModelRequirements."""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag, auto


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
        import re
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
        """CJK-aware token estimation (same heuristic as complexity_router)."""
        if not text:
            return 0
        cjk = sum(1 for ch in text if "一" <= ch <= "鿿" or "぀" <= ch <= "ヿ")
        ascii_chars = len(text) - cjk
        return cjk + max(1, ascii_chars // 4)
