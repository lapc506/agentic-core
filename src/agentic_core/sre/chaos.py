from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ChaosConfig:
    enabled: bool = False
    latency_injection_ms: dict[str, int] = field(default_factory=dict)  # node_name -> ms
    failure_rate: dict[str, float] = field(default_factory=dict)  # node_name -> 0.0-1.0
    provider_kill: list[str] = field(default_factory=list)  # provider names to simulate down


class ChaosError(Exception):
    pass


class ChaosHooks:
    """Controlled fault injection for resilience testing. Opt-in via config."""

    def __init__(self, config: ChaosConfig | None = None) -> None:
        self._config = config or ChaosConfig()

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    async def before_node(self, node_name: str) -> None:
        if not self._config.enabled:
            return

        # Latency injection
        delay_ms = self._config.latency_injection_ms.get(node_name, 0)
        if delay_ms > 0:
            logger.info("Chaos: injecting %dms latency into %s", delay_ms, node_name)
            await asyncio.sleep(delay_ms / 1000.0)

        # Failure injection
        failure_rate = self._config.failure_rate.get(node_name, 0.0)
        if failure_rate > 0 and random.random() < failure_rate:
            logger.info("Chaos: injecting failure into %s (rate=%.2f)", node_name, failure_rate)
            raise ChaosError(f"Chaos: simulated failure in {node_name}")

    def is_provider_killed(self, provider_name: str) -> bool:
        if not self._config.enabled:
            return False
        return provider_name in self._config.provider_kill
