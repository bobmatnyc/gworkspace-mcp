"""Migration runner for executing YAML-based migrations.

This module provides the MigrationRunner class which loads migration
definitions from YAML files and executes them in order, tracking state
to prevent re-running already applied migrations.
"""

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from gworkspace_mcp.migrations.models import (
    AppliedMigration,
    Migration,
    MigrationOperation,
    MigrationState,
)
from gworkspace_mcp.migrations.operations import OperationResult, execute_operation

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Runner for YAML-based declarative migrations.

    Loads migration definitions from YAML files, tracks applied migrations
    in a state file, and executes pending migrations in order.

    Attributes:
        migrations_dir: Directory containing migration YAML files.
        state_file: Path to the migration state JSON file.

    Example:
        ```python
        runner = MigrationRunner()

        # Check pending migrations
        pending = runner.get_pending_migrations()
        print(f"{len(pending)} migrations pending")

        # Run all pending (dry-run first)
        runner.run_all_pending(dry_run=True)

        # Actually run them
        applied = runner.run_all_pending()
        ```
    """

    def __init__(
        self,
        migrations_dir: Path | None = None,
        state_file: Path | None = None,
    ) -> None:
        """Initialize migration runner.

        Args:
            migrations_dir: Directory containing migration YAML files.
                Defaults to the package's migrations/ directory.
            state_file: Path to store migration state.
                Defaults to ~/.gworkspace-mcp/.migration_state.json
        """
        self.migrations_dir = migrations_dir or Path(__file__).parent
        self.state_file = state_file or (Path.home() / ".gworkspace-mcp" / ".migration_state.json")
        self._on_progress: Callable[[str], None] | None = None

    def set_progress_callback(self, callback: Callable[[str], None] | None) -> None:
        """Set a callback for progress updates.

        Args:
            callback: Function to call with progress messages.
        """
        self._on_progress = callback

    def _log(self, message: str) -> None:
        """Log a message and call progress callback if set."""
        logger.info(message)
        if self._on_progress:
            self._on_progress(message)

    def load_migrations(self) -> list[Migration]:
        """Load all migration YAML files from the migrations directory.

        Returns:
            List of Migration objects, sorted by ID.
        """
        migrations: list[Migration] = []

        # Find all YAML files matching migration pattern
        for yaml_file in self.migrations_dir.glob("*.yaml"):
            # Skip non-migration files
            if not yaml_file.stem[0].isdigit():
                continue

            try:
                content = yaml_file.read_text()
                data = yaml.safe_load(content)
                if data:
                    # Parse operations
                    ops_data = data.pop("operations", [])
                    operations = [MigrationOperation.model_validate(op) for op in ops_data]
                    data["operations"] = operations
                    migrations.append(Migration.model_validate(data))
            except (yaml.YAMLError, ValueError) as e:
                logger.warning(f"Failed to load migration {yaml_file}: {e}")
                continue

        # Sort by ID (which should have numeric prefix)
        return sorted(migrations, key=lambda m: m.id)

    def _load_state(self) -> MigrationState:
        """Load migration state from state file.

        Returns:
            Current migration state.
        """
        if not self.state_file.exists():
            return MigrationState()

        try:
            content = self.state_file.read_text()
            data = json.loads(content)
            return MigrationState.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to load migration state: {e}")
            return MigrationState()

    def _save_state(self, state: MigrationState) -> None:
        """Save migration state to state file.

        Args:
            state: Migration state to save.
        """
        # Ensure parent directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        content = state.model_dump_json(indent=2)
        self.state_file.write_text(content)

    def get_applied_migrations(self) -> list[str]:
        """Get list of applied migration IDs.

        Returns:
            List of migration IDs that have been applied.
        """
        state = self._load_state()
        return [m.id for m in state.applied_migrations]

    def get_pending_migrations(self) -> list[Migration]:
        """Get list of migrations that haven't been applied.

        Returns:
            List of pending Migration objects, in order.
        """
        all_migrations = self.load_migrations()
        applied_ids = set(self.get_applied_migrations())

        return [m for m in all_migrations if m.id not in applied_ids]

    def run_migration(
        self,
        migration: Migration,
        dry_run: bool = False,
    ) -> tuple[bool, list[OperationResult]]:
        """Execute a single migration.

        Args:
            migration: The migration to execute.
            dry_run: If True, only simulate operations.

        Returns:
            Tuple of (success, list of operation results).
        """
        self._log(f"{'[DRY-RUN] ' if dry_run else ''}Running migration: {migration.id}")
        self._log(f"  Description: {migration.description}")

        results: list[OperationResult] = []
        all_success = True

        for i, op in enumerate(migration.operations, 1):
            self._log(f"  Operation {i}/{len(migration.operations)}: {op.type.value}")

            result = execute_operation(op, dry_run)
            results.append(result)

            if result.success:
                status = "[SKIPPED]" if result.skipped else "[OK]"
                self._log(f"    {status} {result.message}")
            else:
                self._log(f"    [FAILED] {result.message}")
                all_success = False
                break  # Stop on first failure

        if all_success and not dry_run:
            # Record the migration as applied
            state = self._load_state()
            state.applied_migrations.append(
                AppliedMigration(
                    id=migration.id,
                    applied_at=datetime.now(timezone.utc),
                    version=migration.version,
                )
            )
            state.current_version = migration.version
            self._save_state(state)
            self._log(f"  Migration {migration.id} applied successfully")

        return all_success, results

    def run_all_pending(self, dry_run: bool = False) -> list[str]:
        """Run all pending migrations in order.

        Args:
            dry_run: If True, only simulate operations.

        Returns:
            List of migration IDs that were applied (or would be in dry-run).
        """
        pending = self.get_pending_migrations()

        if not pending:
            self._log("No pending migrations")
            return []

        self._log(f"{'[DRY-RUN] ' if dry_run else ''}Found {len(pending)} pending migration(s)")

        applied: list[str] = []
        for migration in pending:
            success, _ = self.run_migration(migration, dry_run)
            if success:
                applied.append(migration.id)
            else:
                self._log(f"Migration {migration.id} failed, stopping")
                break

        return applied

    def get_status(self) -> dict[str, Any]:
        """Get current migration status.

        Returns:
            Dictionary with status information.
        """
        state = self._load_state()
        all_migrations = self.load_migrations()
        pending = self.get_pending_migrations()

        return {
            "current_version": state.current_version,
            "total_migrations": len(all_migrations),
            "applied_count": len(state.applied_migrations),
            "pending_count": len(pending),
            "applied_migrations": [
                {
                    "id": m.id,
                    "version": m.version,
                    "applied_at": m.applied_at.isoformat(),
                }
                for m in state.applied_migrations
            ],
            "pending_migrations": [
                {
                    "id": m.id,
                    "version": m.version,
                    "description": m.description,
                }
                for m in pending
            ],
        }
