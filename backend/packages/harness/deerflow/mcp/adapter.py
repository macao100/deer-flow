"""MCP tool adapter — converts MCP Tool descriptors to LangChain StructuredTool.

Provides JSON Schema → Pydantic type mapping, metadata injection for
tracing, and session-pool-backed tool execution.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from mcp.types import Tool as MCPTool
from pydantic import BaseModel, Field, create_model

from deerflow.tools.mcp_metadata import MCP_TOOL_METADATA_KEY

logger = logging.getLogger(__name__)

# Mapping of JSON Schema types to Python types
_JSON_TO_PYTHON: dict[str, type] = {
    "string": str,
    "number": float,
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}


class MCPToolAdapter:
    """Converts MCP Tool descriptors to LangChain StructuredTool.

    Handles JSON Schema → Pydantic model creation, session-pool-backed
    execution, sync wrapper attachment, and tracing-metadata injection.
    """

    # ── Schema mapping ──────────────────────────────────────────────

    @staticmethod
    def json_schema_to_pydantic(
        schema: dict[str, Any],
        tool_name: str,
    ) -> type[BaseModel]:
        """Convert a JSON Schema object definition to a Pydantic BaseModel.

        Args:
            schema: JSON Schema dict (must have ``type="object"`` and ``properties``).
            tool_name: Used to name the generated model class.

        Returns:
            A dynamically created Pydantic model class.

        Raises:
            ValueError: If the schema is not of type ``object``.
        """
        if schema.get("type") != "object":
            raise ValueError(f"Schema root type must be 'object', got '{schema.get('type')}'")

        properties: dict[str, dict] = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        if not properties:
            # Return an empty model — the tool takes no arguments.
            safe_name = tool_name.replace("-", "_").replace(".", "_")
            return create_model(f"{safe_name}_args", __base__=BaseModel)

        fields: dict[str, tuple[type, Any]] = {}
        for prop_name, prop_schema in properties.items():
            field_type = MCPToolAdapter._resolve_json_type(prop_schema)
            is_required = prop_name in required
            description = prop_schema.get("description", "")

            if is_required:
                fields[prop_name] = (field_type, Field(..., description=description))
            else:
                fields[prop_name] = (field_type | None, Field(default=None, description=description))

        safe_name = tool_name.replace("-", "_").replace(".", "_")
        return create_model(f"{safe_name}_args", **fields, __base__=BaseModel)  # type: ignore[call-overload]

    @staticmethod
    def _resolve_json_type(prop_schema: dict[str, Any]) -> type:
        """Resolve a JSON Schema property definition to a Python type.

        Handles ``type``, ``anyOf``/``oneOf`` for unions, ``array`` with
        ``items``, and nested ``object`` schemas.
        """
        # Union types via anyOf / oneOf
        if "anyOf" in prop_schema or "oneOf" in prop_schema:
            alternatives = prop_schema.get("anyOf") or prop_schema.get("oneOf") or []
            resolved: list[type] = []
            for alt in alternatives:
                if isinstance(alt, dict):
                    resolved.append(MCPToolAdapter._resolve_json_type(alt))
            if not resolved:
                return Any  # type: ignore[return-value]
            if len(resolved) == 1:
                return resolved[0]
            # Build a Union type — order doesn't matter for validation

            union: Any = resolved[0]
            for t in resolved[1:]:
                union = union | t
            return union

        json_type = prop_schema.get("type")

        # Array with items
        if json_type == "array":
            items = prop_schema.get("items")
            if isinstance(items, dict):
                item_type = MCPToolAdapter._resolve_json_type(items)
                return list[item_type]  # type: ignore[return-value]
            return list

        # Nested object
        if json_type == "object" and "properties" in prop_schema:
            # Use a synthetic name since nested objects are anonymous
            inner_name = prop_schema.get("title", "nested")
            return MCPToolAdapter.json_schema_to_pydantic(
                prop_schema,
                f"_{inner_name}",
            )

        # Simple types
        if json_type in _JSON_TO_PYTHON:
            return _JSON_TO_PYTHON[json_type]

        # Fallback for untyped or unknown schemas
        return Any  # type: ignore[return-value]

    # ── Tool creation ────────────────────────────────────────────────

    @staticmethod
    def to_langchain_tool(
        mcp_tool: MCPTool,
        server_name: str,
        connection_params: dict[str, Any],
    ) -> StructuredTool:
        """Convert an MCP Tool descriptor to a LangChain StructuredTool.

        The resulting tool uses :class:`MCPSessionPool` for persistent
        sessions, supports ``content_and_artifact`` responses, and carries
        tracing metadata (``deerflow_mcp``, ``mcp_server``, ``mcp_tool_name``).

        Args:
            mcp_tool: Raw MCP tool descriptor from tool discovery.
            server_name: Server name for name prefixing and session scoping.
            connection_params: Connection dict (transport, command, args, etc.).

        Returns:
            A fully configured StructuredTool.
        """
        from deerflow.mcp.session_pool import get_session_pool
        from deerflow.tools.sync import make_sync_tool_wrapper

        # Build the args_schema from the MCP tool's inputSchema
        if mcp_tool.inputSchema:
            args_schema: type[BaseModel] = MCPToolAdapter.json_schema_to_pydantic(
                mcp_tool.inputSchema,
                mcp_tool.name,
            )
        else:
            args_schema = create_model(f"{mcp_tool.name}_args", __base__=BaseModel)

        pool = get_session_pool()

        async def _call_mcp_tool(
            runtime: Any = None,
            **arguments: Any,
        ) -> Any:
            """Execute the MCP tool via a pooled session, converting the result."""
            # Lazy import to avoid circular dependency at module level
            from deerflow.mcp.tools import _convert_call_tool_result, _extract_thread_id

            thread_id = _extract_thread_id(runtime)
            session = await pool.get_session(server_name, thread_id, connection_params)
            call_tool_result = await session.call_tool(mcp_tool.name, arguments)
            return _convert_call_tool_result(call_tool_result)

        tool_name = f"{server_name}_{mcp_tool.name}"
        tool = StructuredTool(
            name=tool_name,
            description=mcp_tool.description or f"MCP tool: {mcp_tool.name}",
            args_schema=args_schema,
            coroutine=_call_mcp_tool,
            response_format="content_and_artifact",
            metadata={},
        )

        # Attach sync wrapper for synchronous callers
        if tool.coroutine is not None and tool.func is None:
            tool.func = make_sync_tool_wrapper(tool.coroutine, tool.name)

        # Inject tracing metadata
        MCPToolAdapter.inject_metadata(tool, server_name, mcp_tool.name)

        return tool

    # ── Metadata injection ───────────────────────────────────────────

    @staticmethod
    def inject_metadata(
        tool: BaseTool,
        server_name: str,
        tool_name: str,
    ) -> BaseTool:
        """Inject tracing metadata into a tool.

        Sets ``tool.metadata`` to include:

        - ``deerflow_mcp``: True (used by deferred-tool system)
        - ``mcp_server``: originating server name
        - ``mcp_tool_name``: original MCP tool name (without server prefix)

        Args:
            tool: The LangChain tool to tag.
            server_name: Originating MCP server.
            tool_name: Original MCP tool name.

        Returns:
            The same tool (mutated in place, returned for chaining).
        """
        tool.metadata = {
            **(tool.metadata or {}),
            MCP_TOOL_METADATA_KEY: True,
            "mcp_server": server_name,
            "mcp_tool_name": tool_name,
        }
        return tool
