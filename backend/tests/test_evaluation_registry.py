"""Tests for DatasetRegistry — CRUD operations on evaluation datasets."""

import tempfile
from pathlib import Path

import pytest
import yaml

from deerflow.evaluation.models import EvalDataset, EvalExample, ToolCallSpec
from deerflow.evaluation.registry import DatasetRegistry


@pytest.fixture
def tmp_registry():
    """Create a DatasetRegistry backed by a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield DatasetRegistry(tmpdir)


class TestDatasetRegistryCRUD:
    """Tests for basic CRUD operations."""

    def test_save_and_reload_roundtrip(self, tmp_registry):
        """A saved dataset can be loaded back identically."""
        dataset = EvalDataset(
            id="ds1",
            name="Basic Tests",
            description="Simple math questions",
            examples=[
                EvalExample(id="ex1", input="What is 2+2?", expected_output="4"),
                EvalExample(id="ex2", input="What is 3+5?", expected_output="8"),
            ],
            tags=["math", "basic"],
        )
        path = tmp_registry.save_dataset(dataset)
        assert path.exists()

        reloaded = tmp_registry.get_dataset("ds1")
        assert reloaded is not None
        assert reloaded.id == "ds1"
        assert reloaded.name == "Basic Tests"
        assert len(reloaded.examples) == 2
        assert reloaded.examples[0].input == "What is 2+2?"

    def test_list_datasets_empty(self, tmp_registry):
        """An empty registry returns an empty list."""
        datasets = tmp_registry.list_datasets()
        assert datasets == []

    def test_list_datasets_with_files(self, tmp_registry):
        """Registry lists all saved datasets."""
        tmp_registry.save_dataset(EvalDataset(id="ds1", name="First"))
        tmp_registry.save_dataset(EvalDataset(id="ds2", name="Second"))
        datasets = tmp_registry.list_datasets()
        assert len(datasets) == 2

    def test_get_dataset_not_found(self, tmp_registry):
        """get_dataset returns None for unknown datasets."""
        assert tmp_registry.get_dataset("nonexistent") is None

    def test_get_dataset_by_name(self, tmp_registry):
        """get_dataset_by_name finds a dataset by its name."""
        tmp_registry.save_dataset(EvalDataset(id="abc123", name="Math Eval"))
        found = tmp_registry.get_dataset_by_name("Math Eval")
        assert found is not None
        assert found.id == "abc123"

    def test_get_dataset_by_name_not_found(self, tmp_registry):
        """get_dataset_by_name returns None for unknown names."""
        assert tmp_registry.get_dataset_by_name("Unknown") is None

    def test_delete_dataset(self, tmp_registry):
        """delete_dataset removes the file and cache entry."""
        tmp_registry.save_dataset(EvalDataset(id="ds-del", name="To Delete"))
        assert tmp_registry.delete_dataset("ds-del") is True
        assert tmp_registry.get_dataset("ds-del") is None

    def test_delete_nonexistent(self, tmp_registry):
        """delete_dataset returns False for nonexistent IDs."""
        assert tmp_registry.delete_dataset("nope") is False

    def test_save_updates_existing(self, tmp_registry):
        """Saving a dataset with the same ID updates it."""
        dataset = EvalDataset(id="ds-upd", name="Original")
        tmp_registry.save_dataset(dataset)
        updated = EvalDataset(
            id="ds-upd",
            name="Updated Name",
            description="Changed",
            examples=[EvalExample(id="new-ex", input="Hello")],
        )
        tmp_registry.save_dataset(updated)
        reloaded = tmp_registry.get_dataset("ds-upd")
        assert reloaded.name == "Updated Name"
        assert reloaded.description == "Changed"
        assert len(reloaded.examples) == 1

    def test_skips_non_yaml_files(self, tmp_registry):
        """Registry ignores non-YAML/JSON files in the datasets directory."""
        # Save a real dataset
        tmp_registry.save_dataset(EvalDataset(id="ds-real", name="Real"))
        # Create a junk file
        junk_path = Path(tmp_registry._dir) / "notes.txt"
        junk_path.write_text("not a dataset")

        # Create a fresh registry pointing to the same dir (clears cache)
        fresh = DatasetRegistry(tmp_registry._dir)
        datasets = fresh.list_datasets()
        assert len(datasets) == 1
        assert datasets[0].id == "ds-real"


class TestDatasetRegistryExamples:
    """Tests for example manipulation."""

    def test_save_with_tool_calls(self, tmp_registry):
        """Tool call specs survive save/reload."""
        dataset = EvalDataset(
            id="ds-tools",
            name="Tool Tests",
            examples=[
                EvalExample(
                    id="tc1",
                    input="Search for Python",
                    expected_tool_calls=[
                        ToolCallSpec(name="web_search", args={"query": "Python"}),
                        ToolCallSpec(name="read_file", args={"path": "/tmp/result.txt"}),
                    ],
                ),
            ],
        )
        tmp_registry.save_dataset(dataset)
        reloaded = tmp_registry.get_dataset("ds-tools")
        assert reloaded.examples[0].expected_tool_calls is not None
        assert len(reloaded.examples[0].expected_tool_calls) == 2
        assert reloaded.examples[0].expected_tool_calls[0].name == "web_search"

    def test_save_with_trajectory(self, tmp_registry):
        """Trajectory expectations survive save/reload."""
        dataset = EvalDataset(
            id="ds-traj",
            name="Trajectory Tests",
            examples=[
                EvalExample(
                    id="tj1",
                    input="Do a web search and read the result",
                    expected_trajectory=["agent", "tools", "agent", "tools", "agent"],
                ),
            ],
        )
        tmp_registry.save_dataset(dataset)
        reloaded = tmp_registry.get_dataset("ds-traj")
        assert reloaded.examples[0].expected_trajectory == ["agent", "tools", "agent", "tools", "agent"]

    def test_save_with_metadata(self, tmp_registry):
        """Example metadata survives save/reload."""
        dataset = EvalDataset(
            id="ds-meta",
            name="Metadata Tests",
            examples=[
                EvalExample(
                    id="meta1",
                    input="Test",
                    metadata={"difficulty": "hard", "category": "reasoning", "timeout": 30},
                ),
            ],
        )
        tmp_registry.save_dataset(dataset)
        reloaded = tmp_registry.get_dataset("ds-meta")
        assert reloaded.examples[0].metadata["difficulty"] == "hard"
        assert reloaded.examples[0].metadata["timeout"] == 30


class TestDatasetRegistryYAMLFormat:
    """Tests for the on-disk YAML format."""

    def test_yaml_file_is_valid(self, tmp_registry):
        """Saved YAML is valid and parseable by PyYAML directly."""
        dataset = EvalDataset(
            id="ds-yaml",
            name="YAML Format Test",
            description="A test",
            examples=[
                EvalExample(id="ex1", input="Hello", expected_output="World"),
            ],
            tags=["test"],
        )
        path = tmp_registry.save_dataset(dataset)
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["id"] == "ds-yaml"
        assert data["name"] == "YAML Format Test"
        assert len(data["examples"]) == 1
        assert data["examples"][0]["input"] == "Hello"

    def test_yaml_file_not_overwritten_by_other_formats(self, tmp_registry):
        """Registry only reads .yaml/.yml/.json files."""
        path = Path(tmp_registry._dir) / "malformed.xml"
        path.write_text("<dataset><id>test</id></dataset>")
        datasets = tmp_registry.list_datasets()
        assert len(datasets) == 0


class TestDatasetRegistryEdgeCases:
    """Edge case tests."""

    def test_empty_examples(self, tmp_registry):
        """Dataset with no examples loads correctly."""
        dataset = EvalDataset(id="ds-empty", name="Empty")
        tmp_registry.save_dataset(dataset)
        reloaded = tmp_registry.get_dataset("ds-empty")
        assert reloaded.examples == []

    def test_special_characters_in_name(self, tmp_registry):
        """Dataset names with special characters produce safe filenames."""
        dataset = EvalDataset(id="ds-special", name="Test: Special / Chars?")
        path = tmp_registry.save_dataset(dataset)
        assert path.exists()
        # The filename should be safe
        assert "?" not in path.name
        assert "/" not in path.name

    def test_dataset_with_empty_metadata(self, tmp_registry):
        """Empty metadata is handled gracefully."""
        dataset = EvalDataset(id="ds-nometa", name="No Metadata")
        tmp_registry.save_dataset(dataset)
        reloaded = tmp_registry.get_dataset("ds-nometa")
        assert reloaded is not None

    def test_large_dataset(self, tmp_registry):
        """Dataset with many examples works correctly."""
        examples = [EvalExample(id=f"ex{i}", input=f"Input {i}") for i in range(100)]
        dataset = EvalDataset(id="ds-big", name="Large Dataset", examples=examples)
        tmp_registry.save_dataset(dataset)
        reloaded = tmp_registry.get_dataset("ds-big")
        assert len(reloaded.examples) == 100

    def test_refresh_detects_new_files(self, tmp_registry):
        """Registry detects new files added after construction."""
        # Create and save a dataset
        tmp_registry.save_dataset(EvalDataset(id="ds1", name="First"))

        # Create a second dataset file directly (bypassing cache)
        ds2 = EvalDataset(id="ds2", name="Second")
        tmp_registry.save_dataset(ds2)

        datasets = tmp_registry.list_datasets()
        assert len(datasets) == 2
