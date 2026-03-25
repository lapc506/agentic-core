from __future__ import annotations

from typing import Any


class ActorNode:
    """Executes tools/actions based on current plan step or LLM decision."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        state.setdefault("actions_taken", [])
        return state
