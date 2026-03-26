# SLO Definitions for Agent Personas

## Overview

Each agent persona defines SLO targets in its YAML config. The SLOTracker measures SLIs against these targets in a sliding window and publishes `SLOBreached` events when thresholds are exceeded.

## Example SLO Definitions

### Support Agent (customer-facing, high availability)

```yaml
slo_targets:
  latency_p99_ms: 5000     # 99th percentile response time
  success_rate: 0.995       # 99.5% of requests succeed
  availability: 0.999       # 99.9% uptime
```

| SLI | Target | Error Budget (30 days) | Meaning |
|-----|--------|----------------------|---------|
| Success Rate | 99.5% | 2,160 errors / 432,000 requests | ~72 errors/day allowed |
| Latency P99 | 5s | N/A (latency SLO) | 1% of requests can exceed 5s |

### Analyst Agent (complex reasoning, relaxed latency)

```yaml
slo_targets:
  latency_p99_ms: 30000    # 30s allowed for deep analysis
  success_rate: 0.99        # 99%
  availability: 0.995
```

### Orchestrator (multi-agent coordination)

```yaml
slo_targets:
  latency_p99_ms: 60000    # 60s for full orchestration cycles
  success_rate: 0.95        # 95% (complex workflows may fail)
  availability: 0.99
```

## Error Budget Calculation

```
Error Budget = 1 - SLO Target
Budget Period = 30 days

Allowed failures = Total requests * Error Budget
Example: 100,000 req/month * (1 - 0.995) = 500 failures allowed
```

## Burn Rate Alerting

| Burn Rate | Window | Meaning | Severity |
|-----------|--------|---------|----------|
| 14x | 1 hour | Budget exhausted in ~2 days | Critical |
| 5x | 6 hours | Budget exhausted in ~6 days | Warning |
| 2x | 3 days | Budget exhausted in ~15 days | Info |

Alert fires when `error_budget_remaining < 0.25` (25% remaining).

## Monitoring

```bash
# Check SLO status via gRPC
grpcurl localhost:50051 agentic_core.AgentService/HealthCheck

# Prometheus queries
# Success rate by persona
sum(rate(agent_requests_total{status="success"}[1h])) by (persona_id)
/ sum(rate(agent_requests_total[1h])) by (persona_id)

# Latency P99 by persona
histogram_quantile(0.99,
  sum(rate(agent_request_duration_seconds_bucket[5m])) by (le, persona_id)
)

# Error budget remaining
agent_error_budget_remaining_ratio
```
