from __future__ import annotations

import re
from pathlib import Path

import yaml

from agentic_core.domain.entities.persona import Persona
from agentic_core.domain.enums import GraphTemplate


def _slugify(name: str) -> str:
    """Convert a name to a URL-safe slug: lowercase, spaces to hyphens, remove special chars."""
    slug = name.lower()
    slug = slug.replace(" ", "-")
    # Remove all characters that are not alphanumeric or hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # Collapse consecutive hyphens
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug


class CreateAgentCommand:
    __slots__ = ("name", "role", "description", "graph_template", "tools", "system_prompt")

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        graph_template: str = "react",
        tools: list[str] | None = None,
        system_prompt: str = "",
    ) -> None:
        self.name = name
        self.role = role
        self.description = description
        self.graph_template = graph_template
        self.tools = tools if tools is not None else []
        self.system_prompt = system_prompt


class CreateAgentHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = Path(agents_dir)

    async def execute(self, cmd: CreateAgentCommand) -> Persona:
        graph_template = GraphTemplate(cmd.graph_template)
        persona = Persona(
            name=cmd.name,
            role=cmd.role,
            description=cmd.description,
            graph_template=graph_template,
            tools=list(cmd.tools),
        )

        slug = _slugify(cmd.name)
        yaml_path = self._agents_dir / f"{slug}.yaml"

        data = {
            "name": cmd.name,
            "role": cmd.role,
            "description": cmd.description,
            "graph_template": cmd.graph_template,
            "tools": list(cmd.tools),
            "system_prompt": cmd.system_prompt,
            "gates": [],
        }

        self._agents_dir.mkdir(parents=True, exist_ok=True)
        with open(yaml_path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

        return persona
