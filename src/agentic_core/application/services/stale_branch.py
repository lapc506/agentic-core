"""Stale branch detection and auto-remediation policy."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class BranchFreshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    DIVERGED = "diverged"


class StaleBranchPolicy(str, Enum):
    AUTO_REBASE = "auto_rebase"
    AUTO_MERGE_FORWARD = "auto_merge_forward"
    WARN_ONLY = "warn_only"
    BLOCK = "block"


@dataclass
class BranchStatus:
    branch: str
    freshness: BranchFreshness
    commits_behind: int = 0
    commits_ahead: int = 0
    missing_fixes: list[str] = None
    policy: StaleBranchPolicy = StaleBranchPolicy.WARN_ONLY

    def __post_init__(self):
        if self.missing_fixes is None:
            self.missing_fixes = []


class StaleBranchDetector:
    """Detects stale branches and recommends remediation."""

    def __init__(self, stale_threshold: int = 5) -> None:
        self._threshold = stale_threshold
        self._policies: dict[str, StaleBranchPolicy] = {}

    def set_policy(self, branch_pattern: str, policy: StaleBranchPolicy) -> None:
        self._policies[branch_pattern] = policy

    def assess(self, branch: str, commits_behind: int, commits_ahead: int = 0) -> BranchStatus:
        if commits_behind == 0 and commits_ahead == 0:
            freshness = BranchFreshness.FRESH
        elif commits_behind > 0 and commits_ahead > 0:
            freshness = BranchFreshness.DIVERGED
        elif commits_behind >= self._threshold:
            freshness = BranchFreshness.STALE
        else:
            freshness = BranchFreshness.FRESH

        policy = self._get_policy(branch)
        return BranchStatus(
            branch=branch, freshness=freshness,
            commits_behind=commits_behind, commits_ahead=commits_ahead,
            policy=policy,
        )

    def should_block(self, status: BranchStatus) -> bool:
        return status.freshness != BranchFreshness.FRESH and status.policy == StaleBranchPolicy.BLOCK

    def should_auto_fix(self, status: BranchStatus) -> bool:
        return status.freshness != BranchFreshness.FRESH and status.policy in (
            StaleBranchPolicy.AUTO_REBASE, StaleBranchPolicy.AUTO_MERGE_FORWARD,
        )

    def _get_policy(self, branch: str) -> StaleBranchPolicy:
        import fnmatch
        for pattern, policy in self._policies.items():
            if fnmatch.fnmatch(branch, pattern):
                return policy
        return StaleBranchPolicy.WARN_ONLY
