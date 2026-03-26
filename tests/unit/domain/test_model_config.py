import pytest

from agentic_core.domain.value_objects.model_config import MODEL_ALIASES, ModelConfig


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


# --- Fallback chain tests (#63) ---


def test_no_fallback_by_default():
    mc = ModelConfig()
    assert mc.fallback == ()


def test_fallback_chain_single():
    fb = ModelConfig(provider="google", model="gemini-2.5-pro")
    mc = ModelConfig(fallback=(fb,))
    chain = mc.fallback_chain()
    assert len(chain) == 2
    assert chain[0].model == "claude-sonnet-4-6"
    assert chain[1].model == "gemini-2.5-pro"


def test_fallback_chain_multiple():
    fb1 = ModelConfig(provider="google", model="gemini-2.5-pro")
    fb2 = ModelConfig(provider="ollama", model="llama3.3")
    mc = ModelConfig(
        model="claude-opus-4-6",
        fallback=(fb1, fb2),
    )
    chain = mc.fallback_chain()
    assert len(chain) == 3
    assert chain[0].model == "claude-opus-4-6"
    assert chain[1].model == "gemini-2.5-pro"
    assert chain[2].model == "llama3.3"


def test_fallback_chain_no_fallbacks():
    mc = ModelConfig()
    chain = mc.fallback_chain()
    assert chain == [mc]


# --- Model alias tests (#63) ---


def test_alias_fast():
    mc = ModelConfig(model="fast")
    assert mc.provider == "anthropic"
    assert mc.model == "claude-haiku-4-5"


def test_alias_smart():
    mc = ModelConfig(model="smart")
    assert mc.provider == "anthropic"
    assert mc.model == "claude-opus-4-6"


def test_alias_cheap():
    mc = ModelConfig(model="cheap")
    assert mc.provider == "google"
    assert mc.model == "gemini-2.5-flash"


def test_alias_local():
    mc = ModelConfig(model="local")
    assert mc.provider == "ollama"
    assert mc.model == "llama3.3"


def test_non_alias_unchanged():
    mc = ModelConfig(model="claude-sonnet-4-6")
    assert mc.model == "claude-sonnet-4-6"


def test_aliases_dict_has_expected_keys():
    expected = {"fast", "balanced", "smart", "cheap", "powerful", "local"}
    assert set(MODEL_ALIASES.keys()) == expected


def test_alias_in_fallback():
    mc = ModelConfig(
        model="smart",
        fallback=(ModelConfig(model="cheap"),),
    )
    chain = mc.fallback_chain()
    assert chain[0].model == "claude-opus-4-6"
    assert chain[1].provider == "google"
    assert chain[1].model == "gemini-2.5-flash"
