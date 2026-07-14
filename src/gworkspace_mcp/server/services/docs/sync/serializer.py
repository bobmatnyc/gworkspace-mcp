"""Native Docs-JSON <-> block-IR <-> Markdown serializer (RFC section 2/3).

Two public entry points, both pure (no network, no side effects):

- ``doc_json_to_blocks(document)`` walks a ``documents.get`` response JSON and
  emits the *same* block dicts ``blocks.parse_markdown`` produces, so the two
  sides feed a common differ.
- ``blocks_to_markdown(blocks)`` renders a block list back to faithful GFM
  Markdown (headings, inline styles, links, code, ordered/unordered/nested
  lists, and pipe tables with a header separator row).

``markdown_to_blocks(markdown)`` is the Markdown -> block IR entry point; it is a
thin, explicit alias over ``blocks.parse_markdown`` so callers of this module
never have to reach across into ``markdown_file``.

Fidelity notes (see RFC section 3 "What's available vs lost"):

- Inline code has no native Docs concept. This codebase's encoder marks both
  fenced code blocks and inline code spans with ``weightedFontFamily ==
  "Courier New"``. Decode heuristic: a whole paragraph entirely in Courier New
  becomes a fenced ``code`` block; a partial Courier-New run inside an otherwise
  normal paragraph becomes an inline ``code`` run. This is inherently ambiguous
  for documents a human formatted in a monospace font for unrelated reasons.
- Horizontal rules are decoded from an empty paragraph carrying
  ``paragraphStyle.borderBottom`` (the idiom the encoder now emits) rather than
  a text sentinel.
- Table column widths, borders, and header shading are *derived formatting*:
  they are not represented in GFM and are recomputed on the next MD -> Doc sync,
  so they are intentionally dropped here.
- Merged table cells (``rowSpan``/``columnSpan`` > 1) are flattened lossily by
  duplicating the merged cell's text into each spanned grid position.
"""

from __future__ import annotations

from typing import Any

from gworkspace_mcp.server.services.docs.sync.blocks import (
    HEADING_LEVEL_BY_STYLE,
    parse_markdown,
)

# Glyph types that indicate an *ordered* list.  Everything else (glyph symbols
# such as bullets/discs/squares) is an unordered list.  Docs stores the glyph
# type per nesting level under ``document.lists[listId].listProperties``.
_ORDERED_GLYPH_TYPES = frozenset(
    {
        "DECIMAL",
        "ZERO_DECIMAL",
        "UPPER_ALPHA",
        "ALPHA",
        "UPPER_ROMAN",
        "ROMAN",
    }
)

# The font family this codebase's encoder uses to mark code (inline + fenced).
_CODE_FONT = "Courier New"


# =============================================================================
# Docs-JSON -> block IR
# =============================================================================


def doc_json_to_blocks(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Serialize a ``documents.get`` response JSON into the shared block IR.

    Walks ``document.body.content`` (the same shape ``_extract_doc_text`` and
    ``_extract_tables`` consume) and emits ``heading``/``paragraph``/``code``/
    ``bullet``/``ordered``/``rule``/``table`` blocks. Blank paragraphs become
    ``blank`` blocks so vertical spacing round-trips.

    ``document`` may be the full response or already unwrapped to the ``body``
    level; both are accepted.
    """
    return [block for block, _start, _end in doc_json_to_blocks_with_ranges(document)]


def doc_json_to_blocks_with_ranges(
    document: dict[str, Any],
) -> list[tuple[dict[str, Any], int, int]]:
    """Like ``doc_json_to_blocks``, but each block is paired with its
    ``(start_index, end_index)`` character range in the live document.

    This is the positional counterpart the differ/patch-planner (Phase B)
    needs to translate a block-level diff into ``deleteContentRange``/
    ``insertText`` requests against real document indices — ``doc_json_to_blocks``
    itself stays position-free so Phase A callers (and the differ's *target*
    side, which comes from ``parse_markdown`` and has no document positions at
    all) are unaffected.

    When adjacent Courier-New paragraphs are merged into one fenced ``code``
    block (see ``doc_json_to_blocks``), the merged block's range spans from the
    first paragraph's ``start_index`` to the last paragraph's ``end_index``.
    """
    body = document.get("body", document)
    content: list[dict[str, Any]] = body.get("content", []) or []
    lists: dict[str, Any] = document.get("lists", {}) or {}

    out: list[tuple[dict[str, Any], int, int]] = []
    ordered_counters: dict[tuple[str, int], int] = {}
    prev_list_key: tuple[str, int] | None = None

    for element in content:
        start = element.get("startIndex", 0)
        end = element.get("endIndex", start)

        if "table" in element:
            out.append((_table_element_to_block(element["table"]), start, end))
            prev_list_key = None
            continue

        paragraph = element.get("paragraph")
        if paragraph is None:
            # sectionBreak, tableOfContents, etc. — not represented in the IR.
            continue

        block, prev_list_key = _paragraph_to_block(
            paragraph, lists, ordered_counters, prev_list_key
        )
        if block is None:
            continue
        # The encoder emits a multi-line fenced code block as one Courier-New
        # paragraph per line (newlines split Docs paragraphs).  Merge adjacent
        # whole-code paragraphs back into a single fenced ``code`` block,
        # extending the merged range to the new last paragraph's end_index.
        if block["type"] == "code" and out and out[-1][0]["type"] == "code":
            prev_block, prev_start, _prev_end = out[-1]
            prev_block["text"] += "\n" + block["text"]
            out[-1] = (prev_block, prev_start, end)
        else:
            out.append((block, start, end))

    return out


def document_end_index(document: dict[str, Any]) -> int:
    """Return the safe insert index at the end of the document body.

    Mirrors the ``last_end - 1`` convention already used in
    ``markdown_file._markdown_file_to_doc`` (the position just before the
    body's final trailing-newline paragraph marker, where Docs always accepts
    an ``insertText``).
    """
    body = document.get("body", document)
    content: list[dict[str, Any]] = body.get("content", []) or []
    if not content:
        return 1
    last_end = content[-1].get("endIndex", 1)
    return max(1, last_end - 1)


def _paragraph_to_block(
    paragraph: dict[str, Any],
    lists: dict[str, Any],
    ordered_counters: dict[tuple[str, int], int],
    prev_list_key: tuple[str, int] | None,
) -> tuple[dict[str, Any] | None, tuple[str, int] | None]:
    """Convert one ``paragraph`` structural element into a block.

    Returns ``(block, new_prev_list_key)``. ``block`` is None only for elements
    that carry no representable content and no structural meaning.
    """
    runs = _elements_to_runs(paragraph.get("elements", []))
    plain = "".join(r["text"] for r in runs)
    style = paragraph.get("paragraphStyle", {}) or {}

    # ---- Horizontal rule: empty paragraph carrying a bottom border ----
    if not plain.strip() and "borderBottom" in style:
        return {"type": "rule"}, None

    # ---- Blank paragraph ----
    if not plain.strip() and not runs_have_content(runs):
        return {"type": "blank"}, None

    # ---- List item (bullet / ordered) ----
    bullet = paragraph.get("bullet")
    if bullet is not None:
        list_id = bullet.get("listId", "")
        nesting = bullet.get("nestingLevel", 0)
        ordered = _is_ordered_list(lists, list_id, nesting)
        key = (list_id, nesting)
        if ordered:
            if key != prev_list_key:
                ordered_counters[key] = 0
            ordered_counters[key] += 1
            index = ordered_counters[key]
            return (
                {"type": "ordered", "index": index, "depth": nesting, "runs": runs},
                key,
            )
        return {"type": "bullet", "depth": nesting, "runs": runs}, key

    # ---- Fenced code block: whole paragraph in the code font ----
    if runs and all(r.get("code") for r in runs):
        return {"type": "code", "text": plain}, None

    # ---- Heading ----
    named_style = style.get("namedStyleType", "NORMAL_TEXT")
    level = HEADING_LEVEL_BY_STYLE.get(named_style)
    if level is not None:
        return {"type": "heading", "level": level, "runs": runs}, None

    # ---- Ordinary paragraph ----
    return {"type": "paragraph", "runs": runs}, None


def runs_have_content(runs: list[dict[str, Any]]) -> bool:
    """True if any run carries non-empty text."""
    return any(r["text"] for r in runs)


def _elements_to_runs(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert a paragraph's ``elements`` into inline run dicts.

    Only ``textRun`` elements are represented. The trailing paragraph newline
    (Docs stores it as the last character of the last run) is stripped so block
    text matches what ``parse_markdown`` produces.
    """
    runs: list[dict[str, Any]] = []
    for el in elements:
        text_run = el.get("textRun")
        if text_run is None:
            # inlineObjectElement (image), pageBreak, columnBreak, etc. — lost.
            continue
        content = text_run.get("content", "")
        if not content:
            continue
        text_style = text_run.get("textStyle", {}) or {}
        runs.append(
            {
                "text": content,
                "bold": bool(text_style.get("bold", False)),
                "italic": bool(text_style.get("italic", False)),
                "code": _is_code_style(text_style),
                "link": _extract_link(text_style),
            }
        )

    # Strip a single trailing newline from the paragraph's last run.
    if runs and runs[-1]["text"].endswith("\n"):
        runs[-1]["text"] = runs[-1]["text"][:-1]
        if not runs[-1]["text"]:
            runs.pop()

    return runs


def _is_code_style(text_style: dict[str, Any]) -> bool:
    font = text_style.get("weightedFontFamily", {}) or {}
    return font.get("fontFamily") == _CODE_FONT


def _extract_link(text_style: dict[str, Any]) -> str | None:
    link = text_style.get("link")
    if isinstance(link, dict):
        url = link.get("url")
        if url:
            return str(url)
    return None


def _is_ordered_list(lists: dict[str, Any], list_id: str, nesting: int) -> bool:
    """Resolve whether a list is ordered by inspecting its glyph type."""
    list_props = (lists.get(list_id, {}) or {}).get("listProperties", {}) or {}
    nesting_levels = list_props.get("nestingLevels", []) or []
    if 0 <= nesting < len(nesting_levels):
        level_props = nesting_levels[nesting] or {}
        glyph_type = level_props.get("glyphType")
        if glyph_type is not None:
            return glyph_type in _ORDERED_GLYPH_TYPES
        # No glyphType but an explicit glyphSymbol -> unordered.
    return False


# ---- Table serialization -----------------------------------------------------


def _table_element_to_block(table: dict[str, Any]) -> dict[str, Any]:
    """Convert a ``table`` structural element into a table block.

    Row 0 is treated as the header row (matching the encoder, which always
    styles row 0 as the header). Merged cells are flattened by duplicating the
    spanning cell's text into each covered grid position.
    """
    grid = _table_to_text_grid(table)
    if not grid:
        return {"type": "table", "headers": [], "rows": []}
    headers = grid[0]
    rows = grid[1:]
    return {"type": "table", "headers": headers, "rows": rows}


def _table_to_text_grid(table: dict[str, Any]) -> list[list[str]]:
    """Flatten a Docs table into a rectangular grid of cell-text strings.

    Merged cells (``rowSpan``/``columnSpan`` > 1) are expanded so every covered
    grid position holds the merged cell's text — a documented lossy fallback
    (GFM has no merge concept), preferable to silently misaligning columns.
    """
    table_rows = table.get("tableRows", []) or []
    num_cols = int(table.get("columns", 0) or 0)
    if not num_cols:
        # Fall back to the widest row's cell count.
        num_cols = max((len(r.get("tableCells", []) or []) for r in table_rows), default=0)

    num_rows = len(table_rows)
    grid: list[list[str | None]] = [[None] * num_cols for _ in range(num_rows)]

    for row_i, row in enumerate(table_rows):
        col_i = 0
        for cell in row.get("tableCells", []) or []:
            # Advance past positions already filled by a cell spanning from above.
            while col_i < num_cols and grid[row_i][col_i] is not None:
                col_i += 1
            if col_i >= num_cols:
                break
            text = _cell_to_text(cell)
            cell_style = cell.get("tableCellStyle", {}) or {}
            row_span = int(cell_style.get("rowSpan", 1) or 1)
            col_span = int(cell_style.get("columnSpan", 1) or 1)
            for dr in range(row_span):
                for dc in range(col_span):
                    r, c = row_i + dr, col_i + dc
                    if r < num_rows and c < num_cols:
                        grid[r][c] = text
            col_i += col_span

    return [["" if cell is None else cell for cell in row] for row in grid]


def _cell_to_text(cell: dict[str, Any]) -> str:
    """Render a table cell's paragraphs to inline Markdown.

    GFM table cells cannot contain real newlines, so multiple cell paragraphs
    are joined with ``<br>`` (a documented loss).
    """
    parts: list[str] = []
    for element in cell.get("content", []) or []:
        paragraph = element.get("paragraph")
        if paragraph is None:
            continue
        runs = _elements_to_runs(paragraph.get("elements", []))
        rendered = _runs_to_markdown(runs)
        if rendered:
            parts.append(rendered)
    return "<br>".join(parts)


# =============================================================================
# block IR -> Markdown
# =============================================================================


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """Render a block list to GFM Markdown.

    Consecutive blocks are separated by newlines; block-level constructs
    (headings, paragraphs, code, tables) are followed by a blank line so they
    round-trip through ``parse_markdown`` as distinct blocks. ``blank`` blocks
    already model that spacing, so they are emitted as bare blank lines and no
    extra separator is added around them.
    """
    lines: list[str] = []
    for block in blocks:
        btype = block["type"]
        if btype == "heading":
            lines.append("#" * block["level"] + " " + _runs_to_markdown(block["runs"]))
        elif btype == "paragraph":
            lines.append(_runs_to_markdown(block["runs"]))
        elif btype == "code":
            lines.append("```")
            lines.extend(block["text"].split("\n"))
            lines.append("```")
        elif btype == "bullet":
            indent = "  " * int(block.get("depth", 0))
            lines.append(f"{indent}- {_runs_to_markdown(block['runs'])}")
        elif btype == "ordered":
            indent = "  " * int(block.get("depth", 0))
            index = int(block.get("index", 1))
            lines.append(f"{indent}{index}. {_runs_to_markdown(block['runs'])}")
        elif btype == "table":
            lines.extend(_table_block_to_markdown(block))
        elif btype == "rule":
            lines.append("---")
        elif btype == "blank":
            lines.append("")

    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


def _table_block_to_markdown(block: dict[str, Any]) -> list[str]:
    """Render a table block as GFM pipe-table lines (header + separator + rows)."""
    headers: list[str] = block.get("headers", []) or []
    rows: list[list[str]] = block.get("rows", []) or []
    num_cols = len(headers)
    if num_cols == 0:
        return []

    def _fmt_row(cells: list[str]) -> str:
        # Pad/truncate to the header column count so the table stays rectangular.
        padded = list(cells[:num_cols]) + [""] * (num_cols - len(cells))
        return "| " + " | ".join(_escape_cell(c) for c in padded) + " |"

    out = [_fmt_row(headers), "| " + " | ".join(["---"] * num_cols) + " |"]
    out.extend(_fmt_row(row) for row in rows)
    return out


def _escape_cell(text: str) -> str:
    """Escape pipe characters so cell content doesn't break the column layout."""
    return text.replace("|", "\\|")


def _runs_to_markdown(runs: list[dict[str, Any]]) -> str:
    """Render inline runs back to Markdown, inverting ``_parse_inline_runs``."""
    return "".join(_run_to_markdown(r) for r in runs)


def _run_to_markdown(run: dict[str, Any]) -> str:
    text = run.get("text", "")
    # A pure hard-break run round-trips as a GFM hard line break.
    if text == "\n":
        return "  \n"
    if run.get("link"):
        return f"[{_apply_emphasis(text, run)}]({run['link']})"
    return _apply_emphasis(text, run)


def _apply_emphasis(text: str, run: dict[str, Any]) -> str:
    if not text:
        return ""
    if run.get("code"):
        return f"`{text}`"
    bold = run.get("bold")
    italic = run.get("italic")
    if bold and italic:
        return f"***{text}***"
    if bold:
        return f"**{text}**"
    if italic:
        return f"*{text}*"
    return text


# =============================================================================
# Markdown -> block IR (entry point; reuses the shared parser)
# =============================================================================


def markdown_to_blocks(markdown: str) -> list[dict[str, Any]]:
    """Parse Markdown into the shared block IR.

    Thin, explicit alias over ``blocks.parse_markdown`` so sync-engine callers
    have a single import surface for both directions of the round trip.
    """
    return parse_markdown(markdown)
