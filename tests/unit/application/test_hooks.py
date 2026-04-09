"""Tests for the event-based HookRunner pipeline (hooks.py)."""

from __future__ import annotations

import pytest

from agentic_core.application.hooks import HookEvent, HookRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def noop_hook(ctx: dict) -> dict:
    """Modifying hook that passes context through unchanged."""
    return ctx


async def void_hook(ctx: dict) -> None:
    """Side-effect hook that returns nothing."""
    ctx["void_called"] = True  # mutates in-place but returns None


async def raising_hook(ctx: dict) -> dict:
    """Hook that always raises."""
    raise RuntimeError("intentional error")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register_single_hook():
    runner = HookRunner()
    runner.register(HookEvent.BEFORE_AGENT_START, noop_hook)
    assert runner.count(HookEvent.BEFORE_AGENT_START) == 1


def test_register_multiple_hooks_same_event():
    runner = HookRunner()
    runner.register(HookEvent.BEFORE_TOOL_CALL, noop_hook)
    runner.register(HookEvent.BEFORE_TOOL_CALL, void_hook)
    assert runner.count(HookEvent.BEFORE_TOOL_CALL) == 2


def test_register_hooks_different_events():
    runner = HookRunner()
    runner.register(HookEvent.BEFORE_AGENT_START, noop_hook)
    runner.register(HookEvent.AFTER_TOOL_CALL, noop_hook)
    runner.register(HookEvent.SESSION_END, void_hook)

    assert runner.count(HookEvent.BEFORE_AGENT_START) == 1
    assert runner.count(HookEvent.AFTER_TOOL_CALL) == 1
    assert runner.count(HookEvent.SESSION_END) == 1
    assert runner.count() == 3  # total across all events


def test_unregister_hook():
    runner = HookRunner()
    runner.register(HookEvent.AGENT_END, noop_hook)
    runner.register(HookEvent.AGENT_END, void_hook)
    runner.unregister(HookEvent.AGENT_END, noop_hook)
    assert runner.count(HookEvent.AGENT_END) == 1


def test_unregister_nonexistent_hook_is_noop():
    runner = HookRunner()
    runner.register(HookEvent.SESSION_END, noop_hook)
    runner.unregister(HookEvent.SESSION_END, void_hook)  # void_hook was never added
    assert runner.count(HookEvent.SESSION_END) == 1


# ---------------------------------------------------------------------------
# run() — modifying pipeline
# ---------------------------------------------------------------------------

async def test_run_no_hooks_returns_copy_of_context():
    runner = HookRunner()
    ctx = {"key": "value"}
    result = await runner.run(HookEvent.BEFORE_AGENT_START, ctx)
    assert result == ctx
    assert result is not ctx  # returns a copy, not the same object


async def test_run_modifying_hook_mutates_context():
    runner = HookRunner()

    async def add_user(ctx: dict) -> dict:
        ctx["user"] = "alice"
        return ctx

    runner.register(HookEvent.BEFORE_AGENT_START, add_user)
    result = await runner.run(HookEvent.BEFORE_AGENT_START, {})
    assert result["user"] == "alice"


async def test_run_hooks_execute_in_registration_order():
    runner = HookRunner()
    order: list[str] = []

    async def hook_a(ctx: dict) -> dict:
        order.append("a")
        return ctx

    async def hook_b(ctx: dict) -> dict:
        order.append("b")
        return ctx

    async def hook_c(ctx: dict) -> dict:
        order.append("c")
        return ctx

    runner.register(HookEvent.MESSAGE_SENDING, hook_a)
    runner.register(HookEvent.MESSAGE_SENDING, hook_b)
    runner.register(HookEvent.MESSAGE_SENDING, hook_c)

    await runner.run(HookEvent.MESSAGE_SENDING, {})
    assert order == ["a", "b", "c"]


async def test_run_chained_modifications():
    """Each hook sees the context modified by the previous hook."""
    runner = HookRunner()

    async def step1(ctx: dict) -> dict:
        ctx["step1"] = True
        return ctx

    async def step2(ctx: dict) -> dict:
        assert ctx.get("step1") is True, "step1 result must propagate to step2"
        ctx["step2"] = True
        return ctx

    runner.register(HookEvent.BEFORE_TOOL_CALL, step1)
    runner.register(HookEvent.BEFORE_TOOL_CALL, step2)

    result = await runner.run(HookEvent.BEFORE_TOOL_CALL, {})
    assert result["step1"] is True
    assert result["step2"] is True


async def test_run_void_returning_hook_does_not_break_chain():
    """A hook returning None should not wipe out the accumulated context."""
    runner = HookRunner()

    async def set_flag(ctx: dict) -> dict:
        ctx["flag"] = True
        return ctx

    async def side_effect_only(ctx: dict) -> None:
        # returns None; context from previous hook must survive
        pass

    async def verify(ctx: dict) -> dict:
        assert ctx.get("flag") is True, "context must survive a None-returning hook"
        return ctx

    runner.register(HookEvent.AFTER_TOOL_CALL, set_flag)
    runner.register(HookEvent.AFTER_TOOL_CALL, side_effect_only)
    runner.register(HookEvent.AFTER_TOOL_CALL, verify)

    result = await runner.run(HookEvent.AFTER_TOOL_CALL, {})
    assert result["flag"] is True


async def test_run_reraises_exceptions():
    runner = HookRunner()
    runner.register(HookEvent.BEFORE_AGENT_START, raising_hook)

    with pytest.raises(RuntimeError, match="intentional error"):
        await runner.run(HookEvent.BEFORE_AGENT_START, {})


# ---------------------------------------------------------------------------
# run_void() — fire-and-forget / side-effect pipeline
# ---------------------------------------------------------------------------

async def test_run_void_calls_all_hooks():
    runner = HookRunner()
    called: list[str] = []

    async def hook_x(ctx: dict) -> None:
        called.append("x")

    async def hook_y(ctx: dict) -> None:
        called.append("y")

    runner.register(HookEvent.SESSION_END, hook_x)
    runner.register(HookEvent.SESSION_END, hook_y)

    await runner.run_void(HookEvent.SESSION_END, {})
    assert called == ["x", "y"]


async def test_run_void_does_not_raise_on_exception():
    """Void hooks swallow exceptions so callers are never blocked."""
    runner = HookRunner()
    runner.register(HookEvent.AGENT_END, raising_hook)

    # Must not raise
    await runner.run_void(HookEvent.AGENT_END, {})


async def test_run_void_continues_after_failing_hook():
    """A failing hook must not prevent subsequent hooks from running."""
    runner = HookRunner()
    called: list[str] = []

    async def hook_fail(ctx: dict) -> None:
        raise ValueError("boom")

    async def hook_ok(ctx: dict) -> None:
        called.append("ok")

    runner.register(HookEvent.AGENT_END, hook_fail)
    runner.register(HookEvent.AGENT_END, hook_ok)

    await runner.run_void(HookEvent.AGENT_END, {})
    assert called == ["ok"]


async def test_run_void_no_hooks_is_noop():
    runner = HookRunner()
    await runner.run_void(HookEvent.SESSION_END, {"a": 1})  # must not raise


async def test_run_void_does_not_return_modified_context():
    """run_void always returns None, regardless of hook return values."""
    runner = HookRunner()

    async def modifying_hook(ctx: dict) -> dict:
        ctx["injected"] = True
        return ctx

    runner.register(HookEvent.MESSAGE_SENDING, modifying_hook)
    result = await runner.run_void(HookEvent.MESSAGE_SENDING, {})
    assert result is None


# ---------------------------------------------------------------------------
# All new HookEvent values are present
# ---------------------------------------------------------------------------

def test_all_lifecycle_events_defined():
    expected = {
        "before_agent_start",
        "before_tool_call",
        "after_tool_call",
        "message_sending",
        "agent_end",
        "session_end",
    }
    actual = {e.value for e in HookEvent}
    assert expected.issubset(actual)


# ---------------------------------------------------------------------------
# Backward-compatibility: original HookRegistry still works
# ---------------------------------------------------------------------------

async def test_hook_registry_still_works():
    """Sanity check that the pre-existing HookRegistry API is unchanged."""
    from agentic_core.application.hooks import (
        HookContext,
        HookRegistry,
        HookResult,
        HookVerdict,
    )

    registry = HookRegistry()

    async def blocking_hook(ctx: HookContext) -> HookResult:
        if ctx.tool_args.get("deny"):
            return HookResult(verdict=HookVerdict.BLOCK, reason="denied")
        return HookResult()

    registry.register(HookEvent.PRE_TOOL_USE, blocking_hook)

    allowed_ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_args={"deny": False})
    result = await registry.run(allowed_ctx)
    assert result.verdict == HookVerdict.ALLOW

    blocked_ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_args={"deny": True})
    result = await registry.run(blocked_ctx)
    assert result.verdict == HookVerdict.BLOCK
    assert result.reason == "denied"
