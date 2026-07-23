"""Tests for ModelRegistry."""
from deerflow.routing.model_entry import (
    Capabilities,
    ModelCost,
    ModelEntry,
    ModelRegistry,
)


def _make_entry(name: str, caps: Capabilities = Capabilities.TOOLS, max_tokens: int = 8192) -> ModelEntry:
    return ModelEntry(
        name=name, model_id=name, provider="test",
        capabilities=caps, cost=ModelCost(1.0, 2.0),
        max_tokens=max_tokens, priority=1, fallback_order=(), supports_thinking=False,
    )


class TestModelRegistry:
    def test_get_existing(self):
        reg = ModelRegistry({"a": _make_entry("a")})
        assert reg.get("a") is not None
        assert reg.get("a").name == "a"

    def test_get_missing(self):
        reg = ModelRegistry({})
        assert reg.get("nonexistent") is None

    def test_filter_by_required(self):
        reg = ModelRegistry({
            "basic": _make_entry("basic", Capabilities.TOOLS),
            "thinker": _make_entry("thinker", Capabilities.TOOLS | Capabilities.THINKING),
            "vision": _make_entry("vision", Capabilities.TOOLS | Capabilities.THINKING | Capabilities.VISION),
        })
        results = reg.filter(required=Capabilities.THINKING)
        names = {r.name for r in results}
        assert "thinker" in names
        assert "vision" in names
        assert "basic" not in names

    def test_filter_by_forbidden(self):
        reg = ModelRegistry({
            "a": _make_entry("a", Capabilities.TOOLS),
            "b": _make_entry("b", Capabilities.TOOLS | Capabilities.THINKING),
        })
        results = reg.filter(required=Capabilities.TOOLS, forbidden=Capabilities.THINKING)
        assert len(results) == 1
        assert results[0].name == "a"

    def test_filter_empty(self):
        reg = ModelRegistry({"a": _make_entry("a", Capabilities.TOOLS)})
        results = reg.filter(required=Capabilities.VISION)
        assert results == []

    def test_list_all(self):
        reg = ModelRegistry({"a": _make_entry("a"), "b": _make_entry("b")})
        assert len(reg.list_all()) == 2

    def test_from_config_empty(self):
        """from_config with no models returns empty registry."""
        from unittest.mock import Mock
        cfg = Mock()
        cfg.models = []
        reg = ModelRegistry.from_config(cfg)
        assert reg.list_all() == []

    def test_from_config_builds_entries(self):
        """from_config should derive capabilities from model config fields."""
        from unittest.mock import Mock, PropertyMock

        # Build a mock config with one model
        model_mock = Mock()
        type(model_mock).name = PropertyMock(return_value="test-model")
        type(model_mock).model = PropertyMock(return_value="test-model-id")
        type(model_mock).use = PropertyMock(return_value="langchain_openai:ChatOpenAI")
        type(model_mock).supports_thinking = PropertyMock(return_value=True)
        type(model_mock).supports_vision = PropertyMock(return_value=False)
        type(model_mock).max_tokens = PropertyMock(return_value=16384)
        type(model_mock).input_price_per_mtok = PropertyMock(return_value=0.14)
        type(model_mock).output_price_per_mtok = PropertyMock(return_value=0.28)
        # Ensure extras dict returns None for optional fields
        type(model_mock).model_extra = PropertyMock(return_value={})

        cfg = Mock()
        cfg.models = [model_mock]

        reg = ModelRegistry.from_config(cfg)
        entry = reg.get("test-model")
        assert entry is not None
        assert entry.name == "test-model"
        assert entry.model_id == "test-model-id"
        assert entry.provider == "openai"  # langchain_openai → openai
        assert Capabilities.THINKING in entry.capabilities
        assert Capabilities.VISION not in entry.capabilities
        assert entry.cost.input_price_per_mtok == 0.14
