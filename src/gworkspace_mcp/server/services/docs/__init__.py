"""Google Docs service package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.services.docs import (
    comments,
    core,
    formatting,
    headers_footers,
    markdown,
    markdown_file,
    table_ops,
    templates,
)

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = (
    comments.TOOLS
    + core.TOOLS
    + markdown.TOOLS
    + markdown_file.TOOLS
    + formatting.TOOLS
    + table_ops.TOOLS
    + templates.TOOLS
    + headers_footers.TOOLS
)


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Docs handlers."""
    handlers: dict[str, Any] = {}
    for mod in [
        comments,
        core,
        markdown,
        markdown_file,
        formatting,
        table_ops,
        templates,
        headers_footers,
    ]:
        handlers.update(mod.get_handlers(svc))
    return handlers
