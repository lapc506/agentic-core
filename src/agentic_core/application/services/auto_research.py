from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from agentic_core.domain.entities.skill import Skill
from agentic_core.domain.events.domain_events import SkillOptimized
from agentic_core.domain.services.eval_scoring import EvalScoring

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from agentic_core.domain.value_objects.eval import BinaryEvalRule
    from agentic_core.shared_kernel.events import EventBus

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    original_score: float
    final_score: float
    iterations_used: int
    skill_version: int
    improved: bool


class AutoResearchLoop:
    """Skill self-improvement via batch execute -> binary eval -> mutate -> iterate."""

    def __init__(
        self,
        event_bus: EventBus,
        eval_scoring: EvalScoring | None = None,
        skill_executor: Callable[[Skill, int], Awaitable[list[bool]]] | None = None,
        skill_mutator: Callable[[Skill, list[bool], list[BinaryEvalRule]], Awaitable[str]] | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._eval = eval_scoring or EvalScoring()
        self._executor = skill_executor
        self._mutator = skill_mutator

    async def optimize(
        self,
        skill: Skill,
        rules: list[BinaryEvalRule],
        max_iterations: int = 5,
        batch_size: int = 10,
    ) -> OptimizationResult:
        best_skill = skill
        initial_score = 0.0
        best_score = 0.0

        for i in range(max_iterations):
            # 1. Batch execute
            actuals = await self._execute_batch(best_skill, batch_size)

            # 2. Evaluate with binary rules — expand rules to match actuals count
            expanded_rules = (rules * (len(actuals) // len(rules) + 1))[:len(actuals)]
            results = self._eval.evaluate(expanded_rules, actuals)
            score = self._eval.score(results)

            if i == 0:
                initial_score = score

            logger.info(
                "AutoResearch iteration %d: skill=%s score=%.2f (best=%.2f)",
                i + 1, skill.name, score, best_score,
            )

            if score > best_score:
                best_score = score
                best_skill = skill

            if score >= 1.0:
                logger.info("Perfect score reached for skill=%s", skill.name)
                break

            # 3. Mutate instructions
            failures = [not r.passed for r in results]
            new_instructions = await self._mutate(best_skill, failures, rules)
            skill = Skill(
                name=skill.name,
                instructions=new_instructions,
                version=skill.version + 1,
            )
            skill.record_score(score)

        # Publish optimization event
        if best_score > initial_score:
            await self._event_bus.publish(SkillOptimized(
                skill_name=best_skill.name,
                old_score=initial_score,
                new_score=best_score,
                version=best_skill.version,
                timestamp=datetime.now(UTC),
            ))

        return OptimizationResult(
            original_score=initial_score,
            final_score=best_score,
            iterations_used=min(i + 1, max_iterations),
            skill_version=best_skill.version,
            improved=best_score > initial_score,
        )

    async def _execute_batch(self, skill: Skill, batch_size: int) -> list[bool]:
        if self._executor is not None:
            return await self._executor(skill, batch_size)
        # Default stub: all pass
        return [True] * batch_size

    async def _mutate(
        self, skill: Skill, failures: list[bool], rules: list[BinaryEvalRule],
    ) -> str:
        if self._mutator is not None:
            return await self._mutator(skill, failures, rules)
        # Default stub: append iteration note
        return skill.instructions + "\n[AUTO-MUTATED]"
