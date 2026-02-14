"""MCP server implementation for Google Workspace.

Provides 66 tools across Gmail, Calendar, Drive, Docs, and Tasks:

Gmail Tools (18):
- List messages with search queries
- Get message details and metadata
- Send and reply to messages
- Manage labels and filters
- Search and archive operations
- Batch operations for efficiency

Calendar Tools (10):
- List and create calendars
- Manage events with attendees
- Search across calendars
- Handle recurring events
- Delete events and calendars

Drive Tools (17):
- List and search files
- Create and manage folders
- Upload and download files
- Share permissions management
- Trash and delete operations
- Optional rclone sync features (4 tools)

Docs Tools (11):
- Create and manage documents
- Append and read content
- Upload markdown as Google Docs
- Comment management

Tasks Tools (10):
- List and manage task lists
- Create and update tasks
- Complete and delete tasks
- Search and move tasks

Transport: Stdio (for Claude Desktop)
Authentication: OAuth 2.0 with automatic token refresh
"""

from gworkspace_mcp.server.google_workspace_server import (
    GoogleWorkspaceServer,
    main,
)


def create_server() -> GoogleWorkspaceServer:
    """Create and configure a Google Workspace MCP server.

    Returns:
        GoogleWorkspaceServer: Configured server instance ready to run.

    Example:
        >>> server = create_server()
        >>> asyncio.run(server.run())
    """
    return GoogleWorkspaceServer()


__all__ = ["create_server", "GoogleWorkspaceServer", "main"]
