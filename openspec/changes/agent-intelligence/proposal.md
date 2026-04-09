# Cambio: agent-intelligence

**Change ID:** agent-intelligence
**Fecha:** 2026-04-09

## Que
Servicios de inteligencia para agentes: memoria (semantica, procedural, graph, dual-layer), hook pipeline, evaluadores, LLM judge, routing, seguridad, presupuesto de iteracion.

## Por que
- Agentes sin memoria son stateless — no aprenden
- Sin hooks, cross-cutting concerns (auth, audit, safety) se duplican en cada tool
- Sin evaluadores, no hay garantia de calidad en respuestas
- Patrones adoptados de ElizaOS (character files, evaluators) y OpenClaw (hooks, memory, security)

## Alcance
### Incluido
- Hook pipeline (6 lifecycle events)
- Memory extraction (heuristic + dedup)
- Procedural memory (skill self-creation, refinement cada 15 tasks)
- Graph memory (entity/relationship extraction)
- Dual-layer memory manager (hot/cold, async writes)
- Persona routing (channel + keyword + explicit)
- Graph graceful degradation (FalkorDB → pgvector)
- MCP OAuth 2.1 + server discovery
- HTN Planner, Trajectory scoring, Progressive deployment gates
- Security auditor, Iteration budget + stuck detection
- HITL confirmation service
- Tool-owned views registry
- Coding agent primitives (read/edit/search/bash)
- Tool cache (TTL, dedup)
- Context window budget manager

## Etiquetas
- Tipo: feature
- Tamano: XL
- Prioridad: alta
