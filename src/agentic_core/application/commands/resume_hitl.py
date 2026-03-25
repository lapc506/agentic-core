from __future__ import annotations

from agentic_core.application.ports.session import SessionPort
from agentic_core.domain.entities.session import Session
from agentic_core.domain.enums import SessionState


class ResumeHITLCommand:
    __slots__ = ("session_id", "human_response")

    def __init__(self, session_id: str, human_response: str) -> None:
        self.session_id = session_id
        self.human_response = human_response


class ResumeHITLHandler:
    def __init__(self, session_port: SessionPort) -> None:
        self._session = session_port

    async def execute(self, cmd: ResumeHITLCommand) -> Session:
        session = await self._session.get(cmd.session_id)
        if session is None:
            raise ValueError(f"Session {cmd.session_id} not found")
        session.transition_to(SessionState.ACTIVE)
        await self._session.update(session)
        # Phase 2: will load checkpoint, inject human response, resume graph
        return session
