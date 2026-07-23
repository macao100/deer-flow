"""Evaluation metrics for measuring agent output quality.

Each metric is a callable class that takes an ``EvalExample`` and ``EvalResult``
and returns a list of ``EvalMetric`` objects.

Metrics implemented:
- ExactMatchMetric — normalized string comparison of expected vs actual output
- ToolCallAccuracyMetric — precision of tool calls (name + args match)
- TrajectoryAccuracyMetric — sequence alignment via LCS (Longest Common Subsequence)
- LatencyMetric — pass/fail based on a configurable latency threshold
- TokenUsageMetric — pass/fail based on a configurable token count threshold
"""

from __future__ import annotations

from deerflow.config.evaluation_config import EvalMetricsConfig
from deerflow.evaluation.models import EvalExample, EvalMetric, EvalResult

# ── Helpers ────────────────────────────────────────────────────────────────

def _longest_common_subsequence(seq1: list[str], seq2: list[str]) -> int:
    """Return the length of the longest common subsequence of two string lists."""
    if not seq1 or not seq2:
        return 0
    m, n = len(seq1), len(seq2)
    # Use two rows to save memory
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, prev
    return prev[n]


def _normalize(text: str) -> str:
    """Normalize text for comparison: strip whitespace."""
    return text.strip() if text else ""


# ── ExactMatchMetric ────────────────────────────────────────────────────────

class ExactMatchMetric:
    """Compares expected and actual output after whitespace normalization.

    Returns 1.0 for exact match, 0.0 otherwise.
    """

    name = "exact_match"

    def __call__(self, example: EvalExample, result: EvalResult) -> list[EvalMetric]:
        expected = _normalize(example.expected_output or "")
        actual = _normalize(result.actual_output or "")
        passed = bool(expected and actual and expected == actual)
        return [
            EvalMetric(
                name=self.name,
                value=1.0 if passed else 0.0,
                threshold=0.5,
                passed=passed,
            )
        ]


# ── ToolCallAccuracyMetric ──────────────────────────────────────────────────

class ToolCallAccuracyMetric:
    """Measures precision of actual tool calls against expected ones.

    Each expected tool call is considered matched if the actual calls contain
    a tool call with the same name AND the same args dict.

    Score = matched_count / len(expected_tool_calls).
    Returns 1.0 if no expected calls (trivially correct).
    """

    name = "tool_call_accuracy"

    def __call__(self, example: EvalExample, result: EvalResult) -> list[EvalMetric]:
        expected = example.expected_tool_calls or []
        actual = result.actual_tool_calls or []

        if not expected:
            return [
                EvalMetric(
                    name=self.name,
                    value=1.0,
                    threshold=0.8,
                    passed=True,
                )
            ]

        matched = 0
        for expected_call in expected:
            for actual_call in actual:
                if expected_call.name == actual_call.name and expected_call.args == actual_call.args:
                    matched += 1
                    break

        score = matched / len(expected)
        return [
            EvalMetric(
                name=self.name,
                value=score,
                threshold=0.8,
                passed=score >= 0.8,
            )
        ]


# ── TrajectoryAccuracyMetric ────────────────────────────────────────────────

class TrajectoryAccuracyMetric:
    """Measures how well the actual agent trajectory matches the expected one.

    Uses Longest Common Subsequence (LCS) to compute similarity:
        score = len(LCS) / len(expected_trajectory)

    Returns 1.0 if no expected trajectory (trivially correct).
    Returns 1.0 if both are empty.
    """

    name = "trajectory_accuracy"

    def __call__(self, example: EvalExample, result: EvalResult) -> list[EvalMetric]:
        expected = example.expected_trajectory or []
        actual = result.actual_trajectory or []

        if not expected:
            return [
                EvalMetric(
                    name=self.name,
                    value=1.0,
                    threshold=0.8,
                    passed=True,
                )
            ]

        if not actual:
            return [
                EvalMetric(
                    name=self.name,
                    value=0.0,
                    threshold=0.8,
                    passed=False,
                )
            ]

        lcs_len = _longest_common_subsequence(expected, actual)
        score = lcs_len / len(expected)
        return [
            EvalMetric(
                name=self.name,
                value=score,
                threshold=0.8,
                passed=score >= 0.8,
            )
        ]


# ── LatencyMetric ───────────────────────────────────────────────────────────

class LatencyMetric:
    """Reports the observed latency and checks it against a threshold.

    Passes if latency_ms is available and <= max_threshold_ms.
    """

    name = "latency"

    def __init__(self, max_threshold_ms: float = 5000.0) -> None:
        self.max_threshold_ms = max_threshold_ms

    def __call__(self, example: EvalExample, result: EvalResult) -> list[EvalMetric]:
        if result.latency_ms is None:
            return [
                EvalMetric(
                    name=self.name,
                    value=0.0,
                    threshold=self.max_threshold_ms,
                    passed=False,
                )
            ]

        passed = result.latency_ms <= self.max_threshold_ms
        return [
            EvalMetric(
                name=self.name,
                value=result.latency_ms,
                threshold=self.max_threshold_ms,
                passed=passed,
            )
        ]


# ── TokenUsageMetric ────────────────────────────────────────────────────────

class TokenUsageMetric:
    """Reports the total token usage and checks it against a threshold.

    Passes if tokens_used is available and <= max_threshold.
    """

    name = "token_usage"

    def __init__(self, max_threshold: int = 8000) -> None:
        self.max_threshold = max_threshold

    def __call__(self, example: EvalExample, result: EvalResult) -> list[EvalMetric]:
        if result.tokens_used is None:
            return [
                EvalMetric(
                    name=self.name,
                    value=0.0,
                    threshold=self.max_threshold,
                    passed=False,
                )
            ]

        passed = result.tokens_used <= self.max_threshold
        return [
            EvalMetric(
                name=self.name,
                value=float(result.tokens_used),
                threshold=float(self.max_threshold),
                passed=passed,
            )
        ]


# ── compute_metrics ─────────────────────────────────────────────────────────

def compute_metrics(
    example: EvalExample,
    result: EvalResult,
    config: EvalMetricsConfig,
) -> list[EvalMetric]:
    """Compute all enabled metrics for a single example/result pair.

    Args:
        example: The evaluation example (contains expected values).
        result: The actual result from the agent run.
        config: Which metrics to compute.

    Returns:
        Flat list of ``EvalMetric`` objects (one entry per enabled metric).
    """
    metrics: list[EvalMetric] = []

    if config.exact_match:
        metrics.extend(ExactMatchMetric()(example, result))

    if config.tool_call_accuracy:
        metrics.extend(ToolCallAccuracyMetric()(example, result))

    if config.trajectory_accuracy:
        metrics.extend(TrajectoryAccuracyMetric()(example, result))

    if config.latency:
        metrics.extend(LatencyMetric()(example, result))

    if config.token_usage:
        metrics.extend(TokenUsageMetric()(example, result))

    # semantic_similarity deferred — requires LLM-as-judge

    return metrics
