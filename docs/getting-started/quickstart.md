# Quickstart

Get started with gworkspace-mcp in 5 minutes.

## Prerequisites

Before starting, ensure you have:

1. [Installed the package](installation.md)
2. [Set up authentication](authentication.md)

Verify with:

```bash
workspace doctor
```

## Starting the MCP Server

Start the server:

```bash
workspace mcp
```

The server runs on stdio and waits for MCP protocol messages. You'll typically connect this to Claude Desktop rather than interact directly.

**Note**: Press `Ctrl+C` to stop the server.

## Connect to Claude Desktop

### 1. Find the Configuration File

Locate your Claude Desktop config file:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### 2. Add the Server Configuration

Add gworkspace-mcp to the config file:

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

### 3. Restart Claude Desktop

Quit and reopen Claude Desktop. The google-workspace tools should now be available.

## Example Conversations

Once connected, try these example prompts with Claude:

### Gmail

**Search for emails**:
> "Search my Gmail for emails from john@example.com in the last week"

**Send an email**:
> "Send an email to team@example.com with subject 'Meeting Notes' and body with today's discussion points"

**Organize inbox**:
> "Archive all emails older than 30 days that are marked as read"

### Calendar

**View schedule**:
> "Show me my calendar events for this week"

**Create an event**:
> "Create a meeting called 'Team Standup' tomorrow at 10am for 30 minutes"

**Find free time**:
> "When am I free this Friday afternoon?"

### Drive

**Search files**:
> "Find all PDF files in my Drive containing 'quarterly report'"

**Create folder structure**:
> "Create a folder called 'Projects' with subfolders for 'Active' and 'Archive'"

**Upload content**:
> "Upload my meeting notes to Drive in the Projects/Active folder"

### Docs

**Create a document**:
> "Create a Google Doc called 'Project Proposal' with an outline for our new feature"

**Add content**:
> "Append today's meeting notes to the document with ID xyz123"

**Add diagrams**:
> "Create a Mermaid flowchart showing our deployment process and add it to my architecture doc"

### Tasks

**View tasks**:
> "Show me all my incomplete tasks"

**Create tasks**:
> "Add a task 'Review PR #123' due this Friday to my work task list"

**Complete tasks**:
> "Mark the task 'Send weekly report' as complete"

## Testing Individual Tools

You can test tools directly using the MCP Inspector. Install it:

```bash
npx @modelcontextprotocol/inspector workspace mcp
```

This opens a web UI where you can:
- See all available tools
- Test tools with sample inputs
- View responses

## Common Workflows

### Daily Email Triage

```
1. "Show me unread emails from today"
2. "Mark these as read: [message IDs]"
3. "Archive all newsletters from today"
```

### Meeting Preparation

```
1. "What meetings do I have tomorrow?"
2. "Search my Drive for files related to [meeting topic]"
3. "Create a notes document for tomorrow's 10am meeting"
```

### Task Management

```
1. "Show me all tasks due this week"
2. "Move the overdue tasks to next week"
3. "Complete all tasks tagged 'daily'"
```

## Troubleshooting

### "Not authenticated" error

Run the setup command again:

```bash
workspace setup
```

### "Tool not found"

Restart Claude Desktop after config changes.

### API rate limits

Google APIs have quotas. If you hit limits:
- Wait a few minutes before retrying
- Reduce batch sizes for bulk operations

## Next Steps

- [Claude Desktop Guide](../guides/claude-desktop.md) - Advanced configuration
- [CLI Reference](../guides/cli-usage.md) - All CLI commands
- [Gmail Tools](../api/gmail.md) - Detailed Gmail API reference
- [Calendar Tools](../api/calendar.md) - Detailed Calendar API reference
- [Drive Tools](../api/drive.md) - Detailed Drive API reference
- [Docs Tools](../api/docs.md) - Detailed Docs API reference
- [Tasks Tools](../api/tasks.md) - Detailed Tasks API reference
