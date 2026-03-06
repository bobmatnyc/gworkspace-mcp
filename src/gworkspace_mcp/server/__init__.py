"""MCP server implementation for Google Workspace.

Provides 84 tools across Gmail, Calendar, Drive, Docs, Sheets, Slides, and Tasks:

Gmail Tools (21):
- List messages with search queries
- Get message details and metadata
- Send and reply to messages
- Manage labels and filters
- Search and archive operations
- Batch operations for efficiency
- NEW: Email formatting (HTML content, signatures, formatted emails)

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

Docs Tools (16):
- Create and manage documents
- Append and read content
- Upload markdown as Google Docs
- Comment management
- NEW: Text formatting (bold, italic, font size, colors)
- NEW: Paragraph formatting (alignment, spacing, indentation)
- NEW: Lists and tables insertion
- NEW: Heading styles application

Sheets Tools (12):
- List and manage spreadsheets
- Read and write cell data
- Multi-sheet operations
- Add new sheets/tabs to existing spreadsheets
- NEW: Cell formatting (colors, fonts, borders)
- NEW: Number formatting (currency, percentage, dates)
- NEW: Cell merging and column width
- NEW: Chart creation (bar, line, pie charts)

Slides Tools (15):
- List and manage presentations
- Read slide content and metadata
- Create and modify slides
- Add text boxes and images
- NEW: Text formatting in slides
- NEW: Slide backgrounds and layouts
- NEW: Bulleted list slides

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
