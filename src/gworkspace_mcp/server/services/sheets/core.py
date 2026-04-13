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
        name="get_spreadsheet",
        description=(
            "Read a Google Spreadsheet. "
            "action='list_sheets': list all tabs with their properties. "
            "action='get_sheet': read values from a specific sheet (requires sheet_name; range optional). "
            "action='get_all': batch-read all sheets and their data (max_rows optional, default 1000)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_sheets", "get_sheet", "get_all"],
                    "description": "Operation to perform",
                },
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Sheet/tab name — required for get_sheet",
                },
                "range": {
                    "type": "string",
                    "description": "A1 notation range (get_sheet only, default 'A:ZZ')",
                    "default": "A:ZZ",
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Max rows per sheet (get_all only, default 1000)",
                    "default": 1000,
                },
            },
            "required": ["action", "spreadsheet_id"],
        },
    ),
    Tool(
        name="manage_spreadsheet",
        description=(
            "Create or modify a Google Spreadsheet. "
            "action='create': create a new spreadsheet (title required; sheet_names optional). "
            "action='add_sheet': add a tab to an existing spreadsheet (spreadsheet_id and title required; "
            "index and tab_color optional)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "add_sheet"],
                    "description": "Operation to perform",
                },
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID — required for add_sheet",
                },
                "title": {
                    "type": "string",
                    "description": "Spreadsheet title (create) or new sheet/tab name (add_sheet)",
                },
                "sheet_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Initial tab names (create only, default ['Sheet1'])",
                },
                "index": {
                    "type": "integer",
                    "description": "0-based insertion position (add_sheet only, default: append)",
                },
                "tab_color": {
                    "type": "object",
                    "description": "RGB tab color, each component 0.0–1.0 (add_sheet only)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "required": ["action", "title"],
        },
    ),
    Tool(
        name="modify_sheet_values",
        description=(
            "Write or clear values in a Google Spreadsheet sheet. "
            "action='update': overwrite a range (range and values required). "
            "action='append': append rows after the last data row (values required). "
            "action='clear': clear values from a range, keeping formatting (range required)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["update", "append", "clear"],
                    "description": "Operation to perform",
                },
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab",
                },
                "range": {
                    "type": "string",
                    "description": "A1 notation range — required for update and clear",
                },
                "values": {
                    "type": "array",
                    "items": {"type": "array", "items": {}},
                    "description": "2D array of values (rows of cells) — required for update and append",
                },
            },
            "required": ["action", "spreadsheet_id", "sheet_name"],
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
    response = await svc._make_request(
        "GET", url, params={"fields": "sheets(properties(sheetId,title))"}
    )
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
# Private handler implementations
# =============================================================================


async def _list_spreadsheet_sheets(svc: BaseService, spreadsheet_id: str) -> dict[str, Any]:
    """List all sheets/tabs in a Google Spreadsheet."""
    _FIELDS = (
        "spreadsheetId,properties/title,"
        "sheets(properties(sheetId,title,index,sheetType,gridProperties,tabColor))"
    )
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}"
    params = {"fields": _FIELDS}
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


async def _get_sheet_values(
    svc: BaseService, spreadsheet_id: str, sheet_name: str, cell_range: str = "A:ZZ"
) -> dict[str, Any]:
    """Get values from a specific sheet/tab in a Google Spreadsheet."""
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


async def _get_spreadsheet_data(
    svc: BaseService, spreadsheet_id: str, max_rows: int = 1000
) -> dict[str, Any]:
    """Get all sheets and their data from a Google Spreadsheet in a single API call.

    Uses ``includeGridData=true`` on the spreadsheets.get endpoint so that both
    sheet metadata and cell values are returned together, reducing HTTP round-trips
    from 2 (metadata + batchGet) to 1.
    """
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}"
    params = {
        "includeGridData": "true",
        "fields": (
            "spreadsheetId,properties/title,"
            "sheets(properties(title,sheetId),data/rowData/values/formattedValue)"
        ),
    }
    response = await svc._make_request("GET", url, params=params)

    title = response.get("properties", {}).get("title", "")
    raw_sheets = response.get("sheets", [])

    if not raw_sheets:
        return {
            "spreadsheet_id": spreadsheet_id,
            "title": title,
            "sheets": {},
            "count": 0,
            "message": "No sheets found in this spreadsheet.",
        }

    sheets_data: dict[str, Any] = {}
    for sheet in raw_sheets:
        sheet_name = sheet.get("properties", {}).get("title", "")
        # data is a list of grid ranges; we only need the first one (the full grid)
        row_data = []
        sheet_data_list = sheet.get("data", [])
        if sheet_data_list:
            row_data = sheet_data_list[0].get("rowData", [])

        # Apply max_rows limit
        row_data = row_data[:max_rows]

        values: list[list[str]] = []
        for row in row_data:
            cells = row.get("values", [])
            values.append([c.get("formattedValue", "") or "" for c in cells])

        # Drop trailing empty rows introduced by includeGridData padding
        while values and all(cell == "" for cell in values[-1]):
            values.pop()

        csv_lines = []
        for row in values:
            escaped_row = []
            for cell_str in row:
                if "," in cell_str or '"' in cell_str or "\n" in cell_str:
                    cell_str = '"' + cell_str.replace('"', '""') + '"'
                escaped_row.append(cell_str)
            csv_lines.append(",".join(escaped_row))

        sheets_data[sheet_name] = {
            "data": "\n".join(csv_lines),
            "row_count": len(values),
            "column_count": max(len(row) for row in values) if values else 0,
        }

    return {
        "spreadsheet_id": spreadsheet_id,
        "title": title,
        "sheets": sheets_data,
        "count": len(sheets_data),
    }


async def _create_spreadsheet(
    svc: BaseService, title: str, sheet_names: list[str] | None = None
) -> dict[str, Any]:
    """Create a new Google Spreadsheet."""
    if sheet_names is None:
        sheet_names = ["Sheet1"]

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


async def _add_sheet(
    svc: BaseService,
    spreadsheet_id: str,
    title: str,
    index: int | None = None,
    tab_color: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a new sheet/tab to an existing Google Spreadsheet."""
    sheet_properties: dict[str, Any] = {"title": title}
    if index is not None:
        sheet_properties["index"] = index
    if tab_color is not None:
        sheet_properties["tabColor"] = tab_color

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


async def _update_sheet_values(
    svc: BaseService,
    spreadsheet_id: str,
    sheet_name: str,
    cell_range: str,
    values: list[list[Any]],
) -> dict[str, Any]:
    """Update values in a specific range of a Google Spreadsheet."""
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


async def _append_sheet_values(
    svc: BaseService,
    spreadsheet_id: str,
    sheet_name: str,
    values: list[list[Any]],
) -> dict[str, Any]:
    """Append rows to the end of data in a Google Spreadsheet sheet."""
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


async def _clear_sheet_values(
    svc: BaseService, spreadsheet_id: str, sheet_name: str, cell_range: str
) -> dict[str, Any]:
    """Clear values from a specific range in a Google Spreadsheet."""
    range_notation = f"'{sheet_name}'!{cell_range}"
    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}/values/{range_notation}:clear"
    response = await svc._make_request("POST", url)

    return {
        "spreadsheet_id": spreadsheet_id,
        "cleared_range": response.get("clearedRange", range_notation),
    }


# =============================================================================
# Consolidated action dispatchers
# =============================================================================


async def _get_spreadsheet(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch get_spreadsheet actions."""
    action = arguments["action"]
    spreadsheet_id = arguments["spreadsheet_id"]

    if action == "list_sheets":
        return await _list_spreadsheet_sheets(svc, spreadsheet_id)

    if action == "get_sheet":
        sheet_name = arguments.get("sheet_name")
        if not sheet_name:
            raise ValueError("sheet_name is required for action='get_sheet'")
        cell_range = arguments.get("range", "A:ZZ")
        return await _get_sheet_values(svc, spreadsheet_id, sheet_name, cell_range)

    if action == "get_all":
        max_rows = arguments.get("max_rows", 1000)
        return await _get_spreadsheet_data(svc, spreadsheet_id, max_rows)

    raise ValueError(f"Unknown action: {action!r}")


async def _manage_spreadsheet(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch manage_spreadsheet actions."""
    action = arguments["action"]
    title = arguments["title"]

    if action == "create":
        sheet_names = arguments.get("sheet_names")
        return await _create_spreadsheet(svc, title, sheet_names)

    if action == "add_sheet":
        spreadsheet_id = arguments.get("spreadsheet_id")
        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required for action='add_sheet'")
        index = arguments.get("index")
        tab_color = arguments.get("tab_color")
        return await _add_sheet(svc, spreadsheet_id, title, index, tab_color)

    raise ValueError(f"Unknown action: {action!r}")


async def _modify_sheet_values(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch modify_sheet_values actions."""
    action = arguments["action"]
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]

    if action == "update":
        cell_range = arguments.get("range")
        values = arguments.get("values")
        if not cell_range:
            raise ValueError("range is required for action='update'")
        if values is None:
            raise ValueError("values is required for action='update'")
        return await _update_sheet_values(svc, spreadsheet_id, sheet_name, cell_range, values)

    if action == "append":
        values = arguments.get("values")
        if values is None:
            raise ValueError("values is required for action='append'")
        return await _append_sheet_values(svc, spreadsheet_id, sheet_name, values)

    if action == "clear":
        cell_range = arguments.get("range")
        if not cell_range:
            raise ValueError("range is required for action='clear'")
        return await _clear_sheet_values(svc, spreadsheet_id, sheet_name, cell_range)

    raise ValueError(f"Unknown action: {action!r}")


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Sheets core handlers."""
    return {
        "get_spreadsheet": lambda args: _get_spreadsheet(svc, args),
        "manage_spreadsheet": lambda args: _manage_spreadsheet(svc, args),
        "modify_sheet_values": lambda args: _modify_sheet_values(svc, args),
    }
