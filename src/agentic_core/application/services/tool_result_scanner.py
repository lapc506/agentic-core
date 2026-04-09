"""Tool result injection scanner -- wraps the injection detector for tool outputs.

Scans every tool result before it enters the LLM context window:
- Configurable per-tool trust levels (trusted tools skip scanning)
- On detection: strips the injection payload, logs to audit trail
- Supports MCP tool results, coding tool results, and RAG retrieval results
- Returns sanitized result with metadata about what was stripped
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agentic_core.application.middleware.injection_detector import (
    FrequencyTracker,
    InjectionScanResult,
    Recommendation,
    scan_tool_result as _raw_scan,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class ToolTrustLevel(StrEnum):
    """Trust level assigned to a tool for result scanning policy."""

    TRUSTED = "trusted"          # Skip scanning entirely
    STANDARD = "standard"        # Scan, strip on WARN or BLOCK
    UNTRUSTED = "untrusted"      # Scan, block result on any detection


class ScanAction(StrEnum):
    """Action taken by the scanner on a result."""

    PASSED = "passed"
    SANITIZED = "sanitized"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ResultSource(StrEnum):
    """Origin of the tool result."""

    MCP = "mcp"
    CODING = "coding"
    RAG = "rag"
    GENERIC = "generic"


@dataclass(frozen=True)
class StrippedPayload:
    """Record of a single stripped injection payload."""

    pattern: str
    original_fragment: str
    replacement: str


@dataclass
class ScanOutcome:
    """Complete result of scanning a tool output."""

    tool_name: str
    source: ResultSource
    action: ScanAction
    original_result: Any
    sanitized_result: Any
    scan_result: InjectionScanResult | None
    stripped_payloads: list[StrippedPayload] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def was_modified(self) -> bool:
        return self.action in (ScanAction.SANITIZED, ScanAction.BLOCKED)


# ---------------------------------------------------------------------------
# Payload stripping
# ---------------------------------------------------------------------------

# Patterns to strip when injection is detected.  Each tuple is
# (compiled regex, human-readable label).
_STRIP_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Role / system injection markers
    (re.compile(r"(?i)^(system|assistant)\s*:.*$", re.MULTILINE), "role-injection-line"),
    (re.compile(r"(?i)</?(?:system|instructions|tool_call|function_call)>", re.MULTILINE),
     "xml-tag-injection"),
    (re.compile(r"(?i)<\|im_(?:start|end)\|>", re.MULTILINE), "chatml-injection"),
    (re.compile(r"(?i)<</?SYS>>", re.MULTILINE), "llama-sys-injection"),
    (re.compile(r"(?i)\[/?INST\]", re.MULTILINE), "inst-injection"),
    (re.compile(r"(?i)<\|endoftext\|>", re.MULTILINE), "endoftext-injection"),
    # Instruction override phrases
    (re.compile(
        r"(?i)(?:ignore|disregard|forget|override)\s+"
        r"(?:all\s+|previous\s+|prior\s+|above\s+|your\s+)*instructions?",
        re.MULTILINE,
    ), "instruction-override"),
    # Jailbreak / DAN
    (re.compile(r"(?i)(?:do anything now|jailbreak|unrestricted mode|bypass your)", re.MULTILINE),
     "jailbreak-phrase"),
    # JSON role injection
    (re.compile(r'(?i)\{\s*"role"\s*:\s*"(?:system|assistant)"[^}]*\}', re.MULTILINE),
     "json-role-injection"),
]

_REPLACEMENT = "[STRIPPED]"


def _strip_payloads(text: str) -> tuple[str, list[StrippedPayload]]:
    """Remove known injection patterns from *text*."""
    stripped: list[StrippedPayload] = []
    result = text
    for pattern, label in _STRIP_PATTERNS:
        for match in pattern.finditer(result):
            stripped.append(StrippedPayload(
                pattern=label,
                original_fragment=match.group()[:120],
                replacement=_REPLACEMENT,
            ))
        result = pattern.sub(_REPLACEMENT, result)
    return result, stripped


def _sanitize_result(result: Any) -> tuple[Any, list[StrippedPayload]]:
    """Recursively sanitize a tool result (str, dict, list)."""
    all_stripped: list[StrippedPayload] = []

    if isinstance(result, str):
        cleaned, stripped = _strip_payloads(result)
        return cleaned, stripped

    if isinstance(result, list):
        out: list[Any] = []
        for item in result:
            cleaned, stripped = _sanitize_result(item)
            out.append(cleaned)
            all_stripped.extend(stripped)
        return out, all_stripped

    if isinstance(result, dict):
        out_dict: dict[str, Any] = {}
        for key, value in result.items():
            cleaned, stripped = _sanitize_result(value)
            out_dict[key] = cleaned
            all_stripped.extend(stripped)
        return out_dict, all_stripped

    # Non-text types pass through unchanged
    return result, []


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class ToolResultScanner:
    """Scans tool results for injection payloads before they enter LLM context.

    Parameters
    ----------
    trust_config:
        Mapping of ``tool_name -> ToolTrustLevel``.  Tools not listed default
        to ``ToolTrustLevel.STANDARD``.
    block_on_detection:
        If ``True``, results with BLOCK-level scores are replaced entirely
        with an error message rather than being sanitized.
    frequency_tracker:
        Optional shared :class:`FrequencyTracker` for cross-tool frequency
        analysis.
    """

    def __init__(
        self,
        *,
        trust_config: dict[str, ToolTrustLevel] | None = None,
        block_on_detection: bool = True,
        frequency_tracker: FrequencyTracker | None = None,
    ) -> None:
        self._trust: dict[str, ToolTrustLevel] = dict(trust_config or {})
        self._block = block_on_detection
        self._freq = frequency_tracker or FrequencyTracker()
        self._audit: list[dict[str, Any]] = []

    # -- Configuration ------------------------------------------------------

    def set_trust(self, tool_name: str, level: ToolTrustLevel) -> None:
        """Set or update the trust level for a tool."""
        self._trust[tool_name] = level

    def get_trust(self, tool_name: str) -> ToolTrustLevel:
        return self._trust.get(tool_name, ToolTrustLevel.STANDARD)

    # -- Main entry point ---------------------------------------------------

    def scan(
        self,
        tool_name: str,
        result: Any,
        *,
        source: ResultSource = ResultSource.GENERIC,
        session_id: str | None = None,
    ) -> ScanOutcome:
        """Scan a tool result and return a :class:`ScanOutcome`.

        Trusted tools are skipped.  Standard/untrusted tools are scanned
        and potentially sanitized or blocked.
        """
        trust = self.get_trust(tool_name)

        # Trusted tools bypass scanning
        if trust == ToolTrustLevel.TRUSTED:
            outcome = ScanOutcome(
                tool_name=tool_name,
                source=source,
                action=ScanAction.SKIPPED,
                original_result=result,
                sanitized_result=result,
                scan_result=None,
            )
            self._record_audit(outcome)
            return outcome

        # Run the injection detector
        scan_result = _raw_scan(
            result,
            session_id=session_id,
            frequency_tracker=self._freq,
        )

        # For untrusted tools, ANY non-zero score triggers a block --
        # checked before the ALLOW early-return so low scores still block.
        if trust == ToolTrustLevel.UNTRUSTED and scan_result.score > 0:
            blocked_msg = (
                f"[BLOCKED] Tool result from '{tool_name}' blocked due to "
                f"injection detection (score={scan_result.score:.2f}, "
                f"patterns={scan_result.detected_patterns})"
            )
            outcome = ScanOutcome(
                tool_name=tool_name,
                source=source,
                action=ScanAction.BLOCKED,
                original_result=result,
                sanitized_result=blocked_msg,
                scan_result=scan_result,
            )
            self._record_audit(outcome)
            logger.warning(
                "Tool result BLOCKED: tool=%s score=%.4f patterns=%s",
                tool_name, scan_result.score, scan_result.detected_patterns,
            )
            return outcome

        # Standard tools with ALLOW recommendation pass through
        if scan_result.recommendation == Recommendation.ALLOW:
            outcome = ScanOutcome(
                tool_name=tool_name,
                source=source,
                action=ScanAction.PASSED,
                original_result=result,
                sanitized_result=result,
                scan_result=scan_result,
            )
            self._record_audit(outcome)
            return outcome

        # BLOCK-level score with block_on_detection enabled
        if scan_result.recommendation == Recommendation.BLOCK and self._block:
            blocked_msg = (
                f"[BLOCKED] Tool result from '{tool_name}' blocked due to "
                f"injection detection (score={scan_result.score:.2f})"
            )
            outcome = ScanOutcome(
                tool_name=tool_name,
                source=source,
                action=ScanAction.BLOCKED,
                original_result=result,
                sanitized_result=blocked_msg,
                scan_result=scan_result,
            )
            self._record_audit(outcome)
            logger.warning(
                "Tool result BLOCKED: tool=%s score=%.4f patterns=%s",
                tool_name, scan_result.score, scan_result.detected_patterns,
            )
            return outcome

        # WARN or BLOCK with block_on_detection=False: sanitize
        sanitized, stripped = _sanitize_result(result)
        outcome = ScanOutcome(
            tool_name=tool_name,
            source=source,
            action=ScanAction.SANITIZED,
            original_result=result,
            sanitized_result=sanitized,
            scan_result=scan_result,
            stripped_payloads=stripped,
        )
        self._record_audit(outcome)
        logger.info(
            "Tool result SANITIZED: tool=%s score=%.4f stripped=%d patterns=%s",
            tool_name, scan_result.score, len(stripped), scan_result.detected_patterns,
        )
        return outcome

    # -- Convenience methods for specific sources ---------------------------

    def scan_mcp_result(
        self,
        tool_name: str,
        result: Any,
        *,
        session_id: str | None = None,
    ) -> ScanOutcome:
        """Scan an MCP tool result."""
        return self.scan(tool_name, result, source=ResultSource.MCP, session_id=session_id)

    def scan_coding_result(
        self,
        tool_name: str,
        result: Any,
        *,
        session_id: str | None = None,
    ) -> ScanOutcome:
        """Scan a coding tool result (shell output, file read, etc.)."""
        return self.scan(tool_name, result, source=ResultSource.CODING, session_id=session_id)

    def scan_rag_result(
        self,
        tool_name: str,
        result: Any,
        *,
        session_id: str | None = None,
    ) -> ScanOutcome:
        """Scan a RAG retrieval result."""
        return self.scan(tool_name, result, source=ResultSource.RAG, session_id=session_id)

    # -- Audit trail --------------------------------------------------------

    @property
    def audit_trail(self) -> list[dict[str, Any]]:
        return list(self._audit)

    def _record_audit(self, outcome: ScanOutcome) -> None:
        entry: dict[str, Any] = {
            "timestamp": outcome.timestamp,
            "tool_name": outcome.tool_name,
            "source": outcome.source.value,
            "action": outcome.action.value,
            "score": outcome.scan_result.score if outcome.scan_result else 0.0,
            "patterns": outcome.scan_result.detected_patterns if outcome.scan_result else [],
            "stripped_count": len(outcome.stripped_payloads),
        }
        self._audit.append(entry)
