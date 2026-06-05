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
