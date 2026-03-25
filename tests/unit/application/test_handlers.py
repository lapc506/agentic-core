from __future__ import annotations

import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

from agentic_core.application.commands.create_session import (
    CreateSessionCommand,
    CreateSessionHandler,
)
from agentic_core.application.commands.handle_message import (
    HandleMessageCommand,
    HandleMessageHandler,
)
from agentic_core.application.commands.resume_hitl import (
    ResumeHITLCommand,
    ResumeHITLHandler,
)
from agentic_core.application.queries.get_session import (
    GetSessionHandler,
    GetSessionQuery,
)
from agentic_core.application.queries.list_personas import (
    ListPersonasHandler,
    ListPersonasQuery,
)
from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.entities.session import Session
from agentic_core.domain.enums import SessionState
from agentic_core.domain.services.routing import RoutingService
from agentic_core.shared_kernel.events import EventBus


# -- CreateSession --

async def test_create_session_handler():
    session_port = AsyncMock()
    event_bus = EventBus()
    created_events: list[Any] = []

    async def on_created(event: Any) -> None:
        created_events.append(event)

    from agentic_core.domain.events.domain_events import SessionCreated
    event_bus.subscribe(SessionCreated, on_created)

    handler = CreateSessionHandler(session_port, event_bus)
    cmd = CreateSessionCommand(persona_id="support", user_id="u1")
    session = await handler.execute(cmd)

    assert session.state == SessionState.ACTIVE
    assert session.persona_id == "support"
    assert session.user_id == "u1"
    session_port.create.assert_awaited_once()
    assert len(created_events) == 1


# -- HandleMessage --

async def test_handle_message_session_not_found():
    memory_port = AsyncMock()
    session_port = AsyncMock()
    session_port.get.return_value = None
    event_bus = EventBus()

    handler = HandleMessageHandler(memory_port, session_port, event_bus)
    cmd = HandleMessageCommand(
        session_id="nonexistent", persona_id="p", content="hi", user_id="u"
    )
    with pytest.raises(ValueError, match="not found"):
        async for _ in handler.execute(cmd):
            pass


async def test_handle_message_with_valid_session():
    memory_port = AsyncMock()
    session_port = AsyncMock()
    session_port.get.return_value = Session.create("s1", "support", "u1")
    event_bus = EventBus()

    handler = HandleMessageHandler(memory_port, session_port, event_bus)
    cmd = HandleMessageCommand(
        session_id="s1", persona_id="support", content="hello", user_id="u1"
    )
    tokens = [msg async for msg in handler.execute(cmd)]
    # Phase 1 skeleton yields nothing
    assert tokens == []


# -- ResumeHITL --

async def test_resume_hitl_transitions_to_active():
    session = Session.create("s1", "support", "u1")
    session.transition_to(SessionState.ESCALATED)

    session_port = AsyncMock()
    session_port.get.return_value = session

    handler = ResumeHITLHandler(session_port)
    cmd = ResumeHITLCommand(session_id="s1", human_response="Approved")
    result = await handler.execute(cmd)

    assert result.state == SessionState.ACTIVE
    session_port.update.assert_awaited_once()


async def test_resume_hitl_session_not_found():
    session_port = AsyncMock()
    session_port.get.return_value = None

    handler = ResumeHITLHandler(session_port)
    cmd = ResumeHITLCommand(session_id="x", human_response="y")
    with pytest.raises(ValueError, match="not found"):
        await handler.execute(cmd)


# -- GetSession --

async def test_get_session_found():
    session = Session.create("s1", "support", "u1")
    session_port = AsyncMock()
    session_port.get.return_value = session

    handler = GetSessionHandler(session_port)
    result = await handler.execute(GetSessionQuery("s1"))
    assert result is not None
    assert result.id == "s1"


async def test_get_session_not_found():
    session_port = AsyncMock()
    session_port.get.return_value = None

    handler = GetSessionHandler(session_port)
    result = await handler.execute(GetSessionQuery("x"))
    assert result is None


# -- ListPersonas --

async def test_list_personas():
    routing = RoutingService()
    routing.register(Persona(name="a", role="r", description="d"))
    routing.register(Persona(name="b", role="r", description="d"))

    handler = ListPersonasHandler(routing)
    result = await handler.execute(ListPersonasQuery())
    assert len(result) == 2
    assert {p.name for p in result} == {"a", "b"}
