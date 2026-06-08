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
import base64
import hashlib
import os
import secrets
import socket
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
    # Identity scopes — required so the userinfo endpoint returns the account
    # email after authentication (fixes list_accounts returning email: null).
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    # Service scopes
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


def _find_free_port(preferred: int, host: str = DEFAULT_OAUTH_HOST) -> int:
    """Find an available local port, preferring ``preferred`` if free.

    Why: macOS keeps ports in TIME_WAIT after a failed/timed-out OAuth callback,
    so a hard-coded 8789 leaves users with `[Errno 48] Address already in use`
    and no way forward. Probing with SO_REUSEADDR and falling back to an
    OS-assigned port lets `workspace setup` recover automatically (issue #18).

    What: Tries to bind to ``(host, preferred)`` with SO_REUSEADDR set on the
    probe socket; if that raises OSError (port busy/blocked), rebinds to
    ``(host, 0)`` and returns the kernel-assigned port.

    Test: Bind a blocker socket to a chosen port, then call
    ``_find_free_port(that_port)`` and assert the returned port differs from
    the blocked one and is non-zero. Also call with a known-free port and
    assert it returns the same port.

    Args:
        preferred: Port to try first.
        host: Host/interface to bind on. Defaults to 127.0.0.1.

    Returns:
        An available port number on the given host.
    """
    # Try the preferred port first with SO_REUSEADDR so a stale TIME_WAIT
    # binding from a prior failed flow does not block recovery.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, preferred))
        return preferred
    except OSError:
        # Preferred port is unavailable — let the kernel assign any free port.
        pass
    finally:
        sock.close()

    fallback = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        fallback.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        fallback.bind((host, 0))
        return fallback.getsockname()[1]
    finally:
        fallback.close()


class OAuthManager:
    """OAuth authentication manager for Google Workspace.

    Handles the complete OAuth2 flow including authorization,
    token exchange, storage, and refresh. The authorization flow
    uses PKCE (Proof Key for Code Exchange, RFC 7636) with S256
    challenge method to protect against authorization code
    interception attacks.

    Supports named profiles so multiple Google accounts can be stored
    and used simultaneously. Pass ``profile`` to target a specific
    account; omit it to use the default profile ("gworkspace-mcp").

    Attributes:
        storage: Token storage instance for persisting credentials.

    Example:
        ```python
        manager = OAuthManager()

        # Authenticate with Google (uses PKCE internally)
        token = await manager.authenticate(scopes=GOOGLE_WORKSPACE_SCOPES)

        # Authenticate a second account under a named profile
        manager2 = OAuthManager(profile="work")
        token2 = await manager2.authenticate(scopes=GOOGLE_WORKSPACE_SCOPES)

        # Check token status
        status, stored = manager.get_status()
        if status == TokenStatus.EXPIRED:
            token = await manager.refresh_if_needed()
        ```
    """

    def __init__(
        self, storage: TokenStorage | None = None, profile: str = "gworkspace-mcp"
    ) -> None:
        """Initialize OAuth manager.

        Args:
            storage: Token storage instance. Creates default if not provided.
            profile: Named profile (account key) for token storage.
                Defaults to "gworkspace-mcp" for backward compatibility.
        """
        self.storage = storage or TokenStorage()
        self._service_name = profile

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
            client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
            scopes=token.scopes,
        )

    @staticmethod
    def _extract_email_from_id_token(id_token: str) -> str | None:
        """Extract the email claim from a Google id_token JWT without signature verification.

        Why: When the ``openid`` scope is granted, the token exchange returns a signed
        JWT ``id_token`` that contains the user's email.  Decoding the payload avoids
        an extra network call to the userinfo endpoint and works even when the
        userinfo endpoint is rate-limited or temporarily unavailable.

        What: Base64url-decodes the middle (payload) segment of the JWT and returns
        the ``email`` claim.  No signature verification is performed because the
        token was received directly from Google's token endpoint over TLS.

        Test: Pass a hand-crafted JWT string (header.payload.sig) where payload is
        base64url({"email": "x@example.com"}) and assert the method returns
        "x@example.com".  Pass a malformed string and assert None is returned.

        Args:
            id_token: Raw JWT string from the token exchange response.

        Returns:
            Email address from the ``email`` claim, or None if not present / malformed.
        """
        import base64
        import json as _json
        import logging as _logging

        try:
            parts = id_token.split(".")
            if len(parts) != 3:
                return None
            # Add padding for base64url decoding
            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64).decode())
            return payload.get("email")
        except Exception as exc:  # pragma: no cover — defensive; decode rarely fails
            _logging.getLogger(__name__).debug("id_token decode failed: %s", exc)
            return None

    async def _fetch_user_email(self, access_token: str, id_token: str | None = None) -> str | None:
        """Resolve the authenticated user's email address.

        Why: ``list_accounts`` must show which Google identity owns each profile so
        users can distinguish accounts and pass the correct ``account`` parameter.
        Without the identity scope the userinfo endpoint returns HTTP 401 and email
        is silently stored as None.

        What: First attempts to decode the ``email`` claim from the ``id_token`` JWT
        (no extra network call).  Falls back to a GET to the userinfo v2 endpoint
        if ``id_token`` is absent or does not contain an email.  Returns None and
        logs a clear warning (not a silent swallow) if both approaches fail.

        Test: (1) Mock ``id_token`` containing ``email`` — assert that email is
        returned and no HTTP call is made.  (2) Pass ``id_token=None`` with a mock
        urlopen that returns ``{"email": "u@g.com"}`` — assert the email is returned.
        (3) Pass ``id_token=None`` and mock urlopen to raise ``urllib.error.URLError``
        — assert None is returned and a warning is logged.

        Args:
            access_token: Valid Google OAuth access token.
            id_token: Optional JWT from the token exchange (present when ``openid``
                scope was granted).  Decoding this avoids an extra HTTP round-trip.

        Returns:
            User's email address, or None if resolution fails.
        """
        import json as _json
        import logging as _logging
        import urllib.error
        import urllib.request

        logger = _logging.getLogger(__name__)

        # Prefer id_token decoding — no extra network call.
        if id_token:
            email = self._extract_email_from_id_token(id_token)
            if email:
                return email

        # Fallback: call the userinfo endpoint.
        try:
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                data = _json.loads(resp.read().decode())
                return data.get("email")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                logger.warning(
                    "Could not resolve account email: Google userinfo returned 401 "
                    "(HTTP Unauthorized).  The token was likely minted without the "
                    "'openid' or 'userinfo.email' scope.  Re-authenticate with "
                    "'gworkspace-mcp authenticate' to mint a new token that includes "
                    "the identity scopes, then run 'list_accounts' again."
                )
            else:
                logger.warning(
                    "Could not resolve account email: userinfo endpoint returned HTTP %d — %s",
                    exc.code,
                    exc.reason,
                )
        except urllib.error.URLError as exc:
            logger.warning("Could not resolve account email: network error — %s", exc.reason)
        except Exception as exc:
            logger.warning("Could not resolve account email: unexpected error — %s", exc)
        return None

    async def authenticate(
        self,
        scopes: list[str] | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> OAuthToken:
        """Perform complete OAuth2 authentication flow.

        Uses google-auth-oauthlib Flow for Web Application OAuth with local server.
        Supports custom redirect URIs like http://127.0.0.1:8789/callback.

        After a successful token exchange the authenticated user's email is
        fetched from the Google userinfo endpoint and stored in ``TokenMetadata``.
        The first profile stored is automatically marked as the default.

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
        credentials = await asyncio.to_thread(
            self._run_oauth_flow, client_config, scopes, redirect_uri
        )

        # Convert to our token model
        token = self._credentials_to_token(credentials, scopes)

        # Resolve user email.  google-auth-oauthlib stores the id_token JWT on the
        # credentials object when the ``openid`` scope was granted; prefer it over
        # an extra HTTP round-trip.
        id_token: str | None = getattr(credentials, "id_token", None)
        email = await self._fetch_user_email(token.access_token, id_token=id_token)

        # Determine whether this should be the default profile.
        # Mark as default if it is the first profile being stored OR this profile
        # replaces the only existing one (same name) and no explicit default is set.
        existing_profiles = self.storage.list_profiles()
        has_explicit_default = any(p["is_default"] for p in existing_profiles)
        is_same_profile = any(p["profile_name"] == self._service_name for p in existing_profiles)
        should_be_default = (
            len(existing_profiles) == 0  # First profile ever
            or (is_same_profile and not has_explicit_default)  # Re-auth of only profile
        )

        # Store token
        metadata = TokenMetadata(
            service_name=self._service_name,
            provider="google",
            email=email,
            is_default=should_be_default,
        )
        self.storage.store(self._service_name, token, metadata)

        return token

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate a PKCE code_verifier and code_challenge pair.

        Implements RFC 7636 Proof Key for Code Exchange using the S256
        challenge method. The code_verifier is a high-entropy random string;
        the code_challenge is BASE64URL(SHA256(ASCII(code_verifier))) without
        padding characters.

        Returns:
            Tuple of (code_verifier, code_challenge) where:
                - code_verifier: URL-safe base64 string, ~86 chars (43-128 range).
                - code_challenge: BASE64URL-encoded SHA-256 digest of the verifier.
        """
        code_verifier = secrets.token_urlsafe(64)  # ~86 URL-safe base64 chars
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )
        return code_verifier, code_challenge

    def _run_oauth_flow(
        self, client_config: dict, scopes: list[str], redirect_uri: str
    ) -> Credentials:
        """Run the OAuth flow (blocking operation).

        Uses Web Application OAuth flow with custom redirect URI support and
        PKCE (Proof Key for Code Exchange, RFC 7636) with S256 challenge method
        to prevent authorization code interception attacks.
        Opens browser for authorization and starts local server to receive callback.

        Args:
            client_config: Google OAuth client configuration (web type).
            scopes: List of OAuth scopes.
            redirect_uri: Full redirect URI including path (e.g., http://127.0.0.1:8789/callback).

        Returns:
            Google OAuth2 credentials.
        """
        # Parse redirect URI to get host, port, and path
        parsed = urlparse(redirect_uri)
        host = parsed.hostname or DEFAULT_OAUTH_HOST
        requested_port = parsed.port or DEFAULT_OAUTH_PORT
        callback_path = parsed.path or "/callback"

        # Resolve the actual port BEFORE constructing the auth URL so the
        # redirect_uri sent to Google matches the port we'll actually listen on.
        # If the preferred port is taken (e.g. stale TIME_WAIT on macOS), we
        # transparently fall back to an OS-assigned free port. See issue #18.
        actual_port = _find_free_port(requested_port, host)
        if actual_port != requested_port:
            # Rebuild redirect_uri with the actual port. Note: this URI must
            # also be registered in the Google Cloud Console OAuth client for
            # the auth exchange to succeed. The user may need to add the
            # fallback URI (or a localhost redirect) in their console.
            scheme = parsed.scheme or "http"
            redirect_uri = f"{scheme}://{host}:{actual_port}{callback_path}"
            print(
                f"Port {requested_port} unavailable; using fallback port {actual_port}. "
                f"Ensure {redirect_uri} is registered in your Google Cloud Console "
                f"OAuth client (or use a port range registered there)."
            )

        port = actual_port

        # Update client_config redirect_uris to match the resolved redirect_uri
        # so Flow advertises the correct URI in the token exchange.
        client_config = {
            "web": {
                **client_config["web"],
                "redirect_uris": [redirect_uri],
            }
        }

        # Create flow for web application
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            redirect_uri=redirect_uri,
        )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Generate PKCE pair for authorization code interception protection (RFC 7636)
        code_verifier, code_challenge = self._generate_pkce_pair()

        # Get authorization URL with PKCE challenge (S256 method)
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=state,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        # Create callback handler
        auth_code: list[str | None] = [None]
        error_message: list[str | None] = [None]

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            """HTTP handler for OAuth callback."""

            def log_message(self, format: str, *args) -> None:
                """Suppress HTTP server logs."""
                del format, args

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

                # Validate CSRF state parameter
                returned_state = query_params.get("state", [None])[0]
                if returned_state != state:
                    error_message[0] = "state_mismatch"
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(
                        b"<html><body><h1>Authentication Failed</h1>"
                        b"<p>Invalid state parameter. Possible CSRF attack.</p></body></html>"
                    )
                    return

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

        # Start local server.
        # Set SO_REUSEADDR so the socket can rebind even if a prior failed
        # flow left the port in TIME_WAIT (issue #18). HTTPServer's
        # allow_reuse_address class attr is True on most platforms but we
        # also set it explicitly on the underlying socket to be defensive
        # across macOS/Linux/Windows.
        HTTPServer.allow_reuse_address = True
        server = HTTPServer((host, port), OAuthCallbackHandler)
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

        # Exchange code for tokens, supplying PKCE verifier to complete the challenge
        flow.fetch_token(code=auth_code[0], code_verifier=code_verifier)

        # google_auth_oauthlib.Flow always returns google.oauth2.credentials.Credentials
        # after fetch_token; cast to satisfy Pyright's union-type inference.
        assert isinstance(flow.credentials, Credentials)  # nosec B101
        return flow.credentials

    async def refresh_if_needed(self) -> OAuthToken | None:
        """Refresh token if expired or about to expire, with email backfill.

        Why: Expired tokens must be refreshed to keep API calls alive.  As a
        side-effect, if the stored profile has ``email: null`` (e.g. it was minted
        before the identity scopes were added) but the refreshed token now carries
        identity claims, we backfill the email so ``list_accounts`` shows it going
        forward — without requiring a full re-authentication.

        What: Retrieves the stored token; returns it unchanged if still valid;
        otherwise calls Google's token endpoint to refresh, then persists the new
        token.  If the metadata email is None after refresh, attempts to resolve it
        from the refreshed access token (and id_token if available).

        Test: Store an expired token with ``email=None``, mock ``credentials.refresh``
        to succeed, mock ``_fetch_user_email`` to return ``"u@g.com"``, then call
        ``refresh_if_needed`` and assert ``storage.retrieve().metadata.email`` equals
        ``"u@g.com"``.

        Returns:
            New OAuthToken if refreshed, existing token if still valid,
            None if no token exists or refresh failed.
        """
        stored = self.storage.retrieve(self._service_name)
        if stored is None:
            return None

        # Check if token is still valid
        if not stored.token.is_expired():
            # Backfill email even for valid tokens that have email=None.
            if stored.metadata.email is None:
                id_token: str | None = None  # No credentials object available here
                email = await self._fetch_user_email(stored.token.access_token, id_token=id_token)
                if email:
                    stored.metadata.email = email
                    self.storage.store(self._service_name, stored.token, stored.metadata)
            return stored.token

        # Need to refresh
        if stored.token.refresh_token is None:
            return None

        # Convert to credentials and refresh
        credentials = self._token_to_credentials(stored.token)

        # Run refresh in executor (blocking)
        await asyncio.to_thread(credentials.refresh, Request())

        # Convert back to our token model
        new_token = self._credentials_to_token(credentials, stored.token.scopes)

        # Backfill email if still missing after refresh.
        metadata = stored.metadata
        if metadata.email is None:
            refreshed_id_token: str | None = getattr(credentials, "id_token", None)
            email = await self._fetch_user_email(
                new_token.access_token, id_token=refreshed_id_token
            )
            if email:
                metadata.email = email

        # Update stored token
        metadata.last_refreshed = datetime.now(timezone.utc)
        self.storage.store(self._service_name, new_token, metadata)

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
