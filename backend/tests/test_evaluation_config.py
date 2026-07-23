"""Tests for evaluation configuration models."""

import pytest
from pydantic import ValidationError

from deerflow.config.evaluation_config import EvalMetricsConfig, EvaluationConfig


class TestEvalMetricsConfig:
    """Tests for EvalMetricsConfig — metric selection."""

    def test_defaults_all_standard_metrics(self):
        """By default, exact_match, latency, and token_usage are enabled."""
        config = EvalMetricsConfig()
        assert config.exact_match is True
        assert config.semantic_similarity is False
        assert config.tool_call_accuracy is False
        assert config.trajectory_accuracy is False
        assert config.latency is True
        assert config.token_usage is True

    def test_accepts_custom_values(self):
        """All fields accept explicit boolean values."""
        config = EvalMetricsConfig(
            exact_match=False,
            semantic_similarity=True,
            tool_call_accuracy=True,
            trajectory_accuracy=True,
            latency=False,
            token_usage=False,
        )
        assert config.exact_match is False
        assert config.semantic_similarity is True
        assert config.tool_call_accuracy is True
        assert config.trajectory_accuracy is True
        assert config.latency is False
        assert config.token_usage is False

    def test_partial_override(self):
        """Only specified fields are overridden."""
        config = EvalMetricsConfig(semantic_similarity=True, tool_call_accuracy=True)
        assert config.exact_match is True  # default preserved
        assert config.semantic_similarity is True
        assert config.tool_call_accuracy is True
        assert config.latency is True  # default preserved

    def test_model_dump_roundtrip(self):
        """model_dump + model_validate roundtrip."""
        config = EvalMetricsConfig(
            exact_match=True,
            semantic_similarity=True,
            tool_call_accuracy=False,
            trajectory_accuracy=False,
            latency=True,
            token_usage=True,
        )
        data = config.model_dump()
        reloaded = EvalMetricsConfig.model_validate(data)
        assert reloaded == config


class TestEvaluationConfig:
    """Tests for EvaluationConfig — top-level evaluation configuration."""

    def test_defaults_are_disabled(self):
        """Evaluation is disabled by default — safe for existing deployments."""
        config = EvaluationConfig()
        assert config.enabled is False
        assert config.datasets_dir == ".deer-flow/evaluation/datasets"
        assert config.default_judge_model == "deepseek-v4-pro"
        assert config.max_concurrent_evals == 3
        assert isinstance(config.metrics, EvalMetricsConfig)

    def test_accepts_custom_values(self):
        """All fields accept explicit values."""
        metrics = EvalMetricsConfig(exact_match=True, latency=True, token_usage=False)
        config = EvaluationConfig(
            enabled=True,
            datasets_dir="/custom/datasets",
            default_judge_model="deepseek-v4-flash",
            max_concurrent_evals=5,
            metrics=metrics,
        )
        assert config.enabled is True
        assert config.datasets_dir == "/custom/datasets"
        assert config.default_judge_model == "deepseek-v4-flash"
        assert config.max_concurrent_evals == 5
        assert config.metrics == metrics

    def test_max_concurrent_evals_clamped(self):
        """max_concurrent_evals must be between 1 and 10."""
        with pytest.raises(ValidationError):
            EvaluationConfig(max_concurrent_evals=0)

        with pytest.raises(ValidationError):
            EvaluationConfig(max_concurrent_evals=11)

    def test_max_concurrent_evals_boundary_values(self):
        """Boundary values 1 and 10 are accepted."""
        config1 = EvaluationConfig(max_concurrent_evals=1)
        assert config1.max_concurrent_evals == 1

        config10 = EvaluationConfig(max_concurrent_evals=10)
        assert config10.max_concurrent_evals == 10

    def test_model_dump_roundtrip(self):
        """model_dump + model_validate roundtrip preserves all values."""
        metrics = EvalMetricsConfig(
            exact_match=True,
            semantic_similarity=True,
            tool_call_accuracy=True,
            trajectory_accuracy=False,
            latency=True,
            token_usage=True,
        )
        config = EvaluationConfig(
            enabled=True,
            datasets_dir="/tmp/evals",
            default_judge_model="mistral-large",
            max_concurrent_evals=2,
            metrics=metrics,
        )
        data = config.model_dump()
        reloaded = EvaluationConfig.model_validate(data)
        assert reloaded == config
        assert reloaded.metrics == metrics

    def test_default_judge_model_accepts_any_string(self):
        """default_judge_model accepts any model name string."""
        config = EvaluationConfig(default_judge_model="my-custom-model")
        assert config.default_judge_model == "my-custom-model"

    def test_datasets_dir_accepts_relative_path(self):
        """datasets_dir accepts relative paths."""
        config = EvaluationConfig(datasets_dir="./relative/path")
        assert config.datasets_dir == "./relative/path"
