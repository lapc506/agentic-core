"""Unit tests for MCP Bridge adapter — tool discovery, execution, and phantom prevention."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from agentic_core.adapters.secondary.mcp_bridge_adapter import (
    MCPBridgeAdapter,
    MCPServerConnection,
    MCPTool,
    _build_safe_env,
    _passes_tool_filter,
    _sanitize_error,
)
from agentic_core.config.settings import (
    MCPBridgeConfig,
    MCPServerEntry,
    MCPToolFilter,
)
from agentic_core.domain.value_objects.tools import ToolHealthStatus
from agentic_core.shared_kernel.events import EventBus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_config(
    servers: dict[str, MCPServerEntry] | None = None,
    tool_prefix: bool = True,
) -> MCPBridgeConfig:
    return MCPBridgeConfig(servers=servers or {}, tool_prefix=tool_prefix)


def make_server_entry(
    transport: str = "stdio",
    command: str | None = "echo",
    args: list[str] | None = None,
    url: str | None = None,
    env: dict[str, str] | None = None,
) -> MCPServerEntry:
    return MCPServerEntry(
        transport=transport,  # type: ignore[arg-type]
        command=command,
        args=args or [],
        url=url,
        env=env or {},
    )


def make_adapter(
    servers: dict[str, MCPServerEntry] | None = None,
    tool_prefix: bool = True,
) -> MCPBridgeAdapter:
    config = make_config(servers=servers, tool_prefix=tool_prefix)
    bus = EventBus()
    return MCPBridgeAdapter(config=config, event_bus=bus)


def make_adapter_with_bus(
    servers: dict[str, MCPServerEntry] | None = None,
    tool_prefix: bool = True,
) -> tuple[MCPBridgeAdapter, EventBus]:
    config = make_config(servers=servers, tool_prefix=tool_prefix)
    bus = EventBus()
    adapter = MCPBridgeAdapter(config=config, event_bus=bus)
    return adapter, bus


# ---------------------------------------------------------------------------
# 1. MCPServerConnection — initial state
# ---------------------------------------------------------------------------


def test_server_connection_initial_state():
    entry = make_server_entry(transport="stdio", command="node")
    conn = MCPServerConnection(name="test-server", config=entry)
    assert conn.name == "test-server"
    assert conn.is_connected is False
    assert conn.error == ""
    assert conn.tools == {}
    assert conn.transport == "stdio"


def test_server_connection_http_initial_state():
    entry = make_server_entry(transport="streamable-http", command=None, url="https://mcp.example.com")
    conn = MCPServerConnection(name="remote", config=entry)
    assert conn.is_connected is False
    assert conn.transport == "streamable-http"


# ---------------------------------------------------------------------------
# 2. MCPTool dataclass
# ---------------------------------------------------------------------------


def test_mcp_tool_defaults():
    tool = MCPTool(name="search", description="Search the web")
    assert tool.name == "search"
    assert tool.description == "Search the web"
    assert tool.input_schema == {}
    assert tool.server_name == ""
    assert tool.healthy is True


def test_mcp_tool_custom_fields():
    tool = MCPTool(
        name="query_db",
        description="Query database",
        input_schema={"type": "object", "properties": {"sql": {"type": "string"}}},
        server_name="db-server",
        healthy=False,
    )
    assert tool.server_name == "db-server"
    assert tool.healthy is False
    assert "sql" in tool.input_schema["properties"]


# ---------------------------------------------------------------------------
# 3. Tool registration and listing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tools_empty_initially():
    adapter = make_adapter()
    tools = await adapter.list_tools("persona-1")
    assert tools == []


@pytest.mark.asyncio
async def test_healthy_tool_count_starts_at_zero():
    adapter = make_adapter()
    assert adapter.healthy_tool_count == 0


@pytest.mark.asyncio
async def test_connected_server_count_starts_at_zero():
    adapter = make_adapter()
    assert adapter.connected_server_count == 0


# ---------------------------------------------------------------------------
# 4. Phantom tool prevention — deregister unhealthy tools
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deregister_tool_removes_from_healthy_set():
    adapter = make_adapter()
    # Manually inject a tool into the registry
    tool = MCPTool(name="broken_tool", description="will fail", server_name="srv")
    adapter._tool_registry["mcp_srv_broken_tool"] = tool
    adapter._tool_to_server["mcp_srv_broken_tool"] = "srv"
    adapter._healthy_tools.add("mcp_srv_broken_tool")

    assert adapter.healthy_tool_count == 1

    await adapter.deregister_tool("mcp_srv_broken_tool")

    assert adapter.healthy_tool_count == 0
    assert "mcp_srv_broken_tool" not in adapter._healthy_tools
    assert tool.healthy is False


@pytest.mark.asyncio
async def test_deregister_nonexistent_tool_is_safe():
    adapter = make_adapter()
    # Should not raise
    await adapter.deregister_tool("does_not_exist")
    assert adapter.healthy_tool_count == 0


@pytest.mark.asyncio
async def test_list_tools_excludes_deregistered():
    adapter = make_adapter()
    # Register two tools
    for name in ("tool_a", "tool_b"):
        tool = MCPTool(name=name, description=f"desc {name}", server_name="srv")
        adapter._tool_registry[name] = tool
        adapter._tool_to_server[name] = "srv"
        adapter._healthy_tools.add(name)

    assert len(await adapter.list_tools("p")) == 2

    await adapter.deregister_tool("tool_a")

    tools = await adapter.list_tools("p")
    assert tools == ["tool_b"]


# ---------------------------------------------------------------------------
# 5. Healthcheck marks tool unhealthy on disconnected server
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcheck_returns_unhealthy_for_disconnected_server():
    adapter = make_adapter()
    entry = make_server_entry()
    server = MCPServerConnection(name="dead", config=entry)
    # Server is not connected
    adapter._servers["dead"] = server
    adapter._tool_to_server["mcp_dead_search"] = "dead"

    status = await adapter.healthcheck_tool("mcp_dead_search")
    assert status.healthy is False
    assert status.reason == "Server disconnected"


@pytest.mark.asyncio
async def test_healthcheck_returns_healthy_for_new_unregistered_tool():
    adapter = make_adapter()
    status = await adapter.healthcheck_tool("brand_new_tool")
    assert status.healthy is True


# ---------------------------------------------------------------------------
# 6. List servers status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_servers_empty():
    adapter = make_adapter()
    assert adapter.list_servers() == []


@pytest.mark.asyncio
async def test_list_servers_shows_status():
    adapter = make_adapter()
    entry = make_server_entry(transport="stdio", command="node")
    server = MCPServerConnection(name="my-server", config=entry)
    adapter._servers["my-server"] = server

    servers = adapter.list_servers()
    assert len(servers) == 1
    assert servers[0]["name"] == "my-server"
    assert servers[0]["transport"] == "stdio"
    assert servers[0]["connected"] is False
    assert servers[0]["tool_count"] == 0
    assert servers[0]["error"] == ""


@pytest.mark.asyncio
async def test_list_servers_shows_error():
    adapter = make_adapter()
    entry = make_server_entry(transport="stdio", command="node")
    server = MCPServerConnection(name="bad", config=entry)
    server._error = "Connection refused"
    adapter._servers["bad"] = server

    servers = adapter.list_servers()
    assert servers[0]["error"] == "Connection refused"


# ---------------------------------------------------------------------------
# 7. HTTP server configuration
# ---------------------------------------------------------------------------


def test_http_server_entry_config():
    entry = make_server_entry(
        transport="streamable-http",
        command=None,
        url="https://mcp.example.com/v1",
    )
    assert entry.transport == "streamable-http"
    assert entry.url == "https://mcp.example.com/v1"
    assert entry.command is None


@pytest.mark.asyncio
async def test_http_server_connect_requires_url():
    entry = MCPServerEntry(transport="streamable-http")  # type: ignore[arg-type]
    server = MCPServerConnection(name="no-url", config=entry)
    await server.connect()
    assert server.is_connected is False
    assert "url is required" in server.error


@pytest.mark.asyncio
async def test_http_server_connect_sets_connected():
    entry = make_server_entry(
        transport="streamable-http",
        command=None,
        url="https://mcp.example.com",
    )
    server = MCPServerConnection(name="remote", config=entry)
    await server.connect()
    assert server.is_connected is True


# ---------------------------------------------------------------------------
# 8. Execute tool on disconnected server returns error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_not_registered():
    adapter = make_adapter()
    result = await adapter.execute("nonexistent_tool", {"arg": "value"})
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "not_found"
    assert "not registered" in result.error.message


@pytest.mark.asyncio
async def test_execute_tool_on_disconnected_server():
    adapter, bus = make_adapter_with_bus()
    # Register a tool pointing to a disconnected server
    tool = MCPTool(name="do_thing", description="does a thing", server_name="dead-srv")
    adapter._tool_registry["mcp_dead-srv_do_thing"] = tool
    adapter._tool_to_server["mcp_dead-srv_do_thing"] = "dead-srv"
    adapter._healthy_tools.add("mcp_dead-srv_do_thing")

    entry = make_server_entry()
    server = MCPServerConnection(name="dead-srv", config=entry)
    # Server is NOT connected
    adapter._servers["dead-srv"] = server

    result = await adapter.execute("mcp_dead-srv_do_thing", {})
    assert result.success is False
    assert result.error is not None
    assert result.error.code == "capability_missing"
    assert "disconnected" in result.error.message

    # Phantom prevention: tool should now be deregistered
    assert adapter.healthy_tool_count == 0


# ---------------------------------------------------------------------------
# 9. Connected / healthy property counts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connected_server_count():
    adapter = make_adapter()
    entry = make_server_entry()
    # Add two servers, one connected, one not
    srv_a = MCPServerConnection(name="a", config=entry)
    srv_a._connected = True
    srv_b = MCPServerConnection(name="b", config=entry)
    srv_b._connected = False
    adapter._servers["a"] = srv_a
    adapter._servers["b"] = srv_b

    assert adapter.connected_server_count == 1


@pytest.mark.asyncio
async def test_healthy_tool_count_reflects_registrations():
    adapter = make_adapter()
    adapter._healthy_tools = {"t1", "t2", "t3"}
    assert adapter.healthy_tool_count == 3
    adapter._healthy_tools.discard("t2")
    assert adapter.healthy_tool_count == 2


# ---------------------------------------------------------------------------
# 10. Degradation publishes ToolDegraded event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_degradation_publishes_tool_degraded_event():
    adapter, bus = make_adapter_with_bus()
    events_received: list[Any] = []
    from agentic_core.domain.events.domain_events import ToolDegraded
    bus.subscribe(ToolDegraded, AsyncMock(side_effect=lambda e: events_received.append(e)))

    # Set up a registered tool on a disconnected server
    tool = MCPTool(name="failing", description="will fail", server_name="srv")
    adapter._tool_registry["failing"] = tool
    adapter._tool_to_server["failing"] = "srv"
    adapter._healthy_tools.add("failing")

    entry = make_server_entry()
    server = MCPServerConnection(name="srv", config=entry)
    adapter._servers["srv"] = server

    result = await adapter.execute("failing", {})
    assert result.success is False

    # Event should have been published
    assert len(events_received) == 1
    assert events_received[0].tool_name == "failing"


# ---------------------------------------------------------------------------
# 11. Tool filter logic
# ---------------------------------------------------------------------------


def test_tool_filter_passes_all_by_default():
    f = MCPToolFilter()
    assert _passes_tool_filter("any_tool", f) is True


def test_tool_filter_include_restricts():
    f = MCPToolFilter(include=["search_*", "query_*"])
    assert _passes_tool_filter("search_web", f) is True
    assert _passes_tool_filter("delete_all", f) is False


def test_tool_filter_exclude_blocks():
    f = MCPToolFilter(exclude=["dangerous_*"])
    assert _passes_tool_filter("safe_tool", f) is True
    assert _passes_tool_filter("dangerous_delete", f) is False


def test_tool_filter_exclude_takes_precedence():
    f = MCPToolFilter(include=["*_tool"], exclude=["bad_tool"])
    assert _passes_tool_filter("good_tool", f) is True
    assert _passes_tool_filter("bad_tool", f) is False


# ---------------------------------------------------------------------------
# 12. Safe env and error sanitization
# ---------------------------------------------------------------------------


def test_build_safe_env_includes_explicit_vars():
    env = _build_safe_env({"MY_KEY": "my_value"})
    assert env["MY_KEY"] == "my_value"


def test_sanitize_error_redacts_api_keys():
    msg = "Error: key sk-abcdefghijklmnopqrstuvwxyz is invalid"
    sanitized = _sanitize_error(msg)
    assert "sk-" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_error_redacts_bearer_tokens():
    msg = "Auth failed: Bearer eyJhbGciOiJIUzI1NiJ9.payload"
    sanitized = _sanitize_error(msg)
    assert "eyJhbGciOi" not in sanitized
    assert "[REDACTED]" in sanitized


# ---------------------------------------------------------------------------
# 13. Stop clears all state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_clears_all_state():
    adapter = make_adapter()
    tool = MCPTool(name="t", description="d", server_name="s")
    adapter._tool_registry["t"] = tool
    adapter._tool_to_server["t"] = "s"
    adapter._healthy_tools.add("t")
    entry = make_server_entry()
    server = MCPServerConnection(name="s", config=entry)
    adapter._servers["s"] = server

    await adapter.stop()

    assert adapter._servers == {}
    assert adapter._tool_registry == {}
    assert adapter._tool_to_server == {}
    assert adapter._healthy_tools == set()
    assert adapter.connected_server_count == 0
    assert adapter.healthy_tool_count == 0


# ---------------------------------------------------------------------------
# 14. Server disconnect lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_disconnect_marks_not_connected():
    entry = make_server_entry(
        transport="streamable-http",
        command=None,
        url="https://mcp.example.com",
    )
    server = MCPServerConnection(name="remote", config=entry)
    await server.connect()
    assert server.is_connected is True

    await server.disconnect()
    assert server.is_connected is False
