"""Evaluation pipeline configuration.

Provides :class:`EvaluationConfig` and :class:`EvalMetricsConfig` Pydantic
models for the automated agent evaluation subsystem. When ``enabled`` is
``False`` (the default), no evaluation components are created and the
system is fully backward-compatible.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvalMetricsConfig(BaseModel):
    """Selection of metrics to compute during evaluation runs.

    Each boolean controls whether a specific metric is calculated for
    every example in the dataset. Disabled metrics are skipped entirely.
    """

    exact_match: bool = Field(
        default=True,
        description="Compare expected_output with actual_output (normalized string comparison)",
    )
    semantic_similarity: bool = Field(
        default=False,
        description="LLM-as-judge semantic similarity between expected and actual output",
    )
    tool_call_accuracy: bool = Field(
        default=False,
        description="Compare expected tool calls with actual tool calls (name + args)",
    )
    trajectory_accuracy: bool = Field(
        default=False,
        description="Compare expected agent trajectory (node sequence) with actual trajectory",
    )
    latency: bool = Field(
        default=True,
        description="Record end-to-end latency for each example",
    )
    token_usage: bool = Field(
        default=True,
        description="Record token consumption for each example",
    )


class EvaluationConfig(BaseModel):
    """Top-level evaluation configuration.

    When ``enabled`` is ``False`` (the default), no evaluation components
    are created and the system is fully backward-compatible.
    """

    enabled: bool = Field(
        default=False,
        description="Master switch for the evaluation subsystem",
    )
    datasets_dir: str = Field(
        default=".deer-flow/evaluation/datasets",
        description="Directory where evaluation datasets are stored (YAML files, one per dataset)",
    )
    default_judge_model: str = Field(
        default="deepseek-v4-pro",
        description="Default model used for LLM-as-judge metrics (semantic_similarity)",
    )
    max_concurrent_evals: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of examples evaluated concurrently (1-10)",
    )
    metrics: EvalMetricsConfig = Field(
        default_factory=EvalMetricsConfig,
        description="Which metrics to compute during evaluation runs",
    )
