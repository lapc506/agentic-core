from __future__ import annotations

from agentic_core.application.services.gsd_sequencer import GSDSequencer, TaskResult
from agentic_core.application.services.auto_research import AutoResearchLoop
from agentic_core.domain.entities.roadmap import GateCondition, Phase, Roadmap, RoadmapTask
from agentic_core.domain.entities.skill import Skill
from agentic_core.domain.value_objects.eval import BinaryEvalRule
from agentic_core.shared_kernel.events import EventBus


# -- GSD Sequencer --

async def test_gsd_all_tasks_pass():
    sequencer = GSDSequencer()
    roadmap = Roadmap(
        title="Test",
        objectives=["Build X"],
        phases=[
            Phase(name="P1", tasks=[
                RoadmapTask(id="t1", description="Do A", spec="spec A"),
                RoadmapTask(id="t2", description="Do B", spec="spec B"),
            ]),
            Phase(name="P2", tasks=[
                RoadmapTask(id="t3", description="Do C", spec="spec C"),
            ]),
        ],
    )
    result = await sequencer.execute_roadmap(roadmap)
    assert result.success
    assert len(result.phase_results) == 2
    assert "2/3" in result.summary() or "3/3" in result.summary()


async def test_gsd_stops_on_phase_failure():
    async def failing_executor(task: RoadmapTask, ctx: str) -> TaskResult:
        if task.id == "t2":
            return TaskResult(task_id=task.id, success=False, error="boom")
        return TaskResult(task_id=task.id, success=True, output="ok")

    sequencer = GSDSequencer(task_executor=failing_executor)
    roadmap = Roadmap(
        title="Test",
        phases=[
            Phase(name="P1", tasks=[
                RoadmapTask(id="t1", description="A", spec=""),
                RoadmapTask(id="t2", description="B", spec=""),
            ]),
            Phase(name="P2", tasks=[
                RoadmapTask(id="t3", description="C", spec=""),
            ]),
        ],
    )
    result = await sequencer.execute_roadmap(roadmap)
    assert not result.success
    assert len(result.phase_results) == 1  # P2 never ran


async def test_gsd_empty_roadmap():
    sequencer = GSDSequencer()
    roadmap = Roadmap(title="Empty", phases=[])
    result = await sequencer.execute_roadmap(roadmap)
    assert result.success


# -- Auto Research Loop --

async def test_auto_research_perfect_score():
    bus = EventBus()
    loop = AutoResearchLoop(bus)

    skill = Skill(name="test-skill", instructions="Do X well")
    rules = [BinaryEvalRule(name="r1", question="Is it good?", expected=True, evaluator="code")]

    result = await loop.optimize(skill, rules, max_iterations=3, batch_size=5)
    assert result.final_score == 1.0
    assert result.iterations_used == 1


async def test_auto_research_with_custom_executor():
    bus = EventBus()
    call_count = 0

    async def executor(skill: Skill, batch_size: int) -> list[bool]:
        nonlocal call_count
        call_count += 1
        # First call: 50% pass. Second call: 100% pass
        if call_count == 1:
            return [True, False] * (batch_size // 2)
        return [True] * batch_size

    async def mutator(skill: Skill, failures: list[bool], rules: list[BinaryEvalRule]) -> str:
        return skill.instructions + " [IMPROVED]"

    loop = AutoResearchLoop(bus, skill_executor=executor, skill_mutator=mutator)
    skill = Skill(name="evolving", instructions="Original")
    rules = [BinaryEvalRule(name="r1", question="Pass?", expected=True, evaluator="code")]

    result = await loop.optimize(skill, rules, max_iterations=3, batch_size=4)
    assert result.final_score >= result.original_score


async def test_auto_research_publishes_event():
    bus = EventBus()
    events: list = []

    async def on_optimized(event: object) -> None:
        events.append(event)

    from agentic_core.domain.events.domain_events import SkillOptimized
    bus.subscribe(SkillOptimized, on_optimized)

    call_count = 0

    async def executor(skill: Skill, batch_size: int) -> list[bool]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [True, False, True, False]
        return [True] * 4

    async def mutator(skill: Skill, failures: list[bool], rules: list[BinaryEvalRule]) -> str:
        return skill.instructions + " [v2]"

    loop = AutoResearchLoop(bus, skill_executor=executor, skill_mutator=mutator)
    skill = Skill(name="test", instructions="v1")
    rules = [BinaryEvalRule(name="r1", question="?", expected=True, evaluator="code")]

    result = await loop.optimize(skill, rules, max_iterations=3, batch_size=4)
    assert result.improved
    assert len(events) == 1
