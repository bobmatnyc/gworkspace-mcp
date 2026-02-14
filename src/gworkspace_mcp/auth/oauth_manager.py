"""Simplified OAuth manager for Google Workspace authentication.

This module provides a streamlined OAuth2 authentication flow
specifically for Google Workspace services using google-auth-oauthlib.

Environment Variables:
    GOOGLE_OAUTH_CLIENT_ID: Google OAuth client ID (required)
    GOOGLE_OAUTH_CLIENT_SECRET: Google OAuth client secret (required)
    GOOGLE_OAUTH_REDIRECT_URI: Redirect URI (default: http://127.0.0.1:8789/callback)
        Supports custom paths like /callback for Web Application OAuth clients.
"""

import asyncio
import os
import secrets
import webbrowser
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from gworkspace_mcp.auth.models import OAuthToken, StoredToken, TokenMetadata
from gworkspace_mcp.auth.token_storage import TokenStorage

# Google Workspace OAuth scopes
GOOGLE_WORKSPACE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",  # Full Slides access
]

# OAuth configuration defaults
DEFAULT_OAUTH_HOST = "127.0.0.1"
DEFAULT_OAUTH_PORT = 8789
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8789/callback"


class OAuthManager:
    """OAuth authentication manager for Google Workspace.

    Handles the complete OAuth2 flow including authorization,
    token exchange, storage, and refresh.

    Attributes:
        storage: Token storage instance for persisting credentials.

    Example:
        ```python
        manager = OAuthManager()

        # Authenticate with Google
        token = await manager.authenticate(scopes=GOOGLE_WORKSPACE_SCOPES)

        # Check token status
        status, stored = manager.get_status()
        if status == TokenStatus.EXPIRED:
            token = await manager.refresh_if_needed()
        ```
    """

    def __init__(self, storage: TokenStorage | None = None) -> None:
        """Initialize OAuth manager.

        Args:
            storage: Token storage instance. Creates default if not provided.
        """
        self.storage = storage or TokenStorage()
        self._service_name = "gworkspace-mcp"

    def has_valid_tokens(self) -> bool:
        """Check if valid tokens exist.

        Returns:
            True if valid tokens exist, False otherwise.
        """
        from gworkspace_mcp.auth.models import TokenStatus

        status = self.storage.get_status(self._service_name)
        return status == TokenStatus.VALID

    @property
    def token_path(self) -> Path:
        """Get the token storage path.

        Returns:
            Path to the tokens.json file.
        """
        return self.storage.token_path

    def _credentials_to_token(self, credentials: Credentials, scopes: list[str]) -> OAuthToken:
        """Convert google-auth Credentials to OAuthToken.

        Args:
            credentials: Google OAuth2 credentials.
            scopes: List of granted scopes.

        Returns:
            OAuthToken with all credential data.
        """
        # Get expiration time
        if credentials.expiry:
            expires_at = credentials.expiry
            # Ensure timezone-aware
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        else:
            # Default to 1 hour expiration
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        return OAuthToken(  # nosec B106 - "Bearer" is OAuth token type, not a password
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
            scopes=scopes,
            token_type="Bearer",
        )

    def _token_to_credentials(self, token: OAuthToken) -> Credentials:
        """Convert OAuthToken to google-auth Credentials.

        Args:
            token: OAuth token to convert.

        Returns:
            Google OAuth2 credentials.
        """
        return Credentials(  # nosec B106 - token_uri is public Google OAuth endpoint
            token=token.access_token,
            refresh_token=token.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=token.scopes,
        )

    async def authenticate(
        self,
        scopes: list[str] | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> OAuthToken:
        """Perform complete OAuth2 authentication flow.

        Uses google-auth-oauthlib Flow for Web Application OAuth with local server.
        Supports custom redirect URIs like http://127.0.0.1:8789/callback.

        Args:
            scopes: OAuth scopes to request. Uses GOOGLE_WORKSPACE_SCOPES if not specified.
            client_id: Google OAuth client ID. Required if not set in environment.
            client_secret: Google OAuth client secret. Required if not set in environment.

        Returns:
            OAuthToken containing access and refresh tokens.

        Raises:
            ValueError: If client ID/secret not provided.
            Exception: If authentication fails.
        """
        if scopes is None:
            scopes = GOOGLE_WORKSPACE_SCOPES

        if not client_id or not client_secret:
            raise ValueError(
                "Client ID and secret required. "
                "Pass as arguments or set GOOGLE_OAUTH_CLIENT_ID and "
                "GOOGLE_OAUTH_CLIENT_SECRET environment variables."
            )

        # Get redirect URI from environment (supports custom paths like /callback)
        redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)

        # Create client config for Web Application
        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

        # Run OAuth flow in executor (it's blocking)
        loop = asyncio.get_event_loop()
        credentials = await loop.run_in_executor(
            None, self._run_oauth_flow, client_config, scopes, redirect_uri
        )

        # Convert to our token model
        token = self._credentials_to_token(credentials, scopes)

        # Store token
        metadata = TokenMetadata(
            service_name=self._service_name,
            provider="google",
        )
        self.storage.store(self._service_name, token, metadata)

        return token

    def _run_oauth_flow(
        self, client_config: dict, scopes: list[str], redirect_uri: str
    ) -> Credentials:
        """Run the OAuth flow (blocking operation).

        Uses Web Application OAuth flow with custom redirect URI support.
        Opens browser for authorization and starts local server to receive callback.

        Args:
            client_config: Google OAuth client configuration (web type).
            scopes: List of OAuth scopes.
            redirect_uri: Full redirect URI including path (e.g., http://127.0.0.1:8789/callback).

        Returns:
            Google OAuth2 credentials.
        """
        # Create flow for web application
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri=redirect_uri,
        )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Get authorization URL
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=state,
        )

        # Parse redirect URI to get host, port, and path
        parsed = urlparse(redirect_uri)
        host = parsed.hostname or DEFAULT_OAUTH_HOST
        port = parsed.port or DEFAULT_OAUTH_PORT
        callback_path = parsed.path or "/callback"

        # Create callback handler
        auth_code: list[str | None] = [None]
        error_message: list[str | None] = [None]

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            """HTTP handler for OAuth callback."""

            def log_message(self, format: str, *args) -> None:
                """Suppress HTTP server logs."""
                pass

            def do_GET(self) -> None:
                """Handle GET request from OAuth redirect."""
                # Parse the request path
                request_parsed = urlparse(self.path)

                # Only handle the callback path
                if request_parsed.path != callback_path:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Not Found")
                    return

                # Parse query parameters
                query_params = parse_qs(request_parsed.query)

                # Check for error
                if "error" in query_params:
                    error_message[0] = query_params["error"][0]
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Authentication Failed</h1>"
                        b"<p>Please close this window and try again.</p></body></html>"
                    )
                    return

                # Get authorization code
                if "code" in query_params:
                    auth_code[0] = query_params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Authentication Successful!</h1>"
                        b"<p>You can close this window and return to the terminal.</p>"
                        b"</body></html>"
                    )
                else:
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Authentication Failed</h1>"
                        b"<p>No authorization code received.</p></body></html>"
                    )

        # Start local server
        server = HTTPServer((host, port), OAuthCallbackHandler)
        server.timeout = 300  # 5 minute timeout

        # Open browser with authorization URL
        print("Opening browser for Google authorization...")
        print(f"If browser doesn't open, visit: {auth_url}")
        webbrowser.open(auth_url)

        # Wait for single callback request
        server.handle_request()
        server.server_close()

        # Check for errors
        if error_message[0]:
            raise Exception(f"OAuth authentication failed: {error_message[0]}")

        if not auth_code[0]:
            raise Exception("No authorization code received from Google")

        # Exchange code for tokens
        flow.fetch_token(code=auth_code[0])

        return flow.credentials

    async def refresh_if_needed(self) -> OAuthToken | None:
        """Refresh token if expired or about to expire.

        Returns:
            New OAuthToken if refreshed, existing token if still valid,
            None if no token exists or refresh failed.
        """
        stored = self.storage.retrieve(self._service_name)
        if stored is None:
            return None

        # Check if token is still valid
        if not stored.token.is_expired():
            return stored.token

        # Need to refresh
        if stored.token.refresh_token is None:
            return None

        # Convert to credentials and refresh
        credentials = self._token_to_credentials(stored.token)

        # Run refresh in executor (blocking)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, credentials.refresh, Request())

        # Convert back to our token model
        new_token = self._credentials_to_token(credentials, stored.token.scopes)

        # Update stored token
        stored.metadata.last_refreshed = datetime.now(timezone.utc)
        self.storage.store(self._service_name, new_token, stored.metadata)

        return new_token

    def get_status(self) -> tuple[str, StoredToken | None]:
        """Get the status of stored tokens.

        Returns:
            Tuple of (TokenStatus, StoredToken or None).
        """
        from gworkspace_mcp.auth.models import TokenStatus

        status = self.storage.get_status(self._service_name)
        stored = (
            self.storage.retrieve(self._service_name) if status != TokenStatus.MISSING else None
        )
        return (status, stored)

    def get_credentials(self) -> Credentials | None:
        """Get Google credentials for API use.

        Returns:
            Google OAuth2 credentials, or None if not authenticated.
        """
        stored = self.storage.retrieve(self._service_name)
        if stored is None:
            return None

        return self._token_to_credentials(stored.token)
