from datetime import UTC, datetime

from agentic_core.domain.events.domain_events import (
    ErrorBudgetExhausted,
    HumanEscalationRequested,
    MessageProcessed,
    SessionCreated,
    SkillOptimized,
    SLOBreached,
    ToolDegraded,
    ToolRecovered,
)


def _now() -> datetime:
    return datetime.now(UTC)


def test_message_processed():
    e = MessageProcessed(
        session_id="s1", persona_id="p1", latency_ms=123.4, token_count=500,
        timestamp=_now(),
    )
    assert e.latency_ms == 123.4
    assert e.token_count == 500


def test_session_created():
    e = SessionCreated(session_id="s1", persona_id="p1", user_id="u1", timestamp=_now())
    assert e.user_id == "u1"


def test_slo_breached():
    e = SLOBreached(
        persona_id="p1", sli_name="latency_p99", current_value=6.0, target_value=5.0,
        timestamp=_now(),
    )
    assert e.current_value > e.target_value


def test_skill_optimized():
    e = SkillOptimized(
        skill_name="summarizer", old_score=0.7, new_score=0.9, version=3,
        timestamp=_now(),
    )
    assert e.new_score > e.old_score


def test_human_escalation_requested():
    e = HumanEscalationRequested(
        session_id="s1", persona_id="p1", prompt="Approve refund?", reason="billing > 500",
        timestamp=_now(),
    )
    assert e.prompt == "Approve refund?"


def test_error_budget_exhausted():
    e = ErrorBudgetExhausted(
        persona_id="p1", sli_name="success_rate", budget_remaining=0.01,
        timestamp=_now(),
    )
    assert e.budget_remaining < 0.25


def test_tool_degraded():
    e = ToolDegraded(tool_name="mcp_github_create_issue", reason="disconnected", timestamp=_now())
    assert e.tool_name == "mcp_github_create_issue"


def test_tool_recovered():
    e = ToolRecovered(tool_name="mcp_github_create_issue", timestamp=_now())
    assert e.tool_name == "mcp_github_create_issue"


def test_all_events_have_trace_id():
    for cls in (MessageProcessed, SessionCreated, SLOBreached, ToolDegraded, ToolRecovered):
        # All events should accept trace_id
        if cls == MessageProcessed:
            e = cls(session_id="s", persona_id="p", latency_ms=1, token_count=1,
                    timestamp=_now(), trace_id="t123")
        elif cls == SessionCreated:
            e = cls(session_id="s", persona_id="p", user_id="u",
                    timestamp=_now(), trace_id="t123")
        elif cls == SLOBreached:
            e = cls(persona_id="p", sli_name="x", current_value=1, target_value=0,
                    timestamp=_now(), trace_id="t123")
        elif cls == ToolDegraded:
            e = cls(tool_name="t", reason="r", timestamp=_now(), trace_id="t123")
        else:
            e = cls(tool_name="t", timestamp=_now(), trace_id="t123")
        assert e.trace_id == "t123"
