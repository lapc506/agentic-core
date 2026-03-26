from __future__ import annotations

from pathlib import Path

from agentic_core.application.services.context_loader import (
    PERSONALITY_PRESETS,
    ContextLoader,
    PersonalityConfig,
)
from agentic_core.domain.entities.persona import Persona


# --- PersonalityConfig defaults ---


def test_personality_config_defaults() -> None:
    config = PersonalityConfig()
    assert config.soul_file is None
    assert config.preset is None
    assert config.context_files == []


def test_personality_config_with_values() -> None:
    config = PersonalityConfig(
        soul_file="SOUL.md",
        preset="professional",
        context_files=[".cursorrules", "CONVENTIONS.md"],
    )
    assert config.soul_file == "SOUL.md"
    assert config.preset == "professional"
    assert len(config.context_files) == 2


# --- Preset loading ---


def test_load_preset_professional(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(preset="professional")
    result = loader.load_personality(config)
    assert result == PERSONALITY_PRESETS["professional"]


def test_load_preset_casual(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(preset="casual")
    result = loader.load_personality(config)
    assert result == PERSONALITY_PRESETS["casual"]


def test_load_preset_technical(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(preset="technical")
    result = loader.load_personality(config)
    assert result == PERSONALITY_PRESETS["technical"]


def test_load_preset_friendly(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(preset="friendly")
    result = loader.load_personality(config)
    assert result == PERSONALITY_PRESETS["friendly"]


def test_load_unknown_preset_returns_empty(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(preset="nonexistent")
    result = loader.load_personality(config)
    assert result == ""


# --- SOUL.md file loading ---


def test_load_soul_file(tmp_path: Path) -> None:
    soul = tmp_path / "SOUL.md"
    soul.write_text("You are a pirate captain. Speak with authority and sea metaphors.")
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(soul_file="SOUL.md")
    result = loader.load_personality(config)
    assert "pirate captain" in result


def test_soul_file_takes_precedence_over_preset(tmp_path: Path) -> None:
    soul = tmp_path / "SOUL.md"
    soul.write_text("Custom soul content")
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(soul_file="SOUL.md", preset="professional")
    result = loader.load_personality(config)
    assert result == "Custom soul content"
    assert result != PERSONALITY_PRESETS["professional"]


def test_missing_soul_file_falls_back_to_preset(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(soul_file="missing_SOUL.md", preset="casual")
    result = loader.load_personality(config)
    assert result == PERSONALITY_PRESETS["casual"]


def test_missing_soul_file_no_preset_returns_empty(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(soul_file="missing_SOUL.md")
    result = loader.load_personality(config)
    assert result == ""


def test_soul_file_absolute_path(tmp_path: Path) -> None:
    soul = tmp_path / "SOUL.md"
    soul.write_text("Absolute path soul")
    loader = ContextLoader("/some/other/dir")
    config = PersonalityConfig(soul_file=str(soul))
    result = loader.load_personality(config)
    assert result == "Absolute path soul"


# --- Context files loading ---


def test_load_context_files(tmp_path: Path) -> None:
    (tmp_path / ".cursorrules").write_text("rule: always use type hints")
    (tmp_path / "CONVENTIONS.md").write_text("# Conventions\nUse snake_case.")
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(context_files=[".cursorrules", "CONVENTIONS.md"])
    results = loader.load_context_files(config)
    assert len(results) == 2
    assert "type hints" in results[0]
    assert "snake_case" in results[1]


def test_load_context_files_skips_missing(tmp_path: Path) -> None:
    (tmp_path / "exists.md").write_text("I exist")
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(context_files=["exists.md", "missing.md"])
    results = loader.load_context_files(config)
    assert len(results) == 1
    assert "I exist" in results[0]


def test_load_context_files_empty_list(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(context_files=[])
    results = loader.load_context_files(config)
    assert results == []


# --- build_context ---


def test_build_context_personality_and_files(tmp_path: Path) -> None:
    soul = tmp_path / "SOUL.md"
    soul.write_text("You are a helpful bot.")
    (tmp_path / ".cursorrules").write_text("Use Python 3.12+")
    (tmp_path / "STYLE.md").write_text("Be concise")

    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(
        soul_file="SOUL.md",
        context_files=[".cursorrules", "STYLE.md"],
    )
    result = loader.build_context(config)
    assert "You are a helpful bot." in result
    assert "Use Python 3.12+" in result
    assert "Be concise" in result
    # Parts are joined by double newline
    assert "\n\n" in result


def test_build_context_preset_only(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(preset="technical")
    result = loader.build_context(config)
    assert result == PERSONALITY_PRESETS["technical"]


def test_build_context_empty_config(tmp_path: Path) -> None:
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig()
    result = loader.build_context(config)
    assert result == ""


def test_build_context_files_only(tmp_path: Path) -> None:
    (tmp_path / "rules.txt").write_text("Always test your code")
    loader = ContextLoader(str(tmp_path))
    config = PersonalityConfig(context_files=["rules.txt"])
    result = loader.build_context(config)
    assert result == "Always test your code"


# --- Persona entity with personality field ---


def test_persona_default_personality_is_none() -> None:
    persona = Persona(name="test", role="tester", description="A test persona")
    assert persona.personality is None


def test_persona_with_personality_config() -> None:
    config = PersonalityConfig(preset="professional", context_files=["rules.md"])
    persona = Persona(
        name="test",
        role="tester",
        description="A test persona",
        personality=config,
    )
    assert persona.personality is not None
    assert persona.personality.preset == "professional"
    assert persona.personality.context_files == ["rules.md"]
