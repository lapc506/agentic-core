from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agentic_core.application.services.persona_registry import (
    _GRAPH_REGISTRY,
    PersonaRegistry,
    agent_persona,
)
from agentic_core.domain.enums import GraphTemplate
from agentic_core.domain.services.routing import RoutingService
from agentic_core.graph_templates.base import BaseAgentGraph

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_YAML = """
name: test-agent
role: "Test role"
description: "A test persona"
graph_template: react
skills:
  - search
  - summarize
tools:
  - mcp_github_*
escalation_rules:
  - condition: "error_count > 3"
    target: "human"
    priority: "urgent"
model_config:
  provider: "anthropic"
  model: "claude-sonnet-4-6"
  temperature: 0.5
slo_targets:
  latency_p99_ms: 3000
  success_rate: 0.99
capabilities:
  gsd_enabled: true
  auto_research: false
"""

SUPERVISOR_YAML = """
name: orchestrator
role: "Orchestrator"
description: "Routes work"
graph_template: supervisor
delegate_to:
  - name: researcher
    model_config:
      provider: google
      model: gemini-2.5-pro
  - name: writer
"""


def test_discover_yaml(tmp_path: Path):
    (tmp_path / "test-agent.yaml").write_text(SAMPLE_YAML)
    routing = RoutingService()
    registry = PersonaRegistry(routing)

    count = registry.discover(tmp_path)
    assert count == 1

    persona = routing.resolve("test-agent")
    assert persona.role == "Test role"
    assert persona.graph_template == GraphTemplate.REACT
    assert len(persona.skills) == 2
    assert len(persona.escalation_rules) == 1
    assert persona.escalation_rules[0].priority == "urgent"
    assert persona.model_config is not None
    assert persona.model_config.model == "claude-sonnet-4-6"
    assert persona.slo_targets is not None
    assert persona.slo_targets.latency_p99_ms == 3000
    assert persona.capabilities.gsd_enabled is True


def test_discover_supervisor_with_delegates(tmp_path: Path):
    (tmp_path / "orchestrator.yaml").write_text(SUPERVISOR_YAML)
    routing = RoutingService()
    registry = PersonaRegistry(routing)

    count = registry.discover(tmp_path)
    assert count == 1

    persona = routing.resolve("orchestrator")
    assert persona.graph_template == GraphTemplate.SUPERVISOR
    assert len(persona.delegate_to) == 2
    assert persona.delegate_to[0].name == "researcher"
    assert persona.delegate_to[0].model_config is not None
    assert persona.delegate_to[0].model_config.provider == "google"
    assert persona.delegate_to[1].model_config is None


def test_discover_empty_dir(tmp_path: Path):
    routing = RoutingService()
    registry = PersonaRegistry(routing)
    count = registry.discover(tmp_path)
    assert count == 0


def test_discover_nonexistent_dir():
    routing = RoutingService()
    registry = PersonaRegistry(routing)
    count = registry.discover("/nonexistent/path")
    assert count == 0


def test_agent_persona_decorator(tmp_path: Path):
    # Clean global registry state for this test
    _GRAPH_REGISTRY.clear()

    @agent_persona("test-agent")
    class MyGraph(BaseAgentGraph):
        def build_graph(self) -> Any:
            return "my_graph"

    (tmp_path / "test-agent.yaml").write_text(SAMPLE_YAML)
    routing = RoutingService()
    registry = PersonaRegistry(routing)
    registry.discover(tmp_path)

    persona = routing.resolve("test-agent")
    assert persona.graph_cls is MyGraph

    _GRAPH_REGISTRY.clear()


def test_multiple_personas(tmp_path: Path):
    (tmp_path / "agent-a.yaml").write_text(SAMPLE_YAML.replace("test-agent", "agent-a"))
    (tmp_path / "agent-b.yaml").write_text(SAMPLE_YAML.replace("test-agent", "agent-b"))
    routing = RoutingService()
    registry = PersonaRegistry(routing)
    count = registry.discover(tmp_path)
    assert count == 2
    assert len(routing.list_personas()) == 2
