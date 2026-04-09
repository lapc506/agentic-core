"""Memory integrity -- injection scanning, provenance, HMAC checksums, trust segmentation.

Provides a defense layer around memory writes to detect and quarantine
poisoned memories before they can influence agent behavior.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agentic_core.application.middleware.injection_detector import (
    InjectionScanResult,
    Recommendation,
    scan_text,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trust model
# ---------------------------------------------------------------------------


class TrustLevel(StrEnum):
    """Trust level for a memory based on its provenance."""

    HIGH = "high"        # Direct user input, verified
    MEDIUM = "medium"    # Agent reasoning, tool results from trusted tools
    LOW = "low"          # RAG retrieval, untrusted tool results
    QUARANTINED = "quarantined"  # Flagged as suspicious


class MemorySource(StrEnum):
    """Origin of a memory write."""

    USER = "user"
    AGENT = "agent"
    TOOL = "tool"
    RAG = "rag"


_SOURCE_TRUST: dict[MemorySource, TrustLevel] = {
    MemorySource.USER: TrustLevel.HIGH,
    MemorySource.AGENT: TrustLevel.MEDIUM,
    MemorySource.TOOL: TrustLevel.MEDIUM,
    MemorySource.RAG: TrustLevel.LOW,
}


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


@dataclass
class MemoryProvenance:
    """Who/what wrote a memory and when."""

    user_id: str
    session_id: str
    source: MemorySource
    tool_name: str | None = None  # Set when source is TOOL
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Guarded memory record
# ---------------------------------------------------------------------------

# Default TTLs per trust level (seconds)
TTL_BY_TRUST: dict[TrustLevel, float] = {
    TrustLevel.HIGH: 0.0,           # No expiry for user-sourced memories
    TrustLevel.MEDIUM: 7 * 86400,   # 7 days
    TrustLevel.LOW: 24 * 3600,      # 24 hours
    TrustLevel.QUARANTINED: 3600,   # 1 hour
}


@dataclass
class GuardedMemory:
    """A memory record with integrity metadata."""

    memory_id: str
    content: str
    provenance: MemoryProvenance
    trust_level: TrustLevel
    hmac_checksum: str
    scan_score: float
    scan_patterns: list[str] = field(default_factory=list)
    ttl_seconds: float = 0.0  # 0 = no expiry
    created_at: float = field(default_factory=time.time)
    quarantine_reason: str = ""

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds

    @property
    def is_quarantined(self) -> bool:
        return self.trust_level == TrustLevel.QUARANTINED


# ---------------------------------------------------------------------------
# Memory Integrity service
# ---------------------------------------------------------------------------


class MemoryIntegrity:
    """Integrity layer for memory writes.

    Scans all writes for injection, tracks provenance, computes HMAC
    checksums, segments by trust level, and quarantines suspicious content.

    Parameters
    ----------
    hmac_key:
        Secret used for HMAC integrity checksums.  Falls back to
        ``AGENTIC_MEMORY_HMAC_KEY`` env var, then auto-generates.
    quarantine_threshold:
        Injection scan score at or above which a memory is quarantined
        (default 0.3 -- the WARN boundary in the injection detector).
    block_threshold:
        Score at or above which the memory write is rejected entirely
        (default 0.6 -- the BLOCK boundary).
    """

    def __init__(
        self,
        *,
        hmac_key: str | None = None,
        quarantine_threshold: float = 0.3,
        block_threshold: float = 0.6,
    ) -> None:
        key_material = hmac_key or os.environ.get("AGENTIC_MEMORY_HMAC_KEY") or secrets.token_urlsafe(32)
        self._hmac_key = hashlib.sha256(key_material.encode()).digest()
        self._quarantine_threshold = quarantine_threshold
        self._block_threshold = block_threshold

        self._memories: dict[str, GuardedMemory] = {}
        self._audit: list[dict[str, Any]] = []
        self._id_counter = 0

    # -- Write --------------------------------------------------------------

    def write(
        self,
        content: str,
        provenance: MemoryProvenance,
        *,
        trust_override: TrustLevel | None = None,
        ttl_override: float | None = None,
    ) -> GuardedMemory | None:
        """Write a memory with full integrity checks.

        Returns the :class:`GuardedMemory` on success, or ``None`` if the
        write was blocked (score >= block_threshold).
        """
        # 1. Injection scan
        scan_result: InjectionScanResult = scan_text(content)

        # 2. Determine trust level
        base_trust = trust_override or _SOURCE_TRUST.get(provenance.source, TrustLevel.LOW)

        # 3. Decide: block, quarantine, or accept
        if scan_result.score >= self._block_threshold:
            self._log_audit("blocked", content, provenance, scan_result)
            logger.warning(
                "Memory write BLOCKED: score=%.4f patterns=%s source=%s",
                scan_result.score, scan_result.detected_patterns, provenance.source,
            )
            return None

        quarantine_reason = ""
        if scan_result.score >= self._quarantine_threshold:
            base_trust = TrustLevel.QUARANTINED
            quarantine_reason = (
                f"Injection score {scan_result.score:.2f} >= threshold "
                f"{self._quarantine_threshold:.2f}: {scan_result.detected_patterns}"
            )
            logger.info(
                "Memory QUARANTINED: score=%.4f patterns=%s",
                scan_result.score, scan_result.detected_patterns,
            )

        # 4. Compute HMAC
        checksum = self._compute_hmac(content)

        # 5. TTL
        ttl = ttl_override if ttl_override is not None else TTL_BY_TRUST.get(base_trust, 0.0)

        # 6. Store
        self._id_counter += 1
        memory_id = f"mem-{self._id_counter:06d}"

        record = GuardedMemory(
            memory_id=memory_id,
            content=content,
            provenance=provenance,
            trust_level=base_trust,
            hmac_checksum=checksum,
            scan_score=scan_result.score,
            scan_patterns=scan_result.detected_patterns,
            ttl_seconds=ttl,
            quarantine_reason=quarantine_reason,
        )
        self._memories[memory_id] = record
        self._log_audit("stored", content, provenance, scan_result, memory_id=memory_id, trust=base_trust)
        return record

    # -- Read ---------------------------------------------------------------

    def get(self, memory_id: str) -> GuardedMemory | None:
        """Retrieve a memory by ID (returns ``None`` if expired or missing)."""
        record = self._memories.get(memory_id)
        if record is None:
            return None
        if record.is_expired:
            del self._memories[memory_id]
            return None
        return record

    def query(
        self,
        *,
        trust_levels: set[TrustLevel] | None = None,
        include_quarantined: bool = False,
        include_expired: bool = False,
    ) -> list[GuardedMemory]:
        """Query memories filtered by trust level.

        By default, quarantined and expired memories are excluded.
        """
        self._purge_expired()
        results: list[GuardedMemory] = []
        for record in self._memories.values():
            if not include_expired and record.is_expired:
                continue
            if not include_quarantined and record.is_quarantined:
                continue
            if trust_levels and record.trust_level not in trust_levels:
                continue
            results.append(record)
        return results

    def query_quarantined(self) -> list[GuardedMemory]:
        """Return all quarantined (but not expired) memories."""
        self._purge_expired()
        return [m for m in self._memories.values() if m.is_quarantined]

    # -- Integrity verification ---------------------------------------------

    def verify_integrity(self, memory_id: str) -> bool:
        """Re-compute the HMAC and compare against the stored checksum.

        Returns ``False`` if the memory has been tampered with, is missing, or
        is expired.
        """
        record = self.get(memory_id)
        if record is None:
            return False
        expected = self._compute_hmac(record.content)
        return hmac.compare_digest(record.hmac_checksum, expected)

    # -- Lifecycle ----------------------------------------------------------

    def promote(self, memory_id: str, new_trust: TrustLevel) -> bool:
        """Promote a memory to a higher trust level (e.g. after human review)."""
        record = self._memories.get(memory_id)
        if record is None:
            return False
        old_trust = record.trust_level
        record.trust_level = new_trust
        record.quarantine_reason = ""
        record.ttl_seconds = TTL_BY_TRUST.get(new_trust, 0.0)
        logger.info("Memory promoted: %s %s->%s", memory_id, old_trust, new_trust)
        return True

    def delete(self, memory_id: str) -> bool:
        """Permanently delete a memory."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    # -- Properties ---------------------------------------------------------

    @property
    def total_count(self) -> int:
        return len(self._memories)

    @property
    def quarantined_count(self) -> int:
        return sum(1 for m in self._memories.values() if m.is_quarantined)

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit)

    # -- Internal -----------------------------------------------------------

    def _compute_hmac(self, content: str) -> str:
        return hmac.new(self._hmac_key, content.encode(), hashlib.sha256).hexdigest()

    def _purge_expired(self) -> None:
        expired = [mid for mid, m in self._memories.items() if m.is_expired]
        for mid in expired:
            del self._memories[mid]
            logger.debug("Purged expired memory: %s", mid)

    def _log_audit(
        self,
        action: str,
        content: str,
        provenance: MemoryProvenance,
        scan_result: InjectionScanResult,
        *,
        memory_id: str = "",
        trust: TrustLevel | None = None,
    ) -> None:
        self._audit.append({
            "timestamp": time.time(),
            "action": action,
            "memory_id": memory_id,
            "source": provenance.source.value,
            "user_id": provenance.user_id,
            "session_id": provenance.session_id,
            "scan_score": scan_result.score,
            "scan_patterns": scan_result.detected_patterns,
            "trust_level": trust.value if trust else "",
            "content_length": len(content),
        })
