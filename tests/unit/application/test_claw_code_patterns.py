"""Unit tests for multi-agent coordination patterns: lane orchestration,
green contracts, recovery recipes, stale branch detection, and task packets."""

from __future__ import annotations

import pytest

from agentic_core.application.services.lane_orchestrator import (
    Lane,
    LaneFailureClass,
    LaneOrchestrator,
    LaneState,
)
from agentic_core.application.services.green_contract import (
    GreenContract,
    GreenLevel,
)
from agentic_core.application.services.recovery_recipes import (
    FailureScenario,
    RecoveryAction,
    RecoveryEngine,
)
from agentic_core.application.services.stale_branch import (
    BranchFreshness,
    StaleBranchDetector,
    StaleBranchPolicy,
)
from agentic_core.application.services.task_packet import (
    TaskPacket,
    validate_packet,
)


# ---------------------------------------------------------------------------
# Lane Orchestrator
# ---------------------------------------------------------------------------

def test_lane_create() -> None:
    orch = LaneOrchestrator()
    lane = orch.create_lane("L1", "T1", "coder", "feat/a", modules=["src/foo.py"])
    assert lane.id == "L1"
    assert lane.state == LaneState.STARTED
    assert lane.branch == "feat/a"
    assert orch.lane_count == 1


def test_lane_transition() -> None:
    orch = LaneOrchestrator()
    orch.create_lane("L1", "T1", "coder", "feat/a")
    lane = orch.transition("L1", LaneState.GREEN)
    assert lane.state == LaneState.GREEN
    lane = orch.transition("L1", LaneState.RED, failure=LaneFailureClass.TEST)
    assert lane.state == LaneState.RED
    assert lane.failure_class == LaneFailureClass.TEST


def test_lane_detect_collisions() -> None:
    orch = LaneOrchestrator()
    orch.create_lane("L1", "T1", "coder", "feat/a", modules=["src/shared.py", "src/a.py"])
    orch.create_lane("L2", "T2", "reviewer", "feat/b", modules=["src/shared.py", "src/b.py"])
    collisions = orch.detect_collisions()
    assert len(collisions) == 1
    assert collisions[0][0] == "L1"
    assert collisions[0][1] == "L2"
    assert "src/shared.py" in collisions[0][2]


def test_lane_active_count() -> None:
    orch = LaneOrchestrator()
    orch.create_lane("L1", "T1", "coder", "feat/a")
    orch.create_lane("L2", "T2", "reviewer", "feat/b")
    assert orch.active_count == 2
    orch.transition("L1", LaneState.MERGED)
    assert orch.active_count == 1
    orch.close_lane("L2", reason="done")
    assert orch.active_count == 0


# ---------------------------------------------------------------------------
# Green Contract
# ---------------------------------------------------------------------------

def test_green_record_result() -> None:
    gc = GreenContract()
    gc.record_result("L1", GreenLevel.TARGETED_TESTS, True)
    gc.record_result("L1", GreenLevel.PACKAGE, True)
    result = gc.evaluate("L1", GreenLevel.PACKAGE)
    assert result.satisfied is True
    assert result.current_level == GreenLevel.PACKAGE


def test_green_evaluate_insufficient() -> None:
    gc = GreenContract()
    gc.record_result("L1", GreenLevel.TARGETED_TESTS, True)
    result = gc.evaluate("L1", GreenLevel.WORKSPACE)
    assert result.satisfied is False
    assert "FAIL" in result.details


def test_green_merge_ready() -> None:
    gc = GreenContract()
    for level in GreenLevel:
        gc.record_result("L1", level, True)
    assert gc.is_merge_ready("L1") is True
    assert gc.is_merge_ready("L_unknown") is False


def test_green_highest_green() -> None:
    gc = GreenContract()
    gc.record_result("L1", GreenLevel.TARGETED_TESTS, True)
    gc.record_result("L1", GreenLevel.PACKAGE, True)
    gc.record_result("L1", GreenLevel.WORKSPACE, True)
    assert gc.highest_green("L1") == GreenLevel.WORKSPACE


# ---------------------------------------------------------------------------
# Recovery Engine
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recovery_attempt() -> None:
    engine = RecoveryEngine()
    result = await engine.attempt_recovery("L1", FailureScenario.COMPILE_RED)
    assert result.recovered is True
    assert RecoveryAction.CLEAN_BUILD in result.steps_taken
    assert engine.attempts_for("L1") == 1


@pytest.mark.asyncio
async def test_recovery_escalate_after_max() -> None:
    engine = RecoveryEngine()
    await engine.attempt_recovery("L1", FailureScenario.COMPILE_RED)
    result = await engine.attempt_recovery("L1", FailureScenario.COMPILE_RED)
    assert result.recovered is False
    assert result.escalated is True


@pytest.mark.asyncio
async def test_recovery_reset() -> None:
    engine = RecoveryEngine()
    await engine.attempt_recovery("L1", FailureScenario.STALE_BRANCH)
    assert engine.attempts_for("L1") == 1
    engine.reset("L1")
    assert engine.attempts_for("L1") == 0


@pytest.mark.asyncio
async def test_recovery_provider_failure_multi_step() -> None:
    engine = RecoveryEngine()
    result = await engine.attempt_recovery("L1", FailureScenario.PROVIDER_FAILURE)
    assert result.recovered is True
    assert len(result.steps_taken) == 2
    assert RecoveryAction.SWITCH_PROVIDER in result.steps_taken
    assert RecoveryAction.RESTART_WORKER in result.steps_taken


# ---------------------------------------------------------------------------
# Stale Branch Detector
# ---------------------------------------------------------------------------

def test_stale_assess_fresh() -> None:
    detector = StaleBranchDetector(stale_threshold=5)
    status = detector.assess("feat/x", commits_behind=0)
    assert status.freshness == BranchFreshness.FRESH


def test_stale_assess_stale() -> None:
    detector = StaleBranchDetector(stale_threshold=5)
    status = detector.assess("feat/x", commits_behind=10)
    assert status.freshness == BranchFreshness.STALE


def test_stale_policy_matching() -> None:
    detector = StaleBranchDetector()
    detector.set_policy("feat/*", StaleBranchPolicy.AUTO_REBASE)
    status = detector.assess("feat/x", commits_behind=10)
    assert status.policy == StaleBranchPolicy.AUTO_REBASE
    assert detector.should_auto_fix(status) is True


def test_stale_should_block() -> None:
    detector = StaleBranchDetector()
    detector.set_policy("release/*", StaleBranchPolicy.BLOCK)
    status = detector.assess("release/v1", commits_behind=10)
    assert detector.should_block(status) is True


# ---------------------------------------------------------------------------
# Task Packet
# ---------------------------------------------------------------------------

def test_task_packet_valid() -> None:
    packet = TaskPacket(
        objective="Implement feature X",
        scope="src/feature_x/",
        repo="org/repo",
        branch_policy="create_new",
        acceptance_tests=["test_feature_x"],
        commit_policy="atomic",
    )
    valid, errors = validate_packet(packet)
    assert valid is True
    assert errors == []


def test_task_packet_missing_fields() -> None:
    packet = TaskPacket()
    valid, errors = validate_packet(packet)
    assert valid is False
    assert len(errors) == 6


def test_task_packet_partial_validation() -> None:
    packet = TaskPacket(objective="Do something", scope="src/")
    valid, errors = validate_packet(packet)
    assert valid is False
    assert "repo is required" in errors
    assert "objective is required" not in errors
    assert "scope is required" not in errors
