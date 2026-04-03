"""Google Drive service module for MCP server."""

from __future__ import annotations

import json
import logging
import secrets
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DRIVE_API_BASE, SERVICE_NAME

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="search_drive_files",
        description="Search Google Drive files using a query string. Bare search terms like 'MSA' are automatically wrapped in 'fullText contains' syntax. You can also use Drive API query syntax directly (e.g., 'name contains \"report\"', 'mimeType = \"application/pdf\"').",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - can be simple terms (auto-wrapped) or Drive API syntax (e.g., 'name contains \"report\"')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of files to return (default: 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_drive_file_content",
        description=(
            "Get the content of a Google Drive file by ID. "
            "Text files are returned inline; binary files require save_path. "
            "Use output_format='auto' (default) to automatically convert Google Docs to "
            "markdown, Sheets to CSV, and local docx/pdf/pptx files to markdown. "
            "Use output_format='raw' to skip conversion and return the original bytes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID",
                },
                "save_path": {
                    "type": "string",
                    "description": "Absolute local path to save the file. Required for binary files; optional for text files (returns content inline if omitted).",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["auto", "md", "markdown", "csv", "json", "raw"],
                    "description": (
                        "Output format. 'auto' converts based on file type "
                        "(Google Docs/docx/pdf/pptx -> markdown, Google Sheets/xls/xlsx -> csv). "
                        "'raw' returns original bytes/text without conversion."
                    ),
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="convert_document",
        description=(
            "Convert a document between formats using pandoc. "
            "Supports docx<->md, pdf->md, xls/xlsx<->csv/json, pptx->md, html<->md, and more. "
            "Pandoc must be installed on the system."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "input_path": {
                    "type": "string",
                    "description": "Absolute local file path to convert.",
                },
                "output_path": {
                    "type": "string",
                    "description": (
                        "Absolute output file path. "
                        "Extension determines output format if to_format is not specified."
                    ),
                },
                "from_format": {
                    "type": "string",
                    "description": "Input format (auto-detected from extension if omitted).",
                },
                "to_format": {
                    "type": "string",
                    "enum": [
                        "md",
                        "markdown",
                        "html",
                        "docx",
                        "odt",
                        "rst",
                        "txt",
                        "pdf",
                        "csv",
                        "json",
                        "xlsx",
                    ],
                    "description": "Output format. Defaults to 'md' (markdown).",
                    "default": "md",
                },
            },
            "required": ["input_path"],
        },
    ),
    Tool(
        name="create_drive_folder",
        description="Create a new folder in Google Drive",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Folder name",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent folder ID (optional, defaults to root)",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="upload_drive_file",
        description="Upload a file to Google Drive. Supports binary files via local_path or text content via content parameter.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "File name in Drive. If omitted when using local_path, the local filename is used.",
                },
                "local_path": {
                    "type": "string",
                    "description": "Absolute path to a local file to upload (binary or text). If provided, content parameter is ignored.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to upload. Use local_path instead for binary files.",
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIME type (default: 'text/plain', or auto-detected from local_path)",
                    "default": "text/plain",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent folder ID (optional)",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="delete_drive_file",
        description="Delete a file or folder from Google Drive",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "File or folder ID to delete",
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="move_drive_file",
        description="Move a file to a different folder in Google Drive",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "File ID to move",
                },
                "new_parent_id": {
                    "type": "string",
                    "description": "Destination folder ID",
                },
            },
            "required": ["file_id", "new_parent_id"],
        },
    ),
    Tool(
        name="copy_drive_file",
        description="Create a copy of a file in Google Drive",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "File ID to copy",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the copy (optional, defaults to 'Copy of [original]')",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Destination folder ID (optional, defaults to same folder)",
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="rename_drive_file",
        description="Rename a file or folder in Google Drive",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "File or folder ID to rename",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name for the file or folder",
                },
            },
            "required": ["file_id", "new_name"],
        },
    ),
    # Drive Permissions Management
    Tool(
        name="list_file_permissions",
        description="List all permissions (who has access) for a Google Drive file or folder",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="share_file",
        description="Share a Drive file or folder with a user, group, domain, or make it public (anyone with link)",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder to share",
                },
                "type": {
                    "type": "string",
                    "enum": ["user", "group", "domain", "anyone"],
                    "description": "Type of grantee: user (individual), group (Google Group), domain (all users in domain), anyone (public link)",
                },
                "role": {
                    "type": "string",
                    "enum": ["reader", "writer", "commenter"],
                    "description": "Permission level: reader (view only), writer (can edit), commenter (can comment)",
                },
                "email_address": {
                    "type": "string",
                    "description": "Email address (required for user/group type)",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain name (required for domain type, e.g., 'company.com')",
                },
                "send_notification": {
                    "type": "boolean",
                    "description": "Send email notification to the user (default: true, only for user/group type)",
                    "default": True,
                },
            },
            "required": ["file_id", "type", "role"],
        },
    ),
    Tool(
        name="update_file_permission",
        description="Update an existing permission's role on a Drive file or folder",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
                "permission_id": {
                    "type": "string",
                    "description": "Permission ID to update (from list_file_permissions)",
                },
                "role": {
                    "type": "string",
                    "enum": ["reader", "writer", "commenter"],
                    "description": "New permission level",
                },
            },
            "required": ["file_id", "permission_id", "role"],
        },
    ),
    Tool(
        name="remove_file_permission",
        description="Remove a permission (revoke access) from a Drive file or folder",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
                "permission_id": {
                    "type": "string",
                    "description": "Permission ID to remove (from list_file_permissions)",
                },
            },
            "required": ["file_id", "permission_id"],
        },
    ),
    Tool(
        name="transfer_file_ownership",
        description="Transfer ownership of a Drive file to another user. The current owner becomes a writer. Only works for files you own.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file to transfer ownership",
                },
                "new_owner_email": {
                    "type": "string",
                    "description": "Email address of the new owner",
                },
            },
            "required": ["file_id", "new_owner_email"],
        },
    ),
    # Drive rclone-powered operations
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


def _normalize_drive_query(query: str) -> str:
    """Normalize a search query for Google Drive API.

    If the query doesn't contain Drive API operators, wrap it in fullText contains.
    """
    operators = ["contains", "=", "!=", "<", ">", " in ", " has ", " not "]
    query_lower = query.lower()
    if any(op in query_lower for op in operators):
        return query
    escaped_query = query.replace("'", "\\'")
    return f"fullText contains '{escaped_query}'"


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


async def _search_drive_files(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search Google Drive files."""
    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 10)

    normalized_query = _normalize_drive_query(query)

    url = f"{DRIVE_API_BASE}/files"
    params = {
        "q": normalized_query,
        "pageSize": max_results,
        "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink,owners)",
        "includeItemsFromAllDrives": "true",
        "supportsAllDrives": "true",
    }

    response = await svc._make_request("GET", url, params=params)

    files = []
    for item in response.get("files", []):
        files.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "mimeType": item.get("mimeType"),
                "modifiedTime": item.get("modifiedTime"),
                "size": item.get("size"),
                "webViewLink": item.get("webViewLink"),
                "owners": [o.get("emailAddress") for o in item.get("owners", [])],
            }
        )

    return {"files": files, "count": len(files)}


async def _get_drive_file_content(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get content of a Google Drive file with format conversion support."""
    import os
    from pathlib import Path

    from gworkspace_mcp.conversion.pandoc_service import (
        GDRIVE_EXPORT_MIME,
        PANDOC_INPUT_FORMATS,
        SPREADSHEET_FORMATS,
        ConversionError,
        PandocService,
    )

    file_id = arguments["file_id"]
    save_path = arguments.get("save_path")
    output_format = arguments.get("output_format", "auto").lower()

    meta_url = f"{DRIVE_API_BASE}/files/{file_id}"
    metadata = await svc._make_request(
        "GET", meta_url, params={"fields": "id,name,mimeType,size", "supportsAllDrives": "true"}
    )

    mime_type = metadata.get("mimeType", "")
    file_name = metadata.get("name", "")

    pandoc = PandocService()

    is_gdrive_native = mime_type in GDRIVE_EXPORT_MIME
    is_spreadsheet_gdrive = mime_type == "application/vnd.google-apps.spreadsheet"

    plain_export_map = {
        "application/vnd.google-apps.document": "text/plain",
        "application/vnd.google-apps.spreadsheet": "text/csv",
        "application/vnd.google-apps.presentation": "text/plain",
    }

    if output_format == "raw":
        if mime_type in plain_export_map:
            export_url = f"{DRIVE_API_BASE}/files/{file_id}/export"
            response = await svc._make_raw_request(
                "GET",
                export_url,
                params={"mimeType": plain_export_map[mime_type], "supportsAllDrives": "true"},
            )
        else:
            response = await svc._make_raw_request(
                "GET",
                f"{DRIVE_API_BASE}/files/{file_id}",
                params={"alt": "media", "supportsAllDrives": "true"},
            )
        raw_bytes = response.content
        if save_path:
            _resolved_save = Path(save_path).expanduser().resolve()
            _home = Path.home().resolve()
            if not str(_resolved_save).startswith(str(_home)):
                return {
                    "error": f"save_path must be within home directory ({_home}). Got: {_resolved_save}"
                }
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(raw_bytes)
            return {
                "id": metadata.get("id"),
                "name": file_name,
                "mimeType": mime_type,
                "saved_to": save_path,
                "size": len(raw_bytes),
            }
        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = f"[Binary file: {len(raw_bytes)} bytes. Use save_path to download.]"
        return {
            "id": metadata.get("id"),
            "name": file_name,
            "mimeType": mime_type,
            "content": content,
        }

    want_json = output_format == "json"
    want_md = output_format in ("md", "markdown") or (
        output_format == "auto" and not is_spreadsheet_gdrive
    )

    if is_gdrive_native:
        rich_mime = GDRIVE_EXPORT_MIME[mime_type]
        export_url = f"{DRIVE_API_BASE}/files/{file_id}/export"
        response = await svc._make_raw_request(
            "GET", export_url, params={"mimeType": rich_mime, "supportsAllDrives": "true"}
        )
        downloaded_bytes = response.content
        ext_map = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        }
        downloaded_ext = ext_map.get(rich_mime, ".bin")
    else:
        response = await svc._make_raw_request(
            "GET",
            f"{DRIVE_API_BASE}/files/{file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
        )
        downloaded_bytes = response.content
        downloaded_ext = Path(file_name).suffix.lower() if file_name else ".bin"

    output_ext: str
    if downloaded_ext in SPREADSHEET_FORMATS or (
        is_spreadsheet_gdrive and downloaded_ext == ".xlsx"
    ):
        if want_json:
            try:
                converted_bytes = pandoc.convert_bytes(
                    downloaded_bytes, "xlsx", "json", filename_hint=file_name or "sheet"
                )
                content = converted_bytes.decode("utf-8")
                output_ext = ".json"
            except ConversionError as exc:
                content = f"[Conversion error: {exc}]"
                output_ext = ".txt"
        else:
            try:
                converted_bytes = pandoc.convert_bytes(
                    downloaded_bytes, "xlsx", "csv", filename_hint=file_name or "sheet"
                )
                content = converted_bytes.decode("utf-8")
                output_ext = ".csv"
            except ConversionError as exc:
                content = f"[Conversion error: {exc}]"
                output_ext = ".txt"
    elif want_md and pandoc.is_available():
        from_fmt = PANDOC_INPUT_FORMATS.get(downloaded_ext, "docx")
        try:
            converted_bytes = pandoc.convert_bytes(
                downloaded_bytes, from_fmt, "markdown", filename_hint=file_name or "doc"
            )
            content = converted_bytes.decode("utf-8")
            output_ext = ".md"
        except ConversionError as exc:
            logger.warning("Pandoc conversion failed, falling back to raw text: %s", exc)
            try:
                content = downloaded_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = (
                    f"[Binary file: {len(downloaded_bytes)} bytes. Use save_path to download.]"
                )
            output_ext = ".txt"
    else:
        try:
            content = downloaded_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = f"[Binary file: {len(downloaded_bytes)} bytes. Use save_path to download.]"
        output_ext = ".txt"

    if save_path:
        sp = Path(save_path)
        if not sp.suffix:
            sp = sp.with_suffix(output_ext)
        os.makedirs(str(sp.parent), exist_ok=True)
        sp.write_text(content, encoding="utf-8")
        return {
            "id": metadata.get("id"),
            "name": file_name,
            "mimeType": mime_type,
            "saved_to": str(sp),
            "size": len(content.encode("utf-8")),
            "output_format": output_ext.lstrip("."),
        }

    return {
        "id": metadata.get("id"),
        "name": file_name,
        "mimeType": mime_type,
        "content": content,
        "output_format": output_ext.lstrip("."),
    }


async def _convert_document(
    svc: BaseService,  # noqa: ARG001
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Convert a local document between formats using pandoc or openpyxl."""
    import os
    from pathlib import Path

    from gworkspace_mcp.conversion.pandoc_service import (
        ConversionError,
        PandocService,
        _pandoc_format_to_ext,
    )

    input_path_str = arguments["input_path"]
    to_format = arguments.get("to_format", "md")
    from_format = arguments.get("from_format")

    input_path = Path(input_path_str)
    if not input_path.exists():
        return {"error": f"Input file not found: {input_path_str}"}

    output_path_str = arguments.get("output_path")
    if output_path_str:
        output_path = Path(output_path_str)
    else:
        out_ext = _pandoc_format_to_ext(to_format)
        output_path = input_path.with_suffix(out_ext)

    os.makedirs(str(output_path.parent), exist_ok=True)

    pandoc = PandocService()
    try:
        result_path = pandoc.convert(
            input_path,
            output_path,
            from_format=from_format,
            to_format=to_format,
        )
    except ConversionError as exc:
        return {"error": str(exc)}

    size = result_path.stat().st_size
    return {
        "input_path": str(input_path),
        "output_path": str(result_path),
        "from_format": from_format or pandoc.detect_format(input_path) or "auto",
        "to_format": to_format,
        "size_bytes": size,
    }


async def _create_drive_folder(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new folder in Google Drive."""
    name = arguments["name"]
    parent_id = arguments.get("parent_id")

    url = f"{DRIVE_API_BASE}/files"
    metadata: dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    if parent_id:
        metadata["parents"] = [parent_id]

    response = await svc._make_request(
        "POST", url, params={"supportsAllDrives": "true"}, json_data=metadata
    )

    return {
        "status": "folder_created",
        "id": response.get("id"),
        "name": response.get("name"),
        "mimeType": response.get("mimeType"),
    }


async def _upload_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Upload a file to Google Drive (text or binary)."""
    import mimetypes
    import os

    local_path = arguments.get("local_path")
    mime_type = arguments.get("mime_type", "text/plain")
    parent_id = arguments.get("parent_id")

    if local_path:
        with open(local_path, "rb") as f:
            file_bytes = f.read()
        if not arguments.get("mime_type"):
            detected, _ = mimetypes.guess_type(local_path)
            mime_type = detected or "application/octet-stream"
        name = arguments.get("name") or os.path.basename(local_path)
    else:
        content = arguments.get("content")
        if content is None:
            raise ValueError("Either 'local_path' or 'content' must be provided")
        name = arguments.get("name", "untitled")
        file_bytes = content.encode("utf-8")

    metadata: dict[str, Any] = {"name": name, "mimeType": mime_type}
    if parent_id:
        metadata["parents"] = [parent_id]

    boundary = secrets.token_hex(16).encode()
    metadata_part = (
        b"--" + boundary + b"\r\n"
        b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        + json.dumps(metadata).encode("utf-8")
        + b"\r\n"
    )
    file_part = (
        b"--" + boundary + b"\r\n"
        b"Content-Type: " + mime_type.encode("utf-8") + b"\r\n\r\n" + file_bytes + b"\r\n"
    )
    closing = b"--" + boundary + b"--"
    body = metadata_part + file_part + closing

    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true"

    response = await svc._make_raw_request(
        "POST",
        upload_url,
        content=body,
        headers={"Content-Type": f"multipart/related; boundary={boundary.decode()}"},
        timeout=60.0,
    )
    result = response.json()

    return {
        "status": "uploaded",
        "id": result.get("id"),
        "name": result.get("name"),
        "mimeType": result.get("mimeType"),
    }


async def _delete_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a file or folder from Google Drive."""
    file_id = arguments["file_id"]

    url = f"{DRIVE_API_BASE}/files/{file_id}?supportsAllDrives=true"
    await svc._make_delete_request(url)

    return {"status": "deleted", "file_id": file_id}


async def _move_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Move a file to a different folder in Google Drive."""
    file_id = arguments["file_id"]
    new_parent_id = arguments["new_parent_id"]

    get_url = f"{DRIVE_API_BASE}/files/{file_id}?fields=parents&supportsAllDrives=true"
    file_info = await svc._make_request("GET", get_url)
    current_parents = file_info.get("parents", [])

    update_url = f"{DRIVE_API_BASE}/files/{file_id}"
    params = {
        "addParents": new_parent_id,
        "removeParents": ",".join(current_parents),
        "fields": "id,name,parents",
        "supportsAllDrives": "true",
    }

    response = await svc._make_raw_request("PATCH", update_url, params=params)
    result = response.json()

    return {
        "status": "moved",
        "id": result.get("id"),
        "name": result.get("name"),
        "new_parents": result.get("parents", []),
    }


async def _copy_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a copy of a file in Google Drive."""
    file_id = arguments["file_id"]
    name = arguments.get("name")
    parent_id = arguments.get("parent_id")

    url = f"{DRIVE_API_BASE}/files/{file_id}/copy"

    copy_body: dict[str, Any] = {}
    if name:
        copy_body["name"] = name
    if parent_id:
        copy_body["parents"] = [parent_id]

    params = {"fields": "id,name,mimeType,parents", "supportsAllDrives": "true"}
    response = await svc._make_request(
        "POST", url, params=params, json_data=copy_body if copy_body else None
    )

    return {
        "status": "copied",
        "id": response.get("id"),
        "name": response.get("name"),
        "mimeType": response.get("mimeType"),
        "parents": response.get("parents", []),
    }


async def _rename_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Rename a file or folder in Google Drive."""
    file_id = arguments["file_id"]
    new_name = arguments["new_name"]

    url = f"{DRIVE_API_BASE}/files/{file_id}"
    params = {"fields": "id,name,mimeType", "supportsAllDrives": "true"}

    response = await svc._make_request("PATCH", url, params=params, json_data={"name": new_name})

    return {
        "status": "renamed",
        "id": response.get("id"),
        "name": response.get("name"),
        "mimeType": response.get("mimeType"),
    }


async def _list_file_permissions(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all permissions for a Drive file or folder."""
    file_id = arguments["file_id"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    response = await svc._make_request("GET", url, params={"fields": "*"})

    permissions = []
    for perm in response.get("permissions", []):
        perm_info: dict[str, Any] = {
            "permission_id": perm.get("id"),
            "type": perm.get("type"),
            "role": perm.get("role"),
        }
        if perm.get("emailAddress"):
            perm_info["email_address"] = perm.get("emailAddress")
        if perm.get("displayName"):
            perm_info["display_name"] = perm.get("displayName")
        if perm.get("domain"):
            perm_info["domain"] = perm.get("domain")
        permissions.append(perm_info)

    return {
        "status": "success",
        "file_id": file_id,
        "permissions": permissions,
        "count": len(permissions),
    }


async def _share_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Share a Drive file or folder with a user, group, domain, or anyone."""
    file_id = arguments["file_id"]
    perm_type = arguments["type"]
    role = arguments["role"]
    email_address = arguments.get("email_address")
    domain = arguments.get("domain")
    send_notification = arguments.get("send_notification", True)

    if perm_type in ("user", "group") and not email_address:
        return {
            "status": "error",
            "error": f"email_address is required for type '{perm_type}'",
        }
    if perm_type == "domain" and not domain:
        return {
            "status": "error",
            "error": "domain is required for type 'domain'",
        }

    permission: dict[str, Any] = {
        "type": perm_type,
        "role": role,
    }
    if email_address:
        permission["emailAddress"] = email_address
    if domain:
        permission["domain"] = domain

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    params = {"sendNotificationEmail": str(send_notification).lower()}

    response = await svc._make_request("POST", url, params=params, json_data=permission)

    result: dict[str, Any] = {
        "status": "shared",
        "file_id": file_id,
        "permission_id": response.get("id"),
        "type": response.get("type"),
        "role": response.get("role"),
    }
    if response.get("emailAddress"):
        result["email_address"] = response.get("emailAddress")
    if response.get("domain"):
        result["domain"] = response.get("domain")

    return result


async def _update_file_permission(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update an existing permission's role on a Drive file."""
    file_id = arguments["file_id"]
    permission_id = arguments["permission_id"]
    role = arguments["role"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions/{permission_id}"
    response = await svc._make_request("PATCH", url, json_data={"role": role})

    return {
        "status": "updated",
        "file_id": file_id,
        "permission_id": response.get("id"),
        "role": response.get("role"),
        "type": response.get("type"),
    }


async def _remove_file_permission(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Remove a permission from a Drive file or folder."""
    file_id = arguments["file_id"]
    permission_id = arguments["permission_id"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions/{permission_id}"
    await svc._make_delete_request(url)

    return {
        "status": "removed",
        "file_id": file_id,
        "permission_id": permission_id,
    }


async def _transfer_file_ownership(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Transfer ownership of a Drive file to another user."""
    file_id = arguments["file_id"]
    new_owner_email = arguments["new_owner_email"]

    permission = {
        "type": "user",
        "role": "owner",
        "emailAddress": new_owner_email,
    }

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    response = await svc._make_request(
        "POST", url, params={"transferOwnership": "true"}, json_data=permission
    )

    return {
        "status": "ownership_transferred",
        "file_id": file_id,
        "new_owner": new_owner_email,
        "permission_id": response.get("id"),
    }


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


# =============================================================================
# Handler registry
# =============================================================================


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Drive handlers."""
    return {
        "search_drive_files": lambda args: _search_drive_files(svc, args),
        "get_drive_file_content": lambda args: _get_drive_file_content(svc, args),
        "convert_document": lambda args: _convert_document(svc, args),
        "create_drive_folder": lambda args: _create_drive_folder(svc, args),
        "upload_drive_file": lambda args: _upload_drive_file(svc, args),
        "delete_drive_file": lambda args: _delete_drive_file(svc, args),
        "move_drive_file": lambda args: _move_drive_file(svc, args),
        "copy_drive_file": lambda args: _copy_drive_file(svc, args),
        "rename_drive_file": lambda args: _rename_drive_file(svc, args),
        "list_file_permissions": lambda args: _list_file_permissions(svc, args),
        "share_file": lambda args: _share_file(svc, args),
        "update_file_permission": lambda args: _update_file_permission(svc, args),
        "remove_file_permission": lambda args: _remove_file_permission(svc, args),
        "transfer_file_ownership": lambda args: _transfer_file_ownership(svc, args),
        "list_drive_contents": lambda args: _list_drive_contents(svc, args),
        "download_drive_folder": lambda args: _download_drive_folder(svc, args),
        "upload_to_drive": lambda args: _upload_to_drive(svc, args),
        "sync_drive_folder": lambda args: _sync_drive_folder(svc, args),
    }
