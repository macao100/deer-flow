"""Tests for deerflow.tracing.observability.callbacks."""

from __future__ import annotations

import uuid

from deerflow.tracing.observability.callbacks import ObservabilityCallbacks
from deerflow.tracing.observability.metrics_collector import MetricsCollector


class TestObservabilityCallbacks:
    def test_chain_latency_recording(self):
        collector = MetricsCollector(buffer_size=100)
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        serialized = {"name": "agent", "id": ["test"]}
        cb.on_chain_start(serialized, {}, run_id=run_id)
        cb.on_chain_end({}, run_id=run_id)

        summary = collector.get_summary()
        assert "agent" in summary.latency
        assert summary.latency["agent"].count == 1

    def test_llm_token_recording(self):
        collector = MetricsCollector(buffer_size=100)
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        serialized = {"ls_model_name": "gpt-4", "name": "ChatOpenAI"}
        cb.on_llm_start(serialized, ["prompt"], run_id=run_id)

        # Mock LLM response with token usage
        class FakeResponse:
            llm_output = {"token_usage": {"prompt_tokens": 100, "completion_tokens": 50}}
            generations = None

        cb.on_llm_end(FakeResponse(), run_id=run_id)

        summary = collector.get_summary()
        assert "gpt-4" in summary.tokens
        assert summary.tokens["gpt-4"].total_input_tokens == 100
        assert summary.tokens["gpt-4"].total_output_tokens == 50
        assert summary.tokens["gpt-4"].call_count == 1

    def test_tool_success_recording(self):
        collector = MetricsCollector(buffer_size=100)
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        serialized = {"name": "bash"}
        cb.on_tool_start(serialized, "ls -la", run_id=run_id)
        cb.on_tool_end("file1.txt\nfile2.txt", run_id=run_id)

        summary = collector.get_summary()
        assert "bash" in summary.tool_calls
        assert summary.tool_calls["bash"].total == 1
        assert summary.tool_calls["bash"].success == 1
        assert summary.tool_calls["bash"].failure == 0

    def test_tool_failure_recording(self):
        collector = MetricsCollector(buffer_size=100)
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        serialized = {"name": "bash"}
        cb.on_tool_start(serialized, "rm -rf /", run_id=run_id)
        cb.on_tool_end("Error: permission denied", run_id=run_id)

        summary = collector.get_summary()
        assert summary.tool_calls["bash"].failure == 1
        assert summary.tool_calls["bash"].success == 0

    def test_missing_timer_does_not_crash(self):
        collector = MetricsCollector()
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        # on_chain_end without matching on_chain_start should not crash
        cb.on_chain_end({}, run_id=run_id)

    def test_unknown_provider_extracted_from_serialized(self):
        collector = MetricsCollector(buffer_size=100)
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        serialized = {"name": "some-unknown-llm"}
        cb.on_llm_start(serialized, ["p"], run_id=run_id)

        # Use the generations fallback path with token_usage in message response_metadata
        class FakeMessage:
            pass

        msg = FakeMessage()
        msg.response_metadata = {"token_usage": {"prompt_tokens": 5, "completion_tokens": 3}}

        class FakeResponse:
            llm_output = {}
            generations = [[msg]]

        cb.on_llm_end(FakeResponse(), run_id=run_id)

        summary = collector.get_summary()
        assert "some-unknown-llm" in summary.tokens
        assert summary.tokens["some-unknown-llm"].total_input_tokens == 5
        assert summary.tokens["some-unknown-llm"].total_output_tokens == 3

    def test_metadata_not_required(self):
        collector = MetricsCollector(buffer_size=100)
        cb = ObservabilityCallbacks(metrics=collector)

        run_id = uuid.uuid4()
        # on_chain_start with None metadata
        cb.on_chain_start({"name": "test"}, {}, run_id=run_id, metadata=None)
        cb.on_chain_end({}, run_id=run_id)

        summary = collector.get_summary()
        assert summary.latency["test"].count == 1
