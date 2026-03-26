# AGENTS.md -- Guide for AI Coding Assistants

This file tells AI assistants (Claude Code, Cursor, Copilot) how to work with agentic-core.

## Architecture

agentic-core uses **Explicit Architecture** (Hexagonal + DDD + CQRS). The dependency rule: all arrows point inward.

```
Primary Adapters (WebSocket, gRPC)  -- call into -->
  Application Layer (Commands, Queries, Ports, Middleware)  -- uses -->
    Domain Layer (Entities, Value Objects, Events, Services)
  Application Layer  <-- implemented by --
Secondary Adapters (Redis, PostgreSQL, pgvector, FalkorDB, OTel, Langfuse, MCP)
```

**Never import concrete adapters in domain or application code.** Only import port ABCs.

## Creating a New Graph

1. Create a persona YAML in `agents/`:

```yaml
name: my-agent
role: "Description of what it does"
graph_template: react          # react | plan-and-execute | reflexion | supervisor
tools:
  - mcp_tool_name_*
model_config:
  provider: anthropic
  model: claude-sonnet-4-6
```

2. (Optional) Override with code:

```python
from agentic_core.application.services.persona_registry import agent_persona
from agentic_core.graph_templates.base import BaseAgentGraph

@agent_persona("my-agent")
class MyGraph(BaseAgentGraph):
    def build_graph(self):
        # Custom LangGraph StateGraph
        ...
```

## Graph Template Decision Tree

```
Does your agent use tools?
  No  -> Direct LLM (no graph)
  Yes -> Needs multi-step planning?
           No  -> react (default, 80% of cases)
           Yes -> Steps independent?
                    Yes -> llm-compiler (parallel)
                    No  -> plan-and-execute

Output quality needs retry loops? -> reflexion (wraps any template)
Multiple personas collaborating?  -> supervisor
Full autonomous dev cycles?       -> orchestrator
```

## Key Conventions

- **Domain layer** (`domain/`): Pure Python. Zero external imports. No async.
- **Application layer** (`application/`): Port ABCs, command/query handlers, middleware.
- **Adapters** (`adapters/`): Concrete implementations. Primary = driving (WS, gRPC). Secondary = driven (Redis, PG...).
- **Tests**: Mirror source structure in `tests/unit/`. Integration tests require `RUN_INTEGRATION=1`.
- **Config**: All via env vars with `AGENTIC_` prefix. Nested: `AGENTIC_DEFAULT_MODEL__MODEL=claude-opus-4-6`.

## Running

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v                    # unit tests
make proto                   # regenerate gRPC stubs
make lint                    # ruff
make typecheck               # mypy
```

## SRE Practices

- Every persona can define `slo_targets` in YAML (latency_p99, success_rate)
- SLOTracker publishes SLOBreached events when thresholds are exceeded
- ChaosHooks available for resilience testing (opt-in)
- All observability signals correlated via trace_id
