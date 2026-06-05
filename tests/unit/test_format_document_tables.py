"""Unit tests for format_document_tables — pure width-algorithm coverage.

Tests verify (offline, no API calls):
  (a) widths sum to usable_width (within floating-point tolerance)
  (b) the column with the longest max-cell-text receives the largest width
  (c) min-clamp (40pt) is respected for all columns
  (d) edge cases: single column, equal columns, empty rows, cap enforcement
"""

from __future__ import annotations

import pytest

from gworkspace_mcp.server.services.docs.table_format import (
    _FALLBACK_WIDTH,
    _MIN_COL_PT,
    TOOLS,
    _build_header_requests,
    _find_header_cell_indices,
    compute_content_aware_widths,
)

USABLE = 468.0  # standard US-Letter usable width


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatDocumentTablesTool:
    def test_tool_registered(self) -> None:
        names = [t.name for t in TOOLS]
        assert "format_document_tables" in names

    def test_tool_description_nonempty(self) -> None:
        tool = next(t for t in TOOLS if t.name == "format_document_tables")
        assert len(tool.description) > 20

    def test_schema_requires_document_id(self) -> None:
        tool = next(t for t in TOOLS if t.name == "format_document_tables")
        assert "document_id" in tool.inputSchema.get("required", [])

    def test_schema_has_account(self) -> None:
        tool = next(t for t in TOOLS if t.name == "format_document_tables")
        assert "account" in tool.inputSchema.get("properties", {})


# ---------------------------------------------------------------------------
# Width algorithm: compute_content_aware_widths
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestComputeContentAwareWidths:
    # ------------------------------------------------------------------
    # (a) Widths sum to usable_width
    # ------------------------------------------------------------------

    def test_widths_sum_to_usable_width_basic(self) -> None:
        data = [
            ["Work Type", "Description", "%"],
            ["Feature", "New user-facing functionality", "45"],
            ["Bug Fix", "Defect resolution", "30"],
        ]
        widths = compute_content_aware_widths(data, USABLE)
        assert abs(sum(widths) - USABLE) < 0.5, f"sum={sum(widths)} != {USABLE}"

    def test_widths_sum_to_usable_width_single_col(self) -> None:
        data = [["Header"], ["Some text"], ["More"]]
        widths = compute_content_aware_widths(data, USABLE)
        assert len(widths) == 1
        assert abs(widths[0] - USABLE) < 0.5

    def test_widths_sum_to_usable_width_many_cols(self) -> None:
        data = [["A", "BB", "CCC", "DDDD", "EEEEE", "FFFFFF"]]
        widths = compute_content_aware_widths(data, USABLE)
        assert abs(sum(widths) - USABLE) < 0.5

    def test_widths_sum_with_custom_usable_width(self) -> None:
        data = [["Col1", "Col2"], ["abc", "x"]]
        usable = 300.0
        widths = compute_content_aware_widths(data, usable)
        assert abs(sum(widths) - usable) < 0.5

    # ------------------------------------------------------------------
    # (b) Longest column gets the largest width
    # ------------------------------------------------------------------

    def test_longest_column_gets_largest_width(self) -> None:
        """'Work Type' column has much longer text than '%' column."""
        data = [
            ["Work Type", "% Commits"],
            ["Feature Development & new capability work", "45%"],
            ["Bug Fix and Maintenance", "30%"],
            ["Technical Debt Reduction", "25%"],
        ]
        widths = compute_content_aware_widths(data, USABLE)
        # col 0 ("Work Type") has much longer cells than col 1 ("% Commits")
        assert (
            widths[0] > widths[1]
        ), f"Expected col0 ({widths[0]:.1f}pt) > col1 ({widths[1]:.1f}pt)"

    def test_widest_col_in_multi_col_table(self) -> None:
        """The column with the globally longest cell should be widest."""
        data = [
            ["Short", "Very long description that goes on and on", "Num"],
            ["A", "Another moderately long description here", "1"],
            ["B", "Yet another entry", "2"],
        ]
        widths = compute_content_aware_widths(data, USABLE)
        max_idx = widths.index(max(widths))
        assert max_idx == 1, f"Expected column 1 to be widest, got {max_idx}"

    def test_equal_columns_get_equal_widths(self) -> None:
        """When all columns have identical content lengths, widths should be equal."""
        data = [["ABC", "DEF", "GHI"], ["123", "456", "789"]]
        widths = compute_content_aware_widths(data, USABLE)
        assert len({round(w, 1) for w in widths}) == 1, f"Expected equal widths, got {widths}"

    # ------------------------------------------------------------------
    # (c) Minimum clamp respected
    # ------------------------------------------------------------------

    def test_min_clamp_respected(self) -> None:
        """Even a one-character column must be >= _MIN_COL_PT."""
        data = [["A" * 100, "x"], ["B" * 100, "y"]]
        widths = compute_content_aware_widths(data, USABLE)
        for i, w in enumerate(widths):
            assert w >= _MIN_COL_PT, f"col {i} width {w:.1f}pt < min {_MIN_COL_PT}pt"

    def test_custom_min_clamp(self) -> None:
        custom_min = 50.0
        data = [["LongText" * 10, "x"]]
        widths = compute_content_aware_widths(data, USABLE, min_col_pt=custom_min)
        for w in widths:
            assert w >= custom_min

    # ------------------------------------------------------------------
    # (d) Cap enforcement
    # ------------------------------------------------------------------

    def test_cap_prevents_one_column_domination(self) -> None:
        """A cell with 1000 chars should be treated the same as one with cap chars."""
        data_capped = [["X" * 200, "ShortCol"]]
        data_exact = [["X" * 60, "ShortCol"]]  # 60 == default CAP
        widths_capped = compute_content_aware_widths(data_capped, USABLE, cap=60)
        widths_exact = compute_content_aware_widths(data_exact, USABLE, cap=60)
        assert (
            abs(widths_capped[0] - widths_exact[0]) < 0.5
        ), "Cap should make 200-char and 60-char columns produce equal weight"

    def test_cap_respected_for_all_cols(self) -> None:
        data = [["X" * 500, "Y" * 500, "Z" * 500]]
        widths = compute_content_aware_widths(data, USABLE, cap=60)
        # All three should be equal (all exceed cap)
        assert abs(widths[0] - widths[1]) < 0.5
        assert abs(widths[1] - widths[2]) < 0.5

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_table_returns_empty(self) -> None:
        widths = compute_content_aware_widths([], USABLE)
        assert widths == []

    def test_single_row_single_col(self) -> None:
        widths = compute_content_aware_widths([["text"]], USABLE)
        assert len(widths) == 1
        assert abs(widths[0] - USABLE) < 0.5

    def test_rows_with_varying_col_counts(self) -> None:
        """Ragged rows — num_cols taken from the widest row."""
        data = [["A", "B", "C"], ["X"]]  # row 1 only has 1 cell
        widths = compute_content_aware_widths(data, USABLE)
        assert len(widths) == 3
        assert abs(sum(widths) - USABLE) < 0.5

    def test_fallback_width_constant(self) -> None:
        assert _FALLBACK_WIDTH == 468.0

    def test_min_col_pt_constant(self) -> None:
        assert _MIN_COL_PT == 40.0


# ---------------------------------------------------------------------------
# Header bold-range tests (finding: endIndex must cover full cell text)
# ---------------------------------------------------------------------------


def _make_body_content(
    table_start: int,
    header_cells: list[tuple[int, int]],
) -> list[dict]:
    """Build a minimal body_content list with one table at table_start.

    Each item in header_cells is (start_index, end_index) for that cell's
    first paragraph content element.
    """
    cells = []
    for start, end in header_cells:
        cells.append(
            {
                "content": [
                    {
                        "startIndex": start,
                        "endIndex": end,
                        "paragraph": {"elements": []},
                    }
                ]
            }
        )
    return [
        {
            "startIndex": table_start,
            "table": {
                "tableRows": [
                    {"tableCells": cells},
                ]
            },
        }
    ]


@pytest.mark.unit
class TestHeaderBoldRange:
    """Regression: updateTextStyle for header cells must span the full cell text.

    Previously endIndex was start_idx + 1, which only bolded the first character.
    """

    def test_bold_range_spans_full_header_text(self) -> None:
        """For a 5-char header cell the bold range endIndex must be > startIndex + 1."""
        table_start = 10
        # Cell with text spanning indices 12..17 (5 chars: "Hello" + trailing newline)
        body_content = _make_body_content(table_start, [(12, 17)])
        ranges = _find_header_cell_indices(body_content, table_start)
        assert len(ranges) == 1
        start, end = ranges[0]
        assert (
            end > start + 1
        ), f"endIndex ({end}) must be > startIndex + 1 ({start + 1}) for a multi-char header cell"

    def test_bold_request_uses_full_range(self) -> None:
        """_build_header_requests must emit endIndex equal to the cell's endIndex."""
        table_start = 5
        # Two header cells: "Name" (4 chars, indices 7..12), "Value" (5 chars, 14..20)
        cell_ranges: list[tuple[int, int]] = [(7, 12), (14, 20)]
        requests = _build_header_requests(table_start, 2, cell_ranges)
        bold_reqs = [
            r
            for r in requests
            if "updateTextStyle" in r and r["updateTextStyle"]["textStyle"].get("bold")
        ]
        assert len(bold_reqs) == 2
        # First cell: endIndex must be 12 (not 7+1=8)
        r0 = bold_reqs[0]["updateTextStyle"]["range"]
        assert r0["startIndex"] == 7
        assert r0["endIndex"] == 12, f"Expected endIndex=12, got {r0['endIndex']}"
        # Second cell: endIndex must be 20 (not 14+1=15)
        r1 = bold_reqs[1]["updateTextStyle"]["range"]
        assert r1["startIndex"] == 14
        assert r1["endIndex"] == 20, f"Expected endIndex=20, got {r1['endIndex']}"

    def test_two_col_table_bold_ranges_both_multichar(self) -> None:
        """All columns in a 2-col header table must have bold endIndex > startIndex + 1."""
        table_start = 3
        header_cells = [(5, 13), (15, 25)]  # "ColName" (8 chars), "LongHeader" (10 chars)
        ranges = _find_header_cell_indices(
            _make_body_content(table_start, header_cells), table_start
        )
        for i, (start, end) in enumerate(ranges):
            assert end > start + 1, f"Column {i}: endIndex={end} must be > startIndex+1={start + 1}"


# ---------------------------------------------------------------------------
# Issue #24: compute_content_aware_widths overflow when all cols clamp to min
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContentAwareWidthsAllClamped:
    """#24: When num_cols * min_col_pt > usable_width, all columns clamp and
    sum(widths) previously exceeded usable_width.  After the fix, the function
    must proportionally scale all columns down so sum <= usable_width."""

    def test_many_cols_sum_does_not_exceed_usable_width(self) -> None:
        """15 columns, each 40pt min, total = 600pt > 468pt usable_width.

        Before the fix: sum(widths) == 15 * 40 == 600 > 468.
        After the fix:  sum(widths) <= 468 (within tiny float tolerance).
        """
        usable = 468.0
        num_cols = 15
        # All cells have the same short text so all weights are equal and all
        # columns clamp to min_col_pt.
        data = [["x"] * num_cols]
        widths = compute_content_aware_widths(data, usable)
        assert len(widths) == num_cols
        total = sum(widths)
        assert total <= usable + 1e-6, (
            f"sum(widths)={total:.4f} exceeds usable_width={usable}; "
            "all-clamped case must scale columns proportionally."
        )

    def test_many_cols_sum_matches_usable_width_closely(self) -> None:
        """Widths should sum to exactly usable_width (within float tolerance)."""
        usable = 468.0
        data = [["AB"] * 20]  # 20 cols, each 2 chars → all clamp to 40pt min
        widths = compute_content_aware_widths(data, usable)
        total = sum(widths)
        assert (
            abs(total - usable) < 0.5
        ), f"sum(widths)={total:.4f} should be close to {usable} (within 0.5pt)"

    def test_all_clamped_each_width_positive(self) -> None:
        """Every column width must be positive even when all clamp."""
        usable = 100.0
        data = [["x"] * 10]  # 10 cols, min=40 → total=400 >> 100
        widths = compute_content_aware_widths(data, usable, min_col_pt=40.0)
        for i, w in enumerate(widths):
            assert w > 0, f"Column {i} has non-positive width {w}"

    def test_normal_case_unchanged_by_fix(self) -> None:
        """When num_cols * min_col_pt <= usable_width the normal path is taken
        and the fix must not change the result."""
        usable = 468.0
        # 3 cols, one much wider — no all-clamp scenario
        data = [
            ["ShortCol", "A very long description column that has lots of text", "Num"],
            ["A", "Another moderately long description", "1"],
        ]
        widths = compute_content_aware_widths(data, usable)
        assert abs(sum(widths) - usable) < 0.5
        # The wide column must still be widest
        assert widths[1] > widths[0]
        assert widths[1] > widths[2]
