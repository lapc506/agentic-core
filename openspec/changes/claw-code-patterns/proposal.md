# Cambio: claw-code-patterns

**Change ID:** claw-code-patterns
**Fecha:** 2026-04-08
**Branch:** feat/claw-code-patterns

## Que

Patrones de coordinacion multi-agente inspirados en OpenClaw/NemoClaw para orquestar multiples workers de codigo trabajando en paralelo sin colisiones de branch, con contratos de CI graduados y recetas de recuperacion automatica.

## Por que

- **Paralelismo real:** Multiples agentes trabajando en ramas simultaneas necesitan un orquestador de lanes que evite colisiones de merge y lock de branches.
- **Calidad graduada:** Green contracts (CI gates graduados) aseguran que cada lane pase por validaciones incrementales antes de merge a main.
- **Resiliencia:** Las recetas de recuperacion cubren 7 escenarios comunes (conflictos de merge, tests flaky, timeout de worker, etc.) con auto-retry antes de escalar a humano.
- **Branches limpios:** Deteccion de branches stale y politica de auto-rebase mantienen el repo limpio.
- **Contratos de trabajo:** Task packets estructurados garantizan que cada worker recibe un contrato de trabajo validado antes de empezar.

## Alcance

### Incluido
- Lane orchestrator (state machine, branch lock, collision detection)
- Green contracts (graduated CI gates: lint -> unit -> integration -> e2e)
- Recovery recipes (7 scenarios, 1-auto-retry-then-escalate policy)
- Stale branch detection + auto-rebase policy
- Task packet validation (structured work contracts)
- Worker boot state machine
- Plugin degraded mode (partial functionality)
- MCP 11-phase lifecycle hardening

### Excluido
- Integracion directa con NVIDIA NIM (ver nvidia-nemoclaw)
- GPU scheduling o resource allocation
- Custom CI runners

## Etiquetas

- **Tipo:** feature
- **Prioridad:** alta
- **Tamano:** XL (semanas)
- **Dependencias:** standalone-agent-studio (runtime), agent-intelligence (graph templates)
- **Personas afectadas:** desarrolladores, CI/CD pipelines, agentes autonomos

## Criterios de Aceptacion

- [ ] Lane orchestrator maneja 4+ workers en paralelo sin colisiones de branch
- [ ] Green contracts bloquean merge si algun gate falla
- [ ] Recovery recipes resuelven automaticamente al menos 5/7 escenarios sin intervencion humana
- [ ] Branches stale se detectan y se ofrece auto-rebase o cleanup
- [ ] Task packets se validan con schema antes de asignar a worker
