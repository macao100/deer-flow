"""Tests for deerflow.tracing.observability.alert_manager."""

from __future__ import annotations

import time

import pytest

from deerflow.tracing.observability.alert_manager import (
    Alert,
    AlertConfig,
    AlertManager,
    AlertSeverity,
)
from deerflow.tracing.observability.metrics_collector import (
    MetricsCollector,
    MetricsSummary,
    NodeLatency,
    Percentiles,
    TokenStats,
    TokenUsage,
    ToolCallResult,
    ToolStats,
)


def _make_summary(*, latencies: dict | None = None, tokens: dict | None = None, tool_calls: dict | None = None) -> MetricsSummary:
    return MetricsSummary(
        latency=latencies or {},
        tokens=tokens or {},
        tool_calls=tool_calls or {},
        window_seconds=60.0,
        total_events=10,
    )


class TestAlertManagerEvaluate:
    def test_no_alerts_when_under_threshold(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=5000.0))
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=100.0, p50=100.0, p95=200.0, p99=300.0, min=50.0, max=350.0, count=10)
            }
        )
        alerts = mgr.evaluate(summary)
        assert len(alerts) == 0

    def test_latency_alert_when_p95_exceeds(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=100.0))
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=200.0, p50=200.0, p95=250.0, p99=300.0, min=100.0, max=350.0, count=10)
            }
        )
        alerts = mgr.evaluate(summary)
        assert len(alerts) == 1
        assert alerts[0].name == "latency_high:agent"
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].value == 250.0

    def test_latency_alert_requires_min_samples(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=10.0))
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=1)
            }
        )
        alerts = mgr.evaluate(summary)
        # Need at least 2 data points
        assert len(alerts) == 0

    def test_error_rate_alert(self):
        mgr = AlertManager(AlertConfig(error_rate_max=0.05))
        summary = _make_summary(
            tool_calls={
                "bash": ToolStats(total=10, success=5, failure=5, success_rate=0.5, avg_duration_ms=100.0)
            }
        )
        alerts = mgr.evaluate(summary)
        assert len(alerts) == 1
        assert alerts[0].name == "error_rate:bash"
        assert alerts[0].severity == AlertSeverity.CRITICAL  # > 25%
        assert alerts[0].value == 0.5

    def test_error_rate_requires_min_samples(self):
        mgr = AlertManager(AlertConfig(error_rate_max=0.01))
        summary = _make_summary(
            tool_calls={
                "bash": ToolStats(total=1, success=0, failure=1, success_rate=0.0, avg_duration_ms=100.0)
            }
        )
        alerts = mgr.evaluate(summary)
        # Need at least 3 calls
        assert len(alerts) == 0

    def test_token_budget_alert(self):
        mgr = AlertManager(AlertConfig(token_budget_warn=100))
        summary = _make_summary(
            tokens={
                "gpt-4": TokenStats(total_input_tokens=600, total_output_tokens=300, call_count=3)
            }
        )
        alerts = mgr.evaluate(summary)
        assert len(alerts) == 1
        assert alerts[0].name == "token_budget:gpt-4"
        assert alerts[0].value == 200.0  # avg input = 600/3


class TestAlertManagerRateLimiting:
    def test_rate_limit_prevents_duplicate(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=10.0, rate_limit_seconds=300))
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=10)
            }
        )
        alerts_1 = mgr.evaluate(summary)
        alerts_2 = mgr.evaluate(summary)
        assert len(alerts_1) == 1
        assert len(alerts_2) == 0  # rate-limited

    def test_rate_limit_allows_after_cooldown(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=10.0, rate_limit_seconds=0))
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=10)
            }
        )
        alerts_1 = mgr.evaluate(summary)
        alerts_2 = mgr.evaluate(summary)
        assert len(alerts_1) == 1
        assert len(alerts_2) == 1  # rate_limit=0, always fires


class TestAlertManagerHooks:
    def test_hook_registration_and_firing(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=10.0))
        received: list[Alert] = []

        def my_hook(alert: Alert) -> None:
            received.append(alert)

        mgr.register_hook("custom", my_hook)
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=10)
            }
        )
        mgr.evaluate(summary)
        assert len(received) == 1
        assert received[0].name == "latency_high:agent"

    def test_default_log_hook_present(self):
        mgr = AlertManager()
        # The default "log" hook should exist
        recent = mgr.recent_alerts()
        assert recent == []

    def test_unregister_hook(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=10.0, rate_limit_seconds=0))
        received: list[Alert] = []

        def my_hook(alert: Alert) -> None:
            received.append(alert)

        mgr.register_hook("custom", my_hook)
        mgr.unregister_hook("custom")
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=10)
            }
        )
        mgr.evaluate(summary)
        # Unregistered hook should not be called, but default "log" hook still fires
        assert len(received) == 0

    def test_hook_error_does_not_propagate(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=10.0, rate_limit_seconds=0))

        def bad_hook(_alert: Alert) -> None:
            raise RuntimeError("hook exploded")

        mgr.register_hook("bad", bad_hook)
        summary = _make_summary(
            latencies={
                "agent": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=10)
            }
        )
        # Should not raise
        alerts = mgr.evaluate(summary)
        assert len(alerts) == 1  # alert still emitted despite hook error

    def test_recent_alerts_capped(self):
        mgr = AlertManager(AlertConfig(latence_max_ms=1.0, rate_limit_seconds=0))
        for i in range(150):
            summary = _make_summary(
                latencies={
                    f"node_{i}": Percentiles(avg=500.0, p50=500.0, p95=500.0, p99=500.0, min=500.0, max=500.0, count=10)
                }
            )
            mgr.evaluate(summary)
        recent = mgr.recent_alerts()
        assert len(recent) == 100  # capped
