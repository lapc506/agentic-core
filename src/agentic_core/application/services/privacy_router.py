"""Privacy router -- routes data to local vs cloud models based on sensitivity."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RoutingDecision(str, Enum):
    LOCAL = "local"  # Process with local model (Ollama, LMStudio)
    CLOUD = "cloud"  # Process with cloud model (OpenRouter, Anthropic)
    BLOCKED = "blocked"  # Do not process


@dataclass
class RoutingResult:
    decision: RoutingDecision
    model: str
    reason: str
    sensitivity: DataSensitivity


class PrivacyRouter:
    """Routes inference requests based on data sensitivity policy.

    The SYSTEM (not the agent) decides which model processes which data.
    This is an infrastructure concern, not an application concern.
    """

    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = {
        DataSensitivity.RESTRICTED: [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
            r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",  # Private keys
        ],
        DataSensitivity.CONFIDENTIAL: [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"password\s*[=:]\s*\S+",  # Password in config
            r"(api[_-]?key|secret|token)\s*[=:]\s*\S+",  # API keys
        ],
        DataSensitivity.INTERNAL: [
            r"\b(?:192\.168|10\.|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+\b",  # Internal IPs
            r"https?://(?:localhost|127\.0\.0\.1)",  # Localhost URLs
        ],
    }

    def __init__(
        self,
        local_model: str = "ollama/llama3.1",
        cloud_model: str = "openrouter/default",
    ) -> None:
        self._local = local_model
        self._cloud = cloud_model
        self._policy: dict[DataSensitivity, RoutingDecision] = {
            DataSensitivity.PUBLIC: RoutingDecision.CLOUD,
            DataSensitivity.INTERNAL: RoutingDecision.CLOUD,
            DataSensitivity.CONFIDENTIAL: RoutingDecision.LOCAL,
            DataSensitivity.RESTRICTED: RoutingDecision.BLOCKED,
        }

    def classify(self, content: str) -> DataSensitivity:
        """Classify data sensitivity level."""
        for level in [
            DataSensitivity.RESTRICTED,
            DataSensitivity.CONFIDENTIAL,
            DataSensitivity.INTERNAL,
        ]:
            patterns = self.SENSITIVE_PATTERNS.get(level, [])
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    return level
        return DataSensitivity.PUBLIC

    def route(self, content: str) -> RoutingResult:
        """Route content to appropriate model based on sensitivity."""
        sensitivity = self.classify(content)
        decision = self._policy.get(sensitivity, RoutingDecision.LOCAL)

        if decision == RoutingDecision.LOCAL:
            model = self._local
            reason = f"Data classified as {sensitivity.value} -- routing to local model"
        elif decision == RoutingDecision.CLOUD:
            model = self._cloud
            reason = f"Data classified as {sensitivity.value} -- routing to cloud model"
        else:
            model = ""
            reason = f"Data classified as {sensitivity.value} -- blocked by policy"

        logger.info(
            "Privacy routing: %s -> %s (%s)",
            sensitivity.value,
            decision.value,
            model,
        )
        return RoutingResult(
            decision=decision,
            model=model,
            reason=reason,
            sensitivity=sensitivity,
        )

    def set_policy(
        self,
        sensitivity: DataSensitivity,
        decision: RoutingDecision,
    ) -> None:
        self._policy[sensitivity] = decision

    def set_models(
        self,
        local: str | None = None,
        cloud: str | None = None,
    ) -> None:
        if local:
            self._local = local
        if cloud:
            self._cloud = cloud
