# agentic-core

Production-ready Python 3.12+ library for AI agent orchestration. Designed as a shared dependency for any startup integrating autonomous agents into their Kubernetes infrastructure.

## Architecture

Built on [Explicit Architecture](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/) (Hexagonal + DDD + CQRS):

```
Primary Adapters (WebSocket, gRPC)
        |
Application Layer (Commands, Queries, Ports, Middleware)
        |
Domain Layer (Entities, Value Objects, Events, Services)
        |
Secondary Adapters (Redis, PostgreSQL, pgvector, FalkorDB, OTel, Langfuse, MCP)
```

**Dependency rule:** All arrows point inward. Infrastructure depends on domain-defined ports, never the reverse.

## Key Features

- **Hybrid Transport** -- WebSocket (bidirectional, streaming, voice) + gRPC (backend-to-sidecar)
- **LangGraph Orchestration** -- Pluggable graph templates: ReAct, Plan-and-Execute, Reflexion, LLM-Compiler, Supervisor, Orchestrator
- **Unified Memory** -- Redis + PostgreSQL + pgvector + FalkorDB (all required)
- **MCP Bridge** -- Discover and execute tools from MCP servers with phantom tool prevention
- **Multimodal RAG** -- Gemini Embedding 2 (text + image + audio + video + PDF in one vector space) with Matryoshka dimension control
- **Meta-Orchestration** -- GSD Sequencer, Superpowers Flow, Auto Research Loop for self-improving agents
- **Hybrid Persona System** -- YAML config (PM-editable) + Python code (engineer override)
- **LLM Model Cascading** -- Runtime -> Persona -> Sub-agent inheritance with per-level override
- **Full SRE Observability** -- OpenTelemetry + Prometheus + Loki + Tempo + Grafana + Langfuse + Alertmanager
- **Kubernetes-Native** -- Dual deployment: standalone or sidecar, single Helm chart

## Quick Start

```bash
pip install agentic-core
```

### Define a Persona (YAML)

```yaml
# agents/support-agent.yaml
name: support-agent
role: "Customer support specialist"
graph_template: react
tools:
  - mcp_zendesk_*
  - rag_search
escalation_rules:
  - condition: "sentiment < -0.7"
    target: "human"
    priority: "urgent"
model_config:
  provider: "anthropic"
  model: "claude-sonnet-4-6"
  temperature: 0.3
slo_targets:
  latency_p99_ms: 5000
  success_rate: 0.995
```

### Override with Code (Optional)

```python
from agentic_core.graph_templates.base import BaseAgentGraph

@agent_persona("support-agent")
class SupportGraph(BaseAgentGraph):
    def build_graph(self):
        # Custom LangGraph logic -- overrides YAML graph_template
        ...
```

### Start the Runtime

```python
from agentic_core.config.settings import AgenticSettings
from agentic_core.runtime import AgentRuntime

settings = AgenticSettings(
    redis_url="redis://localhost:6379",
    postgres_dsn="postgresql://localhost:5432/agentic",
    falkordb_url="redis://localhost:6380",
)

runtime = AgentRuntime(settings)
await runtime.start()  # WebSocket :8765 + gRPC :50051
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
Full autonomous dev cycles?       -> orchestrator (GSD + Superpowers + Auto Research)
```

## Deployment Modes

| Mode | Binding | Use Case |
|------|---------|----------|
| **Standalone** | `0.0.0.0` | Own Deployment, scales independently |
| **Sidecar** | `127.0.0.1` | Same Pod as backend (NestJS, Serverpod) |

Set via `AGENTIC_MODE=standalone|sidecar`. Helm chart supports both.

## Observability Stack

```
agentic-core -> OpenTelemetry Collector -> Tempo (traces) + Prometheus (metrics)
             -> structlog (JSON) -> Grafana Alloy -> Loki (logs)
             -> Langfuse SDK -> Langfuse (LLM cost tracking)
             -> Alertmanager (SLO breach alerts)

All signals correlated via trace_id. 7 pre-built Grafana dashboards included.
```

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Core + Transport + Runtime | In Progress | Shared kernel, domain, ports, WebSocket, gRPC, config |
| Phase 2: Memory + RAG + LangGraph | Planned | Redis, PG, pgvector, FalkorDB adapters, graph templates |
| Phase 3: Observability + SRE | Planned | OTel, Langfuse, SLO tracking, chaos hooks, meta-orchestration |
| Phase 4: Security + Deployment | Planned | Auth, rate limit, PII, Helm, ArgoCD, Terraform, docs |

## Contributing

This is an open-source MIT project. See [GitHub Issues](https://github.com/lapc506/agentic-core/issues) for current tasks.

```bash
git clone https://github.com/lapc506/agentic-core.git
cd agentic-core
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

## License

MIT
