# Standalone Agent Studio — Design Spec

**Date:** 2026-04-08
**Status:** Approved
**Author:** Andrés Peña + Claude

## Overview

A self-contained standalone mode for agentic-core that runs with Docker/Podman without requiring a Kubernetes cluster. Provides a Flutter Web UI ("Agent Studio") for configuring agents, testing conversations, and monitoring metrics — targeted at client demos.

### Goals

- **Zero-config demo:** `docker compose up` → open `localhost:8765`
- **Agent Studio UI:** Non-technical users configure agents visually (personality, gates, business rules)
- **Developer Settings:** Terminal debug, connection status, environment configuration
- **Self-contained:** Single port, no external dependencies beyond the compose stack

### Non-Goals

- Production-scale observability (Alloy/Grafana/Prometheus — use staging for that)
- Multi-tenant auth
- Kubernetes deployment (already exists separately)
- Hot reload in Docker (single developer; use `flutter run -d chrome` for UI iteration)

---

## 1. Architecture

### Container Architecture (Approach C: Self-Contained)

agentic-core serves Flutter Web static files, REST API, and WebSocket from a single process. Minimal coupling (~5 lines of static file serving, reversible to Nginx proxy in 15 minutes).

```
docker-compose.yml (docker compose up → localhost:8765)
│
├── agentic-core (Python 3.12, distroless)
│   ├── /              → Flutter Web UI (static files from /app/web)
│   ├── /ws            → WebSocket (chat, streaming, HITL)
│   ├── /api/*         → REST endpoints (CRUD agents, gates, metrics, config)
│   ├── :50051         → gRPC (internal, future sidecar)
│   └── :9090          → Prometheus metrics endpoint (internal)
│
├── redis:7-alpine
│   └── Sessions, memory store, pub/sub
│
├── postgresql:16 + pgvector
│   └── Agent persistence, sessions, embeddings
│
└── falkordb:latest
    └── Graph store (entity relationships)
```

### What Exists vs What's New

| Component | Status | Notes |
|---|---|---|
| Dockerfile multi-stage | Exists | Add Flutter Web build stage |
| docker-compose.test.yaml | Exists | Extend to full `docker-compose.yml` |
| WebSocket transport | Exists | HandleMessage, streaming, HITL |
| gRPC transport | Exists | For sidecar mode |
| REST API adapter | **New** | CRUD Personas, Gates, metrics, health |
| Static file serving | **New** | ~5 lines in runtime, serves `/app/web` |
| Flutter Web app | **New** | Agent Studio UI |

### Data Flow

```
Client (browser)
    │
    ├── HTTP GET /           → Flutter Web UI (static)
    ├── HTTP REST /api/*     → CRUD agents, gates, config, metrics
    └── WebSocket /ws        → Chat streaming, HITL
          │
          ├── PersonaRegistry → loads agents
          ├── Graph (LangGraph) → executes react/plan-exec
          ├── Gates pipeline → PII → Tone → Compliance
          └── Tools (MCP) → rimm-classifier, etc.
```

---

## 2. Integration Modes: Standalone vs Sidecar

agentic-core supports two deployment modes. The API protocol changes depending on context:

```
                          agentic-core
                             :50051 gRPC
                                │
        ┌──────────────┬────────┼────────┬─────────────┐
        │              │        │        │             │
    aduanext       altrupets  vertivo  habitanexus  standalone
    gRPC native    NestJS     Serverpod WebSocket   REST API
    (same          translates adapter   direct to   (for demo
     protocol)     to GraphQL gRPC→RPC  Flutter app  Flutter UI)
                   in gateway
```

### Standalone Mode (this spec)

- **REST API** for CRUD operations (request-response pattern)
- **WebSocket** for chat (streaming pattern, already exists)
- **Static file serving** for Flutter Web UI
- Target: client demos, local development testing

### Sidecar Mode (existing)

- **gRPC** for backend-to-backend communication
- Each host backend translates to its own frontend protocol:
  - aduanext: gRPC native (same protocol)
  - altrupets: NestJS gateway translates gRPC → GraphQL (Apollo)
  - vertivolatam: Serverpod adapter wraps gRPC → Serverpod RPC
  - habitanexus: No backend — agentic-core IS the backend (WebSocket direct)
- Target: production deployments in Kubernetes

### Why Not GraphQL in agentic-core?

agentic-core stays protocol-agnostic at the core. gRPC is the sidecar lingua franca. Each backend exposes the API style its frontend prefers. Adding GraphQL to agentic-core would couple it to a specific frontend protocol, violating the hexagonal architecture.

---

## 3. Flutter Web UI

### Tech Stack

| Package | Purpose | License |
|---|---|---|
| `flutter` (web) | UI framework | BSD-3 |
| `go_router` | Navigation (same pattern as aduanext) | BSD-3 |
| `graphic` | Charts — Grammar of Graphics | MIT |
| `flutter_quill` + `markdown_quill` | WYSIWYG Markdown editor for Gates | MIT |
| `xterm` | Debug terminal (pure Dart) | MIT |
| `web_socket_channel` | WebSocket connection to agentic-core | BSD-3 |

All dependencies are compatible with BSL 1.1 (permissive licenses, no copyleft).

### Navigation Hierarchy (4 Levels)

```
Level 1 — Rail (persistent icons, 56px)
  💬 Chat (Home) │ 👤 Cliente │ 📐 Reglas │ 📋 Sesiones │ 🔧 Herramientas │ ⚙️ Sistema │ 📊 Métricas

Level 2 — Panel (contextual list, 210px)
  💬 → Recent conversations       👤 → Agent list         📐 → Business rules per agent
  📋 → Session history             🔧 → MCP Servers list   ⚙️ → Settings tabs
  📊 → Dashboard overview

Level 3 — Tabs (within content area)
  Agent Editor: Inputs │ Guardrails │ Outputs
  Settings: Conexiones │ Modelos │ Variables │ Debug │ Docker

Level 4 — Cards (within each tab)
  Inputs: Personalidad, Modelo & Template, Herramientas asignadas
  Guardrails: Cantidad de Gates (expandable WYSIWYG), Restricciones
  Outputs: Formato de respuesta, Canales de salida
```

### Screens

| Route | Screen | Description |
|---|---|---|
| `/` | ChatPage (Home) | Chat with agent selector in top bar, conversation history in panel |
| `/agents/:id` | AgentEditorPage | Tabs (Inputs/Guardrails/Outputs) with card-based forms |
| `/rules/:id` | RulesEditorPage | Business rules editor per agent |
| `/sessions` | SessionsPage | Session history + HITL escalations |
| `/sessions/:id` | SessionDetailPage | Conversation replay + metrics |
| `/tools` | ToolsPage | MCP servers + Skills, health status |
| `/settings` | SettingsPage | Tabs: Conexiones, Modelos, Variables, Debug (xterm), Docker |
| `/metrics` | MetricsPage | Charts dashboard (graphic) |

### Gates Editor

Each gate is a collapsible card with vertical flip animation:

- **Collapsed:** Header showing gate number (color-coded), name, status, drag handle
- **Expanded:** Full WYSIWYG Markdown editor (`flutter_quill`) with:
  - Toolbar: Bold, Italic, H1, H2, Lists, Code, Links, MD↔Preview toggle
  - Editor content area (Markdown rendered as rich text)
  - Footer: Action type selector (Bloqueante / Warning / Rewrite / HITL)
- **Interaction:** Click header to toggle, drag handle (⠿) to reorder, +/- counter for gate count
- **Pipeline visualization:** Arrow (↓) between gates showing flow order

### Debug Terminal

In Settings → Debug tab:
- `xterm` (Dart pure) terminal widget
- Container selector dropdown (agentic-core, redis, postgres, falkordb)
- Log level filters (ALL, INFO, WARN, ERROR, DEBUG)
- Search in logs
- Controls: Clear, Split view, Fullscreen

### Charts (Metrics Dashboard)

Using `graphic` (Grammar of Graphics) for composable visualizations:
- Latency over time (LineMark — p50/p95/p99)
- Token usage per agent (IntervalMark — stacked bars)
- Gate pass/fail rates (IntervalMark + Proportion — funnel or stacked percentage)
- Session counts per period (IntervalMark)
- Future: treemap by model cost, radar chart for SLO compliance

### Theme

Reuses AduaNext dark theme pattern with Material 3:

```
Surfaces:  Rail #080810, Panel #0F0F1E, Content #12121E, Card #1A1A2E, Border #2A2A40
Primary:   #3B6FE0, Light #6B9FFF
Text:      Primary #E0E0F0, Secondary #666680
Status:    Green #4CAF50, Yellow #FF9800, Red #EF5350, Blue #3B6FE0
Font:      Ubuntu (Google Fonts)
Material 3: enabled
```

### Atomic Design Components

| Level | Components |
|---|---|
| **Atoms** | StatusBadge, GateBadge (semaphore colors), CounterButton (+/−), ToolHealthDot, ChartCard |
| **Molecules** | AgentListItem, ConversationItem, GateHeader (collapsed), ToolChip, MetricKpi |
| **Organisms** | SidebarRail, SidebarPanel, GateEditor (WYSIWYG expandable), ChatMessageList, DebugTerminal, MetricsDashboard |
| **Templates** | DashboardLayout (rail+panel+content), ChatLayout, AgentEditorLayout |
| **Pages** | ChatPage, AgentEditorPage, SessionDetailPage, ToolsPage, SettingsPage, MetricsPage |

---

## 4. Docker / Deployment

### docker-compose.yml

```yaml
services:
  agentic-core:
    build: .
    ports:
      - "8765:8765"
    environment:
      AGENTIC_MODE: standalone
      AGENTIC_REDIS_URL: redis://redis:6379
      AGENTIC_POSTGRES_DSN: postgresql://agentic:agentic@postgres:5432/agentic
      AGENTIC_FALKORDB_URL: redis://falkordb:6380
    depends_on:
      redis:    { condition: service_healthy }
      postgres: { condition: service_healthy }
      falkordb: { condition: service_healthy }

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 3

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: agentic
      POSTGRES_PASSWORD: agentic
      POSTGRES_DB: agentic
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agentic"]
      interval: 5s
      retries: 3

  falkordb:
    image: falkordb/falkordb:latest
    healthcheck:
      test: ["CMD", "redis-cli", "-p", "6380", "ping"]
      interval: 5s
      retries: 3
```

### Dockerfile (multi-stage)

```dockerfile
# Stage 1: Flutter Web build
FROM ghcr.io/cirruslabs/flutter:stable AS flutter-build
WORKDIR /app
COPY ui/ .
RUN flutter build web --release

# Stage 2: Python dependencies
FROM python:3.12-slim AS python-build
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ src/

# Stage 3: Final (distroless)
FROM gcr.io/distroless/python3-debian12
COPY --from=python-build /app /app
COPY --from=flutter-build /app/build/web /app/web
WORKDIR /app
EXPOSE 8765
CMD ["python", "-m", "agentic_core.runtime"]
```

### Client Experience

```bash
git clone https://github.com/lapc506/agentic-core.git
cd agentic-core
docker compose up    # or: podman compose up
# → Open http://localhost:8765
```

### Podman Compatibility

Docker Compose and Podman Compose use the same `docker-compose.yml`. Podman runs rootless by default — no changes needed.

---

## 5. REST API

New driving adapter following existing hexagonal architecture. Only for standalone mode — sidecar mode uses gRPC.

### Endpoints

```
# Agents (Personas)
GET    /api/agents                    → List agents
POST   /api/agents                    → Create agent
GET    /api/agents/:id                → Agent detail
PUT    /api/agents/:id                → Update agent
DELETE /api/agents/:id                → Delete agent

# Gates (per agent)
GET    /api/agents/:id/gates          → List gates for agent
PUT    /api/agents/:id/gates          → Update gates (order + MD content)
PUT    /api/agents/:id/gates/:gateId  → Update individual gate

# Sessions
GET    /api/sessions                  → List sessions (paginated)
GET    /api/sessions/:id              → Session detail + messages

# Tools
GET    /api/tools                     → MCP servers + health status
GET    /api/tools/:name/health        → Individual health check

# Metrics (for graphic charts)
GET    /api/metrics/latency           → Latency p50/p95/p99 by window
GET    /api/metrics/tokens            → Token usage by agent/period
GET    /api/metrics/gates             → Pass/fail rate by gate
GET    /api/metrics/sessions          → Session count by period

# System
GET    /api/health                    → General health check
GET    /api/config                    → Current config (no secrets)
```

### Architecture Placement

```
src/agentic_core/
├── adapters/
│   ├── driving/
│   │   ├── websocket_transport.py    ← Exists
│   │   ├── grpc_transport.py         ← Exists
│   │   └── rest_api.py               ← NEW (aiohttp routes)
│   └── driven/                       ← No changes
├── application/
│   ├── commands/
│   │   ├── handle_message.py         ← Exists
│   │   ├── create_agent.py           ← NEW
│   │   ├── update_agent.py           ← NEW
│   │   └── update_gates.py           ← NEW
│   └── queries/
│       ├── get_session.py            ← Exists
│       ├── list_agents.py            ← NEW
│       ├── get_metrics.py            ← NEW
│       └── list_tools.py             ← NEW
└── domain/                           ← No changes
    └── Gate modeled as Value Object within Persona entity
```

### Domain Modeling: Gates as Value Objects

A Gate is an immutable Value Object within the Persona entity:
- `content: str` — Markdown body (guardrail rules)
- `action: GateAction` — enum: BLOCK | WARN | REWRITE | HITL
- `order: int` — position in the pipeline
- `name: str` — display name

No identity outside its parent Persona. Follows existing DDD patterns (like `AgentMessage` which is frozen/immutable).

---

## 6. Visual Mockups Reference

Interactive mockups created during brainstorming are preserved in:
```
.superpowers/brainstorm/*/content/
├── sidebar-sections.html          — Initial sidebar proposal
├── sidebar-v2-chat-home.html      — Chat as home + updated sidebar
├── navigation-flow.html           — Full 4-level navigation with interactive tabs
├── gates-terminal-update.html     — Gates WYSIWYG + terminal debug mockup
└── gates-flip-animation.html      — Interactive gates with flip animation + WYSIWYG
```
