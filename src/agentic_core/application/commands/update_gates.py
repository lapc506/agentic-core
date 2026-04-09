from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentic_core.domain.value_objects.gate import Gate


class UpdateGatesCommand:
    __slots__ = ("agent_slug", "gates")

    def __init__(self, agent_slug: str, gates: list[dict[str, Any]]) -> None:
        self.agent_slug = agent_slug
        self.gates = gates


class UpdateGatesHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = Path(agents_dir)

    async def execute(self, cmd: UpdateGatesCommand) -> list[Gate]:
        yaml_path = self._agents_dir / f"{cmd.agent_slug}.yaml"

        if not yaml_path.exists():
            raise FileNotFoundError(f"Agent '{cmd.agent_slug}' not found at {yaml_path}")

        with open(yaml_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        gate_objects = [Gate(**g) for g in cmd.gates]

        data["gates"] = [g.model_dump(mode="json") for g in gate_objects]

        with open(yaml_path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

        return gate_objects
