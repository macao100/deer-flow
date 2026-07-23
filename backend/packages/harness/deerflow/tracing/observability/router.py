"""FastAPI router for observability endpoints.

Serves ``GET /api/observability/metrics/summary`` (aggregated metrics)
and ``GET /api/observability/alerts/history`` (recent alerts).

Mounted by the Gateway application when observability is enabled.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

if TYPE_CHECKING:
    from .alert_manager import AlertManager
    from .exporter import MetricsExporter
    from .metrics_collector import MetricsCollector

_router: APIRouter | None = None


def get_observability_router(
    metrics_collector: MetricsCollector,
    alert_manager: AlertManager | None = None,
    metrics_exporter: MetricsExporter | None = None,
) -> APIRouter:
    """Build a FastAPI router with observability endpoints.

    Args:
        metrics_collector: The collector to query for summary data.
        alert_manager: Optional alert manager for alert history.
        metrics_exporter: Optional exporter (used for Prometheus format).

    Returns:
        A FastAPI APIRouter ready for ``app.include_router()``.
    """
    global _router

    router = APIRouter(prefix="/api/observability", tags=["observability"])

    @router.get("/metrics/summary")
    async def metrics_summary():
        """Return aggregated metrics (avg, P50, P95, P99) from the current buffer."""
        summary = metrics_collector.get_summary()
        return {
            "latency": {
                node: {
                    "avg_ms": round(p.avg, 2),
                    "p50_ms": round(p.p50, 2),
                    "p95_ms": round(p.p95, 2),
                    "p99_ms": round(p.p99, 2),
                    "min_ms": round(p.min, 2),
                    "max_ms": round(p.max, 2),
                    "count": p.count,
                }
                for node, p in summary.latency.items()
            },
            "tokens": {
                model: {
                    "total_input_tokens": stats.total_input_tokens,
                    "total_output_tokens": stats.total_output_tokens,
                    "call_count": stats.call_count,
                }
                for model, stats in summary.tokens.items()
            },
            "tool_calls": {
                tool: {
                    "total": stats.total,
                    "success": stats.success,
                    "failure": stats.failure,
                    "success_rate": round(stats.success_rate, 4),
                    "avg_duration_ms": round(stats.avg_duration_ms, 2),
                }
                for tool, stats in summary.tool_calls.items()
            },
            "window_seconds": round(summary.window_seconds, 1),
            "total_events": summary.total_events,
        }

    @router.get("/metrics")
    async def prometheus_metrics():
        """Return metrics in Prometheus text format (Content-Type: text/plain)."""
        from fastapi.responses import PlainTextResponse

        if metrics_exporter is not None:
            text = metrics_exporter.prometheus_text()
        else:
            text = "# DeerFlow metrics exporter not configured\n"
        return PlainTextResponse(content=text, media_type="text/plain; version=0.0.4; charset=utf-8")

    @router.get("/alerts/history")
    async def alerts_history():
        """Return recent alerts fired by the alert manager."""
        if alert_manager is None:
            return {"alerts": []}
        alerts = alert_manager.recent_alerts()
        return {
            "alerts": [
                {
                    "name": a.name,
                    "severity": a.severity.value,
                    "message": a.message,
                    "value": a.value,
                    "threshold": a.threshold,
                    "timestamp": a.timestamp,
                }
                for a in alerts
            ]
        }

    @router.get("/health")
    async def observability_health():
        """Health check for the observability subsystem."""
        summary = metrics_collector.get_summary()
        return {
            "status": "ok",
            "buffer_total_events": summary.total_events,
            "window_seconds": round(summary.window_seconds, 1),
        }

    _router = router
    return router
