"""Tests for ModelRouter orchestrator."""
from unittest.mock import Mock
from deerflow.routing.model_entry import (
    Capabilities,
    ModelCost,
    ModelEntry,
    ModelRegistry,
    ModelRequirements,
)
from deerflow.routing.latency_tracker import LatencyTracker
from deerflow.routing.strategies import BalancedStrategy, CostOptimizedStrategy
from deerflow.routing.router import ModelRouter


def _entry(name: str, caps: Capabilities = Capabilities.TOOLS, input_cost: float = 1.0,
           output_cost: float = 2.0, max_tokens: int = 8192, supports_thinking: bool = False) -> ModelEntry:
    return ModelEntry(
        name=name, model_id=name, provider="test",
        capabilities=caps, cost=ModelCost(input_cost, output_cost),
        max_tokens=max_tokens, priority=1, fallback_order=(), supports_thinking=supports_thinking,
    )


class TestModelRouter:
    def test_route_respects_user_override(self):
        """When user explicitly picks a model, bypass routing."""
        registry = ModelRegistry({"m1": _entry("m1"), "m2": _entry("m2")})
        router = ModelRouter(registry=registry, strategy=CostOptimizedStrategy(), latency_tracker=LatencyTracker())
        model_name, thinking = router.route(
            requirements=ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=100, estimated_output_tokens=100, user_message="hi"),
            user_model_override="m2",
        )
        assert model_name == "m2"

    def test_route_picks_best_match(self):
        """Without override, route selects best according to strategy."""
        registry = ModelRegistry({
            "cheap": _entry("cheap", input_cost=0.1, output_cost=0.2),
            "expensive": _entry("expensive", input_cost=10.0, output_cost=20.0),
        })
        router = ModelRouter(registry=registry, strategy=CostOptimizedStrategy(), latency_tracker=LatencyTracker())
        model_name, _ = router.route(
            requirements=ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=1000, estimated_output_tokens=1000, user_message="hi"),
        )
        assert model_name == "cheap"

    def test_route_no_candidates_raises(self):
        """When no model satisfies required capabilities."""
        registry = ModelRegistry({"basic": _entry("basic", Capabilities.TOOLS)})
        router = ModelRouter(registry=registry, strategy=BalancedStrategy(), latency_tracker=LatencyTracker())
        import pytest
        with pytest.raises(ValueError, match="No model satisfies"):
            router.route(
                requirements=ModelRequirements(required=Capabilities.VISION, estimated_input_tokens=100, estimated_output_tokens=100, user_message="hi"),
            )

    def test_record_latency_delegates_to_tracker(self):
        tracker = LatencyTracker()
        registry = ModelRegistry({"m1": _entry("m1")})
        router = ModelRouter(registry=registry, strategy=BalancedStrategy(), latency_tracker=tracker)
        router.record_latency("m1", 250.0)
        assert tracker.p50("m1") == 250.0

    def test_route_returns_thinking_flag(self):
        """Thinking-capable model selected should return thinking=True."""
        registry = ModelRegistry({
            "thinker": _entry("thinker", Capabilities.TOOLS | Capabilities.THINKING, supports_thinking=True),
        })
        router = ModelRouter(registry=registry, strategy=BalancedStrategy(), latency_tracker=LatencyTracker())
        req = ModelRequirements(required=Capabilities.THINKING, estimated_input_tokens=100, estimated_output_tokens=100, user_message="complex analysis needed")
        model_name, thinking = router.route(requirements=req)
        assert model_name == "thinker"
        assert thinking is True
