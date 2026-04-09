from __future__ import annotations

import os

import pytest
import yaml

from agentic_core.application.commands.create_agent import CreateAgentCommand, CreateAgentHandler
from agentic_core.domain.enums import GraphTemplate


@pytest.fixture
def agents_dir(tmp_path):
    return str(tmp_path)


async def test_create_agent_writes_yaml(agents_dir):
    handler = CreateAgentHandler(agents_dir=agents_dir)
    cmd = CreateAgentCommand(name="Test Agent", role="assistant", description="A test agent", graph_template="react")
    persona = await handler.execute(cmd)
    assert persona.name == "Test Agent"
    assert persona.graph_template == GraphTemplate.REACT
    yaml_path = os.path.join(agents_dir, "test-agent.yaml")
    assert os.path.exists(yaml_path)
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert data["name"] == "Test Agent"


async def test_create_agent_slugifies_name(agents_dir):
    handler = CreateAgentHandler(agents_dir=agents_dir)
    cmd = CreateAgentCommand(name="Asistente Aduanero", role="customs", description="Customs assistant", graph_template="react")
    await handler.execute(cmd)
    assert os.path.exists(os.path.join(agents_dir, "asistente-aduanero.yaml"))


async def test_create_agent_defaults(agents_dir):
    handler = CreateAgentHandler(agents_dir=agents_dir)
    cmd = CreateAgentCommand(name="Simple Agent", role="helper", description="Simple")
    persona = await handler.execute(cmd)
    assert persona.graph_template == GraphTemplate.REACT
    assert persona.tools == []
    yaml_path = os.path.join(agents_dir, "simple-agent.yaml")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert data["gates"] == []
    assert data["system_prompt"] == ""


async def test_create_agent_yaml_contains_all_fields(agents_dir):
    handler = CreateAgentHandler(agents_dir=agents_dir)
    cmd = CreateAgentCommand(
        name="Full Agent",
        role="analyst",
        description="Full agent",
        graph_template="react",
        tools=["search", "calculator"],
        system_prompt="You are an analyst.",
    )
    await handler.execute(cmd)
    yaml_path = os.path.join(agents_dir, "full-agent.yaml")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert data["tools"] == ["search", "calculator"]
    assert data["system_prompt"] == "You are an analyst."
    assert data["gates"] == []


async def test_update_agent_modifies_fields(agents_dir):
    from agentic_core.application.commands.update_agent import (
        UpdateAgentCommand,
        UpdateAgentHandler,
    )

    # Create first
    create_handler = CreateAgentHandler(agents_dir=agents_dir)
    await create_handler.execute(CreateAgentCommand(name="Update Me", role="original", description="original desc"))

    # Update
    update_handler = UpdateAgentHandler(agents_dir=agents_dir)
    cmd = UpdateAgentCommand(agent_slug="update-me", updates={"role": "updated", "description": "new desc"})
    result = await update_handler.execute(cmd)

    assert result["role"] == "updated"
    assert result["description"] == "new desc"
    # Verify persisted
    yaml_path = os.path.join(agents_dir, "update-me.yaml")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    assert data["role"] == "updated"


async def test_update_agent_ignores_disallowed_keys(agents_dir):
    from agentic_core.application.commands.update_agent import (
        UpdateAgentCommand,
        UpdateAgentHandler,
    )

    create_handler = CreateAgentHandler(agents_dir=agents_dir)
    await create_handler.execute(CreateAgentCommand(name="Guard Agent", role="guard", description="guarded"))

    update_handler = UpdateAgentHandler(agents_dir=agents_dir)
    # 'gates' is not in the allowed keys for UpdateAgentCommand
    cmd = UpdateAgentCommand(agent_slug="guard-agent", updates={"role": "changed", "secret_field": "injected"})
    result = await update_handler.execute(cmd)

    assert result["role"] == "changed"
    assert "secret_field" not in result


async def test_update_agent_raises_if_not_found(agents_dir):
    from agentic_core.application.commands.update_agent import (
        UpdateAgentCommand,
        UpdateAgentHandler,
    )

    handler = UpdateAgentHandler(agents_dir=agents_dir)
    cmd = UpdateAgentCommand(agent_slug="nonexistent", updates={"role": "x"})
    with pytest.raises(FileNotFoundError):
        await handler.execute(cmd)


async def test_update_gates_persists_to_yaml(agents_dir):
    from agentic_core.application.commands.update_gates import (
        UpdateGatesCommand,
        UpdateGatesHandler,
    )
    from agentic_core.domain.value_objects.gate import GateAction

    # Setup: create agent first
    create_handler = CreateAgentHandler(agents_dir=agents_dir)
    await create_handler.execute(CreateAgentCommand(name="Test Agent", role="test", description="test"))

    # Update gates
    handler = UpdateGatesHandler(agents_dir=agents_dir)
    gates = [
        {"name": "PII", "content": "Filter PII", "action": "block", "order": 0},
        {"name": "Tone", "content": "Check tone", "action": "rewrite", "order": 1},
    ]
    cmd = UpdateGatesCommand(agent_slug="test-agent", gates=gates)
    result = await handler.execute(cmd)

    assert len(result) == 2
    assert result[0].name == "PII"
    assert result[1].action == GateAction.REWRITE

    # Verify persisted
    with open(os.path.join(agents_dir, "test-agent.yaml")) as f:
        data = yaml.safe_load(f)
    assert len(data["gates"]) == 2


async def test_update_gates_raises_if_not_found(agents_dir):
    from agentic_core.application.commands.update_gates import (
        UpdateGatesCommand,
        UpdateGatesHandler,
    )

    handler = UpdateGatesHandler(agents_dir=agents_dir)
    cmd = UpdateGatesCommand(agent_slug="ghost", gates=[])
    with pytest.raises(FileNotFoundError):
        await handler.execute(cmd)
