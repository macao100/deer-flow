"""Tests for evaluation data models."""

import json

import pytest
import yaml
from pydantic import ValidationError

from deerflow.evaluation.models import (
    EvalDataset,
    EvalExample,
    EvalMetric,
    EvalResult,
    EvalRun,
    ToolCallSpec,
)


class TestToolCallSpec:
    """Tests for ToolCallSpec — expected tool call specification."""

    def test_creates_with_name_and_args(self):
        spec = ToolCallSpec(name="web_search", args={"query": "test"})
        assert spec.name == "web_search"
        assert spec.args == {"query": "test"}

    def test_default_args_is_empty_dict(self):
        spec = ToolCallSpec(name="bash")
        assert spec.args == {}

    def test_serializes_to_yaml(self):
        spec = ToolCallSpec(name="read_file", args={"path": "/tmp/test.txt"})
        data = spec.model_dump()
        yaml_str = yaml.dump(data, sort_keys=False)
        reloaded = yaml.safe_load(yaml_str)
        assert reloaded["name"] == "read_file"
        assert reloaded["args"] == {"path": "/tmp/test.txt"}

    def test_immutable(self):
        spec = ToolCallSpec(name="test")
        with pytest.raises(ValidationError):
            spec.name = "other"  # type: ignore[misc]


class TestEvalExample:
    """Tests for EvalExample — a single evaluation example."""

    def test_minimal_example(self):
        example = EvalExample(id="ex1", input="What is 2+2?")
        assert example.id == "ex1"
        assert example.input == "What is 2+2?"
        assert example.expected_output is None
        assert example.expected_tool_calls is None
        assert example.expected_trajectory is None
        assert example.metadata == {}

    def test_full_example(self):
        example = EvalExample(
            id="ex2",
            input="Search for Python docs",
            expected_output="Found: https://docs.python.org",
            expected_tool_calls=[ToolCallSpec(name="web_search", args={"query": "Python docs"})],
            expected_trajectory=["agent", "tools", "agent"],
            metadata={"difficulty": "easy", "category": "web_search"},
        )
        assert example.expected_output == "Found: https://docs.python.org"
        assert len(example.expected_tool_calls) == 1
        assert example.expected_tool_calls[0].name == "web_search"
        assert example.expected_trajectory == ["agent", "tools", "agent"]
        assert example.metadata["difficulty"] == "easy"

    def test_yaml_roundtrip(self):
        example = EvalExample(
            id="ex3",
            input="Read file /tmp/data.txt",
            expected_output="File contents: hello",
            metadata={"category": "file_ops"},
        )
        yaml_str = yaml.dump(example.model_dump(), sort_keys=False)
        data = yaml.safe_load(yaml_str)
        reloaded = EvalExample.model_validate(data)
        assert reloaded == example


class TestEvalDataset:
    """Tests for EvalDataset — a collection of evaluation examples."""

    def test_minimal_dataset(self):
        dataset = EvalDataset(id="ds1", name="Basic Tests")
        assert dataset.id == "ds1"
        assert dataset.name == "Basic Tests"
        assert dataset.description == ""
        assert dataset.examples == []
        assert dataset.tags == []

    def test_dataset_with_examples(self):
        examples = [
            EvalExample(id="ex1", input="Q1"),
            EvalExample(id="ex2", input="Q2", expected_output="A2"),
        ]
        dataset = EvalDataset(
            id="ds2",
            name="Math Tests",
            description="Basic math evaluation",
            examples=examples,
            tags=["math", "basic"],
        )
        assert len(dataset.examples) == 2
        assert dataset.tags == ["math", "basic"]
        assert dataset.description == "Basic math evaluation"

    def test_yaml_roundtrip(self):
        dataset = EvalDataset(
            id="ds3",
            name="Web Search Tests",
            description="Evaluating web search capabilities",
            examples=[
                EvalExample(
                    id="ex1",
                    input="Search for Python",
                    expected_tool_calls=[ToolCallSpec(name="web_search", args={"query": "Python"})],
                ),
            ],
            tags=["web", "search"],
        )
        data = dataset.model_dump()
        yaml_str = yaml.dump(data, sort_keys=False, allow_unicode=True)
        reloaded_data = yaml.safe_load(yaml_str)
        reloaded = EvalDataset.model_validate(reloaded_data)
        assert reloaded.id == dataset.id
        assert reloaded.name == dataset.name
        assert len(reloaded.examples) == 1
        assert reloaded.examples[0].expected_tool_calls[0].name == "web_search"

    def test_created_at_auto_generated(self):
        dataset = EvalDataset(id="ds4", name="Time Test")
        assert dataset.created_at is not None
        assert dataset.updated_at is not None

    def test_empty_dataset_yaml_roundtrip(self):
        """Dataset with no examples serializes and deserializes correctly."""
        dataset = EvalDataset(id="empty", name="Empty Dataset")
        data = dataset.model_dump()
        yaml_str = yaml.dump(data, sort_keys=False)
        reloaded_data = yaml.safe_load(yaml_str)
        reloaded = EvalDataset.model_validate(reloaded_data)
        assert reloaded.id == "empty"
        assert reloaded.examples == []


class TestEvalMetric:
    """Tests for EvalMetric — a single metric result."""

    def test_basic_metric(self):
        metric = EvalMetric(name="exact_match", value=1.0, threshold=0.8, passed=True)
        assert metric.name == "exact_match"
        assert metric.value == 1.0
        assert metric.threshold == 0.8
        assert metric.passed is True

    def test_metric_without_threshold(self):
        metric = EvalMetric(name="latency", value=245.5)
        assert metric.threshold is None
        assert metric.passed is None

    def test_yaml_roundtrip(self):
        metric = EvalMetric(name="tool_call_accuracy", value=0.75, threshold=0.8, passed=False)
        yaml_str = yaml.dump(metric.model_dump(), sort_keys=False)
        data = yaml.safe_load(yaml_str)
        reloaded = EvalMetric.model_validate(data)
        assert reloaded == metric


class TestEvalResult:
    """Tests for EvalResult — result of a single example evaluation."""

    def test_passed_result(self):
        result = EvalResult(
            example_id="ex1",
            passed=True,
            score=1.0,
            actual_output="The answer is 4",
            metrics=[EvalMetric(name="exact_match", value=1.0, threshold=0.8, passed=True)],
            latency_ms=150.0,
            tokens_used=42,
        )
        assert result.passed is True
        assert result.score == 1.0
        assert result.error is None
        assert result.latency_ms == 150.0

    def test_failed_result_with_error(self):
        result = EvalResult(
            example_id="ex2",
            passed=False,
            score=0.0,
            error="Model returned empty response",
            metrics=[],
        )
        assert result.passed is False
        assert result.error == "Model returned empty response"
        assert result.actual_output is None
        assert result.latency_ms is None

    def test_default_fields(self):
        result = EvalResult(example_id="ex3", passed=True, score=0.5)
        assert result.actual_output is None
        assert result.actual_tool_calls == []
        assert result.actual_trajectory == []
        assert result.metrics == []
        assert result.error is None
        assert result.latency_ms is None
        assert result.tokens_used is None

    def test_yaml_roundtrip(self):
        result = EvalResult(
            example_id="ex4",
            passed=False,
            score=0.3,
            actual_output="Partial answer",
            actual_tool_calls=[ToolCallSpec(name="web_search", args={})],
            metrics=[EvalMetric(name="exact_match", value=0.0, passed=False)],
            latency_ms=320.5,
            tokens_used=128,
        )
        yaml_str = yaml.dump(result.model_dump(), sort_keys=False)
        data = yaml.safe_load(yaml_str)
        reloaded = EvalResult.model_validate(data)
        assert reloaded == result


class TestEvalRun:
    """Tests for EvalRun — a complete evaluation run."""

    def test_pending_run(self):
        run = EvalRun(id="run1", dataset_id="ds1", model_name="deepseek-v4-flash")
        assert run.status == "pending"
        assert run.results == []
        assert run.summary == {}
        assert run.started_at is None
        assert run.completed_at is None

    def test_completed_run_with_results(self):
        results = [
            EvalResult(example_id="ex1", passed=True, score=1.0, metrics=[]),
            EvalResult(example_id="ex2", passed=False, score=0.0, metrics=[], error="timeout"),
        ]
        run = EvalRun(
            id="run1",
            dataset_id="ds1",
            model_name="deepseek-v4-pro",
            status="completed",
            results=results,
            summary={"total": 2, "passed": 1, "failed": 1, "pass_rate": 0.5},
        )
        assert len(run.results) == 2
        assert run.summary["pass_rate"] == 0.5

    def test_status_validation(self):
        """status must be one of pending, running, completed, failed."""
        with pytest.raises(ValidationError):
            EvalRun(id="r1", dataset_id="d1", model_name="m1", status="invalid")

    def test_yaml_roundtrip(self):
        run = EvalRun(
            id="run2",
            dataset_id="ds2",
            model_name="deepseek-v4-flash",
            status="completed",
            results=[
                EvalResult(
                    example_id="ex1",
                    passed=True,
                    score=1.0,
                    actual_output="OK",
                    latency_ms=100.0,
                    tokens_used=50,
                ),
            ],
            summary={"total": 1, "passed": 1, "pass_rate": 1.0},
        )
        yaml_str = yaml.dump(run.model_dump(), sort_keys=False, default_flow_style=False)
        data = yaml.safe_load(yaml_str)
        reloaded = EvalRun.model_validate(data)
        assert reloaded.id == run.id
        assert reloaded.status == "completed"
        assert len(reloaded.results) == 1
