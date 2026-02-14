"""YAML-based declarative migration system for gworkspace-mcp.

This module provides a migration system for handling schema changes,
directory renames, and configuration updates across versions.

Example usage:
    ```python
    from google_workspace_mcp.migrations import MigrationRunner

    # Run all pending migrations
    runner = MigrationRunner()
    applied = runner.run_all_pending()
    print(f"Applied {len(applied)} migrations")

    # Dry-run mode
    runner.run_all_pending(dry_run=True)
    ```
"""

from google_workspace_mcp.migrations.models import Migration, MigrationOperation, MigrationState
from google_workspace_mcp.migrations.runner import MigrationRunner

__all__ = [
    "Migration",
    "MigrationOperation",
    "MigrationRunner",
    "MigrationState",
]
