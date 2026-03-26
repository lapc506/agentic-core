"""CLI primary adapter: custom commands with $ARGUMENTS placeholder support (#58)."""
from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

ARGUMENTS_PLACEHOLDER = "$ARGUMENTS"


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    content: str
    persona: str
    graph_template: str | None
    model_config: dict[str, Any] | None
    source_path: Path


class CommandNotFoundError(Exception):
    pass


class CLITransport:
    """Primary adapter for terminal/CLI interaction.
    Discovers commands from .md files, replaces $ARGUMENTS, routes to personas."""

    def __init__(self, commands_dir: str | Path = "commands") -> None:
        self._commands_dir = Path(commands_dir)
        self._commands: dict[str, CommandDefinition] = {}

        # Callbacks (wired by runtime)
        self.on_create_session: Callable[[str, str], Awaitable[str]] | None = None
        self.on_message: Callable[[str, str, str], AsyncIterator[dict[str, Any]]] | None = None

    def discover(self) -> int:
        self._commands.clear()
        if not self._commands_dir.exists():
            logger.warning("Commands directory not found: %s", self._commands_dir)
            return 0

        count = 0
        for md_file in sorted(self._commands_dir.glob("*.md")):
            try:
                cmd = self._parse_command(md_file)
                self._commands[cmd.name] = cmd
                count += 1
                logger.info("Discovered command: /%s (persona=%s)", cmd.name, cmd.persona)
            except Exception:
                logger.exception("Failed to parse command: %s", md_file)
        return count

    def list_commands(self) -> list[CommandDefinition]:
        return list(self._commands.values())

    def get_command(self, name: str) -> CommandDefinition:
        cmd = self._commands.get(name)
        if cmd is None:
            raise CommandNotFoundError(f"Command '/{name}' not found. Available: {list(self._commands.keys())}")
        return cmd

    async def execute(self, command_name: str, arguments: str) -> AsyncIterator[str]:
        cmd = self.get_command(command_name)
        content = cmd.content.replace(ARGUMENTS_PLACEHOLDER, arguments)
        persona_id = cmd.persona

        # Create session
        session_id = "cli_session"
        if self.on_create_session is not None:
            session_id = await self.on_create_session(persona_id, "cli_user")

        # Send message and stream response
        if self.on_message is not None:
            async for chunk in self.on_message(session_id, persona_id, content):
                chunk_type = chunk.get("type", "")
                if chunk_type == "stream_token":
                    yield chunk.get("token", "")
                elif chunk_type == "error":
                    yield f"\n[ERROR] {chunk.get('code', '')}: {chunk.get('message', '')}\n"

    def _parse_command(self, path: Path) -> CommandDefinition:
        raw = path.read_text(encoding="utf-8")
        frontmatter, content = self._split_frontmatter(raw)

        meta = yaml.safe_load(frontmatter) if frontmatter else {}
        if not isinstance(meta, dict):
            meta = {}

        persona = meta.get("persona", path.stem)
        graph_template = meta.get("graph_template")
        model_config = meta.get("model_config")

        return CommandDefinition(
            name=path.stem,
            content=content.strip(),
            persona=persona,
            graph_template=graph_template,
            model_config=model_config,
            source_path=path,
        )

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[str, str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        # Try HTML comment frontmatter (<!-- ... -->)
        match = re.match(r"^<!--\s*\n(.*?)\n-->\s*\n(.*)$", raw, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return "", raw
