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
    table_format,
    table_ops,
    templates,
)
from gworkspace_mcp.server.services.docs import sync as docs_sync

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = (
    comments.TOOLS
    + core.TOOLS
    + markdown.TOOLS
    + markdown_file.TOOLS
    + formatting.TOOLS
    + table_ops.TOOLS
    + table_format.TOOLS
    + templates.TOOLS
    + headers_footers.TOOLS
    + docs_sync.TOOLS
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
        table_format,
        templates,
        headers_footers,
        docs_sync,
    ]:
        handlers.update(mod.get_handlers(svc))
    return handlers
