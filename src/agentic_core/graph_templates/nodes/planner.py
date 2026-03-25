from __future__ import annotations

from typing import Any


class PlannerNode:
    """Generates a multi-step plan from user input. Used by plan-execute and orchestrator."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        # Phase 2 skeleton: LangGraph will inject LLM here
        state.setdefault("plan", [])
        return state
