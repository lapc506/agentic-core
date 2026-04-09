# Diseno: agent-intelligence

## Arquitectura

Todos los servicios siguen el patron de application services con inyeccion de dependencias via ports. Los hooks corren como middleware en el lifecycle del agente.

## Servicios implementados

| Servicio | Archivo | Tests | Patron |
|---|---|---|---|
| Hook Pipeline | application/hooks.py | 18 | Event-based, modifying + void |
| Memory Extraction | services/memory_extraction.py | 20 | Heuristic, bilingual |
| Procedural Memory | services/skill_creation.py | 32 | YAML persistence, refinement |
| Memory Manager | services/memory_manager.py | 40 | Dual-layer, entity extraction |
| Persona Router | services/persona_router.py | 20 | Channel + keyword + explicit |
| Graph Service | services/graph_service.py | 21 | FalkorDB → pgvector fallback |
| MCP Auth | adapters/secondary/mcp_auth.py | 37 | OAuth 2.1 PKCE |
| HTN Planner | graph_templates/htn_planner.py | 5 | TaskNode trees |
| Trajectory Evaluator | domain/services/trajectory_evaluator.py | 5 | pass@k scoring |
| Deployment Gates | services/deployment_gates.py | 5 | Progressive thresholds |
| Security Auditor | services/security_auditor.py | 5 | Config scanning |
| Iteration Budget | services/iteration_budget.py | 5 | Stuck detection |
| HITL Confirmation | services/hitl_confirmation.py | 4 | Async approval gate |
| Tool Views | services/tool_views.py | 4 | View registry |
| Coding Tools | services/coding_tools.py | 4 | 5 primitives |
| Tool Cache | services/tool_cache.py | 4 | TTL + dedup |
| Context Budget | services/context_budget.py | 4 | Token allocation |
