"""Single source of truth for the MCP-tool metadata tag.

A tool is "MCP-sourced" when it carries the ``deerflow_mcp`` metadata flag.
The tag is *written* where MCP tools are loaded (``tools.py``) and *read* by
deferred-tool assembly (``tool_search.py``) and the agent build site
(``agent.py``). Keeping the key, the tagger, and the predicate here means the
magic string lives in exactly one place, and readers import a public predicate
instead of a private cross-module helper.

This is a leaf module by design: it depends only on ``BaseTool`` so that any
module (including the tool loader) can import it without an import cycle.
"""

from __future__ import annotations

from langchain.tools import BaseTool

MCP_TOOL_METADATA_KEY = "deerflow_mcp"


def tag_mcp_tool(tool: BaseTool, *, server_name: str | None = None, tool_name: str | None = None) -> BaseTool:
    """Mark ``tool`` as MCP-sourced. Mutates in place and returns it for chaining.

    Args:
        tool: The LangChain tool to tag.
        server_name: Optional originating MCP server name.
        tool_name: Optional original MCP tool name (without prefix).

    Returns:
        The same tool (mutated in place, returned for chaining).
    """
    meta: dict[str, object] = {**(tool.metadata or {}), MCP_TOOL_METADATA_KEY: True}
    if server_name is not None:
        meta["mcp_server"] = server_name
    if tool_name is not None:
        meta["mcp_tool_name"] = tool_name
    tool.metadata = meta
    return tool


def is_mcp_tool(tool: BaseTool) -> bool:
    """True when ``tool`` carries the MCP-source tag written by :func:`tag_mcp_tool`."""
    return (getattr(tool, "metadata", None) or {}).get(MCP_TOOL_METADATA_KEY) is True
