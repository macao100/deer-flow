"""Data models for the evaluation pipeline.

All models use Pydantic v2 for validation and YAML/JSON serialization.
Datasets are stored as YAML files and loaded/saved through these models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ToolCallSpec(BaseModel):
    """Specification for an expected tool call in an evaluation example."""

    model_config = {"frozen": True}

    name: str = Field(description="Name of the tool that should be called")
    args: dict = Field(default_factory=dict, description="Expected arguments for the tool call")


class EvalExample(BaseModel):
    """A single evaluation example — input paired with expected outputs and behavior.

    At minimum, ``id`` and ``input`` are required. The expected fields
    (output, tool_calls, trajectory) are all optional — a dataset may
    validate only a subset of aspects.
    """

    model_config = {"frozen": True}

    id: str = Field(description="Unique identifier for this example within its dataset")
    input: str = Field(description="User query or prompt to send to the agent")
    expected_output: str | None = Field(default=None, description="Expected text response (for exact-match or LLM-as-judge metrics)")
    expected_tool_calls: list[ToolCallSpec] | None = Field(default=None, description="Expected tool calls with their arguments")
    expected_trajectory: list[str] | None = Field(default=None, description="Expected sequence of graph node names executed")
    metadata: dict = Field(default_factory=dict, description="Arbitrary metadata (difficulty, category, tags, etc.)")


class EvalDataset(BaseModel):
    """A named collection of evaluation examples."""

    id: str = Field(description="Unique identifier for this dataset")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="", description="Description of what this dataset evaluates")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp (UTC)")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last modification timestamp (UTC)")
    examples: list[EvalExample] = Field(default_factory=list, description="Evaluation examples")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering and organization")


class EvalMetric(BaseModel):
    """A single computed metric for one example or aggregate."""

    name: str = Field(description="Metric name (e.g., exact_match, latency, tool_call_accuracy)")
    value: float = Field(description="Computed value")
    threshold: float | None = Field(default=None, description="Threshold that defines pass/fail")
    passed: bool | None = Field(default=None, description="Whether the metric passed its threshold")


class EvalResult(BaseModel):
    """The outcome of evaluating a single example."""

    example_id: str = Field(description="ID of the evaluated example")
    passed: bool = Field(description="Whether the example passed overall (all metrics passed)")
    score: float = Field(description="Aggregated score 0.0–1.0")
    actual_output: str | None = Field(default=None, description="Actual text response from the agent")
    actual_tool_calls: list[ToolCallSpec] = Field(default_factory=list, description="Actual tool calls observed")
    actual_trajectory: list[str] = Field(default_factory=list, description="Actual graph node sequence observed")
    metrics: list[EvalMetric] = Field(default_factory=list, description="Computed metrics for this example")
    error: str | None = Field(default=None, description="Error message if the example failed unexpectedly")
    latency_ms: float | None = Field(default=None, description="End-to-end latency in milliseconds")
    tokens_used: int | None = Field(default=None, description="Total tokens consumed (input + output)")


class EvalRun(BaseModel):
    """A complete evaluation run against one model using one dataset."""

    id: str = Field(description="Unique identifier for this run")
    dataset_id: str = Field(description="ID of the dataset used")
    model_name: str = Field(description="Name of the model being evaluated")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending",
        description="Current status of the evaluation run",
    )
    started_at: datetime | None = Field(default=None, description="When the run started (UTC)")
    completed_at: datetime | None = Field(default=None, description="When the run completed (UTC)")
    results: list[EvalResult] = Field(default_factory=list, description="Per-example evaluation results")
    summary: dict = Field(default_factory=dict, description="Aggregated summary statistics")
