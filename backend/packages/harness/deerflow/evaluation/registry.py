"""Dataset registry for loading, saving, and managing evaluation datasets.

Each dataset is stored as a separate YAML file in ``datasets_dir``.
The registry maintains an in-memory cache with lazy loading.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from deerflow.evaluation.models import EvalDataset, EvalExample, ToolCallSpec

logger = logging.getLogger(__name__)


class DatasetRegistry:
    """Loads, saves, and manages evaluation datasets from a local directory.

    Each dataset is stored as a separate YAML file. The registry scans
    the directory on first access and caches results in memory.

    Typical usage::

        registry = DatasetRegistry(".deer-flow/evaluation/datasets")
        datasets = registry.list_datasets()
        dataset = registry.get_dataset("my-benchmark")
    """

    def __init__(self, datasets_dir: str | Path) -> None:
        self._dir = Path(datasets_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, EvalDataset] = {}
        self._scanned = False

    # ── Public API ──────────────────────────────────────────────────────

    def list_datasets(self) -> list[EvalDataset]:
        """Return all datasets currently in the registry."""
        self._ensure_scanned()
        return list(self._cache.values())

    def get_dataset(self, dataset_id: str) -> EvalDataset | None:
        """Retrieve a dataset by its id."""
        self._ensure_scanned()
        return self._cache.get(dataset_id)

    def get_dataset_by_name(self, name: str) -> EvalDataset | None:
        """Retrieve a dataset by its name (case-sensitive)."""
        self._ensure_scanned()
        for ds in self._cache.values():
            if ds.name == name:
                return ds
        return None

    def save_dataset(self, dataset: EvalDataset) -> Path:
        """Persist *dataset* to a YAML file. Returns the file path."""
        file_path = self._file_path_for(dataset.id, dataset.name)
        data = self._serialize_dataset(dataset)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        self._cache[dataset.id] = dataset
        logger.info("Saved dataset '%s' (%s) to %s", dataset.name, dataset.id, file_path)
        return file_path

    def delete_dataset(self, dataset_id: str) -> bool:
        """Remove a dataset by id. Returns ``True`` if it existed."""
        ds = self._cache.pop(dataset_id, None)
        if ds is None:
            return False
        file_path = self._file_path_for(ds.id, ds.name)
        if file_path.exists():
            file_path.unlink()
        logger.info("Deleted dataset '%s' (%s)", ds.name, dataset_id)
        return True

    # ── Internal ────────────────────────────────────────────────────────

    def _ensure_scanned(self) -> None:
        """Scan the datasets directory and populate the cache if not already done."""
        if self._scanned:
            return
        self._scanned = True
        if not self._dir.is_dir():
            return
        for path in sorted(self._dir.iterdir()):
            if path.suffix not in (".yaml", ".yml", ".json"):
                continue
            try:
                dataset = self._load_file(path)
                if dataset is not None and dataset.id not in self._cache:
                    self._cache[dataset.id] = dataset
            except Exception:
                logger.exception("Failed to load dataset file %s", path)

    def _load_file(self, path: Path) -> EvalDataset | None:
        """Load a single dataset file from disk."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if not isinstance(data, dict):
            return None

        examples_raw = data.get("examples", [])
        examples = [self._parse_example(ex) for ex in examples_raw]

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(UTC)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now(UTC)

        return EvalDataset.model_validate({
            "id": data.get("id", path.stem),
            "name": data.get("name", path.stem),
            "description": data.get("description", ""),
            "created_at": created_at,
            "updated_at": updated_at,
            "examples": [ex.model_dump() for ex in examples],
            "tags": data.get("tags", []),
        })

    @staticmethod
    def _parse_example(data: dict) -> EvalExample:
        """Parse a serialized example dict into an ``EvalExample``."""
        tool_calls_raw = data.get("expected_tool_calls") or []
        tool_calls = [
            ToolCallSpec(name=tc["name"], args=tc.get("args", {}))
            for tc in tool_calls_raw
        ]

        return EvalExample.model_validate({
            "id": data["id"],
            "input": data["input"],
            "expected_output": data.get("expected_output"),
            "expected_tool_calls": [tc.model_dump() for tc in tool_calls],
            "expected_trajectory": data.get("expected_trajectory"),
            "metadata": data.get("metadata", {}),
        })

    @staticmethod
    def _serialize_dataset(dataset: EvalDataset) -> dict:
        """Serialize a dataset to a dict ready for YAML dump."""
        return {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "created_at": dataset.created_at.isoformat(),
            "updated_at": dataset.updated_at.isoformat(),
            "tags": dataset.tags,
            "examples": [
                {
                    "id": ex.id,
                    "input": ex.input,
                    "expected_output": ex.expected_output,
                    "expected_tool_calls": [
                        {"name": tc.name, "args": tc.args}
                        for tc in (ex.expected_tool_calls or [])
                    ],
                    "expected_trajectory": ex.expected_trajectory,
                    "metadata": ex.metadata,
                }
                for ex in dataset.examples
            ],
        }

    def _file_path_for(self, dataset_id: str, dataset_name: str) -> Path:
        """Determine the YAML file path for a dataset."""
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in dataset_name)
        return self._dir / f"{safe_name or dataset_id}.yaml"
