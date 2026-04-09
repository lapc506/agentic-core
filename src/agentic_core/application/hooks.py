"""Hook system for granular execution control.

Hooks complement middleware: while middleware wraps the full request lifecycle,
hooks fire at specific points (before/after tool calls, on session stop, on error)
and can BLOCK execution by returning HookVerdict.BLOCK.

Two complementary APIs are provided:

1. ``HookRegistry`` — original low-level API that works with ``HookContext`` /
   ``HookResult`` objects and supports BLOCK verdicts.

2. ``HookRunner`` — higher-level event-based pipeline where each hook is a plain
   ``async callable`` that receives and returns a plain ``dict``.  Hooks can be
   "modifying" (return updated context dict) or "void" (side-effects only, should
   return ``None``).

Usage — HookRegistry (original)::

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

Usage — HookRunner (event-based pipeline)::

    runner = HookRunner()

    async def inject_user(ctx: dict) -> dict:
        ctx["user"] = "alice"
        return ctx

    async def audit_log(ctx: dict) -> None:
        print("tool called:", ctx.get("tool_name"))

    runner.register(HookEvent.BEFORE_AGENT_START, inject_user)
    runner.register(HookEvent.BEFORE_TOOL_CALL, audit_log)

    ctx = await runner.run(HookEvent.BEFORE_AGENT_START, {"session_id": "s1"})
    assert ctx["user"] == "alice"

    await runner.run_void(HookEvent.BEFORE_TOOL_CALL, {"tool_name": "search"})
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HookEvent(StrEnum):
    # --- original events (HookRegistry) ---
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_STOP = "session_stop"
    ON_ERROR = "on_error"

    # --- lifecycle events (HookRunner) ---
    BEFORE_AGENT_START = "before_agent_start"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    MESSAGE_SENDING = "message_sending"
    AGENT_END = "agent_end"
    SESSION_END = "session_end"


class HookVerdict(StrEnum):
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


# ---------------------------------------------------------------------------
# HookRunner — event-based pipeline (higher-level API)
# ---------------------------------------------------------------------------

# A pipeline hook is an async callable that receives a context dict and either
# returns an updated dict (modifying hook) or returns None (void hook).
PipelineHook = Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]


class HookRunner:
    """Event-based hook pipeline.

    Hooks are registered per ``HookEvent``.  They are executed in registration
    order.

    * **Modifying hooks** return an updated ``dict``; the returned value becomes
      the context passed to the next hook in the chain.
    * **Void hooks** return ``None``; the context is forwarded unchanged.

    Use ``run`` when you need the (possibly mutated) context back.
    Use ``run_void`` for fire-and-forget side-effect hooks — exceptions are
    swallowed and logged so they never block the caller.
    """

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[PipelineHook]] = defaultdict(list)

    def register(self, event: HookEvent, hook: PipelineHook) -> None:
        """Register *hook* to be called when *event* fires."""
        self._hooks[event].append(hook)

    def unregister(self, event: HookEvent, hook: PipelineHook) -> None:
        """Remove a previously registered hook (no-op if not found)."""
        self._hooks[event] = [h for h in self._hooks[event] if h is not hook]

    async def run(self, event: HookEvent, context: dict[str, Any]) -> dict[str, Any]:
        """Run all hooks for *event* and return the (possibly modified) context.

        Each modifying hook's return value becomes the input for the next hook.
        Void hooks (returning ``None``) are skipped for context propagation.
        Exceptions raised by individual hooks are logged and re-raised so that
        callers can decide how to handle failures in modifying pipelines.
        """
        current: dict[str, Any] = dict(context)
        for hook in self._hooks.get(event, []):
            try:
                result = await hook(current)
                if result is not None:
                    current = result
            except Exception:
                logger.exception(
                    "HookRunner: modifying hook failed for event '%s'", event.value,
                )
                raise
        return current

    async def run_void(self, event: HookEvent, context: dict[str, Any]) -> None:
        """Run all hooks for *event* as fire-and-forget side effects.

        Exceptions are caught, logged, and swallowed so that a failing hook
        never blocks the caller.  The context dict is passed to each hook but
        any return value is ignored.
        """
        snapshot: dict[str, Any] = dict(context)
        for hook in self._hooks.get(event, []):
            try:
                await hook(snapshot)
            except Exception:
                logger.exception(
                    "HookRunner: void hook failed for event '%s'", event.value,
                )

    def count(self, event: HookEvent | None = None) -> int:
        """Return the number of registered hooks, optionally filtered by event."""
        if event is not None:
            return len(self._hooks.get(event, []))
        return sum(len(hooks) for hooks in self._hooks.values())
