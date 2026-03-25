from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ModelConfig(BaseModel, frozen=True):
    provider: Literal[
        "anthropic", "openai", "google", "azure", "ollama", "custom"
    ] = "anthropic"
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.3
    max_tokens: int = 4096
    top_p: float | None = None
    api_key_env: str | None = None
    base_url: str | None = None
    extra_params: dict[str, Any] = {}
