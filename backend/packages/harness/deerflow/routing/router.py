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
            # Fallback: try relaxing one capability at a time
            if requirements.required & Capabilities.THINKING:
                candidates = self._registry.filter(required=requirements.required & ~Capabilities.THINKING)
                logger.debug("ModelRouter: relaxed THINKING requirement, %d candidates", len(candidates))
            if not candidates and requirements.required & Capabilities.LARGE_CONTEXT:
                candidates = self._registry.filter(required=requirements.required & ~Capabilities.LARGE_CONTEXT)
                logger.debug("ModelRouter: relaxed LARGE_CONTEXT requirement, %d candidates", len(candidates))
            # I3: If both THINKING and LARGE_CONTEXT were required and neither
            # single-relaxation produced candidates, try relaxing both.
            if not candidates and (requirements.required & Capabilities.THINKING) and (requirements.required & Capabilities.LARGE_CONTEXT):
                candidates = self._registry.filter(required=requirements.required & ~Capabilities.THINKING & ~Capabilities.LARGE_CONTEXT)
                logger.debug("ModelRouter: relaxed both THINKING and LARGE_CONTEXT, %d candidates", len(candidates))

        if not candidates:
            raise ValueError(
                f"No model satisfies requirements {requirements.required}. "
                f"Available models: {[e.name for e in self._registry.list_all()]}"
            )

        # ── Strategy selection ───────────────────────────────────────────
        strategy = _STRATEGY_MAP.get(strategy_hint, self._strategy) if strategy_hint else self._strategy
        latency_stats = self._latency_tracker.all_stats()
        selected = strategy.select(candidates, requirements, latency_stats)

        # ── Fallback chain resolution ──────────────────────────────────────
        # If the selected model has a fallback_order, iterate through it and
        # use the first fallback that exists in the registry and satisfies the
        # required capabilities.
        if selected.fallback_order:
            for fallback_name in selected.fallback_order:
                fallback_entry = self._registry.get(fallback_name)
                if fallback_entry is None:
                    logger.debug("ModelRouter: fallback %r not found in registry, skipping", fallback_name)
                    continue
                if not fallback_entry.has_capability(requirements.required):
                    logger.debug(
                        "ModelRouter: fallback %r does not satisfy required capabilities %r, skipping",
                        fallback_name, requirements.required,
                    )
                    continue
                logger.info(
                    "ModelRouter: falling back from %r to %r (provider=%s, cost=$%.4f)",
                    selected.name, fallback_name, fallback_entry.provider,
                    fallback_entry.cost.total_cost(requirements.estimated_input_tokens, requirements.estimated_output_tokens),
                )
                selected = fallback_entry
                break
            else:
                logger.warning(
                    "ModelRouter: no valid fallback found for %r (fallback_order=%r) — keeping primary",
                    selected.name, selected.fallback_order,
                )

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
