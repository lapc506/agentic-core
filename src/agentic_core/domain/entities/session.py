from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agentic_core.domain.enums import SessionState

_VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.ACTIVE: {
        SessionState.PAUSED,
        SessionState.ESCALATED,
        SessionState.COMPLETED,
    },
    SessionState.PAUSED: {SessionState.ACTIVE, SessionState.COMPLETED},
    SessionState.ESCALATED: {SessionState.ACTIVE},
    SessionState.COMPLETED: set(),
}


class InvalidTransitionError(Exception):
    pass


class Session:
    __slots__ = (
        "id",
        "persona_id",
        "user_id",
        "state",
        "checkpoint_id",
        "created_at",
        "updated_at",
        "metadata",
    )

    def __init__(
        self,
        *,
        id: str,
        persona_id: str,
        user_id: str,
        state: SessionState,
        checkpoint_id: str | None,
        created_at: datetime,
        updated_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        self.id = id
        self.persona_id = persona_id
        self.user_id = user_id
        self.state = state
        self.checkpoint_id = checkpoint_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata

    @classmethod
    def create(cls, id: str, persona_id: str, user_id: str) -> Session:
        now = datetime.now(timezone.utc)
        return cls(
            id=id,
            persona_id=persona_id,
            user_id=user_id,
            state=SessionState.ACTIVE,
            checkpoint_id=None,
            created_at=now,
            updated_at=now,
            metadata={},
        )

    def transition_to(self, new_state: SessionState) -> None:
        if new_state not in _VALID_TRANSITIONS[self.state]:
            raise InvalidTransitionError(
                f"Cannot transition from {self.state.value} to {new_state.value}"
            )
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
