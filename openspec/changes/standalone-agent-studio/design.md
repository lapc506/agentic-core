# Diseno: standalone-agent-studio

**Spec completo:** `docs/superpowers/specs/2026-04-08-standalone-agent-studio-design.md`

## Arquitectura General

```
docker-compose.yml (docker compose up → localhost:8765)
│
├── agentic-core (Python 3.12, distroless)
│   ├── /              → Flutter Web UI (static files desde /app/web)
│   ├── /ws            → WebSocket (chat, streaming, HITL)
│   ├── /api/*         → REST endpoints (CRUD agentes, gates, metricas)
│   ├── :50051         → gRPC (interno, sidecar futuro)
│   └── :9090          → Metricas Prometheus (interno)
│
├── redis:7-alpine     → Sesiones, memory store
├── postgresql:16      → Persistencia, pgvector
└── falkordb:latest    → Graph store
```

## Enfoque: Self-Contained (Approach C)

agentic-core sirve Flutter Web + REST API + WebSocket desde un solo proceso.
Acoplamiento minimo (~5 lineas de static serving, reversible a Nginx en 15 min).

## Modos de Integracion

```
                      agentic-core
                         :50051 gRPC
                            │
    ┌──────────┬────────────┼────────────┬─────────────┐
    │          │            │            │             │
aduanext   altrupets    vertivo    habitanexus    standalone
gRPC       NestJS→GQL   Serverpod  WebSocket     REST API
nativo     gateway       adapter    directo       (demo UI)
```

- **Standalone:** REST para CRUD, WebSocket para chat, static para UI
- **Sidecar:** gRPC nativo — cada backend traduce a su protocolo

## Stack UI (Plan 2)

| Paquete | Proposito | Licencia |
|---|---|---|
| go_router | Navegacion | BSD-3 |
| graphic | Charts (Grammar of Graphics) | MIT |
| flutter_quill | Editor WYSIWYG Markdown | MIT |
| xterm | Terminal debug (Dart puro) | MIT |
| web_socket_channel | WebSocket | BSD-3 |

Todas compatibles con BSL 1.1.

## Dominio: Gate como Value Object

Gate es inmutable (Pydantic frozen=True) dentro de Persona:
- `name: str`, `content: str` (Markdown), `action: GateAction` (block|warn|rewrite|hitl), `order: int`
