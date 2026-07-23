"""Tests for observability integration in tracing factory."""

from __future__ import annotations

import pytest

from deerflow.tracing import factory as tracing_factory


@pytest.fixture(autouse=True)
def clear_tracing_env(monkeypatch):
    from deerflow.config.tracing_config import reset_tracing_config

    for name in (
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_TRACING",
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_PROJECT",
        "LANGCHAIN_PROJECT",
        "LANGSMITH_ENDPOINT",
        "LANGCHAIN_ENDPOINT",
        "LANGFUSE_TRACING",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    reset_tracing_config()
    yield
    reset_tracing_config()


class TestObservabilityFactoryIntegration:
    def test_callbacks_include_observability_when_enabled(self, monkeypatch):
        """When observability.enabled=True, ObservabilityCallbacks is appended."""
        monkeypatch.setattr(tracing_factory, "validate_enabled_tracing_providers", lambda: None)
        monkeypatch.setattr(tracing_factory, "get_enabled_tracing_providers", lambda: [])

        # Mock get_app_config to return observability.enabled=True
        class FakeMetricsConfig:
            buffer_size = 1000

        class FakeObsConfig:
            enabled = True
            metrics = FakeMetricsConfig()

        class FakeAppConfig:
            observability = FakeObsConfig()

        monkeypatch.setattr(tracing_factory, "_observability_enabled", lambda: True)
        # Inject a fake collector so we don't create a real one
        fake_collector = object()
        monkeypatch.setattr(tracing_factory, "_get_or_create_metrics_collector", lambda: fake_collector)

        callbacks = tracing_factory.build_tracing_callbacks()
        assert len(callbacks) == 1  # ObservabilityCallbacks
        from deerflow.tracing.observability.callbacks import ObservabilityCallbacks

        assert isinstance(callbacks[0], ObservabilityCallbacks)

    def test_callbacks_exclude_observability_when_disabled(self, monkeypatch):
        """When observability.enabled=False, no ObservabilityCallbacks."""
        monkeypatch.setattr(tracing_factory, "validate_enabled_tracing_providers", lambda: None)
        monkeypatch.setattr(tracing_factory, "get_enabled_tracing_providers", lambda: [])
        monkeypatch.setattr(tracing_factory, "_observability_enabled", lambda: False)

        callbacks = tracing_factory.build_tracing_callbacks()
        assert len(callbacks) == 0

    def test_get_metrics_collector_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr(tracing_factory, "_observability_enabled", lambda: False)
        assert tracing_factory.get_metrics_collector() is None

    def test_get_metrics_collector_returns_singleton(self, monkeypatch):
        monkeypatch.setattr(tracing_factory, "_observability_enabled", lambda: True)
        fake_collector = object()
        monkeypatch.setattr(tracing_factory, "_get_or_create_metrics_collector", lambda: fake_collector)
        c1 = tracing_factory.get_metrics_collector()
        c2 = tracing_factory.get_metrics_collector()
        assert c1 is c2
        assert c1 is fake_collector
