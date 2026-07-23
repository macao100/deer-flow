"""Tests for ModelEntry, Capabilities, ModelCost, and ModelRequirements."""
import pytest

from deerflow.routing.model_entry import (
    Capabilities,
    ModelCost,
    ModelEntry,
    ModelRequirements,
)


class TestCapabilities:
    def test_flags_are_unique(self):
        flags = list(Capabilities)
        values = [f.value for f in flags]
        # IntFlag values should be powers of 2
        for v in values:
            assert v & (v - 1) == 0, f"{v} is not a power of 2"

    def test_combine_flags(self):
        combo = Capabilities.THINKING | Capabilities.VISION
        assert Capabilities.THINKING in combo
        assert Capabilities.VISION in combo
        assert Capabilities.TOOLS not in combo

    def test_empty_requirements_has_no_required(self):
        req = ModelRequirements(required=Capabilities(0), estimated_input_tokens=100, estimated_output_tokens=100, user_message="")
        assert req.required == Capabilities(0)


class TestModelCost:
    def test_total_cost_zero_output(self):
        cost = ModelCost(input_price_per_mtok=1.0, output_price_per_mtok=2.0)
        # 1000 input tokens, 0 output = 1000/1M * 1.0 = 0.001
        assert cost.total_cost(input_tokens=1_000_000, output_tokens=0) == pytest.approx(1.0)

    def test_total_cost_mixed(self):
        cost = ModelCost(input_price_per_mtok=0.14, output_price_per_mtok=0.28)
        total = cost.total_cost(input_tokens=1_000_000, output_tokens=1_000_000)
        assert total == pytest.approx(0.42)

    def test_total_cost_handles_zero_prices(self):
        cost = ModelCost(input_price_per_mtok=0.0, output_price_per_mtok=0.0)
        assert cost.total_cost(input_tokens=1000, output_tokens=500) == 0.0


class TestModelEntry:
    def test_immutable(self):
        entry = ModelEntry(
            name="test-model",
            model_id="test-1",
            provider="openai",
            capabilities=Capabilities.THINKING | Capabilities.VISION,
            cost=ModelCost(1.0, 2.0),
            max_tokens=8192,
            priority=1,
            fallback_order=("fallback-1",),
            supports_thinking=True,
        )
        with pytest.raises(Exception):
            entry.name = "other"  # type: ignore

    def test_has_capability(self):
        entry = ModelEntry(
            name="m", model_id="m-1", provider="test",
            capabilities=Capabilities.THINKING | Capabilities.STREAMING,
            cost=ModelCost(0, 0), max_tokens=4096, priority=1,
            fallback_order=(), supports_thinking=True,
        )
        assert entry.has_capability(Capabilities.THINKING)
        assert not entry.has_capability(Capabilities.VISION)


class TestModelRequirements:
    def test_from_message_detects_long_message(self):
        req = ModelRequirements.from_message("hi")
        assert req.estimated_input_tokens > 0

    def test_from_message_estimates_tokens(self):
        long_msg = "architecture refactor design " * 100
        req = ModelRequirements.from_message(long_msg)
        assert req.estimated_input_tokens > 500
