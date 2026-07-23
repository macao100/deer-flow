"""Tests for MCPToolAdapter — schema mapping, tool creation, metadata injection."""

import pytest
from langchain_core.tools import StructuredTool
from mcp.types import Tool as MCPTool
from pydantic import BaseModel

from deerflow.mcp.adapter import MCPToolAdapter


class TestJsonSchemaToPydantic:
    """JSON Schema → Pydantic model conversion."""

    def test_simple_types(self):
        """Map string, integer, number, boolean to Python types."""
        schema: dict = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "A name"},
                "count": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
            },
            "required": ["name", "count"],
        }
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "test_tool")

        # Required fields
        instance = model(name="hello", count=42)
        assert instance.name == "hello"
        assert instance.count == 42
        assert instance.score is None  # optional, not provided

        # Optional fields can be set
        instance2 = model(name="x", count=1, score=3.14, active=True)
        assert instance2.score == 3.14
        assert instance2.active is True

    def test_no_properties(self):
        """Schema with no properties produces an empty model."""
        schema: dict = {"type": "object", "properties": {}}
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "no_args")
        instance = model()
        assert instance is not None

    def test_optional_fields(self):
        """Fields not in 'required' default to None."""
        schema: dict = {
            "type": "object",
            "properties": {
                "required_field": {"type": "string"},
                "optional_field": {"type": "string"},
            },
            "required": ["required_field"],
        }
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "opt")
        instance = model(required_field="x")
        assert instance.required_field == "x"
        assert instance.optional_field is None

    def test_non_object_root_raises(self):
        """Non-object root type raises ValueError."""
        schema: dict = {"type": "string"}
        with pytest.raises(ValueError, match="'object'"):
            MCPToolAdapter.json_schema_to_pydantic(schema, "bad")

    def test_array_type(self):
        """Array with items resolves to list[item_type]."""
        schema: dict = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["tags"],
        }
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "arr")
        instance = model(tags=["a", "b"])
        assert instance.tags == ["a", "b"]

    def test_array_without_items(self):
        """Array without items definition resolves to plain list."""
        schema: dict = {
            "type": "object",
            "properties": {
                "data": {"type": "array"},
            },
            "required": ["data"],
        }
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "arr2")
        instance = model(data=[1, 2, 3])
        assert instance.data == [1, 2, 3]

    def test_nested_object(self):
        """Nested object with properties creates a nested model."""
        schema: dict = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "title": "UserInfo",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                    "required": ["name"],
                },
            },
            "required": ["user"],
        }
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "nested")
        instance = model(user={"name": "Alice", "age": 30})
        # Nested objects become Pydantic models — attribute access, not dict
        assert instance.user.name == "Alice"  # type: ignore[union-attr]

    def test_anyof_union(self):
        """anyOf creates a Union type."""
        schema: dict = {
            "type": "object",
            "properties": {
                "result": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "integer"},
                    ],
                },
            },
            "required": ["result"],
        }
        model = MCPToolAdapter.json_schema_to_pydantic(schema, "union_test")
        # Accept string
        instance = model(result="ok")
        assert instance.result == "ok"
        # Accept integer
        instance2 = model(result=42)
        assert instance2.result == 42


class TestToLangchainTool:
    """MCPTool → LangChain StructuredTool conversion."""

    @pytest.fixture
    def sample_mcp_tool(self):
        """A minimal MCP Tool descriptor."""
        return MCPTool(
            name="search",
            description="Search the web",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        )

    @pytest.fixture
    def sample_connection(self):
        """Minimal connection params for testing."""
        return {"transport": "stdio", "command": "echo", "args": []}

    def test_creates_structured_tool(self, sample_mcp_tool, sample_connection):
        """Tool is created with correct type."""
        tool = MCPToolAdapter.to_langchain_tool(sample_mcp_tool, "test-srv", sample_connection)
        assert isinstance(tool, StructuredTool)

    def test_name_prefix(self, sample_mcp_tool, sample_connection):
        """Tool name is prefixed with server_name."""
        tool = MCPToolAdapter.to_langchain_tool(sample_mcp_tool, "test-srv", sample_connection)
        assert tool.name == "test-srv_search"

    def test_description_fallback(self, sample_connection):
        """Tool without description gets a fallback."""
        tool_desc = MCPTool(name="foo", description="", inputSchema={"type": "object", "properties": {}})
        tool = MCPToolAdapter.to_langchain_tool(tool_desc, "srv", sample_connection)
        assert "foo" in tool.description

    def test_args_schema(self, sample_mcp_tool, sample_connection):
        """Tool has a Pydantic args_schema built from inputSchema."""
        tool = MCPToolAdapter.to_langchain_tool(sample_mcp_tool, "test-srv", sample_connection)
        assert tool.args_schema is not None
        assert issubclass(tool.args_schema, BaseModel)

    def test_response_format(self, sample_mcp_tool, sample_connection):
        """Tool uses content_and_artifact response format."""
        tool = MCPToolAdapter.to_langchain_tool(sample_mcp_tool, "test-srv", sample_connection)
        assert tool.response_format == "content_and_artifact"

    def test_no_input_schema(self, sample_connection):
        """Tool with empty inputSchema gets an empty args_schema."""
        tool_no_schema = MCPTool(name="no_args", description="No args tool", inputSchema={"type": "object", "properties": {}})
        tool = MCPToolAdapter.to_langchain_tool(tool_no_schema, "srv", sample_connection)
        assert tool.args_schema is not None
        instance = tool.args_schema()
        assert instance is not None


class TestInjectMetadata:
    """Metadata injection into BaseTool."""

    def test_inject_metadata_sets_flags(self):
        """Metadata keys are set correctly."""
        from langchain_core.tools import tool

        @tool
        def dummy_tool(x: str) -> str:
            """A dummy."""
            return x

        MCPToolAdapter.inject_metadata(dummy_tool, "test-server", "test-tool")
        assert dummy_tool.metadata["deerflow_mcp"] is True
        assert dummy_tool.metadata["mcp_server"] == "test-server"
        assert dummy_tool.metadata["mcp_tool_name"] == "test-tool"

    def test_inject_metadata_preserves_existing(self):
        """Existing metadata keys are preserved."""
        from langchain_core.tools import tool

        @tool
        def dummy_tool(x: str) -> str:
            """A dummy."""
            return x

        dummy_tool.metadata = {"existing": "value"}
        MCPToolAdapter.inject_metadata(dummy_tool, "srv", "tool")
        assert dummy_tool.metadata["existing"] == "value"
        assert dummy_tool.metadata["deerflow_mcp"] is True
        assert dummy_tool.metadata["mcp_server"] == "srv"
