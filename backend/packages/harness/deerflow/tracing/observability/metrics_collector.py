"""Thread-safe metrics collector for LangGraph agent observability.

Collects latency, token usage, and tool call results in a ring buffer.
Non-blocking on the critical path — all I/O is deferred to the drain cycle.
"""

from __future__ import annotations

import statistics
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NodeLatency:
    """Latency measurement for a single graph node or chain execution."""

    node_name: str
    agent_name: str
    start_time: float
    end_time: float
    duration_ms: float


@dataclass(frozen=True)
class TokenUsage:
    """Token consumption for a single LLM call."""

    model_name: str
    input_tokens: int
    output_tokens: int
    timestamp: float


@dataclass(frozen=True)
class ToolCallResult:
    """Outcome of a single tool invocation."""

    tool_name: str
    success: bool
    duration_ms: float
    error: str | None = None


@dataclass
class Percentiles:
    """Aggregated latency statistics for a group of measurements."""

    avg: float
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    count: int


@dataclass
class TokenStats:
    """Aggregated token statistics per model."""

    total_input_tokens: int
    total_output_tokens: int
    call_count: int


@dataclass
class ToolStats:
    """Aggregated tool call statistics."""

    total: int
    success: int
    failure: int
    success_rate: float
    avg_duration_ms: float


@dataclass
class MetricsSummary:
    """Snapshot of aggregated metrics computed from the current buffer."""

    latency: dict[str, Percentiles]  # key = node_name
    tokens: dict[str, TokenStats]  # key = model_name
    tool_calls: dict[str, ToolStats]  # key = tool_name
    window_seconds: float
    total_events: int


def _compute_percentiles(durations_ms: list[float]) -> Percentiles:
    """Compute aggregate statistics from a list of duration values."""
    if not durations_ms:
        return Percentiles(avg=0.0, p50=0.0, p95=0.0, p99=0.0, min=0.0, max=0.0, count=0)
    sorted_durations = sorted(durations_ms)
    n = len(sorted_durations)
    return Percentiles(
        avg=statistics.mean(sorted_durations),
        p50=_percentile(sorted_durations, 0.50),
        p95=_percentile(sorted_durations, 0.95),
        p99=_percentile(sorted_durations, 0.99),
        min=sorted_durations[0],
        max=sorted_durations[-1],
        count=n,
    )


def _percentile(sorted_values: list[float], q: float) -> float:
    """Compute the q-th percentile from a sorted list (linear interpolation)."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    idx = q * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


class MetricsCollector:
    """Thread-safe ring buffer for agent observability events.

    Events are appended from LangChain callback threads (non-blocking,
    O(1)). A background thread periodically drains the buffer for export
    and alert evaluation.
    """

    def __init__(self, buffer_size: int = 10000) -> None:
        self._buffer_size = buffer_size
        self._lock = threading.RLock()
        self._latencies: deque[NodeLatency] = deque(maxlen=buffer_size)
        self._tokens: deque[TokenUsage] = deque(maxlen=buffer_size)
        self._tool_calls: deque[ToolCallResult] = deque(maxlen=buffer_size)
        self._started_at: float = time.monotonic()

    # ── Append (called from callback threads) ──────────────────────────

    def record_latency(self, event: NodeLatency) -> None:
        """Record a node latency event. Non-blocking, O(1)."""
        with self._lock:
            self._latencies.append(event)

    def record_tokens(self, event: TokenUsage) -> None:
        """Record a token usage event. Non-blocking, O(1)."""
        with self._lock:
            self._tokens.append(event)

    def record_tool_call(self, event: ToolCallResult) -> None:
        """Record a tool call result. Non-blocking, O(1)."""
        with self._lock:
            self._tool_calls.append(event)

    # ── Snapshot (called from API handler) ─────────────────────────────

    def get_summary(self) -> MetricsSummary:
        """Compute aggregated metrics from current buffer without draining."""
        with self._lock:
            latencies = list(self._latencies)
            tokens = list(self._tokens)
            tool_calls = list(self._tool_calls)
            total_events = len(latencies) + len(tokens) + len(tool_calls)
            window_seconds = time.monotonic() - self._started_at

        # Aggregate latencies by node_name
        latency_by_node: dict[str, list[float]] = {}
        for event in latencies:
            latency_by_node.setdefault(event.node_name, []).append(event.duration_ms)
        latency_agg = {node: _compute_percentiles(durations) for node, durations in latency_by_node.items()}

        # Aggregate tokens by model_name
        tokens_by_model: dict[str, TokenStats] = {}
        for event in tokens:
            if event.model_name not in tokens_by_model:
                tokens_by_model[event.model_name] = TokenStats(total_input_tokens=0, total_output_tokens=0, call_count=0)
            stats = tokens_by_model[event.model_name]
            stats.total_input_tokens += event.input_tokens
            stats.total_output_tokens += event.output_tokens
            stats.call_count += 1

        # Aggregate tool calls by tool_name
        tool_by_name: dict[str, dict[str, Any]] = {}
        for event in tool_calls:
            if event.tool_name not in tool_by_name:
                tool_by_name[event.tool_name] = {"total": 0, "success": 0, "failure": 0, "durations": []}
            entry = tool_by_name[event.tool_name]
            entry["total"] += 1
            if event.success:
                entry["success"] += 1
            else:
                entry["failure"] += 1
            entry["durations"].append(event.duration_ms)
        tool_agg: dict[str, ToolStats] = {}
        for name, data in tool_by_name.items():
            total = data["total"]
            durations: list[float] = data["durations"]
            tool_agg[name] = ToolStats(
                total=total,
                success=data["success"],
                failure=data["failure"],
                success_rate=data["success"] / total if total > 0 else 0.0,
                avg_duration_ms=statistics.mean(durations) if durations else 0.0,
            )

        return MetricsSummary(
            latency=latency_agg,
            tokens=tokens_by_model,
            tool_calls=tool_agg,
            window_seconds=window_seconds,
            total_events=total_events,
        )

    # ── Drain (called from background export thread) ──────────────────

    def drain(self) -> tuple[list[NodeLatency], list[TokenUsage], list[ToolCallResult]]:
        """Drain all buffered events and return them, resetting the buffer."""
        with self._lock:
            latencies = list(self._latencies)
            tokens = list(self._tokens)
            tool_calls = list(self._tool_calls)
            self._latencies.clear()
            self._tokens.clear()
            self._tool_calls.clear()
        return latencies, tokens, tool_calls
