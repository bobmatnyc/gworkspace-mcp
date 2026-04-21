# Google Workspace MCP Server

Connect Claude to Google Workspace APIs through the Model Context Protocol (MCP).

[![PyPI version](https://badge.fury.io/py/gworkspace-mcp.svg)](https://badge.fury.io/py/gworkspace-mcp)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/masapasa/google-workspace-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/masapasa/google-workspace-mcp/actions/workflows/test.yml)

## Features

**116 MCP tools** across 7 Google Workspace APIs:

| Service | Tools | Capabilities |
|---------|-------|--------------|
| **Gmail** | 27 | Search, send, reply, drafts, labels, filters, formatting, batch operations, **attachments** |
| **Calendar** | 8 | List calendars, create/update/delete events, manage attendees, free/busy |
| **Drive** | 17 | Search, upload/download **binary files**, folders, permissions, sync (rclone integration) |
| **Docs** | 17 | Create, edit, format text/paragraphs, tables, lists, tabs, comments |
| **Sheets** | 12 | Create, read, write, format cells, charts, merge, conditional formatting |
| **Slides** | 21 | Create presentations, slides, format text, backgrounds, layouts |
| **Tasks** | 13 | Task lists, create/update/complete tasks, subtasks, search |

### Highlights

- **Full Gmail Management**: Search with advanced queries, send/reply with file attachments, organize with labels, filters, rich HTML formatting, batch operations
- **Binary File Transfer**: Upload any file type to Drive via local path; download Drive files and Gmail attachments to disk
- **Calendar Integration**: Create events with attendees, manage multiple calendars, handle timezones, check availability
- **Drive Operations**: Search files, manage folders, permissions, upload/download with optional rclone sync
- **Google Docs**: Create and edit documents, rich text formatting, tables, lists, tabs, comments, Mermaid diagrams
- **Google Sheets**: Create spreadsheets, format cells, charts, conditional formatting, merge cells, number formats
- **Google Slides**: Create presentations, format text, add images/text boxes, backgrounds, layouts, bullet lists
- **Tasks API**: Full task management with lists, subtasks, due dates, and cross-list search

### Binary File Transfer (v0.3.0)

Work with any file type — not just text:

```
# Upload a JPEG to Drive
upload_drive_file(local_path="/path/to/photo.jpg", parent_id="<folder-id>")

# Download a Drive file to disk (PDF, image, etc.)
get_drive_file_content(file_id="<id>", save_path="/tmp/report.pdf")

# Send an email with attachments
send_email(to="...", subject="...", body="...", attachments=["/path/to/file.pdf"])

# List attachments in a received email
get_gmail_message_content(message_id="<id>")
# → response includes: attachments: [{filename, mimeType, size, attachmentId}, ...]

# Download a Gmail attachment
download_gmail_attachment(message_id="<id>", attachment_id="<att-id>", save_path="/tmp/file.pdf")
```

### Formatting Capabilities

- **Rich Text Formatting**: Apply bold, italic, underline, colors, fonts across Docs, Slides, and Gmail
- **Advanced Cell Formatting**: Background colors, borders, number formats, conditional formatting in Sheets
- **Professional Presentations**: Custom layouts, formatted text boxes, backgrounds, and bullet lists in Slides
- **HTML Email Creation**: Rich formatting for professional email communications

## Installation

```bash
pip install gworkspace-mcp
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install gworkspace-mcp
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
   - Google Sheets API
   - Google Slides API
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

## Multi-Account Support

Multiple Google accounts can be configured as named profiles, letting you switch between personal and work accounts without re-authenticating.

### Setting Up Multiple Accounts

```bash
# Set up a named profile (opens browser for each account)
workspace setup --account personal@gmail.com
workspace setup --account work@company.com

# List all configured profiles
workspace accounts list

# Switch the default profile
workspace accounts default work@company.com

# Remove a profile
workspace accounts remove personal@gmail.com

# Check authentication status for a specific account
workspace doctor --account work@company.com
```

### Using Accounts Per Tool Call

Every MCP tool accepts an optional `account` parameter:

```
search_gmail_messages(query="budget", account="work@company.com")
get_events(calendar_id="primary", account="personal@gmail.com")
```

### Account Resolution Order

When `account` is not specified, the server selects the account in this order:

1. `account` parameter in the tool call (explicit, highest priority)
2. `GWORKSPACE_ACCOUNT` environment variable (session-wide override)
3. Default profile set via `workspace accounts default`
4. Fallback to `"gworkspace-mcp"` (backward compatible with existing tokens)

### Session-Wide Account Override

Set `GWORKSPACE_ACCOUNT` to make all tool calls in a session use a specific account without passing `account` each time:

```bash
export GWORKSPACE_ACCOUNT=work@company.com
workspace mcp
```

### Listing Configured Accounts

The `list_accounts` MCP tool returns all configured profiles:

```
list_accounts()
# → [{email, is_default, created_at}, ...]
```

### Storage Format

All profiles are stored in `~/.gworkspace-mcp/tokens.json`. The format is backward compatible — existing single-account tokens continue to work without any changes:

```json
{
  "gworkspace-mcp": { ... },
  "work@company.com": { ... },
  "personal@gmail.com": { ... }
}
```

## Authentication

### OAuth 2.0 Flow

This server uses OAuth 2.0 for secure authentication with Google APIs. The authentication flow:

1. `workspace setup` opens your browser for Google consent
2. You authorize access to Gmail, Calendar, Drive, Docs, Sheets, Slides, and Tasks
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
| `https://www.googleapis.com/auth/spreadsheets` | Read and write Google Sheets |
| `https://www.googleapis.com/auth/presentations` | Read and write Google Slides |
| `https://www.googleapis.com/auth/tasks` | Full Tasks access |

### Token Storage

Tokens are stored at: `~/.gworkspace-mcp/tokens.json`

This file contains your OAuth tokens. Keep it secure and do not share it.

## Available Tools

### Gmail (26 tools)

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
| `format_email_content` | Format email content with HTML styling |
| `set_email_signature` | Set Gmail signature with formatting |
| `create_formatted_email` | Create rich HTML emails with formatting |
| `list_gmail_filters` | List all Gmail filters |
| `create_gmail_filter` | Create new Gmail filter |
| `delete_gmail_filter` | Delete Gmail filter |
| `get_vacation_settings` | Get vacation auto-responder settings |
| `set_vacation_settings` | Configure vacation auto-responder |

### Calendar (8 tools)

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
| `query_free_busy` | Check availability for attendees |

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

### Sheets (12 tools)

| Tool | Description |
|------|-------------|
| `create_spreadsheet` | Create a new Google Spreadsheet |
| `get_spreadsheet_data` | Get spreadsheet metadata and structure |
| `list_spreadsheet_sheets` | List all sheets in a spreadsheet |
| `get_sheet_values` | Get values from a specific sheet/range |
| `update_sheet_values` | Update specific cells with new values |
| `append_sheet_values` | Append rows to end of sheet data |
| `clear_sheet_values` | Clear values from a range |
| `format_cells` | Apply formatting (colors, fonts, borders) |
| `set_number_format` | Set number formats (currency, percentage, date) |
| `merge_cells` | Merge cells across ranges |
| `set_column_width` | Adjust column widths |
| `create_chart` | Create charts (bar, line, pie) from data |

### Slides (21 tools)

| Tool | Description |
|------|-------------|
| `create_presentation` | Create a new Google Slides presentation |
| `get_presentation` | Get presentation metadata and structure |
| `list_presentations` | List accessible presentations |
| `get_presentation_text` | Extract all text from presentation |
| `get_slide` | Get specific slide content |
| `add_slide` | Add new slide with layout |
| `delete_slide` | Delete a slide |
| `update_slide_text` | Update text in slide shapes |
| `format_text_in_slide` | Apply text formatting to slide content |
| `add_formatted_text_box` | Add text box with custom formatting |
| `add_text_box` | Add basic text box to slide |
| `set_slide_background` | Set slide background color or image |
| `create_bulleted_list_slide` | Create slide with bulleted list |
| `apply_slide_layout` | Apply predefined layout to slide |
| `add_image` | Add image from URL to slide |

### Docs (17 tools)

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
| `format_text_in_document` | Apply text formatting (bold, italic, colors, fonts) |
| `format_paragraph_in_document` | Apply paragraph formatting (alignment, spacing) |
| `create_list_in_document` | Create bulleted or numbered lists |
| `insert_table_in_document` | Insert tables with custom dimensions |
| `apply_heading_style` | Apply heading styles (H1, H2, etc.) |
| `set_document_margins` | Configure document margins |
| `publish_markdown_to_doc` | Publish markdown content as Google Doc |

### Accounts (1 tool)

| Tool | Description |
|------|-------------|
| `list_accounts` | List all configured profiles with email, is_default, and created_at |

### Tasks (13 tools)

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
# Authenticate with Google (default profile)
workspace setup

# Authenticate a named profile
workspace setup --account NAME

# Check authentication status and dependencies
workspace doctor

# Check status for a specific account
workspace doctor --account NAME

# Manage named profiles
workspace accounts list          # show all profiles with default marker
workspace accounts default NAME  # switch the default profile
workspace accounts remove NAME   # remove a profile

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
- **[API Reference](docs/api/)** - Complete tool documentation for all 116 tools
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

Delete `~/.gworkspace-mcp/tokens.json` and run `workspace setup` again.

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
- **PyPI**: https://pypi.org/project/gworkspace-mcp/

## Acknowledgments

Extracted from [claude-mpm](https://github.com/masapasa/claude-mpm) - Multi-agent project manager with MCP server integrations.
