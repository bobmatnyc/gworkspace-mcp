"""Google Drive sync sub-module: rclone-powered list, download, upload, and sync."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import SERVICE_NAME

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="list_drive_contents",
        description="List contents of a Google Drive folder using rclone. Returns structured JSON with file metadata including size, modification time, and file IDs. Requires rclone to be installed.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Drive path to list (e.g., 'Documents' or 'Shared drives/TeamDrive/Projects')",
                    "default": "",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Recursively list all subdirectories",
                    "default": False,
                },
                "files_only": {
                    "type": "boolean",
                    "description": "Show only files, not directories",
                    "default": False,
                },
                "include_hash": {
                    "type": "boolean",
                    "description": "Include MD5 hash for each file",
                    "default": False,
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum recursion depth (requires recursive=true, -1 for unlimited)",
                    "default": -1,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="download_drive_folder",
        description="Download a folder from Google Drive to local filesystem using rclone. Does not delete local files. Requires rclone to be installed.",
        inputSchema={
            "type": "object",
            "properties": {
                "drive_path": {
                    "type": "string",
                    "description": "Path in Google Drive to download (e.g., 'Documents/Reports')",
                },
                "local_path": {
                    "type": "string",
                    "description": "Local destination directory",
                },
                "google_docs_format": {
                    "type": "string",
                    "description": "Export format for Google Docs/Sheets/Slides",
                    "enum": ["docx", "pdf", "odt", "txt", "xlsx", "csv", "pptx"],
                    "default": "docx",
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Patterns to exclude (e.g., ['*.tmp', '.git/**'])",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview changes without downloading",
                    "default": False,
                },
            },
            "required": ["drive_path", "local_path"],
        },
    ),
    Tool(
        name="upload_to_drive",
        description="Upload a local folder to Google Drive using rclone. Does not delete files in Drive. Requires rclone to be installed.",
        inputSchema={
            "type": "object",
            "properties": {
                "local_path": {
                    "type": "string",
                    "description": "Local folder path to upload",
                },
                "drive_path": {
                    "type": "string",
                    "description": "Destination path in Google Drive",
                },
                "convert_to_google_docs": {
                    "type": "boolean",
                    "description": "Convert Office files to Google Docs format",
                    "default": False,
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Patterns to exclude (e.g., ['node_modules/**', '.git/**'])",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview changes without uploading",
                    "default": False,
                },
            },
            "required": ["local_path", "drive_path"],
        },
    ),
    Tool(
        name="sync_drive_folder",
        description="Sync files between local filesystem and Google Drive using rclone. Use dry_run=true to preview changes before syncing. Requires rclone to be installed.",
        inputSchema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source path. Use 'drive:path' for Drive or '/local/path' for local",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination path. Use 'drive:path' for Drive or '/local/path' for local",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview changes without making them (RECOMMENDED: start with true)",
                    "default": True,
                },
                "delete_extra": {
                    "type": "boolean",
                    "description": "Delete files in destination that don't exist in source (CAUTION: destructive)",
                    "default": False,
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Patterns to exclude (e.g., ['*.tmp', '.git/**'])",
                },
                "include": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Patterns to include (if set, only matching files are synced)",
                },
            },
            "required": ["source", "destination"],
        },
    ),
]


# =============================================================================
# Helper functions
# =============================================================================


def _get_rclone_manager(svc: BaseService) -> Any:
    """Get an RcloneManager instance using the service's storage."""
    try:
        from gworkspace_mcp.rclone_manager import RcloneManager, RcloneNotInstalledError
    except ImportError as e:
        raise RuntimeError(
            "rclone features are not available. RcloneManager module not found. "
            "The following Drive tools require rclone:\n"
            "- list_drive_contents\n"
            "- download_drive_folder\n"
            "- upload_to_drive\n"
            "- sync_drive_folder"
        ) from e

    try:
        return RcloneManager(
            storage=svc.storage,
            service_name=SERVICE_NAME,
        )
    except RcloneNotInstalledError as e:
        raise RuntimeError(
            "rclone is not installed. Install it from https://rclone.org/downloads/ "
            "to use Drive sync features."
        ) from e


# =============================================================================
# Handler functions
# =============================================================================


async def _list_drive_contents(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List Drive folder contents using rclone lsjson."""
    path = arguments.get("path", "")
    recursive = arguments.get("recursive", False)
    files_only = arguments.get("files_only", False)
    include_hash = arguments.get("include_hash", False)
    max_depth = arguments.get("max_depth", -1)

    manager = _get_rclone_manager(svc)
    try:
        items = manager.list_json(
            path=path,
            recursive=recursive,
            files_only=files_only,
            include_hash=include_hash,
            max_depth=max_depth,
        )
        return {
            "items": items,
            "count": len(items),
            "path": path or "(root)",
        }
    finally:
        manager.cleanup()


async def _download_drive_folder(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Download Drive folder to local filesystem."""
    drive_path = arguments["drive_path"]
    local_path = arguments["local_path"]
    google_docs_format = arguments.get("google_docs_format", "docx")
    exclude = arguments.get("exclude")
    dry_run = arguments.get("dry_run", False)

    manager = _get_rclone_manager(svc)
    try:
        return manager.download(
            drive_path=drive_path,
            local_path=local_path,
            google_docs_format=google_docs_format,
            exclude=exclude,
            dry_run=dry_run,
        )
    finally:
        manager.cleanup()


async def _upload_to_drive(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Upload local folder to Google Drive."""
    local_path = arguments["local_path"]
    drive_path = arguments["drive_path"]
    convert_to_google_docs = arguments.get("convert_to_google_docs", False)
    exclude = arguments.get("exclude")
    dry_run = arguments.get("dry_run", False)

    manager = _get_rclone_manager(svc)
    try:
        return manager.upload(
            local_path=local_path,
            drive_path=drive_path,
            convert_to_google_docs=convert_to_google_docs,
            exclude=exclude,
            dry_run=dry_run,
        )
    finally:
        manager.cleanup()


async def _sync_drive_folder(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Sync files between local and Drive."""
    source = arguments["source"]
    destination = arguments["destination"]
    dry_run = arguments.get("dry_run", True)
    delete_extra = arguments.get("delete_extra", False)
    exclude = arguments.get("exclude")
    include = arguments.get("include")

    manager = _get_rclone_manager(svc)
    try:
        return manager.sync(
            source=source,
            destination=destination,
            delete_extra=delete_extra,
            exclude=exclude,
            include=include,
            dry_run=dry_run,
        )
    finally:
        manager.cleanup()


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Drive sync handlers."""
    return {
        "list_drive_contents": lambda args: _list_drive_contents(svc, args),
        "download_drive_folder": lambda args: _download_drive_folder(svc, args),
        "upload_to_drive": lambda args: _upload_to_drive(svc, args),
        "sync_drive_folder": lambda args: _sync_drive_folder(svc, args),
    }
