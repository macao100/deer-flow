"""Metrics exporter: Prometheus text format + daily JSON rotation.

Runs a lightweight HTTP server for Prometheus scraping and a background
thread for periodic JSON export with automatic rotation/cleanup.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .metrics_collector import MetricsCollector, MetricsSummary

logger = logging.getLogger(__name__)


def _default_export_path() -> Path:
    """Return the default metrics export directory for the current OS."""
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "DeerFlow" / "metrics"
    return Path("/var/log/deerflow/metrics")


class MetricsExporter:
    """Exports metrics to Prometheus format and daily JSON files.

    The Prometheus text format is generated manually — no dependency on
    ``prometheus_client``. A lightweight ``http.server.HTTPServer`` serves
    ``GET /metrics`` on the configured port.
    """

    def __init__(
        self,
        metrics: MetricsCollector,
        *,
        export_path: str | None = None,
        rotation_days: int = 30,
        prometheus_port: int = 9090,
    ) -> None:
        self._metrics = metrics
        self._export_path = Path(export_path) if export_path else _default_export_path()
        self._rotation_days = rotation_days
        self._prometheus_port = prometheus_port
        self._lock = threading.RLock()
        self._latest_summary: MetricsSummary | None = None
        self._prometheus_server: Any = None

    # ── Prometheus text format ─────────────────────────────────────────

    def prometheus_text(self) -> str:
        """Return metrics in Prometheus text exposition format."""
        summary = self._metrics.get_summary()
        with self._lock:
            self._latest_summary = summary

        lines: list[str] = []

        # Latency gauges per node
        for node_name, p in summary.latency.items():
            lines.append(f"# HELP deerflow_node_latency_ms Latency for node '{node_name}' in milliseconds")
            lines.append("# TYPE deerflow_node_latency_ms gauge")
            lines.append(f'deerflow_node_latency_ms{{node="{node_name}",quantile="0.5"}} {p.p50:.2f}')
            lines.append(f'deerflow_node_latency_ms{{node="{node_name}",quantile="0.95"}} {p.p95:.2f}')
            lines.append(f'deerflow_node_latency_ms{{node="{node_name}",quantile="0.99"}} {p.p99:.2f}')
            lines.append(f'deerflow_node_latency_ms{{node="{node_name}",quantile="avg"}} {p.avg:.2f}')
            lines.append(f'deerflow_node_latency_ms{{node="{node_name}",quantile="min"}} {p.min:.2f}')
            lines.append(f'deerflow_node_latency_ms{{node="{node_name}",quantile="max"}} {p.max:.2f}')
            lines.append(f"# HELP deerflow_node_latency_count Number of latency samples for node '{node_name}'")
            lines.append("# TYPE deerflow_node_latency_count gauge")
            lines.append(f'deerflow_node_latency_count{{node="{node_name}"}} {p.count}')

        # Token counters per model
        lines.append("# HELP deerflow_token_input_total Total input tokens by model")
        lines.append("# TYPE deerflow_token_input_total counter")
        lines.append("# HELP deerflow_token_output_total Total output tokens by model")
        lines.append("# TYPE deerflow_token_output_total counter")
        lines.append("# HELP deerflow_token_calls_total Total LLM calls by model")
        lines.append("# TYPE deerflow_token_calls_total counter")
        for model_name, stats in summary.tokens.items():
            lines.append(f'deerflow_token_input_total{{model="{model_name}"}} {stats.total_input_tokens}')
            lines.append(f'deerflow_token_output_total{{model="{model_name}"}} {stats.total_output_tokens}')
            lines.append(f'deerflow_token_calls_total{{model="{model_name}"}} {stats.call_count}')

        # Tool call counters
        lines.append("# HELP deerflow_tool_calls_total Total tool calls by name")
        lines.append("# TYPE deerflow_tool_calls_total counter")
        lines.append("# HELP deerflow_tool_errors_total Total tool errors by name")
        lines.append("# TYPE deerflow_tool_errors_total counter")
        lines.append("# HELP deerflow_tool_success_rate Success rate by tool name")
        lines.append("# TYPE deerflow_tool_success_rate gauge")
        for tool_name, stats in summary.tool_calls.items():
            lines.append(f'deerflow_tool_calls_total{{tool="{tool_name}"}} {stats.total}')
            lines.append(f'deerflow_tool_errors_total{{tool="{tool_name}"}} {stats.failure}')
            lines.append(f'deerflow_tool_success_rate{{tool="{tool_name}"}} {stats.success_rate:.4f}')

        # Window metadata
        lines.append("# HELP deerflow_metrics_window_seconds Age of oldest event in buffer")
        lines.append("# TYPE deerflow_metrics_window_seconds gauge")
        lines.append(f"deerflow_metrics_window_seconds {summary.window_seconds:.1f}")
        lines.append("# HELP deerflow_metrics_total_events Total events in current buffer")
        lines.append("# TYPE deerflow_metrics_total_events gauge")
        lines.append(f"deerflow_metrics_total_events {summary.total_events}")

        return "\n".join(lines) + "\n"

    # ── Prometheus HTTP server ─────────────────────────────────────────

    def start_prometheus_server(self) -> None:
        """Start a lightweight HTTP server for Prometheus scraping in a daemon thread."""
        if self._prometheus_server is not None:
            return

        exporter = self

        class _MetricsHandler:
            def do_GET(self):
                if self.path == "/metrics":
                    try:
                        body = exporter.prometheus_text().encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    except Exception:
                        logger.exception("Prometheus /metrics handler failed")
                        self.send_response(500)
                        self.end_headers()
                elif self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"ok")
                else:
                    self.send_response(404)
                    self.end_headers()

        def _run_server() -> None:
            try:
                from http.server import HTTPServer

                server = HTTPServer(("0.0.0.0", self._prometheus_port), _MetricsHandler)
                self._prometheus_server = server
                logger.info("Prometheus metrics server listening on port %s", self._prometheus_port)
                server.serve_forever()
            except Exception:
                logger.exception("Prometheus server failed to start on port %s", self._prometheus_port)

        thread = threading.Thread(target=_run_server, name="deerflow-prometheus", daemon=True)
        thread.start()

    # ── JSON daily export ──────────────────────────────────────────────

    def start_rotation_loop(self, interval_seconds: float = 60.0) -> None:
        """Start a background daemon thread that drains and exports metrics periodically."""

        def _loop() -> None:
            self._export_path.mkdir(parents=True, exist_ok=True)
            while True:
                try:
                    time.sleep(interval_seconds)
                    self._rotate()
                except Exception:
                    logger.exception("Metrics rotation failed")

        thread = threading.Thread(target=_loop, name="deerflow-metrics-export", daemon=True)
        thread.start()
        logger.info("Metrics rotation loop started (interval=%ss, path=%s)", interval_seconds, self._export_path)

    def _rotate(self) -> None:
        """Drain the collector, write a daily JSONL append, clean up old files."""
        latencies, tokens, tool_calls = self._metrics.drain()
        if not latencies and not tokens and not tool_calls:
            return

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = self._export_path / f"{today}.jsonl"

        snapshot: dict = {
            "ts": datetime.now(UTC).isoformat(),
            "type": "snapshot",
            "data": {
                "latencies": [
                    {
                        "node_name": e.node_name,
                        "agent_name": e.agent_name,
                        "duration_ms": round(e.duration_ms, 2),
                    }
                    for e in latencies
                ],
                "tokens": [
                    {
                        "model_name": e.model_name,
                        "input_tokens": e.input_tokens,
                        "output_tokens": e.output_tokens,
                    }
                    for e in tokens
                ],
                "tool_calls": [
                    {
                        "tool_name": e.tool_name,
                        "success": e.success,
                        "duration_ms": round(e.duration_ms, 2),
                        "error": e.error,
                    }
                    for e in tool_calls
                ],
            },
        }

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to write metrics snapshot to %s", file_path)

        # Clean up files older than rotation_days
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove metrics files older than ``rotation_days``."""
        cutoff = time.time() - (self._rotation_days * 86400)
        try:
            for entry in self._export_path.iterdir():
                if entry.suffix != ".jsonl":
                    continue
                try:
                    if entry.stat().st_mtime < cutoff:
                        entry.unlink()
                        logger.debug("Removed expired metrics file: %s", entry.name)
                except OSError:
                    logger.debug("Failed to remove metrics file: %s", entry.name, exc_info=True)
        except Exception:
            logger.debug("Metrics cleanup skipped", exc_info=True)
