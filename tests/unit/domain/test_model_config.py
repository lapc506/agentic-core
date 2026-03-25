import pytest

from agentic_core.domain.value_objects.model_config import ModelConfig


def test_defaults():
    mc = ModelConfig()
    assert mc.provider == "anthropic"
    assert mc.model == "claude-sonnet-4-6"
    assert mc.temperature == 0.3
    assert mc.max_tokens == 4096


def test_custom_provider():
    mc = ModelConfig(provider="google", model="gemini-2.5-pro", temperature=0.2)
    assert mc.provider == "google"
    assert mc.model == "gemini-2.5-pro"


def test_invalid_provider_rejected():
    with pytest.raises(Exception):
        ModelConfig(provider="invalid_provider")  # type: ignore[arg-type]


def test_frozen():
    mc = ModelConfig()
    with pytest.raises(Exception):
        mc.model = "changed"  # type: ignore[misc]


def test_api_key_env():
    mc = ModelConfig(api_key_env="ANTHROPIC_API_KEY_PREMIUM")
    assert mc.api_key_env == "ANTHROPIC_API_KEY_PREMIUM"


def test_extra_params():
    mc = ModelConfig(extra_params={"thinking_budget": 10000})
    assert mc.extra_params["thinking_budget"] == 10000
