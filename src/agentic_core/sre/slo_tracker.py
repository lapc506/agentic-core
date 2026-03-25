from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from agentic_core.domain.events.domain_events import ErrorBudgetExhausted, SLOBreached
from agentic_core.domain.value_objects.slo import SLOTargets
from agentic_core.shared_kernel.events import EventBus

logger = logging.getLogger(__name__)


@dataclass
class SLIWindow:
    """Sliding window for SLI measurement."""
    requests: deque[tuple[float, bool]] = field(default_factory=deque)  # (timestamp, success)
    latencies: deque[tuple[float, float]] = field(default_factory=deque)  # (timestamp, latency_ms)
    window_seconds: float = 3600.0  # 1 hour default

    def record_request(self, success: bool, latency_ms: float) -> None:
        now = time.time()
        self.requests.append((now, success))
        self.latencies.append((now, latency_ms))
        self._evict(now)

    def success_rate(self) -> float:
        self._evict(time.time())
        if not self.requests:
            return 1.0
        successes = sum(1 for _, s in self.requests if s)
        return successes / len(self.requests)

    def latency_p99(self) -> float:
        self._evict(time.time())
        if not self.latencies:
            return 0.0
        sorted_lats = sorted(lat for _, lat in self.latencies)
        idx = int(len(sorted_lats) * 0.99)
        return sorted_lats[min(idx, len(sorted_lats) - 1)]

    def total_requests(self) -> int:
        self._evict(time.time())
        return len(self.requests)

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self.requests and self.requests[0][0] < cutoff:
            self.requests.popleft()
        while self.latencies and self.latencies[0][0] < cutoff:
            self.latencies.popleft()


class SLOTracker:
    """Tracks SLIs against SLO targets per persona. Publishes domain events on breach."""

    def __init__(self, event_bus: EventBus, window_seconds: float = 3600.0) -> None:
        self._event_bus = event_bus
        self._window_seconds = window_seconds
        self._windows: dict[str, SLIWindow] = {}
        self._targets: dict[str, SLOTargets] = {}

    def register_persona(self, persona_id: str, targets: SLOTargets) -> None:
        self._targets[persona_id] = targets
        self._windows[persona_id] = SLIWindow(window_seconds=self._window_seconds)

    async def record(self, persona_id: str, success: bool, latency_ms: float) -> None:
        window = self._windows.get(persona_id)
        if window is None:
            return
        window.record_request(success, latency_ms)

        targets = self._targets.get(persona_id)
        if targets is None:
            return

        now = datetime.now(timezone.utc)

        # Check success rate SLO
        current_rate = window.success_rate()
        if current_rate < targets.success_rate:
            await self._event_bus.publish(SLOBreached(
                persona_id=persona_id,
                sli_name="success_rate",
                current_value=current_rate,
                target_value=targets.success_rate,
                timestamp=now,
            ))

        # Check latency P99 SLO
        current_p99 = window.latency_p99()
        if current_p99 > targets.latency_p99_ms:
            await self._event_bus.publish(SLOBreached(
                persona_id=persona_id,
                sli_name="latency_p99",
                current_value=current_p99,
                target_value=targets.latency_p99_ms,
                timestamp=now,
            ))

    def error_budget_remaining(self, persona_id: str) -> float:
        window = self._windows.get(persona_id)
        targets = self._targets.get(persona_id)
        if window is None or targets is None:
            return 1.0
        allowed_error_rate = 1.0 - targets.success_rate
        actual_error_rate = 1.0 - window.success_rate()
        if allowed_error_rate <= 0:
            return 0.0
        return max(0.0, 1.0 - (actual_error_rate / allowed_error_rate))

    def get_status(self, persona_id: str) -> dict[str, float]:
        window = self._windows.get(persona_id)
        if window is None:
            return {}
        return {
            "success_rate": window.success_rate(),
            "latency_p99_ms": window.latency_p99(),
            "total_requests": float(window.total_requests()),
            "error_budget_remaining": self.error_budget_remaining(persona_id),
        }
