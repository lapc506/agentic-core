from __future__ import annotations

import os

import yaml


class ListAgentsQuery:
    pass


class ListAgentsHandler:
    def __init__(self, agents_dir: str) -> None:
        self._agents_dir = agents_dir

    async def execute(self, query: ListAgentsQuery) -> list[dict]:
        results = []
        try:
            filenames = sorted(
                f for f in os.listdir(self._agents_dir) if f.endswith(".yaml")
            )
        except FileNotFoundError:
            return []

        for filename in filenames:
            path = os.path.join(self._agents_dir, filename)
            with open(path) as fh:
                data = yaml.safe_load(fh) or {}
            slug = filename[: -len(".yaml")]
            data["slug"] = slug
            results.append(data)

        return results
