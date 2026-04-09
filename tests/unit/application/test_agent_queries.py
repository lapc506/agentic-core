import pytest
import yaml

from agentic_core.application.queries.list_agents import ListAgentsHandler, ListAgentsQuery


@pytest.fixture
def agents_dir(tmp_path):
    for name, role in [("agent-one", "assistant"), ("agent-two", "reviewer")]:
        data = {"name": name, "role": role, "description": "test", "gates": [], "tools": []}
        with open(tmp_path / f"{name}.yaml", "w") as f:
            yaml.dump(data, f)
    return str(tmp_path)


async def test_list_agents_returns_all(agents_dir):
    handler = ListAgentsHandler(agents_dir=agents_dir)
    result = await handler.execute(ListAgentsQuery())
    assert len(result) == 2
    names = {a["name"] for a in result}
    assert names == {"agent-one", "agent-two"}


async def test_list_agents_includes_slug(agents_dir):
    handler = ListAgentsHandler(agents_dir=agents_dir)
    result = await handler.execute(ListAgentsQuery())
    slugs = {a["slug"] for a in result}
    assert "agent-one" in slugs
