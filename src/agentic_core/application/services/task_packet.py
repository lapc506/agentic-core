"""Task packet — structured work contract for autonomous agent execution."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskPacket:
    """Structured contract between coordinator and executing agent."""
    objective: str = ""
    scope: str = ""
    repo: str = ""
    branch_policy: str = ""  # create_new, use_existing, worktree
    acceptance_tests: list[str] = field(default_factory=list)
    commit_policy: str = ""  # atomic, incremental, squash
    reporting_contract: str = ""  # on_complete, per_step, silent
    escalation_policy: str = ""  # auto_retry, escalate_immediately, ignore


def validate_packet(packet: TaskPacket) -> tuple[bool, list[str]]:
    """Validate that a task packet has all required fields."""
    errors: list[str] = []
    if not packet.objective:
        errors.append("objective is required")
    if not packet.scope:
        errors.append("scope is required")
    if not packet.repo:
        errors.append("repo is required")
    if not packet.branch_policy:
        errors.append("branch_policy is required")
    if not packet.acceptance_tests:
        errors.append("at least one acceptance_test is required")
    if not packet.commit_policy:
        errors.append("commit_policy is required")
    return len(errors) == 0, errors
