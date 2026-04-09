# Diseno: docs-infrastructure

## Arquitectura

Documentacion estatica generada en dos formatos independientes: Zensical para el sitio publico y MyST para specs tecnicas internas. El Makefile orquesta ambos.

## Estructura del sitio Zensical

```
docs/
  introduction.md          — que es agentic-core
  quickstart.md            — instalacion y primer agente
  concepts/
    agents.md              — modelo de agentes
    tools.md               — integracion MCP
    memory.md              — sistema de memoria
    personas.md            — routing y personalidades
  guides/
    standalone.md          — modo standalone con Docker
    langchain.md           — integracion LangChain
    langgraph.md           — integracion LangGraph
  reference/
    api.md                 — REST API reference
    config.md              — configuracion YAML
    cli.md                 — comandos CLI
  changelog.md             — historial de versiones
```

## MyST Specs

Especificaciones tecnicas en `docs/specs/`:
- `architecture.md` — diagrama de capas y flujos principales
- `hooks.md` — lifecycle events y contratos de hooks
- `memory-protocol.md` — protocolo de extraccion y almacenamiento
- `a2a-protocol.md` — Agent-to-Agent task lifecycle

## Makefile targets

| Target | Descripcion |
|---|---|
| `make docs-site` | Build Zensical → `dist/docs/` |
| `make docs-specs` | Build MyST → `dist/specs/` |
| `make docs` | Ejecuta ambos |

## README sections

- Tabla comparativa: agentic-core vs ElizaOS vs OpenClaw vs Gemini CLI vs Claude Code
- Demo standalone: `docker compose up` en 3 pasos
- Badges: CI status, version, license

## OpenSpec

- `openspec/changes/` — ADRs por cambio arquitectonico
- `openspec/linear-setup.json` — configuracion de equipos y labels en Linear
