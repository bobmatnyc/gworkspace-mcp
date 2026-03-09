# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


### Added

- Initial release of Google Workspace MCP Server
- OAuth 2.0 authentication infrastructure with token persistence
- CLI commands: `workspace setup`, `workspace doctor`, `workspace mcp`
- Token storage at `~/.gworkspace-mcp/tokens.json`

### Gmail Tools (18)
- `search_gmail_messages` - Search emails with Gmail query syntax
- `get_gmail_message_content` - Retrieve email content
- `send_email` - Send new emails
- `reply_to_email` - Reply to existing emails
- `create_draft` - Create email drafts
- `list_gmail_labels` - List all labels
- `create_gmail_label`, `delete_gmail_label` - Manage labels
- `modify_gmail_message` - Modify message labels
- `archive_gmail_message`, `trash_gmail_message`, `untrash_gmail_message`
- `mark_gmail_as_read`, `mark_gmail_as_unread`
- `star_gmail_message`, `unstar_gmail_message`
- Batch operations: `batch_modify`, `batch_archive`, `batch_trash`, `batch_mark_read`, `batch_delete`

### Calendar Tools (10)
- `list_calendars` - List all calendars
- `create_calendar`, `update_calendar`, `delete_calendar`
- `get_events` - List calendar events
- `create_event`, `update_event`, `delete_event`

### Drive Tools (17)
- `search_drive_files` - Search files
- `get_drive_file_content` - Read file content
- `create_drive_folder` - Create folders
- `upload_drive_file`, `delete_drive_file`, `move_drive_file`
- `list_drive_contents` - List folder contents
- `download_drive_folder` - Download folders (requires rclone)
- `upload_to_drive` - Upload files
- `sync_drive_folder` - Sync folders (requires rclone)

### Docs Tools (11)
- `create_document`, `append_to_document`, `get_document`
- `upload_markdown_as_doc`
- `list_document_comments`, `add_document_comment`, `reply_to_comment`
- Document Tabs: `list_document_tabs`, `get_tab_content`, `create_document_tab`, `update_tab_properties`, `move_tab`
- `render_mermaid_to_doc` - Render Mermaid diagrams

### Tasks Tools (10)
- `list_task_lists`, `get_task_list`
- `create_task_list`, `update_task_list`, `delete_task_list`
- `list_tasks`, `get_task`, `search_tasks`
- `create_task`, `update_task`, `complete_task`, `delete_task`, `move_task`

### Infrastructure
- Simplified OAuth from claude-mpm (850 -> 400 lines)
- No external dependencies on claude-mpm
- RcloneManager optional (4 tools degrade gracefully if rclone not installed)

[Unreleased]: https://github.com/masapasa/gworkspace-mcp/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/masapasa/gworkspace-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.9...v0.2.0
[0.1.9]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/masapasa/gworkspace-mcp/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/masapasa/gworkspace-mcp/releases/tag/v0.1.0

## v0.3.3 (2026-03-09)

### Feat

- add Claude skill auto-install on workspace setup
- use pypandoc as first-class dependency for pandoc conversion
- add pandoc conversion service for automatic document format conversion

## v0.3.2 (2026-03-06)

### Feat

- add add_sheet tool for inserting new sheets into existing spreadsheets

### Fix

- fall back to ../claude-mpm/.env.local for HOMEBREW_TAP_TOKEN
- use x-access-token format and GIT_TERMINAL_PROMPT=0 for Homebrew push

## v0.3.0 (2026-03-03)

### Feat

- add binary file transfer capability (Drive + Gmail)

## v0.2.1 (2026-03-01)

### Feat

- add PKCE (RFC 7636) to OAuth authorization flow

## v0.2.0 (2026-02-27)

## v0.1.29 (2026-02-26)

### Fix

- pass client_id and client_secret to Google Credentials for token refresh

## v0.1.28 (2026-02-25)

### Feat

- Configure for shared bobmatnyc/homebrew-tools tap

## v0.1.27 (2026-02-24)

### Feat

- Add unified publishing system for PyPI, GitHub, and Homebrew

### Fix

- Update Makefile to use uv run python for tests

## v0.1.25 (2026-02-24)

## v0.1.24 (2026-02-17)

### Fix

- Use Arial font and remove heading bookmarks in Google Docs

## v0.1.23 (2026-02-17)

### Fix

- Use PNG instead of SVG for mermaid diagrams in Google Docs

## v0.1.22 (2026-02-17)

## v0.1.21 (2026-02-17)

### Feat

- Enhanced markdown-to-GDocs with mermaid diagram support
- Web Application OAuth with custom redirect URI support
- Add Google Slides API support with 10 new tools
- Add Sheets write tools and no-browser OAuth flow
- Add Google Sheets multi-tab support with 3 new tools
- Project-level token storage and .gitignore auto-add
- project-level only token storage
- support project-level token storage

### Fix

- Auto-open browser for OAuth flow
- add missing from_version field to migration 0002
- rename service key from 'google-workspace' to 'gworkspace-mcp'
- OAuth redirect URI handling and CI test failures

## v0.1.9 (2026-02-14)

### Refactor

- simplify OAuth env vars to GOOGLE_OAUTH_REDIRECT_URI only

## v0.1.8 (2026-02-14)

### Fix

- improve env var loading and OAuth configuration

## v0.1.7 (2026-02-14)

### Feat

- make OAuth port and redirect URI configurable

## v0.1.6 (2026-02-14)

### Fix

- use dynamic port for OAuth redirect URI

## v0.1.5 (2026-02-14)

### Fix

- update MCP server name to gworkspace-mcp

## v0.1.4 (2026-02-14)

### BREAKING CHANGE

- Python module renamed for consistency with package name.

### Refactor

- rename module google_workspace_mcp -> gworkspace_mcp

## v0.1.3 (2026-02-13)

### BREAKING CHANGE

- Credentials directory changed from
~/.google-workspace-mcp/ to ~/.gworkspace-mcp/

### Feat

- add declarative YAML-based migration system

### Refactor

- standardize naming to gworkspace-mcp

## v0.1.1 (2026-02-10)

### Feat

- Comprehensive code review fixes and feature additions

## v0.1.0 (2026-02-10)

### Feat

- Extract Google Workspace MCP server from claude-mpm
- Add OAuth infrastructure for Google Workspace authentication

### Fix

- Update publish script for gworkspace-mcp package name
- Resolve lint errors and update mypy config

### Refactor

- **package**: Rename PyPI package from google-workspace-mcp to gworkspace-mcp
