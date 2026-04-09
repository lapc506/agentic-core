from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ALLOWED_KEYS = frozenset({"name", "role", "description", "graph_template", "tools", "system_prompt"})


class UpdateAgentCommand:
    __slots__ = ("agent_slug", "updates")

    def __init__(self, agent_slug: str, updates: dict[str, Any]) -> None:
        self.agent_slug = agent_slug
        self.updates = updates


class UpdateAgentHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = Path(agents_dir)

    async def execute(self, cmd: UpdateAgentCommand) -> dict[str, Any]:
        yaml_path = self._agents_dir / f"{cmd.agent_slug}.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Agent '{cmd.agent_slug}' not found at {yaml_path}")

        with open(yaml_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        for key, value in cmd.updates.items():
            if key in _ALLOWED_KEYS:
                data[key] = value

        with open(yaml_path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

        return data
