from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from agentic_core.domain.entities.roadmap import Phase, Roadmap, RoadmapTask

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    task_id: str
    success: bool
    output: str = ""
    error: str | None = None


@dataclass
class PhaseResult:
    phase_name: str
    task_results: list[TaskResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.success for r in self.task_results)


@dataclass
class RoadmapResult:
    title: str
    phase_results: list[PhaseResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return all(p.passed for p in self.phase_results)

    def summary(self) -> str:
        total = sum(len(p.task_results) for p in self.phase_results)
        passed = sum(1 for p in self.phase_results for t in p.task_results if t.success)
        return f"{passed}/{total} tasks passed across {len(self.phase_results)} phases"


class GSDSequencer:
    """Spec-Driven Development: executes roadmap phases SEQUENTIALLY,
    each task with isolated context (only compressed summary of prior results)."""

    def __init__(self, task_executor: Any = None) -> None:
        self._executor = task_executor

    async def execute_roadmap(self, roadmap: Roadmap) -> RoadmapResult:
        result = RoadmapResult(title=roadmap.title)
        prior_context = ""

        for phase in roadmap.phases:
            phase_result = await self._execute_phase(phase, prior_context)
            result.phase_results.append(phase_result)

            if not phase_result.passed:
                logger.warning("Phase '%s' failed, stopping roadmap", phase.name)
                break

            prior_context = self._summarize(result)
            logger.info("Phase '%s' complete, advancing", phase.name)

        return result

    async def _execute_phase(self, phase: Phase, prior_context: str) -> PhaseResult:
        phase_result = PhaseResult(phase_name=phase.name)

        for task in phase.tasks:
            task_result = await self._execute_task(task, prior_context)
            phase_result.task_results.append(task_result)

            if not task_result.success:
                logger.warning("Task '%s' failed in phase '%s'", task.id, phase.name)

        return phase_result

    async def _execute_task(self, task: RoadmapTask, prior_context: str) -> TaskResult:
        if self._executor is not None:
            result: TaskResult = await self._executor(task, prior_context)
            return result
        # Default: mark as success (skeleton for Phase 3)
        return TaskResult(task_id=task.id, success=True, output=f"Executed: {task.description}")

    def _summarize(self, result: RoadmapResult) -> str:
        lines = [f"Roadmap: {result.title}"]
        for pr in result.phase_results:
            status = "PASS" if pr.passed else "FAIL"
            lines.append(f"  Phase '{pr.phase_name}': {status}")
            for tr in pr.task_results:
                s = "OK" if tr.success else "FAIL"
                lines.append(f"    [{s}] {tr.task_id}: {tr.output[:80]}")
        return "\n".join(lines)
