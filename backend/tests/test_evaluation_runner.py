"""Tests for the evaluation runner — EvalRunner and summary computation."""

from unittest.mock import MagicMock, patch

import pytest

from deerflow.config.evaluation_config import EvalMetricsConfig
from deerflow.evaluation.models import (
    EvalDataset,
    EvalExample,
    EvalMetric,
    EvalResult,
    EvalRun,
    ToolCallSpec,
)
from deerflow.evaluation.runner import EvalRunner


# ── Helpers ────────────────────────────────────────────────────────────

def _make_mock_stream_events(
    *,
    text: str = "The answer is 4",
    tool_calls: list[dict] | None = None,
    tool_results: list[str] | None = None,
    total_tokens: int = 100,
) -> list:
    """Build a realistic sequence of stream events for a mock client."""
    from deerflow.client import StreamEvent

    events: list[StreamEvent] = []

    # Agent turn with optional tool calls
    ai_data: dict = {"type": "ai", "content": text, "id": "msg-1"}
    if tool_calls:
        ai_data["tool_calls"] = tool_calls
    events.append(StreamEvent(type="messages-tuple", data=ai_data))

    # Tool results if any
    if tool_results:
        for i, result in enumerate(tool_results):
            events.append(
                StreamEvent(
                    type="messages-tuple",
                    data={
                        "type": "tool",
                        "content": result,
                        "name": f"tool_{i}",
                        "tool_call_id": f"tc_{i}",
                        "id": f"tr-{i}",
                    },
                )
            )
        # Final agent response after tools
        events.append(
            StreamEvent(type="messages-tuple", data={"type": "ai", "content": text, "id": "msg-2"})
        )

    # Values snapshot
    values_messages = [
        {"type": "human", "content": "What is 2+2?", "id": "h-1"},
        {"type": "ai", "content": text, "id": "msg-1"},
    ]
    if tool_calls:
        values_messages.insert(1, {"type": "ai", "content": "", "tool_calls": tool_calls, "id": "msg-1"})
        for i in range(len(tool_results or [])):
            values_messages.append({"type": "tool", "content": tool_results[i] if tool_results else "", "id": f"tr-{i}"})
        values_messages.append({"type": "ai", "content": text, "id": "msg-2"})

    events.append(
        StreamEvent(
            type="values",
            data={"title": "Test", "messages": values_messages, "artifacts": []},
        )
    )

    # End event with usage
    events.append(
        StreamEvent(
            type="end",
            data={"usage": {"input_tokens": 50, "output_tokens": 50, "total_tokens": total_tokens}},
        )
    )

    return events


def _make_config(**overrides) -> "EvaluationConfig":
    """Create an EvaluationConfig for testing."""
    from deerflow.config.evaluation_config import EvaluationConfig

    defaults = {
        "enabled": True,
        "datasets_dir": "/tmp/eval-datasets",
        "default_judge_model": "test-model",
        "max_concurrent_evals": 1,
        "metrics": EvalMetricsConfig(
            exact_match=True,
            tool_call_accuracy=True,
            trajectory_accuracy=True,
            latency=True,
            token_usage=True,
        ),
    }
    defaults.update(overrides)
    return EvaluationConfig.model_validate(defaults)


# ── Tests: run_dataset ─────────────────────────────────────────────────

class TestEvalRunnerRunDataset:
    def test_basic_run(self):
        """A simple dataset with one example runs and returns an EvalRun."""
        dataset = EvalDataset(
            id="ds1",
            name="Basic",
            examples=[EvalExample(id="ex1", input="What is 2+2?", expected_output="4")],
        )

        mock_events = _make_mock_stream_events(text="4")
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert isinstance(eval_run, EvalRun)
        assert eval_run.dataset_id == "ds1"
        assert eval_run.model_name == "test-model"
        assert eval_run.status == "completed"
        assert len(eval_run.results) == 1
        assert eval_run.results[0].example_id == "ex1"
        assert eval_run.results[0].actual_output == "4"
        assert eval_run.summary["total"] == 1

    def test_multiple_examples(self):
        """Dataset with multiple examples evaluates all of them."""
        dataset = EvalDataset(
            id="ds2",
            name="Multi",
            examples=[
                EvalExample(id="ex1", input="Q1?", expected_output="A1"),
                EvalExample(id="ex2", input="Q2?", expected_output="A2"),
                EvalExample(id="ex3", input="Q3?", expected_output="A3"),
            ],
        )

        mock_events = _make_mock_stream_events(text="A1")
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert len(eval_run.results) == 3
        assert eval_run.summary["total"] == 3

    def test_passed_and_failed_counts(self):
        """Summary correctly counts passed vs failed examples."""
        dataset = EvalDataset(
            id="ds3",
            name="Mixed",
            examples=[
                EvalExample(id="ex1", input="Q1", expected_output="correct"),
                EvalExample(id="ex2", input="Q2", expected_output="correct"),
            ],
        )

        # First mock returns exact match, second returns wrong answer
        events_correct = _make_mock_stream_events(text="correct")
        events_wrong = _make_mock_stream_events(text="wrong")

        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.side_effect = [events_correct, events_wrong]

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert eval_run.summary["passed"] == 1
        assert eval_run.summary["failed"] == 1

    def test_empty_dataset(self):
        """Empty dataset returns a run with no results."""
        dataset = EvalDataset(id="ds-empty", name="Empty")

        runner = EvalRunner(model_name="test-model", config=_make_config())
        eval_run = runner.run_dataset(dataset)

        assert len(eval_run.results) == 0
        assert eval_run.summary["total"] == 0
        assert eval_run.summary["pass_rate"] == 0.0


# ── Tests: stream event handling ───────────────────────────────────────

class TestEvalRunnerStreamCapture:
    def test_captures_text_output(self):
        """Actual output is extracted from the last AI message in values."""
        dataset = EvalDataset(
            id="ds-text",
            name="Text Capture",
            examples=[EvalExample(id="ex1", input="Hello", expected_output=None)],
        )

        mock_events = _make_mock_stream_events(text="Bonjour le monde")
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert eval_run.results[0].actual_output == "Bonjour le monde"

    def test_captures_tool_calls(self):
        """Tool calls from messages-tuple events are captured."""
        dataset = EvalDataset(
            id="ds-tools",
            name="Tool Capture",
            examples=[EvalExample(id="ex1", input="Search for Python")],
        )

        mock_events = _make_mock_stream_events(
            text="Here is the result",
            tool_calls=[{"name": "web_search", "args": {"query": "python"}, "id": "tc1"}],
            tool_results=["Found: Python is a programming language"],
        )
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        actual_tool_calls = eval_run.results[0].actual_tool_calls
        assert len(actual_tool_calls) == 1
        assert actual_tool_calls[0].name == "web_search"
        assert actual_tool_calls[0].args == {"query": "python"}

    def test_captures_trajectory(self):
        """Trajectory records agent/tools sequence."""
        dataset = EvalDataset(
            id="ds-traj",
            name="Trajectory Capture",
            examples=[EvalExample(id="ex1", input="Do a search")],
        )

        mock_events = _make_mock_stream_events(
            text="Done",
            tool_calls=[{"name": "bash", "args": {"command": "ls"}, "id": "tc1"}],
            tool_results=["file1.txt\nfile2.txt"],
        )
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        trajectory = eval_run.results[0].actual_trajectory
        assert "agent" in trajectory
        assert "tools" in trajectory

    def test_captures_latency(self):
        """Latency is measured from the stream call."""
        dataset = EvalDataset(
            id="ds-lat",
            name="Latency Capture",
            examples=[EvalExample(id="ex1", input="Ping")],
        )

        mock_events = _make_mock_stream_events(text="Pong")
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert eval_run.results[0].latency_ms is not None
        assert eval_run.results[0].latency_ms >= 0.0

    def test_captures_token_usage(self):
        """Token usage is extracted from the end event."""
        dataset = EvalDataset(
            id="ds-tok",
            name="Token Capture",
            examples=[EvalExample(id="ex1", input="Count tokens")],
        )

        mock_events = _make_mock_stream_events(text="ok", total_tokens=250)
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert eval_run.results[0].tokens_used == 250


# ── Tests: error handling ──────────────────────────────────────────────

class TestEvalRunnerErrorHandling:
    def test_client_exception_is_captured(self):
        """When the client raises, the error is captured and the run continues."""
        dataset = EvalDataset(
            id="ds-err",
            name="Error Test",
            examples=[EvalExample(id="ex1", input="crash")],
        )

        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.side_effect = RuntimeError("Model unavailable")

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert eval_run.results[0].error is not None
        assert "RuntimeError" in eval_run.results[0].error
        assert eval_run.results[0].passed is False
        assert eval_run.summary["errors"] == 1

    def test_mixed_success_and_error(self):
        """One example fails, the next succeeds."""
        dataset = EvalDataset(
            id="ds-mixed",
            name="Mixed Errors",
            examples=[
                EvalExample(id="ex1", input="Q1", expected_output="A1"),
                EvalExample(id="ex2", input="Q2", expected_output="A2"),
            ],
        )

        events = _make_mock_stream_events(text="A2")

        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.side_effect = [RuntimeError("fail"), events]

            runner = EvalRunner(model_name="test-model", config=_make_config())
            eval_run = runner.run_dataset(dataset)

        assert eval_run.results[0].error is not None
        assert eval_run.results[1].error is None
        assert eval_run.summary["errors"] == 1
        assert eval_run.summary["total"] == 2


# ── Tests: summary computation ─────────────────────────────────────────

class TestEvalRunnerSummary:
    def test_summary_aggregates_metrics(self):
        """Summary includes per-metric aggregation."""
        # Build results manually to test _build_summary directly
        results = [
            EvalResult(
                example_id="ex1",
                passed=True,
                score=1.0,
                actual_output="correct",
                metrics=[
                    EvalMetric(name="exact_match", value=1.0, threshold=0.5, passed=True),
                    EvalMetric(name="latency", value=100.0, threshold=5000.0, passed=True),
                ],
                latency_ms=100.0,
                tokens_used=50,
            ),
            EvalResult(
                example_id="ex2",
                passed=False,
                score=0.5,
                actual_output="wrong",
                metrics=[
                    EvalMetric(name="exact_match", value=0.0, threshold=0.5, passed=False),
                    EvalMetric(name="latency", value=300.0, threshold=5000.0, passed=True),
                ],
                latency_ms=300.0,
                tokens_used=150,
            ),
        ]

        summary = EvalRunner._build_summary(results)

        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 0.5
        assert summary["avg_latency_ms"] == 200.0
        assert summary["avg_tokens"] == 100.0

        # Per-metric aggregation
        assert "exact_match" in summary["metrics"]
        assert summary["metrics"]["exact_match"]["avg"] == 0.5
        assert summary["metrics"]["exact_match"]["min"] == 0.0
        assert summary["metrics"]["exact_match"]["max"] == 1.0

        assert "latency" in summary["metrics"]
        assert summary["metrics"]["latency"]["avg"] == 200.0

    def test_summary_empty_results(self):
        """Empty results produce a valid empty summary."""
        summary = EvalRunner._build_summary([])
        assert summary == {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}

    def test_summary_with_none_values(self):
        """Results with None latency/tokens don't break the summary."""
        results = [
            EvalResult(
                example_id="ex1",
                passed=True,
                score=1.0,
                metrics=[],
                latency_ms=None,
                tokens_used=None,
            ),
        ]

        summary = EvalRunner._build_summary(results)
        assert summary["avg_latency_ms"] == 0.0
        assert summary["avg_tokens"] == 0.0


# ── Tests: metric configuration ────────────────────────────────────────

class TestEvalRunnerMetricConfig:
    def test_only_exact_match_enabled(self):
        """When only exact_match is enabled, only that metric is computed."""
        dataset = EvalDataset(
            id="ds-cfg",
            name="Config Test",
            examples=[EvalExample(id="ex1", input="Hello", expected_output="Hello")],
        )

        config = _make_config(
            metrics=EvalMetricsConfig(
                exact_match=True,
                tool_call_accuracy=False,
                trajectory_accuracy=False,
                latency=False,
                token_usage=False,
            )
        )

        mock_events = _make_mock_stream_events(text="Hello")
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=config)
            eval_run = runner.run_dataset(dataset)

        metric_names = [m.name for m in eval_run.results[0].metrics]
        assert metric_names == ["exact_match"]

    def test_all_metrics_enabled(self):
        """When all metrics are enabled, all are computed."""
        dataset = EvalDataset(
            id="ds-all",
            name="All Metrics",
            examples=[
                EvalExample(
                    id="ex1",
                    input="Hello",
                    expected_output="Hello",
                    expected_tool_calls=[ToolCallSpec(name="bash", args={})],
                    expected_trajectory=["agent", "tools", "agent"],
                )
            ],
        )

        config = _make_config(
            metrics=EvalMetricsConfig(
                exact_match=True,
                tool_call_accuracy=True,
                trajectory_accuracy=True,
                latency=True,
                token_usage=True,
            )
        )

        mock_events = _make_mock_stream_events(
            text="Hello",
            tool_calls=[{"name": "bash", "args": {}, "id": "tc1"}],
            tool_results=["output"],
        )
        with patch("deerflow.client.DeerFlowClient") as MockClient:
            mock_instance = MockClient.return_value
            mock_instance.stream.return_value = mock_events

            runner = EvalRunner(model_name="test-model", config=config)
            eval_run = runner.run_dataset(dataset)

        metric_names = {m.name for m in eval_run.results[0].metrics}
        assert metric_names == {"exact_match", "tool_call_accuracy", "trajectory_accuracy", "latency", "token_usage"}
