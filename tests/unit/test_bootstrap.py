"""Tests for the bootstrap module -- ServiceRegistry and service wiring."""

from __future__ import annotations

import pytest

from agentic_core.bootstrap import ServiceRegistry, bootstrap
from agentic_core.config.settings import AgenticSettings


# ---------------------------------------------------------------------------
# ServiceRegistry unit tests
# ---------------------------------------------------------------------------


class TestServiceRegistry:
    def test_register_and_get(self) -> None:
        settings = AgenticSettings(ws_port=0, grpc_port=0)
        registry = ServiceRegistry(settings)

        registry.register("foo", "bar")
        assert registry.get("foo") == "bar"

    def test_get_missing_returns_none(self) -> None:
        settings = AgenticSettings(ws_port=0, grpc_port=0)
        registry = ServiceRegistry(settings)

        assert registry.get("nonexistent") is None

    def test_registered_lists_keys(self) -> None:
        settings = AgenticSettings(ws_port=0, grpc_port=0)
        registry = ServiceRegistry(settings)

        registry.register("a", 1)
        registry.register("b", 2)
        assert set(registry.registered) == {"a", "b"}

    def test_overwrite_service(self) -> None:
        settings = AgenticSettings(ws_port=0, grpc_port=0)
        registry = ServiceRegistry(settings)

        registry.register("svc", "old")
        registry.register("svc", "new")
        assert registry.get("svc") == "new"

    def test_settings_stored(self) -> None:
        settings = AgenticSettings(ws_port=0, grpc_port=0)
        registry = ServiceRegistry(settings)
        assert registry.settings is settings


# ---------------------------------------------------------------------------
# Bootstrap integration tests (no external services)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_with_no_external_services() -> None:
    """Bootstrap must succeed even when no external services are reachable.

    All storage adapters (Redis, Postgres, pgvector, FalkorDB) will fail
    to connect, but the remaining pure-Python services should still register.
    """
    settings = AgenticSettings(
        ws_port=0,
        grpc_port=0,
        redis_url="redis://localhost:1",
        postgres_dsn="postgresql://localhost:1/test",
        falkordb_url="redis://localhost:1",
    )
    registry = await bootstrap(settings)

    # Should NOT crash
    assert isinstance(registry, ServiceRegistry)

    # Storage adapters should be absent (no connectivity)
    assert registry.get("redis") is None
    assert registry.get("postgres") is None
    assert registry.get("pgvector") is None
    assert registry.get("falkordb") is None


@pytest.mark.asyncio
async def test_bootstrap_registers_intelligence_services() -> None:
    """Pure-Python intelligence services should always register."""
    settings = AgenticSettings(
        ws_port=0,
        grpc_port=0,
        redis_url="redis://localhost:1",
        postgres_dsn="postgresql://localhost:1/test",
        falkordb_url="redis://localhost:1",
    )
    registry = await bootstrap(settings)

    # Memory services (always available -- they accept None stores)
    assert registry.get("memory_extraction") is not None
    assert registry.get("memory_manager") is not None

    # Policy / tool services
    assert registry.get("policy_engine") is not None
    assert registry.get("context_budget") is not None
    assert registry.get("tool_cache") is not None
    assert registry.get("iteration_budget") is not None

    # Tool helpers
    assert registry.get("tool_views") is not None
    assert registry.get("skill_disclosure") is not None
    assert registry.get("todo_tracker") is not None


@pytest.mark.asyncio
async def test_bootstrap_registers_security_services() -> None:
    """Security services should always register."""
    settings = AgenticSettings(
        ws_port=0,
        grpc_port=0,
        redis_url="redis://localhost:1",
        postgres_dsn="postgresql://localhost:1/test",
        falkordb_url="redis://localhost:1",
    )
    registry = await bootstrap(settings)

    assert registry.get("credential_vault") is not None
    assert registry.get("network_egress") is not None
    assert registry.get("security_auditor") is not None


@pytest.mark.asyncio
async def test_security_audit_runs_on_startup() -> None:
    """The SecurityAuditor should have been invoked during bootstrap.

    We verify this indirectly: the auditor object is registered, and
    we can call audit() again without errors.
    """
    settings = AgenticSettings(
        ws_port=0,
        grpc_port=0,
        redis_url="redis://localhost:1",
        postgres_dsn="postgresql://localhost:1/test",
        falkordb_url="redis://localhost:1",
    )
    registry = await bootstrap(settings)

    auditor = registry.get("security_auditor")
    assert auditor is not None

    # audit() should be callable and return findings
    findings = auditor.audit(
        {
            "mode": settings.mode,
            "ws_host": settings.ws_host,
            "rate_limit_rpm": settings.rate_limit_rpm,
            "pii_redaction_enabled": settings.pii_redaction_enabled,
            "allowed_origins": settings.allowed_origins,
        },
    )
    assert isinstance(findings, list)
    # Default settings should trigger at least the "no allowed_origins" warning
    assert len(findings) > 0


@pytest.mark.asyncio
async def test_bootstrap_minimum_service_count() -> None:
    """Even with no external infra, a minimum set of services must register."""
    settings = AgenticSettings(
        ws_port=0,
        grpc_port=0,
        redis_url="redis://localhost:1",
        postgres_dsn="postgresql://localhost:1/test",
        falkordb_url="redis://localhost:1",
    )
    registry = await bootstrap(settings)

    # At minimum we expect the pure-Python services:
    # memory_extraction, memory_manager, policy_engine, context_budget,
    # tool_cache, iteration_budget, tool_views, skill_disclosure,
    # todo_tracker, credential_vault, network_egress, security_auditor
    # Plus persona_registry and routing_service (even if 0 personas loaded)
    assert len(registry.registered) >= 12
