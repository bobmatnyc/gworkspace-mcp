# Google Workspace MCP Server

Connect Claude to Google Workspace APIs including Gmail, Calendar, Drive, Docs, and Tasks.

## Features

- **66 tools** across five Google Workspace services
- **Gmail**: Search, read, send, label, archive messages
- **Calendar**: List, create, update events; check availability
- **Drive**: Search, list, upload, download, organize files
- **Docs**: Read, create, append documents; manage comments
- **Tasks**: Manage task lists and tasks

## Installation

**Note**: This is an alpha release extracted from claude-mpm. Installation will be available via pip in a future release.

```bash
# Future installation (not yet available)
pip install google-workspace-mcp
```

## Quick Start

### 1. OAuth Setup (Phase 2)

```bash
# Setup OAuth credentials
google-workspace-mcp setup

# Verify installation
google-workspace-mcp doctor
```

### 2. MCP Server (Phase 3)

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "google-workspace-mcp",
      "args": ["mcp"]
    }
  }
}
```

### 3. Use in Claude

Once configured, Claude will have access to 66 tools:

**Gmail Tools** (17 total):
- `search_gmail_messages`: Search Gmail with advanced queries
- `get_gmail_message_content`: Get full message content
- `send_email`: Send new email
- `reply_to_email`: Reply to existing thread
- `create_draft`: Save email as draft
- `list_gmail_labels`, `create_gmail_label`, `delete_gmail_label`
- `modify_gmail_message`: Add/remove labels
- `archive_gmail_message`, `trash_gmail_message`, `untrash_gmail_message`
- `mark_gmail_as_read`, `mark_gmail_as_unread`
- `star_gmail_message`, `unstar_gmail_message`
- `batch_modify_gmail_messages`, `batch_archive_gmail_messages`, `batch_trash_gmail_messages`, `batch_mark_gmail_as_read`, `batch_delete_gmail_messages`

**Calendar Tools** (6 total):
- `list_calendars`: List all calendars
- `create_calendar`, `update_calendar`, `delete_calendar`
- `get_events`: Get calendar events
- `create_event`, `update_event`, `delete_event`

**Drive Tools** (9 total):
- `search_drive_files`: Search Drive with queries
- `get_drive_file_content`: Download file content
- `create_drive_folder`: Create new folder
- `upload_drive_file`: Upload file
- `delete_drive_file`: Move to trash
- `move_drive_file`: Move to different folder
- `list_drive_contents`: List folder contents
- `download_drive_folder`: Batch download
- `upload_to_drive`: Batch upload
- `sync_drive_folder`: Sync local with Drive

**Docs Tools** (4 total):
- `create_document`: Create new Google Doc
- `get_document`: Read document content
- `append_to_document`: Add content to doc
- `upload_markdown_as_doc`: Convert Markdown to Doc
- `list_document_comments`: Get comments
- `add_document_comment`: Add comment
- `reply_to_comment`: Reply to comment

**Tasks Tools** (10 total):
- `list_task_lists`: List all task lists
- `get_task_list`, `create_task_list`, `update_task_list`, `delete_task_list`
- `list_tasks`: List tasks in list
- `get_task`: Get task details
- `search_tasks`: Search across all lists
- `create_task`, `update_task`, `complete_task`, `delete_task`, `move_task`

## Development Status

This package is being extracted from [claude-mpm](https://github.com/masapasa/claude-mpm) as a standalone installable MCP server.

**Roadmap**:
- **Phase 1** ✓: Project scaffolding (current)
- **Phase 2**: OAuth infrastructure extraction
- **Phase 3**: MCP server extraction (66 tools)
- **Phase 4**: Testing infrastructure
- **Phase 5**: Documentation and publishing

## Architecture

```
google-workspace-mcp/
├── src/google_workspace_mcp/
│   ├── cli/          # Command-line interface
│   ├── auth/         # OAuth2 authentication (Phase 2)
│   └── server/       # MCP server implementation (Phase 3)
├── tests/
│   ├── unit/         # Unit tests
│   └── integration/  # Integration tests
└── docs/             # Documentation
```

## Requirements

- Python 3.10+
- Google Cloud Project with Workspace APIs enabled
- OAuth2 credentials

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

This is an early extraction. Contributions welcome once Phase 3 is complete.

## Links

- **Source**: https://github.com/masapasa/google-workspace-mcp
- **Issues**: https://github.com/masapasa/google-workspace-mcp/issues
- **Parent Project**: https://github.com/masapasa/claude-mpm

## Acknowledgments

Extracted from [claude-mpm](https://github.com/masapasa/claude-mpm) - Multi-agent project manager with ticket tracking and MCP server integrations.
