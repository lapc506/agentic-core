from __future__ import annotations

from agentic_core.application.services.user_modeling import (
    CommunicationStyle,
    UserModelingService,
    UserPreference,
)


def test_create_default_profile() -> None:
    svc = UserModelingService()
    profile = svc.get_or_create("alice")
    assert profile.user_id == "alice"
    assert profile.interaction_count == 0
    assert profile.preferences == {}
    assert profile.style.formality == 0.5
    assert profile.style.verbosity == 0.5
    assert profile.style.technical_level == 0.5
    assert profile.style.language == "en"


def test_get_or_create_returns_same_profile() -> None:
    svc = UserModelingService()
    p1 = svc.get_or_create("bob")
    p2 = svc.get_or_create("bob")
    assert p1 is p2


def test_get_profile_existing() -> None:
    svc = UserModelingService()
    svc.get_or_create("alice")
    assert svc.get_profile("alice") is not None


def test_get_profile_unknown_returns_none() -> None:
    svc = UserModelingService()
    assert svc.get_profile("unknown") is None


def test_observe_preference_creates_new() -> None:
    svc = UserModelingService()
    svc.observe_preference("alice", "editor", "vim")
    profile = svc.get_profile("alice")
    assert profile is not None
    assert "editor" in profile.preferences
    pref = profile.preferences["editor"]
    assert pref.value == "vim"
    assert pref.confidence == 0.5
    assert pref.observed_count == 1


def test_observe_preference_confidence_increases() -> None:
    svc = UserModelingService()
    svc.observe_preference("alice", "editor", "vim")
    initial_conf = svc.get_profile("alice")
    assert initial_conf is not None
    c0 = initial_conf.preferences["editor"].confidence

    svc.observe_preference("alice", "editor", "vim")
    updated = svc.get_profile("alice")
    assert updated is not None
    c1 = updated.preferences["editor"].confidence

    assert c1 > c0
    assert updated.preferences["editor"].observed_count == 2


def test_observe_preference_value_change_resets_confidence() -> None:
    svc = UserModelingService()
    # Build up confidence
    for _ in range(5):
        svc.observe_preference("alice", "editor", "vim")

    profile = svc.get_profile("alice")
    assert profile is not None
    high_conf = profile.preferences["editor"].confidence
    assert high_conf > 0.5

    # Change value: confidence resets
    svc.observe_preference("alice", "editor", "emacs")
    profile = svc.get_profile("alice")
    assert profile is not None
    assert profile.preferences["editor"].value == "emacs"
    assert profile.preferences["editor"].confidence == 0.5
    assert profile.preferences["editor"].observed_count == 1


def test_observe_preference_increments_interaction_count() -> None:
    svc = UserModelingService()
    svc.observe_preference("alice", "theme", "dark")
    svc.observe_preference("alice", "theme", "dark")
    profile = svc.get_profile("alice")
    assert profile is not None
    assert profile.interaction_count == 2


def test_observe_style_running_average() -> None:
    svc = UserModelingService()
    svc.get_or_create("alice")
    # Default formality is 0.5; observe 1.0
    svc.observe_style("alice", formality=1.0)
    profile = svc.get_profile("alice")
    assert profile is not None
    # Running average: 0.5 * (1/2) + 1.0 * (1/2) = 0.75
    assert abs(profile.style.formality - 0.75) < 0.01


def test_observe_style_partial_update() -> None:
    svc = UserModelingService()
    svc.get_or_create("alice")
    svc.observe_style("alice", verbosity=0.9)
    profile = svc.get_profile("alice")
    assert profile is not None
    # Only verbosity should change; formality stays at 0.5
    assert profile.style.formality == 0.5
    assert profile.style.verbosity != 0.5


def test_observe_style_increments_interaction_count() -> None:
    svc = UserModelingService()
    svc.get_or_create("alice")
    svc.observe_style("alice", formality=0.8)
    svc.observe_style("alice", formality=0.8)
    profile = svc.get_profile("alice")
    assert profile is not None
    assert profile.interaction_count == 2


def test_adaptation_hints_casual() -> None:
    svc = UserModelingService()
    profile = svc.get_or_create("alice")
    profile.style = CommunicationStyle(
        formality=0.1, verbosity=0.1, technical_level=0.1,
    )
    hints = svc.get_adaptation_hints("alice")
    assert hints["tone"] == "casual and friendly"
    assert hints["length"] == "concise, brief responses"
    assert hints["technical"] == "simple language, avoid jargon"


def test_adaptation_hints_formal() -> None:
    svc = UserModelingService()
    profile = svc.get_or_create("alice")
    profile.style = CommunicationStyle(
        formality=0.9, verbosity=0.9, technical_level=0.9,
    )
    hints = svc.get_adaptation_hints("alice")
    assert hints["tone"] == "formal and professional"
    assert hints["length"] == "detailed, thorough explanations"
    assert hints["technical"] == "technical language, include implementation details"


def test_adaptation_hints_includes_high_confidence_preferences() -> None:
    svc = UserModelingService()
    svc.get_or_create("alice")
    # Observe many times to build high confidence
    for _ in range(20):
        svc.observe_preference("alice", "theme", "dark")

    profile = svc.get_profile("alice")
    assert profile is not None
    assert profile.preferences["theme"].confidence >= 0.7

    hints = svc.get_adaptation_hints("alice")
    assert hints.get("preference:theme") == "dark"


def test_adaptation_hints_unknown_user_returns_empty() -> None:
    svc = UserModelingService()
    hints = svc.get_adaptation_hints("nonexistent")
    assert hints == {}


def test_multiple_users_isolated() -> None:
    svc = UserModelingService()
    svc.observe_preference("alice", "editor", "vim")
    svc.observe_preference("bob", "editor", "emacs")

    alice = svc.get_profile("alice")
    bob = svc.get_profile("bob")
    assert alice is not None
    assert bob is not None
    assert alice.preferences["editor"].value == "vim"
    assert bob.preferences["editor"].value == "emacs"


def test_user_preference_frozen() -> None:
    pref = UserPreference(key="k", value="v")
    try:
        pref.key = "other"  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except Exception:
        pass


def test_communication_style_frozen() -> None:
    style = CommunicationStyle()
    try:
        style.formality = 0.9  # type: ignore[misc]
        raise AssertionError("Should have raised")
    except Exception:
        pass
