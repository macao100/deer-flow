"""Integration test: ModelRouter with real config.yaml."""
import pytest
from deerflow.config import get_app_config
from deerflow.routing import ModelRegistry, ModelRouter, ModelRequirements, BalancedStrategy, LatencyTracker


class TestModelRouterIntegration:
    @pytest.mark.integration
    def test_registry_from_real_config(self):
        """ModelRegistry can be built from the actual config.yaml."""
        app_config = get_app_config()
        registry = ModelRegistry.from_config(app_config)
        entries = registry.list_all()
        assert len(entries) > 0, "Expected at least one model from config.yaml"
        assert any(e.name == "deepseek-v4-flash" for e in entries), "deepseek-v4-flash should be in registry"

    @pytest.mark.integration
    def test_router_with_real_registry(self):
        """ModelRouter can route with real config data."""
        app_config = get_app_config()
        registry = ModelRegistry.from_config(app_config)

        router = ModelRouter(
            registry=registry,
            strategy=BalancedStrategy(),
            latency_tracker=LatencyTracker(),
        )

        # Simple message → should route to a cheap model
        model_name, thinking = router.route(
            requirements=ModelRequirements.from_message("hello"),
        )
        assert model_name is not None
        assert model_name in {e.name for e in registry.list_all()}

    @pytest.mark.integration
    def test_router_bypass_for_explicit_model(self):
        """User override should bypass routing."""
        app_config = get_app_config()
        registry = ModelRegistry.from_config(app_config)

        # I4: Precondition — verify the override model exists in the registry.
        assert registry.get("deepseek-v4-pro") is not None, \
            "deepseek-v4-pro must be in the registry for this test"

        router = ModelRouter(
            registry=registry,
            strategy=BalancedStrategy(),
            latency_tracker=LatencyTracker(),
        )

        model_name, thinking = router.route(
            requirements=ModelRequirements.from_message("hello"),
            user_model_override="deepseek-v4-pro",
        )
        assert model_name == "deepseek-v4-pro"

    @pytest.mark.integration
    def test_complexity_router_still_works(self):
        """Old complexity_router should still function when model_router is disabled."""
        from deerflow.agents.middlewares.complexity_router_middleware import route_by_complexity

        # Build a message long enough to trigger both the keyword and token-threshold criteria.
        # _count_tokens_heuristic uses ascii_chars // 4, so we need >= 2004 chars for >500 tokens.
        long_message = (
            "architecture design review for the new system. "
            + "We need to review the architecture design of the entire platform. " * 30
        )
        assert len(long_message) >= 2004, f"Test message too short: {len(long_message)} chars"

        result = route_by_complexity(
            user_message=long_message,
            current_model_name=None,
            thread_message_count=5,
            simple_model="deepseek-v4-flash",
            complex_model="deepseek-v4-pro",
            complex_thinking=True,
            simple_thinking=False,
            token_threshold=500,
            history_threshold=10,
            complex_keywords=["architecture", "design", "review"],
            min_criteria=2,
        )
        assert result is not None
        assert result[0] == "deepseek-v4-pro"
