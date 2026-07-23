"""Evaluation pipeline for automated agent quality measurement.

This package provides:
- Data models for datasets, examples, runs, and results
- Dataset registry for local YAML/JSON file storage
- Evaluation metrics (exact match, tool call accuracy, etc.)
- Runner for executing evaluations against agents
- CLI entry point for offline evaluation runs

Usage::

    from deerflow.evaluation import DatasetRegistry, EvalRunner, EvalDataset

    registry = DatasetRegistry(".deer-flow/eval/datasets")
    dataset = registry.get_dataset("my-benchmark")

    runner = EvalRunner(config)
    eval_run = await runner.run(dataset=dataset, model_name="deepseek-v4-pro")
"""

from __future__ import annotations

from deerflow.evaluation.metrics import (
    ExactMatchMetric,
    LatencyMetric,
    TokenUsageMetric,
    ToolCallAccuracyMetric,
    TrajectoryAccuracyMetric,
    compute_metrics,
)
from deerflow.evaluation.models import (
    EvalDataset,
    EvalExample,
    EvalMetric,
    EvalResult,
    EvalRun,
    ToolCallSpec,
)
from deerflow.evaluation.registry import DatasetRegistry
from deerflow.evaluation.runner import EvalRunner

__all__ = [
    # Models
    "EvalDataset",
    "EvalExample",
    "EvalMetric",
    "EvalResult",
    "EvalRun",
    "ToolCallSpec",
    # Registry
    "DatasetRegistry",
    # Metrics
    "ExactMatchMetric",
    "LatencyMetric",
    "TokenUsageMetric",
    "ToolCallAccuracyMetric",
    "TrajectoryAccuracyMetric",
    "compute_metrics",
    # Runner
    "EvalRunner",
]
