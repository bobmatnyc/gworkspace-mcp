"""Google Drive service package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.services.drive import files, sharing, sync

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = files.TOOLS + sharing.TOOLS + sync.TOOLS


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Drive handlers."""
    handlers: dict[str, Any] = {}
    for mod in [files, sharing, sync]:
        handlers.update(mod.get_handlers(svc))
    return handlers
