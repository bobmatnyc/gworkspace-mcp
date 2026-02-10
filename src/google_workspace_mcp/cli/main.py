"""Command-line interface for google-workspace-mcp."""

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
def setup() -> None:
    """Set up Google Workspace OAuth authentication.

    This command will be implemented in Phase 2.
    It will:
    1. Guide you through OAuth2 consent flow
    2. Store refresh tokens securely
    3. Validate API access
    """
    click.echo("OAuth setup will be implemented in Phase 2")
    click.echo("For now, please see documentation for manual setup")


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

    This command will be implemented in Phase 2.
    It will verify:
    1. Python dependencies installed
    2. OAuth credentials configured
    3. API access working
    4. MCP server connectivity
    """
    click.echo("Doctor command will be implemented in Phase 2")
    click.echo("")
    click.echo("Will check:")
    click.echo("  ✓ Python dependencies")
    click.echo("  ✓ OAuth credentials")
    click.echo("  ✓ API access")
    click.echo("  ✓ MCP server")


if __name__ == "__main__":
    main()
