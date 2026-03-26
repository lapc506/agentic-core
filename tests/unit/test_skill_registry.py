from __future__ import annotations

from agentic_core.application.services.skill_registry import (
    SkillDefinition,
    SkillRegistry,
)


def _make_skill(
    name: str = "summarize",
    tags: list[str] | None = None,
) -> SkillDefinition:
    return SkillDefinition(
        name=name,
        description="Summarize a document",
        instructions="Read the document and produce a concise summary.",
        author="agent-1",
        tags=tags or ["nlp", "text"],
    )


def test_skill_definition_construction() -> None:
    s = _make_skill()
    assert s.name == "summarize"
    assert s.version == 1
    assert s.success_rate == 0.0
    assert s.usage_count == 0
    assert s.author == "agent-1"
    assert len(s.tags) == 2


def test_skill_definition_frozen() -> None:
    s = _make_skill()
    try:
        s.name = "other"  # type: ignore[misc]
        assert False, "Should have raised"
    except Exception:
        pass


def test_register_and_get() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill())
    skill = reg.get("summarize")
    assert skill is not None
    assert skill.name == "summarize"


def test_get_unknown_returns_none() -> None:
    reg = SkillRegistry()
    assert reg.get("nonexistent") is None


def test_list_skills_all() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill("a"))
    reg.register(_make_skill("b"))
    reg.register(_make_skill("c"))
    assert len(reg.list_skills()) == 3


def test_list_skills_filter_by_tag() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill("a", tags=["nlp"]))
    reg.register(_make_skill("b", tags=["code"]))
    reg.register(_make_skill("c", tags=["nlp", "code"]))
    assert len(reg.list_skills(tag="nlp")) == 2
    assert len(reg.list_skills(tag="code")) == 2
    assert len(reg.list_skills(tag="other")) == 0


def test_update_stats_success() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill())
    reg.update_stats("summarize", success=True)
    skill = reg.get("summarize")
    assert skill is not None
    assert skill.usage_count == 1
    assert skill.success_rate == 1.0


def test_update_stats_failure() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill())
    reg.update_stats("summarize", success=False)
    skill = reg.get("summarize")
    assert skill is not None
    assert skill.usage_count == 1
    assert skill.success_rate == 0.0


def test_update_stats_mixed() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill())
    reg.update_stats("summarize", success=True)
    reg.update_stats("summarize", success=False)
    reg.update_stats("summarize", success=True)
    skill = reg.get("summarize")
    assert skill is not None
    assert skill.usage_count == 3
    assert abs(skill.success_rate - 2.0 / 3.0) < 0.01


def test_update_stats_unknown_is_noop() -> None:
    reg = SkillRegistry()
    # Should not raise
    reg.update_stats("nonexistent", success=True)


def test_export_skill() -> None:
    reg = SkillRegistry()
    reg.register(_make_skill())
    exported = reg.export_skill("summarize")
    assert exported is not None
    assert exported["name"] == "summarize"
    assert exported["instructions"] == "Read the document and produce a concise summary."
    assert "tags" in exported


def test_export_unknown_returns_none() -> None:
    reg = SkillRegistry()
    assert reg.export_skill("nonexistent") is None


def test_import_skill() -> None:
    reg = SkillRegistry()
    data = {
        "name": "translate",
        "description": "Translate text",
        "instructions": "Translate the given text to the target language.",
        "version": 2,
        "author": "community",
        "tags": ["nlp", "i18n"],
        "success_rate": 0.95,
        "usage_count": 100,
    }
    skill = reg.import_skill(data)
    assert skill.name == "translate"
    assert skill.version == 2
    assert skill.success_rate == 0.95
    assert skill.usage_count == 100
    # Also stored in registry
    assert reg.get("translate") is not None


def test_export_import_roundtrip() -> None:
    reg = SkillRegistry()
    original = _make_skill()
    reg.register(original)
    exported = reg.export_skill("summarize")
    assert exported is not None

    reg2 = SkillRegistry()
    imported = reg2.import_skill(exported)
    assert imported.name == original.name
    assert imported.description == original.description
    assert imported.instructions == original.instructions
    assert imported.tags == list(original.tags)
    assert imported.author == original.author
