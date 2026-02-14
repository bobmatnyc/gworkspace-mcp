# Authentication

This guide explains how to set up Google OAuth 2.0 credentials for gworkspace-mcp.

## Overview

gworkspace-mcp uses OAuth 2.0 to securely access your Google Workspace data. The flow:

1. You create credentials in Google Cloud Console
2. Run `workspace setup` to authorize the app
3. Tokens are stored locally and refresh automatically

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** > **New Project**
3. Enter a project name (e.g., "Google Workspace MCP")
4. Click **Create**

## Step 2: Enable APIs

Enable each API your workflows need:

1. Go to **APIs & Services** > **Library**
2. Search for and enable each API:

| API | Required For |
|-----|--------------|
| Gmail API | Email operations |
| Google Calendar API | Calendar operations |
| Google Drive API | File operations |
| Google Docs API | Document operations |
| Google Tasks API | Task operations |

For each API:
- Click on the API name
- Click **Enable**

## Step 3: Configure OAuth Consent Screen

Before creating credentials, configure the consent screen:

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** (or Internal for Workspace accounts)
3. Click **Create**

Fill in the required fields:

| Field | Value |
|-------|-------|
| App name | Google Workspace MCP (or your choice) |
| User support email | Your email |
| Developer contact email | Your email |

4. Click **Save and Continue**

### Add Scopes

1. Click **Add or Remove Scopes**
2. Add these scopes:

```
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/documents
https://www.googleapis.com/auth/tasks
```

3. Click **Update** > **Save and Continue**

### Add Test Users (for External apps)

If you selected External:

1. Click **Add Users**
2. Add your Google account email
3. Click **Save and Continue**

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Select **Desktop app** as application type
4. Enter a name (e.g., "Workspace MCP Desktop")
5. Click **Create**

You'll see:
- **Client ID**: `xxxx.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-xxxxx`

**Important**: Save these values securely. You'll need them in the next step.

## Step 5: Authenticate with gworkspace-mcp

### Option A: Environment Variables (Recommended)

Set your credentials as environment variables:

```bash
export GOOGLE_OAUTH_CLIENT_ID='your-client-id.apps.googleusercontent.com'
export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'  # pragma: allowlist secret
```

Then run setup:

```bash
workspace setup
```

### Option B: Command-line Arguments

Pass credentials directly:

```bash
workspace setup \
  --client-id='your-client-id.apps.googleusercontent.com' \
  --client-secret='your-client-secret'  # pragma: allowlist secret
```

### The OAuth Flow

When you run `workspace setup`:

1. Your browser opens to Google's consent screen
2. Sign in with your Google account
3. Review the permissions and click **Allow**
4. The browser shows "Authentication successful"
5. Tokens are saved locally

## Step 6: Verify Authentication

Check that everything is working:

```bash
workspace doctor
```

Expected output:

```
Google Workspace MCP Doctor
===========================
[OK] Dependencies installed
[OK] Authenticated
    Token expires: 2026-02-15 10:30:00 UTC
    Scopes: 5 configured
```

## Token Storage

Tokens are stored at:

```
~/.gworkspace-mcp/tokens.json
```

**Security notes**:
- File permissions are set to `600` (owner read/write only)
- Contains refresh tokens - do not share this file
- Delete to revoke access: `rm ~/.gworkspace-mcp/tokens.json`

## Scopes Explained

| Scope | Permission | Tools |
|-------|------------|-------|
| `gmail.modify` | Read, send, organize email | All Gmail tools |
| `calendar` | Full calendar access | All Calendar tools |
| `drive` | Full Drive access | All Drive tools |
| `documents` | Read/write Google Docs | All Docs tools |
| `tasks` | Full Tasks access | All Tasks tools |

## Refreshing Tokens

Tokens refresh automatically when expired. If you encounter authentication errors:

```bash
# Delete existing tokens
rm ~/.gworkspace-mcp/tokens.json

# Re-authenticate
workspace setup
```

## Troubleshooting

### "Access blocked: This app's request is invalid"

Your OAuth consent screen may not be configured correctly:
- Ensure you added yourself as a test user (for External apps)
- Verify all required scopes are added

### "Error 400: redirect_uri_mismatch"

The callback URL doesn't match. Ensure:
- You created a **Desktop app** credential (not Web app)
- No custom redirect URIs are configured

### "Token refresh failed"

The refresh token may have expired. Re-authenticate:

```bash
rm ~/.gworkspace-mcp/tokens.json
workspace setup
```

### Tokens not persisting

Check file permissions:

```bash
ls -la ~/.gworkspace-mcp/
```

The directory should have `700` permissions:

```bash
chmod 700 ~/.gworkspace-mcp
chmod 600 ~/.gworkspace-mcp/tokens.json
```

## Security Best Practices

1. **Never commit credentials** - Add to `.gitignore`:
   ```
   .env
   .env.local
   *credentials*.json
   ```

2. **Use environment variables** - Don't hardcode credentials in scripts

3. **Limit scopes** - Only request scopes you need (all are required for full functionality)

4. **Revoke access if compromised**:
   - Delete local tokens: `rm ~/.gworkspace-mcp/tokens.json`
   - Revoke in Google: [myaccount.google.com/permissions](https://myaccount.google.com/permissions)

## Next Steps

With authentication complete:

1. [Quickstart guide](quickstart.md) - Test your first API calls
2. [Claude Desktop integration](../guides/claude-desktop.md) - Connect to Claude
