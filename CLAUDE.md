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

### Current Phase 🔄
- **Phase 4**: Testing infrastructure (IN PROGRESS)
  - Unit tests for OAuth flow
  - Integration tests with mock Google APIs
  - MCP Inspector testing
  - CI/CD setup (GitHub Actions)

### Next Phase ⏭️
- **Phase 5**: Documentation + PyPI publish
  - Comprehensive README and docs
  - API reference for all 65 tools
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
├── __version__.py (0.1.0)
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

## MCP Tools (65 Total)

### Gmail (18 tools)
- search_gmail_messages, get_gmail_message_content
- send_email, reply_to_email, create_draft
- list_gmail_labels, create_gmail_label, delete_gmail_label
- modify_gmail_message, archive/trash/untrash
- mark_gmail_as_read/unread, star/unstar
- Batch operations (modify, archive, trash, mark read, delete)

### Calendar (10 tools)
- list_calendars, create/update/delete_calendar
- get_events, create/update/delete_event

### Drive (17 tools)
- search_drive_files, get_drive_file_content
- create_drive_folder, upload/delete/move_drive_file
- list_drive_contents, download_drive_folder (rclone)
- upload_to_drive, sync_drive_folder (rclone)

### Docs (11 tools)
- create_document, append_to_document, get_document
- upload_markdown_as_doc
- list_document_comments, add_document_comment, reply_to_comment
- **Document Tabs** (NEW):
  - list_document_tabs, get_tab_content
  - create_document_tab, update_tab_properties, move_tab
- **Mermaid Diagrams** (NEW):
  - render_mermaid_to_doc (SVG/PNG conversion)

### Tasks (10 tools)
- list_task_lists, get_task_list
- create/update/delete_task_list
- list_tasks, get_task, search_tasks
- create/update/complete/delete_task, move_task

## Session Resume Context

**Previous Session**: claude-mpm project (session-20260210-194921)
**Work Completed**:
- Extracted gworkspace-mcp from claude-mpm monorepo
- Phases 1-3 complete (scaffolding, OAuth, MCP server)
- 65 tools functional, ready for testing

**Next Steps**:
1. Complete Phase 4: Testing infrastructure
2. Unit tests for OAuth (token storage, refresh)
3. Integration tests with mock Google APIs
4. MCP Inspector testing for sample tools
5. CI/CD setup (GitHub Actions)

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
*Session paused: 2026-02-10 19:49:21*
