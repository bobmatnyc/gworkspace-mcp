# CLI Usage

Complete reference for the `workspace` command-line interface.

## Overview

The `workspace` CLI provides commands for:
- Setting up OAuth authentication
- Checking system health
- Running the MCP server

## Commands

### workspace setup

Authenticate with Google and store OAuth tokens.

```bash
workspace setup [OPTIONS]
```

**Options**:

| Option | Description |
|--------|-------------|
| `--client-id TEXT` | Google OAuth Client ID |
| `--client-secret TEXT` | Google OAuth Client Secret |
| `--force` | Force re-authentication even if tokens exist |

**Environment Variables**:

| Variable | Description |
|----------|-------------|
| `GOOGLE_OAUTH_CLIENT_ID` | Client ID (alternative to --client-id) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Client Secret (alternative to --client-secret) |

**Examples**:

Using environment variables (recommended):
```bash
export GOOGLE_OAUTH_CLIENT_ID='your-client-id.apps.googleusercontent.com'
export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'  # pragma: allowlist secret
workspace setup
```

Using command-line options:
```bash
workspace setup \
  --client-id='your-client-id.apps.googleusercontent.com' \
  --client-secret='your-client-secret'  # pragma: allowlist secret
```

Force re-authentication:
```bash
workspace setup --force
```

**What happens**:
1. Opens your default browser to Google's consent screen
2. You sign in and authorize the application
3. Tokens are stored at `~/.gworkspace-mcp/tokens.json`
4. Confirmation message is displayed

### workspace doctor

Check system health and authentication status.

```bash
workspace doctor
```

**Output sections**:

1. **Dependencies**: Verifies required Python packages
2. **Authentication**: Checks token validity
3. **Token Details**: Shows expiration and scope count

**Example output**:

```
Google Workspace MCP Doctor
===========================

Checking dependencies...
  [OK] google-auth
  [OK] google-auth-oauthlib
  [OK] mcp
  [OK] httpx
  [OK] pydantic

Checking authentication...
  [OK] Authenticated
  Token expires: 2026-02-15 14:30:00 UTC
  Scopes: 5 configured

Optional dependencies:
  [OK] rclone (v1.65.0)
  [--] pandoc (not installed)
  [--] mermaid-cli (not installed)

All checks passed!
```

**Exit codes**:

| Code | Meaning |
|------|---------|
| 0 | All checks passed |
| 1 | One or more checks failed |

### workspace mcp

Start the MCP server for Claude Desktop integration.

```bash
workspace mcp [OPTIONS]
```

**Options**:

| Option | Description |
|--------|-------------|
| `--verbose` | Enable verbose logging |

**Environment Variables**:

| Variable | Description |
|----------|-------------|
| `GOOGLE_OAUTH_CLIENT_ID` | Client ID for authentication |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Client Secret for authentication |

**Example**:

```bash
workspace mcp
```

With verbose logging:
```bash
workspace mcp --verbose
```

**Notes**:
- The server runs on stdio (standard input/output)
- Designed for Claude Desktop integration
- Press `Ctrl+C` to stop the server

### workspace --version

Display version information.

```bash
workspace --version
```

**Example output**:

```
gworkspace-mcp version 0.1.0
```

### workspace --help

Display help information.

```bash
workspace --help
```

**Example output**:

```
Usage: workspace [OPTIONS] COMMAND [ARGS]...

  Google Workspace MCP Server CLI

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  doctor  Check authentication and dependencies
  mcp     Start the MCP server
  setup   Authenticate with Google OAuth
```

## Usage Patterns

### Initial Setup

First-time setup flow:

```bash
# 1. Set credentials
export GOOGLE_OAUTH_CLIENT_ID='your-client-id.apps.googleusercontent.com'
export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'  # pragma: allowlist secret

# 2. Authenticate
workspace setup

# 3. Verify
workspace doctor

# 4. Start server (or configure Claude Desktop)
workspace mcp
```

### Re-authentication

When tokens expire or become invalid:

```bash
# Check current status
workspace doctor

# Force new authentication
workspace setup --force
```

### Debugging

Check what's happening:

```bash
# Verbose mode shows detailed logs
workspace mcp --verbose
```

## Token Management

### Token Location

Tokens are stored at:

```
~/.gworkspace-mcp/tokens.json
```

### Viewing Token Status

```bash
workspace doctor
```

Shows:
- Whether tokens exist
- Expiration time
- Number of scopes

### Deleting Tokens

To revoke access or start fresh:

```bash
rm ~/.gworkspace-mcp/tokens.json
```

Then re-authenticate:

```bash
workspace setup
```

### Token Security

The token file has restricted permissions:
- Directory: `700` (owner only)
- File: `600` (owner read/write only)

Verify with:

```bash
ls -la ~/.gworkspace-mcp/
```

## Shell Integration

### Add to Shell Profile

For convenience, add credentials to your shell profile:

**Bash** (`~/.bashrc` or `~/.bash_profile`):
```bash
export GOOGLE_OAUTH_CLIENT_ID='your-client-id.apps.googleusercontent.com'
export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'  # pragma: allowlist secret
```

**Zsh** (`~/.zshrc`):
```bash
export GOOGLE_OAUTH_CLIENT_ID='your-client-id.apps.googleusercontent.com'
export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'  # pragma: allowlist secret
```

**Fish** (`~/.config/fish/config.fish`):
```fish
set -x GOOGLE_OAUTH_CLIENT_ID 'your-client-id.apps.googleusercontent.com'
set -x GOOGLE_OAUTH_CLIENT_SECRET 'your-client-secret'  # pragma: allowlist secret
```

### Alias Examples

Create shortcuts:

```bash
# Quick doctor check
alias gw-doctor='workspace doctor'

# Start server with verbose logging
alias gw-server='workspace mcp --verbose'
```

## Troubleshooting

### Command Not Found

If `workspace` isn't recognized:

1. Check installation:
   ```bash
   pip show gworkspace-mcp
   ```

2. Find the executable:
   ```bash
   python -c "import google_workspace_mcp; print(google_workspace_mcp.__file__)"
   ```

3. Add to PATH or use full path:
   ```bash
   ~/.local/bin/workspace doctor
   ```

### Permission Denied

If you get permission errors:

```bash
# Fix token directory permissions
chmod 700 ~/.gworkspace-mcp
chmod 600 ~/.gworkspace-mcp/tokens.json
```

### Authentication Loops

If `workspace setup` keeps asking for auth:

1. Delete existing tokens:
   ```bash
   rm -rf ~/.gworkspace-mcp/
   ```

2. Re-run setup:
   ```bash
   workspace setup
   ```

### Python Environment Issues

If you have multiple Python versions:

```bash
# Use specific Python version
python3.10 -m google_workspace_mcp.cli.main doctor

# Or use pipx
pipx run gworkspace-mcp doctor
```

## Related Documentation

- [Installation](../getting-started/installation.md)
- [Authentication](../getting-started/authentication.md)
- [Claude Desktop Integration](claude-desktop.md)
