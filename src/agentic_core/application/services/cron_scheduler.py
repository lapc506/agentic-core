"""Scheduled task execution via cron expressions and heartbeat intervals.

Cron scheduler with heartbeat pattern.

Usage:
    scheduler = CronScheduler()

    scheduler.add_job(CronJob(
        name="daily-report",
        cron="0 7 * * *",
        persona_id="analyst-agent",
        message="Generate daily metrics report",
    ))

    scheduler.add_heartbeat(HeartbeatJob(
        name="sensor-check",
        interval_seconds=300,
        persona_id="agronomist",
        message="Check all sensor readings",
    ))

    await scheduler.start()  # Runs until stopped
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class CronJob:
    name: str
    cron: str
    persona_id: str
    message: str
    session_mode: str = "isolated"
    enabled: bool = True
    max_runs: int | None = None
    run_count: int = 0
    status: JobStatus = JobStatus.PENDING
    last_run: datetime | None = None


@dataclass
class HeartbeatJob:
    name: str
    interval_seconds: int
    persona_id: str
    message: str
    enabled: bool = True
    status: JobStatus = JobStatus.PENDING
    last_run: datetime | None = None


JobCallback = Callable[[str, str, str], Awaitable[None]]


def _parse_cron_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field into a set of matching integers."""
    values: set[int] = set()
    for part in field_str.split(","):
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = int(step_str)
            start = min_val if base in ("*", "") else int(base)
            values.update(range(start, max_val + 1, step))
        elif part == "*":
            values.update(range(min_val, max_val + 1))
        elif "-" in part:
            lo, hi = part.split("-", 1)
            values.update(range(int(lo), int(hi) + 1))
        else:
            values.add(int(part))
    return values


def cron_matches(cron_expr: str, dt: datetime) -> bool:
    """Check if a datetime matches a cron expression (minute hour dom month dow)."""
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr!r} (need 5 fields)")

    minute_f, hour_f, dom_f, month_f, dow_f = parts
    return (
        dt.minute in _parse_cron_field(minute_f, 0, 59)
        and dt.hour in _parse_cron_field(hour_f, 0, 23)
        and dt.day in _parse_cron_field(dom_f, 1, 31)
        and dt.month in _parse_cron_field(month_f, 1, 12)
        and dt.weekday() in _parse_cron_field(dow_f, 0, 6)
    )


class CronScheduler:
    """Manages cron jobs and heartbeat intervals."""

    def __init__(self, callback: JobCallback | None = None) -> None:
        self._cron_jobs: dict[str, CronJob] = {}
        self._heartbeat_jobs: dict[str, HeartbeatJob] = {}
        self._callback = callback
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def add_job(self, job: CronJob) -> None:
        self._cron_jobs[job.name] = job

    def remove_job(self, name: str) -> None:
        self._cron_jobs.pop(name, None)

    def add_heartbeat(self, job: HeartbeatJob) -> None:
        self._heartbeat_jobs[job.name] = job

    def remove_heartbeat(self, name: str) -> None:
        self._heartbeat_jobs.pop(name, None)

    def list_jobs(self) -> list[CronJob]:
        return list(self._cron_jobs.values())

    def list_heartbeats(self) -> list[HeartbeatJob]:
        return list(self._heartbeat_jobs.values())

    def get_job(self, name: str) -> CronJob | None:
        return self._cron_jobs.get(name)

    def get_heartbeat(self, name: str) -> HeartbeatJob | None:
        return self._heartbeat_jobs.get(name)

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        self._running = True
        for job in self._cron_jobs.values():
            job.status = JobStatus.ACTIVE
        for hb in self._heartbeat_jobs.values():
            hb.status = JobStatus.ACTIVE
        logger.info(
            "CronScheduler started: %d cron jobs, %d heartbeats",
            len(self._cron_jobs), len(self._heartbeat_jobs),
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None
        for job in self._cron_jobs.values():
            if job.status == JobStatus.ACTIVE:
                job.status = JobStatus.PAUSED
        for hb in self._heartbeat_jobs.values():
            if hb.status == JobStatus.ACTIVE:
                hb.status = JobStatus.PAUSED
        logger.info("CronScheduler stopped")

    async def tick(self, now: datetime | None = None) -> list[str]:
        """Check and fire due jobs. Returns names of fired jobs.

        Pass `now` explicitly for deterministic testing.
        """
        if not self._running:
            return []

        now = now or datetime.now(UTC)
        fired: list[str] = []

        for job in self._cron_jobs.values():
            if not job.enabled or job.status != JobStatus.ACTIVE:
                continue
            if job.max_runs is not None and job.run_count >= job.max_runs:
                job.status = JobStatus.COMPLETED
                continue
            if cron_matches(job.cron, now):
                await self._fire_job(job.persona_id, job.message, job.name)
                job.run_count += 1
                job.last_run = now
                fired.append(job.name)

        for hb in self._heartbeat_jobs.values():
            if not hb.enabled or hb.status != JobStatus.ACTIVE:
                continue
            if hb.last_run is None or (
                (now - hb.last_run).total_seconds() >= hb.interval_seconds
            ):
                await self._fire_job(hb.persona_id, hb.message, hb.name)
                hb.last_run = now
                fired.append(hb.name)

        return fired

    async def _fire_job(
        self, persona_id: str, message: str, job_name: str,
    ) -> None:
        if self._callback is not None:
            try:
                await self._callback(persona_id, message, job_name)
            except Exception:
                logger.exception("Job '%s' callback failed", job_name)
        else:
            logger.info("Job '%s' fired: persona=%s", job_name, persona_id)
