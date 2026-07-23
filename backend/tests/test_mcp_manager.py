"""Tests for MCPClientManager — lifecycle, registry, tool access, reconnect."""

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import Tool as MCPTool

from deerflow.config.extensions_config import McpServerConfig
from deerflow.mcp.manager import MCPClientManager, MCPServerConnection


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure each test starts with a fresh singleton."""
    MCPClientManager._instance = None
    yield
    MCPClientManager._instance = None


class TestSingleton:
    """Singleton pattern."""

    def test_get_instance_returns_same(self):
        """get_instance() returns the same object."""
        a = MCPClientManager.get_instance()
        b = MCPClientManager.get_instance()
        assert a is b


class TestConnect:
    """connect() lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_no_enabled_servers(self):
        """Graceful when no servers are enabled."""
        mock_config = MagicMock()
        mock_config.get_enabled_mcp_servers.return_value = {}
        mock_config.model_extra = None
        mock_config.mcp_servers = {}
        mock_config.skills = {}

        with patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=mock_config):
            manager = MCPClientManager.get_instance()
            await manager.connect()
            assert manager.list_connections() == []

    @pytest.mark.asyncio
    async def test_connect_with_server(self):
        """Connect discovers tools and populates registry."""
        mock_tool = MCPTool(
            name="search",
            description="Search tool",
            inputSchema={"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
        )

        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=[mock_tool])

        mock_config = MagicMock()
        mock_config.get_enabled_mcp_servers.return_value = {
            "search-server": McpServerConfig(
                enabled=True, type="stdio", command="npx", args=["-y", "@mcp/search"]
            ),
        }
        mock_config.model_extra = None
        mock_config.mcp_servers = {}
        mock_config.skills = {}

        with (
            patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=mock_config),
            patch("langchain_mcp_adapters.client.MultiServerMCPClient", return_value=mock_client),
        ):
            manager = MCPClientManager.get_instance()
            await manager.connect()

        assert manager.is_connected("search-server")
        conn = manager.list_connections()
        assert len(conn) == 1
        assert conn[0].server_name == "search-server"
        assert len(conn[0].tools) == 1
        assert conn[0].tools[0].name == "search"

    @pytest.mark.asyncio
    async def test_connect_single_server(self):
        """connect('server1') connects only one server."""
        mock_tool = MCPTool(name="t1", description="", inputSchema={"type": "object", "properties": {}})

        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=[mock_tool])

        mock_config = MagicMock()
        mock_config.get_enabled_mcp_servers.return_value = {
            "srv1": McpServerConfig(enabled=True, type="stdio", command="cmd1", args=[]),
            "srv2": McpServerConfig(enabled=True, type="stdio", command="cmd2", args=[]),
        }
        mock_config.model_extra = None
        mock_config.mcp_servers = {}
        mock_config.skills = {}

        with (
            patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=mock_config),
            patch("langchain_mcp_adapters.client.MultiServerMCPClient", return_value=mock_client),
        ):
            manager = MCPClientManager.get_instance()
            await manager.connect("srv1")

        assert manager.is_connected("srv1")
        assert not manager.is_connected("srv2")

    @pytest.mark.asyncio
    async def test_connect_unknown_server_raises(self):
        """Unknown server name raises ValueError."""
        mock_config = MagicMock()
        mock_config.get_enabled_mcp_servers.return_value = {}
        mock_config.model_extra = None
        mock_config.mcp_servers = {}
        mock_config.skills = {}

        with patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=mock_config):
            manager = MCPClientManager.get_instance()
            with pytest.raises(ValueError, match="not found"):
                await manager.connect("does-not-exist")


class TestDisconnect:
    """disconnect() lifecycle."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_entry(self):
        """Disconnect removes server from registry."""
        manager = MCPClientManager.get_instance()
        with manager._registry_lock:
            manager._registry["srv"] = MCPServerConnection(
                server_name="srv",
                transport="stdio",
                connected=True,
            )

        with patch("deerflow.mcp.session_pool.get_session_pool") as mock_pool:
            mock_pool.return_value.close_server = AsyncMock()
            await manager.disconnect("srv")

        assert not manager.is_connected("srv")

    @pytest.mark.asyncio
    async def test_disconnect_noop_not_connected(self):
        """Disconnecting an unknown server is a no-op."""
        manager = MCPClientManager.get_instance()
        # Should not raise
        await manager.disconnect("unknown")

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """disconnect() without args closes all servers."""
        manager = MCPClientManager.get_instance()
        with manager._registry_lock:
            manager._registry["srv1"] = MCPServerConnection(server_name="srv1", transport="stdio", connected=True)
            manager._registry["srv2"] = MCPServerConnection(server_name="srv2", transport="stdio", connected=True)

        with patch("deerflow.mcp.session_pool.get_session_pool") as mock_pool:
            mock_pool.return_value.close_server = AsyncMock()
            await manager.disconnect()

        assert manager.list_connections() == []


class TestReconnect:
    """reconnect() with exponential backoff."""

    @pytest.mark.asyncio
    async def test_reconnect_success_on_first_try(self):
        """Immediate success on reconnect."""
        mock_tool = MCPTool(name="t", description="", inputSchema={"type": "object", "properties": {}})
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(return_value=[mock_tool])
        mock_config = MagicMock()
        mock_config.get_enabled_mcp_servers.return_value = {
            "srv": McpServerConfig(enabled=True, type="stdio", command="cmd", args=[])
        }
        mock_config.model_extra = None
        mock_config.mcp_servers = {}
        mock_config.skills = {}

        with (
            patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=mock_config),
            patch("langchain_mcp_adapters.client.MultiServerMCPClient", return_value=mock_client),
            patch("deerflow.mcp.session_pool.get_session_pool") as mock_pool,
        ):
            mock_pool.return_value.close_server = AsyncMock()
            manager = MCPClientManager.get_instance()
            await manager.reconnect("srv", max_retries=2)

        assert manager.is_connected("srv")

    @pytest.mark.asyncio
    async def test_reconnect_exhausted_raises(self):
        """ConnectionError after all retries exhausted."""
        manager = MCPClientManager.get_instance()
        # Pre-populate an entry so disconnect works
        with manager._registry_lock:
            manager._registry["srv"] = MCPServerConnection(
                server_name="srv", transport="stdio", connected=True,
            )

        # Make connect always fail by returning empty enabled servers
        mock_config = MagicMock()
        mock_config.get_enabled_mcp_servers.return_value = {}
        mock_config.model_extra = None
        mock_config.mcp_servers = {}
        mock_config.skills = {}

        with (
            patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=mock_config),
            patch("deerflow.mcp.session_pool.get_session_pool") as mock_pool,
        ):
            mock_pool.return_value.close_server = AsyncMock()
            with pytest.raises(ConnectionError, match="Failed to reconnect"):
                await manager.reconnect("srv", max_retries=2, base_delay=0.01)


class TestToolAccess:
    """list_tools(), call_tool(), registry access."""

    def test_list_tools_all(self):
        """list_tools() returns tools from all servers."""
        manager = MCPClientManager.get_instance()
        tool_a = MCPTool(name="a", description="", inputSchema={"type": "object", "properties": {}})
        tool_b = MCPTool(name="b", description="", inputSchema={"type": "object", "properties": {}})

        with manager._registry_lock:
            manager._registry["srv1"] = MCPServerConnection(
                server_name="srv1", transport="stdio", tools=[tool_a], connected=True,
            )
            manager._registry["srv2"] = MCPServerConnection(
                server_name="srv2", transport="stdio", tools=[tool_b], connected=True,
            )

        tools = manager.list_tools()
        assert len(tools) == 2
        tool_names = {t.name for t in tools}
        assert tool_names == {"a", "b"}

    def test_list_tools_filtered(self):
        """list_tools('srv1') returns only srv1 tools."""
        manager = MCPClientManager.get_instance()
        tool_a = MCPTool(name="a", description="", inputSchema={"type": "object", "properties": {}})
        tool_b = MCPTool(name="b", description="", inputSchema={"type": "object", "properties": {}})

        with manager._registry_lock:
            manager._registry["srv1"] = MCPServerConnection(
                server_name="srv1", transport="stdio", tools=[tool_a], connected=True,
            )
            manager._registry["srv2"] = MCPServerConnection(
                server_name="srv2", transport="stdio", tools=[tool_b], connected=True,
            )

        tools = manager.list_tools("srv1")
        assert len(tools) == 1
        assert tools[0].name == "a"

    def test_list_tools_unknown_server_raises(self):
        """ValueError for unknown server."""
        manager = MCPClientManager.get_instance()
        with pytest.raises(ValueError, match="not connected"):
            manager.list_tools("does-not-exist")

    def test_is_connected(self):
        """is_connected reflects registry state."""
        manager = MCPClientManager.get_instance()
        with manager._registry_lock:
            manager._registry["srv"] = MCPServerConnection(
                server_name="srv", transport="stdio", connected=True,
            )
        assert manager.is_connected("srv")
        assert not manager.is_connected("unknown")

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """ValueError when calling tool on disconnected server."""
        manager = MCPClientManager.get_instance()
        with pytest.raises(ValueError, match="not connected"):
            await manager.call_tool("unknown", "tool", {})


class TestThreadSafety:
    """Basic concurrent access safety."""

    def test_concurrent_registry_access(self):
        """Multiple threads can read/write registry without crashing."""
        manager = MCPClientManager.get_instance()
        errors: list[Exception] = []

        def _writer() -> None:
            for i in range(50):
                try:
                    with manager._registry_lock:
                        manager._registry[f"srv-{i}"] = MCPServerConnection(
                            server_name=f"srv-{i}", transport="stdio", connected=True,
                        )
                except Exception as e:
                    errors.append(e)

        def _reader() -> None:
            for _ in range(50):
                try:
                    _ = manager.list_connections()
                    _ = manager.is_connected("srv-0")
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=_writer))
            threads.append(threading.Thread(target=_reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Concurrent access errors: {errors}"


class TestListConnections:
    """list_connections() snapshot."""

    def test_list_connections_snapshot(self):
        """Returns a snapshot of current connections."""
        manager = MCPClientManager.get_instance()
        with manager._registry_lock:
            manager._registry["a"] = MCPServerConnection(server_name="a", transport="stdio", connected=True)

        conns = manager.list_connections()
        assert len(conns) == 1
        assert conns[0].server_name == "a"

    def test_shutdown_clears_all(self):
        """shutdown() clears the registry."""
        manager = MCPClientManager.get_instance()
        with manager._registry_lock:
            manager._registry["srv"] = MCPServerConnection(server_name="srv", transport="stdio", connected=True)

        with patch("deerflow.mcp.session_pool.get_session_pool") as mock_pool:
            mock_pool.return_value.close_server = AsyncMock()
            mock_pool.return_value.close_all = AsyncMock()
            asyncio.run(manager.shutdown())

        assert manager.list_connections() == []
