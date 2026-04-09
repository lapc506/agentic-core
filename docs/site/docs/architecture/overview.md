# Architecture Overview

Agent Studio is built on [Explicit Architecture](https://herbertograca.com/2017/11/16/explicit-architecture-01-ddd-hexagonal-onion-clean-cqrs-how-i-put-it-all-together/), combining Hexagonal Architecture, Domain-Driven Design (DDD), and CQRS. Every dependency arrow points inward: infrastructure depends on domain-defined ports, never the reverse.

---

## Layers

### Domain Layer (innermost)

Pure Python with zero external dependencies. Contains:

- **Entities**: `Session`, `Persona`, `Skill`, `Roadmap`
- **Value Objects**: `AgentMessage`, `Checkpoint`, `SLOTarget`, `EvalResult`
- **Domain Events**: `MessageProcessed`, `SessionCreated`, `SLOBreached`, `SkillOptimized`, `ToolDegraded`, `HumanEscalationRequested`, `ErrorBudgetExhausted`
- **Domain Services**: `RoutingService`, `EscalationService`, `EvalScoring`

The domain layer defines **port interfaces** (abstract base classes) that the infrastructure layer must implement.

---

### Application Layer

Orchestrates domain objects and ports. Contains:

- **Commands**: `HandleMessage`, `CreateSession`, `ResumeHITL`, `ExecuteRoadmap`, `OptimizeSkill`
- **Queries**: `GetSession`, `ListPersonas`, `GetSLOStatus`
- **Middleware**: Tracing, Auth, RateLimit, PII, Metrics — applied as a chain before commands
- **Services**: `GSDSequencer`, `SuperpowersFlow`, `AutoResearchLoop`

---

### Primary Adapters (Driving Side)

Receive input and translate it into application commands:

- **WebSocket Adapter** — Flutter UI, TUI, Ollama-compatible clients
- **gRPC Adapter** — NestJS, Serverpod, and other backend-to-sidecar calls
- **REST Adapter** — HTTP API for the standalone demo UI

---

### Secondary Adapters (Driven Side)

Implement domain ports using real infrastructure:

| Port | Adapter |
|------|---------|
| `MemoryPort` | Redis |
| `SessionPort` | PostgreSQL |
| `EmbeddingPort` | pgvector + Gemini Embedding |
| `GraphStorePort` | FalkorDB |
| `ToolPort` | MCP Bridge |
| `TracingPort` | OpenTelemetry |
| `MetricsPort` | Prometheus |
| `CostTrackingPort` | Langfuse |
| `GraphOrchestrationPort` | LangGraph |
| `AlertPort` | Alertmanager |

---

## CQRS Split

Write operations (commands) and read operations (queries) flow through separate handlers. Commands publish domain events; events fan out to subscribers via an in-process `EventBus`.

```
Primary Adapters
    ├── Write path → Commands → Domain → Secondary Adapters
    │                        └── Domain Events → EventBus → Subscribers
    └── Read path  → Queries → Secondary Adapters (read models)
```

---

## Message Flow (Request Lifecycle)

A WebSocket message from the Flutter client goes through:

1. **WebSocket Adapter** — parse and validate as `AgentMessage` (Pydantic)
2. **Middleware Chain** — Tracing → Auth → RateLimit → PII → Metrics
3. **HandleMessage Handler** — store in Redis, route to `AgentKernel`
4. **AgentKernel** — resolve persona, invoke `GraphOrchestrationPort`
5. **LangGraph** — execute agent graph nodes, call tools via `ToolPort`
6. **Streaming back** — each LLM token flows back up as `stream_token`
7. **PII redaction** — applied on the output side of the middleware chain
8. **Domain Event** — `MessageProcessed` published to `EventBus`

---

## Meta-Orchestration

Three high-level services sit above the standard request/response cycle:

### GSD Sequencer
Spec-driven task execution. Breaks a roadmap into phases, executes tasks sequentially with verification gates, and passes only phase summaries (not full context) forward — preventing context window bloat across long development cycles.

### SuperpowersFlow
Full engineering cycle: terrain mapping → gap research → approach brainstorming → HITL approval → spec generation → roadmap creation → HITL approval → GSD execution.

### Auto Research Loop
Skill self-improvement via batch execution, binary-rule evaluation, and instruction mutation. Runs until score improves or a perfect score is reached.

---

## Tool Health & Phantom Tool Prevention

Tools are registered through `MCPBridge` at startup. Before a tool is added to the LLM's context, it must pass a health check. Tools that fail the check are excluded — the LLM never sees them. If a registered tool degrades during runtime, it is deregistered and a `ToolDegraded` event is published. The LLM's tool list is updated before the next request.

This prevents the common failure mode where an LLM hallucinates successful tool calls because the tool was visible but broken.

---

## Multi-Agent Coordination Layer

When multiple agents work in parallel on the same repository, the **Lane Orchestrator** manages coordination:

### Lane Orchestrator
A state machine that assigns agents to isolated branches ("lanes"), manages branch locks to prevent collision, and coordinates merge back to main. States: idle -> booting -> running -> validating -> merging -> complete, with recovery transitions at each stage.

### Green Contracts
Graduated CI gates that each lane must pass before merge: lint/format -> unit tests -> integration tests -> e2e tests. Each gate must pass before the next runs. A failed gate blocks merge and triggers the recovery engine.

### Recovery Engine
Handles 7 common failure scenarios (merge conflicts, flaky tests, worker timeout, dependency failures, lock contention, CI unavailability, schema errors) with a 1-auto-retry-then-escalate policy. Simple conflicts are auto-resolved via rebase; complex failures escalate to a human or supervisor agent.

### Task Packet Validation
Structured work contracts validated against a JSON Schema before assignment to workers. Each packet specifies the task scope, dependencies, expected outputs, and acceptance criteria.

### Branch Management
Stale branch detection uses an age + activity heuristic to identify abandoned branches. Auto-rebase policy keeps active branches aligned with main, offering cleanup for truly stale work.
