"""Backward-compatibility shim — delegates to server.py.

The implementation has been refactored into service modules under
gworkspace_mcp.server.services.*. Import from gworkspace_mcp.server.server
for the canonical location.
"""

# Re-export auth symbols so existing test patches still resolve here.
from gworkspace_mcp.auth import OAuthManager, TokenStorage  # noqa: F401
from gworkspace_mcp.server.server import ALL_TOOLS, GoogleWorkspaceServer, main

__all__ = ["ALL_TOOLS", "GoogleWorkspaceServer", "OAuthManager", "TokenStorage", "main"]
