from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

PERSONALITY_PRESETS: dict[str, str] = {
    "professional": (
        "You are a professional assistant. Communicate clearly and concisely. "
        "Use formal language, avoid slang, and focus on accuracy. "
        "Structure responses logically with clear headings when appropriate."
    ),
    "casual": (
        "You are a friendly, approachable assistant. Use conversational language "
        "and a warm tone. Keep things simple and relatable. "
        "It is okay to use contractions and informal phrasing."
    ),
    "technical": (
        "You are a technical expert. Prioritize precision and depth. "
        "Use domain-specific terminology, include code examples when relevant, "
        "and cite sources or standards. Assume the reader has technical background."
    ),
    "friendly": (
        "You are a supportive and encouraging assistant. Be empathetic and patient. "
        "Celebrate progress, offer gentle suggestions, and maintain a positive tone. "
        "Make the user feel comfortable asking follow-up questions."
    ),
}


class PersonalityConfig(BaseModel, frozen=True):
    """Configuration for persona personality and context file injection."""

    soul_file: str | None = None
    preset: str | None = None
    context_files: list[str] = []


class ContextLoader:
    """Loads personality definitions and context files for persona prompt injection."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = Path(base_dir)

    def load_personality(self, config: PersonalityConfig) -> str:
        """Load personality from SOUL.md file or a built-in preset.

        SOUL.md takes precedence over preset when both are specified.
        Returns an empty string if neither is configured or the file is missing.
        """
        if config.soul_file is not None:
            resolved = self._resolve_path(config.soul_file)
            content = self._read_file(resolved)
            if content:
                return content

        if config.preset is not None:
            preset_content = PERSONALITY_PRESETS.get(config.preset)
            if preset_content is not None:
                return preset_content
            logger.warning("Unknown personality preset: %s", config.preset)

        return ""

    def load_context_files(self, config: PersonalityConfig) -> list[str]:
        """Load all configured context files, skipping any that are missing."""
        results: list[str] = []
        for file_path in config.context_files:
            resolved = self._resolve_path(file_path)
            content = self._read_file(resolved)
            if content:
                results.append(content)
        return results

    def build_context(self, config: PersonalityConfig) -> str:
        """Combine personality and context files into a single injection string."""
        parts: list[str] = []

        personality = self.load_personality(config)
        if personality:
            parts.append(personality)

        for content in self.load_context_files(config):
            parts.append(content)

        return "\n\n".join(parts)

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a path relative to base_dir, or use as-is if absolute."""
        p = Path(file_path)
        if p.is_absolute():
            return p
        return self._base_dir / p

    def _read_file(self, path: Path) -> str:
        """Read file contents, returning empty string on failure."""
        try:
            return path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Could not read file %s: %s", path, exc)
            return ""
