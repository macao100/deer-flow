"""CLI entry point for the evaluation pipeline.

Usage::

    # List datasets
    python -m deerflow.evaluation datasets list

    # Import a dataset from a YAML file
    python -m deerflow.evaluation datasets create --file path/to/dataset.yaml

    # Run an evaluation
    python -m deerflow.evaluation run --dataset <id> --model <name>

    # Show a run result
    python -m deerflow.evaluation runs show --id <run_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def _get_registry():
    """Lazy-import and return a DatasetRegistry."""
    from deerflow.config.app_config import get_app_config
    from deerflow.evaluation.registry import DatasetRegistry

    app_config = get_app_config()
    return DatasetRegistry(app_config.evaluation.datasets_dir)


def _cmd_datasets_list(_args: argparse.Namespace) -> None:
    """List all datasets in the registry."""
    registry = _get_registry()
    datasets = registry.list_datasets()
    if not datasets:
        print("No datasets found.")
        return
    for ds in datasets:
        print(f"  {ds.id:30s}  {ds.name:40s}  {len(ds.examples)} examples")


def _cmd_datasets_create(args: argparse.Namespace) -> None:
    """Create a dataset from a YAML file."""
    from deerflow.evaluation.models import EvalDataset

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    with open(file_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    dataset = EvalDataset.model_validate(data)
    registry = _get_registry()
    saved_path = registry.save_dataset(dataset)
    print(f"Dataset '{dataset.name}' ({dataset.id}) created at {saved_path}")


def _cmd_run(args: argparse.Namespace) -> None:
    """Run an evaluation against a dataset."""
    from deerflow.config.app_config import get_app_config
    from deerflow.evaluation.runner import EvalRunner

    registry = _get_registry()
    dataset = registry.get_dataset(args.dataset)
    if dataset is None:
        print(f"Error: dataset '{args.dataset}' not found.", file=sys.stderr)
        sys.exit(1)

    app_config = get_app_config()
    runner = EvalRunner(
        model_name=args.model,
        config=app_config.evaluation,
    )
    print(f"Running evaluation: dataset='{dataset.name}' model='{args.model}' ({len(dataset.examples)} examples)...")
    eval_run = runner.run_dataset(dataset)

    # Print summary
    s = eval_run.summary
    print(f"\nResults: {s.get('passed', 0)}/{s.get('total', 0)} passed ({s.get('pass_rate', 0.0) * 100:.1f}%)")
    print(f"  Errors: {s.get('errors', 0)}")
    print(f"  Avg latency: {s.get('avg_latency_ms', 0)} ms")
    print(f"  Avg tokens:  {s.get('avg_tokens', 0)}")

    metrics_summary = s.get("metrics", {})
    if metrics_summary:
        print("\nPer-metric averages:")
        for name, stats in metrics_summary.items():
            print(f"  {name}: avg={stats['avg']:.3f}  min={stats['min']:.3f}  max={stats['max']:.3f}")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            eval_run.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(f"\nFull results written to {out_path}")


def _cmd_runs_show(args: argparse.Namespace) -> None:
    """Show details of a specific run (from a saved JSON file)."""
    file_path = Path(args.id)
    if not file_path.exists():
        print(f"Error: run file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    from deerflow.evaluation.models import EvalRun

    run = EvalRun.model_validate(json.loads(file_path.read_text(encoding="utf-8")))
    s = run.summary
    print(f"Run:       {run.id}")
    print(f"Dataset:   {run.dataset_id}")
    print(f"Model:     {run.model_name}")
    print(f"Status:    {run.status}")
    print(f"Started:   {run.started_at}")
    print(f"Completed: {run.completed_at}")
    print(f"\nResults: {s.get('passed', 0)}/{s.get('total', 0)} passed ({s.get('pass_rate', 0.0) * 100:.1f}%)")
    print(f"  Errors: {s.get('errors', 0)}")
    print(f"  Avg latency: {s.get('avg_latency_ms', 0)} ms")
    print(f"  Avg tokens:  {s.get('avg_tokens', 0)}")

    for r in run.results:
        status = "PASS" if r.passed else "FAIL"
        err = f"  ERROR: {r.error}" if r.error else ""
        print(f"  [{status}] {r.example_id}  score={r.score:.2f}  latency={r.latency_ms:.0f}ms{err}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m deerflow.evaluation",
        description="DeerFlow JE — Evaluation Pipeline CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # datasets list
    sub.add_parser("datasets-list", help="List all evaluation datasets").set_defaults(func=_cmd_datasets_list)

    # datasets create
    p_create = sub.add_parser("datasets-create", help="Create a dataset from a YAML file")
    p_create.add_argument("--file", required=True, help="Path to YAML dataset file")
    p_create.set_defaults(func=_cmd_datasets_create)

    # run
    p_run = sub.add_parser("run", help="Run an evaluation")
    p_run.add_argument("--dataset", required=True, help="Dataset ID to evaluate against")
    p_run.add_argument("--model", required=True, help="Model name to evaluate")
    p_run.add_argument("--output", "-o", default=None, help="Optional JSON output path for full results")
    p_run.set_defaults(func=_cmd_run)

    # runs show
    p_show = sub.add_parser("runs-show", help="Show a saved run result")
    p_show.add_argument("--id", required=True, dest="id", help="Path to a saved run JSON file")
    p_show.set_defaults(func=_cmd_runs_show)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
