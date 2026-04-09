# Diseno: claw-code-patterns

## Arquitectura General

```
LaneOrchestrator (state machine)
│
├── WorkerPool
│   ├── Worker A → branch: feat/task-a (lane 1)
│   ├── Worker B → branch: feat/task-b (lane 2)
│   ├── Worker C → branch: feat/task-c (lane 3)
│   └── Worker D → branch: feat/task-d (lane 4)
│
├── BranchLockManager
│   ├── Lock registry (Redis)
│   ├── Collision detector (pre-merge diff analysis)
│   └── Stale branch detector (age + activity heuristic)
│
├── GreenContractPipeline
│   ├── Gate 1: lint + format
│   ├── Gate 2: unit tests
│   ├── Gate 3: integration tests
│   └── Gate 4: e2e tests (final gate before merge)
│
├── RecoveryEngine
│   ├── Scenario registry (7 built-in)
│   ├── Auto-retry policy (1 retry, then escalate)
│   └── Escalation bridge → HITL
│
└── TaskPacketValidator
    ├── Schema validation (JSON Schema)
    ├── Dependency resolver
    └── Contract registry
```

## Lane Orchestrator State Machine

```
[idle] → assign_task → [booting]
[booting] → worker_ready → [running]
[booting] → boot_failed → [recovery]
[running] → task_complete → [validating]
[running] → task_failed → [recovery]
[validating] → green_contract_pass → [merging]
[validating] → green_contract_fail → [recovery]
[merging] → merge_success → [idle]
[merging] → merge_conflict → [recovery]
[recovery] → auto_retry → [running]
[recovery] → escalate → [waiting_human]
[waiting_human] → human_resolved → [running]
```

## Worker Boot State Machine

```
[init] → load_config → [configured]
[configured] → checkout_branch → [branched]
[branched] → install_deps → [ready]
[ready] → receive_task → [working]
[working] → complete → [reporting]
[reporting] → ack → [idle]
```

## Green Contract Graduation

Cada lane debe pasar gates en orden. Un gate fallido bloquea los siguientes:

| Gate | Check | Timeout | Auto-retry |
|------|-------|---------|------------|
| G1 | lint + format | 30s | si |
| G2 | unit tests | 2m | si |
| G3 | integration tests | 5m | no |
| G4 | e2e tests | 10m | no |

## Recovery Scenarios

| # | Scenario | Auto-fix | Escalate if |
|---|----------|----------|-------------|
| 1 | Merge conflict (simple) | auto-rebase | >3 conflicting files |
| 2 | Flaky test | retry 1x | fails on retry |
| 3 | Worker timeout | restart worker | 2nd timeout |
| 4 | Dependency install fail | clear cache + retry | retry fails |
| 5 | Branch lock contention | queue + backoff | >5min wait |
| 6 | CI runner unavailable | wait + retry | >10min unavailable |
| 7 | Schema validation error | log + skip task | critical task |

## Plugin Degraded Mode

Cuando un plugin falla parcialmente, el sistema entra en modo degradado:
- Funcionalidad core sigue disponible
- Features del plugin fallido se deshabilitan con warning
- ToolDegraded event se publica al EventBus
- Auto-recovery intenta recargar el plugin cada 30s (max 3 intentos)
