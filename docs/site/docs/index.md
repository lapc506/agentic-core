# Agent Studio

**Production-ready Python 3.12+ library for AI agent orchestration.**  
Deploy autonomous agents into your Kubernetes infrastructure as a sidecar or as a fully self-contained standalone service.

---

## What is Agent Studio?

Agent Studio is the shared runtime that powers AI agents across multiple applications. It is a **zero-business-logic library**: all domain-specific graphs live inside each project's own monorepo, while Agent Studio provides the transport, memory, orchestration, and observability infrastructure.

Built on [Explicit Architecture](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/) (Hexagonal + DDD + CQRS), every arrow points inward. Infrastructure always depends on domain-defined ports, never the reverse.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Hybrid Transport** | WebSocket (streaming, ElevenLabs voice) + gRPC (backend-to-sidecar) |
| **LangGraph Orchestration** | Pluggable graph templates: ReAct, Plan-and-Execute, Reflexion, LLM-Compiler, Supervisor, Orchestrator |
| **Unified Memory** | Redis + PostgreSQL + pgvector + FalkorDB working together |
| **MCP Bridge** | Discover and call tools from MCP servers with phantom-tool prevention |
| **Multimodal RAG** | Gemini Embedding 2 — text, image, audio, video, PDF in one vector space |
| **Meta-Orchestration** | GSD Sequencer, Superpowers Flow, Auto Research Loop for self-improving agents |
| **Hybrid Personas** | YAML config (PM-editable) + Python class (engineer override) |
| **Model Cascading** | Runtime → Persona → Sub-agent inheritance with per-level override |
| **SRE Observability** | OpenTelemetry + Prometheus + Loki + Tempo + Grafana + Langfuse + Alertmanager |
| **Kubernetes-Native** | Standalone or sidecar deployment via a single Helm chart |

---

## Quick Start

```bash
git clone https://github.com/lapc506/agentic-core.git
cd agentic-core
make up
```

Open **http://localhost:8765** — the Agent Studio UI loads with:

- Chat page with agent selector and live WebSocket streaming
- Agent editor (Inputs / Guardrails / Outputs tabs + gate configuration)
- Sessions history, Tools health monitor, Settings, and Metrics dashboard

See [Getting Started](getting-started.md) for full prerequisites and step-by-step setup.

---

## Install as a Library

```bash
pip install agentic-core
```

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

---

## Project Status

| Phase | Status |
|-------|--------|
| Phase 1: Core + Transport + Runtime | In Progress |
| Phase 2: Memory + RAG + LangGraph | Planned |
| Phase 3: Observability + SRE + Meta-Orchestration | Planned |
| Phase 4: Security + Deployment + Docs | Planned |

Full technical specification: [docs/superpowers/specs](https://github.com/lapc506/agentic-core/tree/main/docs/superpowers/specs)

---

## License

MIT — open-source, contributions welcome.  
See [GitHub Issues](https://github.com/lapc506/agentic-core/issues) for current tasks.
