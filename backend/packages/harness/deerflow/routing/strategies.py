"""Routing strategy interface and implementations."""
from __future__ import annotations

import logging
from typing import Literal, Protocol

from deerflow.routing.model_entry import Capabilities, ModelEntry, ModelRequirements

logger = logging.getLogger(__name__)

StrategyHint = Literal["cost_optimized", "performance_max", "balanced"]


class RoutingStrategy(Protocol):
    """Protocol for model selection strategies."""

    def select(
        self,
        candidates: list[ModelEntry],
        requirements: ModelRequirements,
        latency_stats: dict[str, dict[str, float]],
    ) -> ModelEntry:
        """Select the best model from *candidates*."""
        ...


class CostOptimizedStrategy:
    """Select the cheapest model that satisfies requirements."""

    def select(
        self,
        candidates: list[ModelEntry],
        requirements: ModelRequirements,
        latency_stats: dict[str, dict[str, float]],
    ) -> ModelEntry:
        if not candidates:
            raise ValueError("No candidates available for selection")
        return min(
            candidates,
            key=lambda e: e.cost.total_cost(requirements.estimated_input_tokens, requirements.estimated_output_tokens),
        )


class PerformanceMaxStrategy:
    """Select the most capable model (max tokens, thinking preferred)."""

    def select(
        self,
        candidates: list[ModelEntry],
        requirements: ModelRequirements,
        latency_stats: dict[str, dict[str, float]],
    ) -> ModelEntry:
        if not candidates:
            raise ValueError("No candidates available for selection")
        return max(
            candidates,
            key=lambda e: (Capabilities.THINKING in e.capabilities, e.max_tokens),
        )


class BalancedStrategy:
    """Select based on a composite score: capability bonus / (normalized cost × latency penalty)."""

    def select(
        self,
        candidates: list[ModelEntry],
        requirements: ModelRequirements,
        latency_stats: dict[str, dict[str, float]],
    ) -> ModelEntry:
        if not candidates:
            raise ValueError("No candidates available for selection")
        if len(candidates) == 1:
            return candidates[0]

        scores: dict[str, float] = {}
        for entry in candidates:
            cost = entry.cost.total_cost(requirements.estimated_input_tokens, requirements.estimated_output_tokens)
            cost = max(cost, 0.0001)  # avoid division by zero

            p50 = latency_stats.get(entry.name, {}).get("p50", 500.0)
            latency_factor = max(p50, 1.0) / 1000.0  # normalize to seconds

            # Capability bonus: +1 for thinking, +0.5 for vision, +0.3 for large context
            bonus = 1.0
            if Capabilities.THINKING in entry.capabilities:
                bonus += 0.5
            if Capabilities.VISION in entry.capabilities:
                bonus += 0.3
            if Capabilities.LARGE_CONTEXT in entry.capabilities:
                bonus += 0.2

            score = bonus / (cost * latency_factor)
            scores[entry.name] = score

        best = max(candidates, key=lambda e: scores[e.name])
        logger.debug("BalancedStrategy: selected %r (score=%.4f)", best.name, scores[best.name])
        return best
