"""Unit tests for OAuthManager class.

Tests cover authentication flow, token refresh, and credential management.
"""

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from gworkspace_mcp.auth.models import OAuthToken, TokenMetadata, TokenStatus
from gworkspace_mcp.auth.oauth_manager import (
    DEFAULT_OAUTH_HOST,
    DEFAULT_OAUTH_PORT,
    DEFAULT_REDIRECT_URI,
    GOOGLE_WORKSPACE_SCOPES,
    OAuthManager,
)
from gworkspace_mcp.auth.token_storage import TokenStorage


def _make_id_token(payload: dict) -> str:
    """Build a minimal (unsigned) JWT string for testing id_token decoding.

    Why: Tests for _extract_email_from_id_token need a realistic JWT structure
    without depending on a real Google token exchange.
    What: Produces header.payload.sig where payload is base64url-encoded JSON.
    Test: Pass to _extract_email_from_id_token and assert the expected email.
    """
    header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.fakesig"


@pytest.mark.unit
class TestOAuthManagerInit:
    """Tests for OAuthManager initialization."""

    def test_should_create_manager_with_default_storage(self) -> None:
        """Verify manager creates default storage when none provided."""
        with patch.object(TokenStorage, "_ensure_credentials_dir"):
            manager = OAuthManager()
            assert manager.storage is not None
            assert isinstance(manager.storage, TokenStorage)

    def test_should_create_manager_with_custom_storage(self, token_storage: TokenStorage) -> None:
        """Verify manager accepts custom storage instance."""
        manager = OAuthManager(storage=token_storage)
        assert manager.storage is token_storage

    def test_should_set_service_name(self, oauth_manager: OAuthManager) -> None:
        """Verify service name is set to gworkspace-mcp."""
        assert oauth_manager._service_name == "gworkspace-mcp"


@pytest.mark.unit
class TestOAuthManagerHasValidTokens:
    """Tests for OAuthManager.has_valid_tokens() method."""

    def test_should_return_true_when_valid_token_exists(
        self,
        oauth_manager: OAuthManager,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify True returned when valid token is stored."""
        oauth_manager.storage.store("gworkspace-mcp", valid_token, token_metadata)

        result = oauth_manager.has_valid_tokens()

        assert result is True

    def test_should_return_false_when_no_token_exists(self, oauth_manager: OAuthManager) -> None:
        """Verify False returned when no token is stored."""
        result = oauth_manager.has_valid_tokens()
        assert result is False

    def test_should_return_false_when_token_expired(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify False returned when token is expired."""
        oauth_manager.storage.store("gworkspace-mcp", expired_token, token_metadata)

        result = oauth_manager.has_valid_tokens()

        assert result is False


@pytest.mark.unit
class TestOAuthManagerTokenPath:
    """Tests for OAuthManager.token_path property."""

    def test_should_return_storage_token_path(
        self, oauth_manager: OAuthManager, temp_token_path: Path
    ) -> None:
        """Verify token_path returns storage path."""
        assert oauth_manager.token_path == temp_token_path


@pytest.mark.unit
class TestOAuthManagerCredentialsConversion:
    """Tests for credential conversion methods."""

    def test_should_convert_credentials_to_token(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify Google credentials convert to OAuthToken."""
        scopes = ["https://www.googleapis.com/auth/calendar"]

        token = oauth_manager._credentials_to_token(mock_google_credentials, scopes)

        assert token.access_token == "mock_access_token"
        assert token.refresh_token == "mock_refresh_token"
        assert token.scopes == scopes
        assert token.token_type == "Bearer"

    def test_should_handle_credentials_without_expiry(self, oauth_manager: OAuthManager) -> None:
        """Verify credentials without expiry get default 1h expiration."""
        mock_creds = MagicMock()
        mock_creds.token = "test_token"
        mock_creds.refresh_token = "test_refresh"
        mock_creds.expiry = None

        token = oauth_manager._credentials_to_token(mock_creds, [])

        # Should be approximately 1 hour from now
        time_diff = token.expires_at - datetime.now(timezone.utc)
        assert timedelta(minutes=55) < time_diff < timedelta(hours=1, minutes=5)

    def test_should_handle_naive_datetime_in_credentials(self, oauth_manager: OAuthManager) -> None:
        """Verify naive datetime in credentials is made timezone-aware."""
        mock_creds = MagicMock()
        mock_creds.token = "test_token"
        mock_creds.refresh_token = "test_refresh"
        mock_creds.expiry = datetime(2025, 12, 31, 23, 59, 59)  # Naive datetime

        token = oauth_manager._credentials_to_token(mock_creds, [])

        assert token.expires_at.tzinfo is not None

    def test_should_convert_token_to_credentials(
        self, oauth_manager: OAuthManager, valid_token: OAuthToken
    ) -> None:
        """Verify OAuthToken converts to Google credentials."""
        credentials = oauth_manager._token_to_credentials(valid_token)

        assert credentials.token == valid_token.access_token
        assert credentials.refresh_token == valid_token.refresh_token
        assert credentials.scopes == valid_token.scopes


@pytest.mark.unit
class TestOAuthManagerAuthenticate:
    """Tests for OAuthManager.authenticate() method."""

    @pytest.mark.asyncio
    async def test_should_raise_without_client_credentials(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify ValueError raised when client ID/secret missing."""
        with pytest.raises(ValueError, match="Client ID and secret required"):
            await oauth_manager.authenticate()

    @pytest.mark.asyncio
    async def test_should_raise_without_client_id(self, oauth_manager: OAuthManager) -> None:
        """Verify ValueError raised when only client_secret provided."""
        with pytest.raises(ValueError):
            await oauth_manager.authenticate(
                client_secret="secret_only"  # pragma: allowlist secret
            )

    @pytest.mark.asyncio
    async def test_should_raise_without_client_secret(self, oauth_manager: OAuthManager) -> None:
        """Verify ValueError raised when only client_id provided."""
        with pytest.raises(ValueError):
            await oauth_manager.authenticate(client_id="id_only")

    @pytest.mark.asyncio
    async def test_should_use_default_scopes_when_none_provided(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify default GOOGLE_WORKSPACE_SCOPES used when scopes not provided."""
        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            await oauth_manager.authenticate(
                client_id="test_id", client_secret="test_secret"
            )  # pragma: allowlist secret

            # Verify _run_oauth_flow was called with default scopes
            call_args = cast(MagicMock, oauth_manager._run_oauth_flow).call_args
            assert call_args[0][1] == GOOGLE_WORKSPACE_SCOPES

    @pytest.mark.asyncio
    async def test_should_use_custom_scopes_when_provided(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify custom scopes are used when provided."""
        custom_scopes = ["https://www.googleapis.com/auth/calendar.readonly"]

        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            await oauth_manager.authenticate(
                scopes=custom_scopes,
                client_id="test_id",
                client_secret="test_secret",  # pragma: allowlist secret
            )

            call_args = cast(MagicMock, oauth_manager._run_oauth_flow).call_args
            assert call_args[0][1] == custom_scopes

    @pytest.mark.asyncio
    async def test_should_store_token_after_authentication(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify token is stored after successful authentication."""
        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            await oauth_manager.authenticate(
                client_id="test_id", client_secret="test_secret"
            )  # pragma: allowlist secret

            stored = oauth_manager.storage.retrieve("gworkspace-mcp")
            assert stored is not None
            assert stored.token.access_token == "mock_access_token"

    @pytest.mark.asyncio
    async def test_should_return_oauth_token(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify authenticate returns OAuthToken."""
        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            token = await oauth_manager.authenticate(
                client_id="test_id",
                client_secret="test_secret",  # pragma: allowlist secret
            )

            assert isinstance(token, OAuthToken)
            assert token.access_token == "mock_access_token"


@pytest.mark.unit
class TestOAuthManagerRefreshIfNeeded:
    """Tests for OAuthManager.refresh_if_needed() method."""

    @pytest.mark.asyncio
    async def test_should_return_none_when_no_token_exists(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify None returned when no token is stored."""
        result = await oauth_manager.refresh_if_needed()
        assert result is None

    @pytest.mark.asyncio
    async def test_should_return_existing_token_when_valid(
        self,
        oauth_manager: OAuthManager,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify valid token is returned without refresh."""
        oauth_manager.storage.store("gworkspace-mcp", valid_token, token_metadata)

        result = await oauth_manager.refresh_if_needed()

        assert result is not None
        assert result.access_token == valid_token.access_token

    @pytest.mark.asyncio
    async def test_should_return_none_when_expired_without_refresh_token(
        self, oauth_manager: OAuthManager, token_metadata: TokenMetadata
    ) -> None:
        """Verify None returned when expired token has no refresh_token."""
        expired_no_refresh = OAuthToken(
            access_token="expired",
            refresh_token=None,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            scopes=[],
        )
        oauth_manager.storage.store("gworkspace-mcp", expired_no_refresh, token_metadata)

        result = await oauth_manager.refresh_if_needed()

        assert result is None

    @pytest.mark.asyncio
    async def test_should_refresh_expired_token(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify expired token triggers refresh."""
        oauth_manager.storage.store("gworkspace-mcp", expired_token, token_metadata)

        # Mock the credentials refresh
        mock_creds = MagicMock()
        mock_creds.token = "new_access_token"
        mock_creds.refresh_token = expired_token.refresh_token
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch.object(oauth_manager, "_token_to_credentials", return_value=mock_creds):
            with patch.object(mock_creds, "refresh"):
                result = await oauth_manager.refresh_if_needed()

                mock_creds.refresh.assert_called_once()
                assert result is not None

    @pytest.mark.asyncio
    async def test_should_update_stored_token_after_refresh(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify stored token is updated after refresh."""
        oauth_manager.storage.store("gworkspace-mcp", expired_token, token_metadata)

        mock_creds = MagicMock()
        mock_creds.token = "refreshed_access_token"
        mock_creds.refresh_token = "refreshed_refresh_token"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch.object(oauth_manager, "_token_to_credentials", return_value=mock_creds):
            with patch.object(mock_creds, "refresh"):
                await oauth_manager.refresh_if_needed()

                stored = oauth_manager.storage.retrieve("gworkspace-mcp")
                assert stored is not None
                assert stored.token.access_token == "refreshed_access_token"


@pytest.mark.unit
class TestOAuthManagerGetStatus:
    """Tests for OAuthManager.get_status() method."""

    def test_should_return_missing_when_no_token(self, oauth_manager: OAuthManager) -> None:
        """Verify MISSING status and None when no token exists."""
        status, stored = oauth_manager.get_status()

        assert status == TokenStatus.MISSING
        assert stored is None

    def test_should_return_valid_status_with_token(
        self,
        oauth_manager: OAuthManager,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify VALID status and token when valid token exists."""
        oauth_manager.storage.store("gworkspace-mcp", valid_token, token_metadata)

        status, stored = oauth_manager.get_status()

        assert status == TokenStatus.VALID
        assert stored is not None
        assert stored.token.access_token == valid_token.access_token

    def test_should_return_expired_status(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify EXPIRED status when token is expired."""
        oauth_manager.storage.store("gworkspace-mcp", expired_token, token_metadata)

        status, stored = oauth_manager.get_status()

        assert status == TokenStatus.EXPIRED
        assert stored is not None


@pytest.mark.unit
class TestOAuthManagerGetCredentials:
    """Tests for OAuthManager.get_credentials() method."""

    def test_should_return_none_when_no_token(self, oauth_manager: OAuthManager) -> None:
        """Verify None returned when no token exists."""
        credentials = oauth_manager.get_credentials()
        assert credentials is None

    def test_should_return_credentials_when_token_exists(
        self,
        oauth_manager: OAuthManager,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify credentials returned when token exists."""
        oauth_manager.storage.store("gworkspace-mcp", valid_token, token_metadata)

        credentials = oauth_manager.get_credentials()

        assert credentials is not None
        assert credentials.token == valid_token.access_token
        assert credentials.refresh_token == valid_token.refresh_token

    def test_should_return_credentials_for_expired_token(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify credentials returned even for expired token."""
        oauth_manager.storage.store("gworkspace-mcp", expired_token, token_metadata)

        credentials = oauth_manager.get_credentials()

        assert credentials is not None
        assert credentials.token == expired_token.access_token


@pytest.mark.unit
class TestOAuthManagerRunOAuthFlow:
    """Tests for OAuthManager._run_oauth_flow() method."""

    def _create_mock_flow(self, auth_url: str = "https://auth.url") -> MagicMock:
        """Create a mock Flow with standard configuration."""
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (auth_url, "state123")
        mock_flow.credentials = MagicMock()
        return mock_flow

    def _create_client_config(self, redirect_uri: str = "http://127.0.0.1:8789/callback") -> dict:
        """Create a standard web client config for testing."""
        return {
            "web": {
                "client_id": "test_id",
                "client_secret": "test_secret",  # pragma: allowlist secret
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }

    def _setup_mock_server_with_auth_code(
        self,
        mock_server_class: MagicMock,
        _auth_code: str = "test_auth_code",
    ) -> MagicMock:
        """Setup mock server that simulates receiving an auth code.

        The key insight: the OAuthCallbackHandler is defined inside _run_oauth_flow,
        so we need to capture it when HTTPServer is instantiated and simulate
        what would happen when handle_request() processes a callback with a code.
        """
        mock_server = MagicMock()
        captured_handler_class: list = []

        def capture_handler(_addr_tuple, handler_class):
            captured_handler_class.append(handler_class)
            return mock_server

        mock_server_class.side_effect = capture_handler

        # When handle_request is called, simulate the callback
        def simulate_auth_callback():
            # The actual auth_code is set via the mock flow's fetch_token
            pass

        mock_server.handle_request = simulate_auth_callback
        return mock_server

    def test_should_create_flow_from_client_config(self, oauth_manager: OAuthManager) -> None:
        """Verify OAuth flow is created with client config and redirect_uri."""
        client_config = self._create_client_config()
        scopes = ["https://www.googleapis.com/auth/calendar"]
        redirect_uri = "http://127.0.0.1:8789/callback"

        mock_flow = self._create_mock_flow()

        with (
            patch(
                "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
                return_value=mock_flow,
            ) as mock_from_config,
            patch(
                # Force the preferred port to be used so the redirect_uri is not
                # rewritten, keeping this test deterministic regardless of which
                # local ports happen to be busy at test time (issue #18).
                "gworkspace_mcp.auth.oauth_manager._find_free_port",
                return_value=8789,
            ),
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch("gworkspace_mcp.auth.oauth_manager.webbrowser.open"):
                    mock_server = MagicMock()

                    # Simulate receiving auth code via closure modification
                    def handle_request_with_code():
                        # Access the auth_code list from the closure and set it
                        # We need to find the auth_code list that was created
                        pass

                    mock_server.handle_request = handle_request_with_code
                    mock_server_class.return_value = mock_server

                    # Since we can't easily inject the auth_code into the closure,
                    # we test that from_client_config was called correctly
                    try:
                        oauth_manager._run_oauth_flow(client_config, scopes, redirect_uri)
                    except Exception:
                        pass  # Expected due to no auth code

                    mock_from_config.assert_called_once_with(
                        client_config,
                        scopes=scopes,
                        redirect_uri=redirect_uri,
                    )

    def test_should_generate_authorization_url_with_offline_access(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify authorization URL is generated with offline access and consent prompt."""
        client_config = self._create_client_config()
        redirect_uri = "http://127.0.0.1:8789/callback"

        mock_flow = self._create_mock_flow()

        with patch(
            "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
            return_value=mock_flow,
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch("gworkspace_mcp.auth.oauth_manager.webbrowser.open"):
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server

                    try:
                        oauth_manager._run_oauth_flow(client_config, [], redirect_uri)
                    except Exception:
                        pass  # Expected

                    # Verify authorization_url was called with correct params
                    mock_flow.authorization_url.assert_called_once()
                    call_kwargs = mock_flow.authorization_url.call_args[1]
                    assert call_kwargs["access_type"] == "offline"
                    assert call_kwargs["prompt"] == "consent"

    def test_should_start_http_server_on_configured_host_port(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify HTTP server starts on host/port from redirect URI."""
        redirect_uri = "http://127.0.0.1:9999/oauth/callback"
        client_config = self._create_client_config(redirect_uri)

        mock_flow = self._create_mock_flow()

        with patch(
            "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
            return_value=mock_flow,
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch("gworkspace_mcp.auth.oauth_manager.webbrowser.open"):
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server

                    try:
                        oauth_manager._run_oauth_flow(client_config, [], redirect_uri)
                    except Exception:
                        pass  # Expected

                    # Verify HTTPServer was instantiated with correct host/port
                    mock_server_class.assert_called_once()
                    call_args = mock_server_class.call_args[0]
                    assert call_args[0] == ("127.0.0.1", 9999)

    def test_should_open_browser_with_authorization_url(self, oauth_manager: OAuthManager) -> None:
        """Verify browser opens with authorization URL."""
        client_config = self._create_client_config()
        redirect_uri = "http://127.0.0.1:8789/callback"
        expected_auth_url = "https://accounts.google.com/o/oauth2/auth?response_type=code"

        mock_flow = self._create_mock_flow(expected_auth_url)

        with patch(
            "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
            return_value=mock_flow,
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch(
                    "gworkspace_mcp.auth.oauth_manager.webbrowser.open"
                ) as mock_browser_open:
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server

                    try:
                        oauth_manager._run_oauth_flow(client_config, [], redirect_uri)
                    except Exception:
                        pass  # Expected

                    mock_browser_open.assert_called_once_with(expected_auth_url)

    def test_should_raise_when_no_auth_code_received(self, oauth_manager: OAuthManager) -> None:
        """Verify exception raised when no authorization code is received."""
        client_config = self._create_client_config()
        redirect_uri = "http://127.0.0.1:8789/callback"

        mock_flow = self._create_mock_flow()

        with patch(
            "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
            return_value=mock_flow,
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch("gworkspace_mcp.auth.oauth_manager.webbrowser.open"):
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server

                    with pytest.raises(
                        Exception, match="No authorization code received from Google"
                    ):
                        oauth_manager._run_oauth_flow(client_config, [], redirect_uri)

    def test_should_set_server_timeout(self, oauth_manager: OAuthManager) -> None:
        """Verify HTTP server timeout is set to 5 minutes."""
        client_config = self._create_client_config()
        redirect_uri = "http://127.0.0.1:8789/callback"

        mock_flow = self._create_mock_flow()

        with patch(
            "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
            return_value=mock_flow,
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch("gworkspace_mcp.auth.oauth_manager.webbrowser.open"):
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server

                    try:
                        oauth_manager._run_oauth_flow(client_config, [], redirect_uri)
                    except Exception:
                        pass  # Expected

                    # Verify timeout was set to 300 seconds (5 minutes)
                    assert mock_server.timeout == 300

    def test_should_close_server_after_request(self, oauth_manager: OAuthManager) -> None:
        """Verify HTTP server is closed after handling request."""
        client_config = self._create_client_config()
        redirect_uri = "http://127.0.0.1:8789/callback"

        mock_flow = self._create_mock_flow()

        with patch(
            "gworkspace_mcp.auth.oauth_manager.Flow.from_client_config",
            return_value=mock_flow,
        ):
            with patch("gworkspace_mcp.auth.oauth_manager.HTTPServer") as mock_server_class:
                with patch("gworkspace_mcp.auth.oauth_manager.webbrowser.open"):
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server

                    try:
                        oauth_manager._run_oauth_flow(client_config, [], redirect_uri)
                    except Exception:
                        pass  # Expected

                    mock_server.handle_request.assert_called_once()
                    mock_server.server_close.assert_called_once()


@pytest.mark.unit
class TestGoogleWorkspaceScopes:
    """Tests for GOOGLE_WORKSPACE_SCOPES constant."""

    def test_should_include_openid_scope(self) -> None:
        """Verify openid scope is included for id_token email resolution."""
        assert "openid" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_userinfo_email_scope(self) -> None:
        """Verify userinfo.email scope is included so userinfo endpoint returns email."""
        assert "https://www.googleapis.com/auth/userinfo.email" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_userinfo_profile_scope(self) -> None:
        """Verify userinfo.profile scope is included for display name resolution."""
        assert "https://www.googleapis.com/auth/userinfo.profile" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_calendar_scope(self) -> None:
        """Verify calendar scope is included."""
        assert "https://www.googleapis.com/auth/calendar" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_gmail_scope(self) -> None:
        """Verify gmail modify scope is included."""
        assert "https://www.googleapis.com/auth/gmail.modify" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_drive_scope(self) -> None:
        """Verify drive scope is included."""
        assert "https://www.googleapis.com/auth/drive" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_docs_scope(self) -> None:
        """Verify documents scope is included."""
        assert "https://www.googleapis.com/auth/documents" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_tasks_scope(self) -> None:
        """Verify tasks scope is included."""
        assert "https://www.googleapis.com/auth/tasks" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_sheets_scope(self) -> None:
        """Verify spreadsheets scope is included for read/write support."""
        assert "https://www.googleapis.com/auth/spreadsheets" in GOOGLE_WORKSPACE_SCOPES

    def test_should_include_slides_scope(self) -> None:
        """Verify presentations scope is included for Slides access."""
        assert "https://www.googleapis.com/auth/presentations" in GOOGLE_WORKSPACE_SCOPES

    def test_should_have_ten_scopes(self) -> None:
        """Verify exactly ten scopes are defined (3 identity + 7 service)."""
        assert len(GOOGLE_WORKSPACE_SCOPES) == 10


@pytest.mark.unit
class TestOAuthDefaults:
    """Tests for OAuth default configuration constants."""

    def test_should_have_default_host(self) -> None:
        """Verify default OAuth host is 127.0.0.1."""
        assert DEFAULT_OAUTH_HOST == "127.0.0.1"

    def test_should_have_default_port(self) -> None:
        """Verify default OAuth port is 8789."""
        assert DEFAULT_OAUTH_PORT == 8789

    def test_should_have_default_redirect_uri_with_callback_path(self) -> None:
        """Verify default redirect URI includes /callback path."""
        assert DEFAULT_REDIRECT_URI == "http://127.0.0.1:8789/callback"

    def test_should_have_consistent_default_redirect_uri(self) -> None:
        """Verify default redirect URI uses default host and port."""
        expected = f"http://{DEFAULT_OAUTH_HOST}:{DEFAULT_OAUTH_PORT}/callback"
        assert DEFAULT_REDIRECT_URI == expected


@pytest.mark.unit
class TestFindFreePort:
    """Tests for the _find_free_port helper (issue #18 fix).

    Why: The OAuth callback server previously hard-coded port 8789 and
    failed with "[Errno 48] Address already in use" when the port was
    held by a stale TIME_WAIT socket from a previous failed flow. The
    helper must (a) reuse the preferred port when free, (b) fall back
    to an OS-assigned port when busy, and (c) set SO_REUSEADDR so it
    survives macOS TIME_WAIT.
    """

    def test_should_return_preferred_port_when_free(self) -> None:
        """Why: Normal happy path — the preferred port should be used.
        What: Pick a likely-free high port and assert _find_free_port
        returns that exact port.
        Test: Bind a probe socket to port 0 to discover a free port,
        close it, then call _find_free_port with that port.
        """
        import socket as _socket

        from gworkspace_mcp.auth.oauth_manager import _find_free_port

        probe = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
        probe.close()

        result = _find_free_port(free_port)
        assert result == free_port

    def test_should_fall_back_when_preferred_port_busy(self) -> None:
        """Why: Issue #18 — when preferred port is held, must not raise.
        What: Block a port with a real listening socket, then verify
        _find_free_port returns a different non-zero port.
        Test: Listen on a port, call _find_free_port with it, assert
        the returned port differs and is a valid port number.
        """
        import socket as _socket

        from gworkspace_mcp.auth.oauth_manager import _find_free_port

        blocker = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        blocker.bind(("127.0.0.1", 0))
        blocker.listen(1)
        blocked_port = blocker.getsockname()[1]
        try:
            result = _find_free_port(blocked_port)
            assert result != blocked_port
            assert 1024 <= result <= 65535
        finally:
            blocker.close()


@pytest.mark.unit
class TestExtractEmailFromIdToken:
    """Tests for OAuthManager._extract_email_from_id_token().

    Why: When the openid scope is granted, Google returns a signed JWT id_token
    in the token exchange response.  Decoding the payload avoids an extra HTTP
    call to the userinfo endpoint.

    Test strategy: Build synthetic (unsigned) JWTs and assert expected outputs.
    """

    def test_should_return_email_from_valid_id_token(self) -> None:
        """Verify email is extracted from a well-formed id_token JWT."""
        token = _make_id_token({"email": "user@example.com", "sub": "123"})
        result = OAuthManager._extract_email_from_id_token(token)
        assert result == "user@example.com"

    def test_should_return_none_when_email_not_in_payload(self) -> None:
        """Verify None returned when JWT payload has no email claim."""
        token = _make_id_token({"sub": "123", "aud": "client-id"})
        result = OAuthManager._extract_email_from_id_token(token)
        assert result is None

    def test_should_return_none_for_malformed_token(self) -> None:
        """Verify None returned for a token with wrong segment count."""
        result = OAuthManager._extract_email_from_id_token("not.a.valid.jwt.with.too.many.dots")
        assert result is None

    def test_should_return_none_for_non_json_payload(self) -> None:
        """Verify None returned when the payload segment is not valid JSON."""
        bad_payload = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
        result = OAuthManager._extract_email_from_id_token(f"header.{bad_payload}.sig")
        assert result is None

    def test_should_handle_unpadded_base64(self) -> None:
        """Verify decoding works regardless of base64url padding."""
        # Build a payload that produces unpadded base64 naturally
        payload = {"email": "padtest@example.com"}
        token = _make_id_token(payload)
        # Token was built without padding — assert it still decodes correctly
        result = OAuthManager._extract_email_from_id_token(token)
        assert result == "padtest@example.com"


@pytest.mark.unit
class TestFetchUserEmail:
    """Tests for OAuthManager._fetch_user_email().

    Why: Email resolution is the fix for list_accounts returning email: null.
    The method must: prefer id_token decoding (no HTTP call), fall back to
    userinfo HTTP call, log a clear warning on 401 (scope missing), and
    return None without crashing on all error paths.
    """

    @pytest.mark.asyncio
    async def test_should_return_email_from_id_token_without_http_call(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify id_token path returns email and skips HTTP call."""
        id_token = _make_id_token({"email": "fromtoken@example.com"})

        with patch("urllib.request.urlopen") as mock_urlopen:
            result = await oauth_manager._fetch_user_email("access_tok", id_token=id_token)

        assert result == "fromtoken@example.com"
        mock_urlopen.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_fall_back_to_http_when_no_id_token(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify userinfo HTTP call is made when id_token is absent."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"email": "http@example.com"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = await oauth_manager._fetch_user_email("access_tok", id_token=None)

        assert result == "http@example.com"

    @pytest.mark.asyncio
    async def test_should_fall_back_to_http_when_id_token_has_no_email(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify HTTP fallback used when id_token payload has no email claim."""
        id_token = _make_id_token({"sub": "123"})  # no email claim
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"email": "fallback@example.com"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = await oauth_manager._fetch_user_email("access_tok", id_token=id_token)

        assert result == "fallback@example.com"

    @pytest.mark.asyncio
    async def test_should_return_none_and_log_warning_on_401(
        self, oauth_manager: OAuthManager, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify 401 returns None and logs actionable warning (not silent swallow)."""
        import logging

        exc = HTTPError(
            url="https://www.googleapis.com/oauth2/v2/userinfo",
            code=401,
            msg="Unauthorized",
            hdrs=MagicMock(),  # type: ignore[arg-type]
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=exc):
            with caplog.at_level(logging.WARNING):
                result = await oauth_manager._fetch_user_email("bad_token", id_token=None)

        assert result is None
        assert any(
            "401" in r.message
            or "identity scope" in r.message.lower()
            or "re-authenticate" in r.message.lower()
            for r in caplog.records
        ), f"Expected actionable 401 warning, got: {[r.message for r in caplog.records]}"

    @pytest.mark.asyncio
    async def test_should_return_none_on_url_error(self, oauth_manager: OAuthManager) -> None:
        """Verify URLError (network failure) returns None without raising."""
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            result = await oauth_manager._fetch_user_email("access_tok", id_token=None)

        assert result is None

    @pytest.mark.asyncio
    async def test_should_return_none_on_http_error_non_401(
        self, oauth_manager: OAuthManager
    ) -> None:
        """Verify non-401 HTTP errors (e.g. 403, 500) return None without raising."""
        exc = HTTPError(
            url="https://www.googleapis.com/oauth2/v2/userinfo",
            code=403,
            msg="Forbidden",
            hdrs=MagicMock(),  # type: ignore[arg-type]
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=exc):
            result = await oauth_manager._fetch_user_email("access_tok", id_token=None)

        assert result is None


@pytest.mark.unit
class TestRefreshIfNeededEmailBackfill:
    """Tests for the email backfill logic added to refresh_if_needed().

    Why: Profiles created before the identity scopes were added have email=None.
    On the next token refresh (or if the token is still valid but email is missing)
    the manager should attempt to resolve and persist the email automatically so
    users don't need to re-authenticate just to see their email in list_accounts.
    """

    @pytest.mark.asyncio
    async def test_should_backfill_email_on_refresh_when_previously_null(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
    ) -> None:
        """Verify email is populated after token refresh when metadata.email was None."""
        metadata_no_email = TokenMetadata(
            service_name="gworkspace-mcp",
            provider="google",
            email=None,
        )
        oauth_manager.storage.store("gworkspace-mcp", expired_token, metadata_no_email)

        mock_creds = MagicMock()
        mock_creds.token = "refreshed_token"
        mock_creds.refresh_token = "refresh_tok"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_creds.id_token = None  # no id_token on the mock

        with patch.object(oauth_manager, "_token_to_credentials", return_value=mock_creds):
            with patch.object(mock_creds, "refresh"):
                with patch.object(
                    oauth_manager,
                    "_fetch_user_email",
                    new=AsyncMock(return_value="backfilled@example.com"),
                ):
                    await oauth_manager.refresh_if_needed()

        stored = oauth_manager.storage.retrieve("gworkspace-mcp")
        assert stored is not None
        assert stored.metadata.email == "backfilled@example.com"

    @pytest.mark.asyncio
    async def test_should_not_overwrite_existing_email_on_refresh(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
    ) -> None:
        """Verify existing email is preserved when refresh succeeds."""
        metadata_with_email = TokenMetadata(
            service_name="gworkspace-mcp",
            provider="google",
            email="existing@example.com",
        )
        oauth_manager.storage.store("gworkspace-mcp", expired_token, metadata_with_email)

        mock_creds = MagicMock()
        mock_creds.token = "refreshed_token"
        mock_creds.refresh_token = "refresh_tok"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_creds.id_token = None

        with patch.object(oauth_manager, "_token_to_credentials", return_value=mock_creds):
            with patch.object(mock_creds, "refresh"):
                # _fetch_user_email should NOT be called because email is already set
                with patch.object(
                    oauth_manager,
                    "_fetch_user_email",
                    new=AsyncMock(return_value="different@example.com"),
                ) as mock_fetch:
                    await oauth_manager.refresh_if_needed()

        # email should remain unchanged regardless of what fetch_user_email returns
        stored = oauth_manager.storage.retrieve("gworkspace-mcp")
        assert stored is not None
        assert stored.metadata.email == "existing@example.com"
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_backfill_email_for_valid_token_with_null_email(
        self,
        oauth_manager: OAuthManager,
        valid_token: OAuthToken,
    ) -> None:
        """Verify email backfill also runs for non-expired tokens missing email."""
        metadata_no_email = TokenMetadata(
            service_name="gworkspace-mcp",
            provider="google",
            email=None,
        )
        oauth_manager.storage.store("gworkspace-mcp", valid_token, metadata_no_email)

        with patch.object(
            oauth_manager,
            "_fetch_user_email",
            new=AsyncMock(return_value="valid@example.com"),
        ):
            result = await oauth_manager.refresh_if_needed()

        assert result is not None
        stored = oauth_manager.storage.retrieve("gworkspace-mcp")
        assert stored is not None
        assert stored.metadata.email == "valid@example.com"

    @pytest.mark.asyncio
    async def test_should_pass_id_token_to_fetch_user_email_on_refresh(
        self,
        oauth_manager: OAuthManager,
        expired_token: OAuthToken,
    ) -> None:
        """Verify id_token from refreshed credentials is forwarded to _fetch_user_email."""
        metadata_no_email = TokenMetadata(
            service_name="gworkspace-mcp",
            provider="google",
            email=None,
        )
        oauth_manager.storage.store("gworkspace-mcp", expired_token, metadata_no_email)

        sample_id_token = _make_id_token({"email": "idtoken@example.com"})
        mock_creds = MagicMock()
        mock_creds.token = "refreshed_token"
        mock_creds.refresh_token = "refresh_tok"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_creds.id_token = sample_id_token

        with patch.object(oauth_manager, "_token_to_credentials", return_value=mock_creds):
            with patch.object(mock_creds, "refresh"):
                with patch.object(
                    oauth_manager,
                    "_fetch_user_email",
                    new=AsyncMock(return_value="idtoken@example.com"),
                ) as mock_fetch:
                    await oauth_manager.refresh_if_needed()

        # Verify id_token was passed through
        mock_fetch.assert_awaited_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs.get("id_token") == sample_id_token or (
            len(call_kwargs.args) >= 2 and call_kwargs.args[1] == sample_id_token
        )


@pytest.mark.unit
class TestAuthenticateEmailResolution:
    """Tests verifying authenticate() resolves and stores email correctly."""

    @pytest.mark.asyncio
    async def test_should_store_email_from_id_token_after_auth(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify email from id_token is persisted in metadata after authenticate."""
        sample_id_token = _make_id_token({"email": "auth@example.com"})
        mock_google_credentials.id_token = sample_id_token

        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            await oauth_manager.authenticate(
                client_id="test_id",
                client_secret="test_secret",  # pragma: allowlist secret
            )

        stored = oauth_manager.storage.retrieve("gworkspace-mcp")
        assert stored is not None
        assert stored.metadata.email == "auth@example.com"

    @pytest.mark.asyncio
    async def test_should_store_email_from_userinfo_when_no_id_token(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify email from userinfo fallback is persisted when no id_token available."""
        mock_google_credentials.id_token = None

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"email": "userinfo@example.com"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            with patch("urllib.request.urlopen", return_value=mock_resp):
                await oauth_manager.authenticate(
                    client_id="test_id",
                    client_secret="test_secret",  # pragma: allowlist secret
                )

        stored = oauth_manager.storage.retrieve("gworkspace-mcp")
        assert stored is not None
        assert stored.metadata.email == "userinfo@example.com"

    @pytest.mark.asyncio
    async def test_should_store_none_email_gracefully_when_resolution_fails(
        self, oauth_manager: OAuthManager, mock_google_credentials: MagicMock
    ) -> None:
        """Verify authenticate completes (does not raise) when email resolution fails."""
        mock_google_credentials.id_token = None

        exc = HTTPError(
            url="https://www.googleapis.com/oauth2/v2/userinfo",
            code=401,
            msg="Unauthorized",
            hdrs=MagicMock(),  # type: ignore[arg-type]
            fp=None,
        )

        with patch.object(oauth_manager, "_run_oauth_flow", return_value=mock_google_credentials):
            with patch("urllib.request.urlopen", side_effect=exc):
                token = await oauth_manager.authenticate(
                    client_id="test_id",
                    client_secret="test_secret",  # pragma: allowlist secret
                )

        # authenticate must not raise; email is None in metadata
        assert token is not None
        stored = oauth_manager.storage.retrieve("gworkspace-mcp")
        assert stored is not None
        assert stored.metadata.email is None
