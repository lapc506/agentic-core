from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class GateAction(StrEnum):
    BLOCK = "block"
    WARN = "warn"
    REWRITE = "rewrite"
    HITL = "hitl"


class Gate(BaseModel, frozen=True):
    """Gate value object. Immutable guardrail applied to persona I/O."""

    name: str
    content: str
    action: GateAction
    order: int
