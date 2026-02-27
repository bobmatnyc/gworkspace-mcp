# Google Workspace MCP Server

## Project Information
- **Path**: /Users/masa/Projects/gworkspace-mcp
- **Language**: Python
- **Framework**: MCP (Model Context Protocol)
- **Purpose**: Standalone Google Workspace MCP server with OAuth authentication

## Project Status

### Completed Phases ✅
- **Phase 1**: Project scaffolding (pyproject.toml, CLI structure)
- **Phase 2**: OAuth infrastructure (~400 lines, simplified from claude-mpm)
  - Token storage at `~/.gworkspace-mcp/tokens.json`
  - CLI commands: `workspace setup`, `workspace doctor`
- **Phase 3**: MCP server extraction (4,595 lines, 65 tools)
  - Extracted from claude-mpm monorepo
  - All Google Workspace APIs: Gmail, Calendar, Drive, Docs, Tasks
  - RcloneManager optional (4 tools require rclone)
- **Phase 4**: Testing infrastructure (COMPLETED ✅)
  - Unit tests for OAuth flow
  - Integration tests with mock Google APIs
  - MCP Inspector testing
  - CI/CD setup (GitHub Actions)
- **Phase 5**: Feature expansion (COMPLETED ✅)
  - Added Google Sheets API (12 tools)
  - Added Google Slides API (21 tools)
  - Rich formatting capabilities across all services
  - Expanded from 65 → 114 tools

### Current Phase 🔄
- **Phase 6**: Documentation + PyPI publish (IN PROGRESS)
  - Comprehensive README and docs update
  - API reference for all 114 tools
  - Publishing setup for PyPI
  - Claude Desktop integration guide

## Git Commits
- `a3726a6`: Initial project scaffolding
- `9802ba2`: OAuth infrastructure (Phase 2)
- `628de1e`: MCP server extraction (Phase 3)

## Key Technologies
- Python 3.10+
- google-auth, google-auth-oauthlib
- google-api-python-client
- MCP (Model Context Protocol)
- Click (CLI framework)
- Pydantic (data validation)

## Development Guidelines

### Installation
```bash
cd /Users/masa/Projects/gworkspace-mcp
pip install -e .
```

### Authentication Setup
```bash
workspace setup   # Opens browser for OAuth
workspace doctor  # Check auth status
```

### Running MCP Server
```bash
workspace mcp     # Starts MCP server on stdio
```

### Project Structure
```
src/google_workspace_mcp/
├── __init__.py
├── __version__.py (0.1.29)
├── cli/
│   └── main.py (CLI commands)
├── auth/
│   ├── models.py (Pydantic models)
│   ├── token_storage.py (Token persistence)
│   └── oauth_manager.py (OAuth flow)
└── server/
    ├── __init__.py (Tool documentation)
    └── google_workspace_server.py (MCP server, 4,595 lines)
```

## MCP Tools (114 Total)

### Gmail (26 tools)
- search_gmail_messages, get_gmail_message_content
- send_email, reply_to_email, create_draft
- list_gmail_labels, create_gmail_label, delete_gmail_label
- modify_gmail_message, archive/trash/untrash
- mark_gmail_as_read/unread, star/unstar
- Batch operations (modify, archive, trash, mark read, delete)
- **Vacation Responder**: get_vacation_settings, set_vacation_settings
- **Filters**: list_gmail_filters, create_gmail_filter, delete_gmail_filter
- **Rich Formatting**: format_email_content, create_formatted_email, set_email_signature

### Calendar (8 tools)
- list_calendars, create/update/delete_calendar
- get_events, create/update/delete_event
- query_free_busy (availability checking)

### Drive (17 tools)
- search_drive_files, get_drive_file_content
- create_drive_folder, upload/delete/move_drive_file
- list_drive_contents, download_drive_folder (rclone)
- upload_to_drive, sync_drive_folder (rclone)

### Docs (17 tools)
- create_document, append_to_document, get_document
- upload_markdown_as_doc, publish_markdown_to_doc
- list_document_comments, add_document_comment, reply_to_comment
- **Document Tabs**: list_document_tabs, get_tab_content, create_document_tab, update_tab_properties, move_tab
- **Mermaid Diagrams**: render_mermaid_to_doc (SVG/PNG conversion)
- **Rich Formatting** (NEW):
  - format_text_in_document, format_paragraph_in_document
  - apply_heading_style, set_document_margins
  - create_list_in_document, insert_table_in_document

### Sheets (12 tools) - NEW SERVICE
- create_spreadsheet, get_spreadsheet_data, list_spreadsheet_sheets
- get_sheet_values, update_sheet_values, append_sheet_values, clear_sheet_values
- **Formatting**: format_cells, set_number_format, merge_cells, set_column_width
- **Charts**: create_chart (bar, line, pie)

### Slides (21 tools) - NEW SERVICE
- create_presentation, get_presentation, list_presentations, get_presentation_text
- get_slide, add_slide, delete_slide, update_slide_text
- **Rich Content**: add_text_box, add_formatted_text_box, add_image
- **Formatting**: format_text_in_slide, set_slide_background, apply_slide_layout
- **Advanced**: create_bulleted_list_slide

### Tasks (13 tools)
- list_task_lists, get_task_list
- create/update/delete_task_list
- list_tasks, get_task, search_tasks
- create/update/complete/delete_task, move_task

## Session Resume Context

**Previous Session**: claude-mpm project (session-20260210-194921)
**Work Completed**:
- Extracted gworkspace-mcp from claude-mpm monorepo
- Phases 1-5 complete (scaffolding, OAuth, MCP server, testing, feature expansion)
- 114 tools functional across 7 Google Workspace services
- Added Google Sheets and Slides APIs with rich formatting
- Complete testing infrastructure and CI/CD

**Current Work** (Phase 6):
1. Update documentation for new services and formatting capabilities
2. API reference for all 114 tools
3. Prepare for version 0.2.0 release with new features
4. Update Claude Desktop integration examples

**Key Files to Review**:
- `src/google_workspace_mcp/server/google_workspace_server.py` (main MCP server)
- `src/google_workspace_mcp/auth/oauth_manager.py` (OAuth flow)
- `pyproject.toml` (dependencies and project config)

## Notes
- Original source: `/Users/masa/Projects/claude-mpm/src/claude_mpm/mcp/google_workspace_server.py`
- Simplified OAuth from 850 → 400 lines
- No claude-mpm dependencies remaining
- RcloneManager optional (4 tools degrade gracefully if missing)
- Token storage: `~/.gworkspace-mcp/tokens.json`

---

*Generated during gworkspace-mcp extraction project*
*Last updated: 2026-02-27 - Documentation update for formatting expansion*
*Session paused: 2026-02-10 19:49:21*
