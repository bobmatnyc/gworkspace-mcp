"""Google Workspace MCP server — wires up all service modules."""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from gworkspace_mcp.server.base import BaseService, _active_account
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
        async def list_tools() -> list[Tool]:  # pyright: ignore[reportUnusedVariable]
            return ALL_TOOLS

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:  # pyright: ignore[reportUnusedVariable]
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
        """Dispatch a tool call to the appropriate service handler.

        Extracts the optional ``account`` parameter before invoking the handler
        and sets it as a ContextVar so that ``_get_access_token`` can resolve
        the correct profile without requiring every handler to pass it explicitly.
        """
        handler = self._all_handlers().get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        # Extract account from arguments and set ContextVar for this call
        account = arguments.pop("account", None)
        token = _active_account.set(account)
        try:
            return await handler(arguments)
        finally:
            _active_account.reset(token)

    # Backward-compatibility aliases: map old private method names to new action-based handlers.
    # Each entry is (old_attr_name_without_underscore, new_tool_name, action_value_or_None).
    # If action_value is not None, it is injected as args["action"] before dispatching.
    _COMPAT_ALIASES: dict[str, tuple[str, str | None]] = {
        # Gmail
        "send_email": ("compose_email", "send"),
        "create_draft": ("compose_email", "draft"),
        "send_draft": ("compose_email", "send_draft"),
        # Calendar
        "list_calendars": ("manage_calendars", "list"),
        "create_event": ("manage_events", "create"),
        # Tasks
        "list_task_lists": ("manage_task_lists", "list"),
        "create_task": ("manage_tasks", "create"),
        # Sheets
        "list_spreadsheet_sheets": ("get_spreadsheet", "list_sheets"),
        "get_sheet_values": ("get_spreadsheet", "get_sheet"),
        "get_spreadsheet_data": ("get_spreadsheet", "get_all"),
        "create_spreadsheet": ("manage_spreadsheet", "create"),
        "update_sheet_values": ("modify_sheet_values", "update"),
        "append_sheet_values": ("modify_sheet_values", "append"),
        "clear_sheet_values": ("modify_sheet_values", "clear"),
        # Slides
        "list_presentations": ("get_slides", "list"),
        "get_presentation": ("get_slides", "get_presentation"),
        "get_slide": ("get_slides", "get_slide"),
        "get_presentation_text": ("get_slides", "get_text"),
        "create_presentation": ("manage_slides", "create"),
        "add_slide": ("manage_slides", "add_slide"),
        "delete_slide": ("manage_slides", "delete_slide"),
        "update_slide_text": ("manage_slides", "update_text"),
        # add_slide_content uses "type" field, not "action"
        # Handled separately via _COMPAT_TYPE_ALIASES
    }

    # Like _COMPAT_ALIASES but inject into "type" key instead of "action"
    _COMPAT_TYPE_ALIASES: dict[str, tuple[str, str]] = {
        "add_text_box": ("add_slide_content", "text_box"),
        "add_image": ("add_slide_content", "image"),
    }

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown _name attributes to service handlers for test compatibility.

        Allows tests to call ``server._search_gmail_messages(args)`` directly.
        The leading underscore is stripped and the tool name is looked up.

        Also supports backward-compatibility aliases for renamed/consolidated tools —
        e.g., ``server._send_email(args)`` transparently calls ``compose_email`` with
        ``action='send'`` injected into the arguments.
        """
        if name.startswith("_"):
            tool_name = name[1:]  # strip leading underscore
            handlers = self._all_handlers()

            # Check backward-compat alias table first (inject into "action" key)
            if tool_name in self._COMPAT_ALIASES:
                new_tool, action = self._COMPAT_ALIASES[tool_name]
                if new_tool in handlers:
                    handler = handlers[new_tool]

                    async def _compat_wrapper(args: dict[str, Any], _h=handler, _a=action) -> Any:
                        merged = dict(args)
                        if _a is not None:
                            merged.setdefault("action", _a)
                        return await _h(merged)

                    return _compat_wrapper

            # Check type-alias table (inject into "type" key)
            if tool_name in self._COMPAT_TYPE_ALIASES:
                new_tool, type_val = self._COMPAT_TYPE_ALIASES[tool_name]
                if new_tool in handlers:
                    handler = handlers[new_tool]

                    async def _compat_type_wrapper(
                        args: dict[str, Any], _h=handler, _t=type_val
                    ) -> Any:
                        merged = dict(args)
                        merged.setdefault("type", _t)
                        return await _h(merged)

                    return _compat_type_wrapper

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
