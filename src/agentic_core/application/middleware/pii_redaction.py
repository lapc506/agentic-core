from __future__ import annotations

import logging
import re

from agentic_core.application.middleware.base import (
    Middleware,
    NextHandler,
    RequestContext,
)
from agentic_core.domain.value_objects.messages import AgentMessage

logger = logging.getLogger(__name__)

# Regex patterns for common PII
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CREDIT_CARD_RE = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")

_REDACTION = "[REDACTED]"


def redact_pii(text: str) -> str:
    text = _EMAIL_RE.sub(_REDACTION, text)
    text = _PHONE_RE.sub(_REDACTION, text)
    text = _SSN_RE.sub(_REDACTION, text)
    text = _CREDIT_CARD_RE.sub(_REDACTION, text)
    return text


class PIIRedactionMiddleware(Middleware):
    """Strips PII from message content on both input and output."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    async def process(
        self, message: AgentMessage, ctx: RequestContext, next_: NextHandler,
    ) -> AgentMessage:
        if not self._enabled:
            return await next_(message, ctx)

        # Redact input
        cleaned_content = redact_pii(message.content)
        if cleaned_content != message.content:
            message = AgentMessage(
                id=message.id,
                session_id=message.session_id,
                persona_id=message.persona_id,
                role=message.role,
                content=cleaned_content,
                metadata=dict(message.metadata),
                timestamp=message.timestamp,
                trace_id=message.trace_id,
            )

        # Process
        result = await next_(message, ctx)

        # Redact output
        if isinstance(result, AgentMessage) and self._enabled:
            cleaned = redact_pii(result.content)
            if cleaned != result.content:
                result = AgentMessage(
                    id=result.id,
                    session_id=result.session_id,
                    persona_id=result.persona_id,
                    role=result.role,
                    content=cleaned,
                    metadata=dict(result.metadata),
                    timestamp=result.timestamp,
                    trace_id=result.trace_id,
                )

        return result
