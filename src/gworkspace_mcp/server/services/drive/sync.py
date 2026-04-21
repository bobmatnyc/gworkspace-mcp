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
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="sync_drive",
        description=(
            "Download, upload, or sync files between Google Drive and local filesystem using "
            "rclone. Use dry_run=true to preview changes before applying them. "
            "Requires rclone to be installed."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["download", "upload", "sync"],
                    "description": (
                        "Operation to perform: download (Drive → local), "
                        "upload (local → Drive), sync (bidirectional with rclone sync)"
                    ),
                },
                "drive_path": {
                    "type": "string",
                    "description": "Path in Google Drive (required for download and upload actions)",
                },
                "local_path": {
                    "type": "string",
                    "description": "Local filesystem path (required for download and upload actions)",
                },
                "source": {
                    "type": "string",
                    "description": (
                        "Source path for sync action. Use 'drive:path' for Drive "
                        "or '/local/path' for local"
                    ),
                },
                "destination": {
                    "type": "string",
                    "description": (
                        "Destination path for sync action. Use 'drive:path' for Drive "
                        "or '/local/path' for local"
                    ),
                },
                "google_docs_format": {
                    "type": "string",
                    "enum": ["docx", "pdf", "odt", "txt", "xlsx", "csv", "pptx"],
                    "description": "Export format for Google Docs/Sheets/Slides (download action only)",
                    "default": "docx",
                },
                "convert_to_google_docs": {
                    "type": "boolean",
                    "description": "Convert Office files to Google Docs format (upload action only)",
                    "default": False,
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Preview changes without applying them (RECOMMENDED: start with true)",
                    "default": True,
                },
                "delete_extra": {
                    "type": "boolean",
                    "description": "Delete files in destination not present in source (sync action only, CAUTION: destructive)",
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
                    "description": "Patterns to include — only matching files are synced (sync action only)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action"],
        },
    ),
]


# =============================================================================
# Helper functions
# =============================================================================


def _get_rclone_manager(svc: BaseService) -> Any:
    """Get an RcloneManager instance using the service's storage."""
    try:
        from gworkspace_mcp.rclone_manager import (  # type: ignore[import-not-found]
            RcloneManager,
            RcloneNotInstalledError,
        )
    except ImportError as e:
        raise RuntimeError(
            "rclone features are not available. RcloneManager module not found. "
            "The following Drive tools require rclone:\n"
            "- list_drive_contents\n"
            "- sync_drive"
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
    drive_path = arguments.get("drive_path")
    local_path = arguments.get("local_path")

    if not drive_path:
        return {"error": "drive_path is required for download action"}
    if not local_path:
        return {"error": "local_path is required for download action"}

    google_docs_format = arguments.get("google_docs_format", "docx")
    exclude = arguments.get("exclude")
    dry_run = arguments.get("dry_run", True)

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
    local_path = arguments.get("local_path")
    drive_path = arguments.get("drive_path")

    if not local_path:
        return {"error": "local_path is required for upload action"}
    if not drive_path:
        return {"error": "drive_path is required for upload action"}

    convert_to_google_docs = arguments.get("convert_to_google_docs", False)
    exclude = arguments.get("exclude")
    dry_run = arguments.get("dry_run", True)

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
    source = arguments.get("source")
    destination = arguments.get("destination")

    if not source:
        return {"error": "source is required for sync action"}
    if not destination:
        return {"error": "destination is required for sync action"}

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


# =============================================================================
# Dispatcher
# =============================================================================


async def _sync_drive(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the appropriate sync handler based on action."""
    action = arguments.get("action")
    if action == "download":
        return await _download_drive_folder(svc, arguments)
    elif action == "upload":
        return await _upload_to_drive(svc, arguments)
    elif action == "sync":
        return await _sync_drive_folder(svc, arguments)
    else:
        return {"error": f"Unknown action '{action}'. Must be one of: download, upload, sync."}


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Drive sync handlers."""
    return {
        "list_drive_contents": lambda args: _list_drive_contents(svc, args),
        "sync_drive": lambda args: _sync_drive(svc, args),
    }
