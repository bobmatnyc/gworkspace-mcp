"""Google Drive files sub-module: search, get, convert, and manage files."""

from __future__ import annotations

import json
import logging
import secrets
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DRIVE_API_BASE

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
        name="manage_drive_file",
        description=(
            "Create, upload, delete, move, copy, or rename files and folders in Google Drive. "
            "Actions: 'create_folder' creates a new folder; 'upload' uploads a local file or inline text; "
            "'delete' removes a file/folder; 'move' moves a file to a different folder; "
            "'copy' duplicates a file; 'rename' renames a file or folder."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create_folder", "upload", "delete", "move", "copy", "rename"],
                    "description": "Operation to perform.",
                },
                "file_id": {
                    "type": "string",
                    "description": "File or folder ID. Required for delete, move, copy, rename.",
                },
                "name": {
                    "type": "string",
                    "description": "Name for the file/folder. Required for create_folder and rename; optional for upload and copy.",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent folder ID. Optional for create_folder, upload, and copy.",
                },
                "new_parent_id": {
                    "type": "string",
                    "description": "Destination folder ID. Required for move.",
                },
                "local_path": {
                    "type": "string",
                    "description": "Absolute path to a local file to upload. Used with action='upload'.",
                },
                "content": {
                    "type": "string",
                    "description": "Inline text content to upload. Used with action='upload' when local_path is not provided.",
                },
                "mime_type": {
                    "type": "string",
                    "description": "MIME type for upload. Auto-detected from local_path if omitted; defaults to 'text/plain' for inline content.",
                },
            },
            "required": ["action"],
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


# =============================================================================
# Handler functions
# =============================================================================


async def _search_drive_files(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search Google Drive files."""
    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 10)

    normalized_query = _normalize_drive_query(query)

    _FIELDS = (
        "files(id,name,mimeType,size,modifiedTime,parents,webViewLink,thumbnailLink),nextPageToken"
    )
    url = f"{DRIVE_API_BASE}/files"
    params = {
        "q": normalized_query,
        "pageSize": max_results,
        "fields": _FIELDS,
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
                "parents": item.get("parents", []),
                "webViewLink": item.get("webViewLink"),
                "thumbnailLink": item.get("thumbnailLink"),
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
    _: BaseService,
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


async def _manage_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch create_folder, upload, delete, move, copy, or rename actions."""
    action = arguments.get("action")

    if action == "create_folder":
        return await _create_drive_folder(svc, arguments)
    elif action == "upload":
        return await _upload_drive_file(svc, arguments)
    elif action == "delete":
        return await _delete_drive_file(svc, arguments)
    elif action == "move":
        return await _move_drive_file(svc, arguments)
    elif action == "copy":
        return await _copy_drive_file(svc, arguments)
    elif action == "rename":
        return await _rename_drive_file(svc, arguments)
    else:
        return {
            "error": f"Unknown action '{action}'. Must be one of: create_folder, upload, delete, move, copy, rename."
        }


async def _create_drive_folder(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new folder in Google Drive."""
    name = arguments.get("name")
    if not name:
        return {"error": "name is required for action='create_folder'"}
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
            return {
                "error": "Either 'local_path' or 'content' must be provided for action='upload'"
            }
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
    file_id = arguments.get("file_id")
    if not file_id:
        return {"error": "file_id is required for action='delete'"}

    url = f"{DRIVE_API_BASE}/files/{file_id}?supportsAllDrives=true"
    await svc._make_delete_request(url)

    return {"status": "deleted", "file_id": file_id}


async def _move_drive_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Move a file to a different folder in Google Drive."""
    file_id = arguments.get("file_id")
    new_parent_id = arguments.get("new_parent_id")
    if not file_id:
        return {"error": "file_id is required for action='move'"}
    if not new_parent_id:
        return {"error": "new_parent_id is required for action='move'"}

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
    file_id = arguments.get("file_id")
    if not file_id:
        return {"error": "file_id is required for action='copy'"}
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
    file_id = arguments.get("file_id")
    new_name = arguments.get("name")
    if not file_id:
        return {"error": "file_id is required for action='rename'"}
    if not new_name:
        return {"error": "name is required for action='rename'"}

    url = f"{DRIVE_API_BASE}/files/{file_id}"
    params = {"fields": "id,name,mimeType", "supportsAllDrives": "true"}

    response = await svc._make_request("PATCH", url, params=params, json_data={"name": new_name})

    return {
        "status": "renamed",
        "id": response.get("id"),
        "name": response.get("name"),
        "mimeType": response.get("mimeType"),
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Drive file handlers."""
    return {
        "search_drive_files": lambda args: _search_drive_files(svc, args),
        "get_drive_file_content": lambda args: _get_drive_file_content(svc, args),
        "convert_document": lambda args: _convert_document(svc, args),
        "manage_drive_file": lambda args: _manage_drive_file(svc, args),
    }
