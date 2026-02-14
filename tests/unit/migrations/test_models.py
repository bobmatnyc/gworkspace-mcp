"""Tests for migration models."""

from datetime import datetime, timezone

from gworkspace_mcp.migrations.models import (
    AppliedMigration,
    Migration,
    MigrationOperation,
    MigrationState,
    OperationType,
)


class TestMigrationOperation:
    """Tests for MigrationOperation model."""

    def test_move_directory_operation(self):
        """Should create move_directory operation with from/to paths."""
        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY,
            **{"from": "~/.old-path", "to": "~/.new-path", "backup": True},
        )
        assert op.type == OperationType.MOVE_DIRECTORY
        assert op.from_path == "~/.old-path"
        assert op.to_path == "~/.new-path"
        assert op.backup is True

    def test_move_file_operation(self):
        """Should create move_file operation."""
        op = MigrationOperation(
            type=OperationType.MOVE_FILE,
            **{"from": "~/.old-path/file.json", "to": "~/.new-path/file.json"},
        )
        assert op.type == OperationType.MOVE_FILE
        assert op.from_path == "~/.old-path/file.json"
        assert op.to_path == "~/.new-path/file.json"

    def test_rename_key_operation(self):
        """Should create rename_key operation."""
        op = MigrationOperation(
            type=OperationType.RENAME_KEY,
            file="~/.config/config.json",
            old_key="oldName",
            new_key="newName",
        )
        assert op.type == OperationType.RENAME_KEY
        assert op.file == "~/.config/config.json"
        assert op.old_key == "oldName"
        assert op.new_key == "newName"

    def test_add_field_operation(self):
        """Should create add_field operation with value."""
        op = MigrationOperation(
            type=OperationType.ADD_FIELD,
            file="~/.config/config.json",
            key="schema_version",
            value="0.2.0",
        )
        assert op.type == OperationType.ADD_FIELD
        assert op.key == "schema_version"
        assert op.value == "0.2.0"

    def test_remove_field_operation(self):
        """Should create remove_field operation."""
        op = MigrationOperation(
            type=OperationType.REMOVE_FIELD,
            file="~/.config/config.json",
            key="deprecated_field",
        )
        assert op.type == OperationType.REMOVE_FIELD
        assert op.key == "deprecated_field"

    def test_skip_if_target_exists_flag(self):
        """Should support skip_if_target_exists flag."""
        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY,
            **{"from": "~/.old", "to": "~/.new", "skip_if_target_exists": True},
        )
        assert op.skip_if_target_exists is True


class TestMigration:
    """Tests for Migration model."""

    def test_migration_with_operations(self):
        """Should create migration with multiple operations."""
        migration = Migration(
            id="0001_test_migration",
            version="0.2.0",
            from_version="0.1.x",
            description="Test migration",
            created_at="2026-02-13",
            operations=[
                MigrationOperation(
                    type=OperationType.MOVE_DIRECTORY, **{"from": "~/.old", "to": "~/.new"}
                ),
                MigrationOperation(
                    type=OperationType.ADD_FIELD,
                    file="~/.new/config.json",
                    key="version",
                    value="0.2.0",
                ),
            ],
        )
        assert migration.id == "0001_test_migration"
        assert migration.version == "0.2.0"
        assert migration.from_version == "0.1.x"
        assert len(migration.operations) == 2

    def test_migration_minimal(self):
        """Should create migration with minimal required fields."""
        migration = Migration(
            id="0002_minimal",
            version="0.3.0",
            from_version="0.2.x",
            description="Minimal migration",
        )
        assert migration.id == "0002_minimal"
        assert migration.operations == []


class TestAppliedMigration:
    """Tests for AppliedMigration model."""

    def test_applied_migration_with_defaults(self):
        """Should create applied migration with default timestamp."""
        applied = AppliedMigration(id="0001_test", version="0.2.0")
        assert applied.id == "0001_test"
        assert applied.version == "0.2.0"
        assert applied.applied_at is not None
        assert applied.applied_at.tzinfo == timezone.utc

    def test_applied_migration_with_timestamp(self):
        """Should create applied migration with custom timestamp."""
        ts = datetime(2026, 2, 13, 15, 30, 0, tzinfo=timezone.utc)
        applied = AppliedMigration(id="0001_test", version="0.2.0", applied_at=ts)
        assert applied.applied_at == ts


class TestMigrationState:
    """Tests for MigrationState model."""

    def test_empty_state(self):
        """Should create empty state with defaults."""
        state = MigrationState()
        assert state.applied_migrations == []
        assert state.current_version == "0.1.0"

    def test_state_with_migrations(self):
        """Should create state with applied migrations."""
        state = MigrationState(
            applied_migrations=[
                AppliedMigration(id="0001_test", version="0.2.0"),
                AppliedMigration(id="0002_another", version="0.3.0"),
            ],
            current_version="0.3.0",
        )
        assert len(state.applied_migrations) == 2
        assert state.current_version == "0.3.0"

    def test_state_serialization(self):
        """Should serialize and deserialize state correctly."""
        state = MigrationState(
            applied_migrations=[
                AppliedMigration(id="0001_test", version="0.2.0"),
            ],
            current_version="0.2.0",
        )
        json_str = state.model_dump_json()
        restored = MigrationState.model_validate_json(json_str)
        assert restored.current_version == state.current_version
        assert len(restored.applied_migrations) == 1
        assert restored.applied_migrations[0].id == "0001_test"
