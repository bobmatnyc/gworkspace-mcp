"""format_document_tables: post-processing pass to add borders + content-aware widths.

Walks all tables in a Google Doc and for each table:
1. Applies visible borders to every cell (1pt solid, all four sides).
2. Styles the first (header) row: bold text + light-grey shading.
3. Sets per-column widths proportional to cell-content length, so text-heavy
   columns receive more space and narrow numeric/code columns stay compact.

Width algorithm (pure, testable via compute_content_aware_widths):
  - For each column compute weight = min(max_chars_in_column, CAP) with CAP=60.
  - Distribute usable_width across columns proportional to weights.
  - Clamp each column to MIN_COL (40pt) and renormalise so widths sum to usable_width.
  - usable_width is read from documentStyle (page_width - left_margin - right_margin),
    falling back to 468pt (US Letter with 1-inch margins).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Width algorithm constants
# ---------------------------------------------------------------------------
_CONTENT_CAP: int = 60  # max chars used for any single column weight
_MIN_COL_PT: float = 40.0  # hard minimum column width in points
_FALLBACK_WIDTH: float = 468.0  # US Letter minus 1-inch margins on each side

# Border style: 1pt solid dark-grey
_BORDER_COLOR: dict[str, float] = {"red": 0.4, "green": 0.4, "blue": 0.4}
_BORDER_WIDTH_PT: float = 1.0

# Header row styling
_HEADER_BG: dict[str, float] = {"red": 0.9, "green": 0.9, "blue": 0.9}  # light grey

# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="format_document_tables",
        description=(
            "Post-processing pass: walk ALL tables in a Google Doc and apply "
            "(1) visible 1pt solid borders on every cell, a bold+light-grey "
            "header row, and (2) content-aware column widths so text-heavy "
            "columns are wider than narrow numeric columns. "
            "Usable page width is read from the document's documentStyle; "
            "falls back to 468pt (US Letter, 1-inch margins). "
            "Idempotent — safe to call multiple times."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "account": {
                    "type": "string",
                    "description": (
                        "Google account profile to use. "
                        "Omit to use the default account. "
                        "Use 'workspace accounts list' to see available profiles."
                    ),
                },
            },
            "required": ["document_id"],
        },
    ),
]

# ---------------------------------------------------------------------------
# Pure helper: content-aware column width algorithm
# ---------------------------------------------------------------------------


def compute_content_aware_widths(
    table_cells: list[list[str]],
    usable_width: float,
    cap: int = _CONTENT_CAP,
    min_col_pt: float = _MIN_COL_PT,
) -> list[float]:
    """Return content-proportional column widths in PT.

    Parameters
    ----------
    table_cells:
        2-D list of cell text strings (row-major). May include the header row.
    usable_width:
        Available horizontal space in PT.
    cap:
        Maximum character count contribution per column (prevents one very
        long cell from dominating). Default 60.
    min_col_pt:
        Hard minimum column width in PT. Default 40.

    Returns
    -------
    list[float]
        One width per column.  Widths sum to ``usable_width``.
        Returns an empty list when ``table_cells`` is empty.
    """
    if not table_cells:
        return []

    num_cols = max(len(row) for row in table_cells)
    if num_cols == 0:
        return []

    # Compute per-column weight = min(max_chars, cap), at least 1
    weights: list[float] = []
    for col_idx in range(num_cols):
        max_chars = 1
        for row in table_cells:
            if col_idx < len(row):
                max_chars = max(max_chars, len(row[col_idx]))
        weights.append(float(min(max_chars, cap)))

    # Iterative min-clamp allocation:
    # Columns whose proportional share < min_col_pt receive min_col_pt exactly.
    # Their "reserved" width is subtracted from the budget, and the remainder is
    # redistributed proportionally among the unclamped columns.  Repeat until stable.
    final: list[float] = [0.0] * num_cols
    clamped_mask: list[bool] = [False] * num_cols
    remaining_width = usable_width

    for _ in range(num_cols + 1):  # at most num_cols iterations to reach stability
        free_weight = sum(w for i, w in enumerate(weights) if not clamped_mask[i])
        if free_weight <= 0:
            break

        # Provisional proportional allocation for free (unclamped) columns
        newly_clamped = False
        for i in range(num_cols):
            if clamped_mask[i]:
                continue
            provisional = remaining_width * weights[i] / free_weight
            if provisional < min_col_pt:
                final[i] = min_col_pt
                clamped_mask[i] = True
                remaining_width -= min_col_pt
                newly_clamped = True

        if not newly_clamped:
            # Stable: assign proportional widths to remaining free columns
            for i in range(num_cols):
                if not clamped_mask[i]:
                    final[i] = remaining_width * weights[i] / free_weight
            break

    # Handle any columns still at 0 (edge case: all remaining budget consumed)
    for i in range(num_cols):
        if final[i] == 0.0:
            final[i] = min_col_pt

    # Renormalise unclamped columns to ensure sum == usable_width exactly,
    # while never reducing clamped columns below their minimum.
    total_clamped = sum(final[i] for i in range(num_cols) if clamped_mask[i])
    free_cols = [i for i in range(num_cols) if not clamped_mask[i]]
    if free_cols:
        remaining_for_free = usable_width - total_clamped
        current_free_total = sum(final[i] for i in free_cols)
        if current_free_total > 0 and remaining_for_free > 0:
            scale = remaining_for_free / current_free_total
            for i in free_cols:
                final[i] = final[i] * scale

    return final


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_cell_text(cell: dict[str, Any]) -> str:
    """Return the concatenated plain text from a table cell."""
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


def _get_usable_width(doc: dict[str, Any]) -> float:
    """Extract usable page width from documentStyle, or return fallback."""
    doc_style = doc.get("documentStyle", {})
    page_size = doc_style.get("pageSize", {})
    page_width_obj = page_size.get("width", {})
    margin_left_obj = doc_style.get("marginLeft", {})
    margin_right_obj = doc_style.get("marginRight", {})

    page_width = page_width_obj.get("magnitude", 0.0)
    margin_left = margin_left_obj.get("magnitude", 0.0)
    margin_right = margin_right_obj.get("magnitude", 0.0)

    if page_width > 0 and (margin_left + margin_right) < page_width:
        return page_width - margin_left - margin_right

    return _FALLBACK_WIDTH


def _build_border_requests(
    table_start_index: int,
    num_rows: int,
    num_cols: int,
) -> list[dict[str, Any]]:
    """Build updateTableCellStyle requests for 1pt solid borders on all cells."""
    border_obj: dict[str, Any] = {
        "color": {"color": {"rgbColor": _BORDER_COLOR}},
        "width": {"magnitude": _BORDER_WIDTH_PT, "unit": "PT"},
        "dashStyle": "SOLID",
    }
    border_fields = "borderTop,borderBottom,borderLeft,borderRight"

    requests: list[dict[str, Any]] = []
    for row_idx in range(num_rows):
        for col_idx in range(num_cols):
            cell_style: dict[str, Any] = {
                "borderTop": border_obj,
                "borderBottom": border_obj,
                "borderLeft": border_obj,
                "borderRight": border_obj,
            }
            requests.append(
                {
                    "updateTableCellStyle": {
                        "tableCellStyle": cell_style,
                        "fields": border_fields,
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
            )
    return requests


def _build_header_requests(
    table_start_index: int,
    num_cols: int,
    header_cell_ranges: list[tuple[int, int]],
) -> list[dict[str, Any]]:
    """Build requests for header row: light-grey background + bold text.

    Why: Applies bold to the *full* text of each header cell, not just its
    first character.  The caller provides (startIndex, endIndex) pairs that
    span the entire paragraph element so every character is bolded.
    What: Emits one updateTableCellStyle (background) per column and one
    updateTextStyle (bold) per non-empty header cell.
    Test: Construct a doc body with a 2-col table whose header cells contain
    multi-char text; assert each bold range has endIndex > startIndex + 1.
    """
    requests: list[dict[str, Any]] = []

    # Background colour on each header cell
    for col_idx in range(num_cols):
        cell_style: dict[str, Any] = {
            "backgroundColor": {"color": {"rgbColor": _HEADER_BG}},
        }
        requests.append(
            {
                "updateTableCellStyle": {
                    "tableCellStyle": cell_style,
                    "fields": "backgroundColor",
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": table_start_index},
                            "rowIndex": 0,
                            "columnIndex": col_idx,
                        },
                        "rowSpan": 1,
                        "columnSpan": 1,
                    },
                }
            }
        )

    # Bold the full text of each header cell using (startIndex, endIndex) ranges
    for start_idx, end_idx in header_cell_ranges:
        if start_idx > 0 and end_idx > start_idx:
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": start_idx, "endIndex": end_idx},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                }
            )

    return requests


def _build_column_width_requests(
    table_start_index: int,
    widths: list[float],
) -> list[dict[str, Any]]:
    """Build updateTableColumnProperties requests for fixed column widths."""
    requests: list[dict[str, Any]] = []
    for col_idx, width_pt in enumerate(widths):
        requests.append(
            {
                "updateTableColumnProperties": {
                    "tableStartLocation": {"index": table_start_index},
                    "columnIndices": [col_idx],
                    "tableColumnProperties": {
                        "widthType": "FIXED_WIDTH",
                        "width": {"magnitude": width_pt, "unit": "PT"},
                    },
                    "fields": "widthType,width",
                }
            }
        )
    return requests


def _find_header_cell_indices(
    body_content: list[dict[str, Any]],
    table_start_index: int,
) -> list[tuple[int, int]]:
    """Return (startIndex, endIndex) pairs for the first paragraph of each cell in row 0.

    Why: Callers need both boundaries to bold the *full* header-cell text rather
    than just its first character.
    What: Walks body content to find the table at table_start_index, then for
    each cell in the header row returns (content[0].startIndex, content[0].endIndex).
    Test: Build a minimal body_content dict with a table at a known startIndex
    containing 2-char and 5-char header cells; assert returned endIndex values
    equal startIndex + len(cell_text) + 1 (the trailing newline char).
    """
    for element in body_content:
        tbl = element.get("table")
        if tbl is None:
            continue
        if element.get("startIndex") != table_start_index:
            continue
        rows = tbl.get("tableRows", [])
        if not rows:
            return []
        header_ranges: list[tuple[int, int]] = []
        for cell in rows[0].get("tableCells", []):
            content = cell.get("content", [])
            if content:
                start = content[0].get("startIndex", 0)
                end = content[0].get("endIndex", start)
                header_ranges.append((start, end))
            else:
                header_ranges.append((0, 0))
        return header_ranges
    return []


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

_BATCH_CHUNK = 200  # stay well under the 2000-request batchUpdate limit


async def _format_document_tables(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id: str = arguments["document_id"]
    doc_url = f"{DOCS_API_BASE}/documents/{document_id}"
    batch_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    # Fetch the document once
    doc = await svc._make_request("GET", doc_url)

    usable_width = _get_usable_width(doc)
    body_content: list[dict[str, Any]] = doc.get("body", {}).get("content", [])

    # Gather all tables
    tables: list[dict[str, Any]] = []
    for element in body_content:
        tbl = element.get("table")
        if tbl is None:
            continue
        t_rows = tbl.get("tableRows", [])
        t_num_rows = len(t_rows)
        t_num_cols = max((len(r.get("tableCells", [])) for r in t_rows), default=0)
        if t_num_rows == 0 or t_num_cols == 0:
            continue

        # Collect cell texts for width computation
        t_cell_texts: list[list[str]] = []
        for row in t_rows:
            t_cell_texts.append([_extract_cell_text(cell) for cell in row.get("tableCells", [])])

        tables.append(
            {
                "start_index": element["startIndex"],
                "num_rows": t_num_rows,
                "num_cols": t_num_cols,
                "cell_texts": t_cell_texts,
            }
        )

    if not tables:
        return {
            "status": "no_tables_found",
            "document_id": document_id,
            "tables_processed": 0,
        }

    total_requests_sent = 0
    tables_processed = 0

    for table_info in tables:
        tsi: int = table_info["start_index"]
        num_rows: int = table_info["num_rows"]
        num_cols: int = table_info["num_cols"]
        cell_texts: list[list[str]] = table_info["cell_texts"]

        all_requests: list[dict[str, Any]] = []

        # 1. Borders on all cells
        all_requests.extend(_build_border_requests(tsi, num_rows, num_cols))

        # 2. Header row styling — need fresh doc body to get cell content indices
        #    For the first table pass we can reuse body_content; subsequent tables
        #    may have been modified by prior batches (but only style/width, not text
        #    positions, so indices remain stable).
        header_cell_ranges = _find_header_cell_indices(body_content, tsi)
        all_requests.extend(_build_header_requests(tsi, num_cols, header_cell_ranges))

        # 3. Content-aware column widths
        widths = compute_content_aware_widths(cell_texts, usable_width)
        all_requests.extend(_build_column_width_requests(tsi, widths))

        # Send in chunks to respect batchUpdate size limits
        for chunk_start in range(0, len(all_requests), _BATCH_CHUNK):
            chunk = all_requests[chunk_start : chunk_start + _BATCH_CHUNK]
            await svc._make_request("POST", batch_url, json_data={"requests": chunk})
            total_requests_sent += len(chunk)

        tables_processed += 1
        logger.debug(
            "format_document_tables: table at index %d formatted (%d rows x %d cols, widths=%s)",
            tsi,
            num_rows,
            num_cols,
            [round(w, 1) for w in widths],
        )

    return {
        "status": "formatted",
        "document_id": document_id,
        "document_url": f"https://docs.google.com/document/d/{document_id}/edit",
        "tables_processed": tables_processed,
        "usable_width_pt": usable_width,
        "total_requests_sent": total_requests_sent,
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for table-format handlers."""
    return {
        "format_document_tables": lambda args: _format_document_tables(svc, args),
    }
