"""Trajectory evaluator — scores complete execution paths, not just outcomes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrajectoryStep:
    step_type: str  # "tool_call", "reasoning", "observation", "response"
    content: str
    tokens_used: int = 0
    duration_ms: int = 0
    success: bool = True

@dataclass
class TrajectoryScore:
    outcome_score: float  # 0-1, did it achieve the goal?
    efficiency_score: float  # 0-1, did it use minimal steps/tokens?
    reliability_score: float  # 0-1, pass@k metric
    total_steps: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    failed_steps: int = 0

    @property
    def composite_score(self) -> float:
        return (self.outcome_score * 0.5 + self.efficiency_score * 0.3 + self.reliability_score * 0.2)

class TrajectoryEvaluator:
    def __init__(self, max_steps: int = 20, max_tokens: int = 10000) -> None:
        self._max_steps = max_steps
        self._max_tokens = max_tokens

    def evaluate(self, steps: list[TrajectoryStep], goal_achieved: bool) -> TrajectoryScore:
        total_steps = len(steps)
        total_tokens = sum(s.tokens_used for s in steps)
        total_duration = sum(s.duration_ms for s in steps)
        failed = sum(1 for s in steps if not s.success)

        outcome = 1.0 if goal_achieved else 0.0
        efficiency = max(0.0, 1.0 - (total_steps / self._max_steps)) * max(0.0, 1.0 - (total_tokens / self._max_tokens))
        reliability = 1.0 - (failed / max(total_steps, 1))

        return TrajectoryScore(
            outcome_score=outcome,
            efficiency_score=round(efficiency, 3),
            reliability_score=round(reliability, 3),
            total_steps=total_steps,
            total_tokens=total_tokens,
            total_duration_ms=total_duration,
            failed_steps=failed,
        )

    def pass_at_k(self, results: list[bool], k: int = 1) -> float:
        n = len(results)
        c = sum(results)
        if n < k:
            return 0.0
        from math import comb
        if c == 0:
            return 0.0
        return 1.0 - comb(n - c, k) / comb(n, k) if comb(n, k) > 0 else 0.0
