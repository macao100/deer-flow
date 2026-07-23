"""Evaluation runner — executes datasets against agent models.

The ``EvalRunner`` takes a model name and evaluation configuration, runs each
example through a ``DeerFlowClient`` instance, captures outputs (text, tool
calls, trajectory, latency, tokens), and computes configured metrics.

Usage::

    from deerflow.evaluation import EvalRunner, DatasetRegistry

    registry = DatasetRegistry(".deer-flow/evaluation/datasets")
    dataset = registry.get_dataset("my-benchmark")

    runner = EvalRunner(model_name="deepseek-v4-pro")
    eval_run = runner.run_dataset(dataset)
    print(eval_run.summary)
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime

from deerflow.config.app_config import get_app_config
from deerflow.config.evaluation_config import EvaluationConfig
from deerflow.evaluation.metrics import (
    compute_metrics,
)
from deerflow.evaluation.models import (
    EvalDataset,
    EvalExample,
    EvalResult,
    EvalRun,
    ToolCallSpec,
)

logger = logging.getLogger(__name__)


class EvalRunner:
    """Runs evaluation datasets against a specified model.

    Each example is executed sequentially through an embedded
    ``DeerFlowClient``.  Outputs (text, tool calls, trajectory, latency,
    token usage) are captured from the streaming response and fed into the
    configured metrics.

    Parameters:
        model_name: Name of the model to evaluate (must exist in config.yaml).
        config: Evaluation configuration. Uses ``get_app_config().evaluation``
            when not provided.
    """

    def __init__(
        self,
        model_name: str,
        config: EvaluationConfig | None = None,
    ) -> None:
        self._model_name = model_name
        self._config = config or get_app_config().evaluation

    # ── Public API ──────────────────────────────────────────────────────

    def run_dataset(self, dataset: EvalDataset) -> EvalRun:
        """Execute all examples in *dataset* and return a completed run.

        This is a synchronous method — each example is executed
        sequentially via ``_run_example``.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)
        logger.info(
            "Starting eval run %s: dataset='%s' model='%s' (%d examples)",
            run_id,
            dataset.name,
            self._model_name,
            len(dataset.examples),
        )

        results: list[EvalResult] = []
        for example in dataset.examples:
            try:
                result = self._run_example(example)
                results.append(result)
            except Exception:
                logger.exception("Unexpected error evaluating example '%s'", example.id)
                results.append(
                    EvalResult(
                        example_id=example.id,
                        passed=False,
                        score=0.0,
                        error="Unexpected error: see logs for details",
                    )
                )

        completed_at = datetime.now(UTC)
        summary = self._build_summary(results)

        run = EvalRun(
            id=run_id,
            dataset_id=dataset.id,
            model_name=self._model_name,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            results=results,
            summary=summary,
        )
        logger.info(
            "Eval run %s completed: %d/%d passed (%.1f%%)",
            run_id,
            summary.get("passed", 0),
            summary.get("total", 0),
            summary.get("pass_rate", 0.0) * 100,
        )
        return run

    # ── Internal ────────────────────────────────────────────────────────

    def _run_example(self, example: EvalExample) -> EvalResult:
        """Execute a single example and compute metrics."""
        from deerflow.client import DeerFlowClient

        client = DeerFlowClient(
            model_name=self._model_name,
            thinking_enabled=False,
            subagent_enabled=False,
        )

        t0 = time.perf_counter()
        actual_output: str | None = None
        actual_tool_calls: list[ToolCallSpec] = []
        actual_trajectory: list[str] = []
        tokens_used: int | None = None
        error: str | None = None

        try:
            # Track trajectory from the stream events
            current_turn: list[str] = []

            for event in client.stream(example.input):
                etype = event.type
                edata = event.data

                if etype == "messages-tuple":
                    msg_type = edata.get("type", "")
                    if msg_type == "ai":
                        # Record an "agent" turn if not already recorded for this sequence
                        if not current_turn or current_turn[-1] != "agent":
                            current_turn.append("agent")
                        # Capture tool calls
                        tcs = edata.get("tool_calls")
                        if tcs:
                            for tc in tcs:
                                actual_tool_calls.append(
                                    ToolCallSpec(
                                        name=tc.get("name", ""),
                                        args=tc.get("args", {}),
                                    )
                                )
                    elif msg_type == "tool":
                        if not current_turn or current_turn[-1] != "tools":
                            current_turn.append("tools")

                elif etype == "values":
                    messages = edata.get("messages", [])
                    # Extract final AI text from the last AI message in values snapshot
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get("type") == "ai":
                            actual_output = msg.get("content") or actual_output
                            break
                    # Track trajectory from the values snapshot
                    for msg in messages:
                        if isinstance(msg, dict):
                            mt = msg.get("type", "")
                            if mt == "ai":
                                if not current_turn or current_turn[-1] != "agent":
                                    current_turn.append("agent")
                            elif mt == "tool":
                                if not current_turn or current_turn[-1] != "tools":
                                    current_turn.append("tools")

                elif etype == "end":
                    usage = edata.get("usage", {})
                    if usage:
                        tokens_used = usage.get("total_tokens", 0)

            actual_trajectory = current_turn

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            logger.warning("Error running example '%s': %s", example.id, error)

        latency_ms = (time.perf_counter() - t0) * 1000.0

        result = EvalResult(
            example_id=example.id,
            passed=False,  # updated after metrics
            score=0.0,  # updated after metrics
            actual_output=actual_output,
            actual_tool_calls=actual_tool_calls,
            actual_trajectory=actual_trajectory,
            metrics=[],
            error=error,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

        # Compute metrics
        metrics = compute_metrics(example, result, self._config.metrics)
        result = result.model_copy(update={"metrics": metrics})

        # Aggregate score and pass/fail
        passed = all(m.passed for m in metrics if m.passed is not None)
        score = sum(m.value for m in metrics) / max(len(metrics), 1)

        return result.model_copy(update={"passed": passed, "score": score})

    @staticmethod
    def _build_summary(results: list[EvalResult]) -> dict:
        """Build aggregated summary statistics from a list of results."""
        total = len(results)
        if total == 0:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0}

        passed_count = sum(1 for r in results if r.passed)
        failed_count = total - passed_count
        error_count = sum(1 for r in results if r.error)

        # Aggregate per-metric stats
        metric_values: dict[str, list[float]] = {}
        for r in results:
            for m in r.metrics:
                metric_values.setdefault(m.name, []).append(m.value)

        metric_summary = {}
        for name, values in metric_values.items():
            metric_summary[name] = {
                "count": len(values),
                "avg": sum(values) / len(values) if values else 0.0,
                "min": min(values) if values else 0.0,
                "max": max(values) if values else 0.0,
            }

        # Latency stats
        latencies = [r.latency_ms for r in results if r.latency_ms is not None]
        latency_avg = sum(latencies) / len(latencies) if latencies else 0.0

        # Token stats
        token_counts = [r.tokens_used for r in results if r.tokens_used is not None]
        tokens_avg = sum(token_counts) / len(token_counts) if token_counts else 0.0

        return {
            "total": total,
            "passed": passed_count,
            "failed": failed_count,
            "errors": error_count,
            "pass_rate": passed_count / total,
            "avg_latency_ms": round(latency_avg, 2),
            "avg_tokens": round(tokens_avg, 1),
            "metrics": metric_summary,
        }
