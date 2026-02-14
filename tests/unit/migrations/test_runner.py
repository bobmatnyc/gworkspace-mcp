"""Tests for migration runner."""

import json
from pathlib import Path

import pytest

from google_workspace_mcp.migrations.models import Migration, MigrationOperation, OperationType
from google_workspace_mcp.migrations.runner import MigrationRunner


@pytest.fixture
def migrations_dir(tmp_path: Path) -> Path:
    """Create a temporary migrations directory."""
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    return migrations


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    """Create a temporary state file path."""
    state_dir = tmp_path / ".gworkspace-mcp"
    state_dir.mkdir()
    return state_dir / ".migration_state.json"


@pytest.fixture
def runner(migrations_dir: Path, state_file: Path) -> MigrationRunner:
    """Create a MigrationRunner with temporary directories."""
    return MigrationRunner(migrations_dir=migrations_dir, state_file=state_file)


class TestMigrationRunner:
    """Tests for MigrationRunner class."""

    def test_load_migrations_empty(self, runner: MigrationRunner):
        """Should return empty list when no migrations exist."""
        migrations = runner.load_migrations()
        assert migrations == []

    def test_load_migrations_from_yaml(self, runner: MigrationRunner, migrations_dir: Path):
        """Should load migrations from YAML files."""
        migration_yaml = migrations_dir / "0001_test.yaml"
        migration_yaml.write_text(
            """
id: "0001_test"
version: "0.2.0"
from_version: "0.1.x"
description: "Test migration"
operations:
  - type: add_field
    file: "~/.test/config.json"
    key: "version"
    value: "0.2.0"
"""
        )

        migrations = runner.load_migrations()

        assert len(migrations) == 1
        assert migrations[0].id == "0001_test"
        assert migrations[0].version == "0.2.0"
        assert len(migrations[0].operations) == 1

    def test_load_migrations_sorted_by_id(self, runner: MigrationRunner, migrations_dir: Path):
        """Should sort migrations by ID."""
        (migrations_dir / "0003_third.yaml").write_text(
            """
id: "0003_third"
version: "0.4.0"
from_version: "0.3.x"
description: "Third"
operations: []
"""
        )
        (migrations_dir / "0001_first.yaml").write_text(
            """
id: "0001_first"
version: "0.2.0"
from_version: "0.1.x"
description: "First"
operations: []
"""
        )
        (migrations_dir / "0002_second.yaml").write_text(
            """
id: "0002_second"
version: "0.3.0"
from_version: "0.2.x"
description: "Second"
operations: []
"""
        )

        migrations = runner.load_migrations()

        assert len(migrations) == 3
        assert migrations[0].id == "0001_first"
        assert migrations[1].id == "0002_second"
        assert migrations[2].id == "0003_third"

    def test_load_migrations_skips_invalid_yaml(
        self, runner: MigrationRunner, migrations_dir: Path
    ):
        """Should skip invalid YAML files."""
        (migrations_dir / "0001_valid.yaml").write_text(
            """
id: "0001_valid"
version: "0.2.0"
from_version: "0.1.x"
description: "Valid"
operations: []
"""
        )
        (migrations_dir / "0002_invalid.yaml").write_text("invalid: yaml: content:")

        migrations = runner.load_migrations()

        # Should only load the valid one
        assert len(migrations) == 1
        assert migrations[0].id == "0001_valid"

    def test_load_migrations_skips_non_migration_files(
        self, runner: MigrationRunner, migrations_dir: Path
    ):
        """Should skip files that don't start with a digit."""
        (migrations_dir / "0001_valid.yaml").write_text(
            """
id: "0001_valid"
version: "0.2.0"
from_version: "0.1.x"
description: "Valid"
operations: []
"""
        )
        (migrations_dir / "readme.yaml").write_text("not a migration")

        migrations = runner.load_migrations()

        assert len(migrations) == 1
        assert migrations[0].id == "0001_valid"

    def test_get_applied_migrations_empty(self, runner: MigrationRunner):
        """Should return empty list when no migrations applied."""
        applied = runner.get_applied_migrations()
        assert applied == []

    def test_get_applied_migrations_from_state(self, runner: MigrationRunner, state_file: Path):
        """Should load applied migrations from state file."""
        state_file.write_text(
            json.dumps(
                {
                    "applied_migrations": [
                        {
                            "id": "0001_test",
                            "version": "0.2.0",
                            "applied_at": "2026-02-13T15:30:00Z",
                        }
                    ],
                    "current_version": "0.2.0",
                }
            )
        )

        applied = runner.get_applied_migrations()

        assert applied == ["0001_test"]

    def test_get_pending_migrations(
        self, runner: MigrationRunner, migrations_dir: Path, state_file: Path
    ):
        """Should return migrations that haven't been applied."""
        (migrations_dir / "0001_first.yaml").write_text(
            """
id: "0001_first"
version: "0.2.0"
from_version: "0.1.x"
description: "First"
operations: []
"""
        )
        (migrations_dir / "0002_second.yaml").write_text(
            """
id: "0002_second"
version: "0.3.0"
from_version: "0.2.x"
description: "Second"
operations: []
"""
        )
        state_file.write_text(
            json.dumps(
                {
                    "applied_migrations": [
                        {
                            "id": "0001_first",
                            "version": "0.2.0",
                            "applied_at": "2026-02-13T15:30:00Z",
                        }
                    ],
                    "current_version": "0.2.0",
                }
            )
        )

        pending = runner.get_pending_migrations()

        assert len(pending) == 1
        assert pending[0].id == "0002_second"

    def test_run_migration_success(self, runner: MigrationRunner, tmp_path: Path, state_file: Path):
        """Should run migration and update state."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        migration = Migration(
            id="0001_test",
            version="0.2.0",
            from_version="0.1.x",
            description="Test",
            operations=[
                MigrationOperation(
                    type=OperationType.ADD_FIELD,
                    file=str(config_file),
                    key="version",
                    value="0.2.0",
                )
            ],
        )

        success, results = runner.run_migration(migration)

        assert success
        assert len(results) == 1
        assert results[0].success

        # Check state was updated
        state = json.loads(state_file.read_text())
        assert state["current_version"] == "0.2.0"
        assert len(state["applied_migrations"]) == 1
        assert state["applied_migrations"][0]["id"] == "0001_test"

    def test_run_migration_dry_run(self, runner: MigrationRunner, tmp_path: Path, state_file: Path):
        """Should not modify files or state in dry-run mode."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        migration = Migration(
            id="0001_test",
            version="0.2.0",
            from_version="0.1.x",
            description="Test",
            operations=[
                MigrationOperation(
                    type=OperationType.ADD_FIELD,
                    file=str(config_file),
                    key="version",
                    value="0.2.0",
                )
            ],
        )

        success, results = runner.run_migration(migration, dry_run=True)

        assert success
        # File should not be modified
        assert config_file.read_text() == "{}"
        # State should not exist
        assert not state_file.exists()

    def test_run_migration_failure_stops_execution(self, runner: MigrationRunner, tmp_path: Path):
        """Should stop on first failed operation."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"version": "0.1.0"}')

        migration = Migration(
            id="0001_test",
            version="0.2.0",
            from_version="0.1.x",
            description="Test",
            operations=[
                # This will fail - key already exists
                MigrationOperation(
                    type=OperationType.ADD_FIELD,
                    file=str(config_file),
                    key="version",
                    value="0.2.0",
                ),
                # This should not run
                MigrationOperation(
                    type=OperationType.ADD_FIELD,
                    file=str(config_file),
                    key="other",
                    value="data",
                ),
            ],
        )

        success, results = runner.run_migration(migration)

        assert not success
        assert len(results) == 1  # Second operation not executed
        # File should not have "other" key
        data = json.loads(config_file.read_text())
        assert "other" not in data

    def test_run_all_pending(self, runner: MigrationRunner, migrations_dir: Path, tmp_path: Path):
        """Should run all pending migrations in order."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        (migrations_dir / "0001_first.yaml").write_text(
            f"""
id: "0001_first"
version: "0.2.0"
from_version: "0.1.x"
description: "First"
operations:
  - type: add_field
    file: "{config_file}"
    key: "version"
    value: "0.2.0"
"""
        )
        (migrations_dir / "0002_second.yaml").write_text(
            f"""
id: "0002_second"
version: "0.3.0"
from_version: "0.2.x"
description: "Second"
operations:
  - type: add_field
    file: "{config_file}"
    key: "schema"
    value: "v2"
"""
        )

        applied = runner.run_all_pending()

        assert applied == ["0001_first", "0002_second"]
        data = json.loads(config_file.read_text())
        assert data["version"] == "0.2.0"
        assert data["schema"] == "v2"

    def test_run_all_pending_stops_on_failure(
        self, runner: MigrationRunner, migrations_dir: Path, tmp_path: Path
    ):
        """Should stop running when a migration fails."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"version": "0.1.0"}')

        (migrations_dir / "0001_first.yaml").write_text(
            f"""
id: "0001_first"
version: "0.2.0"
from_version: "0.1.x"
description: "First - will fail"
operations:
  - type: add_field
    file: "{config_file}"
    key: "version"
    value: "0.2.0"
"""
        )
        (migrations_dir / "0002_second.yaml").write_text(
            f"""
id: "0002_second"
version: "0.3.0"
from_version: "0.2.x"
description: "Second - should not run"
operations:
  - type: add_field
    file: "{config_file}"
    key: "schema"
    value: "v2"
"""
        )

        applied = runner.run_all_pending()

        # First migration fails, second should not run
        assert applied == []

    def test_get_status(self, runner: MigrationRunner, migrations_dir: Path, state_file: Path):
        """Should return comprehensive status."""
        (migrations_dir / "0001_first.yaml").write_text(
            """
id: "0001_first"
version: "0.2.0"
from_version: "0.1.x"
description: "First"
operations: []
"""
        )
        (migrations_dir / "0002_second.yaml").write_text(
            """
id: "0002_second"
version: "0.3.0"
from_version: "0.2.x"
description: "Second"
operations: []
"""
        )
        state_file.write_text(
            json.dumps(
                {
                    "applied_migrations": [
                        {
                            "id": "0001_first",
                            "version": "0.2.0",
                            "applied_at": "2026-02-13T15:30:00Z",
                        }
                    ],
                    "current_version": "0.2.0",
                }
            )
        )

        status = runner.get_status()

        assert status["current_version"] == "0.2.0"
        assert status["total_migrations"] == 2
        assert status["applied_count"] == 1
        assert status["pending_count"] == 1
        assert len(status["applied_migrations"]) == 1
        assert len(status["pending_migrations"]) == 1
        assert status["pending_migrations"][0]["id"] == "0002_second"

    def test_progress_callback(self, runner: MigrationRunner, migrations_dir: Path, tmp_path: Path):
        """Should call progress callback during execution."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        (migrations_dir / "0001_test.yaml").write_text(
            f"""
id: "0001_test"
version: "0.2.0"
from_version: "0.1.x"
description: "Test migration"
operations:
  - type: add_field
    file: "{config_file}"
    key: "version"
    value: "0.2.0"
"""
        )

        messages: list[str] = []
        runner.set_progress_callback(lambda msg: messages.append(msg))

        runner.run_all_pending()

        assert len(messages) > 0
        assert any("0001_test" in msg for msg in messages)
        assert any("Test migration" in msg for msg in messages)
