from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_core.domain.entities.persona import Persona


class PersonaNotFoundError(Exception):
    pass


class RoutingService:
    def __init__(self) -> None:
        self._personas: dict[str, Persona] = {}

    def register(self, persona: Persona) -> None:
        self._personas[persona.name] = persona

    def resolve(self, persona_id: str) -> Persona:
        persona = self._personas.get(persona_id)
        if persona is None:
            raise PersonaNotFoundError(f"Persona '{persona_id}' not found")
        return persona

    def list_personas(self) -> list[Persona]:
        return list(self._personas.values())
