"""Secure credential store -- encryption at rest, TTL, rotation, JIT scoping.

Extends the base CredentialVault with:
- Fernet encryption at rest (falls back to base64 + HMAC when ``cryptography`` is absent)
- Per-credential TTL with auto-expiry on every ``get()``
- Just-in-time scoping via ``get_scoped()``
- Credential rotation via ``rotate()``
- Abstract interface for external vault back-ends (HashiCorp Vault, AWS SM)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Encryption back-end abstraction
# ---------------------------------------------------------------------------

_USE_FERNET = False
_Fernet: Any = None

try:
    from cryptography.fernet import Fernet as _FernetImpl

    _USE_FERNET = True
    _Fernet = _FernetImpl
except ImportError:
    pass


def _derive_key(raw: str) -> bytes:
    """Derive a 32-byte key from an arbitrary string via SHA-256."""
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


class _CryptoBackend:
    """Unified encrypt/decrypt regardless of whether *cryptography* is installed."""

    def __init__(self, key_material: str) -> None:
        self._raw_key = key_material
        if _USE_FERNET:
            self._fernet = _Fernet(_derive_key(key_material))
        else:
            self._fernet = None
            self._hmac_key = hashlib.sha256(key_material.encode()).digest()

    # -- Fernet path --------------------------------------------------------

    def encrypt(self, plaintext: str) -> str:
        if self._fernet is not None:
            return self._fernet.encrypt(plaintext.encode()).decode("ascii")
        return self._fallback_encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        if self._fernet is not None:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        return self._fallback_decrypt(ciphertext)

    # -- Fallback: base64 + HMAC verification (NOT cryptographically secure
    #    against a determined attacker, but prevents plaintext storage) ------

    def _fallback_encrypt(self, plaintext: str) -> str:
        encoded = base64.urlsafe_b64encode(plaintext.encode()).decode("ascii")
        tag = hmac.new(self._hmac_key, encoded.encode(), hashlib.sha256).hexdigest()
        return f"{encoded}.{tag}"

    def _fallback_decrypt(self, token: str) -> str:
        if "." not in token:
            raise ValueError("Invalid credential token (missing HMAC tag)")
        encoded, tag = token.rsplit(".", 1)
        expected = hmac.new(self._hmac_key, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("HMAC verification failed -- credential may have been tampered with")
        return base64.urlsafe_b64decode(encoded.encode()).decode()


# ---------------------------------------------------------------------------
# TTL helpers
# ---------------------------------------------------------------------------

# Defaults (seconds)
TTL_OPERATION = 15 * 60        # 15 minutes
TTL_PERSISTENT = 24 * 60 * 60  # 24 hours


class CredentialScope(StrEnum):
    OPERATION = "operation"
    PERSISTENT = "persistent"


@dataclass
class StoredCredential:
    """Internal record for an encrypted credential with metadata."""

    encrypted_value: str
    scope: CredentialScope
    ttl_seconds: float
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0.0
    version: int = 1

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


# ---------------------------------------------------------------------------
# External vault interface (abstract)
# ---------------------------------------------------------------------------


class ExternalVaultBackend(ABC):
    """Abstract interface for pluggable external vault back-ends.

    Implementations can wrap HashiCorp Vault, AWS Secrets Manager,
    Azure Key Vault, GCP Secret Manager, etc.
    """

    @abstractmethod
    async def fetch_secret(self, service: str) -> str | None:
        """Retrieve a secret value by service name."""

    @abstractmethod
    async def store_secret(self, service: str, value: str) -> None:
        """Persist a secret value under the given service name."""

    @abstractmethod
    async def rotate_secret(self, service: str) -> str | None:
        """Ask the back-end to rotate the secret, returning the new value."""

    @abstractmethod
    async def delete_secret(self, service: str) -> bool:
        """Remove a secret from the external vault."""


# ---------------------------------------------------------------------------
# Scoped token
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopedToken:
    """A short-lived, scoped credential token."""

    service: str
    action: str
    value: str
    expires_at: float
    token_id: str

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


# ---------------------------------------------------------------------------
# Main store
# ---------------------------------------------------------------------------


class SecureCredentialStore:
    """Encrypted credential store with TTL, rotation, and JIT scoping.

    Parameters
    ----------
    vault_key:
        Encryption key material.  Falls back to ``AGENTIC_VAULT_KEY`` env var,
        then auto-generates a random key on first use.
    external_backend:
        Optional :class:`ExternalVaultBackend` for delegating to HashiCorp
        Vault, AWS Secrets Manager, etc.
    """

    def __init__(
        self,
        vault_key: str | None = None,
        external_backend: ExternalVaultBackend | None = None,
    ) -> None:
        key = vault_key or os.environ.get("AGENTIC_VAULT_KEY") or secrets.token_urlsafe(32)
        self._crypto = _CryptoBackend(key)
        self._store: dict[str, StoredCredential] = {}
        self._scoped_tokens: dict[str, ScopedToken] = {}
        self._rotation_log: list[dict[str, Any]] = []
        self._access_log: list[dict[str, Any]] = []
        self._external = external_backend

    # -- Core CRUD ----------------------------------------------------------

    def store(
        self,
        service: str,
        value: str,
        *,
        scope: CredentialScope = CredentialScope.PERSISTENT,
        ttl_seconds: float | None = None,
    ) -> None:
        """Encrypt and store a credential."""
        if ttl_seconds is None:
            ttl_seconds = TTL_OPERATION if scope == CredentialScope.OPERATION else TTL_PERSISTENT

        encrypted = self._crypto.encrypt(value)
        version = 1
        if service in self._store:
            version = self._store[service].version + 1

        self._store[service] = StoredCredential(
            encrypted_value=encrypted,
            scope=scope,
            ttl_seconds=ttl_seconds,
            version=version,
        )
        logger.info("Credential stored: service=%s scope=%s version=%d", service, scope, version)

    def get(self, service: str) -> str | None:
        """Decrypt and return a credential, or ``None`` if missing/expired."""
        entry = self._store.get(service)
        if entry is None:
            return None

        if entry.is_expired:
            logger.info("Credential expired: service=%s", service)
            del self._store[service]
            return None

        entry.last_accessed = time.time()
        self._log_access(service, "get")
        return self._crypto.decrypt(entry.encrypted_value)

    def revoke(self, service: str) -> bool:
        """Immediately invalidate a credential."""
        if service in self._store:
            del self._store[service]
            self._log_access(service, "revoke")
            logger.info("Credential revoked: service=%s", service)
            return True
        return False

    def list_services(self) -> list[str]:
        """Return names of non-expired credentials."""
        self._purge_expired()
        return list(self._store.keys())

    # -- JIT scoping --------------------------------------------------------

    def get_scoped(
        self,
        service: str,
        action: str,
        ttl_seconds: float = 60,
    ) -> ScopedToken | None:
        """Return a short-lived scoped token for a specific service + action.

        The scoped token expires independently of the underlying credential.
        """
        value = self.get(service)
        if value is None:
            return None

        token_id = secrets.token_urlsafe(16)
        token = ScopedToken(
            service=service,
            action=action,
            value=value,
            expires_at=time.time() + ttl_seconds,
            token_id=token_id,
        )
        self._scoped_tokens[token_id] = token
        self._log_access(service, f"scoped:{action}")
        return token

    def validate_scoped_token(self, token_id: str) -> ScopedToken | None:
        """Validate and return a scoped token, or ``None`` if expired/unknown."""
        token = self._scoped_tokens.get(token_id)
        if token is None:
            return None
        if token.is_expired:
            del self._scoped_tokens[token_id]
            return None
        return token

    # -- Rotation -----------------------------------------------------------

    def rotate(self, service: str, new_value: str | None = None) -> bool:
        """Rotate a credential.  If *new_value* is ``None``, generates a random token.

        Returns ``True`` if the credential existed and was rotated.
        """
        entry = self._store.get(service)
        if entry is None:
            return False

        old_version = entry.version
        replacement = new_value or secrets.token_urlsafe(32)

        self.store(
            service,
            replacement,
            scope=entry.scope,
            ttl_seconds=entry.ttl_seconds,
        )

        # Invalidate outstanding scoped tokens for this service
        to_remove = [
            tid for tid, tok in self._scoped_tokens.items() if tok.service == service
        ]
        for tid in to_remove:
            del self._scoped_tokens[tid]

        self._rotation_log.append({
            "service": service,
            "old_version": old_version,
            "new_version": self._store[service].version,
            "timestamp": time.time(),
        })
        logger.info("Credential rotated: service=%s v%d->v%d", service, old_version, old_version + 1)
        return True

    # -- Metadata / audit ---------------------------------------------------

    @property
    def access_log(self) -> list[dict[str, Any]]:
        return list(self._access_log)

    @property
    def rotation_log(self) -> list[dict[str, Any]]:
        return list(self._rotation_log)

    @property
    def service_count(self) -> int:
        self._purge_expired()
        return len(self._store)

    @property
    def uses_fernet(self) -> bool:
        """Whether the store is using real Fernet encryption."""
        return _USE_FERNET

    # -- Internal helpers ---------------------------------------------------

    def _purge_expired(self) -> None:
        expired = [k for k, v in self._store.items() if v.is_expired]
        for k in expired:
            del self._store[k]
            logger.debug("Purged expired credential: %s", k)

    def _log_access(self, service: str, action: str) -> None:
        self._access_log.append({
            "timestamp": time.time(),
            "service": service,
            "action": action,
        })
