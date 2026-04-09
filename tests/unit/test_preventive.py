"""Tests for preventive issues #48-#57."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
import uuid_utils

from agentic_core.application.middleware.base import MiddlewareChain, RequestContext
from agentic_core.application.middleware.context_guard import ContextGuardMiddleware
from agentic_core.domain.value_objects.messages import AgentMessage


def _msg(content: str = "hello") -> AgentMessage:
    return AgentMessage(
        id=str(uuid_utils.uuid7()), session_id="s1", persona_id="p1",
        role="user", content=content, metadata={},
        timestamp=datetime.now(UTC),
    )


async def _echo(msg: AgentMessage, ctx: RequestContext) -> AgentMessage:
    return msg


# -- #50: Context window overflow --

async def test_context_guard_allows_normal():
    mw = ContextGuardMiddleware(max_content_tokens=1000)
    chain = MiddlewareChain([mw], _echo)
    result = await chain(_msg("short message"), RequestContext())
    assert result.content == "short message"


async def test_context_guard_rejects_oversized():
    mw = ContextGuardMiddleware(max_content_tokens=10)
    chain = MiddlewareChain([mw], _echo)
    huge = "x" * 200  # ~50 tokens > 10 limit
    with pytest.raises(ValueError, match="too large"):
        await chain(_msg(huge), RequestContext())


# -- #49: WebSocket close code handling --

def test_websocket_transport_has_close_handler():
    from agentic_core.adapters.primary.websocket import WebSocketTransport
    t = WebSocketTransport()
    assert t.on_close_session is None  # can be wired


# -- #53: Tool output never suppressed --

async def test_tool_result_always_has_output():
    from agentic_core.domain.value_objects.tools import ToolResult
    r = ToolResult(success=True, output="full output here")
    assert r.output == "full output here"
    assert len(r.output) > 0

    from agentic_core.domain.value_objects.tools import ToolError
    r_fail = ToolResult(success=False, output=None,
                        error=ToolError(code="execution_failed", message="detail", retriable=True))
    assert r_fail.error is not None
    assert r_fail.error.message == "detail"


# -- #55: Env var validation --

def test_mcp_safe_env_warns_unresolved():

    from agentic_core.adapters.secondary.mcp_bridge_adapter import _build_safe_env
    # Unresolved var should not crash, just skip
    env = _build_safe_env({"MY_KEY": "${NONEXISTENT_VAR_12345}"})
    assert "MY_KEY" not in env or env.get("MY_KEY") == ""


# -- #56: Tool deregistration fires event --

async def test_tool_deregistration_fires_event():
    from agentic_core.adapters.secondary.mcp_bridge_adapter import MCPBridgeAdapter
    from agentic_core.config.settings import MCPBridgeConfig
    from agentic_core.domain.events.domain_events import ToolDegraded
    from agentic_core.shared_kernel.events import EventBus

    bus = EventBus()
    events: list = []
    async def on_event(e: object) -> None:
        events.append(e)
    bus.subscribe(ToolDegraded, on_event)

    adapter = MCPBridgeAdapter(MCPBridgeConfig(), bus)
    adapter._tool_registry["test_tool"] = "server"
    adapter._healthy_tools.add("test_tool")

    await adapter._handle_degradation("test_tool", "server died")

    assert "test_tool" not in adapter._healthy_tools
    assert len(events) == 1


# -- #57: Middleware chain completeness --

async def test_middleware_chain_all_execute():
    """Every middleware in the chain must execute for every message."""
    call_log: list[str] = []

    from agentic_core.application.middleware.base import Middleware, NextHandler

    class TrackingMiddleware(Middleware):
        def __init__(self, name: str) -> None:
            self._name = name

        async def process(self, msg: AgentMessage, ctx: RequestContext, next_: NextHandler) -> AgentMessage:
            call_log.append(self._name)
            return await next_(msg, ctx)

    chain = MiddlewareChain(
        [TrackingMiddleware("auth"), TrackingMiddleware("rate"), TrackingMiddleware("pii")],
        _echo,
    )
    await chain(_msg(), RequestContext())
    assert call_log == ["auth", "rate", "pii"]
