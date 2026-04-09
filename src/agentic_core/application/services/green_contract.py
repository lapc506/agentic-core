"""Green Contract — graduated CI test levels as formal merge eligibility gates."""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum


class GreenLevel(IntEnum):
    TARGETED_TESTS = 1
    PACKAGE = 2
    WORKSPACE = 3
    MERGE_READY = 4


@dataclass
class GreenContractResult:
    satisfied: bool
    current_level: GreenLevel
    required_level: GreenLevel
    details: str = ""


class GreenContract:
    """Evaluates whether a lane meets the required CI green level for its next action."""

    def __init__(self) -> None:
        self._results: dict[str, dict[GreenLevel, bool]] = {}

    def record_result(self, lane_id: str, level: GreenLevel, passed: bool) -> None:
        if lane_id not in self._results:
            self._results[lane_id] = {}
        self._results[lane_id][level] = passed

    def evaluate(self, lane_id: str, required: GreenLevel) -> GreenContractResult:
        results = self._results.get(lane_id, {})
        current = GreenLevel.TARGETED_TESTS
        for level in GreenLevel:
            if results.get(level, False):
                current = level
            else:
                break

        satisfied = current >= required
        return GreenContractResult(
            satisfied=satisfied,
            current_level=current,
            required_level=required,
            details=f"{'PASS' if satisfied else 'FAIL'}: {current.name} {'≥' if satisfied else '<'} {required.name}",
        )

    def highest_green(self, lane_id: str) -> GreenLevel:
        results = self._results.get(lane_id, {})
        highest = GreenLevel.TARGETED_TESTS
        for level in GreenLevel:
            if results.get(level, False):
                highest = level
        return highest

    def is_merge_ready(self, lane_id: str) -> bool:
        return self.evaluate(lane_id, GreenLevel.MERGE_READY).satisfied

    def clear(self, lane_id: str) -> None:
        self._results.pop(lane_id, None)
