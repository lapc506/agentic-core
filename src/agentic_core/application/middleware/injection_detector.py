"""Multi-layer heuristic prompt injection detector.

Scans inputs, outputs, tool results, and RAG content for prompt injection
attempts using five independent scanners, each scoring 0.0-1.0:

1. keyword_scanner    -- known injection phrases (EN + ES)
2. encoding_scanner   -- base64, hex-encoded, unicode-escaped payloads
3. structure_scanner  -- role injection, XML/HTML system tags, instruction headers
4. semantic_scanner   -- system prompt extraction attempts
5. frequency_scanner  -- per-session injection attempt tracking

Design constraints:
- Pure string/regex operations -- no external API calls
- <5ms latency budget
- Composite score 0.0-1.0 with structured results
- Usable as middleware AND standalone scanner

Modeled after dojo-agent-openclaw-plugin injection-detector.ts.
"""

from __future__ import annotations

import base64
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)

if TYPE_CHECKING:
    from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class Recommendation(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ScannerHit:
    scanner: str
    pattern: str
    score: float


@dataclass(frozen=True)
class InjectionScanResult:
    """Structured result from the injection detector."""

    score: float
    detected_patterns: list[str]
    scanner_hits: list[ScannerHit]
    recommendation: Recommendation


# ---------------------------------------------------------------------------
# 1. Keyword Scanner -- known injection phrases (EN + ES)
# ---------------------------------------------------------------------------

_KEYWORD_PHRASES: list[tuple[str, float]] = [
    # Direct instruction override (EN)
    ("ignore previous instructions", 0.95),
    ("ignore all instructions", 0.95),
    ("ignore prior instructions", 0.90),
    ("ignore above instructions", 0.90),
    ("ignore the above", 0.75),
    ("disregard all previous", 0.90),
    ("disregard previous instructions", 0.95),
    ("disregard your instructions", 0.90),
    ("forget your instructions", 0.90),
    ("forget all instructions", 0.90),
    ("override your instructions", 0.95),
    ("new instructions:", 0.85),
    ("new instructions follow", 0.85),
    ("updated instructions:", 0.80),
    ("revised instructions:", 0.80),
    # Persona / role override (EN)
    ("you are now", 0.60),
    ("from now on you are", 0.80),
    ("you must obey", 0.80),
    ("pretend you are", 0.70),
    ("pretend to be", 0.65),
    ("act as if you", 0.60),
    # Jailbreak / DAN patterns
    ("do anything now", 0.80),
    ("jailbreak", 0.70),
    ("developer mode", 0.55),
    ("enable developer mode", 0.80),
    ("no restrictions", 0.50),
    ("without restrictions", 0.50),
    ("unrestricted mode", 0.70),
    ("bypass your safety", 0.90),
    ("bypass your guardrails", 0.90),
    ("bypass your rules", 0.85),
    # Direct instruction override (ES)
    ("ignora las instrucciones anteriores", 0.95),
    ("ignora todas las instrucciones", 0.95),
    ("ignora las instrucciones previas", 0.90),
    ("olvida tus instrucciones", 0.90),
    ("olvida todas las instrucciones", 0.90),
    ("anula tus instrucciones", 0.90),
    ("nuevas instrucciones:", 0.85),
    ("instrucciones actualizadas:", 0.80),
    # Persona / role override (ES)
    ("ahora eres", 0.60),
    ("a partir de ahora eres", 0.80),
    ("debes obedecer", 0.80),
    ("finge que eres", 0.70),
    ("actua como si fueras", 0.65),
    ("modo sin restricciones", 0.70),
    ("modo desarrollador", 0.55),
]


def keyword_scanner(text: str) -> tuple[float, list[ScannerHit]]:
    """Scan for known injection keyword phrases in English and Spanish."""
    lower = text.lower()
    total = 0.0
    hits: list[ScannerHit] = []

    for phrase, weight in _KEYWORD_PHRASES:
        if phrase in lower:
            total += weight
            hits.append(ScannerHit(scanner="keyword", pattern=phrase, score=weight))

    return min(total, 1.0), hits


# ---------------------------------------------------------------------------
# 2. Encoding Scanner -- base64, hex, unicode escapes
# ---------------------------------------------------------------------------

_BASE64_RE = re.compile(
    r"(?:^|[\s\"'`=:,;(\[{])"
    r"((?:[A-Za-z0-9+/]{4}){5,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?)"
    r"(?:$|[\s\"'`),;\]}\n])",
)

_HEX_RE = re.compile(
    r"(?:^|[\s])(?:0x)?([0-9a-fA-F]{20,})(?:$|[\s])",
)

_UNICODE_ESCAPE_RE = re.compile(
    r"(?:\\u[0-9a-fA-F]{4}){4,}",
)


def _try_base64_decode(encoded: str) -> str | None:
    """Attempt to decode a base64 string. Returns None if not valid UTF-8 text."""
    try:
        decoded = base64.b64decode(encoded).decode("utf-8", errors="strict")
        printable = sum(1 for c in decoded if c.isprintable() or c in ("\n", "\r", "\t"))
        if printable / max(len(decoded), 1) < 0.7:
            return None
        return decoded
    except Exception:
        return None


def _try_hex_decode(hex_str: str) -> str | None:
    """Attempt to decode a hex string to UTF-8 text."""
    try:
        decoded = bytes.fromhex(hex_str).decode("utf-8", errors="strict")
        printable = sum(1 for c in decoded if c.isprintable() or c in ("\n", "\r", "\t"))
        if printable / max(len(decoded), 1) < 0.7:
            return None
        return decoded
    except Exception:
        return None


def _try_unicode_unescape(escaped: str) -> str | None:
    """Attempt to decode unicode escape sequences."""
    try:
        decoded = escaped.encode("utf-8").decode("unicode_escape")
        if len(decoded) < 4:
            return None
        return decoded
    except Exception:
        return None


def encoding_scanner(text: str) -> tuple[float, list[ScannerHit]]:
    """Scan for encoded injection payloads (base64, hex, unicode escapes)."""
    total = 0.0
    hits: list[ScannerHit] = []

    # Base64
    for m in _BASE64_RE.finditer(text):
        candidate = m.group(1)
        if not candidate or len(candidate) < 20:
            continue
        decoded = _try_base64_decode(candidate)
        if decoded:
            inner_score, inner_hits = keyword_scanner(decoded)
            if inner_score > 0:
                total += inner_score
                for h in inner_hits:
                    hits.append(ScannerHit(
                        scanner="encoding",
                        pattern=f"base64->{h.pattern}",
                        score=h.score,
                    ))

    # Hex-encoded
    for m in _HEX_RE.finditer(text):
        candidate = m.group(1)
        decoded = _try_hex_decode(candidate)
        if decoded:
            inner_score, inner_hits = keyword_scanner(decoded)
            if inner_score > 0:
                total += inner_score
                for h in inner_hits:
                    hits.append(ScannerHit(
                        scanner="encoding",
                        pattern=f"hex->{h.pattern}",
                        score=h.score,
                    ))

    # Unicode escapes
    for m in _UNICODE_ESCAPE_RE.finditer(text):
        decoded = _try_unicode_unescape(m.group(0))
        if decoded:
            inner_score, inner_hits = keyword_scanner(decoded)
            if inner_score > 0:
                total += inner_score
                for h in inner_hits:
                    hits.append(ScannerHit(
                        scanner="encoding",
                        pattern=f"unicode->{h.pattern}",
                        score=h.score,
                    ))

    return min(total, 1.0), hits


# ---------------------------------------------------------------------------
# 3. Structure Scanner -- role injection, XML/HTML tags, instruction headers
# ---------------------------------------------------------------------------

_STRUCTURE_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # Role injection
    (re.compile(r"^assistant\s*:", re.IGNORECASE | re.MULTILINE), "role:assistant:", 0.70),
    (re.compile(r"^system\s*:", re.IGNORECASE | re.MULTILINE), "role:system:", 0.85),
    (re.compile(r"^user\s*:", re.IGNORECASE | re.MULTILINE), "role:user:", 0.50),
    # XML/HTML system tags
    (re.compile(r"</system>", re.IGNORECASE), "xml:</system>", 0.80),
    (re.compile(r"<system>", re.IGNORECASE), "xml:<system>", 0.75),
    (re.compile(r"</instructions>", re.IGNORECASE), "xml:</instructions>", 0.80),
    (re.compile(r"<instructions>", re.IGNORECASE), "xml:<instructions>", 0.70),
    (re.compile(r"<tool_call>", re.IGNORECASE), "xml:<tool_call>", 0.80),
    (re.compile(r"</tool_call>", re.IGNORECASE), "xml:</tool_call>", 0.80),
    (re.compile(r"<function_call>", re.IGNORECASE), "xml:<function_call>", 0.80),
    # ChatML / LLaMA format injection
    (re.compile(r"\[INST\]", re.IGNORECASE), "fmt:[INST]", 0.75),
    (re.compile(r"\[/INST\]", re.IGNORECASE), "fmt:[/INST]", 0.75),
    (re.compile(r"<<SYS>>", re.IGNORECASE), "fmt:<<SYS>>", 0.85),
    (re.compile(r"<</SYS>>", re.IGNORECASE), "fmt:<</SYS>>", 0.85),
    (re.compile(r"<\|im_start\|>", re.IGNORECASE), "fmt:<|im_start|>", 0.80),
    (re.compile(r"<\|im_end\|>", re.IGNORECASE), "fmt:<|im_end|>", 0.80),
    (re.compile(r"<\|endoftext\|>", re.IGNORECASE), "fmt:<|endoftext|>", 0.75),
    # JSON role injection
    (re.compile(r'\{\s*"role"\s*:\s*"system"', re.IGNORECASE), "json:role:system", 0.85),
    (re.compile(r'\{\s*"role"\s*:\s*"assistant"', re.IGNORECASE), "json:role:assistant", 0.70),
    # Markdown instruction headers
    (re.compile(r"^#{1,3}\s*(?:system\s+)?instructions?\b", re.IGNORECASE | re.MULTILINE),
     "md:instruction-header", 0.65),
    (re.compile(r"^#{1,3}\s*new\s+(?:system\s+)?prompt\b", re.IGNORECASE | re.MULTILINE),
     "md:new-prompt-header", 0.75),
    (re.compile(r"^#{1,3}\s*(?:system\s+)?rules?\b", re.IGNORECASE | re.MULTILINE),
     "md:rules-header", 0.55),
]


def structure_scanner(text: str) -> tuple[float, list[ScannerHit]]:
    """Scan for role injection, XML/HTML system tags, and instruction headers."""
    total = 0.0
    hits: list[ScannerHit] = []

    for pattern, label, weight in _STRUCTURE_PATTERNS:
        if pattern.search(text):
            total += weight
            hits.append(ScannerHit(scanner="structure", pattern=label, score=weight))

    return min(total, 1.0), hits


# ---------------------------------------------------------------------------
# 4. Semantic Scanner -- system prompt extraction attempts
# ---------------------------------------------------------------------------

_SEMANTIC_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # EN: System prompt extraction
    (re.compile(r"what\s+are\s+your\s+instructions", re.IGNORECASE),
     "extract:what-are-your-instructions", 0.80),
    (re.compile(r"repeat\s+your\s+system\s+prompt", re.IGNORECASE),
     "extract:repeat-system-prompt", 0.90),
    (re.compile(r"show\s+me\s+your\s+(?:system\s+)?(?:prompt|rules|instructions)", re.IGNORECASE),
     "extract:show-me-prompt", 0.85),
    (re.compile(r"print\s+your\s+(?:system\s+)?(?:prompt|instructions|rules)", re.IGNORECASE),
     "extract:print-prompt", 0.85),
    (re.compile(r"reveal\s+your\s+(?:system\s+)?(?:prompt|instructions|rules)", re.IGNORECASE),
     "extract:reveal-prompt", 0.85),
    (re.compile(r"output\s+your\s+system", re.IGNORECASE),
     "extract:output-system", 0.80),
    (re.compile(r"display\s+your\s+(?:system\s+)?(?:prompt|instructions)", re.IGNORECASE),
     "extract:display-prompt", 0.80),
    (re.compile(r"what\s+is\s+your\s+system\s+prompt", re.IGNORECASE),
     "extract:what-is-system-prompt", 0.80),
    (re.compile(r"tell\s+me\s+your\s+(?:system\s+)?(?:prompt|instructions|rules)", re.IGNORECASE),
     "extract:tell-me-prompt", 0.80),
    (re.compile(r"copy\s+(?:and\s+paste\s+)?your\s+(?:system\s+)?(?:prompt|instructions)",
                re.IGNORECASE),
     "extract:copy-prompt", 0.85),
    (re.compile(r"dump\s+your\s+(?:system\s+)?(?:prompt|instructions|config)", re.IGNORECASE),
     "extract:dump-prompt", 0.85),
    # ES: System prompt extraction
    (re.compile(r"muestra\s+tu\s+(?:prompt|instrucciones|reglas)", re.IGNORECASE),
     "extract:muestra-prompt", 0.85),
    (re.compile(r"repite\s+tu\s+prompt\s+(?:de\s+)?sistema", re.IGNORECASE),
     "extract:repite-prompt-sistema", 0.90),
    (re.compile(r"(?:cu[aá]les|que)\s+son\s+tus\s+instrucciones", re.IGNORECASE),
     "extract:cuales-son-instrucciones", 0.80),
    (re.compile(r"dime\s+tus\s+(?:instrucciones|reglas)", re.IGNORECASE),
     "extract:dime-instrucciones", 0.80),
    (re.compile(r"revela\s+tu\s+(?:prompt|instrucciones)", re.IGNORECASE),
     "extract:revela-prompt", 0.85),
]


def semantic_scanner(text: str) -> tuple[float, list[ScannerHit]]:
    """Scan for attempts to extract the system prompt."""
    total = 0.0
    hits: list[ScannerHit] = []

    for pattern, label, weight in _SEMANTIC_PATTERNS:
        if pattern.search(text):
            total += weight
            hits.append(ScannerHit(scanner="semantic", pattern=label, score=weight))

    return min(total, 1.0), hits


# ---------------------------------------------------------------------------
# 5. Frequency Scanner -- per-session injection attempt tracking
# ---------------------------------------------------------------------------


class FrequencyTracker:
    """Track injection attempts per session with configurable threshold."""

    def __init__(
        self,
        threshold: int = 3,
        decay_factor: float = 0.5,
        window_seconds: float = 300.0,
    ) -> None:
        self._threshold = threshold
        self._decay_factor = decay_factor
        self._window = window_seconds
        # session_id -> list of (timestamp, score) tuples
        self._history: dict[str, list[tuple[float, float]]] = defaultdict(list)

    def record_and_score(self, session_id: str, scan_score: float) -> tuple[float, list[ScannerHit]]:
        """Record a scan result and return a frequency-based score."""
        now = time.monotonic()
        history = self._history[session_id]

        # Prune entries outside the window
        cutoff = now - self._window
        history[:] = [(ts, sc) for ts, sc in history if ts > cutoff]

        # Record current attempt if it had any suspicious score
        if scan_score > 0.0:
            history.append((now, scan_score))

        # Count how many suspicious attempts in the window
        attempt_count = len(history)
        if attempt_count < self._threshold:
            return 0.0, []

        # Score increases with number of attempts above threshold
        excess = attempt_count - self._threshold
        freq_score = min(0.3 + (excess * 0.15), 1.0)
        return freq_score, [ScannerHit(
            scanner="frequency",
            pattern=f"session:{session_id}:attempts={attempt_count}",
            score=freq_score,
        )]

    def reset_session(self, session_id: str) -> None:
        """Clear tracking data for a session."""
        self._history.pop(session_id, None)

    def get_attempt_count(self, session_id: str) -> int:
        """Return the current number of tracked attempts for a session."""
        return len(self._history.get(session_id, []))


# ---------------------------------------------------------------------------
# Composite scanner
# ---------------------------------------------------------------------------

# Weights for combining scanner scores into the final 0.0-1.0 composite
_SCANNER_WEIGHTS = {
    "keyword": 0.30,
    "encoding": 0.20,
    "structure": 0.20,
    "semantic": 0.20,
    "frequency": 0.10,
}


def _classify(score: float) -> Recommendation:
    if score > 0.6:
        return Recommendation.BLOCK
    if score >= 0.3:
        return Recommendation.WARN
    return Recommendation.ALLOW


def scan_text(
    text: str,
    *,
    session_id: str | None = None,
    frequency_tracker: FrequencyTracker | None = None,
) -> InjectionScanResult:
    """Run all five scanners on the given text and return a composite result.

    This is the standalone scanner entry point, usable outside the middleware
    pipeline for scanning tool results, RAG content, etc.
    """
    if not text or not isinstance(text, str):
        return InjectionScanResult(
            score=0.0,
            detected_patterns=[],
            scanner_hits=[],
            recommendation=Recommendation.ALLOW,
        )

    # Run the four text-based scanners
    kw_score, kw_hits = keyword_scanner(text)
    enc_score, enc_hits = encoding_scanner(text)
    struct_score, struct_hits = structure_scanner(text)
    sem_score, sem_hits = semantic_scanner(text)

    # Pre-frequency composite (used to decide whether to record)
    pre_score = (
        kw_score * _SCANNER_WEIGHTS["keyword"]
        + enc_score * _SCANNER_WEIGHTS["encoding"]
        + struct_score * _SCANNER_WEIGHTS["structure"]
        + sem_score * _SCANNER_WEIGHTS["semantic"]
    )

    # Frequency scanner
    freq_score = 0.0
    freq_hits: list[ScannerHit] = []
    if frequency_tracker is not None and session_id:
        freq_score, freq_hits = frequency_tracker.record_and_score(session_id, pre_score)

    # Composite score
    composite = (
        kw_score * _SCANNER_WEIGHTS["keyword"]
        + enc_score * _SCANNER_WEIGHTS["encoding"]
        + struct_score * _SCANNER_WEIGHTS["structure"]
        + sem_score * _SCANNER_WEIGHTS["semantic"]
        + freq_score * _SCANNER_WEIGHTS["frequency"]
    )
    composite = min(composite, 1.0)

    all_hits = kw_hits + enc_hits + struct_hits + sem_hits + freq_hits
    detected = [h.pattern for h in all_hits]

    return InjectionScanResult(
        score=round(composite, 4),
        detected_patterns=detected,
        scanner_hits=all_hits,
        recommendation=_classify(composite),
    )


def scan_tool_result(
    result: Any,
    *,
    session_id: str | None = None,
    frequency_tracker: FrequencyTracker | None = None,
) -> InjectionScanResult:
    """Scan a tool result (dict, list, string) for indirect injection payloads."""
    text = _extract_text(result)
    return scan_text(text, session_id=session_id, frequency_tracker=frequency_tracker)


def _extract_text(result: Any, depth: int = 0) -> str:
    """Recursively extract text content from tool results."""
    if depth > 3:
        return ""
    if not result:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        return " ".join(_extract_text(item, depth + 1) for item in result if item)
    if isinstance(result, dict):
        parts: list[str] = []
        # Handle OpenAI/Anthropic content block format
        if isinstance(result.get("content"), list):
            for item in result["content"]:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
        for value in result.values():
            if isinstance(value, str) and len(value) > 10:
                parts.append(value)
            elif isinstance(value, (dict, list)):
                nested = _extract_text(value, depth + 1)
                if nested:
                    parts.append(nested)
        return " ".join(parts)
    return ""


# ---------------------------------------------------------------------------
# Middleware integration
# ---------------------------------------------------------------------------


class InjectionDetectorMiddleware(Middleware):
    """Middleware that scans incoming messages for prompt injection attempts.

    On BLOCK, raises ``PermissionError``. On WARN, logs and attaches metadata
    but allows the message through. On ALLOW, passes through silently.
    """

    def __init__(
        self,
        *,
        block_on_detection: bool = True,
        frequency_tracker: FrequencyTracker | None = None,
    ) -> None:
        self._block = block_on_detection
        self._freq_tracker = frequency_tracker or FrequencyTracker()

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        result = scan_text(
            message.content,
            session_id=message.session_id,
            frequency_tracker=self._freq_tracker,
        )

        if result.recommendation == Recommendation.BLOCK and self._block:
            logger.warning(
                "Injection BLOCKED: score=%.4f patterns=%s session=%s",
                result.score,
                result.detected_patterns,
                message.session_id,
            )
            raise PermissionError(
                f"Prompt injection detected (score={result.score:.2f}, "
                f"recommendation=BLOCK). Patterns: {result.detected_patterns}"
            )

        if result.recommendation == Recommendation.WARN:
            logger.info(
                "Injection WARN: score=%.4f patterns=%s session=%s",
                result.score,
                result.detected_patterns,
                message.session_id,
            )
            ctx.extra["injection_scan"] = {
                "score": result.score,
                "recommendation": result.recommendation.value,
                "patterns": result.detected_patterns,
            }

        return await next_(message, ctx)
