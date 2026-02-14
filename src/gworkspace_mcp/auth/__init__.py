"""OAuth authentication for Google Workspace MCP.

This package provides simplified OAuth2 authentication for
Google Workspace services (Gmail, Calendar, Drive, Docs, Tasks).

Quick Start:
    ```python
    from gworkspace_mcp.auth import OAuthManager

    manager = OAuthManager()

    # Authenticate
    token = await manager.authenticate(
        client_id="your-client-id",
        client_secret="your-client-secret"  # pragma: allowlist secret
    )

    # Get credentials for API use
    credentials = manager.get_credentials()
    ```
"""

from gworkspace_mcp.auth.models import (
    OAuthToken,
    StoredToken,
    TokenMetadata,
    TokenStatus,
)
from gworkspace_mcp.auth.oauth_manager import GOOGLE_WORKSPACE_SCOPES, OAuthManager
from gworkspace_mcp.auth.token_storage import TokenStorage

__all__ = [
    "OAuthManager",
    "TokenStorage",
    "OAuthToken",
    "StoredToken",
    "TokenMetadata",
    "TokenStatus",
    "GOOGLE_WORKSPACE_SCOPES",
]
