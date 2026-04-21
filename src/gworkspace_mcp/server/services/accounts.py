"""Accounts service module for MCP server — profile discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="list_accounts",
        description=(
            "List all configured Google account profiles. "
            "Use this to discover available accounts before making tool calls "
            "with a specific 'account' parameter. "
            "Returns profile names, associated emails, and which profile is the default."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
]


def get_handlers(service: BaseService) -> dict[str, Any]:
    """Return tool name → handler mapping for the accounts service.

    Args:
        service: BaseService instance providing token storage access.

    Returns:
        Mapping of tool names to async handler callables.
    """

    async def list_accounts(args: dict[str, Any]) -> dict[str, Any]:
        """List all configured Google account profiles.

        Args:
            args: Unused; no parameters accepted.

        Returns:
            Dict with 'accounts' list, 'total' count, and usage 'hint'.
        """
        profiles = service.storage.list_profiles()
        return {
            "accounts": [
                {
                    "profile": p["profile_name"],
                    "email": p.get("email"),
                    "is_default": p.get("is_default", False),
                    "created_at": str(p["created_at"]) if p.get("created_at") else None,
                }
                for p in profiles
            ],
            "total": len(profiles),
            "hint": (
                "Pass the 'profile' value as the 'account' parameter in any "
                "tool call to use that account."
            ),
        }

    return {"list_accounts": list_accounts}
