from __future__ import annotations

from datetime import UTC, datetime

import uuid_utils

from agentic_core.application.middleware.base import (
    Middleware,
    MiddlewareChain,
    NextHandler,
    RequestContext,
)
from agentic_core.application.middleware.tracing import TracingMiddleware
from agentic_core.domain.value_objects.messages import AgentMessage


def _make_msg(**overrides: object) -> AgentMessage:
    defaults: dict = {
        "id": str(uuid_utils.uuid7()),
        "session_id": "s1",
        "persona_id": "p1",
        "role": "user",
        "content": "hello",
        "metadata": {},
        "timestamp": datetime.now(UTC),
    }
    defaults.update(overrides)
    return AgentMessage(**defaults)


class AppendMiddleware(Middleware):
    def __init__(self, tag: str) -> None:
        self._tag = tag

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        ctx.extra.setdefault("order", []).append(f"{self._tag}_before")
        result = await next_(message, ctx)
        ctx.extra.setdefault("order", []).append(f"{self._tag}_after")
        return result


async def test_chain_executes_in_order():
    msg = _make_msg()
    ctx = RequestContext()

    async def handler(m: AgentMessage, c: RequestContext) -> AgentMessage:
        c.extra.setdefault("order", []).append("handler")
        return m

    chain = MiddlewareChain(
        [AppendMiddleware("A"), AppendMiddleware("B"), AppendMiddleware("C")],
        handler,
    )
    await chain(msg, ctx)
    assert ctx.extra["order"] == [
        "A_before", "B_before", "C_before",
        "handler",
        "C_after", "B_after", "A_after",
    ]


async def test_empty_chain():
    msg = _make_msg()
    ctx = RequestContext()
    called = False

    async def handler(m: AgentMessage, c: RequestContext) -> AgentMessage:
        nonlocal called
        called = True
        return m

    chain = MiddlewareChain([], handler)
    await chain(msg, ctx)
    assert called


async def test_tracing_middleware_noop():
    msg = _make_msg()
    ctx = RequestContext()

    async def handler(m: AgentMessage, c: RequestContext) -> AgentMessage:
        return m

    mw = TracingMiddleware(tracing_port=None)
    chain = MiddlewareChain([mw], handler)
    result = await chain(msg, ctx)
    assert result == msg
    assert ctx.trace_id is not None  # trace_id was generated


async def test_tracing_middleware_with_port():
    from unittest.mock import MagicMock

    mock_port = MagicMock()
    mock_port.start_span.return_value = "span_obj"

    msg = _make_msg()
    ctx = RequestContext()

    async def handler(m: AgentMessage, c: RequestContext) -> AgentMessage:
        return m

    mw = TracingMiddleware(tracing_port=mock_port)
    chain = MiddlewareChain([mw], handler)
    await chain(msg, ctx)

    mock_port.start_span.assert_called_once()
    mock_port.end_span.assert_called_once_with("span_obj")
