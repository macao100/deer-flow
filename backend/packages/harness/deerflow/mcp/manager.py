"""Explicit lifecycle management for MCP server connections.

Provides a singleton :class:`MCPClientManager` with connect / disconnect /
reconnect semantics, tool discovery, and direct tool execution.
Thread-safe via reentrant lock on the registry and double-checked locking
for the singleton.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

if TYPE_CHECKING:

    pass

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConnection:
    """Tracks the state of a single MCP server connection.

    Attributes:
        server_name: Unique name for this server.
        transport: Transport type (stdio, sse, or http).
        url: Remote URL (for sse/http transports).
        command: Local executable path (for stdio transport).
        args: CLI arguments (for stdio transport).
        tools: Discovered MCP tool descriptors.
        connected: Whether the server is currently connected.
        last_connected: Timestamp (``time.monotonic()``) of last successful connect.
    """

    server_name: str
    transport: Literal["stdio", "sse", "http"]
    url: str | None = None
    command: str | None = None
    args: list[str] = field(default_factory=list)
    tools: list[Any] = field(default_factory=list)  # list[MCPTool]
    connected: bool = False
    last_connected: float | None = None
    # Stored for reconnection
    _raw_config: Any = None  # McpServerConfig


class MCPClientManager:
    """Singleton manager for MCP server lifecycle.

    Provides explicit connect / disconnect / reconnect with exponential
    backoff, tool listing from the in-memory registry, and direct tool
    execution through the session pool.

    Usage::

        manager = MCPClientManager.get_instance()
        await manager.connect()
        tools = manager.list_tools()
        await manager.call_tool("search", "brave_web_search", {"query": "..."})
    """

    _instance: ClassVar[MCPClientManager | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._registry: dict[str, MCPServerConnection] = {}
        self._registry_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> MCPClientManager:
        """Return the process-wide singleton (double-checked locking)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Lifecycle ────────────────────────────────────────────────────

    async def connect(self, server_name: str | None = None) -> None:
        """Connect to one or all enabled MCP servers and discover their tools.

        Loads the latest config from disk, builds connection parameters for
        each enabled server, discovers tools via ``MultiServerMCPClient``,
        and populates the in-memory registry.

        Args:
            server_name: If provided, connect only this server.
                         If ``None``, connect all enabled servers.

        Raises:
            ValueError: If a named server is not found in the config.
        """
        from deerflow.config.extensions_config import ExtensionsConfig
        from deerflow.mcp.client import build_server_params

        # Always read the latest config from disk
        extensions_config = ExtensionsConfig.from_file()
        enabled = extensions_config.get_enabled_mcp_servers()

        if server_name is not None:
            if server_name not in enabled:
                raise ValueError(
                    f"MCP server '{server_name}' not found in config "
                    f"(available: {list(enabled.keys())})"
                )
            targets = {server_name: enabled[server_name]}
        else:
            targets = enabled

        if not targets:
            logger.info("No enabled MCP servers to connect")
            return

        for name, server_config in targets.items():
            try:
                connection_params = build_server_params(name, server_config)
            except Exception as e:
                logger.error("Failed to build params for MCP server '%s': %s", name, e)
                continue

            # Discover tools
            try:
                tools = await self._discover_tools(name, connection_params)
            except Exception as e:
                logger.error(
                    "Failed to discover tools for MCP server '%s': %s",
                    name,
                    e,
                    exc_info=True,
                )
                continue

            transport: Literal["stdio", "sse", "http"] = server_config.type  # type: ignore[assignment]

            connection = MCPServerConnection(
                server_name=name,
                transport=transport,
                url=server_config.url,
                command=server_config.command,
                args=list(server_config.args),
                tools=list(tools),
                connected=True,
                last_connected=time.monotonic(),
                _raw_config=server_config,
            )

            with self._registry_lock:
                self._registry[name] = connection

            logger.info(
                "Connected to MCP server '%s': %d tool(s) discovered",
                name,
                len(tools),
            )

    async def _discover_tools(
        self,
        server_name: str,
        connection_params: dict[str, Any],
    ) -> list[Any]:
        """Discover tools from a single MCP server.

        Uses ``MultiServerMCPClient`` to load tools and returns the raw
        MCP tool descriptors.
        """
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            logger.warning("langchain-mcp-adapters not installed, cannot discover tools")
            return []

        # Build a single-server config for discovery
        single_config = {server_name: connection_params}

        # Run tool discovery in a thread to avoid blocking the event loop
        # on stdio process startup
        def _discover_sync() -> list[Any]:
            async def _run() -> list[Any]:
                client: Any = MultiServerMCPClient(single_config, tool_name_prefix=False)
                return await client.get_tools()

            return asyncio.run(_run())

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — use asyncio.run directly
            async def _direct() -> list[Any]:
                client = MultiServerMCPClient(single_config, tool_name_prefix=False)
                return await client.get_tools()

            return await _direct()

        # We're inside a running loop — offload to a thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return await loop.run_in_executor(pool, _discover_sync)

    async def disconnect(self, server_name: str | None = None) -> None:
        """Disconnect one or all servers and close their sessions.

        Args:
            server_name: If provided, disconnect only this server.
                         If ``None``, disconnect all connected servers.
        """
        from deerflow.mcp.session_pool import get_session_pool

        pool = get_session_pool()

        with self._registry_lock:
            if server_name is not None:
                targets = [server_name] if server_name in self._registry else []
            else:
                targets = list(self._registry.keys())

            for name in targets:
                self._registry.pop(name, None)
                try:
                    await pool.close_server(name)
                except Exception:
                    logger.debug("Error closing sessions for '%s'", name, exc_info=True)
                logger.info("Disconnected MCP server '%s'", name)

    async def reconnect(
        self,
        server_name: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        """Disconnect and reconnect with exponential backoff.

        Args:
            server_name: Server to reconnect.
            max_retries: Maximum number of retry attempts (default 3).
            base_delay: Initial backoff delay in seconds (default 1.0).
            max_delay: Maximum backoff delay in seconds (default 30.0).

        Raises:
            ConnectionError: If all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                await self.disconnect(server_name)
                await self.connect(server_name)
                logger.info(
                    "Reconnected to MCP server '%s' on attempt %d/%d",
                    server_name,
                    attempt,
                    max_retries,
                )
                return
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "Reconnect attempt %d/%d for '%s' failed: %s — retrying in %.1fs",
                        attempt,
                        max_retries,
                        server_name,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)

        raise ConnectionError(
            f"Failed to reconnect to MCP server '{server_name}' "
            f"after {max_retries} attempts"
        ) from last_error

    # ── Tool access ──────────────────────────────────────────────────

    def list_tools(self, server_name: str | None = None) -> list[Any]:
        """List discovered MCP tool descriptors from the registry.

        Args:
            server_name: If provided, list only tools for this server.
                         If ``None``, list tools from all connected servers.

        Returns:
            List of MCP Tool descriptors.

        Raises:
            ValueError: If a named server is not in the registry.
        """
        with self._registry_lock:
            if server_name is not None:
                conn = self._registry.get(server_name)
                if conn is None:
                    raise ValueError(f"MCP server '{server_name}' is not connected")
                return list(conn.tools)

            all_tools: list[Any] = []
            for conn in self._registry.values():
                all_tools.extend(conn.tools)
            return all_tools

    def list_connections(self) -> list[MCPServerConnection]:
        """Return all server connection records (snapshot copy)."""
        with self._registry_lock:
            return list(self._registry.values())

    def is_connected(self, server_name: str) -> bool:
        """Check whether a specific server is connected."""
        with self._registry_lock:
            conn = self._registry.get(server_name)
            return conn is not None and conn.connected

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Execute a tool directly via the session pool.

        Args:
            server_name: Server hosting the tool.
            tool_name: Name of the tool to call (without server prefix).
            arguments: Tool arguments as a dict.

        Returns:
            MCP CallToolResult content (converted to LangChain format).

        Raises:
            ValueError: If the server is not connected.
        """
        from deerflow.mcp.client import build_server_params
        from deerflow.mcp.session_pool import get_session_pool
        from deerflow.mcp.tools import _convert_call_tool_result, _extract_thread_id

        with self._registry_lock:
            conn = self._registry.get(server_name)
            if conn is None or not conn.connected:
                raise ValueError(f"MCP server '{server_name}' is not connected")

            if conn._raw_config is None:
                raise ValueError(f"MCP server '{server_name}' has no stored config for reconnection")

            connection_params = build_server_params(server_name, conn._raw_config)

        pool = get_session_pool()
        thread_id = _extract_thread_id(None)
        session = await pool.get_session(server_name, thread_id, connection_params)
        call_tool_result = await session.call_tool(tool_name, arguments)
        return _convert_call_tool_result(call_tool_result)

    # ── Teardown ─────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Disconnect all servers and close the session pool."""
        await self.disconnect()
        try:
            from deerflow.mcp.session_pool import get_session_pool

            await get_session_pool().close_all()
        except Exception:
            logger.debug("Error closing session pool during shutdown", exc_info=True)
        logger.info("MCPClientManager shut down")
