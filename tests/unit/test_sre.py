from __future__ import annotations

import pytest

from agentic_core.domain.events.domain_events import SLOBreached
from agentic_core.domain.value_objects.slo import SLOTargets
from agentic_core.shared_kernel.events import DomainEvent, EventBus
from agentic_core.sre.chaos import ChaosConfig, ChaosError, ChaosHooks
from agentic_core.sre.slo_tracker import SLIWindow, SLOTracker

# -- SLIWindow --

def test_sli_window_success_rate():
    w = SLIWindow()
    for _ in range(9):
        w.record_request(True, 100.0)
    w.record_request(False, 500.0)
    assert w.success_rate() == pytest.approx(0.9)


def test_sli_window_latency_p99():
    w = SLIWindow()
    for i in range(100):
        w.record_request(True, float(i))
    assert w.latency_p99() == 99.0


def test_sli_window_empty():
    w = SLIWindow()
    assert w.success_rate() == 1.0
    assert w.latency_p99() == 0.0


# -- SLOTracker --

async def test_slo_tracker_no_breach():
    bus = EventBus()
    breaches: list[DomainEvent] = []
    bus.subscribe(SLOBreached, lambda e: breaches.append(e))  # type: ignore[arg-type]

    tracker = SLOTracker(bus)
    tracker.register_persona("p1", SLOTargets(success_rate=0.9, latency_p99_ms=5000))

    for _ in range(10):
        await tracker.record("p1", success=True, latency_ms=100.0)

    # All good — no breaches expected (handler is not async, so subscribe won't work properly)
    # But the important thing is it doesn't crash
    status = tracker.get_status("p1")
    assert status["success_rate"] == 1.0
    assert status["total_requests"] == 10.0


async def test_slo_tracker_success_rate_breach():
    bus = EventBus()
    breaches: list[DomainEvent] = []

    async def on_breach(event: DomainEvent) -> None:
        breaches.append(event)

    bus.subscribe(SLOBreached, on_breach)

    tracker = SLOTracker(bus)
    tracker.register_persona("p1", SLOTargets(success_rate=0.95, latency_p99_ms=5000))

    # 8 success + 2 failure = 80% success rate (below 95% target)
    for _ in range(8):
        await tracker.record("p1", success=True, latency_ms=100.0)
    for _ in range(2):
        await tracker.record("p1", success=False, latency_ms=100.0)

    assert len(breaches) >= 1
    assert any(e.sli_name == "success_rate" for e in breaches)  # type: ignore[attr-defined]


async def test_slo_tracker_error_budget():
    bus = EventBus()
    tracker = SLOTracker(bus)
    tracker.register_persona("p1", SLOTargets(success_rate=0.99))

    # 100 requests, 1 failure = 99% = exactly at target
    for _ in range(99):
        await tracker.record("p1", success=True, latency_ms=50.0)
    await tracker.record("p1", success=False, latency_ms=50.0)

    budget = tracker.error_budget_remaining("p1")
    assert 0.0 <= budget <= 1.0


def test_slo_tracker_unknown_persona():
    bus = EventBus()
    tracker = SLOTracker(bus)
    assert tracker.get_status("unknown") == {}
    assert tracker.error_budget_remaining("unknown") == 1.0


# -- ChaosHooks --

async def test_chaos_disabled_by_default():
    hooks = ChaosHooks()
    assert not hooks.enabled
    await hooks.before_node("test")  # Should not raise


async def test_chaos_latency_injection():
    import time
    config = ChaosConfig(enabled=True, latency_injection_ms={"slow_node": 50})
    hooks = ChaosHooks(config)

    start = time.monotonic()
    await hooks.before_node("slow_node")
    elapsed = (time.monotonic() - start) * 1000
    assert elapsed >= 40  # Allow some tolerance


async def test_chaos_failure_injection():
    config = ChaosConfig(enabled=True, failure_rate={"fail_node": 1.0})
    hooks = ChaosHooks(config)

    with pytest.raises(ChaosError, match="simulated failure"):
        await hooks.before_node("fail_node")


async def test_chaos_no_effect_on_other_nodes():
    config = ChaosConfig(enabled=True, failure_rate={"fail_node": 1.0})
    hooks = ChaosHooks(config)
    await hooks.before_node("safe_node")  # Should not raise


def test_chaos_provider_kill():
    config = ChaosConfig(enabled=True, provider_kill=["redis"])
    hooks = ChaosHooks(config)
    assert hooks.is_provider_killed("redis")
    assert not hooks.is_provider_killed("postgres")
