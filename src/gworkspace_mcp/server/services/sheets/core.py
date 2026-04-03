"""Google Sheets core sub-module: create, read, write, and tab management."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import SHEETS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="list_spreadsheet_sheets",
        description="List all tabs/sheets in a Google Spreadsheet. Returns sheet names with their properties (name, index, sheetId). Use this to discover available sheets before reading data.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
            },
            "required": ["spreadsheet_id"],
        },
    ),
    Tool(
        name="get_sheet_values",
        description="Get values from a specific sheet/tab in a Google Spreadsheet. Returns data as formatted CSV text. Use list_spreadsheet_sheets first to get available sheet names.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab to read (e.g., 'Sheet1', 'Sales Data')",
                },
                "range": {
                    "type": "string",
                    "description": "Cell range in A1 notation (e.g., 'A1:Z100', 'A:ZZ'). Default: 'A:ZZ' (all columns)",
                    "default": "A:ZZ",
                },
            },
            "required": ["spreadsheet_id", "sheet_name"],
        },
    ),
    Tool(
        name="get_spreadsheet_data",
        description="Get all sheets and their data from a Google Spreadsheet. Returns a dictionary mapping sheet names to their values. Efficient batch operation for multi-tab spreadsheets.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum rows to retrieve per sheet (default: 1000)",
                    "default": 1000,
                },
            },
            "required": ["spreadsheet_id"],
        },
    ),
    Tool(
        name="create_spreadsheet",
        description="Create a new Google Spreadsheet. Returns the new spreadsheet ID and URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the new spreadsheet",
                },
                "sheet_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of sheet/tab names to create (default: ['Sheet1'])",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="update_sheet_values",
        description="Update values in a specific range of a Google Spreadsheet. Overwrites existing values in the specified range.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab to update (e.g., 'Sheet1')",
                },
                "range": {
                    "type": "string",
                    "description": "Cell range in A1 notation (e.g., 'A1:C3', 'A1')",
                },
                "values": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {},
                    },
                    "description": "2D array of values to write (rows of cells)",
                },
            },
            "required": ["spreadsheet_id", "sheet_name", "range", "values"],
        },
    ),
    Tool(
        name="append_sheet_values",
        description="Append rows to the end of data in a Google Spreadsheet sheet. Automatically finds the last row with data and appends below it.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab to append to (e.g., 'Sheet1')",
                },
                "values": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {},
                    },
                    "description": "2D array of values to append (rows of cells)",
                },
            },
            "required": ["spreadsheet_id", "sheet_name", "values"],
        },
    ),
    Tool(
        name="clear_sheet_values",
        description="Clear values from a specific range in a Google Spreadsheet. Removes cell values but preserves formatting.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab to clear (e.g., 'Sheet1')",
                },
                "range": {
                    "type": "string",
                    "description": "Cell range in A1 notation to clear (e.g., 'A1:C10', 'A:Z')",
                },
            },
            "required": ["spreadsheet_id", "sheet_name", "range"],
        },
    ),
    Tool(
        name="add_sheet",
        description="Add a new sheet/tab to an existing Google Spreadsheet. Returns the new sheet's ID, title, and index.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "title": {
                    "type": "string",
                    "description": "Name for the new sheet/tab",
                },
                "index": {
                    "type": "integer",
                    "description": "0-based position to insert the sheet (default: append at end)",
                },
                "tab_color": {
                    "type": "object",
                    "description": "RGB tab color (each component 0.0–1.0)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "required": ["spreadsheet_id", "title"],
        },
    ),
]


# =============================================================================
# Helper functions (also used by formatting sub-module)
# =============================================================================


async def get_sheet_id(svc: BaseService, spreadsheet_id: str, sheet_name: str) -> dict[str, Any]:
    """Get sheet ID from sheet name.

    Public helper used by the formatting sub-module.
    """
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}"
    response = await svc._make_request("GET", url)
    for sheet in response["sheets"]:
        if sheet["properties"]["title"] == sheet_name:
            return {"sheet_id": sheet["properties"]["sheetId"], "sheet_name": sheet_name}
    raise ValueError(f"Sheet '{sheet_name}' not found")


async def a1_to_grid_range(range_a1: str, sheet_id: int) -> dict[str, Any]:
    """Convert A1 notation to grid range.

    Public helper used by the formatting sub-module.
    """
    match = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", range_a1)
    if not match:
        raise ValueError(f"Invalid range format: {range_a1}")

    start_col, start_row, end_col, end_row = match.groups()

    def col_to_index(col: str) -> int:
        result = 0
        for char in col:
            result = result * 26 + ord(char) - ord("A") + 1
        return result - 1

    return {
        "sheetId": sheet_id,
        "startRowIndex": int(start_row) - 1,
        "endRowIndex": int(end_row),
        "startColumnIndex": col_to_index(start_col),
        "endColumnIndex": col_to_index(end_col) + 1,
    }


# =============================================================================
# Handler functions
# =============================================================================


async def _list_spreadsheet_sheets(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all sheets/tabs in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}"
    params = {"fields": "spreadsheetId,properties.title,sheets.properties"}
    response = await svc._make_request("GET", url, params=params)

    sheets = []
    for sheet in response.get("sheets", []):
        props = sheet.get("properties", {})
        sheets.append(
            {
                "sheetId": props.get("sheetId"),
                "name": props.get("title", ""),
                "index": props.get("index", 0),
                "sheetType": props.get("sheetType", "GRID"),
                "rowCount": props.get("gridProperties", {}).get("rowCount"),
                "columnCount": props.get("gridProperties", {}).get("columnCount"),
            }
        )

    return {
        "spreadsheet_id": response.get("spreadsheetId"),
        "title": response.get("properties", {}).get("title", ""),
        "sheets": sheets,
        "count": len(sheets),
    }


async def _get_sheet_values(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get values from a specific sheet/tab in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    cell_range = arguments.get("range", "A:ZZ")

    range_notation = f"'{sheet_name}'!{cell_range}"
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}/values/{range_notation}"
    params = {"valueRenderOption": "FORMATTED_VALUE"}
    response = await svc._make_request("GET", url, params=params)

    values = response.get("values", [])
    if not values:
        return {
            "spreadsheet_id": spreadsheet_id,
            "sheet_name": sheet_name,
            "range": response.get("range", range_notation),
            "data": "",
            "row_count": 0,
            "message": "No data found in the specified range.",
        }

    csv_lines = []
    for row in values:
        escaped_row = []
        for cell in row:
            cell_str = str(cell) if cell is not None else ""
            if "," in cell_str or '"' in cell_str or "\n" in cell_str:
                cell_str = '"' + cell_str.replace('"', '""') + '"'
            escaped_row.append(cell_str)
        csv_lines.append(",".join(escaped_row))

    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "range": response.get("range", range_notation),
        "data": "\n".join(csv_lines),
        "row_count": len(values),
        "column_count": max(len(row) for row in values) if values else 0,
    }


async def _get_spreadsheet_data(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get all sheets and their data from a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    max_rows = arguments.get("max_rows", 1000)

    sheets_response = await _list_spreadsheet_sheets(svc, {"spreadsheet_id": spreadsheet_id})
    sheet_names = [sheet["name"] for sheet in sheets_response.get("sheets", [])]

    if not sheet_names:
        return {
            "spreadsheet_id": spreadsheet_id,
            "title": sheets_response.get("title", ""),
            "sheets": {},
            "count": 0,
            "message": "No sheets found in this spreadsheet.",
        }

    ranges = [f"'{name}'!A1:ZZ{max_rows}" for name in sheet_names]
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}/values:batchGet"
    params = {"ranges": ranges, "valueRenderOption": "FORMATTED_VALUE"}
    response = await svc._make_request("GET", url, params=params)

    sheets_data = {}
    value_ranges = response.get("valueRanges", [])
    for i, sheet_name in enumerate(sheet_names):
        if i < len(value_ranges):
            values = value_ranges[i].get("values", [])
            csv_lines = []
            for row in values:
                escaped_row = []
                for cell in row:
                    cell_str = str(cell) if cell is not None else ""
                    if "," in cell_str or '"' in cell_str or "\n" in cell_str:
                        cell_str = '"' + cell_str.replace('"', '""') + '"'
                    escaped_row.append(cell_str)
                csv_lines.append(",".join(escaped_row))
            sheets_data[sheet_name] = {
                "data": "\n".join(csv_lines),
                "row_count": len(values),
                "column_count": max(len(row) for row in values) if values else 0,
            }
        else:
            sheets_data[sheet_name] = {"data": "", "row_count": 0, "column_count": 0}

    return {
        "spreadsheet_id": spreadsheet_id,
        "title": sheets_response.get("title", ""),
        "sheets": sheets_data,
        "count": len(sheets_data),
    }


async def _create_spreadsheet(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new Google Spreadsheet."""
    title = arguments["title"]
    sheet_names = arguments.get("sheet_names", ["Sheet1"])

    sheets = [{"properties": {"title": name, "index": i}} for i, name in enumerate(sheet_names)]
    body = {"properties": {"title": title}, "sheets": sheets}

    url = f"{SHEETS_API_BASE}/spreadsheets"
    response = await svc._make_request("POST", url, json_data=body)

    spreadsheet_id = response.get("spreadsheetId", "")
    return {
        "spreadsheet_id": spreadsheet_id,
        "title": response.get("properties", {}).get("title", title),
        "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "sheets": [s.get("properties", {}).get("title", "") for s in response.get("sheets", [])],
    }


async def _update_sheet_values(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update values in a specific range of a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    cell_range = arguments["range"]
    values = arguments["values"]

    range_notation = f"'{sheet_name}'!{cell_range}"
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}/values/{range_notation}"
    params = {"valueInputOption": "USER_ENTERED"}
    body = {"range": range_notation, "values": values}
    response = await svc._make_request("PUT", url, params=params, json_data=body)

    return {
        "spreadsheet_id": spreadsheet_id,
        "updated_range": response.get("updatedRange", range_notation),
        "updated_rows": response.get("updatedRows", 0),
        "updated_columns": response.get("updatedColumns", 0),
        "updated_cells": response.get("updatedCells", 0),
    }


async def _append_sheet_values(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Append rows to the end of data in a Google Spreadsheet sheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    values = arguments["values"]

    range_notation = f"'{sheet_name}'"
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}/values/{range_notation}:append"
    params = {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
    body = {"values": values}
    response = await svc._make_request("POST", url, params=params, json_data=body)

    updates = response.get("updates", {})
    return {
        "spreadsheet_id": spreadsheet_id,
        "updated_range": updates.get("updatedRange", ""),
        "updated_rows": updates.get("updatedRows", 0),
        "updated_columns": updates.get("updatedColumns", 0),
        "updated_cells": updates.get("updatedCells", 0),
    }


async def _clear_sheet_values(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Clear values from a specific range in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    cell_range = arguments["range"]

    range_notation = f"'{sheet_name}'!{cell_range}"
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}/values/{range_notation}:clear"
    response = await svc._make_request("POST", url)

    return {
        "spreadsheet_id": spreadsheet_id,
        "cleared_range": response.get("clearedRange", range_notation),
    }


async def _add_sheet(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add a new sheet/tab to an existing Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    title = arguments["title"]

    sheet_properties: dict[str, Any] = {"title": title}
    if "index" in arguments:
        sheet_properties["index"] = arguments["index"]
    if "tab_color" in arguments:
        sheet_properties["tabColor"] = arguments["tab_color"]

    request_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": sheet_properties,
                }
            }
        ]
    }

    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}:batchUpdate"
    response = await svc._make_request("POST", url, json_data=request_body)

    replies = response.get("replies", [])
    added_sheet_props: dict[str, Any] = {}
    if replies and "addSheet" in replies[0]:
        added_sheet_props = replies[0]["addSheet"].get("properties", {})

    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_id": added_sheet_props.get("sheetId"),
        "title": added_sheet_props.get("title", title),
        "index": added_sheet_props.get("index"),
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Sheets core handlers."""
    return {
        "list_spreadsheet_sheets": lambda args: _list_spreadsheet_sheets(svc, args),
        "get_sheet_values": lambda args: _get_sheet_values(svc, args),
        "get_spreadsheet_data": lambda args: _get_spreadsheet_data(svc, args),
        "create_spreadsheet": lambda args: _create_spreadsheet(svc, args),
        "update_sheet_values": lambda args: _update_sheet_values(svc, args),
        "append_sheet_values": lambda args: _append_sheet_values(svc, args),
        "clear_sheet_values": lambda args: _clear_sheet_values(svc, args),
        "add_sheet": lambda args: _add_sheet(svc, args),
    }
