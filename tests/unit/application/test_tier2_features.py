"""Unit tests for Tier 2 features: HTN planning, trajectory scoring,
deployment gates, security audit, and iteration budget."""

from __future__ import annotations

from agentic_core.application.services.deployment_gates import (
    DeploymentGateService,
    Stage,
)
from agentic_core.application.services.iteration_budget import (
    BudgetStatus,
    IterationBudget,
)
from agentic_core.application.services.security_auditor import (
    SecurityAuditor,
    Severity,
)
from agentic_core.domain.services.trajectory_evaluator import (
    TrajectoryEvaluator,
    TrajectoryStep,
)
from agentic_core.graph_templates.htn_planner import (
    HTNPlanner,
    TaskStatus,
)

# ---------------------------------------------------------------------------
# HTN Planner
# ---------------------------------------------------------------------------

def test_htn_create_plan_structure() -> None:
    planner = HTNPlanner()
    root = planner.create_plan(
        goal="Deploy service",
        subtasks=[
            {"name": "Build image", "description": "docker build"},
            {"name": "Push image", "description": "docker push"},
        ],
    )
    assert root.name == "Deploy service"
    assert len(root.children) == 2
    assert root.children[0].name == "Build image"
    assert root.children[1].name == "Push image"
    assert not root.is_leaf


def test_htn_get_ready_tasks_no_dependencies() -> None:
    planner = HTNPlanner()
    root = planner.create_plan(
        goal="Goal",
        subtasks=[
            {"name": "Task A"},
            {"name": "Task B"},
        ],
    )
    ready = planner.get_ready_tasks(root)
    assert len(ready) == 2
    assert {t.name for t in ready} == {"Task A", "Task B"}


def test_htn_dependency_resolution_blocks_task() -> None:
    planner = HTNPlanner()
    root = planner.create_plan(
        goal="Ordered goal",
        subtasks=[
            {"name": "First"},
            {"name": "Second", "dependencies": ["task-2"]},  # depends on First (task-2)
        ],
    )
    # task-2 is "First", task-3 is "Second"
    first = root.children[0]
    root.children[1]

    # Before completing First, only First should be ready
    ready = planner.get_ready_tasks(root)
    ready_names = {t.name for t in ready}
    assert "Second" not in ready_names
    assert "First" in ready_names

    # Complete First, then Second should become ready
    first.complete("done")
    ready_after = planner.get_ready_tasks(root)
    assert any(t.name == "Second" for t in ready_after)


def test_htn_update_parent_status_propagation() -> None:
    planner = HTNPlanner()
    root = planner.create_plan(
        goal="Parent goal",
        subtasks=[{"name": "Child A"}, {"name": "Child B"}],
    )
    root.children[0].complete()
    root.children[1].complete()
    planner.update_parent_status(root)
    assert root.status == TaskStatus.COMPLETED


def test_htn_parent_failed_when_child_fails() -> None:
    planner = HTNPlanner()
    root = planner.create_plan(
        goal="Failing goal",
        subtasks=[{"name": "Good"}, {"name": "Bad"}],
    )
    root.children[0].complete()
    root.children[1].fail("timeout")
    planner.update_parent_status(root)
    assert root.status == TaskStatus.FAILED


# ---------------------------------------------------------------------------
# Trajectory Evaluator
# ---------------------------------------------------------------------------

def test_trajectory_evaluate_success() -> None:
    evaluator = TrajectoryEvaluator(max_steps=10, max_tokens=1000)
    steps = [
        TrajectoryStep("tool_call", "search(x)", tokens_used=100, success=True),
        TrajectoryStep("response", "result", tokens_used=50, success=True),
    ]
    score = evaluator.evaluate(steps, goal_achieved=True)
    assert score.outcome_score == 1.0
    assert score.reliability_score == 1.0
    assert score.total_steps == 2
    assert score.total_tokens == 150
    assert score.failed_steps == 0


def test_trajectory_evaluate_failure() -> None:
    evaluator = TrajectoryEvaluator(max_steps=10, max_tokens=1000)
    steps = [TrajectoryStep("tool_call", "broken()", tokens_used=200, success=False)]
    score = evaluator.evaluate(steps, goal_achieved=False)
    assert score.outcome_score == 0.0
    assert score.reliability_score == 0.0
    assert score.failed_steps == 1


def test_trajectory_efficiency_penalises_overuse() -> None:
    evaluator = TrajectoryEvaluator(max_steps=10, max_tokens=1000)
    # Use all 10 steps and 1000 tokens — efficiency should be 0
    steps = [
        TrajectoryStep("reasoning", f"step {i}", tokens_used=100, success=True)
        for i in range(10)
    ]
    score = evaluator.evaluate(steps, goal_achieved=True)
    assert score.efficiency_score == 0.0


def test_trajectory_composite_score_weights() -> None:
    evaluator = TrajectoryEvaluator(max_steps=20, max_tokens=10000)
    steps = [TrajectoryStep("response", "ok", tokens_used=100, success=True)]
    score = evaluator.evaluate(steps, goal_achieved=True)
    expected = score.outcome_score * 0.5 + score.efficiency_score * 0.3 + score.reliability_score * 0.2
    assert abs(score.composite_score - expected) < 1e-9


def test_trajectory_pass_at_k() -> None:
    evaluator = TrajectoryEvaluator()
    results = [True, False, True, False, True]
    p1 = evaluator.pass_at_k(results, k=1)
    assert 0.0 < p1 <= 1.0
    # All failures -> 0
    assert evaluator.pass_at_k([False, False, False], k=1) == 0.0
    # n < k -> 0
    assert evaluator.pass_at_k([True], k=5) == 0.0


# ---------------------------------------------------------------------------
# Deployment Gates
# ---------------------------------------------------------------------------

def test_deployment_gate_dev_passes() -> None:
    svc = DeploymentGateService()
    ok, msg = svc.check_gate(Stage.DEV, score=0.75, eval_count=10)
    assert ok is True
    assert "dev" in msg.lower()


def test_deployment_gate_insufficient_evals() -> None:
    svc = DeploymentGateService()
    ok, msg = svc.check_gate(Stage.STAGING, score=0.90, eval_count=5)
    assert ok is False
    assert "insufficient" in msg.lower()


def test_deployment_gate_score_below_threshold() -> None:
    svc = DeploymentGateService()
    ok, msg = svc.check_gate(Stage.PRODUCTION, score=0.80, eval_count=300)
    assert ok is False
    assert "below threshold" in msg.lower()


def test_deployment_gate_safety_required() -> None:
    svc = DeploymentGateService()
    ok, msg = svc.check_gate(Stage.STAGING, score=0.90, eval_count=100, safety_passed=False)
    assert ok is False
    assert "safety" in msg.lower()


def test_deployment_gate_next_stage() -> None:
    svc = DeploymentGateService()
    assert svc.next_stage(Stage.DEV) == Stage.STAGING
    assert svc.next_stage(Stage.STAGING) == Stage.PRODUCTION
    assert svc.next_stage(Stage.PRODUCTION) is None


# ---------------------------------------------------------------------------
# Security Auditor
# ---------------------------------------------------------------------------

def test_security_audit_auth_warning() -> None:
    auditor = SecurityAuditor()
    findings = auditor.audit({"mode": "standalone", "auth_enabled": False})
    auth_findings = [f for f in findings if f.check == "auth"]
    assert len(auth_findings) == 1
    assert auth_findings[0].severity == Severity.WARNING


def test_security_audit_pii_critical() -> None:
    auditor = SecurityAuditor()
    findings = auditor.audit({"pii_redaction_enabled": False})
    pii_findings = [f for f in findings if f.check == "pii"]
    assert len(pii_findings) == 1
    assert pii_findings[0].severity == Severity.CRITICAL


def test_security_audit_rate_limit_warning() -> None:
    auditor = SecurityAuditor()
    findings = auditor.audit({"rate_limit_rpm": 0})
    rl_findings = [f for f in findings if f.check == "rate_limit"]
    assert len(rl_findings) == 1
    assert rl_findings[0].severity == Severity.WARNING


def test_security_audit_secrets_in_dsn() -> None:
    auditor = SecurityAuditor()
    findings = auditor.audit({"postgres_dsn": "postgresql://user:password123@localhost/db"})
    secret_findings = [f for f in findings if f.check == "secrets"]
    assert len(secret_findings) == 1
    assert "postgres_dsn" in secret_findings[0].message


def test_security_audit_clean_config_no_critical() -> None:
    auditor = SecurityAuditor()
    findings = auditor.audit({
        "mode": "sidecar",
        "auth_enabled": True,
        "rate_limit_rpm": 60,
        "pii_redaction_enabled": True,
        "ws_host": "127.0.0.1",
    })
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert len(critical) == 0


# ---------------------------------------------------------------------------
# Iteration Budget
# ---------------------------------------------------------------------------

def test_iteration_budget_ok_status() -> None:
    budget = IterationBudget(max_turns=50, max_tokens=100_000)
    status = budget.record_turn("s1", tokens=500, success=True)
    assert status == BudgetStatus.OK
    assert not budget.should_pause("s1")


def test_iteration_budget_warning_at_70_percent() -> None:
    budget = IterationBudget(max_turns=10, max_tokens=100_000)
    for _ in range(7):
        status = budget.record_turn("s1", tokens=10, success=True)
    assert status == BudgetStatus.WARNING


def test_iteration_budget_stuck_detection() -> None:
    budget = IterationBudget(max_turns=50, max_tokens=100_000, stuck_threshold=3)
    for _ in range(3):
        status = budget.record_turn("s1", tokens=100, success=False, error="timeout")
    assert status == BudgetStatus.STUCK
    assert budget.should_pause("s1")


def test_iteration_budget_reset_clears_state() -> None:
    budget = IterationBudget(max_turns=5, max_tokens=100_000)
    for _ in range(5):
        budget.record_turn("s1", tokens=100, success=True)
    assert budget.get_state("s1").turns_used == 5
    budget.reset("s1")
    # After reset, a fresh state is returned
    state = budget.get_state("s1")
    assert state.turns_used == 0
    assert state.status == BudgetStatus.OK


def test_iteration_budget_exhausted_turns() -> None:
    budget = IterationBudget(max_turns=3, max_tokens=100_000)
    for _ in range(3):
        status = budget.record_turn("s1", tokens=10, success=True)
    assert status == BudgetStatus.EXHAUSTED
    assert budget.should_pause("s1")
