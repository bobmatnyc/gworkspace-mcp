"""Command-line interface for google-workspace-mcp."""

import asyncio
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
    2. Store refresh tokens securely at ~/.gworkspace-mcp/tokens.json
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
        asyncio.run(manager.authenticate(client_id=client_id, client_secret=client_secret))
        click.echo("✓ Authentication successful!")
        click.echo(f"Token stored at: {manager.token_path}")
        click.echo("")
        click.echo("Run 'workspace doctor' to verify setup.")
    except Exception as e:
        click.echo(f"❌ Authentication failed: {e}")
        sys.exit(1)


@main.command()
def mcp() -> None:
    """Start the MCP server for Claude Desktop integration.

    Starts the stdio MCP server that provides 66 tools across:
    - Gmail (18 tools): Search, send, organize, labels
    - Calendar (10 tools): Events, calendars, availability
    - Drive (17 tools): Files, folders, sharing, search
    - Docs (11 tools): Create, edit, comment management
    - Tasks (10 tools): Task lists and task management

    Authentication is required before starting the server.
    Run 'workspace setup' if not already authenticated.

    This command is typically invoked by Claude Desktop via the MCP protocol.
    """
    from google_workspace_mcp.auth import OAuthManager, TokenStatus
    from google_workspace_mcp.server import main as server_main

    # Check authentication status
    manager = OAuthManager()
    status, _ = manager.get_status()

    if status == TokenStatus.MISSING:
        click.echo("❌ Not authenticated. Run 'workspace setup' first.")
        sys.exit(1)

    if status == TokenStatus.INVALID:
        click.echo("❌ Token file corrupted. Run 'workspace setup' to re-authenticate.")
        sys.exit(1)

    # Start the MCP server (runs indefinitely)
    try:
        click.echo("Starting Google Workspace MCP server...", err=True)
        click.echo("Server provides 66 tools for Claude Desktop", err=True)
        click.echo("", err=True)
        server_main()
    except KeyboardInterrupt:
        click.echo("\nServer stopped.", err=True)
    except Exception as e:
        click.echo(f"❌ Server error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--dry-run", is_flag=True, help="Show what would be migrated without making changes")
def migrate(dry_run: bool) -> None:
    """Run pending migrations.

    Migrations handle schema changes, directory renames, and configuration
    updates when upgrading between versions.

    Use --dry-run to preview what changes would be made without applying them.
    """
    from google_workspace_mcp.migrations import MigrationRunner

    runner = MigrationRunner()

    def progress(msg: str) -> None:
        click.echo(msg)

    runner.set_progress_callback(progress)

    pending = runner.get_pending_migrations()
    if not pending:
        click.echo("No pending migrations.")
        return

    click.echo(f"Found {len(pending)} pending migration(s):")
    for m in pending:
        click.echo(f"  - {m.id}: {m.description}")
    click.echo("")

    if dry_run:
        click.echo("Dry-run mode - showing what would happen:")
        click.echo("")

    applied = runner.run_all_pending(dry_run=dry_run)

    click.echo("")
    if dry_run:
        click.echo(f"Would apply {len(applied)} migration(s).")
    else:
        click.echo(f"Applied {len(applied)} migration(s).")


@main.command("migration-status")
def migration_status() -> None:
    """Show migration status.

    Displays the current schema version, applied migrations,
    and any pending migrations that need to be run.
    """
    from google_workspace_mcp.migrations import MigrationRunner

    runner = MigrationRunner()
    status = runner.get_status()

    click.echo("Migration Status:")
    click.echo(f"  Current version: {status['current_version']}")
    click.echo(f"  Total migrations: {status['total_migrations']}")
    click.echo(f"  Applied: {status['applied_count']}")
    click.echo(f"  Pending: {status['pending_count']}")
    click.echo("")

    if status["applied_migrations"]:
        click.echo("Applied migrations:")
        for m in status["applied_migrations"]:
            click.echo(f"  - {m['id']} (v{m['version']}) applied at {m['applied_at']}")
        click.echo("")

    if status["pending_migrations"]:
        click.echo("Pending migrations:")
        for m in status["pending_migrations"]:
            click.echo(f"  - {m['id']} (v{m['version']}): {m['description']}")
        click.echo("")
        click.echo("Run 'workspace migrate' to apply pending migrations.")
    else:
        click.echo("All migrations applied.")


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
            click.echo(
                f"  Token expires: {stored.token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            click.echo(f"  Scopes: {len(stored.token.scopes)} configured")

    click.echo("")

    if status in (TokenStatus.VALID, TokenStatus.EXPIRED):
        click.echo("✓ Ready to use!")
    else:
        click.echo("❌ Setup required. Run 'workspace setup' to authenticate.")


if __name__ == "__main__":
    main()
