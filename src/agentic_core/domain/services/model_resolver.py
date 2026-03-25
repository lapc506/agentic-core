from __future__ import annotations

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
