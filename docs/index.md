# Google Workspace MCP Server Documentation

Welcome to the documentation for **gworkspace-mcp**, a Model Context Protocol (MCP) server that connects Claude to Google Workspace APIs.

## What is this?

This MCP server provides **66 tools** that enable Claude to interact with your Google Workspace services:

- **Gmail** - Search, send, organize emails
- **Calendar** - Manage events and calendars
- **Drive** - Search, upload, download files
- **Docs** - Create and edit documents
- **Tasks** - Manage task lists and tasks

## Quick Navigation

### Getting Started

New to gworkspace-mcp? Start here:

- [Installation](getting-started/installation.md) - Install the package
- [Authentication](getting-started/authentication.md) - Set up Google OAuth credentials
- [Quickstart](getting-started/quickstart.md) - Your first 5 minutes with the server

### User Guides

Detailed guides for specific use cases:

- [Claude Desktop Integration](guides/claude-desktop.md) - Connect to Claude Desktop
- [CLI Usage](guides/cli-usage.md) - Command-line reference

### API Reference

Complete tool documentation by service:

| Service | Tools | Documentation |
|---------|-------|---------------|
| Gmail | 18 | [Gmail API](api/gmail.md) |
| Calendar | 10 | [Calendar API](api/calendar.md) |
| Drive | 17 | [Drive API](api/drive.md) |
| Docs | 11 | [Docs API](api/docs.md) |
| Tasks | 10 | [Tasks API](api/tasks.md) |

### Development

For contributors and developers:

- [Contributing Guide](development/contributing.md) - How to contribute
- [Testing Guide](development/testing.md) - Running and writing tests
- [Release Process](development/releasing.md) - How releases work

### Other Resources

- [Research Notes](research/) - Background research and design decisions
- [Changelog](../CHANGELOG.md) - Version history

## Requirements

- **Python**: 3.10 or higher
- **Google Cloud Project**: With Workspace APIs enabled
- **OAuth 2.0 Credentials**: Desktop application type

### Optional Dependencies

| Tool | Purpose | Affected Features |
|------|---------|-------------------|
| [rclone](https://rclone.org/) | Drive sync | 4 tools: `list_drive_contents`, `download_drive_folder`, `upload_to_drive`, `sync_drive_folder` |
| [pandoc](https://pandoc.org/) | Document conversion | `upload_markdown_as_doc` |
| [@mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli) | Diagram rendering | `render_mermaid_to_doc` |

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/masapasa/gworkspace-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/masapasa/gworkspace-mcp/discussions)

## License

MIT License - See [LICENSE](../LICENSE) for details.
