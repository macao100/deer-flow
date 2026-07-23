"""Tests for ModelRouterConfig."""
import pytest
from deerflow.config.model_router_config import ModelRouterConfig


class TestModelRouterConfig:
    def test_defaults(self):
        cfg = ModelRouterConfig()
        assert cfg.enabled is False
        assert cfg.default_strategy == "balanced"
        assert cfg.latency_window_size == 50

    def test_strategy_validation(self):
        with pytest.raises(ValueError):
            ModelRouterConfig(default_strategy="invalid")

    def test_window_size_minimum(self):
        with pytest.raises(ValueError):
            ModelRouterConfig(latency_window_size=0)
