from __future__ import annotations

from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.services.routing import RoutingService


class ListPersonasQuery:
    pass


class ListPersonasHandler:
    def __init__(self, routing_service: RoutingService) -> None:
        self._routing = routing_service

    async def execute(self, query: ListPersonasQuery) -> list[Persona]:
        return self._routing.list_personas()
