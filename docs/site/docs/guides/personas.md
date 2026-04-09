# Creating Agent Personas

A **persona** defines an agent's identity, behavior, tools, and model configuration. Agent Studio supports two complementary definition styles that can be combined.

---

## YAML Persona (PM-editable)

The simplest way to define an agent. Create a YAML file in your `agents/` directory:

```yaml
# agents/support-agent.yaml
name: support-agent
role: "Customer support specialist"
description: |
  You are a customer support specialist for Acme Corp.
  You have access to the ticketing system and order database.
  Always be empathetic and solution-focused.

graph_template: react

tools:
  - mcp_zendesk_*
  - mcp_orders_get_order
  - rag_search

escalation_rules:
  - condition: "sentiment < -0.7"
    target: "human"
    priority: "urgent"
  - condition: "topic == 'legal'"
    target: "human"
    priority: "high"

model_config:
  provider: openrouter
  model: anthropic/claude-sonnet-4-6
  temperature: 0.3
  max_tokens: 4096

slo_targets:
  latency_p99_ms: 5000
  success_rate: 0.995
```

---

## YAML Schema Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique slug (used in API and WebSocket calls) |
| `role` | string | yes | One-line role for the system prompt |
| `description` | string | no | Extended system prompt context |
| `graph_template` | string | no | Graph type (see below) |
| `tools` | array | no | MCP tool patterns to expose |
| `escalation_rules` | array | no | Conditions that trigger HITL |
| `model_config` | object | no | LLM provider and parameters |
| `slo_targets` | object | no | SLO thresholds for alerting |
| `soul_md` | string | no | Path to a SOUL.md character file |

### Graph Templates

| Template | When to use |
|----------|-------------|
| `react` | Default — agent with tools, no upfront planning |
| `plan-and-execute` | Multi-step tasks with sequential dependencies |
| `llm-compiler` | Multi-step tasks where steps can run in parallel |
| `reflexion` | Output quality justifies retry loops |
| `supervisor` | Multiple sub-agents coordinating on a task |
| `orchestrator` | Full autonomous dev cycles (GSD + Superpowers) |

---

## Python Persona Override (Engineer-controlled)

For behavior that cannot be expressed in YAML, subclass `BaseAgentGraph`:

```python
from agentic_core.graph_templates.base import BaseAgentGraph
from agentic_core.decorators import agent_persona

@agent_persona("support-agent")
class SupportGraph(BaseAgentGraph):
    """
    Overrides the YAML graph_template with custom LangGraph logic.
    All other YAML fields (tools, escalation_rules, slo_targets) still apply.
    """

    def build_graph(self):
        from langgraph.graph import StateGraph
        from agentic_core.nodes import llm_node, tool_node, escalation_node

        builder = StateGraph(self.state_schema)
        builder.add_node("agent", llm_node(self.model, self.tools))
        builder.add_node("tools", tool_node(self.tool_executor))
        builder.add_node("escalate", escalation_node(self.escalation_rules))

        builder.set_entry_point("agent")
        builder.add_conditional_edges(
            "agent",
            self.route,
            {"tools": "tools", "escalate": "escalate", "end": "__end__"}
        )
        builder.add_edge("tools", "agent")

        return builder.compile(checkpointer=self.checkpointer)
```

The `@agent_persona("support-agent")` decorator registers this class and overrides the `graph_template` from the YAML file. All other YAML fields remain active.

---

## Loading Personas

### From a directory

```python
from agentic_core.persona import PersonaRegistry

registry = PersonaRegistry.from_directory("agents/")
runtime = AgentRuntime(settings, persona_registry=registry)
```

### Programmatically

```python
from agentic_core.persona import Persona

persona = Persona(
    name="quick-agent",
    role="Quick helper",
    graph_template="react",
    model_config={"provider": "ollama", "model": "llama3.2"},
)
registry.register(persona)
```

---

## SOUL.md Character Files

For rich, nuanced agent personalities, reference a [SOUL.md](soul-md.md) file:

```yaml
# agents/companion.yaml
name: companion
role: "Personal assistant"
soul_md: agents/companion.soul.md
graph_template: react
```

The SOUL.md content is injected into the system prompt in addition to the `description` field. See the [SOUL.md guide](soul-md.md) for format details.

---

## Escalation Rules

Escalation rules automatically pause the agent and notify a human operator when a condition is met:

```yaml
escalation_rules:
  - condition: "sentiment < -0.7"
    target: "human"
    priority: "urgent"
    message: "Customer sentiment is very negative — human review recommended."

  - condition: "topic in ['legal', 'compliance', 'gdpr']"
    target: "human"
    priority: "high"

  - condition: "confidence < 0.4"
    target: "human"
    priority: "normal"
    message: "Agent confidence is low — please verify the response."
```

The agent publishes a `HumanEscalationRequested` domain event and sends a `human_escalation` WebSocket message to the client. Resume with [`resume_hitl`](../api/websocket.md#resume_hitl).
