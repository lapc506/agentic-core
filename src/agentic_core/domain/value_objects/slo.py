from __future__ import annotations

from pydantic import BaseModel


class SLOTargets(BaseModel, frozen=True):
    latency_p99_ms: float = 5000.0
    success_rate: float = 0.995
    availability: float = 0.999
