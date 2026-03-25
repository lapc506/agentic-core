import os
from unittest.mock import patch

from agentic_core.config.settings import AgenticSettings


def test_defaults():
    s = AgenticSettings()
    assert s.mode == "standalone"
    assert s.ws_host == "0.0.0.0"
    assert s.grpc_host == "0.0.0.0"
    assert s.ws_port == 8765
    assert s.grpc_port == 50051
    assert s.default_model.model == "claude-sonnet-4-6"


def test_sidecar_overrides_hosts():
    s = AgenticSettings(mode="sidecar")
    assert s.ws_host == "127.0.0.1"
    assert s.grpc_host == "127.0.0.1"


def test_standalone_keeps_hosts():
    s = AgenticSettings(mode="standalone", ws_host="10.0.0.1", grpc_host="10.0.0.2")
    assert s.ws_host == "10.0.0.1"
    assert s.grpc_host == "10.0.0.2"


def test_env_var_loading():
    env = {
        "AGENTIC_MODE": "sidecar",
        "AGENTIC_WS_PORT": "9000",
        "AGENTIC_REDIS_URL": "redis://custom:6379",
    }
    with patch.dict(os.environ, env, clear=False):
        s = AgenticSettings()
    assert s.mode == "sidecar"
    assert s.ws_port == 9000
    assert s.redis_url == "redis://custom:6379"
    assert s.ws_host == "127.0.0.1"  # sidecar override


def test_mcp_config_defaults():
    s = AgenticSettings()
    assert s.mcp.mode == "direct"
    assert s.mcp.servers == {}
    assert s.mcp.tool_prefix is True


def test_observability_defaults():
    s = AgenticSettings()
    assert s.observability.log_format == "json"
    assert s.observability.otel_sample_rate == 1.0


def test_embedding_defaults():
    s = AgenticSettings()
    assert s.embedding.provider == "gemini"
    assert s.embedding.embedding_dimensions == 768
