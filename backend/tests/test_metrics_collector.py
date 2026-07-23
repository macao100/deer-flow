"""Tests for deerflow.tracing.observability.metrics_collector."""

from __future__ import annotations

import threading
import time

import pytest

from deerflow.tracing.observability.metrics_collector import (
    MetricsCollector,
    NodeLatency,
    TokenUsage,
    ToolCallResult,
)


class TestMetricsCollectorAppend:
    def test_append_latency(self):
        collector = MetricsCollector(buffer_size=100)
        event = NodeLatency(
            node_name="agent",
            agent_name="lead-agent",
            start_time=100.0,
            end_time=101.5,
            duration_ms=1500.0,
        )
        collector.record_latency(event)
        summary = collector.get_summary()
        assert summary.total_events == 1
        assert "agent" in summary.latency
        assert summary.latency["agent"].count == 1
        assert summary.latency["agent"].avg == 1500.0

    def test_append_tokens(self):
        collector = MetricsCollector(buffer_size=100)
        collector.record_tokens(TokenUsage(model_name="gpt-4", input_tokens=500, output_tokens=200, timestamp=time.monotonic()))
        collector.record_tokens(TokenUsage(model_name="gpt-4", input_tokens=300, output_tokens=100, timestamp=time.monotonic()))
        summary = collector.get_summary()
        assert "gpt-4" in summary.tokens
        assert summary.tokens["gpt-4"].total_input_tokens == 800
        assert summary.tokens["gpt-4"].total_output_tokens == 300
        assert summary.tokens["gpt-4"].call_count == 2

    def test_append_tool_call_success(self):
        collector = MetricsCollector(buffer_size=100)
        collector.record_tool_call(ToolCallResult(tool_name="bash", success=True, duration_ms=42.0))
        summary = collector.get_summary()
        assert "bash" in summary.tool_calls
        assert summary.tool_calls["bash"].total == 1
        assert summary.tool_calls["bash"].success == 1
        assert summary.tool_calls["bash"].failure == 0
        assert summary.tool_calls["bash"].success_rate == 1.0

    def test_append_tool_call_failure(self):
        collector = MetricsCollector(buffer_size=100)
        collector.record_tool_call(ToolCallResult(tool_name="bash", success=False, duration_ms=100.0, error="command not found"))
        summary = collector.get_summary()
        assert summary.tool_calls["bash"].success_rate == 0.0
        assert summary.tool_calls["bash"].failure == 1


class TestMetricsCollectorSummary:
    def test_empty_summary(self):
        collector = MetricsCollector()
        summary = collector.get_summary()
        assert summary.total_events == 0
        assert summary.latency == {}
        assert summary.tokens == {}
        assert summary.tool_calls == {}

    def test_percentiles(self):
        collector = MetricsCollector(buffer_size=100)
        for ms in [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]:
            collector.record_latency(NodeLatency(node_name="agent", agent_name="test", start_time=0, end_time=ms / 1000, duration_ms=ms))
        summary = collector.get_summary()
        p = summary.latency["agent"]
        assert p.count == 10
        assert p.avg == 55.0
        assert p.p50 == 55.0  # median of 10 sorted values
        assert p.min == 10.0
        assert p.max == 100.0
        # P95 and P99 should be in valid range
        assert 80.0 <= p.p95 <= 100.0
        assert 90.0 <= p.p99 <= 100.0

    def test_single_value_percentiles(self):
        collector = MetricsCollector()
        collector.record_latency(NodeLatency(node_name="solo", agent_name="test", start_time=0, end_time=0.1, duration_ms=42.0))
        summary = collector.get_summary()
        p = summary.latency["solo"]
        assert p.avg == 42.0
        assert p.p50 == 42.0
        assert p.p95 == 42.0
        assert p.p99 == 42.0
        assert p.min == 42.0
        assert p.max == 42.0

    def test_window_seconds(self):
        collector = MetricsCollector()
        summary = collector.get_summary()
        # Window seconds is always non-negative
        assert summary.window_seconds >= 0.0

    def test_window_seconds_increases_with_events(self):
        collector = MetricsCollector()
        initial = collector.get_summary().window_seconds
        time.sleep(0.02)
        collector.record_latency(NodeLatency(node_name="a", agent_name="t", start_time=0, end_time=1, duration_ms=1000.0))
        later = collector.get_summary().window_seconds
        assert later >= initial


class TestMetricsCollectorDrain:
    def test_drain_empties_buffer(self):
        collector = MetricsCollector(buffer_size=100)
        collector.record_latency(NodeLatency(node_name="agent", agent_name="test", start_time=0, end_time=1, duration_ms=1000.0))
        collector.record_tokens(TokenUsage(model_name="gpt-4", input_tokens=10, output_tokens=5, timestamp=time.monotonic()))

        latencies, tokens, tool_calls = collector.drain()
        assert len(latencies) == 1
        assert len(tokens) == 1
        assert len(tool_calls) == 0

        # After drain, buffer is empty
        summary = collector.get_summary()
        assert summary.total_events == 0

    def test_drain_returns_copies(self):
        collector = MetricsCollector()
        collector.record_latency(NodeLatency(node_name="agent", agent_name="test", start_time=0, end_time=1, duration_ms=100.0))
        latencies, _, _ = collector.drain()
        latencies.clear()  # mutate returned list
        # Original buffer should be unaffected (already drained)
        summary = collector.get_summary()
        assert summary.total_events == 0


class TestMetricsCollectorBufferEviction:
    def test_buffer_size_limit(self):
        collector = MetricsCollector(buffer_size=3)
        for i in range(5):
            collector.record_latency(NodeLatency(node_name="agent", agent_name="test", start_time=i, end_time=i + 1, duration_ms=100.0))
        summary = collector.get_summary()
        # Only the last 3 should remain
        assert summary.latency["agent"].count == 3


class TestMetricsCollectorThreadSafety:
    def test_concurrent_appends(self):
        collector = MetricsCollector(buffer_size=1000)
        errors: list[Exception] = []

        def writer():
            try:
                for _ in range(200):
                    collector.record_latency(NodeLatency(node_name="agent", agent_name="test", start_time=0, end_time=1, duration_ms=10.0))
                    collector.record_tokens(TokenUsage(model_name="m", input_tokens=1, output_tokens=1, timestamp=time.monotonic()))
                    collector.record_tool_call(ToolCallResult(tool_name="t", success=True, duration_ms=5.0))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        summary = collector.get_summary()
        assert summary.total_events == 5 * 200 * 3
