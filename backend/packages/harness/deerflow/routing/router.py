"""ModelRouter — orchestrates registry, strategy, and latency feedback."""
from __future__ import annotations

import logging

from deerflow.routing.latency_tracker import LatencyTracker
from deerflow.routing.model_entry import Capabilities, ModelRegistry, ModelRequirements
from deerflow.routing.strategies import (
    BalancedStrategy,
    CostOptimizedStrategy,
    PerformanceMaxStrategy,
    RoutingStrategy,
    StrategyHint,
)

logger = logging.getLogger(__name__)

_STRATEGY_MAP: dict[StrategyHint, RoutingStrategy] = {
    "cost_optimized": CostOptimizedStrategy(),
    "performance_max": PerformanceMaxStrategy(),
    "balanced": BalancedStrategy(),
}


class ModelRouter:
    """Intelligent multi-model router.

    Selects the best model for each request based on:
    - Required capabilities (thinking, vision, large context, etc.)
    - Selection strategy (cost, performance, balanced)
    - Latency data from previous runs (feedback loop)

    Usage::

        router = ModelRouter(
            registry=ModelRegistry.from_config(app_config),
            strategy=BalancedStrategy(),
            latency_tracker=LatencyTracker(),
        )
        model_name, thinking = router.route(
            requirements=ModelRequirements.from_message(user_text),
            user_model_override=None,
        )
    """

    def __init__(
        self,
        registry: ModelRegistry,
        strategy: RoutingStrategy,
        latency_tracker: LatencyTracker | None = None,
    ) -> None:
        self._registry = registry
        self._strategy = strategy
        self._latency_tracker = latency_tracker or LatencyTracker()

    def route(
        self,
        requirements: ModelRequirements,
        user_model_override: str | None = None,
        strategy_hint: StrategyHint | None = None,
    ) -> tuple[str, bool]:
        """Select the best model and return ``(model_name, thinking_enabled)``.

        Parameters
        ----------
        requirements:
            Required capabilities and token estimates.
        user_model_override:
            If set, bypass all routing and use this model directly.
        strategy_hint:
            Override the default strategy for this call.
        """
        # ── User override: bypass everything ─────────────────────────────
        if user_model_override:
            entry = self._registry.get(user_model_override)
            if entry is not None:
                thinking = Capabilities.THINKING in entry.capabilities
                logger.debug("ModelRouter: user override %r (thinking=%s)", user_model_override, thinking)
                return (user_model_override, thinking)
            logger.warning("ModelRouter: user override %r not found in registry, falling through", user_model_override)

        # ── Capability filtering ─────────────────────────────────────────
        candidates = self._registry.filter(required=requirements.required)
        if not candidates:
            # Fallback: try without the most restrictive capability
            if requirements.required & Capabilities.THINKING:
                candidates = self._registry.filter(required=requirements.required & ~Capabilities.THINKING)
                logger.debug("ModelRouter: relaxed THINKING requirement, %d candidates", len(candidates))
            if not candidates and requirements.required & Capabilities.LARGE_CONTEXT:
                candidates = self._registry.filter(required=requirements.required & ~Capabilities.LARGE_CONTEXT)
                logger.debug("ModelRouter: relaxed LARGE_CONTEXT requirement, %d candidates", len(candidates))

        if not candidates:
            raise ValueError(
                f"No model satisfies requirements {requirements.required}. "
                f"Available models: {[e.name for e in self._registry.list_all()]}"
            )

        # ── Strategy selection ───────────────────────────────────────────
        strategy = _STRATEGY_MAP.get(strategy_hint or "balanced", self._strategy)
        latency_stats = self._latency_tracker.all_stats()
        selected = strategy.select(candidates, requirements, latency_stats)

        thinking = Capabilities.THINKING in selected.capabilities and selected.supports_thinking
        logger.info(
            "ModelRouter: selected %r (thinking=%s, provider=%s, cost=$%.4f)",
            selected.name, thinking, selected.provider,
            selected.cost.total_cost(requirements.estimated_input_tokens, requirements.estimated_output_tokens),
        )
        return (selected.name, thinking)

    def record_latency(self, model_name: str, latency_ms: float) -> None:
        """Record end-to-end latency for the model used in a completed run."""
        self._latency_tracker.record(model_name, latency_ms)
