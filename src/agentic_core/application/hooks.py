"""Hook system for granular execution control.

Hooks complement middleware: while middleware wraps the full request lifecycle,
hooks fire at specific points (before/after tool calls, on session stop, on error)
and can BLOCK execution by returning HookVerdict.BLOCK.

Usage:
    registry = HookRegistry()

    async def validate_ph_range(ctx: HookContext) -> HookResult:
        if ctx.tool_name == "set_ph" and ctx.tool_args.get("value", 7) < 5.5:
            return HookResult(verdict=HookVerdict.BLOCK, reason="pH too low")
        return HookResult()

    registry.register(HookEvent.PRE_TOOL_USE, validate_ph_range)

    result = await registry.run(HookContext(
        event=HookEvent.PRE_TOOL_USE,
        tool_name="set_ph",
        tool_args={"value": 4.0},
    ))
    assert result.verdict == HookVerdict.BLOCK
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HookEvent(str, Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_STOP = "session_stop"
    ON_ERROR = "on_error"


class HookVerdict(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


class HookContext(BaseModel):
    event: HookEvent
    session_id: str | None = None
    persona_id: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] = {}
    tool_result_output: str | None = None
    tool_result_success: bool | None = None
    error: str | None = None


class HookResult(BaseModel):
    verdict: HookVerdict = HookVerdict.ALLOW
    reason: str | None = None
    modified_args: dict[str, Any] | None = None


Hook = Callable[[HookContext], Awaitable[HookResult]]


class HookRegistry:
    """Registry for execution hooks. First BLOCK verdict wins."""

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[tuple[int, Hook]]] = defaultdict(list)

    def register(
        self, event: HookEvent, hook: Hook, *, priority: int = 0,
    ) -> None:
        self._hooks[event].append((priority, hook))
        self._hooks[event].sort(key=lambda x: x[0])

    def unregister(self, event: HookEvent, hook: Hook) -> None:
        self._hooks[event] = [
            (p, h) for p, h in self._hooks[event] if h is not hook
        ]

    async def run(self, context: HookContext) -> HookResult:
        hooks = self._hooks.get(context.event, [])
        last_modified_args: dict[str, Any] | None = None
        for _priority, hook in hooks:
            try:
                result = await hook(context)
                if result.verdict == HookVerdict.BLOCK:
                    logger.info(
                        "Hook blocked %s: %s", context.event.value, result.reason,
                    )
                    return result
                if result.modified_args is not None:
                    last_modified_args = result.modified_args
            except Exception:
                logger.exception("Hook failed for %s", context.event.value)
        return HookResult(modified_args=last_modified_args)

    def count(self, event: HookEvent | None = None) -> int:
        if event is not None:
            return len(self._hooks[event])
        return sum(len(hooks) for hooks in self._hooks.values())
