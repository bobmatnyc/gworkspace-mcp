"""Operation handlers for migration system.

Each handler validates parameters, optionally creates backups,
performs the operation, and returns success/failure with details.
"""

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from google_workspace_mcp.migrations.models import MigrationOperation, OperationType

logger = logging.getLogger(__name__)


@dataclass
class OperationResult:
    """Result of a migration operation.

    Attributes:
        success: Whether the operation succeeded.
        message: Human-readable result message.
        backup_path: Path to backup if created.
        skipped: Whether operation was skipped (e.g., target exists).
    """

    success: bool
    message: str
    backup_path: Path | None = None
    skipped: bool = False


def expand_path(path: str) -> Path:
    """Expand ~ and environment variables in path."""
    return Path(path).expanduser()


def create_backup(source: Path) -> Path | None:
    """Create a timestamped backup of a file or directory.

    Args:
        source: Path to back up.

    Returns:
        Path to backup, or None if source doesn't exist.
    """
    if not source.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = source.parent / f"{source.name}.backup_{timestamp}"

    if source.is_dir():
        shutil.copytree(source, backup_path)
    else:
        shutil.copy2(source, backup_path)

    logger.info(f"Created backup at {backup_path}")
    return backup_path


def handle_move_directory(op: MigrationOperation, dry_run: bool = False) -> OperationResult:
    """Move or rename a directory.

    Args:
        op: Migration operation with from_path and to_path.
        dry_run: If True, only simulate the operation.

    Returns:
        OperationResult with success status and details.
    """
    if not op.from_path or not op.to_path:
        return OperationResult(False, "move_directory requires 'from' and 'to' parameters")

    source = expand_path(op.from_path)
    target = expand_path(op.to_path)

    # Check if source exists
    if not source.exists():
        return OperationResult(True, f"Source {source} does not exist, skipping", skipped=True)

    # Check if target already exists
    if target.exists():
        if op.skip_if_target_exists:
            return OperationResult(True, f"Target {target} already exists, skipping", skipped=True)
        return OperationResult(False, f"Target {target} already exists")

    if dry_run:
        return OperationResult(True, f"Would move {source} -> {target}")

    # Create backup if requested
    backup_path = None
    if op.backup:
        backup_path = create_backup(source)

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Perform the move
    try:
        shutil.move(str(source), str(target))
        return OperationResult(True, f"Moved {source} -> {target}", backup_path=backup_path)
    except OSError as e:
        return OperationResult(False, f"Failed to move directory: {e}")


def handle_move_file(op: MigrationOperation, dry_run: bool = False) -> OperationResult:
    """Move or rename a file.

    Args:
        op: Migration operation with from_path and to_path.
        dry_run: If True, only simulate the operation.

    Returns:
        OperationResult with success status and details.
    """
    if not op.from_path or not op.to_path:
        return OperationResult(False, "move_file requires 'from' and 'to' parameters")

    source = expand_path(op.from_path)
    target = expand_path(op.to_path)

    # Check if source exists
    if not source.exists():
        return OperationResult(True, f"Source {source} does not exist, skipping", skipped=True)

    if not source.is_file():
        return OperationResult(False, f"Source {source} is not a file")

    # Check if target already exists
    if target.exists():
        if op.skip_if_target_exists:
            return OperationResult(True, f"Target {target} already exists, skipping", skipped=True)
        return OperationResult(False, f"Target {target} already exists")

    if dry_run:
        return OperationResult(True, f"Would move {source} -> {target}")

    # Create backup if requested
    backup_path = None
    if op.backup:
        backup_path = create_backup(source)

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Perform the move
    try:
        shutil.move(str(source), str(target))
        return OperationResult(True, f"Moved {source} -> {target}", backup_path=backup_path)
    except OSError as e:
        return OperationResult(False, f"Failed to move file: {e}")


def _load_data_file(file_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Load JSON or YAML file.

    Args:
        file_path: Path to load.

    Returns:
        Tuple of (data dict, error message). One will be None.
    """
    if not file_path.exists():
        return None, f"File {file_path} does not exist"

    try:
        content = file_path.read_text()
        if file_path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content) or {}, None
        else:  # Default to JSON
            return json.loads(content), None
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        return None, f"Failed to parse {file_path}: {e}"


def _save_data_file(file_path: Path, data: dict[str, Any]) -> str | None:
    """Save data to JSON or YAML file.

    Args:
        file_path: Path to save to.
        data: Data to save.

    Returns:
        Error message if failed, None on success.
    """
    try:
        if file_path.suffix in (".yaml", ".yml"):
            content = yaml.safe_dump(data, default_flow_style=False)
        else:  # Default to JSON
            content = json.dumps(data, indent=2, default=str)
        file_path.write_text(content)
        return None
    except OSError as e:
        return f"Failed to write {file_path}: {e}"


def handle_rename_key(op: MigrationOperation, dry_run: bool = False) -> OperationResult:
    """Rename a key in a JSON or YAML file.

    Args:
        op: Migration operation with file, old_key, and new_key.
        dry_run: If True, only simulate the operation.

    Returns:
        OperationResult with success status and details.
    """
    if not op.file or not op.old_key or not op.new_key:
        return OperationResult(
            False, "rename_key requires 'file', 'old_key', and 'new_key' parameters"
        )

    file_path = expand_path(op.file)

    # Load the file
    data, error = _load_data_file(file_path)
    if error:
        return OperationResult(False, error)
    if data is None:
        return OperationResult(False, f"Failed to load {file_path}")

    # Check if old key exists
    if op.old_key not in data:
        return OperationResult(
            True, f"Key '{op.old_key}' not found in {file_path}, skipping", skipped=True
        )

    # Check if new key already exists
    if op.new_key in data:
        return OperationResult(False, f"Key '{op.new_key}' already exists in {file_path}")

    if dry_run:
        return OperationResult(
            True, f"Would rename key '{op.old_key}' -> '{op.new_key}' in {file_path}"
        )

    # Create backup if requested
    backup_path = None
    if op.backup:
        backup_path = create_backup(file_path)

    # Perform the rename
    data[op.new_key] = data.pop(op.old_key)

    # Save the file
    error = _save_data_file(file_path, data)
    if error:
        return OperationResult(False, error)

    return OperationResult(
        True,
        f"Renamed key '{op.old_key}' -> '{op.new_key}' in {file_path}",
        backup_path=backup_path,
    )


def handle_add_field(op: MigrationOperation, dry_run: bool = False) -> OperationResult:
    """Add a field to a JSON or YAML file.

    Args:
        op: Migration operation with file, key, and value.
        dry_run: If True, only simulate the operation.

    Returns:
        OperationResult with success status and details.
    """
    if not op.file or not op.key:
        return OperationResult(False, "add_field requires 'file' and 'key' parameters")

    file_path = expand_path(op.file)

    # Load the file (create empty dict if doesn't exist)
    if file_path.exists():
        data, error = _load_data_file(file_path)
        if error:
            return OperationResult(False, error)
        if data is None:
            data = {}
    else:
        data = {}

    # Check if key already exists
    if op.key in data:
        if op.skip_if_target_exists:
            return OperationResult(
                True, f"Key '{op.key}' already exists in {file_path}, skipping", skipped=True
            )
        return OperationResult(False, f"Key '{op.key}' already exists in {file_path}")

    if dry_run:
        return OperationResult(True, f"Would add key '{op.key}' = {op.value!r} to {file_path}")

    # Create backup if requested and file exists
    backup_path = None
    if op.backup and file_path.exists():
        backup_path = create_backup(file_path)

    # Add the field
    data[op.key] = op.value

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the file
    error = _save_data_file(file_path, data)
    if error:
        return OperationResult(False, error)

    return OperationResult(
        True,
        f"Added key '{op.key}' = {op.value!r} to {file_path}",
        backup_path=backup_path,
    )


def handle_remove_field(op: MigrationOperation, dry_run: bool = False) -> OperationResult:
    """Remove a field from a JSON or YAML file.

    Args:
        op: Migration operation with file and key.
        dry_run: If True, only simulate the operation.

    Returns:
        OperationResult with success status and details.
    """
    if not op.file or not op.key:
        return OperationResult(False, "remove_field requires 'file' and 'key' parameters")

    file_path = expand_path(op.file)

    # Load the file
    data, error = _load_data_file(file_path)
    if error:
        return OperationResult(False, error)
    if data is None:
        return OperationResult(False, f"Failed to load {file_path}")

    # Check if key exists
    if op.key not in data:
        return OperationResult(
            True, f"Key '{op.key}' not found in {file_path}, skipping", skipped=True
        )

    if dry_run:
        return OperationResult(True, f"Would remove key '{op.key}' from {file_path}")

    # Create backup if requested
    backup_path = None
    if op.backup:
        backup_path = create_backup(file_path)

    # Remove the field
    del data[op.key]

    # Save the file
    error = _save_data_file(file_path, data)
    if error:
        return OperationResult(False, error)

    return OperationResult(
        True, f"Removed key '{op.key}' from {file_path}", backup_path=backup_path
    )


# Operation handler registry
OPERATION_HANDLERS = {
    OperationType.MOVE_DIRECTORY: handle_move_directory,
    OperationType.MOVE_FILE: handle_move_file,
    OperationType.RENAME_KEY: handle_rename_key,
    OperationType.ADD_FIELD: handle_add_field,
    OperationType.REMOVE_FIELD: handle_remove_field,
}


def execute_operation(op: MigrationOperation, dry_run: bool = False) -> OperationResult:
    """Execute a migration operation.

    Args:
        op: The operation to execute.
        dry_run: If True, only simulate the operation.

    Returns:
        OperationResult with success status and details.
    """
    handler = OPERATION_HANDLERS.get(op.type)
    if not handler:
        return OperationResult(False, f"Unknown operation type: {op.type}")

    return handler(op, dry_run)
