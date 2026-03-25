from __future__ import annotations

from typing import Any


class RouterNode:
    """Routes to sub-agents based on input classification. Used by supervisor template."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        state.setdefault("routed_to", None)
        return state
