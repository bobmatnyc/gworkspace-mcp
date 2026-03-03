# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-03-03

### Added
- **Binary file transfer for Drive** — `upload_drive_file` now accepts a `local_path` parameter for uploading any binary or text file from disk; MIME type is auto-detected; `name` defaults to the local filename
- **Drive download to disk** — `get_drive_file_content` now accepts a `save_path` parameter; binary files are saved locally instead of returning an unreadable byte string
- **Gmail email attachments** — `send_email`, `create_draft`, and `reply_to_email` now accept an `attachments` list of local file paths, encoded with MIME multipart
- **Gmail attachment metadata** — `get_gmail_message_content` now returns an `attachments` list containing `{filename, mimeType, size, attachmentId}` for every attachment in the message
- **`download_gmail_attachment`** — New tool (#115) to download a specific Gmail attachment by ID to a local `save_path`
- PKCE (RFC 7636) support in the OAuth authorization flow for enhanced security

### Changed
- `get_drive_file_content` returns a helpful message for binary files when no `save_path` is provided: `[Binary file: N bytes. Use save_path to download.]`
- `upload_drive_file` multipart request body is now built as bytes (binary-safe); `content` parameter still works for text

### Fixed
- 4 pre-existing mypy type annotation errors in Slides and Sheets formatting tools

## [0.2.0] - 2026-02-27

### Added
- **Google Sheets API** (12 new tools): `create_spreadsheet`, `get_spreadsheet_data`, `list_spreadsheet_sheets`, `get_sheet_values`, `update_sheet_values`, `append_sheet_values`, `clear_sheet_values`, `format_cells`, `set_number_format`, `merge_cells`, `set_column_width`, `create_chart`
- **Google Slides API** (21 new tools): `create_presentation`, `get_presentation`, `list_presentations`, `get_presentation_text`, `get_slide`, `add_slide`, `delete_slide`, `update_slide_text`, `add_text_box`, `add_formatted_text_box`, `add_image`, `format_text_in_slide`, `set_slide_background`, `apply_slide_layout`, `create_bulleted_list_slide`
- **Rich Docs formatting** (6 new tools): `format_text_in_document`, `format_paragraph_in_document`, `apply_heading_style`, `set_document_margins`, `create_list_in_document`, `insert_table_in_document`
- **Gmail rich formatting** (3 new tools): `format_email_content`, `create_formatted_email`, `set_email_signature`
- **Gmail vacation responder**: `get_vacation_settings`, `set_vacation_settings`
- **Gmail filters**: `list_gmail_filters`, `create_gmail_filter`, `delete_gmail_filter`
- **Document tabs**: `list_document_tabs`, `get_tab_content`, `create_document_tab`, `update_tab_properties`, `move_tab`
- **Mermaid diagrams**: `render_mermaid_to_doc`
- Drive permissions: `list_file_permissions`, `share_file`, `update_file_permission`, `remove_file_permission`, `transfer_file_ownership`
- Drive: `copy_drive_file`, `rename_drive_file`
- Calendar: `query_free_busy`
- Total tool count expanded from 65 → 114

## [0.1.9] - 2026-02-14

### Changed
- Simplify OAuth environment variables to use only GOOGLE_OAUTH_REDIRECT_URI
- Port is now automatically parsed from the redirect URI
- Removed GOOGLE_OAUTH_PORT environment variable (redundant)
- Removed GOOGLE_REDIRECT_URI alias (use GOOGLE_OAUTH_REDIRECT_URI instead)

## [0.1.8] - 2026-02-14

### Fixed
- Improve env var loading and OAuth configuration
- Remove 'workspace' CLI alias
- Support GOOGLE_REDIRECT_URI env var
- Parse host/port from redirect URI automatically

## [0.1.7] - 2026-02-14

### Added
- Make OAuth port and redirect URI configurable via environment variables
  - `GWORKSPACE_OAUTH_PORT`: Set specific port for OAuth callback server
  - `GWORKSPACE_OAUTH_REDIRECT_URI`: Override the default redirect URI

## [0.1.6] - 2026-02-14

### Fixed
- Use dynamic port for OAuth redirect URI (works with http://localhost/ registered in GCP)

## [0.1.5] - 2026-02-14

### Fixed
- Update MCP server name to gworkspace-mcp for consistency

## [0.1.4] - 2026-02-14

### Changed
- **BREAKING**: Renamed internal module from `google_workspace_mcp` to `gworkspace_mcp`
  - Import paths changed from `from google_workspace_mcp import ...` to `from gworkspace_mcp import ...`

### Added
- Support for `.env.local` file for OAuth credentials configuration

## [0.1.3] - 2026-02-13

### Added
- Declarative YAML-based migration system for configuration updates

### Changed
- **BREAKING**: Standardized naming to gworkspace-mcp throughout the codebase
  - Credentials directory changed from `~/.google-workspace-mcp/` to `~/.gworkspace-mcp/`
  - Run migration to update existing installations

### Fixed
- Token storage path references in documentation

## [0.1.2] - 2026-02-12

### Added
- Comprehensive documentation structure (22 files, ~5,700 lines)
- API reference for all 66 tools (Gmail, Calendar, Drive, Docs, Tasks)
- Getting started guides (installation, authentication, quickstart)
- Claude Desktop integration guide
- CLI usage reference
- Development guides (contributing, testing, releasing)
- 93 tests (75 unit + 18 integration)
- GitHub Actions CI/CD pipeline
- PyPI publishing infrastructure with semantic versioning

## [0.1.0] - 2026-02-10

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
