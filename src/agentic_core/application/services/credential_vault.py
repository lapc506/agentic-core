"""Credential vault -- agents never hold raw API keys in memory."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VaultEntry:
    name: str
    service: str
    masked_value: str  # First 4 + last 4 chars visible


class CredentialVault:
    """Manages credentials outside agent process memory.

    Agents request credentials by service name. The vault injects
    them into outbound requests at the proxy layer, so agents
    never hold raw keys in memory.
    """

    def __init__(self) -> None:
        self._credentials: dict[str, str] = {}
        self._access_log: list[dict] = []

    def store(self, name: str, value: str) -> None:
        """Store a credential (called by operator, not by agent)."""
        self._credentials[name] = value
        logger.info("Credential stored: %s", name)

    def load_from_env(self, prefix: str = "AGENTIC_CRED_") -> int:
        """Load credentials from environment variables with a prefix."""
        count = 0
        for key, value in os.environ.items():
            if key.startswith(prefix):
                name = key[len(prefix) :].lower()
                self.store(name, value)
                count += 1
        return count

    def inject_header(
        self,
        service: str,
        headers: dict[str, str],
    ) -> dict[str, str]:
        """Inject auth header for a service (called by proxy, not by agent)."""
        cred = self._credentials.get(service)
        if not cred:
            logger.warning("No credential found for service: %s", service)
            return headers

        self._log_access(service, "inject_header")
        headers = dict(headers)
        headers["Authorization"] = f"Bearer {cred}"
        return headers

    def get_for_proxy(self, service: str) -> str | None:
        """Get credential for proxy injection (not for agent use)."""
        cred = self._credentials.get(service)
        if cred:
            self._log_access(service, "proxy_get")
        return cred

    def list_services(self) -> list[VaultEntry]:
        """List stored credentials (masked)."""
        entries: list[VaultEntry] = []
        for name, value in self._credentials.items():
            masked = self._mask(value)
            entries.append(
                VaultEntry(name=name, service=name, masked_value=masked),
            )
        return entries

    def revoke(self, name: str) -> bool:
        if name in self._credentials:
            del self._credentials[name]
            logger.info("Credential revoked: %s", name)
            return True
        return False

    def _mask(self, value: str) -> str:
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]

    def _log_access(self, service: str, action: str) -> None:
        import time

        self._access_log.append(
            {
                "timestamp": time.time(),
                "service": service,
                "action": action,
            }
        )

    @property
    def access_log(self) -> list[dict]:
        return self._access_log

    @property
    def service_count(self) -> int:
        return len(self._credentials)
