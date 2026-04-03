"""Google Docs formatting sub-module: text, paragraph, heading, list, and table."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
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


# =============================================================================
# Handler functions
# =============================================================================


async def _format_text_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
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
    svc: BaseService, arguments: dict[str, Any]
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


async def _create_list_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
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


async def _insert_table_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
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


async def _apply_heading_style(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs formatting handlers."""
    return {
        "format_text_in_document": lambda args: _format_text_in_document(svc, args),
        "format_paragraph_in_document": lambda args: _format_paragraph_in_document(svc, args),
        "create_list_in_document": lambda args: _create_list_in_document(svc, args),
        "insert_table_in_document": lambda args: _insert_table_in_document(svc, args),
        "apply_heading_style": lambda args: _apply_heading_style(svc, args),
    }
