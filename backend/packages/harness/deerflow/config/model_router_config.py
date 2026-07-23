"""Configuration for the intelligent ModelRouter."""
from typing import Literal

from pydantic import BaseModel, Field

StrategyHint = Literal["cost_optimized", "performance_max", "balanced"]


class ModelRouterConfig(BaseModel):
    """Configuration for intelligent multi-model routing.

    When enabled, the ModelRouter selects the best model for each request
    based on required capabilities, selection strategy, and historical latency data.
    """

    enabled: bool = Field(
        default=False,
        description="Enable intelligent multi-model routing",
    )
    default_strategy: StrategyHint = Field(
        default="balanced",
        description="Default selection strategy: cost_optimized, performance_max, or balanced",
    )
    latency_window_size: int = Field(
        default=50,
        ge=1,
        description="Sliding window size for latency tracking per model",
    )
