"""Progressive deployment gates with stage-aware thresholds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Stage(StrEnum):
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class GateThreshold:
    stage: Stage
    min_score: float
    min_eval_count: int = 10
    require_safety: bool = False

DEFAULT_THRESHOLDS = {
    Stage.DEV: GateThreshold(stage=Stage.DEV, min_score=0.70, min_eval_count=5),
    Stage.STAGING: GateThreshold(stage=Stage.STAGING, min_score=0.85, min_eval_count=50, require_safety=True),
    Stage.PRODUCTION: GateThreshold(stage=Stage.PRODUCTION, min_score=0.95, min_eval_count=200, require_safety=True),
}

class DeploymentGateService:
    def __init__(self, thresholds: dict[Stage, GateThreshold] | None = None) -> None:
        self._thresholds = thresholds or DEFAULT_THRESHOLDS

    def check_gate(self, stage: Stage, score: float, eval_count: int, safety_passed: bool = True) -> tuple[bool, str]:
        threshold = self._thresholds.get(stage)
        if not threshold:
            return False, f"Unknown stage: {stage}"
        if eval_count < threshold.min_eval_count:
            return False, f"Insufficient evals: {eval_count}/{threshold.min_eval_count}"
        if score < threshold.min_score:
            return False, f"Score {score:.2f} below threshold {threshold.min_score:.2f} for {stage.value}"
        if threshold.require_safety and not safety_passed:
            return False, f"Safety check required for {stage.value}"
        return True, f"Approved for {stage.value}"

    def next_stage(self, current: Stage) -> Stage | None:
        order = [Stage.DEV, Stage.STAGING, Stage.PRODUCTION]
        idx = order.index(current)
        return order[idx + 1] if idx < len(order) - 1 else None
