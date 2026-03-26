from __future__ import annotations

from datetime import datetime, timezone

from agentic_core.adapters.secondary.mcp_bridge_adapter import (
    MCPBridgeAdapter,
    _build_safe_env,
    _sanitize_error,
)
from agentic_core.config.settings import MCPBridgeConfig
from agentic_core.domain.events.domain_events import ToolDegraded
from agentic_core.shared_kernel.events import DomainEvent, EventBus


def test_build_safe_env_filters():
    env = _build_safe_env({"CUSTOM_KEY": "value"})
    assert "CUSTOM_KEY" in env
    assert "PYTHONPATH" not in env  # not in safe list


def test_sanitize_error_strips_keys():
    msg = "Error: sk-ant-abc123456789012345678901 is invalid"
    sanitized = _sanitize_error(msg)
    assert "sk-ant" not in sanitized
    assert "[REDACTED]" in sanitized


def test_sanitize_error_strips_bearer():
    msg = "Auth failed: Bearer eyJhbGciOi.long.token"
    sanitized = _sanitize_error(msg)
    assert "Bearer" not in sanitized or "[REDACTED]" in sanitized


def test_sanitize_error_no_secrets():
    msg = "Connection refused: localhost:6379"
    assert _sanitize_error(msg) == msg


async def test_mcp_bridge_empty_config():
    bus = EventBus()
    config = MCPBridgeConfig()
    adapter = MCPBridgeAdapter(config, bus)
    await adapter.start()

    tools = await adapter.list_tools("any_persona")
    assert tools == []
    await adapter.stop()


async def test_mcp_bridge_execute_not_found():
    bus = EventBus()
    config = MCPBridgeConfig()
    adapter = MCPBridgeAdapter(config, bus)
    await adapter.start()

    result = await adapter.execute("nonexistent_tool", {})
    assert not result.success
    assert result.error is not None
    assert result.error.code == "not_found"
    await adapter.stop()


async def test_mcp_bridge_deregister_publishes_event():
    bus = EventBus()
    events: list[DomainEvent] = []

    async def on_degraded(event: DomainEvent) -> None:
        events.append(event)

    bus.subscribe(ToolDegraded, on_degraded)

    config = MCPBridgeConfig()
    adapter = MCPBridgeAdapter(config, bus)
    adapter._tool_registry["mcp_test_tool"] = "test_server"
    adapter._healthy_tools.add("mcp_test_tool")

    await adapter._handle_degradation("mcp_test_tool", "server crashed")

    assert "mcp_test_tool" not in adapter._healthy_tools
    assert len(events) == 1
    assert events[0].tool_name == "mcp_test_tool"  # type: ignore[attr-defined]


async def test_mcp_bridge_healthcheck():
    bus = EventBus()
    config = MCPBridgeConfig()
    adapter = MCPBridgeAdapter(config, bus)

    health = await adapter.healthcheck_tool("new_tool")
    assert health.healthy is True  # new tool assumed healthy
