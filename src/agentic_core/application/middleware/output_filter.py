"""Output filter middleware for scanning outgoing messages.

Detects and redacts the following in LLM responses:
- System prompt leakage patterns
- Internal tool name exposure
- API key / JWT / secret patterns
- Error stack traces with internal paths

Can be used as middleware in the pipeline or as a standalone filter.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

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


class LeakageType(str, Enum):
    SYSTEM_PROMPT = "system_prompt_leak"
    TOOL_NAME = "internal_tool_exposure"
    SECRET = "secret_exposure"
    STACK_TRACE = "stack_trace_leak"


@dataclass(frozen=True)
class LeakageHit:
    leak_type: LeakageType
    pattern_name: str
    matched_text: str


@dataclass(frozen=True)
class OutputFilterResult:
    """Result of output filtering."""

    has_leakage: bool
    hits: list[LeakageHit]
    filtered_text: str


# ---------------------------------------------------------------------------
# System prompt leakage patterns
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"my\s+system\s+prompt\s+(?:is|says|reads|states)", re.IGNORECASE),
     "my-system-prompt-is"),
    (re.compile(r"(?:here\s+(?:is|are)\s+)?my\s+(?:system\s+)?instructions?\s*:", re.IGNORECASE),
     "my-instructions"),
    (re.compile(r"i\s+was\s+(?:told|instructed|programmed)\s+to", re.IGNORECASE),
     "i-was-instructed"),
    (re.compile(r"my\s+(?:original|initial|base)\s+(?:prompt|instructions)", re.IGNORECASE),
     "my-original-prompt"),
    (re.compile(r"the\s+system\s+prompt\s+(?:says|reads|is|contains)", re.IGNORECASE),
     "the-system-prompt-says"),
    (re.compile(r"according\s+to\s+my\s+(?:system\s+)?(?:prompt|instructions)", re.IGNORECASE),
     "according-to-my-prompt"),
    (re.compile(r"^system\s*:\s*.{20,}", re.IGNORECASE | re.MULTILINE),
     "system-colon-content"),
    (re.compile(r"<system>.*?</system>", re.IGNORECASE | re.DOTALL),
     "system-xml-block"),
]

# ---------------------------------------------------------------------------
# Internal tool name patterns
# ---------------------------------------------------------------------------

_INTERNAL_TOOL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"_internal_\w+", re.IGNORECASE), "internal-tool-prefix"),
    (re.compile(r"__(?:debug|admin|sudo|root)_\w+", re.IGNORECASE), "debug-admin-tool"),
    (re.compile(r"tool_(?:exec|run|invoke)_(?:raw|unsafe|privileged)", re.IGNORECASE),
     "privileged-tool-exec"),
]

# ---------------------------------------------------------------------------
# Secret / credential patterns
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # API keys
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "openai-api-key"),
    (re.compile(r"sk-ant-[a-zA-Z0-9\-]{20,}"), "anthropic-api-key"),
    (re.compile(r"sk-proj-[a-zA-Z0-9]{20,}"), "openai-project-key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36,}"), "github-pat"),
    (re.compile(r"gho_[a-zA-Z0-9]{36,}"), "github-oauth"),
    (re.compile(r"glpat-[a-zA-Z0-9\-]{20,}"), "gitlab-pat"),
    (re.compile(r"xoxb-[a-zA-Z0-9\-]{20,}"), "slack-bot-token"),
    (re.compile(r"xoxp-[a-zA-Z0-9\-]{20,}"), "slack-user-token"),
    (re.compile(r"AKIA[A-Z0-9]{16}"), "aws-access-key"),
    (re.compile(r"dckr_pat_[a-zA-Z0-9\-_]{20,}"), "docker-pat"),
    # JWTs
    (re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
     "jwt-token"),
    # Generic secret patterns
    (re.compile(r"(?:api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token)"
                r"\s*[:=]\s*['\"]?[a-zA-Z0-9\-_]{16,}['\"]?", re.IGNORECASE),
     "generic-secret-assignment"),
    # Bearer tokens in output
    (re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]{20,}"), "bearer-token"),
    # Connection strings
    (re.compile(r"(?:mongodb|postgres|mysql|redis)://[^\s]{20,}", re.IGNORECASE),
     "connection-string"),
]

# ---------------------------------------------------------------------------
# Stack trace / internal path patterns
# ---------------------------------------------------------------------------

_STACK_TRACE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"Traceback \(most recent call last\):.*?(?:\n\s+File.*?)+",
                re.DOTALL), "python-traceback"),
    (re.compile(r"at\s+\S+\((?:/[a-zA-Z0-9_./\-]+\.(?:js|ts|py|go|rs)):\d+:\d+\)"),
     "js-stack-frame"),
    (re.compile(r'File\s+"(/[a-zA-Z0-9_./\-]+\.py)",\s+line\s+\d+'),
     "python-file-path"),
    (re.compile(r"/(?:home|opt|srv|var|usr/local)/[a-zA-Z0-9_./\-]{10,}\.(?:py|js|ts|go|rs)"),
     "internal-file-path"),
    (re.compile(r"/app/[a-zA-Z0-9_./\-]{10,}\.(?:py|js|ts|go|rs)"),
     "container-file-path"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_REDACTION = "[FILTERED]"


def filter_output(text: str) -> OutputFilterResult:
    """Scan outgoing text for leakage patterns and return a filtered result.

    This is the standalone entry point, usable outside the middleware pipeline.
    """
    if not text or not isinstance(text, str):
        return OutputFilterResult(has_leakage=False, hits=[], filtered_text=text or "")

    hits: list[LeakageHit] = []
    filtered = text

    # System prompt leakage
    for pattern, name in _SYSTEM_PROMPT_PATTERNS:
        for m in pattern.finditer(text):
            hits.append(LeakageHit(
                leak_type=LeakageType.SYSTEM_PROMPT,
                pattern_name=name,
                matched_text=m.group(0)[:80],
            ))
        filtered = pattern.sub(_REDACTION, filtered)

    # Internal tool names
    for pattern, name in _INTERNAL_TOOL_PATTERNS:
        for m in pattern.finditer(text):
            hits.append(LeakageHit(
                leak_type=LeakageType.TOOL_NAME,
                pattern_name=name,
                matched_text=m.group(0)[:80],
            ))
        filtered = pattern.sub(_REDACTION, filtered)

    # Secrets
    for pattern, name in _SECRET_PATTERNS:
        for m in pattern.finditer(text):
            hits.append(LeakageHit(
                leak_type=LeakageType.SECRET,
                pattern_name=name,
                matched_text=m.group(0)[:20] + "***",
            ))
        filtered = pattern.sub(_REDACTION, filtered)

    # Stack traces
    for pattern, name in _STACK_TRACE_PATTERNS:
        for m in pattern.finditer(text):
            hits.append(LeakageHit(
                leak_type=LeakageType.STACK_TRACE,
                pattern_name=name,
                matched_text=m.group(0)[:80],
            ))
        filtered = pattern.sub(_REDACTION, filtered)

    return OutputFilterResult(
        has_leakage=len(hits) > 0,
        hits=hits,
        filtered_text=filtered,
    )


# ---------------------------------------------------------------------------
# Middleware integration
# ---------------------------------------------------------------------------


class OutputFilterMiddleware(Middleware):
    """Middleware that filters outgoing assistant messages for leakage.

    Applied after the handler returns the response. Redacts any detected
    secrets, system prompt leaks, internal tool names, or stack traces.
    """

    def __init__(self, *, enabled: bool = True, log_hits: bool = True) -> None:
        self._enabled = enabled
        self._log_hits = log_hits

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        result = await next_(message, ctx)

        if not self._enabled or result.role != "assistant":
            return result

        filter_result = filter_output(result.content)

        if filter_result.has_leakage:
            if self._log_hits:
                logger.warning(
                    "Output filter caught %d leakage(s) in session=%s: %s",
                    len(filter_result.hits),
                    result.session_id,
                    [(h.leak_type.value, h.pattern_name) for h in filter_result.hits],
                )

            # Rebuild message with filtered content
            from agentic_core.domain.value_objects.messages import AgentMessage as Msg

            result = Msg(
                id=result.id,
                session_id=result.session_id,
                persona_id=result.persona_id,
                role=result.role,
                content=filter_result.filtered_text,
                metadata={
                    **dict(result.metadata),
                    "output_filter": {
                        "leakage_count": len(filter_result.hits),
                        "types": list({h.leak_type.value for h in filter_result.hits}),
                    },
                },
                timestamp=result.timestamp,
                trace_id=result.trace_id,
            )

        return result
