"""Iteration budget and stuck detection for agent sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BudgetStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"  # 70%+
    CRITICAL = "critical"  # 90%+
    EXHAUSTED = "exhausted"
    STUCK = "stuck"

@dataclass
class BudgetState:
    turns_used: int = 0
    tokens_used: int = 0
    consecutive_failures: int = 0
    last_error: str | None = None
    status: BudgetStatus = BudgetStatus.OK

class IterationBudget:
    def __init__(self, max_turns: int = 50, max_tokens: int = 100000, stuck_threshold: int = 3) -> None:
        self._max_turns = max_turns
        self._max_tokens = max_tokens
        self._stuck_threshold = stuck_threshold
        self._sessions: dict[str, BudgetState] = {}

    def get_state(self, session_id: str) -> BudgetState:
        if session_id not in self._sessions:
            self._sessions[session_id] = BudgetState()
        return self._sessions[session_id]

    def record_turn(self, session_id: str, tokens: int, success: bool, error: str | None = None) -> BudgetStatus:
        state = self.get_state(session_id)
        state.turns_used += 1
        state.tokens_used += tokens

        if success:
            state.consecutive_failures = 0
            state.last_error = None
        else:
            state.consecutive_failures += 1
            state.last_error = error

        # Check stuck
        if state.consecutive_failures >= self._stuck_threshold:
            state.status = BudgetStatus.STUCK
            return state.status

        # Check budget
        turn_pct = state.turns_used / self._max_turns
        token_pct = state.tokens_used / self._max_tokens
        max_pct = max(turn_pct, token_pct)

        if max_pct >= 1.0:
            state.status = BudgetStatus.EXHAUSTED
        elif max_pct >= 0.9:
            state.status = BudgetStatus.CRITICAL
        elif max_pct >= 0.7:
            state.status = BudgetStatus.WARNING
        else:
            state.status = BudgetStatus.OK

        return state.status

    def should_pause(self, session_id: str) -> bool:
        state = self.get_state(session_id)
        return state.status in (BudgetStatus.EXHAUSTED, BudgetStatus.STUCK)

    def reset(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
