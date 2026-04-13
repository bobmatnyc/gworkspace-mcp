"""Google Docs formatting sub-module: text, paragraph, heading, list, and table."""

from __future__ import annotations

import math
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
        description=(
            "Insert a table with content into a Google Doc. "
            "Supports optional cell data, column widths, auto-balancing, padding, and header styling."
        ),
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
                    "description": "2D array of cell text (row-major order, optional)",
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "header_row": {
                    "type": "boolean",
                    "default": True,
                    "description": "Treat first row as header for styling purposes",
                },
                "column_widths": {
                    "type": "array",
                    "description": "Explicit column widths in PT (null entries are skipped)",
                    "items": {"type": ["number", "null"]},
                },
                "auto_balance": {
                    "type": "boolean",
                    "default": False,
                    "description": "Run the equalize line-count balance algorithm",
                },
                "available_width": {
                    "type": "number",
                    "default": 468.0,
                    "description": "Usable page width in PT (default: letter page minus 2-inch margins)",
                },
                "font_size": {
                    "type": "number",
                    "default": 11.0,
                    "description": "Font size in PT used by the auto-balance algorithm",
                },
                "padding": {
                    "type": "object",
                    "description": "Cell padding to apply to all cells (PT)",
                    "properties": {
                        "top": {"type": "number"},
                        "bottom": {"type": "number"},
                        "left": {"type": "number"},
                        "right": {"type": "number"},
                    },
                },
                "header_style": {
                    "type": "object",
                    "description": "Styling applied to the first (header) row",
                    "properties": {
                        "background_color": {
                            "type": "object",
                            "properties": {
                                "red": {"type": "number", "minimum": 0, "maximum": 1},
                                "green": {"type": "number", "minimum": 0, "maximum": 1},
                                "blue": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                        },
                        "bold": {"type": "boolean"},
                    },
                },
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
    Tool(
        name="format_table_cells",
        description=(
            "Apply cell styling (padding, borders, background color, content alignment) "
            "to a range of cells in an existing table. "
            "Use row_index=-1 and/or column_index=-1 to target all rows or columns."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "table_start_index": {
                    "type": "integer",
                    "description": "The document index of the table node",
                },
                "row_index": {
                    "type": "integer",
                    "description": "Row index (0-based). Use -1 to target all rows.",
                },
                "column_index": {
                    "type": "integer",
                    "description": "Column index (0-based). Use -1 to target all columns.",
                },
                "num_rows": {
                    "type": "integer",
                    "description": "Total number of rows in the table (required when row_index=-1)",
                },
                "num_columns": {
                    "type": "integer",
                    "description": "Total number of columns in the table (required when column_index=-1)",
                },
                "padding": {
                    "type": "object",
                    "description": "Cell padding in PT (all fields optional)",
                    "properties": {
                        "top": {"type": "number"},
                        "bottom": {"type": "number"},
                        "left": {"type": "number"},
                        "right": {"type": "number"},
                    },
                },
                "border": {
                    "type": "object",
                    "description": "Border style to apply",
                    "properties": {
                        "color": {
                            "type": "object",
                            "properties": {
                                "red": {"type": "number", "minimum": 0, "maximum": 1},
                                "green": {"type": "number", "minimum": 0, "maximum": 1},
                                "blue": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                        },
                        "width": {"type": "number", "default": 1.0, "description": "Width in PT"},
                        "dash_style": {
                            "type": "string",
                            "enum": ["SOLID", "DOT", "DASH"],
                            "default": "SOLID",
                        },
                        "sides": {
                            "type": "array",
                            "description": "Which sides to apply the border to. Defaults to all four.",
                            "items": {
                                "type": "string",
                                "enum": ["top", "bottom", "left", "right"],
                            },
                        },
                    },
                },
                "background_color": {
                    "type": "object",
                    "description": "Background fill color",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "content_alignment": {
                    "type": "string",
                    "enum": ["TOP", "MIDDLE", "BOTTOM"],
                    "description": "Vertical alignment of cell content",
                },
            },
            "required": ["document_id", "table_start_index", "row_index", "column_index"],
        },
    ),
    Tool(
        name="set_table_column_widths",
        description=(
            "Set explicit column widths on an existing table, or run the auto-balance algorithm "
            "to equalize line counts across columns. "
            "Pass null in column_widths to leave a column as EVENLY_DISTRIBUTED."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "table_start_index": {
                    "type": "integer",
                    "description": "The document index of the table node",
                },
                "column_widths": {
                    "type": "array",
                    "description": "PT widths per column. null = EVENLY_DISTRIBUTED for that column.",
                    "items": {"type": ["number", "null"]},
                },
                "auto_balance": {
                    "type": "boolean",
                    "default": False,
                    "description": "Compute widths using the equalize algorithm instead of explicit widths",
                },
                "data": {
                    "type": "array",
                    "description": "2D array of cell text (required when auto_balance=true)",
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "available_width": {
                    "type": "number",
                    "default": 468.0,
                    "description": "Usable page width in PT",
                },
                "font_size": {
                    "type": "number",
                    "default": 11.0,
                    "description": "Font size in PT used by the balance algorithm",
                },
                "min_col_width": {
                    "type": "number",
                    "default": 60.0,
                    "description": "Minimum column width floor in PT",
                },
                "algorithm": {
                    "type": "string",
                    "enum": ["equalize", "sqrt", "proportional"],
                    "default": "equalize",
                    "description": "Balance algorithm to use when auto_balance=true",
                },
            },
            "required": ["document_id", "table_start_index"],
        },
    ),
]


# =============================================================================
# Pure helper: column-width balancing
# =============================================================================


def balance_column_widths(
    data: list[list[str]],
    available_width: float,
    font_size: float = 11.0,
    min_col_width: float = 60.0,
    algorithm: str = "equalize",
) -> list[float]:
    """Return balanced column widths in PT for *data*.

    Parameters
    ----------
    data:
        2-D list of cell text (row-major).  Empty lists are safe.
    available_width:
        Usable horizontal space in PT (e.g. 468 for a US-Letter page with
        1-inch margins on each side).
    font_size:
        Approximate font size in PT used for character-width estimation.
    min_col_width:
        Hard minimum for any column, in PT.
    algorithm:
        One of "equalize" (default), "sqrt", or "proportional".

    Returns
    -------
    list[float]
        One width per column, summing to at most *available_width*.
    """
    if not data or not data[0]:
        return []

    num_cols = max(len(row) for row in data)
    char_width = font_size * 0.55  # PT per average character

    # max characters in any cell, per column
    max_chars: list[int] = []
    max_word_len: list[int] = []
    for c in range(num_cols):
        col_max = 0
        col_word_max = 0
        for row in data:
            if c < len(row):
                cell = row[c]
                col_max = max(col_max, len(cell))
                words = cell.split()
                if words:
                    col_word_max = max(col_word_max, max(len(w) for w in words))
        max_chars.append(max(col_max, 1))
        max_word_len.append(max(col_word_max, 1))

    min_widths = [max(w * char_width, min_col_width) for w in max_word_len]

    if algorithm == "equalize":
        widths = _equalize_widths(max_chars, min_widths, char_width, available_width)
    elif algorithm == "sqrt":
        weights = [max(1.0, math.sqrt(mc)) for mc in max_chars]
        total_w = sum(weights)
        widths = [max(min_col_width, available_width * w / total_w) for w in weights]
    else:  # proportional
        weights = [max(1.0, float(mc)) for mc in max_chars]
        total_w = sum(weights)
        widths = [max(min_col_width, available_width * w / total_w) for w in weights]

    # Rescale if sum exceeds available_width
    total = sum(widths)
    if total > available_width:
        factor = available_width / total
        widths = [w * factor for w in widths]

    return widths


def _equalize_widths(
    max_chars: list[int],
    min_widths: list[float],
    char_width: float,
    available_width: float,
) -> list[float]:
    """Equalize line-count via binary search on target line count T."""
    num_cols = len(max_chars)
    overall_max = max(max_chars)

    best_widths: list[float] = [available_width / num_cols] * num_cols

    # Binary search: find largest T such that sum of clamped widths <= available_width
    lo, hi = 1, overall_max
    while lo <= hi:
        T = (lo + hi) // 2
        raw = [math.ceil(mc / T) * char_width for mc in max_chars]
        clamped = [max(rw, mw) for rw, mw in zip(raw, min_widths, strict=False)]
        if sum(clamped) <= available_width:
            best_widths = list(clamped)
            lo = T + 1  # try to increase T (more lines per cell = narrower cols)
        else:
            hi = T - 1

    # Distribute leftover proportionally to columns that can use more space
    leftover = available_width - sum(best_widths)
    if leftover > 0.5:
        # Columns that benefit from more width (those still limited by content)
        benefiting = [i for i, w in enumerate(best_widths) if w < max_chars[i] * char_width]
        if not benefiting:
            benefiting = list(range(num_cols))
        share = leftover / len(benefiting)
        for i in benefiting:
            best_widths[i] += share

    return best_widths


# =============================================================================
# Internal helpers
# =============================================================================


def _build_cell_style_request(
    table_start_index: int,
    row_idx: int,
    col_idx: int,
    padding: dict[str, float] | None,
    border: dict[str, Any] | None,
    background_color: dict[str, float] | None,
    content_alignment: str | None,
) -> dict[str, Any]:
    """Build a single updateTableCellStyle request dict."""
    cell_style: dict[str, Any] = {}
    field_keys: list[str] = []

    if padding:
        for side in ("top", "bottom", "left", "right"):
            if side in padding:
                key = f"padding{side.capitalize()}"
                cell_style[key] = {"magnitude": padding[side], "unit": "PT"}
                field_keys.append(key)

    if border:
        color = border.get("color", {"red": 0.0, "green": 0.0, "blue": 0.0})
        width_pt = border.get("width", 1.0)
        dash_style = border.get("dash_style", "SOLID")
        sides = border.get("sides") or ["top", "bottom", "left", "right"]
        border_obj = {
            "color": {"color": {"rgbColor": color}},
            "width": {"magnitude": width_pt, "unit": "PT"},
            "dashStyle": dash_style,
        }
        for side in sides:
            key = f"border{side.capitalize()}"
            cell_style[key] = border_obj
            field_keys.append(key)

    if background_color:
        cell_style["backgroundColor"] = {"color": {"rgbColor": background_color}}
        field_keys.append("backgroundColor")

    if content_alignment:
        cell_style["contentAlignment"] = content_alignment
        field_keys.append("contentAlignment")

    if not cell_style:
        return {}

    return {
        "updateTableCellStyle": {
            "tableStartLocation": {"index": table_start_index},
            "tableCellStyle": cell_style,
            "fields": ",".join(field_keys),
            "tableRange": {
                "tableCellLocation": {
                    "tableStartLocation": {"index": table_start_index},
                    "rowIndex": row_idx,
                    "columnIndex": col_idx,
                },
                "rowSpan": 1,
                "columnSpan": 1,
            },
        }
    }


def _find_table_cell_indices(
    doc_body: list[dict[str, Any]], table_start_index: int
) -> list[list[int]]:
    """Walk document body to find start indices of each table cell.

    Returns a 2-D list: cell_indices[row][col] = startIndex of the first
    paragraph segment inside that cell.
    """
    cell_indices: list[list[int]] = []
    for element in doc_body:
        table = element.get("table")
        if table is None:
            continue
        # The table's startIndex is the index of the TABLE element itself.
        elem_start = element.get("startIndex", 0)
        if elem_start != table_start_index:
            continue
        for table_row in table.get("tableRows", []):
            row_cells: list[int] = []
            for cell in table_row.get("tableCells", []):
                content = cell.get("content", [])
                if content:
                    row_cells.append(content[0].get("startIndex", 0))
                else:
                    row_cells.append(0)
            cell_indices.append(row_cells)
        break
    return cell_indices


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
    data: list[list[str]] = arguments.get("data") or []
    header_row: bool = arguments.get("header_row", True)
    column_widths: list[float | None] | None = arguments.get("column_widths")
    auto_balance: bool = arguments.get("auto_balance", False)
    available_width: float = float(arguments.get("available_width", 468.0))
    font_size: float = float(arguments.get("font_size", 11.0))
    padding: dict[str, float] | None = arguments.get("padding")
    header_style: dict[str, Any] | None = arguments.get("header_style")

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    # Step 1: Insert the empty table.
    await svc._make_request(
        "POST",
        url,
        json_data={
            "requests": [
                {
                    "insertTable": {
                        "location": {"index": insert_index},
                        "rows": rows,
                        "columns": columns,
                    }
                }
            ]
        },
    )

    # Step 2: Re-fetch the document to find actual cell indices.
    doc_url = f"{DOCS_API_BASE}/documents/{document_id}"
    doc = await svc._make_request("GET", doc_url)

    body_content: list[dict[str, Any]] = doc.get("body", {}).get("content", [])

    # Locate the table that was just inserted.  The table appears at
    # insert_index + 1 after the newline that Google inserts before it.
    table_start_index = insert_index + 1
    cell_indices = _find_table_cell_indices(body_content, table_start_index)

    post_requests: list[dict[str, Any]] = []

    # Step 3: Populate cell text.
    if data:
        for r, row_data in enumerate(data[:rows]):
            for c, cell_text in enumerate(row_data[:columns]):
                if not cell_text:
                    continue
                if r < len(cell_indices) and c < len(cell_indices[r]):
                    idx = cell_indices[r][c]
                    post_requests.append(
                        {
                            "insertText": {
                                "location": {"index": idx},
                                "text": cell_text,
                            }
                        }
                    )

    # Step 4: Apply column widths.
    computed_widths: list[float] = []
    if auto_balance and data:
        computed_widths = balance_column_widths(data, available_width, font_size=font_size)
    elif column_widths:
        for _, w in enumerate(column_widths):
            if w is not None:
                computed_widths_entry: float = float(w)
                computed_widths.append(computed_widths_entry)
            else:
                computed_widths.append(0.0)  # placeholder; handled below

    for col_idx, width_val in enumerate(computed_widths):
        if col_idx >= columns:
            break
        if width_val <= 0:
            # null / 0 => EVENLY_DISTRIBUTED
            post_requests.append(
                {
                    "updateTableColumnProperties": {
                        "tableStartLocation": {"index": table_start_index},
                        "columnIndices": [col_idx],
                        "tableColumnProperties": {
                            "widthType": "EVENLY_DISTRIBUTED",
                        },
                        "fields": "widthType",
                    }
                }
            )
        else:
            post_requests.append(
                {
                    "updateTableColumnProperties": {
                        "tableStartLocation": {"index": table_start_index},
                        "columnIndices": [col_idx],
                        "tableColumnProperties": {
                            "widthType": "FIXED_WIDTH",
                            "width": {"magnitude": width_val, "unit": "PT"},
                        },
                        "fields": "widthType,width",
                    }
                }
            )

    # Step 5: Apply padding to all cells.
    if padding and cell_indices:
        for r in range(len(cell_indices)):
            for c in range(len(cell_indices[r])):
                req = _build_cell_style_request(table_start_index, r, c, padding, None, None, None)
                if req:
                    post_requests.append(req)

    # Step 6: Apply header row styling.
    if header_row and header_style and cell_indices:
        bg_color: dict[str, float] | None = header_style.get("background_color")
        bold: bool | None = header_style.get("bold")
        if cell_indices:
            first_row = cell_indices[0]
            for c in range(len(first_row)):
                req = _build_cell_style_request(table_start_index, 0, c, None, None, bg_color, None)
                if req:
                    post_requests.append(req)
                # Apply bold text to header cells
                if bold and c < len(first_row):
                    idx = first_row[c]
                    # Bold the entire cell text (approximate range)
                    post_requests.append(
                        {
                            "updateTextStyle": {
                                "range": {"startIndex": idx, "endIndex": idx + 1},
                                "textStyle": {"bold": True},
                                "fields": "bold",
                            }
                        }
                    )

    if post_requests:
        await svc._make_request("POST", url, json_data={"requests": post_requests})

    return {
        "status": "inserted",
        "document_id": document_id,
        "table_start_index": table_start_index,
        "insert_index": insert_index,
        "dimensions": {"rows": rows, "columns": columns},
        "header_row": header_row,
        "cells_populated": bool(data),
        "column_widths_applied": bool(computed_widths),
    }


async def _format_table_cells(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    table_start_index = arguments["table_start_index"]
    row_index: int = arguments["row_index"]
    column_index: int = arguments["column_index"]
    num_rows: int = arguments.get("num_rows", 0)
    num_columns: int = arguments.get("num_columns", 0)
    padding: dict[str, float] | None = arguments.get("padding")
    border: dict[str, Any] | None = arguments.get("border")
    background_color: dict[str, float] | None = arguments.get("background_color")
    content_alignment: str | None = arguments.get("content_alignment")

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    # Build list of (r, c) target cells
    if row_index == -1 and column_index == -1:
        targets = [(r, c) for r in range(num_rows) for c in range(num_columns)]
    elif row_index == -1:
        targets = [(r, column_index) for r in range(num_rows)]
    elif column_index == -1:
        targets = [(row_index, c) for c in range(num_columns)]
    else:
        targets = [(row_index, column_index)]

    requests: list[dict[str, Any]] = []
    for r, c in targets:
        req = _build_cell_style_request(
            table_start_index, r, c, padding, border, background_color, content_alignment
        )
        if req:
            requests.append(req)

    if not requests:
        return {"status": "no_formatting_applied", "document_id": document_id}

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "formatted",
        "document_id": document_id,
        "table_start_index": table_start_index,
        "cells_updated": len(requests),
        "targets": [{"row": r, "col": c} for r, c in targets],
    }


async def _set_table_column_widths(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    table_start_index = arguments["table_start_index"]
    column_widths_raw: list[float | None] | None = arguments.get("column_widths")
    auto_balance: bool = arguments.get("auto_balance", False)
    data: list[list[str]] | None = arguments.get("data")
    available_width: float = float(arguments.get("available_width", 468.0))
    font_size: float = float(arguments.get("font_size", 11.0))
    min_col_width: float = float(arguments.get("min_col_width", 60.0))
    algorithm: str = arguments.get("algorithm", "equalize")

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    # Determine final widths list
    if auto_balance:
        if not data:
            return {
                "status": "error",
                "message": "data is required when auto_balance=true",
            }
        computed = balance_column_widths(
            data,
            available_width,
            font_size=font_size,
            min_col_width=min_col_width,
            algorithm=algorithm,
        )
        widths: list[float | None] = list(computed)
    else:
        widths = column_widths_raw or []

    requests: list[dict[str, Any]] = []
    for col_idx, width_val in enumerate(widths):
        if width_val is None or (isinstance(width_val, float) and width_val <= 0):
            requests.append(
                {
                    "updateTableColumnProperties": {
                        "tableStartLocation": {"index": table_start_index},
                        "columnIndices": [col_idx],
                        "tableColumnProperties": {
                            "widthType": "EVENLY_DISTRIBUTED",
                        },
                        "fields": "widthType",
                    }
                }
            )
        else:
            requests.append(
                {
                    "updateTableColumnProperties": {
                        "tableStartLocation": {"index": table_start_index},
                        "columnIndices": [col_idx],
                        "tableColumnProperties": {
                            "widthType": "FIXED_WIDTH",
                            "width": {"magnitude": float(width_val), "unit": "PT"},
                        },
                        "fields": "widthType,width",
                    }
                }
            )

    if not requests:
        return {"status": "no_widths_applied", "document_id": document_id}

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "applied",
        "document_id": document_id,
        "table_start_index": table_start_index,
        "columns_updated": len(requests),
        "widths_pt": [float(w) if w is not None else None for w in widths],
        "auto_balance": auto_balance,
        "algorithm": algorithm if auto_balance else None,
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
        "format_table_cells": lambda args: _format_table_cells(svc, args),
        "set_table_column_widths": lambda args: _set_table_column_widths(svc, args),
    }
