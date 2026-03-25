from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from agentic_core.adapters.primary.grpc.server import AgentServiceServicer, GrpcTransport
from agentic_core.adapters.primary.grpc.generated import agentic_core_pb2
from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.entities.session import Session
from agentic_core.domain.enums import SessionState


class FakeContext:
    def __init__(self) -> None:
        self.aborted = False
        self.abort_code = None
        self.abort_message = None

    async def abort(self, code: object, message: str) -> None:
        self.aborted = True
        self.abort_code = code
        self.abort_message = message


async def test_health_check():
    servicer = AgentServiceServicer()
    ctx = FakeContext()
    resp = await servicer.HealthCheck(agentic_core_pb2.Empty(), ctx)
    assert resp.healthy is True
    assert resp.version == "0.1.0"


async def test_create_session():
    servicer = AgentServiceServicer()
    session = Session.create("s1", "support", "u1")
    servicer.on_create_session = AsyncMock(return_value=session)

    ctx = FakeContext()
    req = agentic_core_pb2.CreateSessionRequest(persona_id="support", user_id="u1")
    resp = await servicer.CreateSession(req, ctx)

    assert resp.session_id == "s1"
    assert resp.persona_id == "support"
    assert resp.state == "active"


async def test_get_session_found():
    servicer = AgentServiceServicer()
    session = Session.create("s1", "support", "u1")
    servicer.on_get_session = AsyncMock(return_value=session)

    ctx = FakeContext()
    req = agentic_core_pb2.GetSessionRequest(session_id="s1")
    resp = await servicer.GetSession(req, ctx)

    assert resp.session_id == "s1"
    assert not ctx.aborted


async def test_get_session_not_found():
    servicer = AgentServiceServicer()
    servicer.on_get_session = AsyncMock(return_value=None)

    ctx = FakeContext()
    req = agentic_core_pb2.GetSessionRequest(session_id="x")
    await servicer.GetSession(req, ctx)

    assert ctx.aborted


async def test_list_personas():
    servicer = AgentServiceServicer()
    personas = [
        Persona(name="support", role="Support", description="Support agent"),
        Persona(name="analyst", role="Analyst", description="Analyst agent"),
    ]
    servicer.on_list_personas = AsyncMock(return_value=personas)

    ctx = FakeContext()
    resp = await servicer.ListPersonas(agentic_core_pb2.Empty(), ctx)

    assert len(resp.personas) == 2
    assert resp.personas[0].name == "support"
    assert resp.personas[1].graph_template == "react"


async def test_send_message_not_configured():
    servicer = AgentServiceServicer()
    ctx = FakeContext()
    req = agentic_core_pb2.AgentRequest(session_id="s1", persona_id="p", content="hi")

    responses = []
    async for resp in servicer.SendMessage(req, ctx):
        responses.append(resp)

    assert len(responses) == 1
    assert responses[0].error.code == "internal_error"


async def test_grpc_transport_init():
    t = GrpcTransport(host="127.0.0.1", port=50099)
    assert not t.is_running
    assert t.servicer is not None
