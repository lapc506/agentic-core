# Diseno: tui-ralph-patterns

## Arquitectura

Go binary independiente que se comunica con el backend Python via API HTTP/WebSocket. Usa Bubble Tea como framework TUI. Los patrones Ralph se implementan como capas sobre el loop de ejecucion central.

## Patrones implementados

| Patron | Categoria | Descripcion |
|---|---|---|
| TUI-01 | Core Engine | Autonomous execution loop (5 phases) |
| TUI-02 | Core Engine | Session persistence + crash recovery |
| TUI-03 | Core Engine | Completion token detection |
| TUI-04 | Core Engine | Event-driven architecture (22 event types) |
| TUI-05 | UI Views | Single-key navigation |
| TUI-06 | UI Views | Dashboard view (status, progress, cost) |
| TUI-07 | UI Views | Agent tree visualization |
| TUI-08 | Config | Hierarchical config (5-tier TOML) |
| TUI-09 | Config | Prompt templates (Go text/template) |
| TUI-10 | Config | Theme system (5 themes) |
| TUI-11 | Config | Error strategies (retry/skip/abort) |
| TUI-12 | Advanced | Parallel execution (git worktrees) |
| TUI-13 | Advanced | Headless mode (JSON logs for CI) |
| TUI-14 | Advanced | Iteration logging (JSONL) |
| TUI-15 | Remote | Remote instance management (HMAC auth) |
| TUI-16 | Remote | Plugin registry (Agent + Tracker) |
| TUI-17 | Remote | Connection status indicators |
| TUI-18 | Tasks | PRD-as-Fuel task format |
| TUI-19 | Tasks | Cost-aware model tiering |
| TUI-20 | Tasks | Agent scratchpad (persistent TODO.md) |

## Stack tecnico

- Lenguaje: Go 1.22+
- TUI framework: Bubble Tea (Charm)
- Config: TOML (5 niveles de herencia)
- Auth: HMAC-SHA256 para remote instances
- Logging: JSONL estructurado
- Paralelismo: git worktrees para aislamiento
