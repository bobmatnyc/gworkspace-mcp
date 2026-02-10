# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Token storage at `~/.google-workspace-mcp/tokens.json`

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

[Unreleased]: https://github.com/masapasa/google-workspace-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/masapasa/google-workspace-mcp/releases/tag/v0.1.0
