"""Tests for routing strategies."""
import pytest

from deerflow.routing.model_entry import (
    Capabilities,
    ModelCost,
    ModelEntry,
    ModelRequirements,
)
from deerflow.routing.strategies import (
    BalancedStrategy,
    CostOptimizedStrategy,
    PerformanceMaxStrategy,
)


def _entry(name: str, caps: Capabilities = Capabilities.TOOLS, input_cost: float = 1.0,
           output_cost: float = 2.0, max_tokens: int = 8192) -> ModelEntry:
    return ModelEntry(
        name=name, model_id=name, provider="test",
        capabilities=caps, cost=ModelCost(input_cost, output_cost),
        max_tokens=max_tokens, priority=1, fallback_order=(), supports_thinking=False,
    )


class TestCostOptimizedStrategy:
    def test_picks_cheapest(self):
        candidates = [
            _entry("cheap", input_cost=0.1, output_cost=0.2),
            _entry("expensive", input_cost=10.0, output_cost=20.0),
        ]
        strategy = CostOptimizedStrategy()
        req = ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=1000, estimated_output_tokens=1000, user_message="")
        result = strategy.select(candidates, req, {})
        assert result.name == "cheap"

    def test_empty_candidates_raises(self):
        strategy = CostOptimizedStrategy()
        req = ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=100, estimated_output_tokens=100, user_message="")
        with pytest.raises(ValueError, match="No candidates"):
            strategy.select([], req, {})


class TestPerformanceMaxStrategy:
    def test_picks_highest_max_tokens(self):
        candidates = [
            _entry("small", max_tokens=4096),
            _entry("large", max_tokens=128000),
            _entry("medium", max_tokens=16384),
        ]
        strategy = PerformanceMaxStrategy()
        req = ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=100, estimated_output_tokens=100, user_message="")
        result = strategy.select(candidates, req, {})
        assert result.name == "large"

    def test_prefers_thinking(self):
        candidates = [
            ModelEntry(name="thinker", model_id="t", provider="test",
                       capabilities=Capabilities.TOOLS | Capabilities.THINKING,
                       cost=ModelCost(1, 2), max_tokens=8192, priority=1,
                       fallback_order=(), supports_thinking=True),
            _entry("basic", max_tokens=16384),
        ]
        strategy = PerformanceMaxStrategy()
        req = ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=100, estimated_output_tokens=100, user_message="")
        result = strategy.select(candidates, req, {})
        assert result.name == "thinker"


class TestBalancedStrategy:
    def test_picks_good_balance(self):
        """With similar latency, should prefer cheaper."""
        candidates = [
            _entry("cheap", input_cost=0.1, output_cost=0.2),
            _entry("expensive", input_cost=10.0, output_cost=20.0),
        ]
        strategy = BalancedStrategy()
        req = ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=1000, estimated_output_tokens=1000, user_message="")
        latency_stats = {"cheap": {"p50": 100.0}, "expensive": {"p50": 100.0}}
        result = strategy.select(candidates, req, latency_stats)
        assert result.name == "cheap"

    def test_latency_penalty(self):
        """A slower cheap model loses to a faster expensive one."""
        cheap = _entry("cheap-slow", input_cost=0.1, output_cost=0.2)
        fast = _entry("fast-pricey", input_cost=2.0, output_cost=4.0)
        strategy = BalancedStrategy()
        req = ModelRequirements(required=Capabilities.TOOLS, estimated_input_tokens=10000, estimated_output_tokens=10000, user_message="")
        latency_stats = {"cheap-slow": {"p50": 5000.0}, "fast-pricey": {"p50": 100.0}}
        result = strategy.select([cheap, fast], req, latency_stats)
        # Fast should win despite higher cost because latency penalty dominates
        assert result.name == "fast-pricey"
