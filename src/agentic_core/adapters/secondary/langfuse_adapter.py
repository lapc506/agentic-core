from __future__ import annotations

import logging
from typing import Any

from agentic_core.application.ports.cost_tracking import CostTrackingPort
from agentic_core.config.settings import ObservabilitySettings

logger = logging.getLogger(__name__)


class LangfuseAdapter(CostTrackingPort):
    """Langfuse integration for LLM cost tracking + generation tracing.
    Gracefully degrades to no-op when Langfuse SDK is not installed."""

    def __init__(self, settings: ObservabilitySettings) -> None:
        self._settings = settings
        self._client: Any = None
        self._initialized = False

    def initialize(self) -> None:
        try:
            from langfuse import Langfuse
            self._client = Langfuse(
                public_key=self._settings.langfuse_public_key,
                secret_key=self._settings.langfuse_secret_key,
                host=self._settings.langfuse_host,
            )
            self._initialized = True
            logger.info("Langfuse initialized: host=%s", self._settings.langfuse_host)
        except (ImportError, Exception) as e:
            logger.info("Langfuse not available: %s", e)

    async def record_generation(
        self, model: str, input_tokens: int, output_tokens: int, metadata: dict[str, Any],
    ) -> None:
        if self._client is None:
            return
        self._client.generation(
            name=metadata.get("node_name", "llm_call"),
            model=model,
            usage={"input": input_tokens, "output": output_tokens},
            metadata={
                "persona_id": metadata.get("persona_id", ""),
                "session_id": metadata.get("session_id", ""),
                "trace_id": metadata.get("trace_id"),
            },
        )

    def flush(self) -> None:
        if self._client is not None:
            self._client.flush()
