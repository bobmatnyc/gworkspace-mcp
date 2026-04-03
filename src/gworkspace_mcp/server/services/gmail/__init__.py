"""Gmail service package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.services.gmail import labels, messages, organize, settings

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = messages.TOOLS + labels.TOOLS + organize.TOOLS + settings.TOOLS


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Gmail handlers."""
    handlers: dict[str, Any] = {}
    for mod in [messages, labels, organize, settings]:
        handlers.update(mod.get_handlers(svc))
    return handlers
