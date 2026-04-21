"""Google Sheets formatting sub-module: cell formatting, number format, merge, column width, charts."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import SHEETS_API_BASE
from gworkspace_mcp.server.services.sheets.core import a1_to_grid_range, get_sheet_id

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="format_sheet",
        description=(
            "Apply formatting to cells in a Google Spreadsheet. "
            "All actions require spreadsheet_id and sheet_name. "
            "Actions: 'format_cells' (range required; background_color, font_color, bold, italic, borders optional), "
            "'set_number_format' (range and format_type required; pattern optional for custom formats), "
            "'merge' (range required; merge_type optional, unmerge=true to unmerge), "
            "'set_column_width' (start_column_index and end_column_index required; width_pixels or auto_resize=true)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Formatting action to perform",
                    "enum": ["format_cells", "set_number_format", "merge", "set_column_width"],
                },
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab (e.g., 'Sheet1')",
                },
                "range": {
                    "type": "string",
                    "description": "Cell range in A1 notation (e.g., 'A1:C3'). Required for format_cells, set_number_format, and merge.",
                },
                "background_color": {
                    "type": "object",
                    "description": "Background color in RGB format (format_cells only)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "font_color": {
                    "type": "object",
                    "description": "Font color in RGB format (format_cells only)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "bold": {
                    "type": "boolean",
                    "description": "Apply bold formatting (format_cells only)",
                },
                "italic": {
                    "type": "boolean",
                    "description": "Apply italic formatting (format_cells only)",
                },
                "borders": {
                    "type": "object",
                    "description": "Border configuration (format_cells only)",
                    "properties": {
                        "style": {
                            "type": "string",
                            "enum": ["SOLID", "DASHED", "DOTTED"],
                        },
                        "width": {"type": "integer", "minimum": 1, "maximum": 3},
                        "color": {
                            "type": "object",
                            "properties": {
                                "red": {"type": "number", "minimum": 0, "maximum": 1},
                                "green": {"type": "number", "minimum": 0, "maximum": 1},
                                "blue": {"type": "number", "minimum": 0, "maximum": 1},
                            },
                        },
                    },
                },
                "format_type": {
                    "type": "string",
                    "description": "Type of number format (set_number_format only)",
                    "enum": ["CURRENCY", "PERCENTAGE", "DATE", "TIME", "NUMBER", "TEXT"],
                },
                "pattern": {
                    "type": "string",
                    "description": "Custom format pattern (set_number_format only, e.g., '$#,##0.00', '0.00%', 'yyyy-mm-dd')",
                },
                "merge_type": {
                    "type": "string",
                    "description": "Type of merge operation (merge only)",
                    "enum": ["MERGE_ALL", "MERGE_COLUMNS", "MERGE_ROWS"],
                },
                "unmerge": {
                    "type": "boolean",
                    "description": "Whether to unmerge cells instead of merging (merge only)",
                    "default": False,
                },
                "start_column_index": {
                    "type": "integer",
                    "description": "Start column index, 0-based where A=0 (set_column_width only)",
                },
                "end_column_index": {
                    "type": "integer",
                    "description": "End column index, 0-based exclusive (set_column_width only)",
                },
                "width_pixels": {
                    "type": "integer",
                    "description": "Column width in pixels (set_column_width only; optional when auto_resize is true)",
                },
                "auto_resize": {
                    "type": "boolean",
                    "description": "Auto-resize columns to fit content (set_column_width only)",
                    "default": False,
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action", "spreadsheet_id", "sheet_name"],
        },
    ),
    Tool(
        name="create_chart",
        description="Create a basic chart (bar, line, pie) in a Google Spreadsheet.",
        inputSchema={
            "type": "object",
            "properties": {
                "spreadsheet_id": {
                    "type": "string",
                    "description": "Google Spreadsheet ID (from the URL)",
                },
                "sheet_name": {
                    "type": "string",
                    "description": "Name of the sheet/tab containing the data",
                },
                "chart_type": {
                    "type": "string",
                    "description": "Type of chart to create",
                    "enum": ["COLUMN", "BAR", "LINE", "PIE", "AREA"],
                },
                "data_range": {
                    "type": "string",
                    "description": "Data range in A1 notation (e.g., 'A1:C10')",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                },
                "position_row": {
                    "type": "integer",
                    "description": "Row to position the chart (0-based, optional)",
                    "default": 0,
                },
                "position_column": {
                    "type": "integer",
                    "description": "Column to position the chart (0-based, optional)",
                    "default": 0,
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": [
                "spreadsheet_id",
                "sheet_name",
                "chart_type",
                "data_range",
                "title",
            ],
        },
    ),
]


# =============================================================================
# Handler functions
# =============================================================================


async def _format_cells(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Apply formatting to cells in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    range_a1 = arguments["range"]

    sheet_info = await get_sheet_id(svc, spreadsheet_id, sheet_name)
    sheet_id = sheet_info["sheet_id"]
    grid_range = await a1_to_grid_range(range_a1, sheet_id)

    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}:batchUpdate"
    requests = []
    cell_format: dict[str, Any] = {}

    if "background_color" in arguments:
        cell_format["backgroundColor"] = arguments["background_color"]
    if "font_color" in arguments:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["foregroundColor"] = arguments["font_color"]
    if "bold" in arguments:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["bold"] = arguments["bold"]
    if "italic" in arguments:
        cell_format["textFormat"] = cell_format.get("textFormat", {})
        cell_format["textFormat"]["italic"] = arguments["italic"]
    if "borders" in arguments:
        borders = arguments["borders"]
        cell_format["borders"] = {
            "top": borders,
            "bottom": borders,
            "left": borders,
            "right": borders,
        }

    if cell_format:
        requests.append(
            {
                "repeatCell": {
                    "range": grid_range,
                    "cell": {"userEnteredFormat": cell_format},
                    "fields": "userEnteredFormat",
                }
            }
        )

    if requests:
        await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "formatted",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "range": range_a1,
        "applied_formatting": list(cell_format.keys()),
    }


async def _set_number_format(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Set number formatting for cells in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    range_a1 = arguments["range"]
    format_type = arguments["format_type"]
    pattern = arguments.get("pattern")

    sheet_info = await get_sheet_id(svc, spreadsheet_id, sheet_name)
    sheet_id = sheet_info["sheet_id"]
    grid_range = await a1_to_grid_range(range_a1, sheet_id)

    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}:batchUpdate"

    number_format: dict[str, Any] = {"type": format_type}
    if pattern:
        number_format["pattern"] = pattern
    elif format_type == "CURRENCY":
        number_format["pattern"] = "$#,##0.00"
    elif format_type == "PERCENTAGE":
        number_format["pattern"] = "0.00%"
    elif format_type == "DATE":
        number_format["pattern"] = "yyyy-mm-dd"

    request_body = {
        "requests": [
            {
                "repeatCell": {
                    "range": grid_range,
                    "cell": {"userEnteredFormat": {"numberFormat": number_format}},
                    "fields": "userEnteredFormat.numberFormat",
                }
            }
        ]
    }
    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "formatted",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "range": range_a1,
        "format_type": format_type,
        "pattern": number_format.get("pattern"),
    }


async def _merge_cells(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Merge or unmerge cells in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    range_a1 = arguments["range"]
    merge_type = arguments.get("merge_type", "MERGE_ALL")
    unmerge = arguments.get("unmerge", False)

    sheet_info = await get_sheet_id(svc, spreadsheet_id, sheet_name)
    sheet_id = sheet_info["sheet_id"]
    grid_range = await a1_to_grid_range(range_a1, sheet_id)

    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}:batchUpdate"

    if unmerge:
        request_body: dict[str, Any] = {"requests": [{"unmergeCells": {"range": grid_range}}]}
    else:
        request_body = {
            "requests": [
                {
                    "mergeCells": {
                        "range": grid_range,
                        "mergeType": merge_type,
                    }
                }
            ]
        }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "unmerged" if unmerge else "merged",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "range": range_a1,
        "merge_type": merge_type if not unmerge else None,
    }


async def _set_column_width(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Set column width in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    start_column_index = arguments["start_column_index"]
    end_column_index = arguments["end_column_index"]
    width_pixels = arguments.get("width_pixels")
    auto_resize = arguments.get("auto_resize", False)

    sheet_info = await get_sheet_id(svc, spreadsheet_id, sheet_name)
    sheet_id = sheet_info["sheet_id"]

    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}:batchUpdate"

    request_body: dict[str, Any]
    if auto_resize:
        request_body = {
            "requests": [
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_column_index,
                            "endIndex": end_column_index,
                        }
                    }
                }
            ]
        }
    else:
        if not width_pixels:
            raise ValueError("width_pixels is required when auto_resize is False")
        request_body = {
            "requests": [
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": start_column_index,
                            "endIndex": end_column_index,
                        },
                        "properties": {"pixelSize": width_pixels},
                        "fields": "pixelSize",
                    }
                }
            ]
        }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "updated",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "column_range": {"start": start_column_index, "end": end_column_index},
        "auto_resize": auto_resize,
        "width_pixels": width_pixels if not auto_resize else None,
    }


async def _create_chart(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a chart in a Google Spreadsheet."""
    spreadsheet_id = arguments["spreadsheet_id"]
    sheet_name = arguments["sheet_name"]
    chart_type = arguments["chart_type"]
    data_range = arguments["data_range"]
    title = arguments["title"]
    position_row = arguments.get("position_row", 0)
    position_column = arguments.get("position_column", 0)

    sheet_info = await get_sheet_id(svc, spreadsheet_id, sheet_name)
    sheet_id = sheet_info["sheet_id"]
    grid_range = await a1_to_grid_range(data_range, sheet_id)

    url = f"{SHEETS_API_BASE}/spreadsheets/{spreadsheet_id}:batchUpdate"
    chart_id = uuid.uuid4().hex[:8]

    request_body = {
        "requests": [
            {
                "addChart": {
                    "chart": {
                        "chartId": chart_id,
                        "spec": {
                            "title": title,
                            "basicChart": {
                                "chartType": chart_type,
                                "axis": [
                                    {"position": "BOTTOM_AXIS", "title": ""},
                                    {"position": "LEFT_AXIS", "title": ""},
                                ],
                                "domains": [{"domain": {"sourceRange": {"sources": [grid_range]}}}],
                                "series": [{"series": {"sourceRange": {"sources": [grid_range]}}}],
                            },
                        },
                        "position": {
                            "overlayPosition": {
                                "anchorCell": {
                                    "sheetId": sheet_id,
                                    "rowIndex": position_row,
                                    "columnIndex": position_column,
                                }
                            }
                        },
                    }
                }
            }
        ]
    }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "created",
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "chart_id": chart_id,
        "chart_type": chart_type,
        "title": title,
        "data_range": data_range,
        "position": {"row": position_row, "column": position_column},
    }


async def _format_sheet(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch format_sheet actions to the appropriate handler."""
    action = arguments.get("action")
    if action == "format_cells":
        return await _format_cells(svc, arguments)
    elif action == "set_number_format":
        return await _set_number_format(svc, arguments)
    elif action == "merge":
        return await _merge_cells(svc, arguments)
    elif action == "set_column_width":
        return await _set_column_width(svc, arguments)
    else:
        raise ValueError(
            f"Unknown action '{action}'. Must be one of: format_cells, set_number_format, merge, set_column_width"
        )


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Sheets formatting handlers."""
    return {
        "format_sheet": lambda args: _format_sheet(svc, args),
        "create_chart": lambda args: _create_chart(svc, args),
    }
