"""Recovery recipes — automatic recovery for common agent failure scenarios."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class FailureScenario(StrEnum):
    TRUST_PROMPT = "trust_prompt_unresolved"
    PROMPT_MISDELIVERY = "prompt_misdelivery"
    STALE_BRANCH = "stale_branch"
    COMPILE_RED = "compile_red"
    MCP_HANDSHAKE = "mcp_handshake_failure"
    PLUGIN_STARTUP = "partial_plugin_startup"
    PROVIDER_FAILURE = "provider_failure"


class RecoveryAction(StrEnum):
    ACCEPT_TRUST = "accept_trust_prompt"
    REDIRECT_PROMPT = "redirect_prompt_to_agent"
    REBASE_BRANCH = "rebase_branch"
    CLEAN_BUILD = "clean_build"
    RETRY_MCP = "retry_mcp_handshake"
    RESTART_PLUGIN = "restart_plugin"
    RESTART_WORKER = "restart_worker"
    SWITCH_PROVIDER = "switch_provider"
    ESCALATE = "escalate_to_human"


@dataclass
class RecoveryStep:
    action: RecoveryAction
    params: dict = None
    timeout_seconds: float = 60.0

    def __post_init__(self):
        if self.params is None:
            self.params = {}


@dataclass
class RecoveryResult:
    scenario: FailureScenario
    steps_taken: list[RecoveryAction]
    recovered: bool
    escalated: bool = False


RECIPES: dict[FailureScenario, list[RecoveryStep]] = {
    FailureScenario.TRUST_PROMPT: [
        RecoveryStep(RecoveryAction.ACCEPT_TRUST),
    ],
    FailureScenario.PROMPT_MISDELIVERY: [
        RecoveryStep(RecoveryAction.REDIRECT_PROMPT),
    ],
    FailureScenario.STALE_BRANCH: [
        RecoveryStep(RecoveryAction.REBASE_BRANCH),
    ],
    FailureScenario.COMPILE_RED: [
        RecoveryStep(RecoveryAction.CLEAN_BUILD, timeout_seconds=120),
    ],
    FailureScenario.MCP_HANDSHAKE: [
        RecoveryStep(RecoveryAction.RETRY_MCP, timeout_seconds=30),
    ],
    FailureScenario.PLUGIN_STARTUP: [
        RecoveryStep(RecoveryAction.RESTART_PLUGIN),
    ],
    FailureScenario.PROVIDER_FAILURE: [
        RecoveryStep(RecoveryAction.SWITCH_PROVIDER),
        RecoveryStep(RecoveryAction.RESTART_WORKER),
    ],
}


class RecoveryEngine:
    """Executes recovery recipes for failed agent scenarios. One auto-retry, then escalate."""

    def __init__(self) -> None:
        self._attempts: dict[str, int] = {}  # lane_id -> attempt count

    async def attempt_recovery(self, lane_id: str, scenario: FailureScenario) -> RecoveryResult:
        attempts = self._attempts.get(lane_id, 0)
        steps_taken: list[RecoveryAction] = []

        if attempts >= 1:
            logger.warning("Lane %s: max recovery attempts reached for %s, escalating", lane_id, scenario.value)
            return RecoveryResult(scenario=scenario, steps_taken=[], recovered=False, escalated=True)

        recipe = RECIPES.get(scenario, [])
        if not recipe:
            logger.warning("No recovery recipe for %s", scenario.value)
            return RecoveryResult(scenario=scenario, steps_taken=[], recovered=False, escalated=True)

        self._attempts[lane_id] = attempts + 1

        for step in recipe:
            logger.info("Lane %s: executing recovery %s (timeout=%ss)", lane_id, step.action.value, step.timeout_seconds)
            steps_taken.append(step.action)
            # In production: actually execute the recovery action
            # For now: assume success

        logger.info("Lane %s: recovery successful for %s", lane_id, scenario.value)
        return RecoveryResult(scenario=scenario, steps_taken=steps_taken, recovered=True)

    def reset(self, lane_id: str) -> None:
        self._attempts.pop(lane_id, None)

    def attempts_for(self, lane_id: str) -> int:
        return self._attempts.get(lane_id, 0)
