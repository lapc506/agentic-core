"""Behavioral monitoring — detect anomalous agent behavior patterns."""
from __future__ import annotations
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentBehaviorProfile:
    agent_id: str
    tool_calls: int = 0
    tokens_used: int = 0
    data_bytes: int = 0
    sessions: int = 0
    errors: int = 0
    window_start: float = field(default_factory=time.monotonic)


@dataclass
class AnomalyAlert:
    agent_id: str
    alert_type: str
    severity: str  # warning, critical
    current_value: float
    baseline_value: float
    deviation_factor: float
    timestamp: float = field(default_factory=time.time)


class BehavioralMonitor:
    def __init__(self, warning_factor: float = 2.0, critical_factor: float = 5.0, window_seconds: float = 3600) -> None:
        self._warning = warning_factor
        self._critical = critical_factor
        self._window = window_seconds
        self._profiles: dict[str, AgentBehaviorProfile] = {}
        self._baselines: dict[str, AgentBehaviorProfile] = {}
        self._alerts: list[AnomalyAlert] = []

    def record_tool_call(self, agent_id: str, data_bytes: int = 0) -> AnomalyAlert | None:
        p = self._get_profile(agent_id)
        p.tool_calls += 1
        p.data_bytes += data_bytes
        return self._check(agent_id, "tool_calls", p.tool_calls)

    def record_tokens(self, agent_id: str, tokens: int) -> AnomalyAlert | None:
        p = self._get_profile(agent_id)
        p.tokens_used += tokens
        return self._check(agent_id, "tokens_used", p.tokens_used)

    def record_error(self, agent_id: str) -> AnomalyAlert | None:
        p = self._get_profile(agent_id)
        p.errors += 1
        return self._check(agent_id, "errors", p.errors)

    def set_baseline(self, agent_id: str, profile: AgentBehaviorProfile) -> None:
        self._baselines[agent_id] = profile

    def get_alerts(self, agent_id: str | None = None) -> list[AnomalyAlert]:
        if agent_id:
            return [a for a in self._alerts if a.agent_id == agent_id]
        return list(self._alerts)

    def _get_profile(self, agent_id: str) -> AgentBehaviorProfile:
        now = time.monotonic()
        p = self._profiles.get(agent_id)
        if not p or (now - p.window_start) > self._window:
            p = AgentBehaviorProfile(agent_id=agent_id, window_start=now)
            self._profiles[agent_id] = p
        return p

    def _check(self, agent_id: str, metric: str, current: float) -> AnomalyAlert | None:
        baseline = self._baselines.get(agent_id)
        if not baseline:
            return None
        base_val = getattr(baseline, metric, 0)
        if base_val <= 0:
            return None
        factor = current / base_val
        if factor >= self._critical:
            alert = AnomalyAlert(agent_id=agent_id, alert_type=metric, severity="critical",
                                 current_value=current, baseline_value=base_val, deviation_factor=round(factor, 2))
            self._alerts.append(alert)
            logger.critical("ANOMALY [%s] %s: %.0fx baseline (%s vs %s)", agent_id, metric, factor, current, base_val)
            return alert
        if factor >= self._warning:
            alert = AnomalyAlert(agent_id=agent_id, alert_type=metric, severity="warning",
                                 current_value=current, baseline_value=base_val, deviation_factor=round(factor, 2))
            self._alerts.append(alert)
            logger.warning("ANOMALY [%s] %s: %.0fx baseline", agent_id, metric, factor)
            return alert
        return None

    @property
    def monitored_agents(self) -> int:
        return len(self._profiles)
