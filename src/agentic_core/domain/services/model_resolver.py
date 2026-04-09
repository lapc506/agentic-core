from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from agentic_core.domain.value_objects.model_config import ModelConfig


class ModelResolver:
    """Resolves effective ModelConfig using 3-level cascade:
    sub-agent -> persona -> runtime default."""

    def __init__(self, runtime_default: ModelConfig) -> None:
        self._runtime_default = runtime_default

    def resolve(
        self,
        persona_model: ModelConfig | None = None,
        subagent_model: ModelConfig | None = None,
    ) -> ModelConfig:
        if subagent_model is not None:
            return subagent_model
        if persona_model is not None:
            return persona_model
        return self._runtime_default

    def resolve_with_fallbacks(
        self,
        persona_model: ModelConfig | None = None,
        subagent_model: ModelConfig | None = None,
    ) -> Iterator[ModelConfig]:
        """Yield the resolved primary config, then its fallbacks in order.

        Usage:
            for config in resolver.resolve_with_fallbacks(persona_model=pm):
                try:
                    return await call_llm(config)
                except (RateLimitError, UnavailableError):
                    continue
            raise AllModelsExhaustedError()
        """
        primary = self.resolve(persona_model, subagent_model)
        yield from primary.fallback_chain()
