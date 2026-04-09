"""Lane orchestrator — multi-agent parallel work stream coordination."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class LaneState(StrEnum):
    STARTED = "started"
    READY = "ready"
    BLOCKED = "blocked"
    RED = "red"  # CI failing
    GREEN = "green"  # CI passing
    MERGE_READY = "merge_ready"
    FINISHED = "finished"
    RECONCILED = "reconciled"
    MERGED = "merged"
    SUPERSEDED = "superseded"
    CLOSED = "closed"


class LaneFailureClass(StrEnum):
    PROMPT_DELIVERY = "prompt_delivery"
    TRUST_GATE = "trust_gate"
    BRANCH_DIVERGENCE = "branch_divergence"
    COMPILE = "compile"
    TEST = "test"
    PLUGIN_STARTUP = "plugin_startup"
    MCP_STARTUP = "mcp_startup"
    MCP_HANDSHAKE = "mcp_handshake"
    GATEWAY_ROUTING = "gateway_routing"
    TOOL_RUNTIME = "tool_runtime"
    INFRA = "infra"


@dataclass
class BranchLockIntent:
    """Declares which branches and modules a lane will touch."""
    lane_id: str
    branch: str
    modules: list[str] = field(default_factory=list)  # file paths/patterns


@dataclass
class Lane:
    id: str
    task_id: str
    agent_persona: str
    branch: str
    state: LaneState = LaneState.STARTED
    modules: list[str] = field(default_factory=list)
    failure_class: LaneFailureClass | None = None
    recovery_attempts: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class LaneOrchestrator:
    """Coordinates multiple agent lanes working in parallel on the same codebase."""

    MAX_RECOVERY_ATTEMPTS = 1

    def __init__(self) -> None:
        self._lanes: dict[str, Lane] = {}
        self._lock_intents: list[BranchLockIntent] = []

    def create_lane(self, lane_id: str, task_id: str, agent: str, branch: str, modules: list[str] | None = None) -> Lane:
        lane = Lane(id=lane_id, task_id=task_id, agent_persona=agent, branch=branch, modules=modules or [])
        self._lanes[lane_id] = lane
        self._lock_intents.append(BranchLockIntent(lane_id=lane_id, branch=branch, modules=modules or []))
        logger.info("Lane created: %s (branch=%s, agent=%s)", lane_id, branch, agent)
        return lane

    def transition(self, lane_id: str, new_state: LaneState, failure: LaneFailureClass | None = None) -> Lane:
        lane = self._lanes.get(lane_id)
        if not lane:
            raise ValueError(f"Lane not found: {lane_id}")
        old = lane.state
        lane.state = new_state
        if failure:
            lane.failure_class = failure
        logger.info("Lane %s: %s → %s", lane_id, old.value, new_state.value)
        return lane

    def detect_collisions(self) -> list[tuple[str, str, list[str]]]:
        """Detect branch lock collisions between lanes."""
        collisions: list[tuple[str, str, list[str]]] = []
        intents = self._lock_intents
        for i in range(len(intents)):
            for j in range(i + 1, len(intents)):
                a, b = intents[i], intents[j]
                if a.lane_id == b.lane_id:
                    continue
                overlapping = set(a.modules) & set(b.modules)
                if overlapping:
                    collisions.append((a.lane_id, b.lane_id, sorted(overlapping)))
        return collisions

    def get_ready_lanes(self) -> list[Lane]:
        return [l for l in self._lanes.values() if l.state in (LaneState.STARTED, LaneState.READY)]

    def get_green_lanes(self) -> list[Lane]:
        return [l for l in self._lanes.values() if l.state == LaneState.GREEN]

    def get_blocked_lanes(self) -> list[Lane]:
        return [l for l in self._lanes.values() if l.state in (LaneState.BLOCKED, LaneState.RED)]

    def should_recover(self, lane_id: str) -> bool:
        lane = self._lanes.get(lane_id)
        if not lane:
            return False
        return lane.recovery_attempts < self.MAX_RECOVERY_ATTEMPTS

    def record_recovery(self, lane_id: str) -> None:
        lane = self._lanes.get(lane_id)
        if lane:
            lane.recovery_attempts += 1

    def close_lane(self, lane_id: str, reason: str = "") -> None:
        lane = self._lanes.get(lane_id)
        if lane:
            lane.state = LaneState.CLOSED
            lane.metadata["close_reason"] = reason

    @property
    def active_count(self) -> int:
        terminal = {LaneState.FINISHED, LaneState.MERGED, LaneState.SUPERSEDED, LaneState.CLOSED, LaneState.RECONCILED}
        return sum(1 for l in self._lanes.values() if l.state not in terminal)

    @property
    def lane_count(self) -> int:
        return len(self._lanes)

    def get_lane(self, lane_id: str) -> Lane | None:
        return self._lanes.get(lane_id)

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for lane in self._lanes.values():
            counts[lane.state.value] = counts.get(lane.state.value, 0) + 1
        return counts
