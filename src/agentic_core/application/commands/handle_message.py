from __future__ import annotations

from collections.abc import AsyncIterator

from agentic_core.application.ports.memory import MemoryPort
from agentic_core.application.ports.session import SessionPort
from agentic_core.domain.value_objects.messages import AgentMessage
from agentic_core.shared_kernel.events import EventBus


class HandleMessageCommand:
    __slots__ = ("session_id", "persona_id", "content", "user_id", "trace_id")

    def __init__(
        self, session_id: str, persona_id: str, content: str,
        user_id: str, trace_id: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.persona_id = persona_id
        self.content = content
        self.user_id = user_id
        self.trace_id = trace_id


class HandleMessageHandler:
    def __init__(
        self,
        memory_port: MemoryPort,
        session_port: SessionPort,
        event_bus: EventBus,
    ) -> None:
        self._memory = memory_port
        self._session = session_port
        self._event_bus = event_bus

    async def execute(self, cmd: HandleMessageCommand) -> AsyncIterator[AgentMessage]:
        session = await self._session.get(cmd.session_id)
        if session is None:
            raise ValueError(f"Session {cmd.session_id} not found")

        # Phase 2: will invoke LangGraph here and stream tokens
        # For now, yield nothing (skeleton)
        return
        yield  # type: ignore[misc]  # makes this an async generator
