from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
import uuid_utils

from agentic_core.application.middleware.auth import AuthMiddleware
from agentic_core.application.middleware.base import MiddlewareChain, RequestContext
from agentic_core.application.middleware.metrics import MetricsMiddleware
from agentic_core.application.middleware.pii_redaction import PIIRedactionMiddleware, redact_pii
from agentic_core.application.middleware.rate_limit import RateLimitExceeded, RateLimitMiddleware
from agentic_core.domain.value_objects.messages import AgentMessage


def _msg(content: str = "hello", **meta: object) -> AgentMessage:
    return AgentMessage(
        id=str(uuid_utils.uuid7()),
        session_id="s1",
        persona_id="p1",
        role="user",
        content=content,
        metadata=meta,
        timestamp=datetime.now(UTC),
    )


async def _echo(message: AgentMessage, ctx: RequestContext) -> AgentMessage:
    return message


# -- PII Redaction --

def test_redact_email():
    assert "[REDACTED]" in redact_pii("contact me at john@example.com")


def test_redact_phone():
    assert "[REDACTED]" in redact_pii("call me at 555-123-4567")


def test_redact_ssn():
    assert "[REDACTED]" in redact_pii("my SSN is 123-45-6789")


def test_redact_credit_card():
    assert "[REDACTED]" in redact_pii("card 4111-1111-1111-1111")


def test_redact_no_pii():
    text = "nothing sensitive here"
    assert redact_pii(text) == text


async def test_pii_middleware_redacts_input():
    mw = PIIRedactionMiddleware()
    chain = MiddlewareChain([mw], _echo)
    msg = _msg(content="email me at test@example.com")
    ctx = RequestContext()
    result = await chain(msg, ctx)
    assert "test@example.com" not in result.content
    assert "[REDACTED]" in result.content


async def test_pii_middleware_disabled():
    mw = PIIRedactionMiddleware(enabled=False)
    chain = MiddlewareChain([mw], _echo)
    msg = _msg(content="email me at test@example.com")
    result = await chain(msg, RequestContext())
    assert "test@example.com" in result.content


# -- Auth --

async def test_auth_no_keys_configured():
    mw = AuthMiddleware()
    chain = MiddlewareChain([mw], _echo)
    result = await chain(_msg(), RequestContext())
    assert result is not None


async def test_auth_valid_api_key():
    mw = AuthMiddleware(api_keys={"secret123"})
    chain = MiddlewareChain([mw], _echo)
    msg = _msg(x_api_key="secret123")
    ctx = RequestContext()
    result = await chain(msg, ctx)
    assert result is not None
    assert ctx.user_id == "api_key_user"


async def test_auth_invalid_api_key():
    mw = AuthMiddleware(api_keys={"secret123"})
    chain = MiddlewareChain([mw], _echo)
    msg = _msg(x_api_key="wrong")
    with pytest.raises(PermissionError):
        await chain(msg, RequestContext())


async def test_auth_jwt_passthrough():
    mw = AuthMiddleware(api_keys={"key"})
    chain = MiddlewareChain([mw], _echo)
    msg = _msg(authorization="Bearer token123")
    ctx = RequestContext()
    await chain(msg, ctx)
    assert ctx.user_id == "jwt_user"


# -- Rate Limit --

async def test_rate_limit_allows_under_limit():
    mw = RateLimitMiddleware(requests_per_minute=5)
    chain = MiddlewareChain([mw], _echo)
    ctx = RequestContext(user_id="u1")
    for _ in range(5):
        await chain(_msg(), ctx)


async def test_rate_limit_blocks_over_limit():
    mw = RateLimitMiddleware(requests_per_minute=3)
    chain = MiddlewareChain([mw], _echo)
    ctx = RequestContext(user_id="u1")
    for _ in range(3):
        await chain(_msg(), ctx)
    with pytest.raises(RateLimitExceeded):
        await chain(_msg(), ctx)


# -- Metrics --

async def test_metrics_records_success():
    mock_port = MagicMock()
    mw = MetricsMiddleware(metrics_port=mock_port)
    chain = MiddlewareChain([mw], _echo)
    await chain(_msg(), RequestContext(persona_id="p1"))

    mock_port.increment_counter.assert_called_once()
    call_args = mock_port.increment_counter.call_args
    assert call_args[0][0] == "agent_requests_total"
    assert call_args[0][1]["status"] == "success"
    mock_port.observe_histogram.assert_called_once()


async def test_metrics_records_error():
    mock_port = MagicMock()
    mw = MetricsMiddleware(metrics_port=mock_port)

    async def failing_handler(msg: AgentMessage, ctx: RequestContext) -> AgentMessage:
        raise ValueError("boom")

    chain = MiddlewareChain([mw], failing_handler)
    with pytest.raises(ValueError):
        await chain(_msg(), RequestContext(persona_id="p1"))

    # Should record error counter + histogram
    assert mock_port.increment_counter.call_count == 2  # requests_total + errors_total


async def test_metrics_noop():
    mw = MetricsMiddleware(metrics_port=None)
    chain = MiddlewareChain([mw], _echo)
    result = await chain(_msg(), RequestContext())
    assert result is not None
