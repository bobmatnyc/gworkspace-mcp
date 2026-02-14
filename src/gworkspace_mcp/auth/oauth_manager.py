"""Simplified OAuth manager for Google Workspace authentication.

This module provides a streamlined OAuth2 authentication flow
specifically for Google Workspace services using google-auth-oauthlib.

Environment Variables:
    GOOGLE_OAUTH_CLIENT_ID: Google OAuth client ID (required)
    GOOGLE_OAUTH_CLIENT_SECRET: Google OAuth client secret (required)
    GOOGLE_OAUTH_REDIRECT_URI: Redirect URI (default: http://localhost/)
        Port and host are automatically parsed from the URI.
        Example: http://127.0.0.1:8789/callback
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

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
DEFAULT_OAUTH_PORT = 0  # 0 = random available port
DEFAULT_REDIRECT_URI = "http://localhost/"


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

        Uses google-auth-oauthlib for the OAuth flow with local server.
        The authorization URL is always printed for the user to copy/paste.

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

        # For now, require credentials to be passed or use default
        # TODO: Support reading from client_secrets.json or environment
        if not client_id or not client_secret:
            raise ValueError(
                "Client ID and secret required. "
                "Pass as arguments or set GOOGLE_OAUTH_CLIENT_ID and "
                "GOOGLE_OAUTH_CLIENT_SECRET environment variables."
            )

        # Get redirect URI from environment and normalize it
        # (Google's InstalledAppFlow only supports root path "/")
        from urllib.parse import urlparse

        redirect_uri_env = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)
        parsed = urlparse(redirect_uri_env)

        # Construct normalized redirect URI (always use root path)
        if parsed.hostname and parsed.port:
            redirect_uri = f"http://{parsed.hostname}:{parsed.port}/"
        elif parsed.hostname:
            redirect_uri = f"http://{parsed.hostname}/"
        else:
            redirect_uri = DEFAULT_REDIRECT_URI

        # Create client config
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

        # Run OAuth flow in executor (it's blocking)
        loop = asyncio.get_event_loop()
        credentials = await loop.run_in_executor(None, self._run_oauth_flow, client_config, scopes)

        # Convert to our token model
        token = self._credentials_to_token(credentials, scopes)

        # Store token
        metadata = TokenMetadata(
            service_name=self._service_name,
            provider="google",
        )
        self.storage.store(self._service_name, token, metadata)

        return token

    def _run_oauth_flow(self, client_config: dict, scopes: list[str]) -> Credentials:
        """Run the OAuth flow (blocking operation).

        The authorization URL is always printed for the user to copy/paste.
        Browser is never opened automatically.

        Args:
            client_config: Google OAuth client configuration.
            scopes: List of OAuth scopes.

        Returns:
            Google OAuth2 credentials.

        Note:
            Host and port are parsed from GOOGLE_OAUTH_REDIRECT_URI.
            Defaults to localhost with random available port.

            IMPORTANT: Google's InstalledAppFlow.run_local_server() only supports
            the root path "/". Custom paths like "/callback" are NOT supported.
            Configure your Google Cloud Console redirect URI as:
            http://127.0.0.1:PORT/ (not http://127.0.0.1:PORT/callback)
        """
        import sys
        from urllib.parse import urlparse

        flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)

        # Get redirect URI and parse host/port from it
        redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "")

        host = "localhost"
        port = DEFAULT_OAUTH_PORT

        if redirect_uri:
            parsed = urlparse(redirect_uri)
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port:
                port = parsed.port

            # Warn if custom path is specified (not supported by run_local_server)
            if parsed.path and parsed.path not in ("/", ""):
                print(
                    f"Warning: Custom path '{parsed.path}' in redirect URI is ignored.\n"
                    f"   Google's OAuth flow only supports root path '/'.\n"
                    f"   Update your Google Cloud Console redirect URI to:\n"
                    f"   http://{host}:{port}/\n",
                    file=sys.stderr,
                )

        # Print helpful message - browser is never opened automatically
        print(
            "\n"
            "=================================================================\n"
            "MANUAL AUTHENTICATION REQUIRED\n"
            "=================================================================\n"
            "Open this URL in a browser on any device:\n"
            "  (URL will be displayed when the server starts)\n"
            "\n"
            "After authorizing, copy the URL from the browser's address bar\n"
            "and the server will complete the authentication.\n"
            "=================================================================\n",
            file=sys.stderr,
        )

        # Run local server (always uses root path "/")
        credentials = flow.run_local_server(host=host, port=port, open_browser=True)

        return credentials

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
