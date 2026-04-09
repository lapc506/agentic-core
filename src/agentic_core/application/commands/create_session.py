from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import uuid_utils

from agentic_core.domain.entities.session import Session
from agentic_core.domain.events.domain_events import SessionCreated

if TYPE_CHECKING:
    from agentic_core.application.ports.session import SessionPort
    from agentic_core.shared_kernel.events import EventBus


class CreateSessionCommand:
    __slots__ = ("persona_id", "user_id")

    def __init__(self, persona_id: str, user_id: str) -> None:
        self.persona_id = persona_id
        self.user_id = user_id


class CreateSessionHandler:
    def __init__(self, session_port: SessionPort, event_bus: EventBus) -> None:
        self._session = session_port
        self._event_bus = event_bus

    async def execute(self, cmd: CreateSessionCommand) -> Session:
        session_id = str(uuid_utils.uuid7())
        session = Session.create(session_id, cmd.persona_id, cmd.user_id)
        await self._session.create(session)
        await self._event_bus.publish(
            SessionCreated(
                session_id=session_id,
                persona_id=cmd.persona_id,
                user_id=cmd.user_id,
                timestamp=datetime.now(UTC),
            )
        )
        return session
