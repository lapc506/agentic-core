from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentic_core.domain.value_objects.model_config import ModelConfig


class MCPToolFilter(BaseModel):
    """Per-server tool filtering: include/exclude lists + prompt/resource toggles."""
    include: list[str] = []
    exclude: list[str] = []
    prompts: bool = True
    resources: bool = True


class MCPServerEntry(BaseModel):
    transport: Literal["stdio", "sse", "streamable-http"]
    command: str | None = None
    args: list[str] = []
    url: str | None = None
    headers: dict[str, str] = {}
    env: dict[str, str] = {}
    description: str = ""
    keywords: list[str] = []
    tools: MCPToolFilter = MCPToolFilter()


class MCPBridgeConfig(BaseModel):
    mode: Literal["direct", "router"] = "direct"
    servers: dict[str, MCPServerEntry] = {}
    tool_prefix: bool = True
    reconnect_interval_ms: int = 30_000
    connection_timeout_ms: int = 10_000
    request_timeout_ms: int = 60_000


class ObservabilitySettings(BaseModel):
    otel_endpoint: str | None = "http://otel-collector:4317"
    otel_sample_rate: float = 1.0
    otel_export_protocol: Literal["grpc", "http"] = "grpc"
    prometheus_port: int = 9090
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    alertmanager_url: str | None = None
    log_format: Literal["json", "console"] = "json"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


class EmbeddingProviderSettings(BaseModel):
    provider: Literal["gemini", "openai", "local"] = "gemini"
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "gemini-embedding-2-preview"
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-large"
    local_model_name: str = "all-MiniLM-L6-v2"
    embedding_dimensions: int = 768


class AgenticSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTIC_", env_nested_delimiter="__")

    mode: Literal["sidecar", "standalone"] = "standalone"

    # Transport
    ws_host: str = "0.0.0.0"
    ws_port: int = 8765
    grpc_host: str = "0.0.0.0"
    grpc_port: int = 50051

    # Memory stores (required)
    redis_url: str = "redis://localhost:6379"
    postgres_dsn: str = "postgresql://localhost:5432/agentic"
    falkordb_url: str = "redis://localhost:6380"

    # Security
    rate_limit_rpm: int = 60
    pii_redaction_enabled: bool = True

    # Personas
    personas_dir: str = "agents/"

    # Sub-configs
    default_model: ModelConfig = ModelConfig()
    mcp: MCPBridgeConfig = MCPBridgeConfig()
    observability: ObservabilitySettings = ObservabilitySettings()
    embedding: EmbeddingProviderSettings = EmbeddingProviderSettings()

    @model_validator(mode="after")
    def _sidecar_host_override(self) -> AgenticSettings:
        if self.mode == "sidecar":
            object.__setattr__(self, "ws_host", "127.0.0.1")
            object.__setattr__(self, "grpc_host", "127.0.0.1")
        return self
