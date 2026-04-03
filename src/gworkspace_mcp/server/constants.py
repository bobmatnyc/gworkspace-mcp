"""Constants for the Google Workspace MCP server."""

# Service name for token storage - matches gworkspace-mcp convention
SERVICE_NAME = "gworkspace-mcp"

# Google API base URLs
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DOCS_API_BASE = "https://docs.googleapis.com/v1"
TASKS_API_BASE = "https://tasks.googleapis.com/tasks/v1"
SHEETS_API_BASE = "https://sheets.googleapis.com/v4"
SLIDES_API_BASE = "https://slides.googleapis.com/v1"

# Mermaid rendering constants (single source of truth)
MERMAID_CLI_VERSION = "@mermaid-js/mermaid-cli@11.12.0"
MERMAID_TIMEOUT = 30
