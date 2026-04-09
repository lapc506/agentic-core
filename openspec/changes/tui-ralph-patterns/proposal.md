# Cambio: tui-ralph-patterns

**Change ID:** tui-ralph-patterns
**Fecha:** 2026-04-09

## Que
Terminal UI en Go que implementa 20 patrones de Ralph (autonomous TUI agent runner) para ejecutar agentes de forma autonoma desde la linea de comandos con sesiones persistentes, configuracion jerarquica y modo headless para CI.

## Por que
- El backend Python necesita un runner TUI de alto rendimiento escrito en Go
- Los patrones de Ralph cubren el ciclo completo: ejecucion autonoma, recuperacion de crashes, gestion de tareas, plugins y ejecucion paralela
- Permite operar agentes sin interfaz web, ideal para pipelines CI/CD y servidores remotos

## Alcance
### Incluido
- Autonomous execution loop (5 phases: init, plan, execute, evaluate, persist)
- Session persistence con crash recovery
- Completion token detection para saber cuando el agente termino
- Event-driven architecture con 22 tipos de eventos
- Single-key navigation y vistas de dashboard y agent tree
- Hierarchical config con 5 niveles TOML
- Prompt templates (Go text/template), theme system (5 temas)
- Error strategies: retry/skip/abort
- Parallel execution via git worktrees
- Headless mode con JSON logs para CI
- Iteration logging en JSONL
- Remote instance management con HMAC auth
- Plugin registry (Agent + Tracker plugins)
- PRD-as-Fuel task format
- Cost-aware model tiering
- Agent scratchpad (persistent TODO.md)

## Etiquetas
- Tipo: feature
- Tamano: L
- Prioridad: alta
