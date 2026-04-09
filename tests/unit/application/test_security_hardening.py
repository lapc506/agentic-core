"""Unit tests for security hardening: sandbox executor, privacy router,
credential vault, and network egress policy."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from agentic_core.application.services.credential_vault import (
    CredentialVault,
)
from agentic_core.application.services.network_egress import (
    EgressDecision,
    EgressRequest,
    NetworkEgressPolicy,
)
from agentic_core.application.services.privacy_router import (
    DataSensitivity,
    PrivacyRouter,
    RoutingDecision,
)
from agentic_core.application.services.sandbox_executor import (
    SandboxBackend,
    SandboxExecutor,
    SandboxPermission,
    SandboxPolicy,
)

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# Sandbox Executor
# ---------------------------------------------------------------------------


def test_sandbox_policy_check_denies_without_shell_permission() -> None:
    """Default policy lacks EXECUTE_SHELL, so every command is denied."""
    executor = SandboxExecutor()
    result = asyncio.get_event_loop().run_until_complete(
        executor.execute("echo hello"),
    )
    assert result.exit_code == 1
    assert any("Shell execution not permitted" in v for v in result.policy_violations)


def test_sandbox_denied_paths_blocks_sensitive_files() -> None:
    """Commands referencing denied paths are rejected."""
    policy = SandboxPolicy(
        permissions={SandboxPermission.EXECUTE_SHELL},
        denied_paths=["/etc/shadow"],
    )
    executor = SandboxExecutor(default_policy=policy)
    result = asyncio.get_event_loop().run_until_complete(
        executor.execute("cat /etc/shadow"),
    )
    assert result.exit_code == 1
    assert any("/etc/shadow" in v for v in result.policy_violations)


def test_sandbox_dangerous_commands_blocked() -> None:
    """Fork bombs and destructive patterns are caught."""
    policy = SandboxPolicy(
        permissions={SandboxPermission.EXECUTE_SHELL},
        denied_paths=[],
    )
    executor = SandboxExecutor(default_policy=policy)
    result = asyncio.get_event_loop().run_until_complete(
        executor.execute("rm -rf /"),
    )
    assert result.exit_code == 1
    assert any("Dangerous command pattern" in v for v in result.policy_violations)


def test_sandbox_local_execution_succeeds() -> None:
    """A safe command with shell permission runs and returns output."""
    policy = SandboxPolicy(
        permissions={SandboxPermission.EXECUTE_SHELL, SandboxPermission.READ_FILESYSTEM},
        denied_paths=[],
    )
    executor = SandboxExecutor(backend=SandboxBackend.LOCAL, default_policy=policy)
    result = asyncio.get_event_loop().run_until_complete(
        executor.execute("echo sandbox_ok"),
    )
    assert result.exit_code == 0
    assert "sandbox_ok" in result.stdout
    assert not result.timed_out
    # Audit log should have an "allowed" entry
    assert len(executor.audit_log) == 1
    assert executor.audit_log[0]["decision"] == "allowed"


# ---------------------------------------------------------------------------
# Privacy Router
# ---------------------------------------------------------------------------


def test_privacy_classify_public_data() -> None:
    """Plain text without sensitive patterns is classified as public."""
    router = PrivacyRouter()
    level = router.classify("Tell me about the weather in Madrid")
    assert level == DataSensitivity.PUBLIC


def test_privacy_classify_confidential_email() -> None:
    """Content with email addresses is classified as confidential."""
    router = PrivacyRouter()
    level = router.classify("Send this to user@example.com")
    assert level == DataSensitivity.CONFIDENTIAL


def test_privacy_route_confidential_to_local() -> None:
    """Confidential data is routed to the local model."""
    router = PrivacyRouter(local_model="ollama/mistral")
    result = router.route("Contact alice@corp.com for details")
    assert result.decision == RoutingDecision.LOCAL
    assert result.model == "ollama/mistral"
    assert result.sensitivity == DataSensitivity.CONFIDENTIAL


def test_privacy_block_restricted_data() -> None:
    """Data with SSN patterns is blocked entirely."""
    router = PrivacyRouter()
    result = router.route("My SSN is 123-45-6789")
    assert result.decision == RoutingDecision.BLOCKED
    assert result.model == ""
    assert result.sensitivity == DataSensitivity.RESTRICTED


# ---------------------------------------------------------------------------
# Credential Vault
# ---------------------------------------------------------------------------


def test_vault_store_and_list_masked() -> None:
    """Stored credentials appear masked in the listing."""
    vault = CredentialVault()
    vault.store("openai", "sk-abc123456789xyz")
    entries = vault.list_services()
    assert len(entries) == 1
    assert entries[0].name == "openai"
    # Masked: first 4 + **** + last 4
    assert entries[0].masked_value == "sk-a****9xyz"
    assert vault.service_count == 1


def test_vault_inject_header() -> None:
    """inject_header adds Bearer token to outbound headers."""
    vault = CredentialVault()
    vault.store("anthropic", "sk-ant-secret-key-12345")
    headers = vault.inject_header("anthropic", {"Content-Type": "application/json"})
    assert headers["Authorization"] == "Bearer sk-ant-secret-key-12345"
    assert headers["Content-Type"] == "application/json"
    # Access log should record the injection
    assert len(vault.access_log) == 1
    assert vault.access_log[0]["action"] == "inject_header"


def test_vault_revoke_removes_credential() -> None:
    """Revoking a credential removes it from the vault."""
    vault = CredentialVault()
    vault.store("slack", "xoxb-token-value")
    assert vault.service_count == 1
    revoked = vault.revoke("slack")
    assert revoked is True
    assert vault.service_count == 0
    # Revoking again returns False
    assert vault.revoke("slack") is False


def test_vault_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_from_env picks up AGENTIC_CRED_ prefixed env vars."""
    monkeypatch.setenv("AGENTIC_CRED_GITHUB", "ghp_testtoken123")
    monkeypatch.setenv("AGENTIC_CRED_DOCKER", "dckr_pat_abc")
    monkeypatch.setenv("UNRELATED_VAR", "should_not_load")
    vault = CredentialVault()
    count = vault.load_from_env()
    assert count == 2
    assert vault.service_count == 2
    assert vault.get_for_proxy("github") == "ghp_testtoken123"
    assert vault.get_for_proxy("docker") == "dckr_pat_abc"


# ---------------------------------------------------------------------------
# Network Egress Policy
# ---------------------------------------------------------------------------


def test_egress_default_allow_known_apis() -> None:
    """Default rules allow known AI API endpoints."""
    policy = NetworkEgressPolicy()
    req = EgressRequest(
        url="https://api.anthropic.com/v1/messages",
        agent_id="agent-1",
        tool_name="llm_call",
    )
    decision = policy.evaluate(req)
    assert decision == EgressDecision.ALLOW


def test_egress_deny_unknown_url() -> None:
    """URLs not matching any rule are denied by default."""
    policy = NetworkEgressPolicy()
    req = EgressRequest(
        url="https://evil.example.com/exfil",
        agent_id="agent-1",
        tool_name="http_fetch",
    )
    decision = policy.evaluate(req)
    assert decision == EgressDecision.DENY
    # Request should appear in pending
    pending = policy.get_pending()
    assert len(pending) == 1
    assert pending[0].url == "https://evil.example.com/exfil"


def test_egress_approve_pending_clears_queue() -> None:
    """Operator approval clears matching pending requests."""
    policy = NetworkEgressPolicy()
    req = EgressRequest(
        url="https://api.github.com/repos",
        agent_id="agent-1",
        tool_name="github_api",
    )
    policy.evaluate(req)  # Denied, goes to pending
    assert len(policy.get_pending()) == 1

    cleared = policy.approve_pending("https://api.github.com/*")
    assert cleared == 1
    assert len(policy.get_pending()) == 0

    # Now the same URL should be allowed
    decision = policy.evaluate(req)
    assert decision == EgressDecision.ALLOW


def test_egress_audit_log_records_decisions() -> None:
    """Every evaluation is recorded in the audit log."""
    policy = NetworkEgressPolicy()
    policy.evaluate(EgressRequest("https://api.openai.com/v1/chat", "a1", "chat"))
    policy.evaluate(EgressRequest("https://unknown.example.com", "a1", "fetch"))

    log = policy.audit_log
    assert len(log) == 2
    assert log[0]["decision"] == "allow"
    assert log[0]["url"] == "https://api.openai.com/v1/chat"
    assert log[1]["decision"] == "deny"
    assert log[1]["url"] == "https://unknown.example.com"
