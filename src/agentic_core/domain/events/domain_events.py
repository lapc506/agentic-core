from __future__ import annotations

from agentic_core.shared_kernel.events import DomainEvent


class MessageProcessed(DomainEvent):
    session_id: str
    persona_id: str
    latency_ms: float
    token_count: int


class SessionCreated(DomainEvent):
    session_id: str
    persona_id: str
    user_id: str


class SLOBreached(DomainEvent):
    persona_id: str
    sli_name: str
    current_value: float
    target_value: float


class SkillOptimized(DomainEvent):
    skill_name: str
    old_score: float
    new_score: float
    version: int


class HumanEscalationRequested(DomainEvent):
    session_id: str
    persona_id: str
    prompt: str
    reason: str


class ErrorBudgetExhausted(DomainEvent):
    persona_id: str
    sli_name: str
    budget_remaining: float


class ToolDegraded(DomainEvent):
    tool_name: str
    reason: str


class ToolRecovered(DomainEvent):
    tool_name: str
