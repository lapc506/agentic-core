from __future__ import annotations

from datetime import UTC, datetime

from agentic_core.application.services.cron_scheduler import (
    CronJob,
    CronScheduler,
    HeartbeatJob,
    JobStatus,
    _parse_cron_field,
    cron_matches,
)

# --- cron parsing ---


def test_parse_wildcard():
    assert _parse_cron_field("*", 0, 5) == {0, 1, 2, 3, 4, 5}


def test_parse_single_value():
    assert _parse_cron_field("3", 0, 59) == {3}


def test_parse_range():
    assert _parse_cron_field("1-4", 0, 59) == {1, 2, 3, 4}


def test_parse_step():
    assert _parse_cron_field("*/15", 0, 59) == {0, 15, 30, 45}


def test_parse_step_with_start():
    assert _parse_cron_field("5/10", 0, 59) == {5, 15, 25, 35, 45, 55}


def test_parse_comma_list():
    assert _parse_cron_field("1,3,5", 0, 59) == {1, 3, 5}


def test_cron_matches_every_minute():
    dt = datetime(2026, 3, 25, 10, 30, tzinfo=UTC)
    assert cron_matches("* * * * *", dt)


def test_cron_matches_specific():
    dt = datetime(2026, 3, 25, 7, 0, tzinfo=UTC)  # Tuesday
    assert cron_matches("0 7 * * *", dt)


def test_cron_no_match():
    dt = datetime(2026, 3, 25, 8, 0, tzinfo=UTC)
    assert not cron_matches("0 7 * * *", dt)


def test_cron_matches_dow():
    dt = datetime(2026, 3, 25, 9, 0, tzinfo=UTC)  # Wednesday = 2
    assert cron_matches("0 9 * * 2", dt)
    assert not cron_matches("0 9 * * 5", dt)


def test_cron_invalid_raises():
    import pytest
    with pytest.raises(ValueError, match="need 5 fields"):
        cron_matches("* *", datetime.now(UTC))


# --- CronScheduler basics ---


def test_empty_scheduler():
    s = CronScheduler()
    assert s.list_jobs() == []
    assert s.list_heartbeats() == []
    assert not s.is_running


def test_add_remove_job():
    s = CronScheduler()
    job = CronJob(name="test", cron="* * * * *", persona_id="p", message="m")
    s.add_job(job)
    assert len(s.list_jobs()) == 1
    assert s.get_job("test") is job
    s.remove_job("test")
    assert s.list_jobs() == []


def test_add_remove_heartbeat():
    s = CronScheduler()
    hb = HeartbeatJob(
        name="hb", interval_seconds=60, persona_id="p", message="m",
    )
    s.add_heartbeat(hb)
    assert len(s.list_heartbeats()) == 1
    assert s.get_heartbeat("hb") is hb
    s.remove_heartbeat("hb")
    assert s.list_heartbeats() == []


# --- Scheduler lifecycle ---


async def test_start_sets_active():
    s = CronScheduler()
    job = CronJob(name="j", cron="* * * * *", persona_id="p", message="m")
    s.add_job(job)
    await s.start()
    assert s.is_running
    assert job.status == JobStatus.ACTIVE


async def test_stop_pauses_jobs():
    s = CronScheduler()
    job = CronJob(name="j", cron="* * * * *", persona_id="p", message="m")
    s.add_job(job)
    await s.start()
    await s.stop()
    assert not s.is_running
    assert job.status == JobStatus.PAUSED


# --- tick() cron jobs ---


async def test_tick_fires_matching_cron():
    fired: list[tuple[str, str, str]] = []

    async def cb(persona_id: str, message: str, job_name: str) -> None:
        fired.append((persona_id, message, job_name))

    s = CronScheduler(callback=cb)
    s.add_job(CronJob(
        name="morning", cron="0 7 * * *", persona_id="analyst", message="report",
    ))
    await s.start()

    now = datetime(2026, 3, 25, 7, 0, tzinfo=UTC)
    result = await s.tick(now)
    assert result == ["morning"]
    assert fired == [("analyst", "report", "morning")]


async def test_tick_skips_non_matching_cron():
    fired: list[str] = []

    async def cb(persona_id: str, message: str, job_name: str) -> None:
        fired.append(job_name)

    s = CronScheduler(callback=cb)
    s.add_job(CronJob(
        name="morning", cron="0 7 * * *", persona_id="p", message="m",
    ))
    await s.start()

    now = datetime(2026, 3, 25, 8, 0, tzinfo=UTC)
    result = await s.tick(now)
    assert result == []
    assert fired == []


async def test_tick_not_running_does_nothing():
    s = CronScheduler()
    s.add_job(CronJob(
        name="j", cron="* * * * *", persona_id="p", message="m",
    ))
    result = await s.tick()
    assert result == []


async def test_tick_disabled_job_skipped():
    fired: list[str] = []

    async def cb(persona_id: str, message: str, job_name: str) -> None:
        fired.append(job_name)

    s = CronScheduler(callback=cb)
    s.add_job(CronJob(
        name="j", cron="* * * * *", persona_id="p", message="m", enabled=False,
    ))
    await s.start()
    await s.tick()
    assert fired == []


async def test_tick_max_runs():
    fired: list[str] = []

    async def cb(persona_id: str, message: str, job_name: str) -> None:
        fired.append(job_name)

    s = CronScheduler(callback=cb)
    s.add_job(CronJob(
        name="once", cron="* * * * *", persona_id="p", message="m", max_runs=1,
    ))
    await s.start()

    await s.tick()
    await s.tick()
    assert len(fired) == 1
    assert s.get_job("once") is not None
    assert s.get_job("once").status == JobStatus.COMPLETED  # type: ignore[union-attr]


async def test_tick_updates_last_run():
    s = CronScheduler()
    s.add_job(CronJob(
        name="j", cron="* * * * *", persona_id="p", message="m",
    ))
    await s.start()
    now = datetime(2026, 3, 25, 10, 0, tzinfo=UTC)
    await s.tick(now)
    assert s.get_job("j") is not None
    assert s.get_job("j").last_run == now  # type: ignore[union-attr]


# --- tick() heartbeat jobs ---


async def test_tick_fires_heartbeat_first_time():
    fired: list[str] = []

    async def cb(persona_id: str, message: str, job_name: str) -> None:
        fired.append(job_name)

    s = CronScheduler(callback=cb)
    s.add_heartbeat(HeartbeatJob(
        name="sensor", interval_seconds=300, persona_id="agro", message="check",
    ))
    await s.start()

    result = await s.tick()
    assert "sensor" in result
    assert fired == ["sensor"]


async def test_tick_heartbeat_respects_interval():
    fired: list[str] = []

    async def cb(persona_id: str, message: str, job_name: str) -> None:
        fired.append(job_name)

    s = CronScheduler(callback=cb)
    s.add_heartbeat(HeartbeatJob(
        name="hb", interval_seconds=600, persona_id="p", message="m",
    ))
    await s.start()

    t0 = datetime(2026, 3, 25, 10, 0, 0, tzinfo=UTC)
    await s.tick(t0)  # fires (first time)
    assert len(fired) == 1

    t1 = datetime(2026, 3, 25, 10, 5, 0, tzinfo=UTC)  # 5 min later
    await s.tick(t1)  # too early
    assert len(fired) == 1

    t2 = datetime(2026, 3, 25, 10, 10, 0, tzinfo=UTC)  # 10 min later
    await s.tick(t2)  # fires again
    assert len(fired) == 2


# --- Callback error handling ---


async def test_tick_callback_error_logged():
    async def bad_cb(persona_id: str, message: str, job_name: str) -> None:
        raise RuntimeError("oops")

    s = CronScheduler(callback=bad_cb)
    s.add_job(CronJob(
        name="j", cron="* * * * *", persona_id="p", message="m",
    ))
    await s.start()
    result = await s.tick()
    assert result == ["j"]  # still reported as fired


async def test_tick_no_callback_still_works():
    s = CronScheduler()
    s.add_job(CronJob(
        name="j", cron="* * * * *", persona_id="p", message="m",
    ))
    await s.start()
    result = await s.tick()
    assert result == ["j"]
