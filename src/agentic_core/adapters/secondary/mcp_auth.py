"""MCP OAuth 2.1 authentication and server discovery."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPServerInfo:
    """Discovered MCP server capabilities."""
    name: str
    url: str
    tools: list[str] = field(default_factory=list)
    auth_required: bool = False
    auth_url: str = ""
    token_url: str = ""
    scopes: list[str] = field(default_factory=list)


@dataclass
class OAuthToken:
    """OAuth 2.1 token pair."""
    access_token: str
    refresh_token: str | None = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    scope: str = ""


class PKCEChallenge:
    """Generate PKCE code verifier and challenge for OAuth 2.1."""

    def __init__(self) -> None:
        self.verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(self.verifier.encode()).digest()
        self.challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        self.method = "S256"


class MCPServerDiscovery:
    """Discover MCP servers via .well-known/mcp.json."""

    async def discover(self, base_url: str) -> MCPServerInfo | None:
        """Fetch MCP server info from .well-known endpoint.

        In production, this would make an HTTP request.
        For standalone demo, returns a mock or None.
        """
        # Production implementation:
        # resp = await httpx.get(f"{base_url}/.well-known/mcp.json")
        # data = resp.json()
        # return MCPServerInfo(...)

        logger.info("Discovering MCP server at %s", base_url)
        return None  # No discovery in standalone mode


class MCPOAuthClient:
    """OAuth 2.1 client for authenticating with remote MCP servers."""

    def __init__(
        self,
        client_id: str,
        redirect_uri: str = "http://localhost:8080/oauth/callback",
    ) -> None:
        self._client_id = client_id
        self._redirect_uri = redirect_uri
        self._tokens: dict[str, OAuthToken] = {}  # server_url -> token

    def create_auth_url(self, server: MCPServerInfo) -> tuple[str, PKCEChallenge]:
        """Generate authorization URL with PKCE challenge."""
        pkce = PKCEChallenge()
        params: dict[str, Any] = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": " ".join(server.scopes) if server.scopes else "tools:read tools:execute",
            "code_challenge": pkce.challenge,
            "code_challenge_method": pkce.method,
            "state": secrets.token_urlsafe(32),
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{server.auth_url}?{query}", pkce

    async def exchange_code(
        self,
        server: MCPServerInfo,
        code: str,
        pkce: PKCEChallenge,
    ) -> OAuthToken:
        """Exchange authorization code for tokens.

        In production, this would POST to the token endpoint.
        """
        # Production: POST to server.token_url with code + code_verifier
        token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            refresh_token=secrets.token_urlsafe(32),
        )
        self._tokens[server.url] = token
        logger.info("Obtained OAuth token for %s", server.url)
        return token

    async def refresh_token(self, server: MCPServerInfo) -> OAuthToken | None:
        """Refresh an expired token."""
        existing = self._tokens.get(server.url)
        if not existing or not existing.refresh_token:
            return None

        # Production: POST to server.token_url with refresh_token
        new_token = OAuthToken(
            access_token=secrets.token_urlsafe(32),
            refresh_token=existing.refresh_token,
        )
        self._tokens[server.url] = new_token
        logger.info("Refreshed OAuth token for %s", server.url)
        return new_token

    def get_token(self, server_url: str) -> OAuthToken | None:
        """Get stored token for a server."""
        return self._tokens.get(server_url)

    def revoke_token(self, server_url: str) -> bool:
        """Revoke and remove stored token."""
        if server_url in self._tokens:
            del self._tokens[server_url]
            return True
        return False

    @property
    def authenticated_servers(self) -> list[str]:
        """List of servers with valid tokens."""
        return list(self._tokens.keys())
