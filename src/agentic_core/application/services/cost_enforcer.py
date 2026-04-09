"""Cost budget enforcement — prevent denial-of-wallet attacks."""
from __future__ import annotations
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BudgetAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    DOWNGRADE = "downgrade"
    PAUSE = "pause"
    BLOCK = "block"


@dataclass
class CostBudget:
    daily_limit: float = 10.0
    monthly_limit: float = 100.0
    session_limit: float = 5.0
    warn_threshold: float = 0.8
    downgrade_model: str = "meta-llama/llama-3.2-3b-instruct:free"


@dataclass
class CostRecord:
    total: float = 0.0
    daily: float = 0.0
    monthly: float = 0.0
    session_costs: dict[str, float] = field(default_factory=dict)
    last_daily_reset: float = field(default_factory=time.time)
    last_monthly_reset: float = field(default_factory=time.time)


class CostEnforcer:
    DAY = 86400
    MONTH = 86400 * 30

    def __init__(self, budget: CostBudget | None = None) -> None:
        self._budget = budget or CostBudget()
        self._agents: dict[str, CostRecord] = {}
        self._global = CostRecord()

    def record(self, agent_id: str, session_id: str, cost: float) -> BudgetAction:
        self._reset_windows()
        rec = self._get_record(agent_id)
        rec.total += cost
        rec.daily += cost
        rec.monthly += cost
        rec.session_costs[session_id] = rec.session_costs.get(session_id, 0) + cost
        self._global.total += cost
        self._global.daily += cost
        self._global.monthly += cost

        session_cost = rec.session_costs.get(session_id, 0)
        if session_cost >= self._budget.session_limit:
            logger.warning("Cost PAUSE: agent=%s session=%s cost=%.4f limit=%.4f", agent_id, session_id, session_cost, self._budget.session_limit)
            return BudgetAction.PAUSE
        if rec.daily >= self._budget.daily_limit:
            logger.warning("Cost BLOCK: agent=%s daily=%.4f limit=%.4f", agent_id, rec.daily, self._budget.daily_limit)
            return BudgetAction.BLOCK
        if rec.monthly >= self._budget.monthly_limit:
            return BudgetAction.BLOCK
        if rec.daily >= self._budget.daily_limit * self._budget.warn_threshold:
            return BudgetAction.DOWNGRADE
        if session_cost >= self._budget.session_limit * self._budget.warn_threshold:
            return BudgetAction.WARN
        return BudgetAction.ALLOW

    def get_status(self, agent_id: str) -> dict:
        rec = self._get_record(agent_id)
        return {
            "daily": round(rec.daily, 4), "daily_limit": self._budget.daily_limit,
            "daily_pct": round(rec.daily / max(self._budget.daily_limit, 0.001) * 100, 1),
            "monthly": round(rec.monthly, 4), "monthly_limit": self._budget.monthly_limit,
            "total": round(rec.total, 4),
        }

    def should_downgrade(self, agent_id: str) -> tuple[bool, str]:
        rec = self._get_record(agent_id)
        if rec.daily >= self._budget.daily_limit * self._budget.warn_threshold:
            return True, self._budget.downgrade_model
        return False, ""

    def _get_record(self, agent_id: str) -> CostRecord:
        if agent_id not in self._agents:
            self._agents[agent_id] = CostRecord()
        return self._agents[agent_id]

    def _reset_windows(self) -> None:
        now = time.time()
        if now - self._global.last_daily_reset > self.DAY:
            for rec in self._agents.values():
                rec.daily = 0
                rec.last_daily_reset = now
            self._global.daily = 0
            self._global.last_daily_reset = now
        if now - self._global.last_monthly_reset > self.MONTH:
            for rec in self._agents.values():
                rec.monthly = 0
                rec.last_monthly_reset = now
            self._global.monthly = 0
            self._global.last_monthly_reset = now

    @property
    def global_spend(self) -> float:
        return round(self._global.total, 4)
