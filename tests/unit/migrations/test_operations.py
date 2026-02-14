"""Tests for migration operation handlers."""

import json
from pathlib import Path

import yaml

from google_workspace_mcp.migrations.models import MigrationOperation, OperationType
from google_workspace_mcp.migrations.operations import (
    create_backup,
    execute_operation,
    expand_path,
    handle_add_field,
    handle_move_directory,
    handle_move_file,
    handle_remove_field,
    handle_rename_key,
)


class TestExpandPath:
    """Tests for path expansion."""

    def test_expand_home_directory(self):
        """Should expand ~ to home directory."""
        result = expand_path("~/.gworkspace-mcp")
        assert str(result).startswith(str(Path.home()))
        assert ".gworkspace-mcp" in str(result)

    def test_expand_absolute_path(self):
        """Should handle absolute paths."""
        result = expand_path("/tmp/test")
        assert str(result) == "/tmp/test"


class TestCreateBackup:
    """Tests for backup creation."""

    def test_backup_file(self, tmp_path: Path):
        """Should create backup of file."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        backup_path = create_backup(test_file)

        assert backup_path is not None
        assert backup_path.exists()
        assert "backup_" in backup_path.name
        assert backup_path.read_text() == '{"key": "value"}'

    def test_backup_directory(self, tmp_path: Path):
        """Should create backup of directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        backup_path = create_backup(test_dir)

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.is_dir()
        assert (backup_path / "file.txt").read_text() == "content"

    def test_backup_nonexistent(self, tmp_path: Path):
        """Should return None for nonexistent path."""
        result = create_backup(tmp_path / "nonexistent")
        assert result is None


class TestHandleMoveDirectory:
    """Tests for move_directory operation."""

    def test_move_directory_success(self, tmp_path: Path):
        """Should move directory successfully."""
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("content")
        target = tmp_path / "target_dir"

        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY, **{"from": str(source), "to": str(target)}
        )
        result = handle_move_directory(op)

        assert result.success
        assert not source.exists()
        assert target.exists()
        assert (target / "file.txt").read_text() == "content"

    def test_move_directory_with_backup(self, tmp_path: Path):
        """Should create backup before moving."""
        source = tmp_path / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("content")
        target = tmp_path / "target_dir"

        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY,
            **{"from": str(source), "to": str(target), "backup": True},
        )
        result = handle_move_directory(op)

        assert result.success
        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_move_directory_source_missing(self, tmp_path: Path):
        """Should skip when source doesn't exist."""
        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY,
            **{"from": str(tmp_path / "nonexistent"), "to": str(tmp_path / "target")},
        )
        result = handle_move_directory(op)

        assert result.success
        assert result.skipped

    def test_move_directory_target_exists(self, tmp_path: Path):
        """Should fail when target exists."""
        source = tmp_path / "source_dir"
        source.mkdir()
        target = tmp_path / "target_dir"
        target.mkdir()

        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY, **{"from": str(source), "to": str(target)}
        )
        result = handle_move_directory(op)

        assert not result.success
        assert "already exists" in result.message

    def test_move_directory_skip_if_target_exists(self, tmp_path: Path):
        """Should skip when target exists with skip flag."""
        source = tmp_path / "source_dir"
        source.mkdir()
        target = tmp_path / "target_dir"
        target.mkdir()

        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY,
            **{"from": str(source), "to": str(target), "skip_if_target_exists": True},
        )
        result = handle_move_directory(op)

        assert result.success
        assert result.skipped

    def test_move_directory_dry_run(self, tmp_path: Path):
        """Should not actually move in dry-run mode."""
        source = tmp_path / "source_dir"
        source.mkdir()
        target = tmp_path / "target_dir"

        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY, **{"from": str(source), "to": str(target)}
        )
        result = handle_move_directory(op, dry_run=True)

        assert result.success
        assert "Would move" in result.message
        assert source.exists()
        assert not target.exists()


class TestHandleMoveFile:
    """Tests for move_file operation."""

    def test_move_file_success(self, tmp_path: Path):
        """Should move file successfully."""
        source = tmp_path / "source.json"
        source.write_text('{"key": "value"}')
        target = tmp_path / "target.json"

        op = MigrationOperation(
            type=OperationType.MOVE_FILE, **{"from": str(source), "to": str(target)}
        )
        result = handle_move_file(op)

        assert result.success
        assert not source.exists()
        assert target.exists()
        assert target.read_text() == '{"key": "value"}'

    def test_move_file_source_missing(self, tmp_path: Path):
        """Should skip when source doesn't exist."""
        op = MigrationOperation(
            type=OperationType.MOVE_FILE,
            **{"from": str(tmp_path / "nonexistent.json"), "to": str(tmp_path / "target.json")},
        )
        result = handle_move_file(op)

        assert result.success
        assert result.skipped

    def test_move_file_not_a_file(self, tmp_path: Path):
        """Should fail when source is a directory."""
        source = tmp_path / "source_dir"
        source.mkdir()

        op = MigrationOperation(
            type=OperationType.MOVE_FILE,
            **{"from": str(source), "to": str(tmp_path / "target.json")},
        )
        result = handle_move_file(op)

        assert not result.success
        assert "not a file" in result.message


class TestHandleRenameKey:
    """Tests for rename_key operation."""

    def test_rename_key_json(self, tmp_path: Path):
        """Should rename key in JSON file."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"old_name": "value", "other": "data"}')

        op = MigrationOperation(
            type=OperationType.RENAME_KEY,
            file=str(test_file),
            old_key="old_name",
            new_key="new_name",
        )
        result = handle_rename_key(op)

        assert result.success
        data = json.loads(test_file.read_text())
        assert "new_name" in data
        assert "old_name" not in data
        assert data["new_name"] == "value"

    def test_rename_key_yaml(self, tmp_path: Path):
        """Should rename key in YAML file."""
        test_file = tmp_path / "config.yaml"
        test_file.write_text("old_name: value\nother: data\n")

        op = MigrationOperation(
            type=OperationType.RENAME_KEY,
            file=str(test_file),
            old_key="old_name",
            new_key="new_name",
        )
        result = handle_rename_key(op)

        assert result.success
        data = yaml.safe_load(test_file.read_text())
        assert "new_name" in data
        assert "old_name" not in data

    def test_rename_key_missing_key(self, tmp_path: Path):
        """Should skip when key doesn't exist."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"other": "data"}')

        op = MigrationOperation(
            type=OperationType.RENAME_KEY,
            file=str(test_file),
            old_key="nonexistent",
            new_key="new_name",
        )
        result = handle_rename_key(op)

        assert result.success
        assert result.skipped

    def test_rename_key_new_key_exists(self, tmp_path: Path):
        """Should fail when new key already exists."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"old_name": "value", "new_name": "existing"}')

        op = MigrationOperation(
            type=OperationType.RENAME_KEY,
            file=str(test_file),
            old_key="old_name",
            new_key="new_name",
        )
        result = handle_rename_key(op)

        assert not result.success
        assert "already exists" in result.message


class TestHandleAddField:
    """Tests for add_field operation."""

    def test_add_field_to_existing(self, tmp_path: Path):
        """Should add field to existing file."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"existing": "value"}')

        op = MigrationOperation(
            type=OperationType.ADD_FIELD,
            file=str(test_file),
            key="new_field",
            value="new_value",
        )
        result = handle_add_field(op)

        assert result.success
        data = json.loads(test_file.read_text())
        assert data["new_field"] == "new_value"
        assert data["existing"] == "value"

    def test_add_field_to_new_file(self, tmp_path: Path):
        """Should create file if it doesn't exist."""
        test_file = tmp_path / "new_config.json"

        op = MigrationOperation(
            type=OperationType.ADD_FIELD,
            file=str(test_file),
            key="version",
            value="0.2.0",
        )
        result = handle_add_field(op)

        assert result.success
        assert test_file.exists()
        data = json.loads(test_file.read_text())
        assert data["version"] == "0.2.0"

    def test_add_field_key_exists(self, tmp_path: Path):
        """Should fail when key already exists."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"version": "0.1.0"}')

        op = MigrationOperation(
            type=OperationType.ADD_FIELD,
            file=str(test_file),
            key="version",
            value="0.2.0",
        )
        result = handle_add_field(op)

        assert not result.success
        assert "already exists" in result.message

    def test_add_field_skip_if_exists(self, tmp_path: Path):
        """Should skip when key exists with skip flag."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"version": "0.1.0"}')

        op = MigrationOperation(
            type=OperationType.ADD_FIELD,
            file=str(test_file),
            key="version",
            value="0.2.0",
            skip_if_target_exists=True,
        )
        result = handle_add_field(op)

        assert result.success
        assert result.skipped


class TestHandleRemoveField:
    """Tests for remove_field operation."""

    def test_remove_field_success(self, tmp_path: Path):
        """Should remove field from file."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"keep": "value", "remove": "this"}')

        op = MigrationOperation(
            type=OperationType.REMOVE_FIELD,
            file=str(test_file),
            key="remove",
        )
        result = handle_remove_field(op)

        assert result.success
        data = json.loads(test_file.read_text())
        assert "remove" not in data
        assert data["keep"] == "value"

    def test_remove_field_missing_key(self, tmp_path: Path):
        """Should skip when key doesn't exist."""
        test_file = tmp_path / "config.json"
        test_file.write_text('{"keep": "value"}')

        op = MigrationOperation(
            type=OperationType.REMOVE_FIELD,
            file=str(test_file),
            key="nonexistent",
        )
        result = handle_remove_field(op)

        assert result.success
        assert result.skipped


class TestExecuteOperation:
    """Tests for execute_operation dispatcher."""

    def test_execute_move_directory(self, tmp_path: Path):
        """Should dispatch to move_directory handler."""
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"

        op = MigrationOperation(
            type=OperationType.MOVE_DIRECTORY, **{"from": str(source), "to": str(target)}
        )
        result = execute_operation(op)

        assert result.success
        assert target.exists()

    def test_execute_missing_params(self, tmp_path: Path):
        """Should handle operations with missing required params."""
        # Move directory without from/to paths will fail validation in handler
        op = MigrationOperation(type=OperationType.MOVE_DIRECTORY)
        result = execute_operation(op)

        assert not result.success
        assert "requires" in result.message
