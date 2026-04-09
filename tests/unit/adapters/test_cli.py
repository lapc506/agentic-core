"""Tests for CLI primary adapter (#58)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from agentic_core.adapters.primary.cli import CLITransport, CommandNotFoundError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

REVIEW_CMD = """\
---
persona: code-reviewer
graph_template: reflexion
---

Review the following file for bugs: $ARGUMENTS
"""

TRANSLATE_CMD = """\
---
persona: translator
---

Translate to Spanish: $ARGUMENTS
"""

NO_FRONTMATTER_CMD = """\
Just do this: $ARGUMENTS
"""

HTML_FRONTMATTER_CMD = """\
<!--
persona: html-agent
graph_template: react
-->

Process: $ARGUMENTS
"""


def test_discover_commands(tmp_path: Path):
    (tmp_path / "review.md").write_text(REVIEW_CMD)
    (tmp_path / "translate.md").write_text(TRANSLATE_CMD)

    cli = CLITransport(commands_dir=tmp_path)
    count = cli.discover()
    assert count == 2
    assert "review" in [c.name for c in cli.list_commands()]
    assert "translate" in [c.name for c in cli.list_commands()]


def test_discover_empty_dir(tmp_path: Path):
    cli = CLITransport(commands_dir=tmp_path)
    assert cli.discover() == 0


def test_discover_nonexistent_dir():
    cli = CLITransport(commands_dir="/nonexistent")
    assert cli.discover() == 0


def test_get_command(tmp_path: Path):
    (tmp_path / "review.md").write_text(REVIEW_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()

    cmd = cli.get_command("review")
    assert cmd.persona == "code-reviewer"
    assert cmd.graph_template == "reflexion"
    assert "$ARGUMENTS" in cmd.content


def test_get_command_not_found(tmp_path: Path):
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()
    with pytest.raises(CommandNotFoundError, match="not found"):
        cli.get_command("nonexistent")


def test_parse_yaml_frontmatter(tmp_path: Path):
    (tmp_path / "review.md").write_text(REVIEW_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()
    cmd = cli.get_command("review")
    assert cmd.persona == "code-reviewer"
    assert cmd.graph_template == "reflexion"
    assert "Review the following file" in cmd.content
    assert "---" not in cmd.content


def test_parse_html_frontmatter(tmp_path: Path):
    (tmp_path / "process.md").write_text(HTML_FRONTMATTER_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()
    cmd = cli.get_command("process")
    assert cmd.persona == "html-agent"
    assert cmd.graph_template == "react"


def test_parse_no_frontmatter(tmp_path: Path):
    (tmp_path / "plain.md").write_text(NO_FRONTMATTER_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()
    cmd = cli.get_command("plain")
    assert cmd.persona == "plain"  # defaults to filename
    assert cmd.graph_template is None


def test_arguments_replacement(tmp_path: Path):
    (tmp_path / "review.md").write_text(REVIEW_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()
    cmd = cli.get_command("review")
    content = cmd.content.replace("$ARGUMENTS", "src/main.py")
    assert "Review the following file for bugs: src/main.py" in content


async def test_execute_streams_tokens(tmp_path: Path):
    (tmp_path / "review.md").write_text(REVIEW_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()

    async def mock_create(persona_id: str, user_id: str) -> str:
        return "sess_cli_1"

    async def mock_message(session_id: str, persona_id: str, content: str) -> AsyncIterator[dict[str, Any]]:
        assert persona_id == "code-reviewer"
        assert "src/main.py" in content
        yield {"type": "stream_token", "token": "Looks "}
        yield {"type": "stream_token", "token": "good!"}

    cli.on_create_session = mock_create
    cli.on_message = mock_message

    tokens: list[str] = []
    async for token in cli.execute("review", "src/main.py"):
        tokens.append(token)

    assert tokens == ["Looks ", "good!"]


async def test_execute_handles_error(tmp_path: Path):
    (tmp_path / "review.md").write_text(REVIEW_CMD)
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()

    async def mock_create(persona_id: str, user_id: str) -> str:
        return "sess_err"

    async def mock_message(session_id: str, persona_id: str, content: str) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "error", "code": "internal_error", "message": "boom"}

    cli.on_create_session = mock_create
    cli.on_message = mock_message

    tokens: list[str] = []
    async for token in cli.execute("review", "file.py"):
        tokens.append(token)

    assert any("ERROR" in t for t in tokens)
    assert any("boom" in t for t in tokens)


async def test_execute_command_not_found(tmp_path: Path):
    cli = CLITransport(commands_dir=tmp_path)
    cli.discover()
    with pytest.raises(CommandNotFoundError):
        async for _ in cli.execute("nope", "args"):
            pass
