# Google Workspace MCP Server

Connect Claude to Google Workspace APIs through the Model Context Protocol (MCP).

[![PyPI version](https://badge.fury.io/py/google-workspace-mcp.svg)](https://badge.fury.io/py/google-workspace-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/masapasa/google-workspace-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/masapasa/google-workspace-mcp/actions/workflows/test.yml)

## Features

**66 MCP tools** across 5 Google Workspace APIs:

| Service | Tools | Capabilities |
|---------|-------|--------------|
| **Gmail** | 18 | Search, send, reply, drafts, labels, archive, trash, star, batch operations |
| **Calendar** | 10 | List calendars, create/update/delete events, manage attendees |
| **Drive** | 17 | Search, upload, download, folders, move, sync (rclone integration) |
| **Docs** | 11 | Create, read, append, tabs, comments, Mermaid diagrams |
| **Tasks** | 10 | Task lists, create/update/complete tasks, subtasks, search |

### Highlights

- **Full Gmail Management**: Search with advanced queries, send/reply, organize with labels, batch operations for efficiency
- **Calendar Integration**: Create events with attendees, manage multiple calendars, handle timezones
- **Drive Operations**: Search files, manage folders, upload/download with optional rclone sync
- **Google Docs**: Create and edit documents, manage tabs, add comments, render Mermaid diagrams to images
- **Tasks API**: Full task management with lists, subtasks, due dates, and cross-list search

## Installation

```bash
pip install google-workspace-mcp
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install google-workspace-mcp
```

For development:

```bash
git clone https://github.com/masapasa/google-workspace-mcp.git
cd google-workspace-mcp
pip install -e ".[dev]"
```

## Quick Start

### 1. Set Up Google Cloud Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Docs API
   - Google Tasks API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download and note your Client ID and Client Secret

### 2. Authenticate

```bash
# Set your credentials
export GOOGLE_OAUTH_CLIENT_ID='your-client-id'
export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'  # pragma: allowlist secret

# Run OAuth flow (opens browser)
workspace setup

# Verify authentication
workspace doctor
```

### 3. Start MCP Server

```bash
workspace mcp
```

### 4. Connect to Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "workspace",
      "args": ["mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"  // pragma: allowlist secret
      }
    }
  }
}
```

Restart Claude Desktop to activate.

## Authentication

### OAuth 2.0 Flow

This server uses OAuth 2.0 for secure authentication with Google APIs. The authentication flow:

1. `workspace setup` opens your browser for Google consent
2. You authorize access to Gmail, Calendar, Drive, Docs, and Tasks
3. Tokens are securely stored locally
4. Tokens auto-refresh when expired

### Required Scopes

The server requests the following OAuth scopes:

| Scope | Purpose |
|-------|---------|
| `https://www.googleapis.com/auth/gmail.modify` | Read, send, and organize Gmail |
| `https://www.googleapis.com/auth/calendar` | Full calendar access |
| `https://www.googleapis.com/auth/drive` | Full Drive access |
| `https://www.googleapis.com/auth/documents` | Read and write Google Docs |
| `https://www.googleapis.com/auth/tasks` | Full Tasks access |

### Token Storage

Tokens are stored at: `~/.google-workspace-mcp/tokens.json`

This file contains your OAuth tokens. Keep it secure and do not share it.

## Available Tools

### Gmail (18 tools)

| Tool | Description |
|------|-------------|
| `search_gmail_messages` | Search messages with Gmail query syntax |
| `get_gmail_message_content` | Get full message content by ID |
| `send_email` | Send a new email |
| `reply_to_email` | Reply to an existing thread |
| `create_draft` | Save email as draft |
| `list_gmail_labels` | List all labels (system and custom) |
| `create_gmail_label` | Create a custom label |
| `delete_gmail_label` | Delete a custom label |
| `modify_gmail_message` | Add/remove labels from a message |
| `archive_gmail_message` | Archive a message (remove from inbox) |
| `trash_gmail_message` | Move message to trash |
| `untrash_gmail_message` | Restore message from trash |
| `mark_gmail_as_read` | Mark message as read |
| `mark_gmail_as_unread` | Mark message as unread |
| `star_gmail_message` | Add star to message |
| `unstar_gmail_message` | Remove star from message |
| `batch_modify_gmail_messages` | Bulk add/remove labels |
| `batch_archive_gmail_messages` | Bulk archive messages |
| `batch_trash_gmail_messages` | Bulk trash messages |
| `batch_mark_gmail_as_read` | Bulk mark as read |
| `batch_delete_gmail_messages` | Permanently delete messages (caution!) |

### Calendar (10 tools)

| Tool | Description |
|------|-------------|
| `list_calendars` | List all accessible calendars |
| `create_calendar` | Create a new calendar |
| `update_calendar` | Update calendar properties |
| `delete_calendar` | Delete a calendar |
| `get_events` | Get events within a time range |
| `create_event` | Create a new event |
| `update_event` | Update an existing event |
| `delete_event` | Delete an event |

### Drive (17 tools)

| Tool | Description |
|------|-------------|
| `search_drive_files` | Search files with Drive query syntax |
| `get_drive_file_content` | Get file content (text files) |
| `create_drive_folder` | Create a new folder |
| `upload_drive_file` | Upload a text file |
| `delete_drive_file` | Delete a file or folder |
| `move_drive_file` | Move file to different folder |
| `list_drive_contents`* | List folder contents |
| `download_drive_folder`* | Download folder to local filesystem |
| `upload_to_drive`* | Upload local folder to Drive |
| `sync_drive_folder`* | Sync between local and Drive |

*Requires [rclone](https://rclone.org/) to be installed

### Docs (11 tools)

| Tool | Description |
|------|-------------|
| `create_document` | Create a new Google Doc |
| `get_document` | Get document content and structure |
| `append_to_document` | Append text to a document |
| `upload_markdown_as_doc` | Convert Markdown to Google Doc |
| `list_document_comments` | List all comments on a document |
| `add_document_comment` | Add a comment to a document |
| `reply_to_comment` | Reply to an existing comment |
| `list_document_tabs` | List all tabs in a document |
| `get_tab_content` | Get content from a specific tab |
| `create_document_tab` | Create a new tab |
| `update_tab_properties` | Update tab title or icon |
| `move_tab` | Move tab to new position |
| `render_mermaid_to_doc` | Render Mermaid diagram and insert into doc |

### Tasks (10 tools)

| Tool | Description |
|------|-------------|
| `list_task_lists` | List all task lists |
| `get_task_list` | Get a specific task list |
| `create_task_list` | Create a new task list |
| `update_task_list` | Update task list title |
| `delete_task_list` | Delete a task list |
| `list_tasks` | List tasks in a list |
| `get_task` | Get a specific task |
| `search_tasks` | Search tasks across all lists |
| `create_task` | Create a new task |
| `update_task` | Update task details |
| `complete_task` | Mark task as completed |
| `delete_task` | Delete a task |
| `move_task` | Move task or make it a subtask |

## CLI Commands

```bash
# Authenticate with Google
workspace setup

# Check authentication status and dependencies
workspace doctor

# Start the MCP server (for Claude Desktop)
workspace mcp

# Show version
workspace --version

# Show help
workspace --help
```

## Documentation

For detailed documentation, see the [docs/](docs/) directory:

- **[Getting Started](docs/getting-started/)** - Installation, authentication, quickstart
- **[User Guides](docs/guides/)** - Claude Desktop integration, CLI reference
- **[API Reference](docs/api/)** - Complete tool documentation for all 66 tools
- **[Development](docs/development/)** - Contributing, testing, releasing

## Development

```bash
# Clone and install
git clone https://github.com/masapasa/google-workspace-mcp.git
cd google-workspace-mcp
pip install -e ".[dev]"

# Run tests
pytest

# Code quality
ruff format src tests && ruff check src tests && mypy src
```

See [Contributing Guide](docs/development/contributing.md) for full development setup.

## Requirements

- **Python**: 3.10 or higher
- **Google Cloud Project**: With Workspace APIs enabled
- **OAuth 2.0 Credentials**: Desktop application type
- **Optional**: [rclone](https://rclone.org/) for Drive sync features (4 tools)
- **Optional**: [pandoc](https://pandoc.org/) for Markdown to Docs conversion
- **Optional**: [@mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli) for Mermaid diagrams

## Troubleshooting

### "Not authenticated" error

Run `workspace setup` to authenticate, or check status with `workspace doctor`.

### Token refresh failing

Delete `~/.google-workspace-mcp/tokens.json` and run `workspace setup` again.

### Missing rclone tools

The 4 rclone-based tools (`list_drive_contents`, `download_drive_folder`, `upload_to_drive`, `sync_drive_folder`) require rclone to be installed. Install from [rclone.org](https://rclone.org/install/).

### Claude Desktop not seeing tools

1. Ensure the config file path is correct for your OS
2. Restart Claude Desktop after config changes
3. Check that `workspace mcp` runs without errors

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Links

- **Repository**: https://github.com/masapasa/google-workspace-mcp
- **Issues**: https://github.com/masapasa/google-workspace-mcp/issues
- **PyPI**: https://pypi.org/project/google-workspace-mcp/

## Acknowledgments

Extracted from [claude-mpm](https://github.com/masapasa/claude-mpm) - Multi-agent project manager with MCP server integrations.
