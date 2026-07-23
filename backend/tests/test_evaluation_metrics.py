"""Tests for evaluation metrics."""

import pytest

from deerflow.evaluation.metrics import (
    ExactMatchMetric,
    LatencyMetric,
    TokenUsageMetric,
    ToolCallAccuracyMetric,
    TrajectoryAccuracyMetric,
    compute_metrics,
)
from deerflow.evaluation.models import EvalExample, EvalMetric, EvalResult, ToolCallSpec
from deerflow.config.evaluation_config import EvalMetricsConfig


# ── Helpers ────────────────────────────────────────────────────────────

def _make_result(**overrides):
    """Create an EvalResult with sensible defaults for testing."""
    defaults = {
        "example_id": "ex1",
        "passed": False,
        "score": 0.0,
        "actual_output": "The answer is 4",
        "actual_tool_calls": [],
        "actual_trajectory": [],
        "metrics": [],
        "error": None,
        "latency_ms": 150.0,
        "tokens_used": 100,
    }
    defaults.update(overrides)
    return EvalResult.model_validate(defaults)


def _make_example(**overrides):
    """Create an EvalExample with sensible defaults for testing."""
    defaults = {
        "id": "ex1",
        "input": "What is 2+2?",
        "expected_output": "4",
    }
    defaults.update(overrides)
    return EvalExample.model_validate(defaults)


# ── ExactMatchMetric ────────────────────────────────────────────────────

class TestExactMatchMetric:
    def test_perfect_match(self):
        metric = ExactMatchMetric()
        example = _make_example(expected_output="Hello world")
        result = _make_result(actual_output="Hello world")
        results = metric(example, result)
        assert len(results) == 1
        assert results[0].value == 1.0
        assert results[0].passed is True

    def test_no_match(self):
        metric = ExactMatchMetric()
        example = _make_example(expected_output="Hello")
        result = _make_result(actual_output="Goodbye")
        results = metric(example, result)
        assert results[0].value == 0.0
        assert results[0].passed is False

    def test_whitespace_difference(self):
        metric = ExactMatchMetric()
        example = _make_example(expected_output="answer")
        result = _make_result(actual_output="  answer  ")
        results = metric(example, result)
        assert results[0].value == 1.0
        assert results[0].passed is True

    def test_no_expected_output(self):
        metric = ExactMatchMetric()
        example = _make_example(expected_output=None)
        result = _make_result(actual_output="something")
        results = metric(example, result)
        assert results[0].value == 0.0
        assert results[0].passed is False

    def test_no_actual_output(self):
        metric = ExactMatchMetric()
        example = _make_example(expected_output="expected")
        result = _make_result(actual_output=None)
        results = metric(example, result)
        assert results[0].value == 0.0
        assert results[0].passed is False


# ── ToolCallAccuracyMetric ──────────────────────────────────────────────

class TestToolCallAccuracyMetric:
    def test_all_correct(self):
        metric = ToolCallAccuracyMetric()
        example = _make_example(
            expected_tool_calls=[
                ToolCallSpec(name="web_search", args={"query": "python"}),
                ToolCallSpec(name="read_file", args={"path": "/tmp/x.txt"}),
            ],
        )
        result = _make_result(
            actual_tool_calls=[
                ToolCallSpec(name="web_search", args={"query": "python"}),
                ToolCallSpec(name="read_file", args={"path": "/tmp/x.txt"}),
            ],
        )
        results = metric(example, result)
        assert results[0].value == 1.0
        assert results[0].passed is True

    def test_partial_correct(self):
        metric = ToolCallAccuracyMetric()
        example = _make_example(
            expected_tool_calls=[
                ToolCallSpec(name="web_search", args={"query": "python"}),
                ToolCallSpec(name="read_file", args={"path": "/tmp/x.txt"}),
            ],
        )
        result = _make_result(
            actual_tool_calls=[
                ToolCallSpec(name="web_search", args={"query": "python"}),
            ],
        )
        results = metric(example, result)
        assert results[0].value == 0.5  # 1 out of 2
        assert results[0].passed is False

    def test_none_correct(self):
        metric = ToolCallAccuracyMetric()
        example = _make_example(
            expected_tool_calls=[ToolCallSpec(name="web_search", args={})],
        )
        result = _make_result(
            actual_tool_calls=[ToolCallSpec(name="bash", args={})],
        )
        results = metric(example, result)
        assert results[0].value == 0.0
        assert results[0].passed is False

    def test_no_expected_calls(self):
        metric = ToolCallAccuracyMetric()
        example = _make_example(expected_tool_calls=None)
        result = _make_result(actual_tool_calls=[])
        results = metric(example, result)
        assert results[0].value == 1.0  # trivially correct
        assert results[0].passed is True

    def test_tool_call_without_args(self):
        """Tool calls without args match correctly."""
        metric = ToolCallAccuracyMetric()
        example = _make_example(
            expected_tool_calls=[ToolCallSpec(name="bash", args={})],
        )
        result = _make_result(
            actual_tool_calls=[ToolCallSpec(name="bash", args={})],
        )
        results = metric(example, result)
        assert results[0].value == 1.0


# ── TrajectoryAccuracyMetric ────────────────────────────────────────────

class TestTrajectoryAccuracyMetric:
    def test_exact_match(self):
        metric = TrajectoryAccuracyMetric()
        example = _make_example(
            expected_trajectory=["agent", "tools", "agent"],
        )
        result = _make_result(
            actual_trajectory=["agent", "tools", "agent"],
        )
        results = metric(example, result)
        assert results[0].value == 1.0
        assert results[0].passed is True

    def test_partial_lcs_match(self):
        metric = TrajectoryAccuracyMetric()
        example = _make_example(
            expected_trajectory=["agent", "tools", "agent", "tools", "agent"],
        )
        result = _make_result(
            actual_trajectory=["agent", "tools", "agent"],
        )
        # LCS = 3, expected = 5, score = 3/5 = 0.6
        results = metric(example, result)
        assert results[0].value == pytest.approx(0.6)

    def test_no_match(self):
        metric = TrajectoryAccuracyMetric()
        example = _make_example(expected_trajectory=["agent", "tools"])
        result = _make_result(actual_trajectory=["other", "stuff"])
        results = metric(example, result)
        assert results[0].value == 0.0

    def test_empty_expected(self):
        metric = TrajectoryAccuracyMetric()
        example = _make_example(expected_trajectory=None)
        result = _make_result(actual_trajectory=["anything"])
        results = metric(example, result)
        assert results[0].value == 1.0
        assert results[0].passed is True

    def test_empty_both(self):
        metric = TrajectoryAccuracyMetric()
        example = _make_example(expected_trajectory=[])
        result = _make_result(actual_trajectory=[])
        results = metric(example, result)
        assert results[0].value == 1.0


# ── LatencyMetric ───────────────────────────────────────────────────────

class TestLatencyMetric:
    def test_under_threshold(self):
        metric = LatencyMetric(max_threshold_ms=1000.0)
        example = _make_example()
        result = _make_result(latency_ms=500.0)
        results = metric(example, result)
        assert results[0].value == 500.0
        assert results[0].passed is True

    def test_over_threshold(self):
        metric = LatencyMetric(max_threshold_ms=1000.0)
        example = _make_example()
        result = _make_result(latency_ms=1500.0)
        results = metric(example, result)
        assert results[0].value == 1500.0
        assert results[0].passed is False

    def test_no_latency_data(self):
        metric = LatencyMetric()
        example = _make_example()
        result = _make_result(latency_ms=None)
        results = metric(example, result)
        assert results[0].value == 0.0
        assert results[0].passed is False

    def test_custom_threshold(self):
        metric = LatencyMetric(max_threshold_ms=500.0)
        example = _make_example()
        result = _make_result(latency_ms=400.0)
        results = metric(example, result)
        assert results[0].threshold == 500.0
        assert results[0].passed is True


# ── TokenUsageMetric ────────────────────────────────────────────────────

class TestTokenUsageMetric:
    def test_under_threshold(self):
        metric = TokenUsageMetric(max_threshold=1000)
        example = _make_example()
        result = _make_result(tokens_used=500)
        results = metric(example, result)
        assert results[0].value == 500.0
        assert results[0].passed is True

    def test_over_threshold(self):
        metric = TokenUsageMetric(max_threshold=1000)
        example = _make_example()
        result = _make_result(tokens_used=2000)
        results = metric(example, result)
        assert results[0].value == 2000.0
        assert results[0].passed is False

    def test_no_token_data(self):
        metric = TokenUsageMetric()
        example = _make_example()
        result = _make_result(tokens_used=None)
        results = metric(example, result)
        assert results[0].value == 0.0
        assert results[0].passed is False


# ── compute_metrics ─────────────────────────────────────────────────────

class TestComputeMetrics:
    def test_all_enabled(self):
        """When all metrics are enabled, all are computed."""
        config = EvalMetricsConfig(
            exact_match=True,
            semantic_similarity=False,
            tool_call_accuracy=True,
            trajectory_accuracy=True,
            latency=True,
            token_usage=True,
        )
        example = _make_example(expected_output="Hello", expected_tool_calls=None, expected_trajectory=None)
        result = _make_result(actual_output="Hello")
        metrics = compute_metrics(example, result, config)
        assert len(metrics) == 5  # exact_match, tool_call, trajectory, latency, token_usage

    def test_only_exact_match(self):
        """When only exact_match is enabled, only it is computed."""
        config = EvalMetricsConfig(
            exact_match=True,
            semantic_similarity=False,
            tool_call_accuracy=False,
            trajectory_accuracy=False,
            latency=False,
            token_usage=False,
        )
        example = _make_example(expected_output="Hello")
        result = _make_result(actual_output="Hello")
        metrics = compute_metrics(example, result, config)
        assert len(metrics) == 1
        assert metrics[0].name == "exact_match"

    def test_none_enabled(self):
        """When no metrics are enabled, returns empty list."""
        config = EvalMetricsConfig(
            exact_match=False, semantic_similarity=False,
            tool_call_accuracy=False, trajectory_accuracy=False,
            latency=False, token_usage=False,
        )
        example = _make_example()
        result = _make_result()
        metrics = compute_metrics(example, result, config)
        assert metrics == []
