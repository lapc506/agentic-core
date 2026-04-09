"""Unit tests for MCP OAuth 2.1 authentication and server discovery."""

from __future__ import annotations

import base64
import hashlib

import pytest

from agentic_core.adapters.secondary.mcp_auth import (
    MCPOAuthClient,
    MCPServerDiscovery,
    MCPServerInfo,
    OAuthToken,
    PKCEChallenge,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_server(
    name: str = "Test MCP Server",
    url: str = "https://mcp.example.com",
    auth_required: bool = True,
    auth_url: str = "https://mcp.example.com/oauth/authorize",
    token_url: str = "https://mcp.example.com/oauth/token",
    scopes: list[str] | None = None,
    tools: list[str] | None = None,
) -> MCPServerInfo:
    return MCPServerInfo(
        name=name,
        url=url,
        tools=tools or [],
        auth_required=auth_required,
        auth_url=auth_url,
        token_url=token_url,
        scopes=scopes or [],
    )


def make_client(
    client_id: str = "test-client",
    redirect_uri: str = "http://localhost:8080/oauth/callback",
) -> MCPOAuthClient:
    return MCPOAuthClient(client_id=client_id, redirect_uri=redirect_uri)


# ---------------------------------------------------------------------------
# 1. MCPServerInfo dataclass
# ---------------------------------------------------------------------------


def test_mcp_server_info_defaults():
    server = MCPServerInfo(name="minimal", url="https://srv.example.com")
    assert server.name == "minimal"
    assert server.url == "https://srv.example.com"
    assert server.tools == []
    assert server.auth_required is False
    assert server.auth_url == ""
    assert server.token_url == ""
    assert server.scopes == []


def test_mcp_server_info_full():
    server = make_server(
        name="Full Server",
        scopes=["tools:read", "tools:execute"],
        tools=["search", "summarize"],
    )
    assert server.name == "Full Server"
    assert server.auth_required is True
    assert "tools:read" in server.scopes
    assert "search" in server.tools


def test_mcp_server_info_mutable_defaults_are_independent():
    s1 = MCPServerInfo(name="a", url="https://a.example.com")
    s2 = MCPServerInfo(name="b", url="https://b.example.com")
    s1.tools.append("tool_x")
    assert "tool_x" not in s2.tools


# ---------------------------------------------------------------------------
# 2. PKCEChallenge — verifier length and challenge correctness
# ---------------------------------------------------------------------------


def test_pkce_verifier_is_url_safe_string():
    pkce = PKCEChallenge()
    # token_urlsafe(64) yields a string; no padding chars allowed in verifiers
    assert isinstance(pkce.verifier, str)
    assert len(pkce.verifier) > 0


def test_pkce_verifier_minimum_entropy():
    # RFC 7636 requires verifier to be at least 43 chars (base64url of 32 bytes)
    # secrets.token_urlsafe(64) gives ~85 chars
    pkce = PKCEChallenge()
    assert len(pkce.verifier) >= 43


def test_pkce_challenge_is_sha256_of_verifier():
    pkce = PKCEChallenge()
    digest = hashlib.sha256(pkce.verifier.encode()).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    assert pkce.challenge == expected


def test_pkce_challenge_method_is_s256():
    pkce = PKCEChallenge()
    assert pkce.method == "S256"


def test_pkce_challenge_has_no_padding():
    pkce = PKCEChallenge()
    assert "=" not in pkce.challenge


def test_pkce_generates_unique_verifiers():
    pkce1 = PKCEChallenge()
    pkce2 = PKCEChallenge()
    assert pkce1.verifier != pkce2.verifier
    assert pkce1.challenge != pkce2.challenge


# ---------------------------------------------------------------------------
# 3. Auth URL generation
# ---------------------------------------------------------------------------


def test_create_auth_url_contains_required_params():
    client = make_client(client_id="my-client")
    server = make_server(auth_url="https://auth.example.com/authorize")
    url, pkce = client.create_auth_url(server)

    assert url.startswith("https://auth.example.com/authorize?")
    assert "client_id=my-client" in url
    assert "response_type=code" in url
    assert "code_challenge_method=S256" in url
    assert pkce.challenge in url
    assert "state=" in url


def test_create_auth_url_uses_server_scopes():
    client = make_client()
    server = make_server(scopes=["read", "write"])
    url, _ = client.create_auth_url(server)
    assert "scope=read+write" in url or "scope=read%20write" in url or "scope=read write" in url


def test_create_auth_url_uses_default_scopes_when_none():
    client = make_client()
    server = make_server(scopes=[])
    url, _ = client.create_auth_url(server)
    assert "scope=" in url
    assert "tools" in url


def test_create_auth_url_returns_pkce_object():
    client = make_client()
    server = make_server()
    url, pkce = client.create_auth_url(server)
    assert isinstance(pkce, PKCEChallenge)
    assert pkce.method == "S256"


def test_create_auth_url_contains_redirect_uri():
    client = make_client(redirect_uri="https://app.example.com/cb")
    server = make_server()
    url, _ = client.create_auth_url(server)
    assert "redirect_uri=" in url
    assert "app.example.com" in url


def test_create_auth_url_state_is_unique_across_calls():
    client = make_client()
    server = make_server()
    url1, _ = client.create_auth_url(server)
    url2, _ = client.create_auth_url(server)
    # Extract state values and compare — they must differ
    state1 = [p for p in url1.split("&") if p.startswith("state=")][0]
    state2 = [p for p in url2.split("&") if p.startswith("state=")][0]
    assert state1 != state2


# ---------------------------------------------------------------------------
# 4. Code exchange
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exchange_code_returns_oauth_token():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    token = await client.exchange_code(server, code="auth_code_123", pkce=pkce)
    assert isinstance(token, OAuthToken)
    assert token.access_token
    assert token.refresh_token is not None


@pytest.mark.asyncio
async def test_exchange_code_stores_token_for_server():
    client = make_client()
    server = make_server(url="https://mcp.example.com")
    pkce = PKCEChallenge()
    token = await client.exchange_code(server, code="code", pkce=pkce)
    stored = client.get_token("https://mcp.example.com")
    assert stored is token


@pytest.mark.asyncio
async def test_exchange_code_token_type_is_bearer():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    token = await client.exchange_code(server, code="code", pkce=pkce)
    assert token.token_type == "Bearer"


@pytest.mark.asyncio
async def test_exchange_code_overwrites_existing_token():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    token1 = await client.exchange_code(server, code="code1", pkce=pkce)
    token2 = await client.exchange_code(server, code="code2", pkce=pkce)
    stored = client.get_token(server.url)
    assert stored is token2
    assert stored is not token1


# ---------------------------------------------------------------------------
# 5. Token refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_token_returns_new_access_token():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    original = await client.exchange_code(server, code="code", pkce=pkce)
    refreshed = await client.refresh_token(server)
    assert refreshed is not None
    assert refreshed.access_token != original.access_token


@pytest.mark.asyncio
async def test_refresh_token_preserves_refresh_token():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    original = await client.exchange_code(server, code="code", pkce=pkce)
    original_rt = original.refresh_token
    refreshed = await client.refresh_token(server)
    assert refreshed is not None
    assert refreshed.refresh_token == original_rt


@pytest.mark.asyncio
async def test_refresh_token_returns_none_when_no_token():
    client = make_client()
    server = make_server(url="https://no-token.example.com")
    result = await client.refresh_token(server)
    assert result is None


@pytest.mark.asyncio
async def test_refresh_token_returns_none_when_no_refresh_token():
    client = make_client()
    server = make_server()
    # Manually inject a token without a refresh_token
    client._tokens[server.url] = OAuthToken(access_token="at", refresh_token=None)
    result = await client.refresh_token(server)
    assert result is None


@pytest.mark.asyncio
async def test_refresh_token_updates_stored_token():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    await client.exchange_code(server, code="code", pkce=pkce)
    refreshed = await client.refresh_token(server)
    stored = client.get_token(server.url)
    assert stored is refreshed


# ---------------------------------------------------------------------------
# 6. Token revocation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_token_returns_true_when_token_exists():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    await client.exchange_code(server, code="code", pkce=pkce)
    result = client.revoke_token(server.url)
    assert result is True


@pytest.mark.asyncio
async def test_revoke_token_removes_stored_token():
    client = make_client()
    server = make_server()
    pkce = PKCEChallenge()
    await client.exchange_code(server, code="code", pkce=pkce)
    client.revoke_token(server.url)
    assert client.get_token(server.url) is None


def test_revoke_token_returns_false_when_not_found():
    client = make_client()
    result = client.revoke_token("https://nonexistent.example.com")
    assert result is False


@pytest.mark.asyncio
async def test_revoke_token_only_removes_targeted_server():
    client = make_client()
    server_a = make_server(url="https://a.example.com")
    server_b = make_server(url="https://b.example.com")
    pkce = PKCEChallenge()
    await client.exchange_code(server_a, code="code_a", pkce=pkce)
    await client.exchange_code(server_b, code="code_b", pkce=pkce)
    client.revoke_token(server_a.url)
    assert client.get_token(server_a.url) is None
    assert client.get_token(server_b.url) is not None


# ---------------------------------------------------------------------------
# 7. Authenticated servers property
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authenticated_servers_empty_initially():
    client = make_client()
    assert client.authenticated_servers == []


@pytest.mark.asyncio
async def test_authenticated_servers_lists_all_authenticated():
    client = make_client()
    server_a = make_server(url="https://a.example.com")
    server_b = make_server(url="https://b.example.com")
    pkce = PKCEChallenge()
    await client.exchange_code(server_a, code="code_a", pkce=pkce)
    await client.exchange_code(server_b, code="code_b", pkce=pkce)
    servers = client.authenticated_servers
    assert "https://a.example.com" in servers
    assert "https://b.example.com" in servers
    assert len(servers) == 2


@pytest.mark.asyncio
async def test_authenticated_servers_decrements_after_revoke():
    client = make_client()
    server = make_server(url="https://mcp.example.com")
    pkce = PKCEChallenge()
    await client.exchange_code(server, code="code", pkce=pkce)
    assert len(client.authenticated_servers) == 1
    client.revoke_token(server.url)
    assert client.authenticated_servers == []


# ---------------------------------------------------------------------------
# 8. Server discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_discovery_returns_none_in_standalone_mode():
    discovery = MCPServerDiscovery()
    result = await discovery.discover("https://mcp.example.com")
    assert result is None


@pytest.mark.asyncio
async def test_server_discovery_accepts_any_base_url():
    discovery = MCPServerDiscovery()
    # Should not raise for any well-formed URL
    result = await discovery.discover("http://localhost:3000")
    assert result is None


@pytest.mark.asyncio
async def test_server_discovery_trailing_slash_handled():
    discovery = MCPServerDiscovery()
    result = await discovery.discover("https://mcp.example.com/")
    assert result is None


# ---------------------------------------------------------------------------
# 9. OAuthToken dataclass
# ---------------------------------------------------------------------------


def test_oauth_token_defaults():
    token = OAuthToken(access_token="at_xyz")
    assert token.access_token == "at_xyz"
    assert token.refresh_token is None
    assert token.expires_in == 3600
    assert token.token_type == "Bearer"
    assert token.scope == ""


def test_oauth_token_full_construction():
    token = OAuthToken(
        access_token="at",
        refresh_token="rt",
        expires_in=7200,
        token_type="Bearer",
        scope="tools:read tools:execute",
    )
    assert token.refresh_token == "rt"
    assert token.expires_in == 7200
    assert token.scope == "tools:read tools:execute"


# ---------------------------------------------------------------------------
# 10. get_token returns None for unknown server
# ---------------------------------------------------------------------------


def test_get_token_returns_none_for_unknown_server():
    client = make_client()
    assert client.get_token("https://unknown.example.com") is None
