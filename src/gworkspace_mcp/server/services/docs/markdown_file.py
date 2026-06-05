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

import json
import logging
import re
import secrets
import tempfile
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
            "the shareable link is preserved; omit it to create a new document.  "
            "REQUIRED: supply at least one of markdown_file_path (preferred for large files) "
            "or markdown_content (for small inline documents).  If both are provided, "
            "markdown_file_path takes precedence."
        ),
        inputSchema={
            "type": "object",
            "anyOf": [
                {"required": ["markdown_file_path"]},
                {"required": ["markdown_content"]},
            ],
            "properties": {
                "markdown_file_path": {
                    "type": "string",
                    "description": (
                        "Absolute path to the Markdown file on the server.  "
                        "The server reads the file directly — do NOT pass inline content here.  "
                        "Supply this OR markdown_content (at least one is required)."
                    ),
                },
                "markdown_content": {
                    "type": "string",
                    "description": (
                        "Inline Markdown content.  Alternative to markdown_file_path for small "
                        "documents.  Supply this OR markdown_file_path (at least one is required).  "
                        "If both are supplied, markdown_file_path takes precedence."
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

    Emphasis rules (to avoid over-matching stray * and ~):
    - ``*italic*`` / ``_italic_``: only when * or _ is adjacent to a
      non-whitespace character on both sides (i.e. cannot start/end with space).
    - ``~~strikethrough~~``: treated as literal (no Docs equivalent).
    - ``~text~``: treated as literal.
    """
    runs: list[dict[str, Any]] = []

    # Pattern order matters: links before bold/italic so [text](...) is parsed
    # as a link rather than an italic fragment.
    #
    # Italic patterns use word-boundary-like anchors:
    #   (?<!\s) before the closing delimiter — ensures the italic span does not
    #   end with whitespace (prevents matching "* stray star").
    #   (?!\s) after the opening delimiter — ensures the italic span does not
    #   start with whitespace.
    pattern = re.compile(
        r"(?P<link>\[(?P<link_text>[^\]]+)\]\((?P<link_url>[^)]+)\))"
        r"|(?P<bold>\*\*(?P<bold_text>\S.*?\S|\S)\*\*)"
        r"|(?P<bold2>__(?P<bold2_text>\S.*?\S|\S)__)"
        r"|(?P<italic>\*(?P<italic_text>\S.*?\S|\S)\*)"
        r"|(?P<italic2>_(?P<italic2_text>\S.*?\S|\S)_)"
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
            # Collect consecutive table lines.
            # A line is part of the table only when its stripped form starts
            # with "|" OR matches a GFM separator row.  A blank line or any
            # non-pipe-leading line terminates the table block, preventing
            # greedy absorption of prose that merely contains a "|" character.
            table_lines: list[str] = []
            j = i
            while j < n and (lines[j].strip().startswith("|") or _is_separator_row(lines[j])):
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
        # Collect continuation lines (non-blank, not a new block).
        # Hard line breaks: a line ending in two or more spaces (or backslash)
        # before its newline is a "hard break".  We split the paragraph into
        # sub-lines at those boundaries and emit a "\n" within the paragraph
        # rather than joining with a space.
        # We accumulate (line_text, hard_break) pairs.
        def _is_hard_break(raw_line: str) -> bool:
            return raw_line.endswith("  ") or raw_line.endswith("\\")

        para_raw_lines: list[tuple[str, bool]] = [(raw, _is_hard_break(raw))]
        i += 1
        while i < n:
            next_raw = lines[i]
            next_stripped = next_raw.rstrip()
            if not next_stripped:
                break
            if re.match(r"^#{1,6}\s", next_stripped):
                break
            if re.match(r"^(```|~~~)", next_stripped):
                break
            if re.match(r"^(\s*)[-*+]\s", next_stripped):
                break
            if re.match(r"^(\s*)\d+[.)]\s", next_stripped):
                break
            if re.match(r"^\s*[-*_]{3,}\s*$", next_stripped):
                break
            para_raw_lines.append((next_raw, _is_hard_break(next_raw)))
            i += 1

        # Build paragraph runs, honouring hard breaks.
        # A hard break inserts a literal "\n" run between sub-lines so the
        # DocBuilder emits separate line-break characters in the same paragraph.
        para_runs: list[dict[str, Any]] = []
        for idx, (raw_line, is_hard) in enumerate(para_raw_lines):
            line_text = raw_line.rstrip()  # strip trailing spaces / backslash
            if line_text.endswith("\\"):
                line_text = line_text[:-1]
            para_runs.extend(_parse_inline_runs(line_text))
            if is_hard and idx < len(para_raw_lines) - 1:
                # Insert a hard line-break run (literal newline within paragraph)
                para_runs.append(
                    {"text": "\n", "bold": False, "italic": False, "code": False, "link": None}
                )
            elif idx < len(para_raw_lines) - 1:
                # Soft continuation: join with a space
                para_runs.append(
                    {"text": " ", "bold": False, "italic": False, "code": False, "link": None}
                )

        blocks.append({"type": "paragraph", "runs": para_runs})

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

    def add_ordered(self, runs: list[dict[str, Any]], depth: int = 0) -> None:
        start = self.index
        self._insert_runs(runs)
        self._insert_text("\n")
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
        # Represent as a blank paragraph; Google Docs doesn't have a native HR
        self._insert_text("─" * 60 + "\n")

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

    # Collect tables in document order.  We match sentinels to tables by their
    # sequential position (first sentinel → first table, etc.) rather than by
    # start_index, because the stored table_start_index values come from the
    # builder's pre-insertion estimates which do not account for the pre-table
    # paragraph the API inserts, nor for index shifts caused by earlier inserts.
    doc_tables: list[dict[str, Any]] = [elem for elem in body_content if "table" in elem]

    if len(doc_tables) != len(fill_sentinels):
        logger.warning(
            "Table count mismatch: doc has %d tables, builder has %d sentinels",
            len(doc_tables),
            len(fill_sentinels),
        )

    for sentinel_idx, sentinel in enumerate(fill_sentinels):
        if sentinel_idx >= len(doc_tables):
            logger.warning("No doc table for sentinel %d", sentinel_idx)
            continue
        table_elem = doc_tables[sentinel_idx]

        all_rows: list[list[str]] = sentinel["all_rows"]
        num_cols: int = sentinel["num_cols"]
        num_rows: int = sentinel["num_rows"]
        # Capture the table's actual start_index from the Phase 1 fetch.
        table_actual_start: int = table_elem.get("startIndex", 0)

        table_rows: list[dict[str, Any]] = table_elem.get("table", {}).get("tableRows", [])

        # --- Phase 1: fill cell text ---
        # IMPORTANT: insertText at a given index shifts all subsequent indices
        # forward by the length of the inserted text.  To avoid index drift we
        # must insert cells in REVERSE document order (last cell first).  That
        # way each insertion does not affect the indices of cells that still
        # need to be filled.
        cell_insertions: list[tuple[int, str]] = []  # (para_start_index, text)
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
                    cell_insertions.append((para_start, cell_text))

        # Sort descending by index so each insert does not shift later indices
        cell_insertions.sort(key=lambda x: x[0], reverse=True)
        text_requests: list[dict[str, Any]] = [
            {
                "insertText": {
                    "location": {"index": para_start},
                    "text": cell_text,
                }
            }
            for para_start, cell_text in cell_insertions
        ]

        if text_requests:
            await _batch_update(svc, document_id, text_requests)

        # --- Phase 2: apply borders + header styling ---
        # Re-fetch the single table (by its sentinel index in doc order) to get
        # updated cell indices after text was inserted into it.
        doc2 = await svc._make_request(
            "GET",
            f"{DOCS_API_BASE}/documents/{document_id}",
            params={"fields": "body(content(table,startIndex,endIndex))"},
        )
        body2: list[dict[str, Any]] = doc2.get("body", {}).get("content", [])
        # Tables in doc order; pick the same sentinel_idx-th table.
        # After inserting text into cells the table shifts forward, so we
        # can no longer rely on startIndex.  The table's relative position
        # (its ordinal in the document) is stable.
        doc_tables2 = [e for e in body2 if "table" in e]
        if sentinel_idx >= len(doc_tables2):
            logger.warning("Could not re-locate table %d for styling after text fill", sentinel_idx)
            continue
        target_table_elem = doc_tables2[sentinel_idx]
        if target_table_elem is None:
            logger.warning(
                "Could not re-locate table for styling (rows=%d, cols=%d)", num_rows, num_cols
            )
            continue

        new_ts = target_table_elem.get("startIndex", table_actual_start)
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
# Path-traversal guard helper
# ---------------------------------------------------------------------------


def _is_path_under(path: Path, root: Path) -> bool:
    """Return True if *path* is equal to or a descendant of *root*.

    Why: Prevents path-traversal attacks where a caller supplies a path like
    /etc/passwd to read arbitrary system files.
    What: Uses Path.is_relative_to (Python 3.9+) to check containment after
    both paths have been resolved (symlinks expanded, .. collapsed).
    Test: Assert True for Path('/home/user/docs/file.md') under Path('/home/user');
    assert False for Path('/etc/passwd') under Path('/home/user').
    """
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


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
    markdown_file_path = arguments.get("markdown_file_path")
    markdown_content = arguments.get("markdown_content")
    title = arguments.get("title", "Untitled Document")
    document_id: str | None = arguments.get("document_id")
    folder_id: str | None = arguments.get("folder_id")

    # --- 1. Read markdown ---
    if markdown_file_path:
        path = Path(markdown_file_path).resolve()
        # Path-traversal guard: only allow reads under the current working directory,
        # the user's home directory, or the system temp directory.
        # This blocks /etc/passwd and other system files while keeping the tool
        # practical for local MCP server usage (tmp files, home-dir docs, project files).
        allowed_roots = (
            Path.cwd().resolve(),
            Path.home().resolve(),
            Path(tempfile.gettempdir()).resolve(),
        )
        if not any(_is_path_under(path, root) for root in allowed_roots):
            raise ValueError(
                f"Path '{markdown_file_path}' is outside allowed directories "
                f"({', '.join(str(r) for r in allowed_roots)}). "
                "Only paths under the current working directory, your home directory, "
                "or the system temp directory are permitted."
            )
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

    # --- 4. Build and issue requests in table-bounded segments ---
    # Why: After insertTable, the deferred cell-fill pass inserts N characters
    # into the newly-created cells.  Any content emitted by the builder AFTER a
    # table uses self.index values derived from an arithmetic estimate of the
    # table's structural size — an estimate that cannot account for cell-text
    # insertions that have not yet happened.  Emitting all subsequent blocks in
    # a single batchUpdate therefore causes index drift: paragraphs land inside
    # the table rather than after it.
    #
    # Fix: split blocks into table-bounded segments.  For each segment we:
    #   (a) add all non-table blocks to a builder until we hit a table block,
    #   (b) add the table to the builder (which does NOT advance self.index),
    #   (c) issue all pending insert_requests,
    #   (d) call _fill_tables_and_style for just this table,
    #   (e) re-fetch the document's true end index,
    #   (f) start a fresh builder at that end index for the next segment.
    # Content that follows the last table (or a document with no tables) is
    # emitted in a single batchUpdate without any intervening re-fetch.

    total_insert_requests = 0
    current_index = start_index
    i = 0
    n_blocks = len(blocks)

    while i < n_blocks:
        builder = _DocBuilder(start_index=current_index)
        segment_deferred: list[dict[str, Any]] = []

        # Consume blocks until (and including) the next table, or until end.
        hit_table = False
        while i < n_blocks:
            block = blocks[i]
            btype = block["type"]
            i += 1
            if btype == "heading":
                builder.add_heading(block["level"], block["runs"])
            elif btype == "paragraph":
                builder.add_paragraph(block["runs"])
            elif btype == "code":
                builder.add_code_block(block["text"])
            elif btype == "table":
                builder.add_table(block["headers"], block["rows"])
                # Stop after the table so we can fill it and re-fetch before
                # emitting blocks that follow.
                hit_table = True
                break
            elif btype == "bullet":
                builder.add_bullet(block["depth"], block["runs"])
            elif btype == "ordered":
                builder.add_ordered(block["runs"], block.get("depth", 0))
            elif btype == "blank":
                builder.add_blank()
            elif btype == "rule":
                builder.add_rule()

        insert_requests, segment_deferred = builder.build()

        if insert_requests:
            await _batch_update(svc, document_id, insert_requests)
            total_insert_requests += len(insert_requests)
            logger.info(
                "Segment: inserted %d requests into document %s (hit_table=%s)",
                len(insert_requests),
                document_id,
                hit_table,
            )

        if hit_table and segment_deferred:
            await _fill_tables_and_style(svc, document_id, segment_deferred)

            if i < n_blocks:
                # Re-fetch the document's true end index so subsequent blocks
                # are anchored to the actual document state, not an estimate.
                doc_state = await svc._make_request(
                    "GET",
                    f"{DOCS_API_BASE}/documents/{document_id}",
                    params={"fields": "body(content(endIndex))"},
                )
                body_items = doc_state.get("body", {}).get("content", [])
                if body_items:
                    # The last structural element's endIndex is the document end.
                    # We insert starting at endIndex - 1 (before the final newline).
                    last_end = body_items[-1].get("endIndex", current_index + 1)
                    current_index = max(1, last_end - 1)
                else:
                    current_index += 1  # conservative fallback
                logger.info("Re-fetched document end index after table fill: %d", current_index)
    # --- 5. Fetch webViewLink ---
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
        "requests_issued": total_insert_requests,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for markdown_file_to_doc handler."""
    return {
        "markdown_file_to_doc": lambda args: _markdown_file_to_doc(svc, args),
    }
