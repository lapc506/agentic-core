from __future__ import annotations

import fnmatch
from dataclasses import dataclass


@dataclass
class RoutingRule:
    channel_pattern: str  # glob pattern or exact match
    persona_id: str
    priority: int = 0


class PersonaRouter:
    """Routes incoming messages to the appropriate agent persona.

    Resolution order:
    1. Explicit ``persona_id`` passed directly in the call (highest priority).
    2. Channel-based rules matched against ``channel``, sorted by descending
       priority so that more-specific rules win.
    3. Keyword-based rules matched against the lowercased message ``content``.
    4. The configured default persona (lowest priority / fallback).
    """

    def __init__(self) -> None:
        self._channel_rules: list[RoutingRule] = []
        self._keyword_rules: dict[str, str] = {}  # keyword -> persona_id
        self._default_persona: str = "default"

    def add_channel_rule(self, pattern: str, persona_id: str, priority: int = 0) -> None:
        """Register a channel routing rule.

        ``pattern`` is matched with :func:`fnmatch.fnmatch` (case-insensitive),
        so both exact names (``"#support"``) and globs (``"#sales-*"``) work.
        Rules are kept sorted by *descending* priority so the highest-priority
        match wins during :meth:`route`.
        """
        self._channel_rules.append(RoutingRule(pattern, persona_id, priority))
        self._channel_rules.sort(key=lambda r: r.priority, reverse=True)

    def add_keyword_rule(self, keyword: str, persona_id: str) -> None:
        """Register a keyword → persona mapping used as a content-based fallback."""
        self._keyword_rules[keyword.lower()] = persona_id

    def set_default(self, persona_id: str) -> None:
        """Set the persona returned when no other rule matches."""
        self._default_persona = persona_id

    def route(
        self,
        channel: str | None = None,
        content: str = "",
        explicit_persona: str | None = None,
    ) -> str:
        """Return the persona ID that should handle this message.

        Args:
            channel: The channel name/identifier (e.g. ``"#support"``).
            content: Raw message text used for keyword matching.
            explicit_persona: When provided this value is returned immediately,
                overriding all other rules.

        Returns:
            The resolved persona ID string.
        """
        # 1. Explicit override – highest precedence
        if explicit_persona:
            return explicit_persona

        # 2. Channel-based routing (rules already sorted by descending priority)
        if channel:
            for rule in self._channel_rules:
                if self._matches(rule.channel_pattern, channel):
                    return rule.persona_id

        # 3. Keyword-based fallback
        content_lower = content.lower()
        for keyword, persona_id in self._keyword_rules.items():
            if keyword in content_lower:
                return persona_id

        # 4. Default
        return self._default_persona

    @staticmethod
    def _matches(pattern: str, value: str) -> bool:
        return fnmatch.fnmatch(value.lower(), pattern.lower())
