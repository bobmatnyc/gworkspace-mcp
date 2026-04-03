"""Google Workspace MCP server — wires up all service modules."""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from gworkspace_mcp.server.base import BaseService
from gworkspace_mcp.server.services import calendar, docs, drive, gmail, sheets, slides, tasks

logger = logging.getLogger(__name__)

# Aggregate all tools from every service module
ALL_TOOLS: list[Tool] = (
    calendar.TOOLS
    + gmail.TOOLS
    + drive.TOOLS
    + docs.TOOLS
    + sheets.TOOLS
    + slides.TOOLS
    + tasks.TOOLS
)


class GoogleWorkspaceServer(BaseService):
    """MCP server for Google Workspace APIs.

    Aggregates tools and handlers from all service modules:
    Calendar, Gmail, Drive, Docs, Sheets, Slides, Tasks.
    """

    def __init__(self) -> None:
        """Initialize the Google Workspace MCP server."""
        super().__init__()
        self.server = Server("gworkspace-mcp")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return ALL_TOOLS

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                result = await self._dispatch_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                logger.exception("Error calling tool %s", name)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": str(e)}, indent=2),
                    )
                ]

    def _all_handlers(self) -> dict[str, Any]:
        """Return merged handler dict from all service modules."""
        handlers: dict[str, Any] = {}
        handlers.update(calendar.get_handlers(self))
        handlers.update(gmail.get_handlers(self))
        handlers.update(drive.get_handlers(self))
        handlers.update(docs.get_handlers(self))
        handlers.update(sheets.get_handlers(self))
        handlers.update(slides.get_handlers(self))
        handlers.update(tasks.get_handlers(self))
        return handlers

    async def _dispatch_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call to the appropriate service handler."""
        handler = self._all_handlers().get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        return await handler(arguments)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown _name attributes to service handlers for test compatibility.

        Allows tests to call ``server._search_gmail_messages(args)`` directly.
        The leading underscore is stripped and the tool name is looked up.
        """
        if name.startswith("_"):
            tool_name = name[1:]  # strip leading underscore
            handlers = self._all_handlers()
            if tool_name in handlers:
                # Return an async callable that takes arguments dict
                return handlers[tool_name]
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        finally:
            await self.close()


def main() -> None:
    """Entry point for the Google Workspace MCP server."""
    server = GoogleWorkspaceServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
