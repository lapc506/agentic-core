from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_core.application.ports.session import SessionPort
    from agentic_core.domain.entities.session import Session


class GetSessionQuery:
    __slots__ = ("session_id",)

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


class GetSessionHandler:
    def __init__(self, session_port: SessionPort) -> None:
        self._session = session_port

    async def execute(self, query: GetSessionQuery) -> Session | None:
        return await self._session.get(query.session_id)
