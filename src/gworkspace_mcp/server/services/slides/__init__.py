"""Google Slides service package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.services.slides import content, core

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = core.TOOLS + content.TOOLS


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Slides handlers."""
    handlers: dict[str, Any] = {}
    for mod in [core, content]:
        handlers.update(mod.get_handlers(svc))
    return handlers
