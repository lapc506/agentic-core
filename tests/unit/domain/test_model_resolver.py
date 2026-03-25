from agentic_core.domain.services.model_resolver import ModelResolver
from agentic_core.domain.value_objects.model_config import ModelConfig


def test_returns_runtime_default():
    default = ModelConfig(model="claude-sonnet-4-6")
    resolver = ModelResolver(default)
    result = resolver.resolve()
    assert result.model == "claude-sonnet-4-6"


def test_persona_overrides_runtime():
    default = ModelConfig(model="claude-sonnet-4-6")
    persona = ModelConfig(model="claude-opus-4-6")
    resolver = ModelResolver(default)
    result = resolver.resolve(persona_model=persona)
    assert result.model == "claude-opus-4-6"


def test_subagent_overrides_persona():
    default = ModelConfig(model="claude-sonnet-4-6")
    persona = ModelConfig(model="claude-opus-4-6")
    subagent = ModelConfig(model="claude-haiku-4-5")
    resolver = ModelResolver(default)
    result = resolver.resolve(persona_model=persona, subagent_model=subagent)
    assert result.model == "claude-haiku-4-5"


def test_subagent_overrides_runtime_directly():
    default = ModelConfig(model="claude-sonnet-4-6")
    subagent = ModelConfig(provider="google", model="gemini-2.5-pro")
    resolver = ModelResolver(default)
    result = resolver.resolve(subagent_model=subagent)
    assert result.provider == "google"
    assert result.model == "gemini-2.5-pro"
