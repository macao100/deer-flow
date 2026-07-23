"""Configurable alert manager for agent observability.

Evaluates aggregated metrics against thresholds and dispatches alerts
through registered hooks. Rate-limited to prevent alert storms.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .metrics_collector import MetricsSummary

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Alert:
    """A single alert emitted when a threshold is exceeded."""

    name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: float


class AlertHook(Protocol):
    """Protocol for alert hook callbacks.

    Hooks receive every alert that passes rate-limiting. Implementations
    should be non-blocking (e.g. enqueue to a background sender).
    """

    def __call__(self, alert: Alert) -> None: ...


@dataclass
class AlertConfig:
    """Thresholds and behaviour for the alert manager."""

    latence_max_ms: float = 5000.0
    error_rate_max: float = 0.05
    token_budget_warn: int = 4000
    rate_limit_seconds: int = 300


class AlertManager:
    """Evaluates metrics against thresholds and dispatches alerts via hooks.

    Thread-safe. Designed to be called from the background export thread,
    not from LangChain callback threads.
    """

    def __init__(self, config: AlertConfig | None = None) -> None:
        self._config = config or AlertConfig()
        self._lock = threading.RLock()
        self._hooks: dict[str, AlertHook] = {}
        self._last_emitted: dict[str, float] = {}
        self._recent_alerts: list[Alert] = []  # capped at 100

        # Default: log warning for every alert
        self.register_hook("log", _log_alert_hook)

    @property
    def config(self) -> AlertConfig:
        return self._config

    # ── Hook management ───────────────────────────────────────────────

    def register_hook(self, name: str, hook: AlertHook) -> None:
        """Register an alert hook. Replaces any existing hook with the same name."""
        with self._lock:
            self._hooks[name] = hook

    def unregister_hook(self, name: str) -> None:
        """Remove a previously registered hook."""
        with self._lock:
            self._hooks.pop(name, None)

    # ── Evaluation ─────────────────────────────────────────────────────

    def evaluate(self, summary: MetricsSummary) -> list[Alert]:
        """Evaluate a metrics summary and return alerts for exceeded thresholds.

        Rate-limiting is enforced: an alert with the same name will not fire
        again within ``rate_limit_seconds``.
        """
        now = time.monotonic()
        alerts: list[Alert] = []

        # 1. Latency alert (P95 per node)
        for node_name, percentiles in summary.latency.items():
            if percentiles.count < 2:
                continue  # need at least 2 data points for meaningful P95
            if percentiles.p95 > self._config.latence_max_ms:
                alert = Alert(
                    name=f"latency_high:{node_name}",
                    severity=AlertSeverity.WARNING,
                    message=f"Node '{node_name}' P95 latency {percentiles.p95:.0f}ms exceeds {self._config.latence_max_ms}ms threshold",
                    value=percentiles.p95,
                    threshold=self._config.latence_max_ms,
                    timestamp=now,
                )
                if self._check_rate_limit(alert.name, now):
                    alerts.append(alert)

        # 2. Error rate alert (tool calls)
        for tool_name, stats in summary.tool_calls.items():
            if stats.total < 3:
                continue
            error_rate = 1.0 - stats.success_rate
            if error_rate > self._config.error_rate_max:
                alert = Alert(
                    name=f"error_rate:{tool_name}",
                    severity=AlertSeverity.CRITICAL if error_rate > 0.25 else AlertSeverity.WARNING,
                    message=f"Tool '{tool_name}' error rate {error_rate:.1%} exceeds {self._config.error_rate_max:.1%} threshold ({stats.failure}/{stats.total})",
                    value=error_rate,
                    threshold=self._config.error_rate_max,
                    timestamp=now,
                )
                if self._check_rate_limit(alert.name, now):
                    alerts.append(alert)

        # 3. Token budget warning (per model, average input tokens)
        for model_name, stats in summary.tokens.items():
            if stats.call_count < 2:
                continue
            avg_input = stats.total_input_tokens / stats.call_count
            if avg_input > self._config.token_budget_warn:
                alert = Alert(
                    name=f"token_budget:{model_name}",
                    severity=AlertSeverity.WARNING,
                    message=f"Model '{model_name}' avg input tokens {avg_input:.0f} exceeds {self._config.token_budget_warn} budget (over {stats.call_count} calls)",
                    value=avg_input,
                    threshold=self._config.token_budget_warn,
                    timestamp=now,
                )
                if self._check_rate_limit(alert.name, now):
                    alerts.append(alert)

        # Dispatch through hooks
        for alert in alerts:
            self._dispatch(alert)

        return alerts

    def _check_rate_limit(self, name: str, now: float) -> bool:
        """Return True if the alert should fire (not rate-limited)."""
        with self._lock:
            last = self._last_emitted.get(name)
            if last is not None and (now - last) < self._config.rate_limit_seconds:
                return False
            self._last_emitted[name] = now
            return True

    def _dispatch(self, alert: Alert) -> None:
        """Send an alert through all registered hooks. Errors are logged, never raised."""
        with self._lock:
            hooks = list(self._hooks.values())
            self._recent_alerts.append(alert)
            if len(self._recent_alerts) > 100:
                self._recent_alerts = self._recent_alerts[-100:]

        for hook in hooks:
            try:
                hook(alert)
            except Exception:
                logger.exception("Alert hook failed for alert %s", alert.name)

    def recent_alerts(self) -> list[Alert]:
        """Return recent alerts for the history endpoint."""
        with self._lock:
            return list(self._recent_alerts)


def _log_alert_hook(alert: Alert) -> None:
    """Default hook: log the alert at the appropriate level."""
    msg = f"[{alert.severity.value.upper()}] {alert.message}"
    if alert.severity == AlertSeverity.CRITICAL:
        logger.error(msg)
    else:
        logger.warning(msg)
