"""Data models for the migration system.

This module defines Pydantic models for migration definitions,
operations, and state tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OperationType(str, Enum):
    """Supported migration operation types."""

    MOVE_DIRECTORY = "move_directory"
    MOVE_FILE = "move_file"
    RENAME_KEY = "rename_key"
    ADD_FIELD = "add_field"
    REMOVE_FIELD = "remove_field"


class MigrationOperation(BaseModel):
    """A single migration operation.

    Attributes:
        type: The operation type (move_directory, move_file, etc.).
        params: Operation-specific parameters.
    """

    type: OperationType = Field(..., description="Operation type")
    # Operation-specific parameters
    from_path: str | None = Field(default=None, alias="from", description="Source path")
    to_path: str | None = Field(default=None, alias="to", description="Destination path")
    file: str | None = Field(default=None, description="File to modify")
    old_key: str | None = Field(default=None, description="Key to rename from")
    new_key: str | None = Field(default=None, description="Key to rename to")
    key: str | None = Field(default=None, description="Field key for add/remove")
    value: Any = Field(default=None, description="Value for add_field operation")
    backup: bool = Field(default=False, description="Create backup before operation")
    skip_if_target_exists: bool = Field(default=False, description="Skip if target already exists")

    model_config = {"populate_by_name": True}


class Migration(BaseModel):
    """A complete migration definition.

    Migrations are defined in YAML files and executed in order by ID.

    Attributes:
        id: Unique migration identifier (e.g., "0001_rename_credentials_dir").
        version: Target version after migration (e.g., "0.2.0").
        from_version: Source version pattern (e.g., "0.1.x").
        description: Human-readable description.
        created_at: Migration creation date.
        operations: List of operations to perform.
    """

    id: str = Field(..., description="Unique migration ID")
    version: str = Field(..., description="Target version after migration")
    from_version: str = Field(..., description="Source version pattern")
    description: str = Field(..., description="Human-readable description")
    created_at: str | None = Field(default=None, description="Migration creation date")
    operations: list[MigrationOperation] = Field(
        default_factory=list, description="Operations to perform"
    )


class AppliedMigration(BaseModel):
    """Record of an applied migration.

    Attributes:
        id: Migration ID that was applied.
        applied_at: When the migration was applied.
        version: Version the migration upgraded to.
    """

    id: str = Field(..., description="Migration ID")
    applied_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When migration was applied",
    )
    version: str = Field(..., description="Target version")


class MigrationState(BaseModel):
    """State tracking for applied migrations.

    Stored in ./.gworkspace-mcp/.migration_state.json (project-level)

    Attributes:
        applied_migrations: List of migrations that have been applied.
        current_version: Current schema version after all migrations.
    """

    applied_migrations: list[AppliedMigration] = Field(
        default_factory=list, description="List of applied migrations"
    )
    current_version: str = Field(default="0.1.0", description="Current schema version")
