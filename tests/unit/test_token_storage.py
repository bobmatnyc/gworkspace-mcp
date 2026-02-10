"""Unit tests for TokenStorage class.

Tests cover token persistence, retrieval, deletion, and error handling.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from google_workspace_mcp.auth.models import OAuthToken, TokenMetadata, TokenStatus
from google_workspace_mcp.auth.token_storage import TokenStorage


@pytest.mark.unit
class TestTokenStorageInit:
    """Tests for TokenStorage initialization."""

    def test_should_create_storage_with_default_path(self) -> None:
        """Verify storage uses default path when none provided."""
        with patch.object(TokenStorage, "_ensure_credentials_dir"):
            storage = TokenStorage()
            assert storage.token_path.name == "tokens.json"
            assert ".google-workspace-mcp" in str(storage.token_path)

    def test_should_create_storage_with_custom_path(self, temp_token_path: Path) -> None:
        """Verify storage accepts custom token path."""
        storage = TokenStorage(token_path=temp_token_path)
        assert storage.token_path == temp_token_path

    def test_should_create_directory_when_missing(self, tmp_path: Path) -> None:
        """Verify storage creates directory if it doesn't exist."""
        new_dir = tmp_path / "new_creds_dir"
        token_path = new_dir / "tokens.json"

        TokenStorage(token_path=token_path)  # Storage creation triggers directory creation

        assert new_dir.exists()
        assert new_dir.stat().st_mode & 0o777 == 0o700

    def test_should_fix_directory_permissions(self, tmp_path: Path) -> None:
        """Verify storage corrects insecure directory permissions."""
        creds_dir = tmp_path / "creds"
        creds_dir.mkdir(mode=0o755)
        token_path = creds_dir / "tokens.json"

        TokenStorage(token_path=token_path)

        assert creds_dir.stat().st_mode & 0o777 == 0o700


@pytest.mark.unit
class TestTokenStorageStore:
    """Tests for TokenStorage.store() method."""

    def test_should_store_token(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify token is saved to file."""
        token_storage.store("test-service", valid_token, token_metadata)

        assert token_storage.token_path.exists()
        with open(token_storage.token_path) as f:
            data = json.load(f)
        assert "test-service" in data

    def test_should_store_multiple_tokens(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify multiple service tokens can be stored."""
        metadata1 = TokenMetadata(service_name="service1")
        metadata2 = TokenMetadata(service_name="service2")

        token_storage.store("service1", valid_token, metadata1)
        token_storage.store("service2", valid_token, metadata2)

        with open(token_storage.token_path) as f:
            data = json.load(f)
        assert "service1" in data
        assert "service2" in data

    def test_should_overwrite_existing_token(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify storing same service overwrites previous token."""
        token_storage.store("test-service", valid_token, token_metadata)

        new_token = OAuthToken(
            access_token="new_token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            scopes=["scope1"],
        )
        token_storage.store("test-service", new_token, token_metadata)

        retrieved = token_storage.retrieve("test-service")
        assert retrieved.token.access_token == "new_token"

    def test_should_set_secure_file_permissions(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify token file has secure permissions (600)."""
        token_storage.store("test-service", valid_token, token_metadata)

        file_mode = token_storage.token_path.stat().st_mode & 0o777
        assert file_mode == 0o600


@pytest.mark.unit
class TestTokenStorageRetrieve:
    """Tests for TokenStorage.retrieve() method."""

    def test_should_retrieve_stored_token(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify stored token can be retrieved."""
        token_storage.store("test-service", valid_token, token_metadata)

        retrieved = token_storage.retrieve("test-service")

        assert retrieved is not None
        assert retrieved.token.access_token == valid_token.access_token
        assert retrieved.token.refresh_token == valid_token.refresh_token

    def test_should_return_none_for_missing_service(self, token_storage: TokenStorage) -> None:
        """Verify None returned when service has no stored token."""
        result = token_storage.retrieve("nonexistent-service")
        assert result is None

    def test_should_return_none_for_corrupted_token(self, token_storage: TokenStorage) -> None:
        """Verify None returned when token data is corrupted."""
        # Write invalid JSON structure
        token_storage.token_path.write_text('{"test-service": {"invalid": "data"}}')

        result = token_storage.retrieve("test-service")
        assert result is None

    def test_should_return_none_for_invalid_json(self, token_storage: TokenStorage) -> None:
        """Verify None returned when file contains invalid JSON."""
        token_storage.token_path.write_text("not valid json {{{")

        result = token_storage.retrieve("test-service")
        assert result is None

    def test_should_preserve_all_token_fields(
        self,
        token_storage: TokenStorage,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify all token fields are preserved through storage cycle."""
        original = OAuthToken(
            access_token="access_abc",
            refresh_token="refresh_xyz",
            expires_at=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            scopes=["scope1", "scope2", "scope3"],
            token_type="Bearer",
        )

        token_storage.store("test-service", original, token_metadata)
        retrieved = token_storage.retrieve("test-service")

        assert retrieved.token.access_token == original.access_token
        assert retrieved.token.refresh_token == original.refresh_token
        assert retrieved.token.scopes == original.scopes
        assert retrieved.token.token_type == original.token_type


@pytest.mark.unit
class TestTokenStorageDelete:
    """Tests for TokenStorage.delete() method."""

    def test_should_delete_existing_token(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify token deletion removes the token."""
        token_storage.store("test-service", valid_token, token_metadata)

        result = token_storage.delete("test-service")

        assert result is True
        assert token_storage.retrieve("test-service") is None

    def test_should_return_false_for_nonexistent_token(self, token_storage: TokenStorage) -> None:
        """Verify False returned when deleting nonexistent token."""
        result = token_storage.delete("nonexistent-service")
        assert result is False

    def test_should_preserve_other_tokens_on_delete(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
    ) -> None:
        """Verify deleting one token doesn't affect others."""
        metadata1 = TokenMetadata(service_name="service1")
        metadata2 = TokenMetadata(service_name="service2")

        token_storage.store("service1", valid_token, metadata1)
        token_storage.store("service2", valid_token, metadata2)
        token_storage.delete("service1")

        assert token_storage.retrieve("service1") is None
        assert token_storage.retrieve("service2") is not None


@pytest.mark.unit
class TestTokenStorageListServices:
    """Tests for TokenStorage.list_services() method."""

    def test_should_return_empty_list_when_no_tokens(self, token_storage: TokenStorage) -> None:
        """Verify empty list returned when no tokens stored."""
        result = token_storage.list_services()
        assert result == []

    def test_should_list_all_stored_services(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
    ) -> None:
        """Verify all stored service names are returned."""
        for service in ["service-a", "service-b", "service-c"]:
            metadata = TokenMetadata(service_name=service)
            token_storage.store(service, valid_token, metadata)

        result = token_storage.list_services()

        assert len(result) == 3
        assert "service-a" in result
        assert "service-b" in result
        assert "service-c" in result

    def test_should_return_sorted_list(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
    ) -> None:
        """Verify service list is sorted alphabetically."""
        for service in ["zebra", "apple", "mango"]:
            metadata = TokenMetadata(service_name=service)
            token_storage.store(service, valid_token, metadata)

        result = token_storage.list_services()

        assert result == ["apple", "mango", "zebra"]


@pytest.mark.unit
class TestTokenStorageGetStatus:
    """Tests for TokenStorage.get_status() method."""

    def test_should_return_valid_for_non_expired_token(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify VALID status for non-expired token."""
        token_storage.store("test-service", valid_token, token_metadata)

        status = token_storage.get_status("test-service")

        assert status == TokenStatus.VALID

    def test_should_return_expired_for_expired_token(
        self,
        token_storage: TokenStorage,
        expired_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify EXPIRED status for expired token."""
        token_storage.store("test-service", expired_token, token_metadata)

        status = token_storage.get_status("test-service")

        assert status == TokenStatus.EXPIRED

    def test_should_return_missing_for_nonexistent_token(self, token_storage: TokenStorage) -> None:
        """Verify MISSING status when no token exists."""
        status = token_storage.get_status("nonexistent-service")
        assert status == TokenStatus.MISSING

    def test_should_return_invalid_for_corrupted_token(self, token_storage: TokenStorage) -> None:
        """Verify INVALID status when token data is corrupted."""
        token_storage.token_path.write_text('{"test-service": {"bad": "data"}}')

        status = token_storage.get_status("test-service")

        assert status == TokenStatus.INVALID


@pytest.mark.unit
class TestTokenStorageClearAll:
    """Tests for TokenStorage.clear_all() method."""

    def test_should_remove_token_file(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify clear_all removes the token file."""
        token_storage.store("test-service", valid_token, token_metadata)
        assert token_storage.token_path.exists()

        token_storage.clear_all()

        assert not token_storage.token_path.exists()

    def test_should_handle_missing_file(self, token_storage: TokenStorage) -> None:
        """Verify clear_all doesn't error when file doesn't exist."""
        assert not token_storage.token_path.exists()

        token_storage.clear_all()  # Should not raise

        assert not token_storage.token_path.exists()

    def test_should_clear_all_services(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
    ) -> None:
        """Verify all services are removed after clear_all."""
        for service in ["service1", "service2", "service3"]:
            metadata = TokenMetadata(service_name=service)
            token_storage.store(service, valid_token, metadata)

        token_storage.clear_all()

        assert token_storage.list_services() == []


@pytest.mark.unit
class TestTokenStorageEdgeCases:
    """Tests for edge cases and error handling."""

    def test_should_handle_empty_file(self, token_storage: TokenStorage) -> None:
        """Verify empty file is handled gracefully."""
        token_storage.token_path.write_text("")

        result = token_storage.retrieve("test-service")
        assert result is None

    def test_should_handle_io_error_on_load(self, token_storage: TokenStorage) -> None:
        """Verify IOError during load returns empty dict."""
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Bypass the exists check to trigger the open
            with patch.object(Path, "exists", return_value=True):
                result = token_storage._load_tokens()

        assert result == {}

    def test_should_handle_token_without_refresh_token(
        self,
        token_storage: TokenStorage,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify token without refresh_token is stored correctly."""
        token = OAuthToken(
            access_token="access_only",
            refresh_token=None,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["scope1"],
        )

        token_storage.store("test-service", token, token_metadata)
        retrieved = token_storage.retrieve("test-service")

        assert retrieved.token.refresh_token is None

    def test_should_handle_special_characters_in_service_name(
        self,
        token_storage: TokenStorage,
        valid_token: OAuthToken,
        token_metadata: TokenMetadata,
    ) -> None:
        """Verify special characters in service name are handled."""
        service_name = "test-service_v2.0@google"

        token_storage.store(service_name, valid_token, token_metadata)
        retrieved = token_storage.retrieve(service_name)

        assert retrieved is not None
        assert retrieved.token.access_token == valid_token.access_token
