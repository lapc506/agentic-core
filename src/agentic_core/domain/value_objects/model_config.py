from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_validator

ProviderType = Literal[
    "anthropic", "openai", "google", "azure", "ollama", "custom"
]

MODEL_ALIASES: dict[str, tuple[ProviderType, str]] = {
    "fast": ("anthropic", "claude-haiku-4-5"),
    "balanced": ("anthropic", "claude-sonnet-4-6"),
    "smart": ("anthropic", "claude-opus-4-6"),
    "cheap": ("google", "gemini-2.5-flash"),
    "powerful": ("google", "gemini-2.5-pro"),
    "local": ("ollama", "llama3.3"),
}


class ModelConfig(BaseModel, frozen=True):
    provider: ProviderType = "anthropic"
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.3
    max_tokens: int = 4096
    top_p: float | None = None
    api_key_env: str | None = None
    base_url: str | None = None
    extra_params: dict[str, Any] = {}
    fallback: tuple[ModelConfig, ...] = ()

    @model_validator(mode="after")
    def _resolve_alias(self) -> ModelConfig:
        if self.model in MODEL_ALIASES:
            provider, model = MODEL_ALIASES[self.model]
            object.__setattr__(self, "provider", provider)
            object.__setattr__(self, "model", model)
        return self

    def fallback_chain(self) -> list[ModelConfig]:
        """Return ordered list: primary first, then all fallbacks."""
        return [self, *self.fallback]
