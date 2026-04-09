from __future__ import annotations

import logging
from datetime import UTC, datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserPreference(BaseModel, frozen=True):
    """A single observed user preference with confidence tracking."""

    key: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    observed_count: int = Field(ge=1, default=1)
    last_observed: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CommunicationStyle(BaseModel, frozen=True):
    """Communication style dimensions, each on a 0-1 scale."""

    formality: float = Field(ge=0.0, le=1.0, default=0.5)
    verbosity: float = Field(ge=0.0, le=1.0, default=0.5)
    technical_level: float = Field(ge=0.0, le=1.0, default=0.5)
    language: str = "en"


class UserProfile(BaseModel):
    """Aggregate user profile with preferences and communication style."""

    user_id: str
    preferences: dict[str, UserPreference] = Field(default_factory=dict)
    style: CommunicationStyle = Field(default_factory=CommunicationStyle)
    interaction_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserModelingService:
    """Honcho-inspired dialectic user modeling service.

    Learns user preferences over time, tracks behavioral patterns,
    and adapts communication style. Profiles are stored in-memory
    (designed to be backed by FalkorDB knowledge graph later).
    """

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def get_or_create(self, user_id: str) -> UserProfile:
        """Return existing profile or create a new default one."""
        if user_id not in self._profiles:
            profile = UserProfile(user_id=user_id)
            self._profiles[user_id] = profile
            logger.info("Created new user profile: %s", user_id)
        return self._profiles[user_id]

    def observe_preference(self, user_id: str, key: str, value: str) -> None:
        """Observe a user preference, updating confidence via decay formula.

        Confidence increases with repeated observations, following:
        new_confidence = old_confidence + (1 - old_confidence) * decay_factor
        where decay_factor = 0.1 per observation.
        """
        profile = self.get_or_create(user_id)
        now = datetime.now(UTC)
        decay_factor = 0.1

        if key in profile.preferences:
            old = profile.preferences[key]
            if old.value == value:
                new_confidence = min(1.0, old.confidence + (1.0 - old.confidence) * decay_factor)
                profile.preferences[key] = UserPreference(
                    key=key,
                    value=value,
                    confidence=new_confidence,
                    observed_count=old.observed_count + 1,
                    last_observed=now,
                )
            else:
                # Value changed: reset with base confidence
                profile.preferences[key] = UserPreference(
                    key=key,
                    value=value,
                    confidence=0.5,
                    observed_count=1,
                    last_observed=now,
                )
        else:
            profile.preferences[key] = UserPreference(
                key=key,
                value=value,
                confidence=0.5,
                observed_count=1,
                last_observed=now,
            )

        profile.interaction_count += 1
        profile.updated_at = now

    def observe_style(
        self,
        user_id: str,
        formality: float | None = None,
        verbosity: float | None = None,
        technical_level: float | None = None,
    ) -> None:
        """Update communication style via running average.

        Each dimension is updated independently using:
        new = old * (n / (n+1)) + observed * (1 / (n+1))
        where n is the current interaction_count.
        """
        profile = self.get_or_create(user_id)
        now = datetime.now(UTC)
        n = max(profile.interaction_count, 1)
        weight_old = n / (n + 1)
        weight_new = 1.0 / (n + 1)

        old_style = profile.style
        new_formality = old_style.formality
        new_verbosity = old_style.verbosity
        new_technical = old_style.technical_level

        if formality is not None:
            new_formality = _clamp(old_style.formality * weight_old + formality * weight_new)
        if verbosity is not None:
            new_verbosity = _clamp(old_style.verbosity * weight_old + verbosity * weight_new)
        if technical_level is not None:
            new_technical = _clamp(old_style.technical_level * weight_old + technical_level * weight_new)

        profile.style = CommunicationStyle(
            formality=new_formality,
            verbosity=new_verbosity,
            technical_level=new_technical,
            language=old_style.language,
        )
        profile.interaction_count += 1
        profile.updated_at = now

    def get_profile(self, user_id: str) -> UserProfile | None:
        """Return profile if it exists, None otherwise."""
        return self._profiles.get(user_id)

    def get_adaptation_hints(self, user_id: str) -> dict[str, str]:
        """Return prompting hints based on the user's profile.

        These hints can be injected into system prompts to adapt
        the agent's communication style to the user.
        """
        profile = self._profiles.get(user_id)
        if profile is None:
            return {}

        hints: dict[str, str] = {}
        style = profile.style

        # Formality hints
        if style.formality < 0.3:
            hints["tone"] = "casual and friendly"
        elif style.formality > 0.7:
            hints["tone"] = "formal and professional"
        else:
            hints["tone"] = "balanced"

        # Verbosity hints
        if style.verbosity < 0.3:
            hints["length"] = "concise, brief responses"
        elif style.verbosity > 0.7:
            hints["length"] = "detailed, thorough explanations"
        else:
            hints["length"] = "moderate detail"

        # Technical level hints
        if style.technical_level < 0.3:
            hints["technical"] = "simple language, avoid jargon"
        elif style.technical_level > 0.7:
            hints["technical"] = "technical language, include implementation details"
        else:
            hints["technical"] = "moderate technical depth"

        # Language hint
        hints["language"] = style.language

        # High-confidence preference hints
        for pref in profile.preferences.values():
            if pref.confidence >= 0.7:
                hints[f"preference:{pref.key}"] = pref.value

        return hints


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))
