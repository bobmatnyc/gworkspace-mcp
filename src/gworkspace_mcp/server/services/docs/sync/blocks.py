"""Shared block intermediate-representation (IR) for the Markdown <-> Doc engine.

This module is the single source of truth for the block IR that both the
Markdown encoder (``markdown_file._DocBuilder``) and the native Docs-JSON
serializer (``sync.serializer``) target. It was relocated verbatim from
``markdown_file.py`` — that module re-imports every public name below so its
existing tool (``markdown_file_to_doc``) and tests keep working unchanged.

Block types produced by the parser (and consumed by the encoder/serializer):

- heading:   ``{"type": "heading", "level": int, "runs": [run, ...]}``
- paragraph: ``{"type": "paragraph", "runs": [run, ...]}``
- code:      ``{"type": "code", "text": str}``
- table:     ``{"type": "table", "headers": [str, ...], "rows": [[str, ...], ...]}``
- bullet:    ``{"type": "bullet", "depth": int, "runs": [run, ...]}``
- ordered:   ``{"type": "ordered", "index": int, "depth": int, "runs": [run, ...]}``
- rule:      ``{"type": "rule"}``
- blank:     ``{"type": "blank"}``

Each inline ``run`` dict has: ``text`` (str), ``bold`` (bool), ``italic``
(bool), ``code`` (bool), ``link`` (str | None).
"""

from __future__ import annotations

import re
from typing import Any

# Heading level -> Docs named style.  Shared with the serializer, which inverts
# it via ``HEADING_LEVEL_BY_STYLE`` below.
_HEADING_STYLE: dict[int, str] = {
    1: "HEADING_1",
    2: "HEADING_2",
    3: "HEADING_3",
    4: "HEADING_4",
    5: "HEADING_5",
    6: "HEADING_6",
}

# Inverse of ``_HEADING_STYLE`` — Docs named style -> heading level.  Used by the
# serializer to decode ``paragraphStyle.namedStyleType`` back into a heading
# block.
HEADING_LEVEL_BY_STYLE: dict[str, int] = {v: k for k, v in _HEADING_STYLE.items()}


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
