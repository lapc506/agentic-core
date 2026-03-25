from __future__ import annotations

from typing import Any


class ReflectorNode:
    """Self-critiques the last action output. Used by reflexion template."""

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        state.setdefault("reflections", [])
        return state
