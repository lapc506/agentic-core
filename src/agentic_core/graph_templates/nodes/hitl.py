from __future__ import annotations

from typing import Any


class HITLNode:
    """Human-in-the-loop checkpoint. Pauses graph for human input."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        state["awaiting_human"] = True
        return state
