"""``_DocBuilder``: builds Google Docs batchUpdate requests from block IR.

Relocated verbatim from ``markdown_file.py`` (the same relocate-and-re-export
pattern Phase A used for ``sync.blocks``) so both the create/rebuild path
(``markdown_file._markdown_file_to_doc``) and the Phase B diff/patch path
(``sync.patch_planner``) can import it directly without a circular import —
``patch_planner`` needs ``_DocBuilder`` to render insert/style requests for new
or replaced blocks, and ``markdown_file`` needs ``patch_planner`` for its
default in-place-update path, so ``_DocBuilder`` cannot live in either module
depending on the other. ``markdown_file`` re-imports this class (and
``_RULE_BORDER``) — NOT a fork — so its existing tests/callers keep working
unchanged.
"""

from __future__ import annotations

from typing import Any

from gworkspace_mcp.server.services.docs.sync.blocks import _HEADING_STYLE

# Horizontal-rule border style applied via ``paragraphStyle.borderBottom`` (a
# real Docs paragraph-border idiom) so the serializer can decode a rule from an
# unambiguous structural signal rather than a fragile text sentinel.
_RULE_BORDER = {
    "color": {"color": {"rgbColor": {"red": 0.6, "green": 0.6, "blue": 0.6}}},
    "width": {"magnitude": 1, "unit": "PT"},
    "padding": {"magnitude": 1, "unit": "PT"},
    "dashStyle": "SOLID",
}


class _DocBuilder:
    """Builds a list of Google Docs batchUpdate requests from parsed blocks.

    Tracks the current insert index so requests are issued in document order.
    All text is inserted via insertText requests first; then styling requests
    (updateParagraphStyle, updateTextStyle, updateTableCellStyle) are appended.

    Importantly: ALL text inserts must come before ALL style requests within
    a chunk if we're building a fresh document from index=1.  For safety we
    keep them interleaved per block — this is correct for sequential processing.
    """

    def __init__(self, start_index: int = 1) -> None:
        self.index = start_index
        self.requests: list[dict[str, Any]] = []
        # Deferred table style requests (issued after all insertions for a table)
        self._deferred: list[dict[str, Any]] = []

    def _flush_deferred(self) -> None:
        self.requests.extend(self._deferred)
        self._deferred = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _insert_text(self, text: str, style_only: bool = False) -> int:
        """Emit insertText request and advance index.  Returns start index.

        ``style_only=True`` advances ``self.index`` (so downstream range math
        stays correct) but skips emitting the ``insertText`` request itself.
        This lets callers reuse this class's exact run-walking/index-tracking
        logic to *reapply styling* over text that is already present in the
        document (e.g. patch_planner's scoped inline-edit path, which edits
        only a changed span and then re-derives style requests for the whole
        paragraph without re-inserting its unchanged text).
        """
        start = self.index
        if not style_only:
            self.requests.append(
                {
                    "insertText": {
                        "location": {"index": self.index},
                        "text": text,
                    }
                }
            )
        self.index += len(text)
        return start

    def _style_paragraph(self, start: int, end: int, named_style: str) -> None:
        self.requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": named_style},
                    "fields": "namedStyleType",
                }
            }
        )

    def _style_text_run(
        self,
        start: int,
        end: int,
        bold: bool = False,
        italic: bool = False,
        code: bool = False,
        link: str | None = None,
    ) -> None:
        if start >= end:
            return
        text_style: dict[str, Any] = {}
        fields: list[str] = []
        if bold:
            text_style["bold"] = True
            fields.append("bold")
        if italic:
            text_style["italic"] = True
            fields.append("italic")
        if code:
            text_style["weightedFontFamily"] = {"fontFamily": "Courier New"}
            fields.append("weightedFontFamily")
        if link:
            text_style["link"] = {"url": link}
            fields.append("link")
        if not fields:
            return
        self.requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "textStyle": text_style,
                    "fields": ",".join(fields),
                }
            }
        )

    def _insert_runs(self, runs: list[dict[str, Any]], style_only: bool = False) -> tuple[int, int]:
        """Insert runs into the document.  Returns (block_start, block_end)."""
        block_start = self.index
        for run in runs:
            run_start = self.index
            self._insert_text(run["text"], style_only=style_only)
            run_end = self.index
            if run["bold"] or run["italic"] or run["code"] or run["link"]:
                self._style_text_run(
                    run_start,
                    run_end,
                    bold=run["bold"],
                    italic=run["italic"],
                    code=run["code"],
                    link=run["link"],
                )
        return block_start, self.index

    # ------------------------------------------------------------------
    # Block handlers
    # ------------------------------------------------------------------

    def add_heading(self, level: int, runs: list[dict[str, Any]], style_only: bool = False) -> None:
        start = self.index
        _, end = self._insert_runs(runs, style_only=style_only)
        self._insert_text("\n", style_only=style_only)
        self._style_paragraph(start, end + 1, _HEADING_STYLE.get(level, "HEADING_1"))

    def add_paragraph(self, runs: list[dict[str, Any]], style_only: bool = False) -> None:
        self._insert_runs(runs, style_only=style_only)
        self._insert_text("\n", style_only=style_only)

    def add_code_block(self, text: str) -> None:
        # Insert code text with monospace font, paragraph as NORMAL_TEXT
        start = self.index
        code_text = text + "\n"
        self._insert_text(code_text)
        end = self.index
        # Apply monospace to the whole block
        self.requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "textStyle": {"weightedFontFamily": {"fontFamily": "Courier New"}},
                    "fields": "weightedFontFamily",
                }
            }
        )

    def add_bullet(self, depth: int, runs: list[dict[str, Any]], style_only: bool = False) -> None:
        start = self.index
        _, end = self._insert_runs(runs, style_only=style_only)
        self._insert_text("\n", style_only=style_only)
        para_end = self.index
        # Apply bullet list style.
        # Note: createParagraphBullets only accepts range + bulletPreset;
        # nestingLevel is NOT a valid field and causes a 400 Bad Request.
        # Indentation for nested bullets uses updateParagraphStyle below.
        self.requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": start, "endIndex": para_end},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )
        # Indent nested bullets via paragraph indentation (18pt per level)
        if depth > 0:
            indent_pts = depth * 18.0
            self.requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": para_end},
                        "paragraphStyle": {
                            "indentStart": {"magnitude": indent_pts, "unit": "PT"},
                            "indentFirstLine": {"magnitude": indent_pts, "unit": "PT"},
                        },
                        "fields": "indentStart,indentFirstLine",
                    }
                }
            )
        _ = end  # suppress unused warning

    def add_ordered(
        self,
        runs: list[dict[str, Any]],
        depth: int = 0,
        style_only: bool = False,
    ) -> None:
        start = self.index
        self._insert_runs(runs, style_only=style_only)
        self._insert_text("\n", style_only=style_only)
        para_end = self.index
        # Note: createParagraphBullets only accepts range + bulletPreset.
        self.requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": start, "endIndex": para_end},
                    "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN",
                }
            }
        )
        # Indent nested ordered lists
        if depth > 0:
            indent_pts = depth * 18.0
            self.requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": para_end},
                        "paragraphStyle": {
                            "indentStart": {"magnitude": indent_pts, "unit": "PT"},
                            "indentFirstLine": {"magnitude": indent_pts, "unit": "PT"},
                        },
                        "fields": "indentStart,indentFirstLine",
                    }
                }
            )

    def add_blank(self) -> None:
        self._insert_text("\n")

    def add_rule(self) -> None:
        # Google Docs has no native horizontal-rule primitive.  Instead of the
        # old fragile text sentinel ("─" * 60), emit an empty paragraph carrying
        # a bottom border (a real Docs paragraph-border idiom).  This renders as
        # a horizontal line AND gives the serializer an unambiguous structural
        # signal (paragraphStyle.borderBottom on an empty paragraph) to decode a
        # rule on the way back — no string matching required.
        start = self.index
        self._insert_text("\n")
        end = self.index
        self.requests.append(
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start, "endIndex": end},
                    "paragraphStyle": {"borderBottom": _RULE_BORDER},
                    "fields": "borderBottom",
                }
            }
        )

    def add_table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Insert a table with borders and a styled header row.

        Why: Emitting an insertTable request creates the empty grid structure;
        cell text is filled later via a deferred re-fetch pass so exact indices
        are known.  Emitting post-table content in the same batchUpdate would
        require an accurate structural-size estimate for every possible table
        shape.  Instead, the builder records a ``_fill_table`` sentinel and the
        handler processes each table as its own pass (insert → fill → re-fetch
        → continue), preventing index drift for content that follows a table.

        What: Appends an insertTable request and a ``_fill_table`` sentinel to
        ``_deferred``.  Does NOT advance ``self.index`` because the handler
        will re-fetch the document end index after each table fill and supply
        a fresh start_index to a new builder for subsequent blocks.

        Test: Build a heading + table + trailing paragraph; assert the trailing
        paragraph's insertText index is strictly greater than the table's
        insertTable index plus the table skeleton size.
        """
        num_rows = 1 + len(rows)  # header + data rows
        num_cols = len(headers)
        if num_cols == 0:
            return

        # Emit insertTable request — this creates an empty table structure.
        # We intentionally do NOT advance self.index here.  The handler
        # processes blocks in table-bounded segments; after each table is filled
        # it re-fetches the document's true end index and starts a new builder
        # for the next segment, eliminating any arithmetic-estimate drift.
        self.requests.append(
            {
                "insertTable": {
                    "rows": num_rows,
                    "columns": num_cols,
                    "location": {"index": self.index},
                }
            }
        )

        all_rows = [headers] + rows
        self._deferred.append(
            {
                "_fill_table": True,
                "num_rows": num_rows,
                "num_cols": num_cols,
                "all_rows": all_rows,
            }
        )

    def build(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (insert_requests, deferred_requests).

        Why: Separating insert requests from deferred fill sentinels allows the
        handler to batch-insert structural content first, then fill table cells
        using re-fetched indices.
        What: Returns the accumulated request list and the deferred sentinel list.
        Test: Call build() after add_heading + add_table; assert insert_requests
        contains insertText and insertTable entries, deferred contains a
        _fill_table sentinel.

        insert_requests must be issued first; deferred_requests must be
        issued after a re-fetch to get the actual cell indices.
        """
        return self.requests, self._deferred
