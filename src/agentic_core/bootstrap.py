"""Bootstrap -- wires all adapters and services into the runtime.

Each ``_init_*`` helper follows the same contract:
- Try to import and construct the real adapter / service.
- On success, register it in the ``ServiceRegistry``.
- On *any* failure (missing dependency, bad config, connectivity),
  log an informational message and continue. The runtime still starts
  with whatever subset of services is available (graceful degradation).
"""

from __future__ import annotations

import logging
from typing import Any

from agentic_core.config.settings import AgenticSettings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ServiceRegistry
# ---------------------------------------------------------------------------


class ServiceRegistry:
    """Central registry of all initialised services and adapters."""

    def __init__(self, settings: AgenticSettings) -> None:
        self.settings = settings
        self._services: dict[str, Any] = {}

    def get(self, name: str) -> Any:
        return self._services.get(name)

    def register(self, name: str, service: Any) -> None:
        self._services[name] = service
        logger.info("Service registered: %s", name)

    @property
    def registered(self) -> list[str]:
        return list(self._services.keys())


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


async def bootstrap(settings: AgenticSettings) -> ServiceRegistry:
    """Initialise all services based on configuration.

    Gracefully degrades: if a dependency is unavailable, skip that
    service and log a warning.
    """
    registry = ServiceRegistry(settings)

    # --- Priority 1: Observability ---
    _init_langfuse(registry, settings)
    _init_otel(registry, settings)

    # --- Priority 2: Storage ---
    await _init_redis(registry, settings)
    await _init_postgres(registry, settings)
    await _init_pgvector(registry, settings)
    await _init_falkordb(registry, settings)

    # --- Priority 3: Intelligence ---
    _init_persona_registry(registry, settings)
    _init_memory(registry, settings)
    _init_policy(registry, settings)
    _init_tools(registry, settings)

    # --- Priority 4: Security ---
    _init_security(registry, settings)

    logger.info(
        "Bootstrap complete: %d services registered", len(registry.registered),
    )
    return registry


# ---------------------------------------------------------------------------
# Priority 1 -- Observability
# ---------------------------------------------------------------------------


def _init_langfuse(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.adapters.secondary.langfuse_adapter import LangfuseAdapter

        adapter = LangfuseAdapter(settings.observability)
        adapter.initialize()
        registry.register("langfuse", adapter)
    except Exception as exc:  # noqa: BLE001
        logger.info("Langfuse not available: %s", exc)


def _init_otel(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.adapters.secondary.otel_adapter import OTelAdapter

        adapter = OTelAdapter(settings.observability)
        adapter.initialize()
        registry.register("otel", adapter)
    except Exception as exc:  # noqa: BLE001
        logger.info("OpenTelemetry not available: %s", exc)


# ---------------------------------------------------------------------------
# Priority 2 -- Storage
# ---------------------------------------------------------------------------


async def _init_redis(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.adapters.secondary.redis_adapter import RedisAdapter

        adapter = RedisAdapter(settings.redis_url)
        await adapter.connect()
        registry.register("redis", adapter)
        registry.register("memory_port", adapter)
    except Exception as exc:  # noqa: BLE001
        logger.info("Redis not available: %s", exc)


async def _init_postgres(
    registry: ServiceRegistry, settings: AgenticSettings,
) -> None:
    try:
        from agentic_core.adapters.secondary.postgres_adapter import PostgresAdapter

        adapter = PostgresAdapter(settings.postgres_dsn)
        await adapter.connect()
        registry.register("postgres", adapter)
        registry.register("session_port", adapter)
    except Exception as exc:  # noqa: BLE001
        logger.info("PostgreSQL not available: %s", exc)


async def _init_pgvector(
    registry: ServiceRegistry, settings: AgenticSettings,
) -> None:
    try:
        from agentic_core.adapters.secondary.pgvector_adapter import PgVectorAdapter

        adapter = PgVectorAdapter(settings.postgres_dsn)
        await adapter.connect()
        # Ensure the table uses the dimension from embedding settings
        await adapter.ensure_dimensions(settings.embedding.embedding_dimensions)
        registry.register("pgvector", adapter)
        registry.register("embedding_store_port", adapter)
    except Exception as exc:  # noqa: BLE001
        logger.info("pgvector not available: %s", exc)


async def _init_falkordb(
    registry: ServiceRegistry, settings: AgenticSettings,
) -> None:
    try:
        from agentic_core.adapters.secondary.falkordb_adapter import FalkorDBAdapter

        adapter = FalkorDBAdapter(settings.falkordb_url)
        await adapter.connect()
        registry.register("falkordb", adapter)
        registry.register("graph_store_port", adapter)
    except Exception as exc:  # noqa: BLE001
        logger.info("FalkorDB not available: %s", exc)


# ---------------------------------------------------------------------------
# Priority 3 -- Intelligence
# ---------------------------------------------------------------------------


def _init_persona_registry(
    registry: ServiceRegistry, settings: AgenticSettings,
) -> None:
    try:
        from agentic_core.application.services.persona_registry import PersonaRegistry
        from agentic_core.domain.services.routing import RoutingService

        # Re-use a shared RoutingService if the runtime already created one;
        # otherwise create a fresh instance.
        routing: RoutingService = registry.get("routing_service") or RoutingService()
        reg = PersonaRegistry(routing)
        count = reg.discover(settings.personas_dir)
        registry.register("persona_registry", reg)
        registry.register("routing_service", routing)
        logger.info("PersonaRegistry loaded %d personas", count)
    except Exception as exc:  # noqa: BLE001
        logger.info("PersonaRegistry init failed: %s", exc)


def _init_memory(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.application.services.memory_extraction import (
            MemoryExtractionService,
        )
        from agentic_core.application.services.memory_manager import MemoryManager

        graph = registry.get("graph_store_port")
        vector = registry.get("embedding_store_port")
        extraction = MemoryExtractionService()
        manager = MemoryManager(
            graph_store=graph,
            vector_store=vector,
            memory_service=extraction,
        )

        registry.register("memory_extraction", extraction)
        registry.register("memory_manager", manager)
    except Exception as exc:  # noqa: BLE001
        logger.info("Memory services init failed: %s", exc)


def _init_policy(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.application.services.context_budget import (
            ContextBudgetManager,
        )
        from agentic_core.application.services.iteration_budget import IterationBudget
        from agentic_core.application.services.policy_engine import PolicyEngine
        from agentic_core.application.services.tool_cache import ToolCache

        registry.register("policy_engine", PolicyEngine())
        registry.register("context_budget", ContextBudgetManager())
        registry.register("tool_cache", ToolCache())
        registry.register("iteration_budget", IterationBudget())
    except Exception as exc:  # noqa: BLE001
        logger.info("Policy/tool services init failed: %s", exc)


def _init_tools(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.application.services.skill_disclosure import (
            SkillDisclosureService,
        )
        from agentic_core.application.services.todo_tracker import TodoTracker
        from agentic_core.application.services.tool_views import ToolViewRegistry

        registry.register("tool_views", ToolViewRegistry())
        registry.register("skill_disclosure", SkillDisclosureService())
        registry.register("todo_tracker", TodoTracker())
    except Exception as exc:  # noqa: BLE001
        logger.info("Tool services init failed: %s", exc)


# ---------------------------------------------------------------------------
# Priority 4 -- Security
# ---------------------------------------------------------------------------


def _init_security(registry: ServiceRegistry, settings: AgenticSettings) -> None:
    try:
        from agentic_core.application.services.credential_vault import CredentialVault
        from agentic_core.application.services.network_egress import NetworkEgressPolicy
        from agentic_core.application.services.security_auditor import SecurityAuditor

        # Credential vault
        vault = CredentialVault()
        vault.load_from_env("AGENTIC_CRED_")
        registry.register("credential_vault", vault)

        # Network egress policy
        registry.register("network_egress", NetworkEgressPolicy())

        # Security audit on startup
        auditor = SecurityAuditor()
        findings = auditor.audit(
            {
                "mode": settings.mode,
                "ws_host": settings.ws_host,
                "rate_limit_rpm": settings.rate_limit_rpm,
                "pii_redaction_enabled": settings.pii_redaction_enabled,
                "allowed_origins": settings.allowed_origins,
            },
        )
        for finding in findings:
            logger.warning(
                "Security audit [%s]: %s -- %s",
                finding.severity.value,
                finding.message,
                finding.recommendation,
            )
        registry.register("security_auditor", auditor)
    except Exception as exc:  # noqa: BLE001
        logger.info("Security services init failed: %s", exc)
