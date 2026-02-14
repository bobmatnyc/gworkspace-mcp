"""Unit tests for OAuthManager class.

Tests cover authentication flow, token refresh, and credential management.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gworkspace_mcp.auth.models import OAuthToken, TokenMetadata, TokenStatus
from gworkspace_mcp.auth.oauth_manager import (
    GOOGLE_WORKSPACE_SCOPES,
    OAuthManager,
)
from gworkspace_mcp.auth.token_storage import TokenStorage


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
        """Verify service name is set to google-workspace."""
        assert oauth_manager._service_name == "google-workspace"


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
        oauth_manager.storage.store("google-workspace", valid_token, token_metadata)

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
        oauth_manager.storage.store("google-workspace", expired_token, token_metadata)

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
            call_args = oauth_manager._run_oauth_flow.call_args
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

            call_args = oauth_manager._run_oauth_flow.call_args
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

            stored = oauth_manager.storage.retrieve("google-workspace")
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
        oauth_manager.storage.store("google-workspace", valid_token, token_metadata)

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
        oauth_manager.storage.store("google-workspace", expired_no_refresh, token_metadata)

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
        oauth_manager.storage.store("google-workspace", expired_token, token_metadata)

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
        oauth_manager.storage.store("google-workspace", expired_token, token_metadata)

        mock_creds = MagicMock()
        mock_creds.token = "refreshed_access_token"
        mock_creds.refresh_token = "refreshed_refresh_token"
        mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch.object(oauth_manager, "_token_to_credentials", return_value=mock_creds):
            with patch.object(mock_creds, "refresh"):
                await oauth_manager.refresh_if_needed()

                stored = oauth_manager.storage.retrieve("google-workspace")
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
        oauth_manager.storage.store("google-workspace", valid_token, token_metadata)

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
        oauth_manager.storage.store("google-workspace", expired_token, token_metadata)

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
        oauth_manager.storage.store("google-workspace", valid_token, token_metadata)

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
        oauth_manager.storage.store("google-workspace", expired_token, token_metadata)

        credentials = oauth_manager.get_credentials()

        assert credentials is not None
        assert credentials.token == expired_token.access_token


@pytest.mark.unit
class TestOAuthManagerRunOAuthFlow:
    """Tests for OAuthManager._run_oauth_flow() method."""

    def test_should_create_flow_from_client_config(self, oauth_manager: OAuthManager) -> None:
        """Verify OAuth flow is created with client config."""
        client_config = {
            "installed": {
                "client_id": "test_id",
                "client_secret": "test_secret",  # pragma: allowlist secret
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost/"],
            }
        }
        scopes = ["https://www.googleapis.com/auth/calendar"]

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = MagicMock()

        with patch(
            "gworkspace_mcp.auth.oauth_manager.InstalledAppFlow.from_client_config",
            return_value=mock_flow,
        ) as mock_from_config:
            oauth_manager._run_oauth_flow(client_config, scopes)

            mock_from_config.assert_called_once_with(client_config, scopes=scopes)

    def test_should_run_local_server_with_dynamic_port(self, oauth_manager: OAuthManager) -> None:
        """Verify local server runs with dynamic port (0) by default."""
        client_config = {
            "installed": {
                "client_id": "test_id",
                "client_secret": "test_secret",  # pragma: allowlist secret
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost/"],
            }
        }

        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_flow.run_local_server.return_value = mock_credentials

        with patch(
            "gworkspace_mcp.auth.oauth_manager.InstalledAppFlow.from_client_config",
            return_value=mock_flow,
        ):
            result = oauth_manager._run_oauth_flow(client_config, [])

            mock_flow.run_local_server.assert_called_once_with(
                host="localhost", port=0, open_browser=True
            )
            assert result == mock_credentials


@pytest.mark.unit
class TestGoogleWorkspaceScopes:
    """Tests for GOOGLE_WORKSPACE_SCOPES constant."""

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

    def test_should_have_five_scopes(self) -> None:
        """Verify exactly five scopes are defined."""
        assert len(GOOGLE_WORKSPACE_SCOPES) == 5
