from __future__ import annotations

from agentic_core.adapters.secondary.mcp_bridge_adapter import (
    MCPBridgeAdapter,
    MCPTool,
    _build_safe_env,
    _passes_tool_filter,
    _sanitize_error,
)
from agentic_core.config.settings import MCPBridgeConfig, MCPToolFilter
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
    tool = MCPTool(name="test_tool", description="test", server_name="test_server")
    adapter._tool_registry["mcp_test_tool"] = tool
    adapter._tool_to_server["mcp_test_tool"] = "test_server"
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


# --- Tool filtering tests (#62) ---


def test_filter_no_rules_allows_all():
    f = MCPToolFilter()
    assert _passes_tool_filter("any_tool", f) is True


def test_filter_include_allows_matching():
    f = MCPToolFilter(include=["create_issue", "list_issues"])
    assert _passes_tool_filter("create_issue", f) is True
    assert _passes_tool_filter("list_issues", f) is True
    assert _passes_tool_filter("delete_repo", f) is False


def test_filter_include_glob_pattern():
    f = MCPToolFilter(include=["create_*", "list_*"])
    assert _passes_tool_filter("create_issue", f) is True
    assert _passes_tool_filter("create_pr", f) is True
    assert _passes_tool_filter("list_repos", f) is True
    assert _passes_tool_filter("delete_repo", f) is False


def test_filter_exclude_blocks_matching():
    f = MCPToolFilter(exclude=["delete_customer"])
    assert _passes_tool_filter("create_customer", f) is True
    assert _passes_tool_filter("delete_customer", f) is False


def test_filter_exclude_glob_pattern():
    f = MCPToolFilter(exclude=["delete_*"])
    assert _passes_tool_filter("create_issue", f) is True
    assert _passes_tool_filter("delete_issue", f) is False
    assert _passes_tool_filter("delete_repo", f) is False


def test_filter_exclude_takes_precedence_over_include():
    f = MCPToolFilter(include=["*_issue"], exclude=["delete_*"])
    assert _passes_tool_filter("create_issue", f) is True
    assert _passes_tool_filter("list_issue", f) is True
    # excluded even though it matches include
    assert _passes_tool_filter("delete_issue", f) is False


def test_filter_prompts_and_resources_defaults():
    f = MCPToolFilter()
    assert f.prompts is True
    assert f.resources is True


def test_filter_prompts_disabled():
    f = MCPToolFilter(prompts=False, resources=False)
    assert f.prompts is False
    assert f.resources is False


def test_tool_filter_config_in_server_entry():
    from agentic_core.config.settings import MCPServerEntry
    entry = MCPServerEntry(
        transport="stdio",
        command="node",
        args=["server.js"],
        tools=MCPToolFilter(
            include=["create_*"],
            exclude=["create_dangerous"],
            prompts=False,
        ),
    )
    assert entry.tools.include == ["create_*"]
    assert entry.tools.exclude == ["create_dangerous"]
    assert entry.tools.prompts is False
    assert entry.tools.resources is True  # default


def test_tool_filter_config_default():
    from agentic_core.config.settings import MCPServerEntry
    entry = MCPServerEntry(transport="stdio", command="node")
    assert entry.tools.include == []
    assert entry.tools.exclude == []
    assert entry.tools.prompts is True
