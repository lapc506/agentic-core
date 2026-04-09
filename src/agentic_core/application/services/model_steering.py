"""Model steering — real-time course correction during agent execution."""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SteeringHint:
    content: str
    priority: str = "normal"  # normal, urgent


class ModelSteeringService:
    def __init__(self, max_hints: int = 10) -> None:
        self._hints: dict[str, deque[SteeringHint]] = {}
        self._max = max_hints

    def add_hint(
        self, session_id: str, content: str, priority: str = "normal"
    ) -> None:
        if session_id not in self._hints:
            self._hints[session_id] = deque(maxlen=self._max)
        self._hints[session_id].append(SteeringHint(content=content, priority=priority))
        logger.info(
            "Steering hint added for session %s: %s", session_id, content[:50]
        )

    def consume_hints(self, session_id: str) -> list[SteeringHint]:
        hints = list(self._hints.get(session_id, []))
        if session_id in self._hints:
            self._hints[session_id].clear()
        return hints

    def has_hints(self, session_id: str) -> bool:
        return bool(self._hints.get(session_id))

    def format_for_context(self, session_id: str) -> str:
        hints = self.consume_hints(session_id)
        if not hints:
            return ""
        parts = ["[User steering hints (apply these to your current approach):"]
        for h in hints:
            prefix = "URGENT: " if h.priority == "urgent" else ""
            parts.append(f"- {prefix}{h.content}")
        parts.append("]")
        return "\n".join(parts)

    def clear(self, session_id: str) -> None:
        self._hints.pop(session_id, None)

    @property
    def active_sessions(self) -> int:
        return sum(1 for hints in self._hints.values() if hints)
