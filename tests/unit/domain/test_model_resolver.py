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


# --- resolve_with_fallbacks tests (#63) ---


def test_resolve_with_fallbacks_no_fallback():
    default = ModelConfig(model="claude-sonnet-4-6")
    resolver = ModelResolver(default)
    chain = list(resolver.resolve_with_fallbacks())
    assert len(chain) == 1
    assert chain[0].model == "claude-sonnet-4-6"


def test_resolve_with_fallbacks_persona_with_chain():
    default = ModelConfig(model="claude-sonnet-4-6")
    fb = ModelConfig(provider="google", model="gemini-2.5-pro")
    persona = ModelConfig(model="claude-opus-4-6", fallback=(fb,))
    resolver = ModelResolver(default)
    chain = list(resolver.resolve_with_fallbacks(persona_model=persona))
    assert len(chain) == 2
    assert chain[0].model == "claude-opus-4-6"
    assert chain[1].model == "gemini-2.5-pro"


def test_resolve_with_fallbacks_subagent_overrides():
    default = ModelConfig(model="claude-sonnet-4-6")
    persona = ModelConfig(model="claude-opus-4-6")
    fb = ModelConfig(provider="ollama", model="llama3.3")
    subagent = ModelConfig(model="claude-haiku-4-5", fallback=(fb,))
    resolver = ModelResolver(default)
    chain = list(resolver.resolve_with_fallbacks(
        persona_model=persona, subagent_model=subagent,
    ))
    assert len(chain) == 2
    assert chain[0].model == "claude-haiku-4-5"
    assert chain[1].model == "llama3.3"


def test_resolve_with_fallbacks_runtime_default_chain():
    fb1 = ModelConfig(provider="google", model="gemini-2.5-pro")
    fb2 = ModelConfig(provider="ollama", model="llama3.3")
    default = ModelConfig(
        model="claude-sonnet-4-6", fallback=(fb1, fb2),
    )
    resolver = ModelResolver(default)
    chain = list(resolver.resolve_with_fallbacks())
    assert len(chain) == 3
    assert [c.model for c in chain] == [
        "claude-sonnet-4-6", "gemini-2.5-pro", "llama3.3",
    ]
