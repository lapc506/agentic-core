from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import uuid_utils
from pydantic import BaseModel, field_validator

if TYPE_CHECKING:
    from datetime import datetime


class AgentMessage(BaseModel, frozen=True):
    """Core message value object. Frozen at the model level (field reassignment prevented).
    Metadata dict contents are mutable by design (consumers may need to read nested structures)."""

    id: str
    session_id: str
    persona_id: str
    role: Literal["user", "assistant", "system", "tool", "human_escalation"]
    content: str
    metadata: dict[str, Any]
    timestamp: datetime
    trace_id: str | None = None

    @field_validator("id")
    @classmethod
    def validate_uuid_v7(cls, v: str) -> str:
        parsed = uuid_utils.UUID(v)
        if parsed.version != 7:
            raise ValueError(f"Expected UUID v7, got v{parsed.version}")
        return v
