"""Global kill switch, circuit breaker, and anomaly detection.

Provides emergency shutdown capabilities and automatic failure isolation
for the agentic-core runtime.

Security gap #4 in the agentic-core threat model.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------


@dataclass
class KillRecord:
    """Metadata for a kill event."""

    reason: str
    activated_at: float = field(default_factory=time.time)


class KillSwitch:
    """Global and per-agent emergency shutdown.

    When activated, all agent execution must check :pyattr:`is_active`
    before proceeding with any action.
    """

    def __init__(self) -> None:
        self._global: KillRecord | None = None
        self._per_agent: dict[str, KillRecord] = {}

    # -- global controls ----------------------------------------------------

    def activate(self, reason: str) -> None:
        """Immediately halt **all** agent execution."""
        self._global = KillRecord(reason=reason)
        logger.critical("KILL SWITCH ACTIVATED: %s", reason)

    def deactivate(self) -> None:
        """Resume global operations."""
        self._global = None
        self._per_agent.clear()
        logger.info("Kill switch deactivated, all agents resumed")

    @property
    def is_active(self) -> bool:
        """*True* when the global kill switch is engaged."""
        return self._global is not None

    @property
    def reason(self) -> str | None:
        """The reason the kill switch was activated, or *None*."""
        return self._global.reason if self._global else None

    # -- per-agent controls -------------------------------------------------

    def activate_for_agent(self, agent_id: str, reason: str) -> None:
        """Halt a specific agent."""
        self._per_agent[agent_id] = KillRecord(reason=reason)
        logger.warning("Agent killed: %s — %s", agent_id, reason)

    def deactivate_for_agent(self, agent_id: str) -> None:
        """Resume a specific agent."""
        self._per_agent.pop(agent_id, None)

    def is_agent_killed(self, agent_id: str) -> bool:
        """*True* when the global switch is active **or** the specific agent
        has been individually killed."""
        return self.is_active or agent_id in self._per_agent

    def agent_kill_reason(self, agent_id: str) -> str | None:
        """Return the kill reason for an agent, preferring the global reason."""
        if self._global:
            return self._global.reason
        record = self._per_agent.get(agent_id)
        return record.reason if record else None


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitOpenError(RuntimeError):
    """Raised when a call is attempted on an open circuit."""


class CircuitBreaker:
    """Per-service circuit breaker: closed -> open -> half-open -> closed.

    Parameters
    ----------
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds to wait in OPEN state before transitioning to HALF_OPEN.
    half_open_max_calls:
        Maximum trial calls allowed in HALF_OPEN before deciding.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls: int = 0

    # -- state property -----------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Return the current circuit state, possibly transitioning from
        OPEN to HALF_OPEN if the recovery timeout has elapsed."""
        if (
            self._state == CircuitState.OPEN
            and (time.time() - self._last_failure_time) >= self._recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0
            logger.info("Circuit breaker transitioned to HALF_OPEN")
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    # -- call wrapper -------------------------------------------------------

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute *fn* through the circuit breaker.

        Raises :class:`CircuitOpenError` if the circuit is open.
        """
        current_state = self.state  # may transition OPEN -> HALF_OPEN

        if current_state == CircuitState.OPEN:
            raise CircuitOpenError("Circuit is OPEN — call rejected")

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._half_open_max_calls:
                raise CircuitOpenError(
                    "Circuit is HALF_OPEN — max trial calls reached",
                )
            self._half_open_calls += 1

        try:
            result = fn(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        else:
            self._record_success()
            return result

    # -- manual reset -------------------------------------------------------

    def reset(self) -> None:
        """Manually close the circuit and clear all counters."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        logger.info("Circuit breaker manually reset to CLOSED")

    # -- internals ----------------------------------------------------------

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._success_count = 0
        self._last_failure_time = time.time()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPENED after %d failures",
                self._failure_count,
            )
        elif self._state == CircuitState.HALF_OPEN:
            # Single failure in half-open re-opens the circuit
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker re-OPENED from HALF_OPEN on failure")

    def _record_success(self) -> None:
        self._success_count += 1
        if self._state == CircuitState.HALF_OPEN:
            # Successful trial call — close the circuit
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info("Circuit breaker CLOSED after successful half-open call")


# ---------------------------------------------------------------------------
# Anomaly Detector
# ---------------------------------------------------------------------------


@dataclass
class AnomalyThresholds:
    """Configurable thresholds for automatic kill-switch activation."""

    max_tool_calls_per_window: int = 100
    """Max tool invocations per agent within *window_seconds*."""

    max_data_bytes_per_window: int = 10 * 1024 * 1024  # 10 MiB
    """Max data volume per agent within *window_seconds*."""

    max_consecutive_errors: int = 10
    """Max consecutive errors before kill is triggered."""

    window_seconds: float = 60.0
    """Sliding window duration for rate-based thresholds."""


class AnomalyDetector:
    """Tracks per-agent behaviour and auto-triggers a :class:`KillSwitch`
    when configurable thresholds are breached.

    Monitors:
    * Tool call frequency per agent per sliding window.
    * Cumulative data volume per agent (potential exfiltration).
    * Consecutive errors per agent.
    """

    def __init__(
        self,
        kill_switch: KillSwitch,
        thresholds: AnomalyThresholds | None = None,
    ) -> None:
        self._kill_switch = kill_switch
        self._thresholds = thresholds or AnomalyThresholds()

        # agent_id -> list of timestamps
        self._tool_calls: dict[str, list[float]] = defaultdict(list)
        # agent_id -> list of (timestamp, bytes)
        self._data_volume: dict[str, list[tuple[float, int]]] = defaultdict(list)
        # agent_id -> count
        self._consecutive_errors: dict[str, int] = defaultdict(int)

    @property
    def thresholds(self) -> AnomalyThresholds:
        return self._thresholds

    # -- recording events ---------------------------------------------------

    def record_tool_call(self, agent_id: str) -> None:
        """Record a tool invocation for *agent_id*."""
        now = time.time()
        self._tool_calls[agent_id].append(now)
        self._prune(agent_id)

        count = len(self._tool_calls[agent_id])
        if count > self._thresholds.max_tool_calls_per_window:
            reason = (
                f"Agent {agent_id} exceeded tool call threshold "
                f"({count}/{self._thresholds.max_tool_calls_per_window} "
                f"in {self._thresholds.window_seconds}s)"
            )
            self._kill_switch.activate_for_agent(agent_id, reason)
            logger.warning("Anomaly detected: %s", reason)

    def record_data_volume(self, agent_id: str, num_bytes: int) -> None:
        """Record outbound data volume for *agent_id*."""
        now = time.time()
        self._data_volume[agent_id].append((now, num_bytes))
        self._prune(agent_id)

        total = sum(b for _, b in self._data_volume[agent_id])
        if total > self._thresholds.max_data_bytes_per_window:
            reason = (
                f"Agent {agent_id} exceeded data volume threshold "
                f"({total}/{self._thresholds.max_data_bytes_per_window} bytes "
                f"in {self._thresholds.window_seconds}s)"
            )
            self._kill_switch.activate_for_agent(agent_id, reason)
            logger.warning("Anomaly detected: %s", reason)

    def record_error(self, agent_id: str) -> None:
        """Record a consecutive error for *agent_id*."""
        self._consecutive_errors[agent_id] += 1
        count = self._consecutive_errors[agent_id]
        if count >= self._thresholds.max_consecutive_errors:
            reason = (
                f"Agent {agent_id} hit {count} consecutive errors"
            )
            self._kill_switch.activate_for_agent(agent_id, reason)
            logger.warning("Anomaly detected: %s", reason)

    def record_success(self, agent_id: str) -> None:
        """Reset the consecutive-error counter on a successful operation."""
        self._consecutive_errors[agent_id] = 0

    # -- query --------------------------------------------------------------

    def tool_call_count(self, agent_id: str) -> int:
        """Return the number of tool calls in the current window."""
        self._prune(agent_id)
        return len(self._tool_calls[agent_id])

    def data_volume(self, agent_id: str) -> int:
        """Return cumulative data volume (bytes) in the current window."""
        self._prune(agent_id)
        return sum(b for _, b in self._data_volume[agent_id])

    def consecutive_errors(self, agent_id: str) -> int:
        return self._consecutive_errors.get(agent_id, 0)

    # -- internals ----------------------------------------------------------

    def _prune(self, agent_id: str) -> None:
        """Evict entries older than the sliding window."""
        cutoff = time.time() - self._thresholds.window_seconds
        self._tool_calls[agent_id] = [
            t for t in self._tool_calls[agent_id] if t > cutoff
        ]
        self._data_volume[agent_id] = [
            (t, b) for t, b in self._data_volume[agent_id] if t > cutoff
        ]
