"""Command-line interface for google-workspace-mcp."""

import asyncio
import os
import sys

import click

from google_workspace_mcp.__version__ import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Google Workspace MCP Server - Connect Claude to Google Workspace APIs.

    This tool provides 66 tools across:
    - Gmail (search, read, send, organize)
    - Calendar (events, availability)
    - Drive (files, folders, search)
    - Docs (read, create, edit)
    - Tasks (lists, tasks, management)
    """
    pass


@main.command()
@click.option("--client-id", envvar="GOOGLE_OAUTH_CLIENT_ID", help="Google OAuth client ID")
@click.option(
    "--client-secret", envvar="GOOGLE_OAUTH_CLIENT_SECRET", help="Google OAuth client secret"
)
def setup(client_id: str | None, client_secret: str | None) -> None:
    """Set up Google Workspace OAuth authentication.

    This will:
    1. Open browser for OAuth2 consent flow
    2. Store refresh tokens securely at ~/.google-workspace-mcp/tokens.json
    3. Validate API access

    Requires:
    - GOOGLE_OAUTH_CLIENT_ID environment variable or --client-id option
    - GOOGLE_OAUTH_CLIENT_SECRET environment variable or --client-secret option
    """
    from google_workspace_mcp.auth import OAuthManager

    manager = OAuthManager()

    # Check if already authenticated
    if manager.has_valid_tokens():
        click.echo("✓ Already authenticated!")
        click.echo(f"Token stored at: {manager.token_path}")
        click.echo("")

        if not click.confirm("Re-authenticate?"):
            return

    # Validate credentials
    if not client_id or not client_secret:
        click.echo("❌ Error: OAuth client credentials required")
        click.echo("")
        click.echo("Set environment variables:")
        click.echo("  export GOOGLE_OAUTH_CLIENT_ID='your-client-id'")
        click.echo("  export GOOGLE_OAUTH_CLIENT_SECRET='your-client-secret'")
        click.echo("")
        click.echo("Or pass as options:")
        click.echo("  workspace setup --client-id=... --client-secret=...")
        sys.exit(1)

    # Run authentication
    click.echo("Starting OAuth authentication flow...")
    click.echo("Browser will open for Google consent...")
    click.echo("")

    try:
        asyncio.run(
            manager.authenticate(client_id=client_id, client_secret=client_secret)
        )
        click.echo("✓ Authentication successful!")
        click.echo(f"Token stored at: {manager.token_path}")
        click.echo("")
        click.echo("Run 'workspace doctor' to verify setup.")
    except Exception as e:
        click.echo(f"❌ Authentication failed: {e}")
        sys.exit(1)


@main.command()
def mcp() -> None:
    """Start the MCP server.

    This command will be implemented in Phase 3.
    It will start the stdio MCP server that Claude can connect to.
    """
    click.echo("MCP server will be implemented in Phase 3")
    click.echo("Server will provide 66 tools across Gmail, Calendar, Drive, Docs, and Tasks")


@main.command()
def doctor() -> None:
    """Check installation and authentication status.

    Verifies:
    1. Python dependencies installed
    2. OAuth credentials configured
    3. Token validity
    """
    from google_workspace_mcp.auth import OAuthManager, TokenStatus

    click.echo("Google Workspace MCP Status:")
    click.echo("")

    # Check dependencies
    click.echo("Dependencies:")
    try:
        import google.auth  # noqa: F401
        import google_auth_oauthlib  # noqa: F401

        click.echo("  ✓ google-auth installed")
        click.echo("  ✓ google-auth-oauthlib installed")
    except ImportError as e:
        click.echo(f"  ❌ Missing dependency: {e}")
        sys.exit(1)

    click.echo("")

    # Check authentication
    manager = OAuthManager()
    status, stored = manager.get_status()

    click.echo("Authentication:")
    click.echo(f"  Token file: {manager.token_path}")

    if status == TokenStatus.MISSING:
        click.echo("  ❌ Not authenticated")
        click.echo("")
        click.echo("Run 'workspace setup' to authenticate.")
        sys.exit(1)
    elif status == TokenStatus.INVALID:
        click.echo("  ❌ Token file corrupted")
        click.echo("")
        click.echo("Run 'workspace setup' to re-authenticate.")
        sys.exit(1)
    elif status == TokenStatus.EXPIRED:
        click.echo("  ⚠️  Token expired (can be refreshed)")
        click.echo("")
        click.echo("Run 'workspace setup' or token will refresh automatically on use.")
    elif status == TokenStatus.VALID:
        click.echo("  ✓ Authenticated")
        if stored:
            click.echo(f"  Token expires: {stored.token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            click.echo(f"  Scopes: {len(stored.token.scopes)} configured")

    click.echo("")

    if status in (TokenStatus.VALID, TokenStatus.EXPIRED):
        click.echo("✓ Ready to use!")
    else:
        click.echo("❌ Setup required. Run 'workspace setup' to authenticate.")


if __name__ == "__main__":
    main()
