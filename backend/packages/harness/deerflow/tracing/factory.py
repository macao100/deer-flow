from __future__ import annotations

import threading
from typing import Any

from deerflow.config import (
    get_enabled_tracing_providers,
    get_tracing_config,
    validate_enabled_tracing_providers,
)

# ── Module-level singletons (lazy-initialised) ────────────────────────
_metrics_collector: Any = None
_collector_lock = threading.Lock()


def _observability_enabled() -> bool:
    """Return True when the observability subsystem is enabled in config."""
    try:
        from deerflow.config.app_config import get_app_config

        return get_app_config().observability.enabled
    except Exception:
        return False


def _get_or_create_metrics_collector() -> Any:
    """Return the process-wide MetricsCollector singleton, creating it on first call."""
    global _metrics_collector
    if _metrics_collector is not None:
        return _metrics_collector
    with _collector_lock:
        if _metrics_collector is not None:
            return _metrics_collector
        from deerflow.config.app_config import get_app_config
        from deerflow.tracing.observability.metrics_collector import MetricsCollector

        config = get_app_config().observability.metrics
        _metrics_collector = MetricsCollector(buffer_size=config.buffer_size)
        return _metrics_collector


def get_metrics_collector() -> Any | None:
    """Return the process-wide MetricsCollector singleton, or None if disabled."""
    if not _observability_enabled():
        return None
    return _get_or_create_metrics_collector()


def _create_langsmith_tracer(config) -> Any:
    from langchain_core.tracers.langchain import LangChainTracer

    return LangChainTracer(project_name=config.project)


def _create_langfuse_handler(config) -> Any:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

    # langfuse>=4 initializes project-specific credentials through the client
    # singleton; the LangChain callback then attaches to that configured client.
    Langfuse(
        secret_key=config.secret_key,
        public_key=config.public_key,
        host=config.host,
    )
    return LangfuseCallbackHandler(public_key=config.public_key)


def build_tracing_callbacks() -> list[Any]:
    """Build callbacks for all explicitly enabled tracing providers.

    When ``observability.enabled`` is true in ``config.yaml``, an
    ``ObservabilityCallbacks`` handler is appended so that metrics
    (latency, tokens, tool errors) are collected for every run.
    """
    validate_enabled_tracing_providers()
    enabled_providers = get_enabled_tracing_providers()
    tracing_config = get_tracing_config()
    callbacks: list[Any] = []

    # ── Third-party tracing providers ──────────────────────────────────
    for provider in enabled_providers:
        if provider == "langsmith":
            try:
                callbacks.append(_create_langsmith_tracer(tracing_config.langsmith))
            except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
                raise RuntimeError(f"LangSmith tracing initialization failed: {exc}") from exc
        elif provider == "langfuse":
            try:
                callbacks.append(_create_langfuse_handler(tracing_config.langfuse))
            except Exception as exc:  # pragma: no cover - exercised via tests with monkeypatch
                raise RuntimeError(f"Langfuse tracing initialization failed: {exc}") from exc

    # ── DeerFlow observability (always appended when enabled) ──────────
    if _observability_enabled():
        from deerflow.tracing.observability import ObservabilityCallbacks

        collector = _get_or_create_metrics_collector()
        callbacks.append(ObservabilityCallbacks(metrics=collector))

    return callbacks
