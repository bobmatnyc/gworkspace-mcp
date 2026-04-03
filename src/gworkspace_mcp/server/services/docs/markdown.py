"""Google Docs markdown sub-module: upload markdown, render mermaid, publish."""

from __future__ import annotations

import json
import logging
import secrets
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE, DRIVE_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="upload_markdown_as_doc",
        description="Convert Markdown content to Google Docs format and upload to Drive. Uses pandoc for conversion. Supports automatic rendering of mermaid diagrams when render_mermaid is enabled.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Document name (without extension)",
                },
                "markdown_content": {
                    "type": "string",
                    "description": "Markdown content to convert",
                },
                "parent_id": {
                    "type": "string",
                    "description": "Parent folder ID (optional)",
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format: 'gdoc' (Google Docs) or 'docx' (Microsoft Word)",
                    "default": "gdoc",
                    "enum": ["gdoc", "docx"],
                },
                "render_mermaid": {
                    "type": "boolean",
                    "description": "Automatically render mermaid code blocks to images",
                    "default": False,
                },
                "mermaid_theme": {
                    "type": "string",
                    "description": "Mermaid theme when render_mermaid is enabled",
                    "default": "default",
                    "enum": ["default", "forest", "dark", "neutral"],
                },
            },
            "required": ["name", "markdown_content"],
        },
    ),
    Tool(
        name="render_mermaid_to_doc",
        description="Render Mermaid diagram code to an image and insert it into a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID where the image will be inserted",
                },
                "mermaid_code": {
                    "type": "string",
                    "description": "Mermaid diagram code",
                },
                "insert_index": {
                    "type": "integer",
                    "description": "Character index where to insert the image. If not provided, appends to end.",
                },
                "image_format": {
                    "type": "string",
                    "description": "Output image format: 'svg' or 'png'",
                    "default": "svg",
                    "enum": ["svg", "png"],
                },
                "width_pt": {
                    "type": "integer",
                    "description": "Image width in points (optional)",
                },
                "height_pt": {
                    "type": "integer",
                    "description": "Image height in points (optional)",
                },
                "theme": {
                    "type": "string",
                    "description": "Mermaid theme",
                    "default": "default",
                    "enum": ["default", "forest", "dark", "neutral"],
                },
                "background": {
                    "type": "string",
                    "description": "Background color: 'white', 'transparent', or any CSS color",
                    "default": "white",
                },
            },
            "required": ["document_id", "mermaid_code"],
        },
    ),
    Tool(
        name="publish_markdown_to_doc",
        description="Publish markdown content to Google Docs with enhanced mermaid diagram support.",
        inputSchema={
            "type": "object",
            "properties": {
                "markdown_content": {
                    "type": "string",
                    "description": "Markdown content to publish",
                },
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
                "folder_id": {
                    "type": "string",
                    "description": "Parent folder ID (optional)",
                },
                "render_mermaid": {
                    "type": "boolean",
                    "description": "Auto-detect and render mermaid code blocks as images",
                    "default": True,
                },
                "mermaid_theme": {
                    "type": "string",
                    "description": "Mermaid theme for diagrams",
                    "default": "default",
                    "enum": ["default", "forest", "dark", "neutral"],
                },
                "mermaid_background": {
                    "type": "string",
                    "description": "Background color for diagrams",
                    "default": "transparent",
                },
                "preserve_mermaid_source": {
                    "type": "boolean",
                    "description": "Add original mermaid source as document comments for future editing",
                    "default": True,
                },
            },
            "required": ["markdown_content", "title"],
        },
    ),
]


# =============================================================================
# Helper functions
# =============================================================================


def _clean_docx_for_gdocs(docx_path: Any) -> None:
    """Clean DOCX file for better Google Docs compatibility (Arial font, no bookmarks)."""
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(str(docx_path))

    for element in list(doc.element.iter()):
        tag = element.tag
        if tag.endswith("bookmarkStart") or tag.endswith("bookmarkEnd"):
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)

    for para in doc.paragraphs:
        for run in para.runs:
            run.font.name = "Arial"
            r_element = run._element
            rpr = r_element.get_or_add_rPr()
            rfonts = rpr.get_or_add_rFonts()
            rfonts.set(qn("w:eastAsia"), "Arial")
            rfonts.set(qn("w:ascii"), "Arial")
            rfonts.set(qn("w:hAnsi"), "Arial")
            rfonts.set(qn("w:cs"), "Arial")

    for style in doc.styles:
        if hasattr(style, "font") and style.font is not None:
            style.font.name = "Arial"

    doc.save(str(docx_path))


# =============================================================================
# Handler functions
# =============================================================================


async def _upload_markdown_as_doc(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    import base64
    import re
    import tempfile
    from pathlib import Path

    from gworkspace_mcp.conversion.pandoc_service import ConversionError, PandocService

    name = arguments["name"]
    markdown_content = arguments["markdown_content"]
    parent_id = arguments.get("parent_id")
    output_format = arguments.get("output_format", "gdoc")
    render_mermaid = arguments.get("render_mermaid", False)
    mermaid_theme = arguments.get("mermaid_theme", "default")

    pandoc = PandocService()
    try:
        pandoc._require_pandoc()
    except ConversionError as err:
        raise RuntimeError(str(err)) from err

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / "input.md"
        output_path = tmpdir_path / "output.docx"

        processed_content = markdown_content
        mermaid_count = 0

        if render_mermaid:
            mermaid_pattern = r"```mermaid\s*\n([\s\S]*?)\n```"
            mermaid_blocks = re.findall(mermaid_pattern, markdown_content)

            for i, mermaid_code in enumerate(mermaid_blocks):
                mermaid_output = tmpdir_path / f"mermaid_{i}.png"
                try:
                    image_bytes = await svc._render_mermaid_image(
                        mermaid_code,
                        output_format="png",
                        theme=mermaid_theme,
                        background="white",
                    )
                    mermaid_output.write_bytes(image_bytes)
                    original_block = f"```mermaid\n{mermaid_code}\n```"
                    image_ref = f"![Diagram {i + 1}]({mermaid_output})"
                    processed_content = processed_content.replace(original_block, image_ref, 1)
                    mermaid_count += 1
                    logger.info("Rendered mermaid diagram %d: %s", i + 1, mermaid_output)
                except RuntimeError as e:
                    logger.warning("Failed to render mermaid diagram %d: %s", i + 1, e)

        input_path.write_text(processed_content, encoding="utf-8")

        try:
            pandoc.markdown_to_docx(input_path, output_path)
        except ConversionError as e:
            raise RuntimeError(f"pandoc conversion failed: {e}") from e

        _clean_docx_for_gdocs(output_path)

        docx_content = output_path.read_bytes()

    if output_format == "gdoc":
        metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.document",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&convert=true&supportsAllDrives=true"

        boundary = secrets.token_hex(16)
        docx_base64 = base64.b64encode(docx_content).decode("ascii")

        body_str = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n"
            f"Content-Transfer-Encoding: base64\r\n\r\n"
            f"{docx_base64}\r\n"
            f"--{boundary}--"
        )

        response = await svc._make_raw_request(
            "POST",
            upload_url,
            content=body_str.encode("utf-8"),
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
            timeout=120.0,
        )
        result = response.json()

        response_data: dict[str, Any] = {
            "status": "created",
            "format": "google_docs",
            "id": result.get("id"),
            "name": result.get("name"),
            "mimeType": result.get("mimeType"),
        }
        if render_mermaid:
            response_data["mermaid_diagrams_rendered"] = mermaid_count
        return response_data

    # Upload as DOCX
    metadata = {"name": f"{name}.docx"}
    if parent_id:
        metadata["parents"] = [parent_id]

    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true"
    boundary = secrets.token_hex(16)

    body_start = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n"
    ).encode()
    body_end = f"\r\n--{boundary}--".encode()

    full_body = body_start + docx_content + body_end

    response = await svc._make_raw_request(
        "POST",
        upload_url,
        content=full_body,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        timeout=120.0,
    )
    result = response.json()

    response_data = {
        "status": "uploaded",
        "format": "docx",
        "id": result.get("id"),
        "name": result.get("name"),
        "mimeType": result.get("mimeType"),
    }
    if render_mermaid:
        response_data["mermaid_diagrams_rendered"] = mermaid_count
    return response_data


async def _render_mermaid_to_doc(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    mermaid_code = arguments["mermaid_code"]
    insert_index = arguments.get("insert_index")
    image_format = arguments.get("image_format", "svg")
    width_pt = arguments.get("width_pt")
    height_pt = arguments.get("height_pt")
    theme = arguments.get("theme", "default")
    background = arguments.get("background", "white")

    image_content = await svc._render_mermaid_image(
        mermaid_code, output_format=image_format, theme=theme, background=background
    )

    metadata: dict[str, Any] = {
        "name": f"mermaid-diagram-{document_id[:8]}.{image_format}",
        "mimeType": f"image/{image_format}+xml"
        if image_format == "svg"
        else f"image/{image_format}",
    }

    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true"
    boundary = secrets.token_hex(16)

    body_start = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {metadata['mimeType']}\r\n\r\n"
    ).encode()
    body_end = f"\r\n--{boundary}--".encode()

    full_body = body_start + image_content + body_end

    response = await svc._make_raw_request(
        "POST",
        upload_url,
        content=full_body,
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        timeout=60.0,
    )
    upload_result = response.json()
    file_id = upload_result.get("id")
    logger.info("Uploaded Mermaid image to Drive: %s", file_id)

    permission_url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    permission_body = {"role": "reader", "type": "anyone"}
    await svc._make_request("POST", permission_url, json_data=permission_body)

    public_url = f"https://drive.google.com/uc?export=view&id={file_id}"

    if insert_index is None:
        get_url = f"{DOCS_API_BASE}/documents/{document_id}"
        doc = await svc._make_request("GET", get_url)
        content = doc.get("body", {}).get("content", [])
        if content:
            last_element = content[-1]
            end_index = last_element.get("endIndex", 1)
            insert_index = max(1, end_index - 1)
        else:
            insert_index = 1

    update_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    image_request: dict[str, Any] = {
        "insertInlineImage": {
            "uri": public_url,
            "location": {"index": insert_index},
        }
    }

    if width_pt or height_pt:
        object_size: dict[str, Any] = {}
        if width_pt:
            object_size["width"] = {"magnitude": width_pt, "unit": "PT"}
        if height_pt:
            object_size["height"] = {"magnitude": height_pt, "unit": "PT"}
        image_request["insertInlineImage"]["objectSize"] = object_size

    body = {"requests": [image_request]}
    await svc._make_request("POST", update_url, json_data=body)

    return {
        "status": "success",
        "imageUrl": public_url,
        "fileId": file_id,
        "insertIndex": insert_index,
        "documentId": document_id,
        "format": image_format,
    }


async def _publish_markdown_to_doc(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    import base64
    import re
    import tempfile
    from pathlib import Path

    from gworkspace_mcp.conversion.pandoc_service import ConversionError, PandocService

    markdown_content = arguments["markdown_content"]
    title = arguments["title"]
    folder_id = arguments.get("folder_id")
    render_mermaid = arguments.get("render_mermaid", True)
    mermaid_theme = arguments.get("mermaid_theme", "default")
    mermaid_background = arguments.get("mermaid_background", "transparent")
    preserve_mermaid_source = arguments.get("preserve_mermaid_source", True)

    _pandoc_svc = PandocService()
    try:
        _pandoc_svc._require_pandoc()
    except ConversionError as err:
        raise RuntimeError(str(err)) from err

    mermaid_sources: list[tuple[int, str]] = []
    processed_content = markdown_content
    mermaid_count = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / "input.md"
        output_path = tmpdir_path / "output.docx"

        if render_mermaid:
            mermaid_pattern = r"```mermaid\s*\n([\s\S]*?)\n```"
            mermaid_blocks = re.findall(mermaid_pattern, markdown_content)

            for i, mermaid_code in enumerate(mermaid_blocks):
                mermaid_output = tmpdir_path / f"mermaid_{i}.png"
                try:
                    image_bytes = await svc._render_mermaid_image(
                        mermaid_code,
                        output_format="png",
                        theme=mermaid_theme,
                        background=mermaid_background,
                    )
                    mermaid_output.write_bytes(image_bytes)
                    if preserve_mermaid_source:
                        mermaid_sources.append((i + 1, mermaid_code.strip()))
                    original_block = f"```mermaid\n{mermaid_code}\n```"
                    image_ref = f"![Diagram {i + 1}]({mermaid_output})"
                    processed_content = processed_content.replace(original_block, image_ref, 1)
                    mermaid_count += 1
                    logger.info("Rendered mermaid diagram %d: %s", i + 1, mermaid_output)
                except RuntimeError as e:
                    logger.warning("Failed to render mermaid diagram %d: %s", i + 1, e)

        input_path.write_text(processed_content, encoding="utf-8")

        try:
            _pandoc_svc.markdown_to_docx(input_path, output_path)
        except ConversionError as e:
            raise RuntimeError(f"pandoc conversion failed: {e}") from e

        _clean_docx_for_gdocs(output_path)
        docx_content = output_path.read_bytes()

    metadata: dict[str, Any] = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document",
    }
    if folder_id:
        metadata["parents"] = [folder_id]

    upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&convert=true&supportsAllDrives=true"
    boundary = secrets.token_hex(16)
    docx_base64 = base64.b64encode(docx_content).decode("ascii")

    body_str = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: application/vnd.openxmlformats-officedocument."
        f"wordprocessingml.document\r\n"
        f"Content-Transfer-Encoding: base64\r\n\r\n"
        f"{docx_base64}\r\n"
        f"--{boundary}--"
    )

    response = await svc._make_raw_request(
        "POST",
        upload_url,
        content=body_str.encode("utf-8"),
        headers={"Content-Type": f"multipart/related; boundary={boundary}"},
        timeout=120.0,
    )
    result = response.json()
    document_id = result.get("id")

    comments_added = 0
    if preserve_mermaid_source and mermaid_sources:
        for diagram_num, source_code in mermaid_sources:
            try:
                comment_content = (
                    f"[Mermaid Source - Diagram {diagram_num}]\n```mermaid\n{source_code}\n```"
                )
                comment_url = f"{DRIVE_API_BASE}/files/{document_id}/comments"
                comment_body = {"content": comment_content}
                await svc._make_request("POST", comment_url, json_data=comment_body)
                comments_added += 1
                logger.info("Added mermaid source comment for diagram %d", diagram_num)
            except Exception as e:
                logger.warning("Failed to add comment for diagram %d: %s", diagram_num, e)

    return {
        "status": "published",
        "document_id": document_id,
        "title": result.get("name"),
        "mimeType": result.get("mimeType"),
        "mermaid_diagrams_rendered": mermaid_count,
        "mermaid_source_comments_added": comments_added,
        "mermaid_theme": mermaid_theme if render_mermaid else None,
        "mermaid_background": mermaid_background if render_mermaid else None,
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs markdown handlers."""
    return {
        "upload_markdown_as_doc": lambda args: _upload_markdown_as_doc(svc, args),
        "render_mermaid_to_doc": lambda args: _render_mermaid_to_doc(svc, args),
        "publish_markdown_to_doc": lambda args: _publish_markdown_to_doc(svc, args),
    }
