"""Inter-agent message authentication layer.

Wraps :class:`AgentCommsBus` with HMAC-SHA256 signing, replay prevention,
sender identity verification, trust-level gating, and content sanitization.

Security gap #2 in the agentic-core threat model.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

from agentic_core.application.services.agent_comms import (
    AgentCommsBus,
    AgentMessage,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_MESSAGE_AGE_SECONDS: float = 30.0
"""Messages older than this are rejected as potential replays."""

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\{\{.*?\}\}", re.DOTALL),          # template injection
    re.compile(r"<script[\s>]", re.IGNORECASE),     # XSS / script injection
    re.compile(r"__import__\s*\("),                  # Python code injection
    re.compile(r"eval\s*\("),                        # eval injection
    re.compile(r"exec\s*\("),                        # exec injection
    re.compile(r"os\.(system|popen|exec)", re.IGNORECASE),
    re.compile(r"subprocess\.", re.IGNORECASE),
    re.compile(r"IGNORE\s+(ALL\s+)?PREVIOUS\s+INSTRUCTIONS", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class TrustLevel(str, Enum):
    """Trust classification for inter-agent communication."""

    UNTRUSTED = "UNTRUSTED"
    VERIFIED = "VERIFIED"
    PRIVILEGED = "PRIVILEGED"


@dataclass(frozen=True)
class AgentIdentity:
    """Identity record for a registered agent."""

    agent_id: str
    public_key: str
    trust_level: TrustLevel = TrustLevel.UNTRUSTED


@dataclass(frozen=True)
class SignedMessage:
    """A cryptographically signed inter-agent message."""

    sender_id: str
    recipient_id: str
    content: str
    timestamp: float
    nonce: str
    signature: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def compute_signature(
    sender_id: str,
    recipient_id: str,
    content: str,
    timestamp: float,
    nonce: str,
    secret_key: str,
) -> str:
    """Compute HMAC-SHA256 over the canonical message fields."""
    payload = f"{sender_id}|{recipient_id}|{content}|{timestamp}|{nonce}"
    return hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def sanitize_content(content: str) -> str:
    """Strip known injection patterns from inter-agent message content.

    Returns the sanitized string. Patterns that match are replaced with
    ``[REDACTED]``.
    """
    result = content
    for pattern in _INJECTION_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def has_injection(content: str) -> bool:
    """Return *True* if *content* contains a known injection pattern."""
    return any(p.search(content) for p in _INJECTION_PATTERNS)


# ---------------------------------------------------------------------------
# Payload filter by trust level
# ---------------------------------------------------------------------------

# Fields that UNTRUSTED agents may include in message content.
_UNTRUSTED_MAX_LENGTH = 1024

# Fields that VERIFIED agents may include.
_VERIFIED_MAX_LENGTH = 8192


def filter_payload(content: str, trust_level: TrustLevel) -> str:
    """Truncate or reject payload based on the sender's trust level."""
    if trust_level == TrustLevel.PRIVILEGED:
        return content

    max_len = (
        _UNTRUSTED_MAX_LENGTH
        if trust_level == TrustLevel.UNTRUSTED
        else _VERIFIED_MAX_LENGTH
    )
    if len(content) > max_len:
        logger.warning(
            "Payload truncated for trust level %s (len=%d, max=%d)",
            trust_level.value,
            len(content),
            max_len,
        )
        return content[:max_len]
    return content


# ---------------------------------------------------------------------------
# SecureAgentComms
# ---------------------------------------------------------------------------


class SecureAgentComms:
    """Authenticated wrapper around :class:`AgentCommsBus`.

    All messages are signed with per-agent HMAC-SHA256 keys, checked for
    replay via nonce + timestamp, filtered by trust level, and sanitized
    before delivery.
    """

    def __init__(self, bus: AgentCommsBus) -> None:
        self._bus = bus
        self._identities: dict[str, AgentIdentity] = {}
        self._keys: dict[str, str] = {}  # agent_id -> HMAC secret
        self._seen_nonces: set[str] = set()

    # -- identity management ------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        secret_key: str,
        trust_level: TrustLevel = TrustLevel.UNTRUSTED,
    ) -> None:
        """Register an agent identity and its signing key."""
        if agent_id in self._identities:
            raise ValueError(f"Agent already registered: {agent_id}")
        self._identities[agent_id] = AgentIdentity(
            agent_id=agent_id,
            public_key=secret_key,
            trust_level=trust_level,
        )
        self._keys[agent_id] = secret_key
        self._bus.register(agent_id)
        logger.info(
            "Secure agent registered: %s (trust=%s)",
            agent_id,
            trust_level.value,
        )

    def get_identity(self, agent_id: str) -> AgentIdentity | None:
        """Look up the identity of a registered agent."""
        return self._identities.get(agent_id)

    # -- signing & verification --------------------------------------------

    def sign_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
    ) -> SignedMessage:
        """Create a :class:`SignedMessage` from the sender's key."""
        key = self._keys.get(sender_id)
        if key is None:
            raise KeyError(f"No signing key for agent: {sender_id}")

        ts = time.time()
        nonce = uuid.uuid4().hex
        sig = compute_signature(sender_id, recipient_id, content, ts, nonce, key)
        return SignedMessage(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            timestamp=ts,
            nonce=nonce,
            signature=sig,
        )

    def verify_message(self, msg: SignedMessage) -> bool:
        """Verify HMAC signature, timestamp freshness, and nonce uniqueness."""
        key = self._keys.get(msg.sender_id)
        if key is None:
            logger.warning("Unknown sender: %s", msg.sender_id)
            return False

        # Replay: timestamp freshness
        age = abs(time.time() - msg.timestamp)
        if age > MAX_MESSAGE_AGE_SECONDS:
            logger.warning(
                "Message too old (%.1fs) from %s", age, msg.sender_id,
            )
            return False

        # Replay: nonce uniqueness
        if msg.nonce in self._seen_nonces:
            logger.warning("Duplicate nonce from %s: %s", msg.sender_id, msg.nonce)
            return False

        # Signature check
        expected = compute_signature(
            msg.sender_id,
            msg.recipient_id,
            msg.content,
            msg.timestamp,
            msg.nonce,
            key,
        )
        if not hmac.compare_digest(expected, msg.signature):
            logger.warning("Bad signature from %s", msg.sender_id)
            return False

        # Record nonce
        self._seen_nonces.add(msg.nonce)
        return True

    # -- secure send / receive ---------------------------------------------

    async def send(self, signed_msg: SignedMessage) -> None:
        """Verify, sanitize, filter, and deliver *signed_msg*."""
        if not self.verify_message(signed_msg):
            raise PermissionError(
                f"Message authentication failed for sender {signed_msg.sender_id}",
            )

        identity = self._identities.get(signed_msg.sender_id)
        if identity is None:
            raise PermissionError(f"Unknown sender: {signed_msg.sender_id}")

        # Content sanitization
        clean_content = sanitize_content(signed_msg.content)

        # Trust-level payload filtering
        filtered_content = filter_payload(clean_content, identity.trust_level)

        agent_msg = AgentMessage(
            from_agent=signed_msg.sender_id,
            to_agent=signed_msg.recipient_id,
            content=filtered_content,
        )
        await self._bus.send(agent_msg)

    async def receive(
        self,
        agent_id: str,
        timeout: float | None = None,
    ) -> AgentMessage | None:
        """Receive the next message for *agent_id*."""
        return await self._bus.receive(agent_id, timeout=timeout)

    async def broadcast(self, sender_id: str, content: str) -> int:
        """Broadcast a signed message to all agents except the sender."""
        identity = self._identities.get(sender_id)
        if identity is None:
            raise PermissionError(f"Unknown sender: {sender_id}")

        clean_content = sanitize_content(content)
        filtered_content = filter_payload(clean_content, identity.trust_level)
        return await self._bus.broadcast(sender_id, filtered_content)

    # -- nonce housekeeping -------------------------------------------------

    def clear_nonces(self) -> None:
        """Purge all recorded nonces (useful for long-running processes)."""
        self._seen_nonces.clear()
