# agentic-core

Production-ready Python 3.12+ library for AI agent orchestration. Designed as a shared dependency for any startup integrating autonomous agents into their Kubernetes infrastructure via sidecar injection or standalone deployment.

**This library contains NO domain-specific graphs or business logic.** All graphs live inside each project's own monorepo.

## Architecture

Built on [Explicit Architecture](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/) (Hexagonal + DDD + CQRS). All arrows point inward. Infrastructure depends on domain-defined ports, never the reverse.

### Layered Architecture

```mermaid
graph TB
    subgraph PRIMARY["PRIMARY ADAPTERS (Driving)"]
        WS["WebSocket Adapter"]
        GRPC["gRPC Adapter"]
        CLI["CLI Adapter (future)"]
    end

    subgraph APP["APPLICATION LAYER"]
        direction TB
        CMD["Commands: HandleMessage, CreateSession,<br/>ResumeHITL, ExecuteRoadmap, OptimizeSkill"]
        QRY["Queries: GetSession, ListPersonas, GetSLOStatus"]
        PORTS["Ports: MemoryPort, SessionPort, EmbeddingPort,<br/>GraphStorePort, ToolPort, TracingPort,<br/>MetricsPort, CostTrackingPort, GraphOrchestrationPort, AlertPort"]
        MW["Middleware: Tracing, Auth, RateLimit, PII, Metrics"]
        SVC["Services: GSDSequencer, SuperpowersFlow, AutoResearchLoop"]
    end

    subgraph DOMAIN["DOMAIN LAYER (pure, zero dependencies)"]
        ENT["Entities: Session, Persona, Skill, Roadmap"]
        VO["Value Objects: AgentMessage, Checkpoint, SLOTarget, EvalResult"]
        EVT["Domain Events: MessageProcessed, SessionCreated,<br/>SLOBreached, SkillOptimized, ToolDegraded,<br/>HumanEscalationRequested, ErrorBudgetExhausted"]
        DSVC["Domain Services: RoutingService, EscalationService, EvalScoring"]
    end

    subgraph SECONDARY["SECONDARY ADAPTERS (Driven)"]
        REDIS["Redis"]
        PG["PostgreSQL"]
        PGV["pgvector"]
        FDB["FalkorDB"]
        LFUSE["Langfuse"]
        OTEL["OpenTelemetry"]
        MCP["MCP Bridge"]
        LG["LangGraph"]
    end

    WS & GRPC & CLI -->|"calls Ports"| APP
    APP -->|"uses"| DOMAIN
    APP -.->|"depends on Port interfaces<br/>(dependency inversion)"| SECONDARY

    style PRIMARY fill:#4A90D9,color:#fff
    style APP fill:#7B68EE,color:#fff
    style DOMAIN fill:#2ECC71,color:#fff
    style SECONDARY fill:#E67E22,color:#fff
```

### Hexagonal Ports & Adapters

```mermaid
graph LR
    subgraph DRIVING["Driving Side (Primary)"]
        Flutter["Flutter Client<br/>(WebSocket)"]
        NestJS["NestJS / Serverpod<br/>(gRPC)"]
    end

    subgraph CORE["Application Core"]
        direction TB
        P_IN["Inbound Ports"]
        HANDLERS["Command & Query Handlers"]
        MIDDLEWARE["Middleware Chain"]
        P_OUT["Outbound Ports"]
    end

    subgraph DRIVEN["Driven Side (Secondary)"]
        Redis["Redis"]
        Postgres["PostgreSQL + pgvector"]
        FalkorDB["FalkorDB"]
        MCPServers["MCP Servers"]
        OTel["OpenTelemetry"]
        Langfuse["Langfuse"]
        LangGraph["LangGraph"]
    end

    Flutter -->|WebSocket| P_IN
    NestJS -->|gRPC| P_IN
    P_IN --> MIDDLEWARE --> HANDLERS
    HANDLERS --> P_OUT
    P_OUT -->|MemoryPort| Redis
    P_OUT -->|SessionPort + EmbeddingPort| Postgres
    P_OUT -->|GraphStorePort| FalkorDB
    P_OUT -->|ToolPort| MCPServers
    P_OUT -->|TracingPort + MetricsPort| OTel
    P_OUT -->|CostTrackingPort| Langfuse
    P_OUT -->|GraphOrchestrationPort| LangGraph

    style CORE fill:#2ECC71,color:#fff
    style DRIVING fill:#4A90D9,color:#fff
    style DRIVEN fill:#E67E22,color:#fff
```

### Message Flow (Request Lifecycle)

```mermaid
sequenceDiagram
    participant Client as Flutter Client
    participant WS as WebSocket Adapter
    participant MW as Middleware Chain
    participant CMD as HandleMessageHandler
    participant Kernel as AgentKernel
    participant Graph as LangGraph
    participant Tool as MCP Tool
    participant Mem as Redis (MemoryPort)

    Client->>WS: {"type": "message", "content": "..."}
    WS->>WS: Construct & validate AgentMessage (Pydantic)
    WS->>MW: AgentMessage

    Note over MW: Tracing -> Auth -> RateLimit -> PII -> Metrics

    MW->>CMD: Validated AgentMessage
    CMD->>Mem: store_message()
    CMD->>Kernel: route(persona_id)
    Kernel->>Graph: astream_events(input, thread_id)

    loop Graph Execution
        Graph->>Tool: execute("mcp_zendesk_create_ticket", args)
        Tool-->>Graph: ToolResult
    end

    Graph-->>CMD: StreamEvent (token)
    CMD-->>MW: AgentMessage (stream_token)
    MW-->>WS: Apply PII redaction on output
    WS-->>Client: {"type": "stream_token", "token": "..."}

    Note over CMD: publish(MessageProcessed) -> EventBus
```

### CQRS: Commands vs Queries

```mermaid
graph LR
    subgraph Commands["Commands (Write Side)"]
        C1["HandleMessage"]
        C2["CreateSession"]
        C3["ResumeHITL"]
        C4["ExecuteRoadmap"]
        C5["OptimizeSkill"]
    end

    subgraph Queries["Queries (Read Side)"]
        Q1["GetSession"]
        Q2["ListPersonas"]
        Q3["GetSLOStatus"]
    end

    subgraph Events["Domain Events"]
        E1["MessageProcessed"]
        E2["SessionCreated"]
        E3["SLOBreached"]
        E4["ToolDegraded"]
    end

    PA["Primary Adapters<br/>(WebSocket / gRPC)"]

    PA -->|"write operations"| Commands
    PA -->|"read operations"| Queries
    Commands -->|"publish"| Events
    Events -->|"notify"| HANDLERS["Event Handlers<br/>(via EventBus)"]

    style Commands fill:#E74C3C,color:#fff
    style Queries fill:#3498DB,color:#fff
    style Events fill:#F39C12,color:#fff
```

## Key Features

- **Hybrid Transport** -- WebSocket (bidirectional, streaming, ElevenLabs voice) + gRPC (backend-to-sidecar)
- **LangGraph Orchestration** -- Pluggable graph templates: ReAct, Plan-and-Execute, Reflexion, LLM-Compiler, Supervisor, Orchestrator
- **Unified Memory** -- Redis + PostgreSQL + pgvector + FalkorDB (all required)
- **MCP Bridge** -- Discover and execute tools from MCP servers with phantom tool prevention
- **Multimodal RAG** -- Gemini Embedding 2 (text + image + audio + video + PDF in one vector space) with Matryoshka dimension control
- **Meta-Orchestration** -- GSD Sequencer, Superpowers Flow, Auto Research Loop for self-improving agents
- **Hybrid Persona System** -- YAML config (PM-editable) + Python code (engineer override)
- **LLM Model Cascading** -- Runtime -> Persona -> Sub-agent inheritance with per-level override
- **Full SRE Observability** -- OpenTelemetry + Prometheus + Loki + Tempo + Grafana + Langfuse + Alertmanager
- **Kubernetes-Native** -- Dual deployment: standalone or sidecar, single Helm chart

## Meta-Orchestration: GSD + Superpowers + Auto Research

Three pillars for autonomous agent development cycles:

```mermaid
graph TB
    subgraph SUPERPOWERS["SuperpowersFlow (Full Engineering Cycle)"]
        direction TB
        SP1["Map Terrain<br/><i>analyze codebase</i>"]
        SP2["Research Gaps<br/><i>security, UX, impl</i>"]
        SP3["Brainstorm 2-3<br/>Approaches"]
        SP4{{"HITL: User<br/>Chooses Approach"}}
        SP5["Generate Spec"]
        SP6["Create Roadmap"]
        SP7{{"HITL: User<br/>Approves Roadmap"}}
        SP1 --> SP2 --> SP3 --> SP4 --> SP5 --> SP6 --> SP7
    end

    subgraph GSD["GSD Sequencer (Spec-Driven Execution)"]
        direction TB
        G1["Phase 1: Task A"]
        G2["Verify A"]
        G3["Phase 1: Task B"]
        G4["Verify B"]
        G5["Gate: Phase 1 complete?"]
        G6["Phase 2: Task C<br/><i>(fresh context,<br/>only summary of A+B)</i>"]
        G1 --> G2 --> G3 --> G4 --> G5 -->|pass| G6
        G5 -->|fail| G1
    end

    subgraph AUTO["AutoResearch Loop (Skill Self-Improvement)"]
        direction TB
        A1["Batch Execute<br/>Skill x10"]
        A2["Evaluate with<br/>Binary Rules"]
        A3{"Score<br/>improved?"}
        A4["Mutate<br/>Instructions"]
        A5["Keep Best<br/>Version"]
        A1 --> A2 --> A3
        A3 -->|no| A4 --> A1
        A3 -->|yes| A5 --> A1
        A3 -->|perfect| DONE["Done"]
    end

    SP7 -->|"approved"| GSD
    GSD -->|"has skills to optimize"| AUTO

    style SUPERPOWERS fill:#8E44AD,color:#fff
    style GSD fill:#2980B9,color:#fff
    style AUTO fill:#27AE60,color:#fff
```

## Graph Template Decision Tree

```mermaid
graph TD
    START{"Does your agent<br/>use tools?"} -->|No| DIRECT["Direct LLM<br/><i>no graph needed</i>"]
    START -->|Yes| PLAN{"Needs to plan<br/>multiple steps<br/>before acting?"}
    PLAN -->|No| RE["react<br/><i>default, 80% of cases</i>"]
    PLAN -->|Yes| INDEP{"Are steps<br/>independent?"}
    INDEP -->|Yes| LLC["llm-compiler<br/><i>parallel execution</i>"]
    INDEP -->|No| PE["plan-and-execute"]

    QUALITY{"Output quality<br/>justifies retry loops?<br/><i>(orthogonal)</i>"} -->|Yes| REF["reflexion<br/><i>wraps any template above</i>"]

    MULTI{"Multiple personas<br/>that collaborate?"} -->|Yes| SUP["supervisor"]

    AUTONOMOUS{"Full autonomous<br/>dev cycles?"} -->|Yes| ORCH["orchestrator<br/><i>GSD + Superpowers<br/>+ Auto Research</i>"]

    style RE fill:#2ECC71,color:#fff
    style PE fill:#3498DB,color:#fff
    style LLC fill:#9B59B6,color:#fff
    style REF fill:#E67E22,color:#fff
    style SUP fill:#E74C3C,color:#fff
    style ORCH fill:#1ABC9C,color:#fff
    style DIRECT fill:#95A5A6,color:#fff
```

## Standalone Demo (Docker / Podman)

Run the full Agent Studio locally. Requires Flutter SDK and Docker/Podman:

```bash
git clone https://github.com/lapc506/agentic-core.git
cd agentic-core
make up       # builds Flutter Web + Docker image + starts all containers
```

Or step by step:

```bash
make build-web      # compiles Flutter Web UI (~30 sec)
make build-docker   # builds Python image (~60 sec, no Flutter SDK in Docker)
podman compose up   # starts 4 containers
```

Open **http://localhost:8765** — you'll see the Agent Studio with:
- Chat page (home) with agent selector and WebSocket streaming
- Agent editor with tabs (Inputs / Guardrails / Outputs) and gate configuration
- Sessions history, Tools health, Settings with debug terminal, Metrics dashboard

### What runs

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| agentic-core | `ghcr.io/lapc506/agentic-core` | 8765 (exposed) | Python runtime + Flutter Web UI + REST API + WebSocket |
| redis | `redis:7-alpine` | 6379 (internal) | Sessions, memory store |
| postgres | `pgvector/pgvector:pg16` | 5432 (internal) | Agent persistence, embeddings |
| falkordb | `falkordb/falkordb:latest` | 6380 (internal) | Graph store |

All services include healthchecks — agentic-core waits for dependencies before starting.

### Development workflow

For UI iteration without rebuilding the Docker image:

```bash
# Terminal 1: Backend + dependencies
docker compose up redis postgres falkordb
AGENTIC_MODE=standalone AGENTIC_REDIS_URL=redis://localhost:6379 \
  AGENTIC_POSTGRES_DSN=postgresql://agentic:agentic@localhost:5432/agentic \
  AGENTIC_FALKORDB_URL=redis://localhost:6380 \
  python -m agentic_core.runtime

# Terminal 2: Flutter Web (hot reload)
cd ui
flutter run -d chrome
```

Flutter connects to the backend at `localhost:8765` via WebSocket and REST API.

### REST API

The standalone mode exposes a REST API at `localhost:8765/api/`:

```bash
# Health check
curl http://localhost:8765/api/health

# List agents
curl http://localhost:8765/api/agents

# Create agent
curl -X POST http://localhost:8765/api/agents \
  -H 'Content-Type: application/json' \
  -d '{"name": "My Agent", "role": "assistant", "description": "Test agent"}'

# Update gates
curl -X PUT http://localhost:8765/api/agents/my-agent/gates \
  -H 'Content-Type: application/json' \
  -d '{"gates": [{"name": "PII Filter", "content": "Redact PII", "action": "block", "order": 0}]}'
```

Full endpoint list: `GET /api/health`, `GET/POST /api/agents`, `GET/PUT/DELETE /api/agents/:slug`, `GET/PUT /api/agents/:slug/gates`, `GET /api/metrics/:type`, `GET /api/config`.

### Integration modes

When agentic-core is deployed as a sidecar in Kubernetes, backends communicate via gRPC (`:50051`). Each backend translates to its own frontend protocol:

```mermaid
graph TB
    AC["agentic-core<br/>:50051 gRPC"]
    AD["aduanext<br/><i>gRPC native</i>"]
    AL["altrupets<br/><i>NestJS → GraphQL</i>"]
    VT["vertivolatam<br/><i>Serverpod adapter</i>"]
    HN["habitanexus<br/><i>WebSocket direct</i>"]
    SA["standalone<br/><i>REST API (demo UI)</i>"]

    AC --> AD
    AC --> AL
    AC --> VT
    AC --> HN
    AC --> SA

    style AC fill:#3B6FE0,color:#fff
    style SA fill:#4CAF50,color:#fff
```

The standalone REST API is only for the demo UI — sidecar mode uses gRPC exclusively.

---

## Quick Start (Library)

```bash
pip install agentic-core
```

### 1. Define a Persona (YAML)

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

### 2. Override with Code (Optional)

```python
from agentic_core.graph_templates.base import BaseAgentGraph

@agent_persona("support-agent")
class SupportGraph(BaseAgentGraph):
    def build_graph(self):
        # Custom LangGraph logic -- overrides YAML graph_template
        ...
```

### 3. Start the Runtime

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

### 4. Connect from Flutter

```dart
final channel = WebSocketChannel.connect(Uri.parse('ws://localhost:8765'));

// Create session
channel.sink.add(jsonEncode({
  'type': 'create_session',
  'persona_id': 'support-agent',
  'user_id': 'user_123',
}));

// Send message
channel.sink.add(jsonEncode({
  'type': 'message',
  'session_id': sessionId,
  'persona_id': 'support-agent',
  'content': 'I need help with my order',
}));

// Listen for streaming tokens
channel.stream.listen((data) {
  final msg = jsonDecode(data);
  switch (msg['type']) {
    case 'stream_token': print(msg['token']);
    case 'human_escalation': showEscalationDialog(msg['prompt']);
    case 'error': handleError(msg['code'], msg['message']);
  }
});
```

## LLM Model Cascading

Models inherit from Runtime -> Persona -> Sub-agent. Each level can override:

```mermaid
graph TB
    RUNTIME["Runtime Default<br/><b>AgenticSettings.default_model</b><br/><i>e.g., claude-sonnet-4-6</i>"]
    RUNTIME -->|"inherits if<br/>no override"| P1["Persona: support-agent<br/><i>inherits claude-sonnet-4-6</i>"]
    RUNTIME -->|"overrides"| P2["Persona: analyst-agent<br/><b>model_config:</b><br/><i>claude-opus-4-6</i>"]
    RUNTIME -->|"overrides"| P3["Persona: orchestrator<br/><b>model_config:</b><br/><i>gemini-2.5-pro</i>"]

    P2 -->|"inherits"| S1["Sub-agent: data-fetcher<br/><i>inherits claude-opus-4-6</i>"]
    P2 -->|"overrides"| S2["Sub-agent: summarizer<br/><b>model_config:</b><br/><i>claude-haiku-4-5</i><br/><i>(cheaper for summaries)</i>"]

    P3 -->|"overrides"| S3["Sub-agent: researcher<br/><b>model_config:</b><br/><i>claude-opus-4-6</i>"]
    P3 -->|"inherits"| S4["Sub-agent: spec-writer<br/><i>inherits gemini-2.5-pro</i>"]

    style RUNTIME fill:#E74C3C,color:#fff
    style P1 fill:#3498DB,color:#fff
    style P2 fill:#2980B9,color:#fff
    style P3 fill:#2980B9,color:#fff
    style S1 fill:#7FB3D8,color:#fff
    style S2 fill:#1ABC9C,color:#fff
    style S3 fill:#1ABC9C,color:#fff
    style S4 fill:#7FB3D8,color:#fff
```

## Deployment Modes

```mermaid
graph TB
    subgraph STANDALONE["Standalone Mode"]
        direction TB
        subgraph POD_S["Pod: agentic-core"]
            AC_S["agentic-core<br/>0.0.0.0:8765 (WS)<br/>0.0.0.0:50051 (gRPC)"]
        end
        subgraph POD_B["Pod: backend"]
            NEST_S["NestJS / Serverpod"]
        end
        NEST_S -->|"gRPC (service DNS)"| AC_S
        CLIENT_S["Flutter Client"] -->|"WebSocket (Ingress)"| AC_S
    end

    subgraph SIDECAR["Sidecar Mode"]
        direction TB
        subgraph POD_SC["Pod (shared network namespace)"]
            AC_SC["agentic-core<br/>127.0.0.1:8765 (WS)<br/>127.0.0.1:50051 (gRPC)"]
            NEST_SC["NestJS / Serverpod"]
            NEST_SC -->|"gRPC localhost"| AC_SC
        end
        CLIENT_SC["Flutter Client"] -->|"WebSocket (Ingress)"| AC_SC
    end

    style STANDALONE fill:#3498DB,color:#fff
    style SIDECAR fill:#E67E22,color:#fff
    style POD_SC fill:#D35400,color:#fff
```

Set via `AGENTIC_MODE=standalone|sidecar`. Helm chart supports both.

## Observability Stack

```mermaid
graph TB
    subgraph AGENTIC["agentic-core Process"]
        APP["Application Code"]
        OTEL_SDK["OpenTelemetry SDK"]
        STRUCTLOG["structlog (JSON)"]
        PROM_EXP["/metrics endpoint"]
        LANGFUSE_SDK["Langfuse SDK"]
        APP -->|"spans"| OTEL_SDK
        APP -->|"logs with trace_id"| STRUCTLOG
        APP -->|"token counts + cost"| LANGFUSE_SDK
        OTEL_SDK -->|"expose"| PROM_EXP
    end

    subgraph COLLECTOR["OpenTelemetry Collector"]
        RECV["Receivers<br/>OTLP (gRPC/HTTP)"]
        PROC["Processors<br/>batch, tail_sampling"]
        EXP["Exporters"]
    end

    subgraph STORAGE["Observability Backend"]
        PROM["Prometheus<br/><i>Metrics</i>"]
        TEMPO["Grafana Tempo<br/><i>Traces</i>"]
        LOKI["Grafana Loki<br/><i>Logs</i>"]
        AM["Alertmanager"]
        LANGFUSE["Langfuse<br/><i>LLM cost</i>"]
    end

    subgraph VIZ["Visualization"]
        GRAFANA["Grafana<br/>7 pre-built dashboards"]
    end

    OTEL_SDK -->|"OTLP :4317"| RECV
    STRUCTLOG -->|"stdout -> Alloy"| LOKI
    PROM_EXP -->|"scrape"| PROM
    LANGFUSE_SDK --> LANGFUSE
    RECV --> PROC --> EXP
    EXP -->|"traces"| TEMPO
    EXP -->|"metrics"| PROM
    PROM -->|"alerting rules"| AM
    PROM & TEMPO & LOKI --> GRAFANA
    LANGFUSE --> GRAFANA

    style AGENTIC fill:#2ECC71,color:#fff
    style COLLECTOR fill:#3498DB,color:#fff
    style STORAGE fill:#8E44AD,color:#fff
    style VIZ fill:#E67E22,color:#fff
```

All signals correlated via `trace_id` for seamless drill-down: metrics -> traces -> logs -> cost.

## Session State Machine

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : CreateSession
    ACTIVE --> PAUSED : explicit pause / connection drop
    ACTIVE --> ESCALATED : HITL node / escalation rule
    ACTIVE --> COMPLETED : graph finished / user ended
    PAUSED --> ACTIVE : resume (within TTL)
    PAUSED --> COMPLETED : TTL expired
    ESCALATED --> ACTIVE : human responded
    COMPLETED --> [*]
```

## Tool Health & Phantom Tool Prevention

Lesson learned: tools visible to the LLM but failing at runtime cause hallucinated responses.

```mermaid
stateDiagram-v2
    [*] --> Discovery : MCPBridge.start()
    Discovery --> Healthcheck : tool found
    Healthcheck --> Registered : healthcheck passed
    Healthcheck --> Excluded : healthcheck failed
    Excluded --> [*] : logged as warning, LLM never sees tool

    Registered --> Healthy : serving requests
    Healthy --> Degraded : execution failure / MCP disconnect
    Degraded --> Deregistered : deregister_tool() + ToolDegraded event
    Deregistered --> Healthcheck : MCP server reconnects
    Healthy --> Healthy : successful execution
```

## Competitive Comparison

How agentic-core compares to the leading AI agent frameworks:

| Capability | agentic-core | ElizaOS | OpenClaw | Hermes Agent |
|---|:---:|:---:|:---:|:---:|
| **Agent Orchestration** | | | | |
| LangGraph templates (ReAct, Plan-Execute, Reflexion, Supervisor) | :white_check_mark: | :x: | :x: | :x: |
| HTN hierarchical task planning | :white_check_mark: | :white_check_mark: | :x: | :x: |
| Multi-persona routing (channel + keyword) | :white_check_mark: | :x: | :white_check_mark: | :x: |
| A2A Protocol (agent-to-agent) | :white_check_mark: | :x: | :x: | :x: |
| Multi-agent lane orchestration (branch lock, collision detection) | :white_check_mark: | :x: | :x: | :x: |
| Green contracts (graduated CI gates) | :white_check_mark: | :x: | :x: | :x: |
| Recovery recipes (7 scenarios, auto-retry + escalate) | :white_check_mark: | :x: | :x: | :x: |
| Stale branch detection + auto-rebase | :white_check_mark: | :x: | :x: | :x: |
| Task packet validation (structured work contracts) | :white_check_mark: | :x: | :x: | :x: |
| **Memory** | | | | |
| Semantic memory (fact extraction + dedup) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Procedural memory (skill self-creation) | :white_check_mark: | :x: | :x: | :white_check_mark: |
| Graph memory (entities + relationships) | :white_check_mark: | :x: | :white_check_mark: | :x: |
| Dual-layer hot/cold (async writes) | :white_check_mark: | :x: | :x: | :white_check_mark: |
| **Safety & Guardrails** | | | | |
| Evaluators/Gates (post-response checks) | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |
| LLM Judge (observe/enforce modes) | :white_check_mark: | :x: | :white_check_mark: | :x: |
| Boundaries deny list (SOUL.md) | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |
| PII redaction middleware | :white_check_mark: | :x: | :white_check_mark: | :x: |
| Progressive deployment gates (dev/staging/prod) | :white_check_mark: | :x: | :x: | :x: |
| Security audit command | :white_check_mark: | :x: | :white_check_mark: | :x: |
| Iteration budget + stuck detection | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |
| **Evaluation** | | | | |
| Trajectory scoring (pass@k) | :white_check_mark: | :x: | :x: | :white_check_mark: |
| SLO tracking + error budgets | :white_check_mark: | :x: | :x: | :x: |
| **Tool Integration** | | | | |
| MCP Bridge (stdio + HTTP) | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |
| MCP OAuth 2.1 + server discovery | :white_check_mark: | :x: | :x: | :white_check_mark: |
| Phantom tool prevention | :white_check_mark: | :x: | :x: | :x: |
| **Multi-Provider LLM** | | | | |
| OpenRouter, Ollama, LMStudio, Fireworks, NVIDIA NIM | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Ollama-compatible API (be a provider) | :white_check_mark: | :x: | :white_check_mark: | :x: |
| Model cascading (runtime/persona/sub-agent) | :white_check_mark: | :x: | :x: | :white_check_mark: |
| **Lifecycle Hooks** | | | | |
| Event-based hook pipeline (6 events) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| **Interfaces** | | | | |
| Flutter Web UI (Agent Studio) | :white_check_mark: | :x: | :x: | :x: |
| Go TUI (Bubble Tea) | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |
| REST API | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: |
| WebSocket streaming | :white_check_mark: | :white_check_mark: | :white_check_mark: | :x: |
| gRPC (sidecar) | :white_check_mark: | :x: | :x: | :x: |
| **Deployment** | | | | |
| Docker standalone (`docker compose up`) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Kubernetes (Helm, sidecar injection) | :white_check_mark: | :x: | :x: | :x: |
| Graph DB graceful degradation | :white_check_mark: | :x: | :x: | :x: |
| **Configuration** | | | | |
| Visual agent editor (WYSIWYG gates) | :white_check_mark: | :x: | :x: | :x: |
| SOUL.md (agent personality file) | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Character files (bio, lore, style) | :white_check_mark: | :white_check_mark: | :x: | :x: |
| Onboarding wizard | :white_check_mark: | :x: | :white_check_mark: | :x: |
| **Documentation** | | | | |
| Zensical docs site | :white_check_mark: | :x: | :white_check_mark: | :x: |
| MyST technical specs | :white_check_mark: | :x: | :x: | :x: |
| OpenSpec change management | :white_check_mark: | :x: | :x: | :x: |

**Key differentiators:**
- Only framework with **visual agent editor** (Flutter Web UI with WYSIWYG gate editing)
- Only framework with **LangGraph integration** (6 graph templates, not just ReAct)
- Only framework with **A2A Protocol** for agent-to-agent interoperability
- Only framework with **Kubernetes-native sidecar deployment** alongside standalone Docker
- Only framework with both **Flutter Web UI and Go TUI** interfaces
- Only framework with **multi-agent lane orchestration** (branch lock, collision detection, green contracts, recovery recipes)

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Core + Transport + Runtime | **Complete** | Shared kernel, domain, ports, WebSocket, gRPC, HTTP API, config |
| Phase 2: Memory + Intelligence | **Complete** | Semantic, procedural, graph, dual-layer memory. HTN planning. Trajectory scoring |
| Phase 3: Safety + Ops | **Complete** | Evaluators, LLM Judge, PII, gates, security audit, iteration budget, MCP OAuth |
| Phase 4: Interfaces + Deployment | **Complete** | Flutter Web UI, Go TUI, Ollama API, A2A, Docker, Helm, Zensical docs |

## Full Spec

The complete design specification (1800+ lines, 13 Mermaid diagrams) is at [`docs/superpowers/specs/2026-03-25-agentic-core-phase1-design.md`](docs/superpowers/specs/2026-03-25-agentic-core-phase1-design.md).

## Documentation

- **Project docs**: `docs/site/` (Zensical) — guides, API reference, architecture
- **Technical specs**: `docs/specs/` (MyST) — design specifications, implementation plans

```bash
make docs       # Build both doc sites
make docs-site  # Zensical only
make docs-specs # MyST only
```

## Contributing

See [GitHub Issues](https://github.com/lapc506/agentic-core/issues) for current tasks.

```bash
git clone https://github.com/lapc506/agentic-core.git
cd agentic-core
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v  # 250+ tests passing
```

## License

BSL 1.1
