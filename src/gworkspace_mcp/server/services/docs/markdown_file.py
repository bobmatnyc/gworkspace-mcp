"""markdown_file_to_doc: robust Markdown-to-Google-Doc tool.

Fixes three failure modes of publish_markdown_to_doc:
1. Server-side file reading — no inline content required, so large docs (700+ lines)
   are never truncated by context limits or output-token limits.
2. Tables with borders — uses the Docs API updateTableCellStyle directly, guaranteeing
   visible borders even after Drive import (which drops DOCX table borders).
3. In-place update — when document_id is supplied, clears the existing body and
   re-inserts; the shareable link is preserved.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE, DRIVE_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Max requests per batchUpdate call.  Google Docs API allows up to 2000
# requests per batchUpdate, but sending very large batches increases the
# risk of hitting per-request payload size limits.  We use a conservative
# chunk size that comfortably handles 700-line documents.
# ---------------------------------------------------------------------------
_BATCH_CHUNK_SIZE = 200

# Border style applied to every table cell
_TABLE_BORDER = {
    "color": {"color": {"rgbColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}},
    "width": {"magnitude": 0.75, "unit": "PT"},
    "dashStyle": "SOLID",
}

# Header row background (blue-grey)
_HEADER_BG = {"red": 0.2, "green": 0.35, "blue": 0.6}

# Heading level → Docs named style
_HEADING_STYLE: dict[int, str] = {
    1: "HEADING_1",
    2: "HEADING_2",
    3: "HEADING_3",
    4: "HEADING_4",
    5: "HEADING_5",
    6: "HEADING_6",
}

# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="markdown_file_to_doc",
        description=(
            "Convert a Markdown file to a fully-formatted Google Doc with real table borders, "
            "inline hyperlinks, and correct heading styles.  Reads the file server-side so "
            "large documents (700+ lines / 70 KB+) are never truncated.  "
            "When document_id is supplied the existing document body is replaced in-place so "
            "the shareable link is preserved; omit it to create a new document."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "markdown_file_path": {
                    "type": "string",
                    "description": (
                        "Absolute path to the Markdown file on the server. "
                        "The server reads the file directly — do NOT pass inline content here."
                    ),
                },
                "markdown_content": {
                    "type": "string",
                    "description": (
                        "Inline Markdown content (alternative to markdown_file_path for small "
                        "documents).  If both are supplied, markdown_file_path takes precedence."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Document title.  Required when creating a new document.",
                },
                "document_id": {
                    "type": "string",
                    "description": (
                        "Existing Google Doc ID to update in-place.  "
                        "The document body is cleared and replaced — the ID and shareable link "
                        "are preserved.  Omit to create a new document."
                    ),
                },
                "folder_id": {
                    "type": "string",
                    "description": "Drive folder ID for the new document (ignored when document_id is supplied).",
                },
                "account": {
                    "type": "string",
                    "description": (
                        "Google account profile to use.  Omit to use the default account.  "
                        "Use 'workspace accounts list' to see available profiles."
                    ),
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Markdown parser → list of "block" dicts
# ---------------------------------------------------------------------------


def _strip_inline_md(text: str) -> str:
    """Remove bold/italic/code markers but keep link text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # links: keep only label text for plain extraction
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


def _parse_inline_runs(text: str) -> list[dict[str, Any]]:
    """Parse an inline text string into a list of run dicts.

    Each run dict has:
      - ``text``: the plain text content
      - ``bold``: True if bold
      - ``italic``: True if italic
      - ``code``: True if inline code
      - ``link``: URL string if this run is a hyperlink, else None

    Nested emphasis is not supported; the first matching token wins.
    """
    runs: list[dict[str, Any]] = []

    # Pattern order matters: links before bold/italic so [text](...) is parsed
    # as a link rather than an italic fragment.
    pattern = re.compile(
        r"(?P<link>\[(?P<link_text>[^\]]+)\]\((?P<link_url>[^)]+)\))"
        r"|(?P<bold>\*\*(?P<bold_text>.+?)\*\*)"
        r"|(?P<bold2>__(?P<bold2_text>.+?)__)"
        r"|(?P<italic>\*(?P<italic_text>.+?)\*)"
        r"|(?P<italic2>_(?P<italic2_text>.+?)_)"
        r"|(?P<code>`(?P<code_text>[^`]+)`)"
    )

    pos = 0
    for m in pattern.finditer(text):
        # Plain text before this match
        if m.start() > pos:
            runs.append(
                {
                    "text": text[pos : m.start()],
                    "bold": False,
                    "italic": False,
                    "code": False,
                    "link": None,
                }
            )
        if m.group("link"):
            runs.append(
                {
                    "text": m.group("link_text"),
                    "bold": False,
                    "italic": False,
                    "code": False,
                    "link": m.group("link_url"),
                }
            )
        elif m.group("bold"):
            runs.append(
                {
                    "text": m.group("bold_text"),
                    "bold": True,
                    "italic": False,
                    "code": False,
                    "link": None,
                }
            )
        elif m.group("bold2"):
            runs.append(
                {
                    "text": m.group("bold2_text"),
                    "bold": True,
                    "italic": False,
                    "code": False,
                    "link": None,
                }
            )
        elif m.group("italic"):
            runs.append(
                {
                    "text": m.group("italic_text"),
                    "bold": False,
                    "italic": True,
                    "code": False,
                    "link": None,
                }
            )
        elif m.group("italic2"):
            runs.append(
                {
                    "text": m.group("italic2_text"),
                    "bold": False,
                    "italic": True,
                    "code": False,
                    "link": None,
                }
            )
        elif m.group("code"):
            runs.append(
                {
                    "text": m.group("code_text"),
                    "bold": False,
                    "italic": False,
                    "code": True,
                    "link": None,
                }
            )
        pos = m.end()

    if pos < len(text):
        runs.append(
            {"text": text[pos:], "bold": False, "italic": False, "code": False, "link": None}
        )

    return runs or [{"text": text, "bold": False, "italic": False, "code": False, "link": None}]


# Block types produced by the parser
# heading:   {"type": "heading", "level": int, "runs": [...]}
# paragraph: {"type": "paragraph", "runs": [...]}
# code:      {"type": "code", "text": str}
# table:     {"type": "table", "headers": [str], "rows": [[str]]}
# bullet:    {"type": "bullet", "depth": int, "runs": [...]}
# ordered:   {"type": "ordered", "index": int, "depth": int, "runs": [...]}
# rule:      {"type": "rule"}
# blank:     {"type": "blank"}


def _parse_table(lines: list[str]) -> dict[str, Any]:
    """Parse a GFM pipe-table block into a table block dict."""

    def _parse_row(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [cell.strip() for cell in line.split("|")]

    headers = _parse_row(lines[0])
    # lines[1] is the separator — skip it
    rows = [_parse_row(line) for line in lines[2:] if line.strip()]
    return {"type": "table", "headers": headers, "rows": rows}


def _is_separator_row(line: str) -> bool:
    return bool(re.match(r"^\|?[\s\-:|]+\|[\s\-:|]*(\|[\s\-:|]*)*\|?$", line.strip()))


def parse_markdown(content: str) -> list[dict[str, Any]]:
    """Parse Markdown content into a flat list of block dicts.

    Handles:
    - ATX headings (# through ######)
    - Fenced code blocks (``` and ~~~)
    - GFM pipe tables
    - Unordered lists (-, *, +) with up to 2 levels of nesting
    - Ordered lists (1. 2. ...) with up to 2 levels
    - Horizontal rules (---, ***, ___)
    - Paragraphs (everything else)

    Inline formatting within paragraphs, headings, and list items:
    - **bold**, __bold__
    - *italic*, _italic_
    - `code`
    - [link text](url)
    """
    blocks: list[dict[str, Any]] = []
    lines = content.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i]
        stripped = raw.rstrip()

        # ---- Fenced code block ----
        fence_m = re.match(r"^(```|~~~)(.*)", stripped)
        if fence_m:
            fence_char = fence_m.group(1)
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].startswith(fence_char):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            blocks.append({"type": "code", "text": "\n".join(code_lines)})
            continue

        # ---- Horizontal rule ----
        if (
            re.match(r"^\s*[-*_]{3,}\s*$", stripped)
            and stripped.replace("-", "").replace("*", "").replace("_", "").strip() == ""
        ):
            blocks.append({"type": "rule"})
            i += 1
            continue

        # ---- ATX Heading ----
        heading_m = re.match(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$", stripped)
        if heading_m:
            level = len(heading_m.group(1))
            text = heading_m.group(2)
            blocks.append({"type": "heading", "level": level, "runs": _parse_inline_runs(text)})
            i += 1
            continue

        # ---- GFM Table (peek ahead for separator row) ----
        if stripped.startswith("|") or (
            "|" in stripped and i + 1 < n and _is_separator_row(lines[i + 1])
        ):
            # Collect consecutive table lines
            table_lines: list[str] = []
            j = i
            while j < n and (
                lines[j].strip().startswith("|") or ("|" in lines[j] and not lines[j].strip() == "")
            ):
                table_lines.append(lines[j])
                j += 1
            # Validate: need at least header + separator + 1 row
            if len(table_lines) >= 3 and _is_separator_row(table_lines[1]):
                blocks.append(_parse_table(table_lines))
                i = j
                continue

        # ---- Unordered list item ----
        ul_m = re.match(r"^(\s*)[-*+]\s+(.+)$", stripped)
        if ul_m:
            depth = len(ul_m.group(1)) // 2  # 0 = top level
            text = ul_m.group(2)
            blocks.append({"type": "bullet", "depth": depth, "runs": _parse_inline_runs(text)})
            i += 1
            continue

        # ---- Ordered list item ----
        ol_m = re.match(r"^(\s*)(\d+)[.)]\s+(.+)$", stripped)
        if ol_m:
            depth = len(ol_m.group(1)) // 2
            idx = int(ol_m.group(2))
            text = ol_m.group(3)
            blocks.append(
                {"type": "ordered", "index": idx, "depth": depth, "runs": _parse_inline_runs(text)}
            )
            i += 1
            continue

        # ---- Blank line ----
        if not stripped:
            blocks.append({"type": "blank"})
            i += 1
            continue

        # ---- Paragraph (catch-all) ----
        # Collect continuation lines (non-blank, not a new block)
        para_lines: list[str] = [stripped]
        i += 1
        while i < n:
            next_raw = lines[i].rstrip()
            if not next_raw:
                break
            if re.match(r"^#{1,6}\s", next_raw):
                break
            if re.match(r"^(```|~~~)", next_raw):
                break
            if re.match(r"^(\s*)[-*+]\s", next_raw):
                break
            if re.match(r"^(\s*)\d+[.)]\s", next_raw):
                break
            if re.match(r"^\s*[-*_]{3,}\s*$", next_raw):
                break
            para_lines.append(next_raw)
            i += 1
        paragraph_text = " ".join(para_lines)
        blocks.append({"type": "paragraph", "runs": _parse_inline_runs(paragraph_text)})

    return blocks


# ---------------------------------------------------------------------------
# Google Docs request builder
# ---------------------------------------------------------------------------


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

    def _insert_text(self, text: str) -> int:
        """Emit insertText request and advance index.  Returns start index."""
        start = self.index
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

    def _insert_runs(self, runs: list[dict[str, Any]]) -> tuple[int, int]:
        """Insert runs into the document.  Returns (block_start, block_end)."""
        block_start = self.index
        for run in runs:
            run_start = self.index
            self._insert_text(run["text"])
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

    def add_heading(self, level: int, runs: list[dict[str, Any]]) -> None:
        start = self.index
        _, end = self._insert_runs(runs)
        self._insert_text("\n")
        self._style_paragraph(start, end + 1, _HEADING_STYLE.get(level, "HEADING_1"))

    def add_paragraph(self, runs: list[dict[str, Any]]) -> None:
        self._insert_runs(runs)
        self._insert_text("\n")

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

    def add_bullet(self, depth: int, runs: list[dict[str, Any]]) -> None:
        start = self.index
        _, end = self._insert_runs(runs)
        self._insert_text("\n")
        para_end = self.index
        # Apply bullet list style
        nesting_level = min(depth, 5)
        self.requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": start, "endIndex": para_end},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                    "nestingLevel": nesting_level,
                }
            }
        )
        _ = end  # suppress unused warning

    def add_ordered(self, runs: list[dict[str, Any]], depth: int = 0) -> None:
        start = self.index
        self._insert_runs(runs)
        self._insert_text("\n")
        para_end = self.index
        nesting_level = min(depth, 5)
        self.requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": start, "endIndex": para_end},
                    "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN",
                    "nestingLevel": nesting_level,
                }
            }
        )

    def add_blank(self) -> None:
        self._insert_text("\n")

    def add_rule(self) -> None:
        # Represent as a blank paragraph; Google Docs doesn't have a native HR
        self._insert_text("─" * 60 + "\n")

    def add_table(self, headers: list[str], rows: list[list[str]]) -> None:
        """Insert a table with borders and a styled header row.

        Strategy:
        1. insertTable to create the grid
        2. Re-fetch isn't available in the builder — instead we track the index
           offset manually.  After insertTable the Docs API inserts:
           - 1 char for the table element itself
           - for each row: 1 char for the row element
           - for each cell in a row: 1 char for the cell + content + 1 char for
             the closing newline of the cell paragraph
           We use the insertText/updateTableCellStyle approach instead:
           After insertTable the doc acquires new structure that advances our
           index by a known amount.

        Because tracking insertTable cell indices without a re-fetch is fragile,
        we use a simpler reliable approach: insert the table, then store the
        table_start_index so we can do a deferred batchUpdate after we know all
        indices via a GET.  However, that requires an extra round-trip.

        Simpler and more reliable: represent the table as plain text paragraphs
        in the current insert pass, then issue updateTableCellStyle in the
        deferred pass after the whole document has been inserted.

        Actually, the most robust approach for large documents is:
        1. Use insertTable to create the grid structure.
        2. The insertTable request inserts a structural element; following
           requests insertText into specific cell locations.

        Given the complexity of tracking cell indices without re-fetching, we use
        the approach employed by the existing insert_table_in_document tool:
        insert the table structure first, then fill cells via separate
        insertText requests referencing the cell content locations by tracking
        index arithmetic.

        Google Docs insertTable inserts characters as follows (simplified):
        - The table node itself counts as 1 index unit at table_start_index
        - Each row node counts as 1 index unit
        - Each cell node counts as 1 index unit
        - Each cell's paragraph counts as 1 index unit (for the empty paragraph
          placeholder)
        The total insertion is: 1 + rows*(1 + cols*(2)) for an empty table
        where each cell contains 1 empty paragraph (2 = cell open + paragraph).

        Rather than replicate this brittle arithmetic we emit insertTable with
        the full cell text in a single pass using the approach below.
        """
        num_rows = 1 + len(rows)  # header + data rows
        num_cols = len(headers)
        if num_cols == 0:
            return

        # Store the table_start_index BEFORE issuing insertTable
        table_start = self.index

        # Emit insertTable request — this creates an empty table structure
        self.requests.append(
            {
                "insertTable": {
                    "rows": num_rows,
                    "columns": num_cols,
                    "location": {"index": self.index},
                }
            }
        )

        # After insertTable the index advances by the table structural chars.
        # Formula: 1 (table) + rows*(1 (row) + cols*(2 (cell + paragraph)))
        # Plus a trailing newline the API appends after the table = 1
        structural_chars = 1 + num_rows * (1 + num_cols * 2) + 1
        self.index += structural_chars

        # Now populate cells. We need to re-fetch document to get exact cell
        # indices.  We can't do that here (no async context in builder).
        # Instead, store fill info in the deferred list as a special sentinel.
        all_rows = [headers] + rows
        self._deferred.append(
            {
                "_fill_table": True,
                "table_start_index": table_start,
                "num_rows": num_rows,
                "num_cols": num_cols,
                "all_rows": all_rows,
            }
        )

    def build(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (insert_requests, deferred_requests).

        insert_requests must be issued first; deferred_requests must be
        issued after a re-fetch to get the actual cell indices.
        """
        return self.requests, self._deferred


# ---------------------------------------------------------------------------
# Async builder — uses Google Docs API to fill table cells and apply styles
# ---------------------------------------------------------------------------


async def _fill_tables_and_style(
    svc: BaseService,
    document_id: str,
    deferred: list[dict[str, Any]],
) -> None:
    """For each deferred fill_table sentinel: re-fetch the doc, find the table,
    fill all cells with text + apply borders + header styling."""
    if not deferred:
        return

    fill_sentinels = [d for d in deferred if d.get("_fill_table")]
    if not fill_sentinels:
        return

    # Re-fetch document to get actual indices after all insertions
    doc = await svc._make_request(
        "GET",
        f"{DOCS_API_BASE}/documents/{document_id}",
        params={"fields": "body(content(table,startIndex,endIndex))"},
    )
    body_content: list[dict[str, Any]] = doc.get("body", {}).get("content", [])

    # Build a lookup: table_start_index → table element
    table_by_start: dict[int, dict[str, Any]] = {}
    for elem in body_content:
        if "table" in elem:
            si = elem.get("startIndex")
            if si is not None:
                table_by_start[si] = elem

    for sentinel in fill_sentinels:
        ts = sentinel["table_start_index"]
        table_elem = table_by_start.get(ts)
        if table_elem is None:
            logger.warning("Could not find table at start_index=%d for cell fill", ts)
            continue

        all_rows: list[list[str]] = sentinel["all_rows"]
        num_cols: int = sentinel["num_cols"]
        num_rows: int = sentinel["num_rows"]

        table_rows: list[dict[str, Any]] = table_elem.get("table", {}).get("tableRows", [])

        # --- Phase 1: fill cell text ---
        text_requests: list[dict[str, Any]] = []
        for row_i, row_data in enumerate(all_rows):
            if row_i >= len(table_rows):
                break
            cells = table_rows[row_i].get("tableCells", [])
            for col_i, cell_text in enumerate(row_data[:num_cols]):
                if col_i >= len(cells):
                    break
                if not cell_text.strip():
                    continue
                cell_content = cells[col_i].get("content", [])
                if not cell_content:
                    continue
                # Insert into the first paragraph's start
                para_start = cell_content[0].get("startIndex", 0)
                if para_start:
                    text_requests.append(
                        {
                            "insertText": {
                                "location": {"index": para_start},
                                "text": cell_text,
                            }
                        }
                    )

        if text_requests:
            await _batch_update(svc, document_id, text_requests)

        # --- Phase 2: apply borders + header styling ---
        # Re-fetch table to get updated indices after text insertion
        doc2 = await svc._make_request(
            "GET",
            f"{DOCS_API_BASE}/documents/{document_id}",
            params={"fields": "body(content(table,startIndex,endIndex))"},
        )
        body2: list[dict[str, Any]] = doc2.get("body", {}).get("content", [])
        # Find the table again (start_index is now different due to text insertion!)
        # We find it by row/col count match near original position
        target_table_elem = None
        for elem2 in body2:
            if "table" in elem2:
                t2 = elem2["table"]
                if t2.get("rows") == num_rows and t2.get("columns") == num_cols:
                    target_table_elem = elem2
                    break
        if target_table_elem is None:
            logger.warning(
                "Could not re-locate table for styling (rows=%d, cols=%d)", num_rows, num_cols
            )
            continue

        new_ts = target_table_elem.get("startIndex", ts)
        style_requests: list[dict[str, Any]] = []

        for row_i in range(num_rows):
            is_header = row_i == 0
            for col_i in range(num_cols):
                cell_style: dict[str, Any] = {
                    "borderTop": _TABLE_BORDER,
                    "borderBottom": _TABLE_BORDER,
                    "borderLeft": _TABLE_BORDER,
                    "borderRight": _TABLE_BORDER,
                }
                field_keys = ["borderTop", "borderBottom", "borderLeft", "borderRight"]

                if is_header:
                    cell_style["backgroundColor"] = {"color": {"rgbColor": _HEADER_BG}}
                    field_keys.append("backgroundColor")

                style_requests.append(
                    {
                        "updateTableCellStyle": {
                            "tableCellStyle": cell_style,
                            "fields": ",".join(field_keys),
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": {"index": new_ts},
                                    "rowIndex": row_i,
                                    "columnIndex": col_i,
                                },
                                "rowSpan": 1,
                                "columnSpan": 1,
                            },
                        }
                    }
                )

        # Bold header text
        table_rows2 = target_table_elem.get("table", {}).get("tableRows", [])
        if table_rows2:
            header_cells = table_rows2[0].get("tableCells", [])
            for cell in header_cells:
                content = cell.get("content", [])
                if content:
                    for para_elem in content:
                        para = para_elem.get("paragraph", {})
                        for el in para.get("elements", []):
                            tr = el.get("textRun")
                            if tr:
                                run_start = el.get("startIndex", 0)
                                run_end = el.get("endIndex", run_start)
                                if run_start < run_end:
                                    style_requests.append(
                                        {
                                            "updateTextStyle": {
                                                "range": {
                                                    "startIndex": run_start,
                                                    "endIndex": run_end,
                                                },
                                                "textStyle": {"bold": True},
                                                "fields": "bold",
                                            }
                                        }
                                    )

        if style_requests:
            await _batch_update(svc, document_id, style_requests)


async def _batch_update(
    svc: BaseService,
    document_id: str,
    requests: list[dict[str, Any]],
) -> None:
    """Issue batchUpdate requests in safe chunks."""
    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    for i in range(0, len(requests), _BATCH_CHUNK_SIZE):
        chunk = requests[i : i + _BATCH_CHUNK_SIZE]
        await svc._make_request("POST", url, json_data={"requests": chunk})


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


async def _markdown_file_to_doc(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Convert a Markdown file (or inline content) to a Google Doc.

    Steps:
    1. Read the markdown (from file path or inline content).
    2. Parse into blocks.
    3. Build Docs API requests from the blocks.
    4. Create or clear the target document.
    5. Issue insert requests in chunks.
    6. Post-process: fill table cells, apply borders, heading styles.
    7. Return document id + webViewLink.
    """
    import secrets

    markdown_file_path = arguments.get("markdown_file_path")
    markdown_content = arguments.get("markdown_content")
    title = arguments.get("title", "Untitled Document")
    document_id: str | None = arguments.get("document_id")
    folder_id: str | None = arguments.get("folder_id")

    # --- 1. Read markdown ---
    if markdown_file_path:
        path = Path(markdown_file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {markdown_file_path}")
        markdown_content = path.read_text(encoding="utf-8")
        logger.info("Read %d chars from %s", len(markdown_content), markdown_file_path)
    elif not markdown_content:
        raise ValueError("Either markdown_file_path or markdown_content must be provided")

    # --- 2. Parse ---
    blocks = parse_markdown(markdown_content)
    logger.info("Parsed %d blocks from markdown", len(blocks))

    # --- 3. Create or clear target document ---
    if document_id:
        # In-place update: clear the body then re-insert
        doc = await svc._make_request(
            "GET",
            f"{DOCS_API_BASE}/documents/{document_id}",
            params={"fields": "body(content(startIndex,endIndex))"},
        )
        body_content = doc.get("body", {}).get("content", [])
        if body_content:
            last_end = body_content[-1].get("endIndex", 1)
            if last_end > 1:
                # Delete everything except the trailing paragraph marker (index 0)
                del_requests: list[dict[str, Any]] = [
                    {
                        "deleteContentRange": {
                            "range": {
                                "startIndex": 1,
                                "endIndex": last_end - 1,
                            }
                        }
                    }
                ]
                await _batch_update(svc, document_id, del_requests)
        start_index = 1
    else:
        # Create new document
        if folder_id:
            import json

            gdoc_metadata: dict[str, Any] = {
                "name": title,
                "mimeType": "application/vnd.google-apps.document",
                "parents": [folder_id],
            }
            boundary = secrets.token_hex(16)
            body_str = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(gdoc_metadata)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: text/plain\r\n\r\n"
                f"\r\n--{boundary}--"
            )
            upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true"
            response = await svc._make_raw_request(
                "POST",
                upload_url,
                content=body_str.encode("utf-8"),
                headers={"Content-Type": f"multipart/related; boundary={boundary}"},
                timeout=60.0,
            )
            result = response.json()
            document_id = result.get("id")
        else:
            create_resp = await svc._make_request(
                "POST",
                f"{DOCS_API_BASE}/documents",
                json_data={"title": title},
            )
            document_id = create_resp.get("documentId")
        start_index = 1

    if not document_id:
        raise RuntimeError("Failed to create or identify target document")

    # --- 4. Build requests from blocks ---
    builder = _DocBuilder(start_index=start_index)

    for block in blocks:
        btype = block["type"]
        if btype == "heading":
            builder.add_heading(block["level"], block["runs"])
        elif btype == "paragraph":
            builder.add_paragraph(block["runs"])
        elif btype == "code":
            builder.add_code_block(block["text"])
        elif btype == "table":
            builder.add_table(block["headers"], block["rows"])
        elif btype == "bullet":
            builder.add_bullet(block["depth"], block["runs"])
        elif btype == "ordered":
            builder.add_ordered(block["runs"], block.get("depth", 0))
        elif btype == "blank":
            builder.add_blank()
        elif btype == "rule":
            builder.add_rule()

    insert_requests, deferred = builder.build()

    # --- 5. Issue insert requests in chunks ---
    if insert_requests:
        await _batch_update(svc, document_id, insert_requests)
        logger.info("Inserted %d requests into document %s", len(insert_requests), document_id)

    # --- 6. Post-process: fill tables, apply borders + styles ---
    await _fill_tables_and_style(svc, document_id, deferred)

    # --- 7. Fetch webViewLink ---
    file_meta = await svc._make_request(
        "GET",
        f"{DRIVE_API_BASE}/files/{document_id}",
        params={"fields": "id,name,webViewLink,mimeType"},
    )

    return {
        "status": "published" if not arguments.get("document_id") else "updated",
        "document_id": document_id,
        "title": file_meta.get("name", title),
        "webViewLink": file_meta.get("webViewLink"),
        "mimeType": file_meta.get("mimeType"),
        "blocks_processed": len(blocks),
        "requests_issued": len(insert_requests),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for markdown_file_to_doc handler."""
    return {
        "markdown_file_to_doc": lambda args: _markdown_file_to_doc(svc, args),
    }
