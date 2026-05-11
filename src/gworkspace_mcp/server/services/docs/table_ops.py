"""Google Docs table structural operations: find, insert/delete rows/cols, merge."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService


TOOLS: list[Tool] = [
    Tool(
        name="find_tables_in_document",
        description=(
            "Scan a Google Doc for all tables and return their positions and dimensions. "
            "Returns a list of tables with start_index, end_index, num_rows, num_columns, "
            "and a preview of the first cell. Use the returned table_start_index when calling "
            "table manipulation tools."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Google Doc ID"},
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="manage_table_structure",
        description=(
            "Perform structural operations on an existing table in a Google Doc. Actions: "
            "'insert_row' — insert a new row before/after an existing row; "
            "'delete_row' — delete a row; "
            "'insert_column' — insert a column before/after an existing column; "
            "'delete_column' — delete a column; "
            "'merge_cells' — merge a rectangular range of cells; "
            "'unmerge_cells' — unmerge a previously merged range; "
            "'delete_table' — delete the table entirely (requires table_end_index)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "insert_row",
                        "delete_row",
                        "insert_column",
                        "delete_column",
                        "merge_cells",
                        "unmerge_cells",
                        "delete_table",
                    ],
                },
                "document_id": {"type": "string"},
                "table_start_index": {
                    "type": "integer",
                    "description": "The document index of the table node",
                },
                "row_index": {
                    "type": "integer",
                    "description": "Row index (0-based). Required for row/cell actions.",
                },
                "column_index": {
                    "type": "integer",
                    "description": "Column index (0-based). Required for column/cell actions.",
                },
                "insert_below": {
                    "type": "boolean",
                    "default": True,
                    "description": "When inserting a row, insert below the referenced row (else above)",
                },
                "insert_right": {
                    "type": "boolean",
                    "default": True,
                    "description": "When inserting a column, insert to the right of the referenced column (else left)",
                },
                "row_span": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of rows for merge/unmerge actions",
                },
                "column_span": {
                    "type": "integer",
                    "default": 1,
                    "description": "Number of columns for merge/unmerge actions",
                },
                "row_data": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional cell text to populate a newly-inserted row",
                },
                "table_end_index": {
                    "type": "integer",
                    "description": "End index of the table (required for delete_table action)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action", "document_id", "table_start_index"],
        },
    ),
]


# =============================================================================
# Helpers
# =============================================================================


def _extract_cell_text(cell: dict[str, Any]) -> str:
    """Extract concatenated text from a table cell's paragraph content."""
    parts: list[str] = []
    for content_elem in cell.get("content", []):
        paragraph = content_elem.get("paragraph")
        if not paragraph:
            continue
        for elem in paragraph.get("elements", []):
            text_run = elem.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return "".join(parts).strip()


# =============================================================================
# Handlers
# =============================================================================


async def _find_tables_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    url = f"{DOCS_API_BASE}/documents/{document_id}"
    doc = await svc._make_request("GET", url)

    body_content: list[dict[str, Any]] = doc.get("body", {}).get("content", [])
    tables: list[dict[str, Any]] = []

    for idx, element in enumerate(body_content):
        table = element.get("table")
        if table is None:
            continue
        rows = table.get("tableRows", [])
        num_rows = len(rows)
        num_columns = len(rows[0].get("tableCells", [])) if rows else 0
        first_cell_text = ""
        if rows and rows[0].get("tableCells"):
            first_cell_text = _extract_cell_text(rows[0]["tableCells"][0])
            if len(first_cell_text) > 100:
                first_cell_text = first_cell_text[:100] + "..."

        tables.append(
            {
                "table_index": idx,
                "start_index": element.get("startIndex"),
                "end_index": element.get("endIndex"),
                "num_rows": num_rows,
                "num_columns": num_columns,
                "first_cell_text": first_cell_text,
            }
        )

    return {"tables": tables, "count": len(tables)}


async def _manage_table_structure(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    action = arguments["action"]
    document_id = arguments["document_id"]
    table_start_index = arguments["table_start_index"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    requests: list[dict[str, Any]] = []

    if action == "insert_row":
        row_index = arguments.get("row_index")
        if row_index is None:
            return {"error": "row_index is required for insert_row action"}
        insert_below = arguments.get("insert_below", True)
        requests.append(
            {
                "insertTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start_index},
                        "rowIndex": row_index,
                        "columnIndex": 0,
                    },
                    "insertBelow": insert_below,
                }
            }
        )

        await svc._make_request("POST", url, json_data={"requests": requests})

        # Populate inserted row with data if provided
        row_data = arguments.get("row_data") or []
        if row_data:
            # Re-fetch document to find new cell indices
            doc = await svc._make_request("GET", f"{DOCS_API_BASE}/documents/{document_id}")
            body_content: list[dict[str, Any]] = doc.get("body", {}).get("content", [])
            new_row_idx = row_index + 1 if insert_below else row_index
            populated = 0
            for element in body_content:
                table = element.get("table")
                if table is None:
                    continue
                if element.get("startIndex") != table_start_index:
                    continue
                rows = table.get("tableRows", [])
                if new_row_idx < len(rows):
                    cells = rows[new_row_idx].get("tableCells", [])
                    text_requests: list[dict[str, Any]] = []
                    for c, cell_text in enumerate(row_data[: len(cells)]):
                        if not cell_text:
                            continue
                        content = cells[c].get("content", [])
                        if not content:
                            continue
                        idx = content[0].get("startIndex", 0)
                        if idx:
                            text_requests.append(
                                {
                                    "insertText": {
                                        "location": {"index": idx},
                                        "text": cell_text,
                                    }
                                }
                            )
                            populated += 1
                    if text_requests:
                        await svc._make_request("POST", url, json_data={"requests": text_requests})
                break

        return {
            "status": "inserted",
            "action": action,
            "document_id": document_id,
            "table_start_index": table_start_index,
            "row_index": row_index,
            "insert_below": insert_below,
        }

    if action == "delete_row":
        row_index = arguments.get("row_index")
        if row_index is None:
            return {"error": "row_index is required for delete_row action"}
        requests.append(
            {
                "deleteTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start_index},
                        "rowIndex": row_index,
                        "columnIndex": 0,
                    }
                }
            }
        )

    elif action == "insert_column":
        column_index = arguments.get("column_index")
        if column_index is None:
            return {"error": "column_index is required for insert_column action"}
        insert_right = arguments.get("insert_right", True)
        requests.append(
            {
                "insertTableColumn": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start_index},
                        "rowIndex": 0,
                        "columnIndex": column_index,
                    },
                    "insertRight": insert_right,
                }
            }
        )

    elif action == "delete_column":
        column_index = arguments.get("column_index")
        if column_index is None:
            return {"error": "column_index is required for delete_column action"}
        requests.append(
            {
                "deleteTableColumn": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start_index},
                        "rowIndex": 0,
                        "columnIndex": column_index,
                    }
                }
            }
        )

    elif action == "merge_cells":
        row_index = arguments.get("row_index")
        column_index = arguments.get("column_index")
        if row_index is None or column_index is None:
            return {"error": "row_index and column_index are required for merge_cells action"}
        row_span = arguments.get("row_span", 1)
        column_span = arguments.get("column_span", 1)
        requests.append(
            {
                "mergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table_start_index},
                            "rowIndex": row_index,
                            "columnIndex": column_index,
                        },
                        "rowSpan": row_span,
                        "columnSpan": column_span,
                    }
                }
            }
        )

    elif action == "unmerge_cells":
        row_index = arguments.get("row_index")
        column_index = arguments.get("column_index")
        if row_index is None or column_index is None:
            return {"error": "row_index and column_index are required for unmerge_cells action"}
        row_span = arguments.get("row_span", 1)
        column_span = arguments.get("column_span", 1)
        requests.append(
            {
                "unmergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table_start_index},
                            "rowIndex": row_index,
                            "columnIndex": column_index,
                        },
                        "rowSpan": row_span,
                        "columnSpan": column_span,
                    }
                }
            }
        )

    elif action == "delete_table":
        table_end_index = arguments.get("table_end_index")
        if table_end_index is None:
            return {
                "error": (
                    "table_end_index is required for delete_table action. "
                    "Call find_tables_in_document first to obtain it."
                )
            }
        # Include the preceding newline so the table is fully removed
        start = max(table_start_index - 1, 0)
        requests.append(
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": start,
                        "endIndex": table_end_index,
                    }
                }
            }
        )

    else:
        return {"error": f"Unknown action '{action}'"}

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "applied",
        "action": action,
        "document_id": document_id,
        "table_start_index": table_start_index,
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs table-structure handlers."""
    return {
        "find_tables_in_document": lambda args: _find_tables_in_document(svc, args),
        "manage_table_structure": lambda args: _manage_table_structure(svc, args),
    }
