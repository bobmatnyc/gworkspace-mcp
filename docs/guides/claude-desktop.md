# Claude Desktop Integration

This guide covers connecting gworkspace-mcp to Claude Desktop for seamless Google Workspace access.

## Overview

Claude Desktop supports the Model Context Protocol (MCP), which allows Claude to use external tools. gworkspace-mcp provides 66 tools for interacting with Google Workspace APIs.

## Configuration

### Configuration File Location

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### Basic Configuration

Add gworkspace-mcp to your config:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "workspace",
      "args": ["mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"  // pragma: allowlist secret
      }
    }
  }
}
```

### Configuration with Full Path

If `workspace` isn't in your PATH, use the full path:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "/usr/local/bin/workspace",
      "args": ["mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"  // pragma: allowlist secret
      }
    }
  }
}
```

Find your path with:

```bash
which workspace
```

### Configuration with Python Module

Alternative using Python module:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "python",
      "args": ["-m", "google_workspace_mcp.cli.main", "mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"  // pragma: allowlist secret
      }
    }
  }
}
```

### Configuration with uv

Using [uv](https://github.com/astral-sh/uv) for isolation:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["gworkspace-mcp", "mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"  // pragma: allowlist secret
      }
    }
  }
}
```

## Verifying Connection

After configuring:

1. **Restart Claude Desktop** - Quit completely and reopen
2. **Start a new conversation**
3. **Test with a simple prompt**:
   > "List my Gmail labels"

If tools are available, Claude will use `list_gmail_labels` to respond.

## Available Tools

Once connected, Claude has access to 66 tools:

| Category | Tools | Examples |
|----------|-------|----------|
| Gmail | 18 | Search emails, send messages, manage labels |
| Calendar | 10 | List events, create meetings, manage calendars |
| Drive | 17 | Search files, upload documents, sync folders |
| Docs | 11 | Create documents, add comments, manage tabs |
| Tasks | 10 | Create tasks, manage lists, set due dates |

See the [API Reference](../api/) for complete tool documentation.

## Usage Tips

### Be Specific

Good prompts help Claude choose the right tool:

| Vague | Specific |
|-------|----------|
| "Check my email" | "Search Gmail for unread emails from today" |
| "Make a meeting" | "Create a calendar event called 'Team Sync' tomorrow at 2pm for 1 hour" |
| "Find my files" | "Search Drive for PDF files containing 'Q4 report'" |

### Use Natural Language

Claude understands context. You can say:

> "Send an email to john@example.com thanking him for the meeting yesterday"

Claude will:
1. Use `send_email`
2. Compose appropriate content
3. Format the message properly

### Chain Operations

Claude can combine multiple tools:

> "Find all emails from sarah@example.com about the budget, summarize them, and create a task to follow up by Friday"

This might use:
1. `search_gmail_messages` - Find emails
2. Read and summarize (Claude's capability)
3. `create_task` - Create follow-up task

### Batch Operations

For efficiency, ask for batch operations:

> "Archive all promotional emails from the last month"

Claude can use `batch_archive_gmail_messages` instead of archiving one at a time.

## Troubleshooting

### Tools Not Appearing

**Check the config file syntax**:
```bash
# Validate JSON
python -c "import json; json.load(open('path/to/claude_desktop_config.json'))"
```

**Verify credentials are set**:
- `GOOGLE_OAUTH_CLIENT_ID` should end with `.apps.googleusercontent.com`
- `GOOGLE_OAUTH_CLIENT_SECRET` should start with `GOCSPX-`

**Check server starts**:
```bash
workspace mcp
# Should start without errors
# Press Ctrl+C to stop
```

### Authentication Errors

If you see "Not authenticated":

1. Run authentication:
   ```bash
   workspace setup
   ```

2. Verify tokens exist:
   ```bash
   ls -la ~/.google-workspace-mcp/tokens.json
   ```

3. Restart Claude Desktop

### Server Crashes

Check for Python version issues:

```bash
python --version  # Should be 3.10+
```

Check logs (if available):
- macOS: `~/Library/Logs/Claude/`
- Linux: `~/.local/share/Claude/logs/`

### Rate Limiting

Google APIs have quotas. If operations fail:

- Wait a few minutes
- Reduce batch sizes
- Check [Google Cloud Console](https://console.cloud.google.com/) for quota usage

## Security Considerations

### Credential Storage

Credentials in `claude_desktop_config.json`:
- Are stored in plain text
- Should not be committed to version control

Consider:
- Using environment variables in shell profile instead
- Restricting file permissions:
  ```bash
  chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json
  ```

### Token Security

OAuth tokens in `~/.google-workspace-mcp/tokens.json`:
- Allow access to your Google Workspace
- Should be kept secure
- Can be revoked by deleting the file

### Access Scope

The server requests broad access (calendar, gmail.modify, drive, documents, tasks). This allows:
- Reading and modifying emails
- Full calendar access
- Full Drive access
- Creating and editing documents
- Managing all tasks

Only grant access if you trust the use case.

## Advanced Configuration

### Multiple Google Accounts

Run multiple instances with different token directories:

```json
{
  "mcpServers": {
    "google-workspace-personal": {
      "command": "workspace",
      "args": ["mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "personal-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "personal-secret",  // pragma: allowlist secret
        "GOOGLE_WORKSPACE_MCP_TOKEN_DIR": "~/.google-workspace-mcp/personal"
      }
    },
    "google-workspace-work": {
      "command": "workspace",
      "args": ["mcp"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "work-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "work-secret",  // pragma: allowlist secret
        "GOOGLE_WORKSPACE_MCP_TOKEN_DIR": "~/.google-workspace-mcp/work"
      }
    }
  }
}
```

### Debug Logging

Enable verbose logging:

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "workspace",
      "args": ["mcp", "--verbose"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-secret"  // pragma: allowlist secret
      }
    }
  }
}
```

## Related Documentation

- [Authentication Guide](../getting-started/authentication.md)
- [CLI Usage](cli-usage.md)
- [API Reference](../api/)
