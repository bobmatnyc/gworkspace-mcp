"""Google Sheets service package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.services.sheets import core, formatting

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = core.TOOLS + formatting.TOOLS


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Sheets handlers."""
    handlers: dict[str, Any] = {}
    for mod in [core, formatting]:
        handlers.update(mod.get_handlers(svc))
    return handlers
