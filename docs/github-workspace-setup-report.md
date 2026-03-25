# GitHub Workspace Setup Report

> **Date:** 2026-03-25
> **Repo:** lapc506/agentic-core
> **License:** MIT (open-source)
> **Mode:** clean (full setup)

---

## Labels

### Type (exclusive, required) -- prefix `type:`

| Label | Color | Status |
|-------|-------|--------|
| type:bug | `#EB5757` | Created |
| type:chore | `#9B8AFB` | Created |
| type:feature | `#BB87FC` | Created |
| type:spike | `#C9A0FF` | Created |
| type:improvement | `#4EA7FC` | Created |
| type:design | `#D98AEB` | Created |

### Size (exclusive, AI token budgets) -- prefix `size:`

| Label | Color | Status |
|-------|-------|--------|
| size:XS | `#26B5CE` | Created |
| size:S | `#0B9D6F` | Created |
| size:M | `#4CB782` | Created |
| size:L | `#F2994A` | Created |
| size:XL | `#EB5757` | Created |

### Strategy (exclusive) -- prefix `strategy:`

| Label | Color | Status |
|-------|-------|--------|
| strategy:solo | `#4EA7FC` | Created |
| strategy:explore | `#68B8F8` | Created |
| strategy:team | `#2D6FE4` | Created |
| strategy:human | `#95A2B3` | Created |
| strategy:worktree | `#5E6AD2` | Created |
| strategy:review | `#7C8DB5` | Created |

### Component (combinable) -- prefix `component:`

| Label | Color | Status |
|-------|-------|--------|
| component:transport | `#F2994A` | Created |
| component:domain | `#F28933` | Created |
| component:application | `#E87B35` | Created |
| component:memory | `#E06C3A` | Created |
| component:rag | `#D4613E` | Created |
| component:tools | `#C85640` | Created |
| component:observability | `#F2C94C` | Created |
| component:sre | `#F0B429` | Created |
| component:security | `#E06C3A` | Created |
| component:infra | `#C85640` | Created |
| component:testing | `#F2C94C` | Created |

### Impact (combinable) -- prefix `impact:`

| Label | Color | Status |
|-------|-------|--------|
| impact:critical-path | `#EB5757` | Created |
| impact:oss-adoption | `#E5484D` | Created |

### Flags (combinable) -- prefix `flag:`

| Label | Color | Status |
|-------|-------|--------|
| flag:blocked | `#EB5757` | Created |
| flag:quick-win | `#0B9D6F` | Created |
| flag:epic | `#5E6AD2` | Created |
| flag:good-first-issue | `#7057FF` | Created |
| flag:help-wanted | `#008672` | Created |

---

## Milestones (replace Linear Projects)

| Milestone | Number | Status |
|-----------|--------|--------|
| Phase 1: Core + Transport + Runtime | #1 | Open |
| Phase 2: Memory + RAG + LangGraph | #2 | Open |
| Phase 3: Observability + SRE + Meta-Orchestration | #3 | Open |
| Phase 4: Security + Deployment + Docs | #4 | Open |

---

## Issues Created (Phase 1)

| # | Title | Labels | Size |
|---|-------|--------|------|
| 1 | Project scaffolding | chore, infra, critical-path | S |
| 2 | Shared Kernel | feature, domain, critical-path | S |
| 3 | Domain Enums | feature, domain | XS |
| 4 | Value Objects (AgentMessage, ModelConfig) | feature, domain, critical-path | S |
| 5 | Domain Entities (Session state machine, Persona, etc.) | feature, domain, critical-path | M |
| 6 | Domain Events | feature, domain | XS |
| 7 | Domain Services (Routing, Escalation, ModelResolver) | feature, domain | M |
| 8 | Application Ports (12 ABCs) | feature, application, critical-path | M |
| 9 | Command & Query Handler Skeletons | feature, application | S |
| 10 | Middleware Chain + TracingMiddleware | feature, application | S |
| 11 | Configuration (AgenticSettings, all sub-configs) | feature, application | S |
| 12 | gRPC Proto + Codegen | feature, transport | S |
| 13 | WebSocket Primary Adapter | feature, transport, critical-path | L |
| 14 | gRPC Primary Adapter | feature, transport | M |
| 15 | AgentRuntime Composition Root | feature, application, critical-path | M |

---

## Summary

- Labels: 35 created, 9 default removed
- Milestones: 4 created
- Issues: 15 created (Phase 1 scope)
- Total API calls: ~58
