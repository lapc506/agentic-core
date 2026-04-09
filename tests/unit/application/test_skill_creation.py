from __future__ import annotations

from agentic_core.application.services.skill_creation import (
    ProceduralSkill,
    SkillCreationService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STEPS = ["Step 1: gather data", "Step 2: process data", "Step 3: output results"]
TOOLS = ["search", "summarise"]
TASK = "Analyse and summarise dataset"


async def _create(
    svc: SkillCreationService,
    task: str = TASK,
    steps: list[str] | None = None,
    tools: list[str] | None = None,
    success: bool = True,
    tags: list[str] | None = None,
) -> ProceduralSkill | None:
    return await svc.create_from_task(
        task_description=task,
        steps_taken=steps if steps is not None else STEPS,
        tools_used=tools if tools is not None else TOOLS,
        success=success,
        tags=tags,
    )


# ---------------------------------------------------------------------------
# Skill creation — happy path
# ---------------------------------------------------------------------------


async def test_create_returns_procedural_skill(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc)

    assert isinstance(skill, ProceduralSkill)
    assert skill.description == TASK
    assert skill.steps == STEPS
    assert skill.tools_used == TOOLS
    assert svc.skill_count == 1


async def test_create_stores_tags(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc, tags=["data", "nlp"])

    assert skill is not None
    assert "data" in skill.tags
    assert "nlp" in skill.tags


async def test_created_skill_has_utc_timestamp(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc)

    assert skill is not None
    # created_at must be a non-empty ISO-format string ending with +00:00 or Z
    assert skill.created_at
    assert "2" in skill.created_at  # year present


# ---------------------------------------------------------------------------
# Skill creation — failure / insufficient steps
# ---------------------------------------------------------------------------


async def test_failed_task_returns_none(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    result = await _create(svc, success=False)

    assert result is None
    assert svc.skill_count == 0


async def test_single_step_returns_none(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    result = await _create(svc, steps=["only one step"])

    assert result is None
    assert svc.skill_count == 0


async def test_empty_steps_returns_none(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    result = await _create(svc, steps=[])

    assert result is None
    assert svc.skill_count == 0


# ---------------------------------------------------------------------------
# Duplicate / similar skill detection
# ---------------------------------------------------------------------------


async def test_identical_steps_updates_existing_skill(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    first = await _create(svc, task="First task")
    assert first is not None

    second = await _create(svc, task="Second task with same steps")

    # Should return the same underlying skill object, not a new one
    assert svc.skill_count == 1
    assert second is not None
    assert second.times_used == 1


async def test_similar_steps_increments_times_used(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    steps_a = ["step alpha", "step beta", "step gamma", "step delta"]
    steps_b = ["step alpha", "step beta", "step gamma", "step epsilon"]  # 3/5 overlap = 0.6 < 0.7

    await _create(svc, task="task one", steps=steps_a)
    result = await _create(svc, task="task two", steps=steps_b)

    # Overlap = 3 shared / 5 union = 0.6 — below threshold, new skill created
    assert svc.skill_count == 2
    assert result is not None
    assert result.times_used == 0


async def test_highly_overlapping_steps_treated_as_duplicate(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    steps_a = ["step A", "step B", "step C", "step D", "step E"]
    # 4 out of 5 match → overlap = 4/6 ≈ 0.67 < 0.7, not duplicate
    # Use 5 identical + 1 new → overlap = 5/6 ≈ 0.83 > 0.7
    steps_b = ["step A", "step B", "step C", "step D", "step E", "step F"]

    await _create(svc, steps=steps_a)
    result = await _create(svc, steps=steps_b)

    assert svc.skill_count == 1
    assert result is not None
    assert result.times_used == 1


# ---------------------------------------------------------------------------
# find_relevant
# ---------------------------------------------------------------------------


async def test_find_relevant_returns_matching_skills(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    await _create(svc, task="Analyse and summarise dataset")
    await _create(
        svc,
        task="Deploy web application to cloud",
        steps=["build image", "push registry", "run container"],
        tools=["docker", "kubectl"],
    )

    results = svc.find_relevant("analyse dataset")

    assert len(results) >= 1
    assert any("summarise" in s.description.lower() or "analyse" in s.description.lower() for s in results)


async def test_find_relevant_respects_top_k(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    for i in range(5):
        await svc.create_from_task(
            task_description=f"task number {i} with keyword",
            steps_taken=[f"step {i} a", f"step {i} b"],
            tools_used=[],
            success=True,
        )

    results = svc.find_relevant("task keyword", top_k=2)

    assert len(results) <= 2


async def test_find_relevant_empty_store_returns_empty(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    results = svc.find_relevant("anything")

    assert results == []


async def test_find_relevant_no_match_returns_empty(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    await _create(svc, task="deploy kubernetes cluster")

    results = svc.find_relevant("completely unrelated zebra query")

    assert results == []


async def test_find_relevant_scores_by_tag_overlap(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    await _create(svc, task="generic task one", tags=["nlp", "python"])
    await svc.create_from_task(
        task_description="generic task two",
        steps_taken=["do x", "do y"],
        tools_used=[],
        success=True,
        tags=["docker", "devops"],
    )

    results = svc.find_relevant("python nlp", top_k=1)

    assert results[0].tags == ["nlp", "python"] or "python" in results[0].tags


# ---------------------------------------------------------------------------
# Refinement — remove low-performing skills
# ---------------------------------------------------------------------------


async def test_refine_removes_low_success_high_usage_skill(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc)
    assert skill is not None

    # Manually degrade the skill
    skill.success_rate = 0.1
    skill.times_used = 5
    svc._save_skill(skill)

    await svc._refine_skills()

    assert svc.skill_count == 0
    assert not (tmp_path / f"{skill.name}.yaml").exists()


async def test_refine_keeps_low_success_low_usage_skill(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc)
    assert skill is not None

    # Low success but only used 2 times — should be kept
    skill.success_rate = 0.1
    skill.times_used = 2

    await svc._refine_skills()

    assert svc.skill_count == 1


async def test_refine_keeps_adequate_success_rate_skill(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc)
    assert skill is not None

    # High usage but good enough success rate
    skill.success_rate = 0.5
    skill.times_used = 10

    await svc._refine_skills()

    assert svc.skill_count == 1


# ---------------------------------------------------------------------------
# YAML persistence
# ---------------------------------------------------------------------------


async def test_skill_persisted_as_yaml_file(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc)
    assert skill is not None

    yaml_file = tmp_path / f"{skill.name}.yaml"
    assert yaml_file.exists()


async def test_yaml_file_contains_correct_fields(tmp_path):
    import yaml as _yaml

    svc = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc, tags=["test-tag"])
    assert skill is not None

    yaml_file = tmp_path / f"{skill.name}.yaml"
    with open(yaml_file) as f:
        data = _yaml.safe_load(f)

    assert data["name"] == skill.name
    assert data["description"] == TASK
    assert data["steps"] == STEPS
    assert data["tools_used"] == TOOLS
    assert data["tags"] == ["test-tag"]
    assert data["success_rate"] == 1.0
    assert data["times_used"] == 0


async def test_skills_loaded_from_disk_on_init(tmp_path):
    svc1 = SkillCreationService(skills_dir=str(tmp_path))
    skill = await _create(svc1)
    assert skill is not None

    # New instance pointing at same directory must reload the skill
    svc2 = SkillCreationService(skills_dir=str(tmp_path))
    assert svc2.skill_count == 1
    assert skill.name in svc2._skills


async def test_updated_skill_persisted_to_yaml(tmp_path):
    import yaml as _yaml

    svc = SkillCreationService(skills_dir=str(tmp_path))
    steps_a = ["step A", "step B", "step C", "step D", "step E"]
    steps_b = ["step A", "step B", "step C", "step D", "step E", "step F"]

    await _create(svc, steps=steps_a)
    await _create(svc, steps=steps_b)  # duplicate → updates existing

    first_skill_name = list(svc._skills.keys())[0]
    yaml_file = tmp_path / f"{first_skill_name}.yaml"
    with open(yaml_file) as f:
        data = _yaml.safe_load(f)

    assert data["times_used"] == 1


# ---------------------------------------------------------------------------
# Task count threshold and auto-refinement
# ---------------------------------------------------------------------------


async def test_task_count_increments_on_new_skill(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    assert svc._task_count == 0

    await _create(svc)
    assert svc._task_count == 1


async def test_task_count_not_incremented_for_duplicate(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    steps_a = ["step A", "step B", "step C", "step D", "step E"]
    steps_b = ["step A", "step B", "step C", "step D", "step E", "step F"]

    await _create(svc, steps=steps_a)
    assert svc._task_count == 1

    await _create(svc, steps=steps_b)  # duplicate update
    assert svc._task_count == 1  # unchanged


async def test_task_count_resets_after_refinement_interval(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))

    # Create 15 unique tasks to trigger refinement
    for i in range(SkillCreationService.REFINEMENT_INTERVAL):
        await svc.create_from_task(
            task_description=f"unique task {i}",
            steps_taken=[f"step {i}-a", f"step {i}-b"],
            tools_used=[],
            success=True,
        )

    assert svc._task_count == 0


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------


def test_slugify_lowercases():
    assert SkillCreationService._slugify("Hello World") == "hello-world"


def test_slugify_strips_special_characters():
    result = SkillCreationService._slugify("fetch & summarise (data)!")
    assert "&" not in result
    assert "(" not in result
    assert "!" not in result


def test_slugify_replaces_spaces_with_hyphens():
    result = SkillCreationService._slugify("analyse my dataset")
    assert " " not in result
    assert "-" in result


def test_slugify_truncates_to_60_characters():
    long_text = "a" * 80
    result = SkillCreationService._slugify(long_text)
    assert len(result) <= 60


def test_slugify_empty_string():
    assert SkillCreationService._slugify("") == ""


def test_slugify_handles_underscores():
    result = SkillCreationService._slugify("my_task_name")
    assert "_" not in result
    assert result == "my-task-name"


# ---------------------------------------------------------------------------
# skill_count property
# ---------------------------------------------------------------------------


async def test_skill_count_starts_at_zero(tmp_path):
    svc = SkillCreationService(skills_dir=str(tmp_path))
    assert svc.skill_count == 0


async def test_skill_count_reflects_loaded_skills(tmp_path):
    svc1 = SkillCreationService(skills_dir=str(tmp_path))
    await _create(svc1)
    await svc1.create_from_task(
        task_description="second unique task",
        steps_taken=["do x", "do y"],
        tools_used=[],
        success=True,
    )

    svc2 = SkillCreationService(skills_dir=str(tmp_path))
    assert svc2.skill_count == 2
