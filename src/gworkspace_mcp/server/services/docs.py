"""Google Docs service module."""

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
        name="list_document_comments",
        description="List all comments on a Google Docs, Sheets, or Slides file. Returns comment content, author, timestamps, resolved status, and replies.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "include_deleted": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include deleted comments",
                },
                "max_results": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of comments to return",
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="add_document_comment",
        description="Add a new comment to a Google Docs, Sheets, or Slides file. Comments appear in the document's comment sidebar. Write concise, actionable comments.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "content": {
                    "type": "string",
                    "description": "The comment text.",
                },
                "anchor": {
                    "type": "string",
                    "description": "Optional JSON string specifying the anchor location in the document (for anchored comments)",
                },
            },
            "required": ["file_id", "content"],
        },
    ),
    Tool(
        name="reply_to_comment",
        description="Reply to an existing comment on a Google Docs, Sheets, or Slides file.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "comment_id": {
                    "type": "string",
                    "description": "The ID of the comment to reply to (from list_document_comments)",
                },
                "content": {
                    "type": "string",
                    "description": "The reply text.",
                },
            },
            "required": ["file_id", "comment_id", "content"],
        },
    ),
    Tool(
        name="create_document",
        description="Create a new Google Doc",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="append_to_document",
        description="Append text to an existing Google Doc",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "text": {
                    "type": "string",
                    "description": "Text to append",
                },
            },
            "required": ["document_id", "text"],
        },
    ),
    Tool(
        name="get_document",
        description="Get the content and structure of a Google Doc. Optionally include tab content for documents with multiple tabs.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "include_tabs_content": {
                    "type": "boolean",
                    "description": "Whether to include tab content (default: False). Set to True for documents with tabs.",
                    "default": False,
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="list_document_tabs",
        description="List all tabs in a Google Doc with their metadata (tabId, title, index, nestingLevel, iconEmoji, parentTabId).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="get_tab_content",
        description="Get the content from a specific tab in a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID (from list_document_tabs)",
                },
            },
            "required": ["document_id", "tab_id"],
        },
    ),
    Tool(
        name="create_document_tab",
        description="Create a new tab in a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "title": {
                    "type": "string",
                    "description": "Tab title",
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "Icon emoji for the tab (optional)",
                },
                "parent_tab_id": {
                    "type": "string",
                    "description": "Parent tab ID for nested tabs (optional)",
                },
                "index": {
                    "type": "integer",
                    "description": "Position index for the tab (optional)",
                },
            },
            "required": ["document_id", "title"],
        },
    ),
    Tool(
        name="update_tab_properties",
        description="Update properties of an existing tab (title, iconEmoji).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID to update (from list_document_tabs)",
                },
                "title": {
                    "type": "string",
                    "description": "New tab title (optional)",
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "New icon emoji (optional)",
                },
            },
            "required": ["document_id", "tab_id"],
        },
    ),
    Tool(
        name="move_tab",
        description="Move a tab to a new position or change its parent (nesting level).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID to move (from list_document_tabs)",
                },
                "new_parent_tab_id": {
                    "type": "string",
                    "description": "New parent tab ID (optional). Use empty string to move to root level.",
                },
                "new_index": {
                    "type": "integer",
                    "description": "New position index (optional)",
                },
            },
            "required": ["document_id", "tab_id"],
        },
    ),
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
    Tool(
        name="format_text_in_document",
        description="Apply text formatting to a specific range in a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "start_index": {"type": "integer", "description": "Start character index"},
                "end_index": {"type": "integer", "description": "End character index"},
                "bold": {"type": "boolean", "description": "Apply bold formatting (optional)"},
                "italic": {"type": "boolean", "description": "Apply italic formatting (optional)"},
                "underline": {
                    "type": "boolean",
                    "description": "Apply underline formatting (optional)",
                },
                "font_size": {"type": "number", "description": "Font size in points (optional)"},
                "font_family": {"type": "string", "description": "Font family name (optional)"},
                "text_color": {
                    "type": "object",
                    "description": "Text color in RGB format",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "required": ["document_id", "start_index", "end_index"],
        },
    ),
    Tool(
        name="format_paragraph_in_document",
        description="Apply paragraph formatting to a specific range in a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "start_index": {"type": "integer", "description": "Start character index"},
                "end_index": {"type": "integer", "description": "End character index"},
                "alignment": {
                    "type": "string",
                    "enum": ["LEFT", "CENTER", "RIGHT", "JUSTIFY"],
                },
                "line_spacing": {"type": "number", "description": "Line spacing multiplier"},
                "indent_first_line": {
                    "type": "number",
                    "description": "First line indent in points",
                },
                "indent_start": {"type": "number", "description": "Left indent in points"},
                "indent_end": {"type": "number", "description": "Right indent in points"},
            },
            "required": ["document_id", "start_index", "end_index"],
        },
    ),
    Tool(
        name="create_list_in_document",
        description="Create a bulleted or numbered list in a Google Doc at the specified location.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "insert_index": {
                    "type": "integer",
                    "description": "Character index where to insert the list",
                },
                "list_type": {
                    "type": "string",
                    "enum": ["BULLETED", "NUMBERED"],
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["document_id", "insert_index", "list_type", "items"],
        },
    ),
    Tool(
        name="insert_table_in_document",
        description="Insert a table with specified content into a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "insert_index": {
                    "type": "integer",
                    "description": "Character index where to insert the table",
                },
                "rows": {"type": "integer", "minimum": 1},
                "columns": {"type": "integer", "minimum": 1},
                "data": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "header_row": {"type": "boolean", "default": True},
            },
            "required": ["document_id", "insert_index", "rows", "columns"],
        },
    ),
    Tool(
        name="apply_heading_style",
        description="Apply heading styles to text in a Google Doc (Heading 1-6, Normal text, Title, Subtitle).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "start_index": {"type": "integer"},
                "end_index": {"type": "integer"},
                "heading_style": {
                    "type": "string",
                    "enum": [
                        "NORMAL_TEXT",
                        "TITLE",
                        "SUBTITLE",
                        "HEADING_1",
                        "HEADING_2",
                        "HEADING_3",
                        "HEADING_4",
                        "HEADING_5",
                        "HEADING_6",
                    ],
                },
            },
            "required": ["document_id", "start_index", "end_index", "heading_style"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _extract_doc_text(body: dict[str, Any]) -> str:
    """Extract plain text from a Google Docs body structure."""
    text_parts = []
    for element in body.get("content", []):
        if "paragraph" in element:
            for para_element in element["paragraph"].get("elements", []):
                if "textRun" in para_element:
                    text_parts.append(para_element["textRun"].get("content", ""))
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    cell_text = _extract_doc_text(cell)
                    if cell_text:
                        text_parts.append(cell_text)
                        text_parts.append("\t")
                text_parts.append("\n")
    return "".join(text_parts)


def _format_tabs(tabs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format tab information for response."""
    formatted_tabs = []
    for tab in tabs:
        tab_props = tab.get("tabProperties", {})
        formatted_tab: dict[str, Any] = {
            "tab_id": tab_props.get("tabId"),
            "title": tab_props.get("title", ""),
            "index": tab_props.get("index", 0),
            "nesting_level": tab_props.get("nestingLevel", 0),
        }
        if "iconEmoji" in tab_props:
            formatted_tab["icon_emoji"] = tab_props["iconEmoji"]
        if "parentTabId" in tab_props:
            formatted_tab["parent_tab_id"] = tab_props["parentTabId"]
        formatted_tabs.append(formatted_tab)
    return formatted_tabs


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


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _list_document_comments(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    file_id = arguments["file_id"]
    include_deleted = arguments.get("include_deleted", False)
    max_results = arguments.get("max_results", 100)

    url = f"{DRIVE_API_BASE}/files/{file_id}/comments"
    params = {
        "fields": "comments(id,content,author(displayName,emailAddress),createdTime,modifiedTime,resolved,deleted,quotedFileContent,replies(id,content,author(displayName,emailAddress),createdTime,modifiedTime,deleted))",
        "pageSize": min(max_results, 100),
        "includeDeleted": str(include_deleted).lower(),
    }

    response = await svc._make_request("GET", url, params=params)

    comments = response.get("comments", [])
    if not comments:
        return {"comments": [], "count": 0, "message": "No comments found on this document."}

    formatted_comments = []
    for comment in comments:
        author = comment.get("author", {})
        quoted = comment.get("quotedFileContent", {})

        formatted_comment: dict[str, Any] = {
            "id": comment.get("id"),
            "author_name": author.get("displayName", "Unknown"),
            "author_email": author.get("emailAddress", ""),
            "created_time": comment.get("createdTime", ""),
            "modified_time": comment.get("modifiedTime", ""),
            "resolved": comment.get("resolved", False),
            "deleted": comment.get("deleted", False),
            "content": comment.get("content", ""),
        }

        if quoted.get("value"):
            quoted_text = quoted.get("value", "")
            if len(quoted_text) > 200:
                quoted_text = quoted_text[:200] + "..."
            formatted_comment["quoted_text"] = quoted_text

        replies = comment.get("replies", [])
        if replies:
            formatted_replies = []
            for reply in replies:
                reply_author = reply.get("author", {})
                formatted_replies.append(
                    {
                        "id": reply.get("id"),
                        "author_name": reply_author.get("displayName", "Unknown"),
                        "author_email": reply_author.get("emailAddress", ""),
                        "created_time": reply.get("createdTime", ""),
                        "modified_time": reply.get("modifiedTime", ""),
                        "deleted": reply.get("deleted", False),
                        "content": reply.get("content", ""),
                    }
                )
            formatted_comment["replies"] = formatted_replies
            formatted_comment["reply_count"] = len(formatted_replies)

        formatted_comments.append(formatted_comment)

    return {"comments": formatted_comments, "count": len(formatted_comments)}


async def _add_document_comment(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    file_id = arguments["file_id"]
    content = arguments["content"]
    anchor = arguments.get("anchor")

    url = f"{DRIVE_API_BASE}/files/{file_id}/comments"
    params = {
        "fields": "id,content,author(displayName,emailAddress),createdTime,modifiedTime,resolved",
    }

    body: dict[str, Any] = {"content": content}
    if anchor:
        try:
            body["anchor"] = json.loads(anchor) if isinstance(anchor, str) else anchor
        except json.JSONDecodeError:
            body["anchor"] = anchor

    response = await svc._make_request("POST", url, params=params, json_data=body)

    author = response.get("author", {})
    return {
        "id": response.get("id"),
        "content": response.get("content", ""),
        "author_name": author.get("displayName", "Unknown"),
        "author_email": author.get("emailAddress", ""),
        "created_time": response.get("createdTime", ""),
        "modified_time": response.get("modifiedTime", ""),
        "resolved": response.get("resolved", False),
        "message": "Comment added successfully.",
    }


async def _reply_to_comment(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    file_id = arguments["file_id"]
    comment_id = arguments["comment_id"]
    content = arguments["content"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/comments/{comment_id}/replies"
    params = {
        "fields": "id,content,author(displayName,emailAddress),createdTime,modifiedTime",
    }
    body = {"content": content}

    response = await svc._make_request("POST", url, params=params, json_data=body)

    author = response.get("author", {})
    return {
        "id": response.get("id"),
        "content": response.get("content", ""),
        "author_name": author.get("displayName", "Unknown"),
        "author_email": author.get("emailAddress", ""),
        "created_time": response.get("createdTime", ""),
        "modified_time": response.get("modifiedTime", ""),
        "comment_id": comment_id,
        "message": "Reply added successfully.",
    }


async def _create_document(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    title = arguments["title"]
    url = f"{DOCS_API_BASE}/documents"
    response = await svc._make_request("POST", url, json_data={"title": title})
    return {
        "status": "created",
        "document_id": response.get("documentId"),
        "title": response.get("title"),
        "revision_id": response.get("revisionId"),
    }


async def _append_to_document(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    text = arguments["text"]

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
    body = {
        "requests": [
            {
                "insertText": {
                    "location": {"index": insert_index},
                    "text": text,
                }
            }
        ]
    }

    await svc._make_request("POST", update_url, json_data=body)

    return {
        "status": "appended",
        "document_id": document_id,
        "text_length": len(text),
    }


async def _get_document(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    include_tabs_content = arguments.get("include_tabs_content", False)

    url = f"{DOCS_API_BASE}/documents/{document_id}"
    if include_tabs_content:
        url += "?includeTabsContent=true"

    response = await svc._make_request("GET", url)

    text_content = _extract_doc_text(response.get("body", {}))

    result: dict[str, Any] = {
        "document_id": response.get("documentId"),
        "title": response.get("title"),
        "revision_id": response.get("revisionId"),
        "text_content": text_content,
    }

    if include_tabs_content and "tabs" in response:
        result["tabs"] = _format_tabs(response["tabs"])

    return result


async def _list_document_tabs(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]

    url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
    response = await svc._make_request("GET", url)

    tabs = response.get("tabs", [])
    if not tabs:
        return {
            "document_id": document_id,
            "tabs": [],
            "count": 0,
            "message": "Document has no tabs or only a single tab",
        }

    formatted_tabs = _format_tabs(tabs)
    return {"document_id": document_id, "tabs": formatted_tabs, "count": len(formatted_tabs)}


async def _get_tab_content(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    tab_id = arguments["tab_id"]

    url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
    response = await svc._make_request("GET", url)

    tabs = response.get("tabs", [])
    target_tab = None
    for tab in tabs:
        tab_props = tab.get("tabProperties", {})
        if tab_props.get("tabId") == tab_id:
            target_tab = tab
            break

    if not target_tab:
        return {
            "error": f"Tab '{tab_id}' not found in document",
            "document_id": document_id,
            "available_tabs": [
                t.get("tabProperties", {}).get("tabId") for t in tabs if "tabProperties" in t
            ],
        }

    tab_props = target_tab.get("tabProperties", {})
    tab_body = target_tab.get("documentTab", {}).get("body", {})
    text_content = _extract_doc_text(tab_body)

    result: dict[str, Any] = {
        "document_id": document_id,
        "tab_id": tab_id,
        "title": tab_props.get("title", ""),
        "index": tab_props.get("index", 0),
        "nesting_level": tab_props.get("nestingLevel", 0),
        "text_content": text_content,
    }

    if "iconEmoji" in tab_props:
        result["icon_emoji"] = tab_props["iconEmoji"]
    if "parentTabId" in tab_props:
        result["parent_tab_id"] = tab_props["parentTabId"]

    return result


async def _create_document_tab(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    title = arguments["title"]
    icon_emoji = arguments.get("icon_emoji")
    parent_tab_id = arguments.get("parent_tab_id")
    index = arguments.get("index")

    create_tab_request: dict[str, Any] = {
        "createTab": {
            "tabProperties": {
                "title": title,
            }
        }
    }

    if icon_emoji:
        create_tab_request["createTab"]["tabProperties"]["iconEmoji"] = icon_emoji
    if parent_tab_id:
        create_tab_request["createTab"]["tabProperties"]["parentTabId"] = parent_tab_id
    if index is not None:
        create_tab_request["createTab"]["tabProperties"]["index"] = index

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {"requests": [create_tab_request]}
    response = await svc._make_request("POST", url, json_data=body)

    replies = response.get("replies", [])
    if replies and "createTab" in replies[0]:
        created_tab = replies[0]["createTab"]
        return {
            "status": "created",
            "document_id": document_id,
            "tab_id": created_tab.get("tabId"),
            "title": title,
        }

    return {"status": "created", "document_id": document_id, "title": title}


async def _update_tab_properties(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    tab_id = arguments["tab_id"]
    title = arguments.get("title")
    icon_emoji = arguments.get("icon_emoji")

    if not title and not icon_emoji:
        return {
            "error": "At least one of 'title' or 'icon_emoji' must be provided",
            "document_id": document_id,
            "tab_id": tab_id,
        }

    update_request: dict[str, Any] = {
        "updateTabProperties": {
            "tabId": tab_id,
            "tabProperties": {},
            "fields": [],
        }
    }

    if title:
        update_request["updateTabProperties"]["tabProperties"]["title"] = title
        update_request["updateTabProperties"]["fields"].append("title")
    if icon_emoji:
        update_request["updateTabProperties"]["tabProperties"]["iconEmoji"] = icon_emoji
        update_request["updateTabProperties"]["fields"].append("iconEmoji")

    update_request["updateTabProperties"]["fields"] = ",".join(
        update_request["updateTabProperties"]["fields"]
    )

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {"requests": [update_request]}
    await svc._make_request("POST", url, json_data=body)

    return {
        "status": "updated",
        "document_id": document_id,
        "tab_id": tab_id,
        "updated_fields": update_request["updateTabProperties"]["fields"].split(","),
    }


async def _move_tab(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    tab_id = arguments["tab_id"]
    new_parent_tab_id = arguments.get("new_parent_tab_id")
    new_index = arguments.get("new_index")

    if new_parent_tab_id is None and new_index is None:
        return {
            "error": "At least one of 'new_parent_tab_id' or 'new_index' must be provided",
            "document_id": document_id,
            "tab_id": tab_id,
        }

    update_request: dict[str, Any] = {
        "updateTabProperties": {
            "tabId": tab_id,
            "tabProperties": {},
            "fields": [],
        }
    }

    if new_parent_tab_id is not None:
        if new_parent_tab_id == "":
            update_request["updateTabProperties"]["tabProperties"]["parentTabId"] = None
        else:
            update_request["updateTabProperties"]["tabProperties"]["parentTabId"] = (
                new_parent_tab_id
            )
        update_request["updateTabProperties"]["fields"].append("parentTabId")

    if new_index is not None:
        update_request["updateTabProperties"]["tabProperties"]["index"] = new_index
        update_request["updateTabProperties"]["fields"].append("index")

    update_request["updateTabProperties"]["fields"] = ",".join(
        update_request["updateTabProperties"]["fields"]
    )

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {"requests": [update_request]}
    await svc._make_request("POST", url, json_data=body)

    return {
        "status": "moved",
        "document_id": document_id,
        "tab_id": tab_id,
        "updated_fields": update_request["updateTabProperties"]["fields"].split(","),
    }


async def _upload_markdown_as_doc(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
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


async def _render_mermaid_to_doc(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
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


async def _publish_markdown_to_doc(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
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


async def _format_text_in_document(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    start_index = arguments["start_index"]
    end_index = arguments["end_index"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    text_style: dict[str, Any] = {}
    if "bold" in arguments:
        text_style["bold"] = arguments["bold"]
    if "italic" in arguments:
        text_style["italic"] = arguments["italic"]
    if "underline" in arguments:
        text_style["underline"] = arguments["underline"]
    if "font_size" in arguments:
        text_style["fontSize"] = {"magnitude": arguments["font_size"], "unit": "PT"}
    if "font_family" in arguments:
        text_style["weightedFontFamily"] = {"fontFamily": arguments["font_family"]}
    if "text_color" in arguments:
        color = arguments["text_color"]
        text_style["foregroundColor"] = {"color": {"rgbColor": color}}

    if not text_style:
        return {"status": "no_formatting_applied"}

    requests = [
        {
            "updateTextStyle": {
                "range": {"startIndex": start_index, "endIndex": end_index},
                "textStyle": text_style,
                "fields": ",".join(text_style.keys()),
            }
        }
    ]

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "formatted",
        "document_id": document_id,
        "range": {"start_index": start_index, "end_index": end_index},
        "applied_formatting": list(text_style.keys()),
    }


async def _format_paragraph_in_document(
    svc: "BaseService", arguments: dict[str, Any]
) -> dict[str, Any]:
    document_id = arguments["document_id"]
    start_index = arguments["start_index"]
    end_index = arguments["end_index"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    paragraph_style: dict[str, Any] = {}
    if "alignment" in arguments:
        paragraph_style["alignment"] = arguments["alignment"]
    if "line_spacing" in arguments:
        paragraph_style["lineSpacing"] = arguments["line_spacing"]
    if "indent_first_line" in arguments:
        paragraph_style["indentFirstLine"] = {
            "magnitude": arguments["indent_first_line"],
            "unit": "PT",
        }
    if "indent_start" in arguments:
        paragraph_style["indentStart"] = {"magnitude": arguments["indent_start"], "unit": "PT"}
    if "indent_end" in arguments:
        paragraph_style["indentEnd"] = {"magnitude": arguments["indent_end"], "unit": "PT"}

    if not paragraph_style:
        return {"status": "no_formatting_applied"}

    request_body = {
        "requests": [
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start_index, "endIndex": end_index},
                    "paragraphStyle": paragraph_style,
                    "fields": ",".join(paragraph_style.keys()),
                }
            }
        ]
    }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "formatted",
        "document_id": document_id,
        "range": {"start_index": start_index, "end_index": end_index},
        "applied_formatting": list(paragraph_style.keys()),
    }


async def _create_list_in_document(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    insert_index = arguments["insert_index"]
    list_type = arguments["list_type"]
    items = arguments["items"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    list_text = ""
    for item in items:
        list_text += f"{item}\n"

    end_index = insert_index + len(list_text)
    requests = [
        {
            "insertText": {
                "location": {"index": insert_index},
                "text": list_text,
            }
        },
        {
            "createParagraphBullets": {
                "range": {"startIndex": insert_index, "endIndex": end_index},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                if list_type == "BULLETED"
                else "NUMBERED_DECIMAL_ALPHA_ROMAN",
            }
        },
    ]

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "created",
        "document_id": document_id,
        "list_type": list_type,
        "insert_index": insert_index,
        "items_count": len(items),
    }


async def _insert_table_in_document(
    svc: "BaseService", arguments: dict[str, Any]
) -> dict[str, Any]:
    document_id = arguments["document_id"]
    insert_index = arguments["insert_index"]
    rows = arguments["rows"]
    columns = arguments["columns"]
    header_row = arguments.get("header_row", True)

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    request_body = {
        "requests": [
            {
                "insertTable": {
                    "location": {"index": insert_index},
                    "rows": rows,
                    "columns": columns,
                }
            }
        ]
    }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "inserted",
        "document_id": document_id,
        "insert_index": insert_index,
        "dimensions": {"rows": rows, "columns": columns},
        "header_row": header_row,
    }


async def _apply_heading_style(svc: "BaseService", arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    start_index = arguments["start_index"]
    end_index = arguments["end_index"]
    heading_style = arguments["heading_style"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    request_body = {
        "requests": [
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start_index, "endIndex": end_index},
                    "paragraphStyle": {"namedStyleType": heading_style},
                    "fields": "namedStyleType",
                }
            }
        ]
    }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "applied",
        "document_id": document_id,
        "range": {"start_index": start_index, "end_index": end_index},
        "heading_style": heading_style,
    }


# ---------------------------------------------------------------------------
# Handler registry
# ---------------------------------------------------------------------------


def get_handlers(svc: "BaseService") -> dict[str, Any]:
    """Return mapping of tool name to handler lambda."""
    return {
        "list_document_comments": lambda args: _list_document_comments(svc, args),
        "add_document_comment": lambda args: _add_document_comment(svc, args),
        "reply_to_comment": lambda args: _reply_to_comment(svc, args),
        "create_document": lambda args: _create_document(svc, args),
        "append_to_document": lambda args: _append_to_document(svc, args),
        "get_document": lambda args: _get_document(svc, args),
        "list_document_tabs": lambda args: _list_document_tabs(svc, args),
        "get_tab_content": lambda args: _get_tab_content(svc, args),
        "create_document_tab": lambda args: _create_document_tab(svc, args),
        "update_tab_properties": lambda args: _update_tab_properties(svc, args),
        "move_tab": lambda args: _move_tab(svc, args),
        "upload_markdown_as_doc": lambda args: _upload_markdown_as_doc(svc, args),
        "render_mermaid_to_doc": lambda args: _render_mermaid_to_doc(svc, args),
        "publish_markdown_to_doc": lambda args: _publish_markdown_to_doc(svc, args),
        "format_text_in_document": lambda args: _format_text_in_document(svc, args),
        "format_paragraph_in_document": lambda args: _format_paragraph_in_document(svc, args),
        "create_list_in_document": lambda args: _create_list_in_document(svc, args),
        "insert_table_in_document": lambda args: _insert_table_in_document(svc, args),
        "apply_heading_style": lambda args: _apply_heading_style(svc, args),
    }
