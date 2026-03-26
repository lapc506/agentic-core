from __future__ import annotations

from agentic_core.application.hooks import (
    Hook,
    HookContext,
    HookEvent,
    HookRegistry,
    HookResult,
    HookVerdict,
)


async def _allow_hook(ctx: HookContext) -> HookResult:
    return HookResult()


async def _block_hook(ctx: HookContext) -> HookResult:
    return HookResult(verdict=HookVerdict.BLOCK, reason="blocked by test")


async def _modify_args_hook(ctx: HookContext) -> HookResult:
    return HookResult(modified_args={"sanitized": True})


async def _failing_hook(ctx: HookContext) -> HookResult:
    raise RuntimeError("hook crashed")


# --- Registry basics ---


def test_empty_registry_count():
    reg = HookRegistry()
    assert reg.count() == 0
    assert reg.count(HookEvent.PRE_TOOL_USE) == 0


def test_register_and_count():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _allow_hook)
    reg.register(HookEvent.POST_TOOL_USE, _allow_hook)
    assert reg.count() == 2
    assert reg.count(HookEvent.PRE_TOOL_USE) == 1


def test_unregister():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _allow_hook)
    reg.unregister(HookEvent.PRE_TOOL_USE, _allow_hook)
    assert reg.count(HookEvent.PRE_TOOL_USE) == 0


# --- Run behavior ---


async def test_run_no_hooks_allows():
    reg = HookRegistry()
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="test")
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


async def test_run_allow_hook():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _allow_hook)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="test")
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


async def test_run_block_hook():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _block_hook)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_name="set_ph")
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.BLOCK
    assert result.reason == "blocked by test"


async def test_block_stops_chain():
    """First BLOCK wins; subsequent hooks don't run."""
    call_count = 0

    async def counting_hook(ctx: HookContext) -> HookResult:
        nonlocal call_count
        call_count += 1
        return HookResult()

    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _block_hook, priority=0)
    reg.register(HookEvent.PRE_TOOL_USE, counting_hook, priority=1)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE)
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.BLOCK
    assert call_count == 0


async def test_allow_then_block():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _allow_hook, priority=0)
    reg.register(HookEvent.PRE_TOOL_USE, _block_hook, priority=1)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE)
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.BLOCK


async def test_priority_ordering():
    """Lower priority number runs first."""
    order: list[str] = []

    async def hook_a(ctx: HookContext) -> HookResult:
        order.append("a")
        return HookResult()

    async def hook_b(ctx: HookContext) -> HookResult:
        order.append("b")
        return HookResult()

    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, hook_b, priority=10)
    reg.register(HookEvent.PRE_TOOL_USE, hook_a, priority=1)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE)
    await reg.run(ctx)
    assert order == ["a", "b"]


async def test_failing_hook_does_not_block():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _failing_hook)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE)
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


async def test_modify_args_returned():
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _modify_args_hook)
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE, tool_args={"raw": True})
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW
    assert result.modified_args == {"sanitized": True}


# --- Hook events ---


async def test_post_tool_use_event():
    reg = HookRegistry()
    reg.register(HookEvent.POST_TOOL_USE, _allow_hook)
    ctx = HookContext(
        event=HookEvent.POST_TOOL_USE,
        tool_name="search",
        tool_result_success=True,
        tool_result_output="found 3 results",
    )
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


async def test_session_stop_event():
    reg = HookRegistry()
    reg.register(HookEvent.SESSION_STOP, _allow_hook)
    ctx = HookContext(
        event=HookEvent.SESSION_STOP,
        session_id="sess_123",
    )
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


async def test_on_error_event():
    reg = HookRegistry()
    reg.register(HookEvent.ON_ERROR, _allow_hook)
    ctx = HookContext(
        event=HookEvent.ON_ERROR,
        error="Connection timeout",
    )
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


async def test_hooks_scoped_to_event():
    """Hooks registered for one event don't fire for another."""
    reg = HookRegistry()
    reg.register(HookEvent.PRE_TOOL_USE, _block_hook)
    ctx = HookContext(event=HookEvent.POST_TOOL_USE)
    result = await reg.run(ctx)
    assert result.verdict == HookVerdict.ALLOW


# --- HookContext ---


def test_hook_context_defaults():
    ctx = HookContext(event=HookEvent.PRE_TOOL_USE)
    assert ctx.session_id is None
    assert ctx.persona_id is None
    assert ctx.tool_name is None
    assert ctx.tool_args == {}
    assert ctx.error is None


def test_hook_context_full():
    ctx = HookContext(
        event=HookEvent.PRE_TOOL_USE,
        session_id="s1",
        persona_id="support-agent",
        tool_name="mcp_stripe_create_charge",
        tool_args={"amount": 1000},
    )
    assert ctx.tool_name == "mcp_stripe_create_charge"
    assert ctx.tool_args["amount"] == 1000


# --- HookResult ---


def test_hook_result_defaults():
    r = HookResult()
    assert r.verdict == HookVerdict.ALLOW
    assert r.reason is None
    assert r.modified_args is None
