"""Simplified OAuth token storage for Google Workspace MCP.

This module provides basic JSON-based token persistence without
encryption. For production use, consider adding encryption.

Token Storage (default, project-level):
  - Tokens are written to .gworkspace-mcp/tokens.json relative to cwd.
  - The directory is created automatically if it does not exist.
  - Use ``workspace setup --user`` to store at the user-level path instead.

Token Lookup Order (for retrieval):
  1. Project-level: .gworkspace-mcp/tokens.json  (relative to cwd)
  2. User-level:    ~/.gworkspace-mcp/tokens.json (home directory)

The user-level path uses Path.home() so that Claude Desktop and other
MCP hosts (which may start with cwd=/ or similar read-only paths on
macOS Catalina+) can always read credentials stored there.

IMPORTANT: Each machine requires its own authentication.
Run `gworkspace-mcp setup` to authenticate.
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

# User home credentials directory -- Path.home() is always writable,
# unlike Path.cwd() which resolves to "/" when Claude Desktop launches MCP servers.
CREDENTIALS_DIR = Path.home() / ".gworkspace-mcp"
TOKEN_FILE = CREDENTIALS_DIR / "tokens.json"

# Project-level credentials directory -- checked first during retrieval.
PROJECT_TOKEN_FILE = Path.cwd() / ".gworkspace-mcp" / "tokens.json"


def get_token_path() -> Path:
    """Get the default (project-level) token storage path.

    Returns the project-level path (``.gworkspace-mcp/tokens.json``
    relative to cwd) which is the default write target for
    ``workspace setup``.

    Returns:
        Path to ./.gworkspace-mcp/tokens.json (project-level)
    """
    return PROJECT_TOKEN_FILE


class TokenStorage:
    """Simple JSON-based storage for OAuth tokens.

    Supports a two-tier lookup: project-level tokens are checked first,
    then user-level tokens.  Writes always go to the project-level
    directory by default (creating it if necessary).

    When a custom ``token_path`` is passed to the constructor, only that
    single path is used (no two-tier lookup).

    Attributes:
        token_path: Primary token path used for writes.  Defaults to
            the project-level path (``.gworkspace-mcp/tokens.json``
            relative to cwd).
        user_token_path: Always points to ~/.gworkspace-mcp/tokens.json.

    Example:
        ```python
        storage = TokenStorage()

        # Store a token (writes to ./.gworkspace-mcp/tokens.json)
        token = OAuthToken(
            access_token="abc123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            scopes=["read", "write"]
        )
        metadata = TokenMetadata(service_name="gworkspace-mcp", provider="google")
        storage.store("gworkspace-mcp", token, metadata)

        # Retrieve the token (checks project-level, then user-level)
        stored = storage.retrieve("gworkspace-mcp")
        if stored:
            print(f"Token expires at: {stored.token.expires_at}")
        ```
    """

    def __init__(self, token_path: Path | None = None) -> None:
        """Initialize token storage.

        Args:
            token_path: Custom path for tokens.json.
                When provided, *only* this path is used (no project /
                user-level fallback).  When omitted, the two-tier
                lookup is enabled with the project-level path as the
                default write target.
        """
        # Always record the user-level path for fallback / merging.
        self.user_token_path: Path = TOKEN_FILE

        if token_path is not None:
            # Explicit path -- single-path mode, no fallback.
            self._project_token_path: Path | None = None
            self.token_path: Path = token_path
        else:
            # Two-tier mode: project-level is *always* the write target.
            # The directory is created automatically by _ensure_credentials_dir.
            self._project_token_path = PROJECT_TOKEN_FILE
            self.token_path = PROJECT_TOKEN_FILE

        self.credentials_dir: Path = self.token_path.parent

        # Run pending migrations automatically before any other operations
        self._run_migrations()
        self._ensure_credentials_dir()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _has_fallback(self) -> bool:
        """Return True when two-tier lookup is active."""
        return self._project_token_path is not None

    def _run_migrations(self) -> None:
        """Run pending migrations automatically.

        This ensures the credentials directory is migrated from old
        locations before any token operations are attempted.
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

    @staticmethod
    def _load_tokens_from(path: Path) -> dict[str, dict]:
        """Load all tokens from a specific JSON file.

        Args:
            path: Path to a tokens.json file.

        Returns:
            Dictionary mapping service names to token data.
        """
        if not path.exists():
            return {}

        try:
            with open(path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _load_tokens(self) -> dict[str, dict]:
        """Load tokens from the primary path.

        Returns:
            Dictionary mapping service names to token data.
        """
        return self._load_tokens_from(self.token_path)

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        service_name: str,
        token: OAuthToken,
        metadata: TokenMetadata,
    ) -> None:
        """Store an OAuth token.

        Tokens are written to ``self.token_path`` which defaults to the
        project-level path (``.gworkspace-mcp/tokens.json`` relative to
        cwd).  The directory is created automatically if it does not
        exist.

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

        # Load existing tokens from the *write target*
        tokens = self._load_tokens()

        # Add/update this token
        tokens[service_name] = json.loads(stored_token.model_dump_json())

        # Save back to file
        self._save_tokens(tokens)

    def retrieve(self, service_name: str) -> StoredToken | None:
        """Retrieve a stored OAuth token.

        In two-tier mode the project-level file is checked first.  If
        the service is not found (or is invalid) there, the user-level
        file is consulted as a fallback.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            StoredToken if found and valid, None otherwise.
        """
        # Try primary path first
        result = self._retrieve_from(self.token_path, service_name)
        if result is not None:
            return result

        # Fallback to user-level when two-tier mode is active and the
        # primary path is the project-level one.
        if self._has_fallback and self.token_path != self.user_token_path:
            return self._retrieve_from(self.user_token_path, service_name)

        return None

    @staticmethod
    def _retrieve_from(path: Path, service_name: str) -> StoredToken | None:
        """Try to retrieve a token for *service_name* from *path*."""
        tokens = TokenStorage._load_tokens_from(path)
        if service_name not in tokens:
            return None
        try:
            return StoredToken.model_validate(tokens[service_name])
        except (ValueError, KeyError):
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

        In two-tier mode the results are merged from both project-level
        and user-level files.  Project-level entries take precedence for
        duplicates (they appear first in the lookup order).

        Returns:
            Sorted list of service names that have stored tokens.
        """
        # Start with user-level tokens as the base
        if self._has_fallback and self.token_path != self.user_token_path:
            merged = self._load_tokens_from(self.user_token_path)
            # Project-level tokens override user-level on key collision
            merged.update(self._load_tokens_from(self.token_path))
        else:
            merged = self._load_tokens()

        return sorted(merged.keys())

    def get_status(self, service_name: str) -> TokenStatus:
        """Get the status of a stored token.

        In two-tier mode this reflects the merged view: if the
        project-level file has a valid token the status is VALID even
        when the user-level file is missing or expired.

        Args:
            service_name: Unique identifier for the service.

        Returns:
            TokenStatus indicating the token's current state.
        """
        stored = self.retrieve(service_name)

        if stored is None:
            # Check whether raw data exists but could not be parsed
            tokens = self._load_tokens()
            if self._has_fallback and self.token_path != self.user_token_path:
                user_tokens = self._load_tokens_from(self.user_token_path)
                tokens = {**user_tokens, **tokens}

            if service_name in tokens:
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

    # ------------------------------------------------------------------
    # Multi-profile API
    # ------------------------------------------------------------------

    def list_profiles(self) -> list[dict]:
        """List all stored profiles with their metadata.

        In two-tier mode, profiles from both project-level and user-level
        files are merged, with project-level taking precedence.

        Returns:
            List of dicts with keys: profile_name, email, is_default,
            created_at, last_refreshed.
        """
        if self._has_fallback and self.token_path != self.user_token_path:
            merged = self._load_tokens_from(self.user_token_path)
            merged.update(self._load_tokens_from(self.token_path))
        else:
            merged = self._load_tokens()

        profiles = []
        for profile_name, data in merged.items():
            try:
                stored = StoredToken.model_validate(data)
                profiles.append(
                    {
                        "profile_name": profile_name,
                        "email": stored.metadata.email,
                        "is_default": stored.metadata.is_default,
                        "created_at": stored.metadata.created_at,
                        "last_refreshed": stored.metadata.last_refreshed,
                    }
                )
            except (ValueError, KeyError):
                # Skip corrupted entries
                continue

        return profiles

    def get_default_profile(self) -> str:
        """Get the name of the default profile.

        Resolution order:
        1. Profile explicitly marked as default (is_default=True).
        2. If exactly one profile exists, return its name (implicit default).
        3. Fall back to DEFAULT_PROFILE constant ("gworkspace-mcp").

        Returns:
            Profile name to use as the default.
        """
        from gworkspace_mcp.server.constants import DEFAULT_PROFILE

        profiles = self.list_profiles()

        if not profiles:
            return DEFAULT_PROFILE

        # Return explicitly marked default
        for p in profiles:
            if p["is_default"]:
                return p["profile_name"]

        # Single profile — implicit default
        if len(profiles) == 1:
            return profiles[0]["profile_name"]

        return DEFAULT_PROFILE

    def set_default_profile(self, profile_name: str) -> bool:
        """Mark a profile as the default, clearing the flag on all others.

        Args:
            profile_name: The profile to mark as default.

        Returns:
            True if the profile was found and updated, False otherwise.
        """
        stored = self.retrieve(profile_name)
        if stored is None:
            return False

        # Load ALL profiles from write target and update is_default flags
        tokens = self._load_tokens()

        # Also pull from user-level if in two-tier mode (to update cross-tier)
        if self._has_fallback and self.token_path != self.user_token_path:
            user_tokens = self._load_tokens_from(self.user_token_path)
            # Merge: project-level overrides user-level
            all_tokens = {**user_tokens, **tokens}
        else:
            all_tokens = tokens

        if profile_name not in all_tokens:
            return False

        # Update is_default for all profiles in the merged view
        import json as _json

        for name in all_tokens:
            try:
                entry = StoredToken.model_validate(all_tokens[name])
                entry.metadata.is_default = name == profile_name
                all_tokens[name] = _json.loads(entry.model_dump_json())
            except (ValueError, KeyError):
                continue

        # Write back — only to the primary write target (project-level)
        # We only persist what belongs in this file
        write_tokens: dict[str, dict] = {}
        primary_names = set(self._load_tokens().keys())

        if self._has_fallback and self.token_path != self.user_token_path:
            user_names = set(self._load_tokens_from(self.user_token_path).keys())
        else:
            user_names = set()

        # Include profile_name regardless of which file it came from (move to primary)
        names_to_write = primary_names | {profile_name}
        for name in names_to_write:
            if name in all_tokens:
                write_tokens[name] = all_tokens[name]

        self._save_tokens(write_tokens)

        # Also update user-level file if the profile lives there
        if self._has_fallback and profile_name in user_names and profile_name not in primary_names:
            import json as _json2

            user_data = self._load_tokens_from(self.user_token_path)
            for name in user_data:
                try:
                    entry = StoredToken.model_validate(user_data[name])
                    entry.metadata.is_default = name == profile_name
                    user_data[name] = _json2.loads(entry.model_dump_json())
                except (ValueError, KeyError):
                    continue
            with open(self.user_token_path, "w") as f:
                import json as _json3

                _json3.dump(user_data, f, indent=2, default=str)
            self.user_token_path.chmod(0o600)

        return True
