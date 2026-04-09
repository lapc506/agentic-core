"""Tests for security gaps #9, #10, #13.

Gap  9 -- Behavioral monitoring + anomaly detection
Gap 10 -- EU AI Act compliance layer
Gap 13 -- Cost budget enforcement

Updated to match the simplified API.
"""

from __future__ import annotations

import time

import pytest

# ---------------------------------------------------------------------------
# Gap 9 -- Behavioral Monitor
# ---------------------------------------------------------------------------
from agentic_core.application.services.behavioral_monitor import (
    AgentBehaviorProfile,
    AnomalyAlert,
    BehavioralMonitor,
)


class TestBehavioralMonitorBaseline:
    """Baseline profile management."""

    def test_no_alert_without_baseline(self) -> None:
        m = BehavioralMonitor()
        assert m.record_tool_call("a1") is None

    def test_warning_alert(self) -> None:
        m = BehavioralMonitor(warning_factor=2.0)
        m.set_baseline("a1", AgentBehaviorProfile(agent_id="a1", tool_calls=5))
        for _ in range(10):
            result = m.record_tool_call("a1")
        assert result is not None
        assert result.severity == "warning"

    def test_critical_alert(self) -> None:
        m = BehavioralMonitor(critical_factor=5.0)
        m.set_baseline("a1", AgentBehaviorProfile(agent_id="a1", tool_calls=2))
        for _ in range(10):
            result = m.record_tool_call("a1")
        assert result is not None
        assert result.severity == "critical"

    def test_get_alerts_by_agent(self) -> None:
        m = BehavioralMonitor(warning_factor=2.0)
        m.set_baseline("a1", AgentBehaviorProfile(agent_id="a1", errors=1))
        for _ in range(3):
            m.record_error("a1")
        assert len(m.get_alerts("a1")) > 0
        assert len(m.get_alerts("a2")) == 0

    def test_monitored_agents_count(self) -> None:
        m = BehavioralMonitor()
        m.record_tool_call("a1")
        m.record_tool_call("a2")
        assert m.monitored_agents == 2


# ---------------------------------------------------------------------------
# Gap 10 -- Compliance
# ---------------------------------------------------------------------------
from agentic_core.application.services.compliance import (
    ComplianceConfig,
    ComplianceEvent,
    ComplianceService,
    RiskClassifier,
    RiskLevel,
)


class TestComplianceServiceDisabled:
    """When disabled the service must be a full no-op."""

    def test_disabled_noop(self) -> None:
        svc = ComplianceService(ComplianceConfig(enabled=False))
        svc.record(ComplianceEvent(event_type="test"))
        assert svc.query() == []
        assert not svc.enabled


class TestComplianceServiceEnabled:
    """Enabled service with file backend."""

    def test_enabled_file_store(self, tmp_path) -> None:
        cfg = ComplianceConfig(enabled=True, storage_backend="file", storage_path=str(tmp_path))
        svc = ComplianceService(cfg)
        svc.record(ComplianceEvent(event_type="tool_call", agent_id="a1", user_id="u1"))
        results = svc.query()
        assert len(results) == 1
        assert results[0]["type"] == "tool_call"

    def test_retention_check(self, tmp_path) -> None:
        cfg = ComplianceConfig(enabled=True, storage_backend="file", storage_path=str(tmp_path))
        svc = ComplianceService(cfg)
        svc.record(ComplianceEvent(event_type="test"))
        status = svc.check_retention()
        assert status["status"] == "ok"
        assert status["retention_days"] == 180


class TestRiskClassifier:
    """Risk level classification."""

    def test_minimal_risk(self) -> None:
        c = RiskClassifier()
        assert c.classify_agent([], has_network=False, has_file_access=False) == RiskLevel.MINIMAL

    def test_limited_risk_with_tools(self) -> None:
        c = RiskClassifier()
        assert c.classify_agent(["search"]) == RiskLevel.LIMITED

    def test_high_risk_with_network_and_file(self) -> None:
        c = RiskClassifier()
        assert c.classify_agent(["bash"], has_network=True, has_file_access=True) == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Gap 13 -- Cost Enforcer
# ---------------------------------------------------------------------------
from agentic_core.application.services.cost_enforcer import (
    BudgetAction,
    CostBudget,
    CostEnforcer,
)


class TestCostEnforcer:
    """Budget enforcement."""

    def test_allow_under_budget(self) -> None:
        e = CostEnforcer(CostBudget(daily_limit=10, session_limit=5))
        assert e.record("a1", "s1", 0.01) == BudgetAction.ALLOW

    def test_warn_approaching_session_limit(self) -> None:
        e = CostEnforcer(CostBudget(session_limit=1.0, warn_threshold=0.8))
        e.record("a1", "s1", 0.85)
        assert e.record("a1", "s1", 0.0) == BudgetAction.WARN

    def test_pause_on_session_limit(self) -> None:
        e = CostEnforcer(CostBudget(session_limit=1.0))
        assert e.record("a1", "s1", 1.5) == BudgetAction.PAUSE

    def test_block_on_daily_limit(self) -> None:
        e = CostEnforcer(CostBudget(daily_limit=2.0, session_limit=100))
        e.record("a1", "s1", 2.5)
        assert e.record("a1", "s1", 0.0) == BudgetAction.BLOCK

    def test_downgrade_suggestion(self) -> None:
        e = CostEnforcer(CostBudget(daily_limit=1.0, warn_threshold=0.8, downgrade_model="cheap-model"))
        e.record("a1", "s1", 0.85)
        should, model = e.should_downgrade("a1")
        assert should
        assert model == "cheap-model"

    def test_global_spend(self) -> None:
        e = CostEnforcer()
        e.record("a1", "s1", 0.5)
        e.record("a2", "s2", 0.3)
        assert e.global_spend == 0.8
