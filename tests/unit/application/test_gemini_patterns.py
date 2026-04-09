"""Unit tests for Gemini CLI patterns:
policy engine, skill disclosure, tool masking, context imports,
model steering, and todo tracker.
"""

from __future__ import annotations

from agentic_core.application.services.context_imports import ContextImportResolver
from agentic_core.application.services.model_steering import ModelSteeringService
from agentic_core.application.services.policy_engine import (
    Decision,
    PolicyEngine,
    PolicyRule,
    Priority,
)
from agentic_core.application.services.skill_disclosure import SkillDisclosureService
from agentic_core.application.services.todo_tracker import TodoTracker
from agentic_core.application.services.tool_masking import ToolOutputMasker

# ---------------------------------------------------------------------------
# PolicyEngine
# ---------------------------------------------------------------------------


def test_policy_evaluate_allow_by_default() -> None:
    engine = PolicyEngine()
    decision, reason = engine.evaluate("read_file", {"path": "/tmp/x"})
    assert decision == Decision.ALLOW
    assert "No matching" in reason


def test_policy_evaluate_deny_rule() -> None:
    engine = PolicyEngine()
    engine.add_rule(
        PolicyRule(
            tool_pattern="delete_*",
            decision=Decision.DENY,
            priority=Priority.ADMIN,
            reason="Destructive tool blocked",
        )
    )
    decision, reason = engine.evaluate("delete_file", {"path": "/etc/passwd"})
    assert decision == Decision.DENY
    assert "Destructive" in reason


def test_policy_priority_ordering_higher_wins() -> None:
    engine = PolicyEngine()
    # Lower priority DENY added first
    engine.add_rule(
        PolicyRule(
            tool_pattern="run_*",
            decision=Decision.DENY,
            priority=Priority.DEFAULT,
            reason="default deny",
        )
    )
    # Higher priority ALLOW added second
    engine.add_rule(
        PolicyRule(
            tool_pattern="run_*",
            decision=Decision.ALLOW,
            priority=Priority.ADMIN,
            reason="admin allow",
        )
    )
    decision, reason = engine.evaluate("run_script", {})
    assert decision == Decision.ALLOW
    assert "admin" in reason


def test_policy_wildcard_and_mode_filtering() -> None:
    engine = PolicyEngine()
    engine.add_rule(
        PolicyRule(
            tool_pattern="net_*",
            decision=Decision.DENY,
            priority=Priority.WORKSPACE,
            modes=["restricted"],
            reason="no network in restricted mode",
        )
    )
    # In default mode the rule is skipped
    decision_default, _ = engine.evaluate("net_request", {}, mode="default")
    assert decision_default == Decision.ALLOW

    # In restricted mode the rule fires
    decision_restricted, reason = engine.evaluate(
        "net_request", {}, mode="restricted"
    )
    assert decision_restricted == Decision.DENY
    assert "restricted" in reason


def test_policy_args_pattern_matching() -> None:
    engine = PolicyEngine()
    engine.add_rule(
        PolicyRule(
            tool_pattern="write_file",
            args_pattern=r"/etc/",
            decision=Decision.DENY,
            priority=Priority.USER,
            reason="block writes to /etc",
        )
    )
    deny_decision, _ = engine.evaluate("write_file", {"path": "/etc/hosts"})
    assert deny_decision == Decision.DENY

    allow_decision, _ = engine.evaluate("write_file", {"path": "/tmp/safe.txt"})
    assert allow_decision == Decision.ALLOW


def test_policy_load_rules_from_dicts() -> None:
    engine = PolicyEngine()
    engine.load_rules(
        [
            {"tool": "exec_*", "decision": "ask_user", "priority": 2, "reason": "needs confirmation"},
            {"tool": "read_*", "decision": "allow", "priority": 1},
        ]
    )
    assert engine.rule_count == 2
    d1, _ = engine.evaluate("exec_shell", {})
    assert d1 == Decision.ASK_USER
    d2, _ = engine.evaluate("read_file", {})
    assert d2 == Decision.ALLOW


# ---------------------------------------------------------------------------
# SkillDisclosureService
# ---------------------------------------------------------------------------


def test_skill_disclosure_register_and_count() -> None:
    svc = SkillDisclosureService()
    svc.register("deploy", "Deploy apps", "Full deploy instructions", tier="workspace")
    svc.register("test", "Run tests", "Full test instructions", tier="user")
    assert svc.available_count == 2
    assert svc.active_count == 0


def test_skill_disclosure_activate_returns_instructions() -> None:
    svc = SkillDisclosureService()
    svc.register("deploy", "Deploy apps", "Step 1: build. Step 2: push.")
    instructions = svc.activate("deploy")
    assert instructions == "Step 1: build. Step 2: push."
    assert svc.active_count == 1


def test_skill_disclosure_context_prompt_shows_active_marker() -> None:
    svc = SkillDisclosureService()
    svc.register("alpha", "Alpha skill", "alpha content")
    svc.register("beta", "Beta skill", "beta content")
    svc.activate("alpha")
    prompt = svc.get_context_prompt()
    assert "[ACTIVE]" in prompt
    assert "alpha" in prompt
    assert "beta" in prompt
    # beta should NOT have [ACTIVE]
    assert prompt.count("[ACTIVE]") == 1


def test_skill_disclosure_token_estimate_increases_on_activate() -> None:
    svc = SkillDisclosureService()
    svc.register("big", "Big skill", " ".join(["word"] * 200))
    before = svc.context_token_estimate()
    svc.activate("big")
    after = svc.context_token_estimate()
    assert after["active"] > before["active"]
    assert after["total"] > before["total"]


# ---------------------------------------------------------------------------
# ToolOutputMasker
# ---------------------------------------------------------------------------


def test_masker_short_output_unchanged() -> None:
    masker = ToolOutputMasker(max_tokens=100)
    output = "hello world"
    assert masker.mask("any_tool", output) == output


def test_masker_long_output_is_truncated() -> None:
    masker = ToolOutputMasker(max_tokens=10)
    long_output = " ".join([f"word{i}" for i in range(100)])
    result = masker.mask("big_tool", long_output)
    assert "[..." in result
    assert len(result.split()) < 100


def test_masker_smart_truncation_keeps_head_and_tail() -> None:
    masker = ToolOutputMasker(max_tokens=5)
    lines = [f"line{i}" for i in range(50)]
    output = "\n".join(lines)
    result = masker.mask("log_tool", output)
    assert "line0" in result
    assert f"line{49}" in result
    assert "omitted" in result


def test_masker_per_tool_config_overrides_default() -> None:
    masker = ToolOutputMasker(max_tokens=1000)
    masker.configure_tool("tiny_tool", 2)
    output = "one two three four"
    assert masker.should_mask("tiny_tool", output) is True
    assert masker.should_mask("other_tool", output) is False


# ---------------------------------------------------------------------------
# ContextImportResolver
# ---------------------------------------------------------------------------


def test_context_imports_resolve_file(tmp_path) -> None:
    child = tmp_path / "child.md"
    child.write_text("# Child content")
    parent_content = "@child.md"
    resolver = ContextImportResolver(base_dir=str(tmp_path))
    result = resolver.resolve(parent_content)
    assert "# Child content" in result


def test_context_imports_circular_detection(tmp_path) -> None:
    # a.md imports b.md, b.md imports a.md
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("A content\n@b.md")
    b.write_text("B content\n@a.md")
    resolver = ContextImportResolver(base_dir=str(tmp_path))
    result = resolver.resolve("@a.md")
    assert "circular import" in result


def test_context_imports_max_depth(tmp_path) -> None:
    # Create a chain of 7 files — deeper than MAX_DEPTH=5
    for i in range(7):
        f = tmp_path / f"d{i}.md"
        if i < 6:
            f.write_text(f"depth{i}\n@d{i + 1}.md")
        else:
            f.write_text(f"depth{i}")
    resolver = ContextImportResolver(base_dir=str(tmp_path))
    result = resolver.resolve("@d0.md")
    # Should contain the early depths but stop at MAX_DEPTH
    assert "depth0" in result


def test_context_imports_code_block_ignored(tmp_path) -> None:
    """@import inside a code block must NOT be resolved."""
    injected = tmp_path / "secret.md"
    injected.write_text("SECRET CONTENT")
    content = "Normal text\n```\n@secret.md\n```\nEnd"
    resolver = ContextImportResolver(base_dir=str(tmp_path))
    result = resolver.resolve(content)
    assert "SECRET CONTENT" not in result
    assert "@secret.md" in result  # literal text preserved


# ---------------------------------------------------------------------------
# ModelSteeringService
# ---------------------------------------------------------------------------


def test_model_steering_add_and_has_hints() -> None:
    svc = ModelSteeringService()
    assert not svc.has_hints("session-1")
    svc.add_hint("session-1", "Focus on performance")
    assert svc.has_hints("session-1")


def test_model_steering_consume_clears_queue() -> None:
    svc = ModelSteeringService()
    svc.add_hint("s1", "hint one")
    svc.add_hint("s1", "hint two")
    hints = svc.consume_hints("s1")
    assert len(hints) == 2
    assert not svc.has_hints("s1")


def test_model_steering_format_for_context_urgent() -> None:
    svc = ModelSteeringService()
    svc.add_hint("s1", "Stop and reconsider", priority="urgent")
    svc.add_hint("s1", "Also think about caching", priority="normal")
    text = svc.format_for_context("s1")
    assert "URGENT:" in text
    assert "Stop and reconsider" in text
    assert "caching" in text
    # Consumed after formatting
    assert not svc.has_hints("s1")


def test_model_steering_clear_removes_session() -> None:
    svc = ModelSteeringService()
    svc.add_hint("s1", "some hint")
    svc.add_hint("s2", "another hint")
    svc.clear("s1")
    assert not svc.has_hints("s1")
    assert svc.has_hints("s2")
    assert svc.active_sessions == 1


# ---------------------------------------------------------------------------
# TodoTracker
# ---------------------------------------------------------------------------


def test_todo_tracker_add_and_list() -> None:
    tracker = TodoTracker()
    item = tracker.add("sess", "Write tests")
    assert item.id == 1
    assert item.done is False
    items = tracker.list_todos("sess")
    assert len(items) == 1
    assert items[0].text == "Write tests"


def test_todo_tracker_complete() -> None:
    tracker = TodoTracker()
    tracker.add("sess", "Task A")
    tracker.add("sess", "Task B")
    result = tracker.complete("sess", 1)
    assert result is True
    assert tracker.list_todos("sess")[0].done is True
    assert tracker.list_todos("sess")[1].done is False


def test_todo_tracker_remove() -> None:
    tracker = TodoTracker()
    tracker.add("sess", "To remove")
    tracker.add("sess", "To keep")
    removed = tracker.remove("sess", 1)
    assert removed is True
    items = tracker.list_todos("sess")
    assert len(items) == 1
    assert items[0].text == "To keep"


def test_todo_tracker_progress_and_format() -> None:
    tracker = TodoTracker()
    tracker.add("sess", "Step 1")
    tracker.add("sess", "Step 2")
    tracker.add("sess", "Step 3")
    tracker.complete("sess", 1)
    tracker.complete("sess", 3)
    done, total = tracker.progress("sess")
    assert done == 2
    assert total == 3
    text = tracker.format_for_context("sess")
    assert "Progress: 2/3" in text
    assert "[x]" in text
    assert "[ ]" in text
