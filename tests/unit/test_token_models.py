"""Unit tests for OAuth token models."""

from datetime import datetime, timedelta, timezone

import pytest

from gworkspace_mcp.auth.models import OAuthToken, StoredToken, TokenMetadata, TokenStatus


@pytest.mark.unit
class TestOAuthToken:
    """Tests for OAuthToken model."""

    def test_should_create_valid_token(self, valid_token: OAuthToken) -> None:
        """Verify token creation with valid data."""
        assert valid_token.access_token == "test_access_token_abc123"
        assert valid_token.refresh_token == "test_refresh_token_xyz789"
        assert valid_token.token_type == "Bearer"
        assert len(valid_token.scopes) == 5

    def test_should_detect_non_expired_token(self, valid_token: OAuthToken) -> None:
        """Verify is_expired returns False for valid token."""
        assert valid_token.is_expired() is False

    def test_should_detect_expired_token(self, expired_token: OAuthToken) -> None:
        """Verify is_expired returns True for expired token."""
        assert expired_token.is_expired() is True

    def test_should_respect_buffer_seconds(self) -> None:
        """Verify is_expired respects buffer_seconds parameter."""
        # Token expires in 30 seconds
        token = OAuthToken(
            access_token="test",
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
            scopes=[],
        )
        # With default 60s buffer, should be considered expired
        assert token.is_expired(buffer_seconds=60) is True
        # With 10s buffer, should not be expired
        assert token.is_expired(buffer_seconds=10) is False


@pytest.mark.unit
class TestTokenMetadata:
    """Tests for TokenMetadata model."""

    def test_should_create_metadata_with_defaults(self) -> None:
        """Verify metadata creation with required fields only."""
        metadata = TokenMetadata(service_name="test-service")
        assert metadata.service_name == "test-service"
        assert metadata.provider == "google"
        assert metadata.created_at is not None
        assert metadata.last_refreshed is None

    def test_should_track_service_name(self, token_metadata: TokenMetadata) -> None:
        """Verify service name is preserved."""
        assert token_metadata.service_name == "gworkspace-mcp"


@pytest.mark.unit
class TestStoredToken:
    """Tests for StoredToken model."""

    def test_should_create_stored_token(self, stored_token: StoredToken) -> None:
        """Verify stored token combines token and metadata."""
        assert stored_token.version == 1
        assert stored_token.token.access_token == "test_access_token_abc123"
        assert stored_token.metadata.service_name == "gworkspace-mcp"


@pytest.mark.unit
class TestTokenStatus:
    """Tests for TokenStatus enum."""

    def test_should_have_expected_statuses(self) -> None:
        """Verify all expected statuses exist."""
        assert TokenStatus.VALID.value == "valid"
        assert TokenStatus.EXPIRED.value == "expired"
        assert TokenStatus.MISSING.value == "missing"
        assert TokenStatus.INVALID.value == "invalid"
