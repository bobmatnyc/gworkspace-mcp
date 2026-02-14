"""Simplified OAuth token storage for Google Workspace MCP.

This module provides basic JSON-based token persistence without
encryption. For production use, consider adding encryption.

Storage Location: ./.gworkspace-mcp/tokens.json (PROJECT-LEVEL ONLY)

Tokens are stored at project level since OAuth credentials (.env)
are also project-specific. This allows different projects to connect
to different Google accounts.

IMPORTANT: Each project requires its own authentication.
Run `gworkspace-mcp setup` from the project directory to authenticate.
"""

import json
import logging
from pathlib import Path

from gworkspace_mcp.auth.models import (
    OAuthToken,
    StoredToken,
    TokenMetadata,
    TokenStatus,
)

logger = logging.getLogger(__name__)

# Project-level credentials directory (ONLY supported location)
CREDENTIALS_DIR = Path.cwd() / ".gworkspace-mcp"
TOKEN_FILE = CREDENTIALS_DIR / "tokens.json"


def get_token_path() -> Path:
    """Get the project-level token storage path.

    Returns:
        Path to tokens.json file in ./.gworkspace-mcp/
    """
    return TOKEN_FILE


class TokenStorage:
    """Simple JSON-based storage for OAuth tokens.

    Tokens are stored at project level: ./.gworkspace-mcp/tokens.json

    This matches the project-level .env files that contain OAuth credentials,
    allowing different projects to connect to different Google accounts.

    For production, consider adding encryption (Fernet + keyring).

    Attributes:
        token_path: Path to the tokens.json file.

    Example:
        ```python
        storage = TokenStorage()

        # Store a token
        token = OAuthToken(
            access_token="abc123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["read", "write"]
        )
        metadata = TokenMetadata(service_name="gworkspace-mcp", provider="google")
        storage.store("gworkspace-mcp", token, metadata)

        # Retrieve the token
        stored = storage.retrieve("gworkspace-mcp")
        if stored:
            print(f"Token expires at: {stored.token.expires_at}")
        ```
    """

    def __init__(self, token_path: Path | None = None) -> None:
        """Initialize token storage.

        Args:
            token_path: Custom path for tokens.json.
                If not provided, uses project-level (./.gworkspace-mcp/tokens.json).
                User-level storage is NOT supported - each project must authenticate separately.
        """
        self.token_path = token_path or get_token_path()
        self.credentials_dir = self.token_path.parent
        # Run pending migrations automatically before any other operations
        self._run_migrations()
        self._ensure_credentials_dir()

    def _run_migrations(self) -> None:
        """Run pending migrations automatically.

        This ensures the credentials directory is migrated from old locations
        before any token operations are attempted.
        """
        try:
            from gworkspace_mcp.migrations import MigrationRunner

            runner = MigrationRunner()
            pending = runner.get_pending_migrations()
            if pending:
                logger.info(f"Running {len(pending)} pending migration(s)")
                runner.run_all_pending()
        except Exception as e:
            # Don't fail initialization if migrations fail
            logger.warning(f"Migration check failed (non-fatal): {e}")

    def _ensure_credentials_dir(self) -> None:
        """Create credentials directory with secure permissions if needed."""
        creds_dir = self.token_path.parent
        if not creds_dir.exists():
            creds_dir.mkdir(parents=True, mode=0o700)
        else:
            # Ensure directory has correct permissions
            creds_dir.chmod(0o700)

    def _load_tokens(self) -> dict[str, dict]:
        """Load all tokens from JSON file.

        Returns:
            Dictionary mapping service names to token data.
        """
        if not self.token_path.exists():
            return {}

        try:
            with open(self.token_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_tokens(self, tokens: dict[str, dict]) -> None:
        """Save all tokens to JSON file.

        Args:
            tokens: Dictionary mapping service names to token data.
        """
        # Ensure directory exists
        self._ensure_credentials_dir()

        # Write JSON with secure permissions
        with open(self.token_path, "w") as f:
            json.dump(tokens, f, indent=2, default=str)

        # Set file permissions to owner read/write only (600)
        self.token_path.chmod(0o600)

    def store(
        self,
        service_name: str,
        token: OAuthToken,
        metadata: TokenMetadata,
    ) -> None:
        """Store an OAuth token.

        Args:
            service_name: Unique identifier for the service.
            token: OAuth token data to store.
            metadata: Token metadata including provider info.
        """
        stored_token = StoredToken(
            version=1,
            metadata=metadata,
            token=token,
        )

        # Load existing tokens
        tokens = self._load_tokens()

        # Add/update this token
        tokens[service_name] = json.loads(stored_token.model_dump_json())

        # Save back to file
        self._save_tokens(tokens)

    def retrieve(self, service_name: str) -> StoredToken | None:
        """Retrieve a stored OAuth token.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            StoredToken if found and valid, None otherwise.
        """
        tokens = self._load_tokens()

        if service_name not in tokens:
            return None

        try:
            return StoredToken.model_validate(tokens[service_name])
        except (ValueError, KeyError):
            # Token is corrupted or invalid
            return None

    def delete(self, service_name: str) -> bool:
        """Delete a stored token.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            True if token was deleted, False if it didn't exist.
        """
        tokens = self._load_tokens()

        if service_name not in tokens:
            return False

        del tokens[service_name]
        self._save_tokens(tokens)
        return True

    def list_services(self) -> list[str]:
        """List all services with stored tokens.

        Returns:
            List of service names that have stored tokens.
        """
        tokens = self._load_tokens()
        return sorted(tokens.keys())

    def get_status(self, service_name: str) -> TokenStatus:
        """Get the status of a stored token.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            TokenStatus indicating the token's current state.
        """
        stored = self.retrieve(service_name)

        if stored is None:
            tokens = self._load_tokens()
            if service_name in tokens:
                # File exists but couldn't be parsed
                return TokenStatus.INVALID
            return TokenStatus.MISSING

        if stored.token.is_expired():
            return TokenStatus.EXPIRED

        return TokenStatus.VALID

    def clear_all(self) -> None:
        """Delete all stored tokens.

        This removes the entire tokens.json file.
        """
        if self.token_path.exists():
            self.token_path.unlink()
