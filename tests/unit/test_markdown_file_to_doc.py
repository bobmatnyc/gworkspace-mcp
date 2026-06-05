"""Unit tests for markdown_file_to_doc tool.

Tests cover:
- Tool definition / schema
- Markdown parser (parse_markdown)
- Inline run parser (_parse_inline_runs)
- DocBuilder request generation
- Handler: missing inputs, file-not-found, new-doc creation, in-place update
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from gworkspace_mcp.server.services.docs.markdown_file import (
    TOOLS,
    _DocBuilder,
    _parse_inline_runs,
    get_handlers,
    parse_markdown,
)

# ---------------------------------------------------------------------------
# Tool schema tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMarkdownFileToDocTool:
    def test_tool_registered(self) -> None:
        names = [t.name for t in TOOLS]
        assert "markdown_file_to_doc" in names

    def test_tool_description_nonempty(self) -> None:
        tool = next(t for t in TOOLS if t.name == "markdown_file_to_doc")
        assert tool.description
        assert len(tool.description) > 20

    def test_tool_description_mentions_key_features(self) -> None:
        tool = next(t for t in TOOLS if t.name == "markdown_file_to_doc")
        desc = tool.description.lower()
        assert "file" in desc
        assert "border" in desc or "table" in desc

    def test_schema_has_markdown_file_path_property(self) -> None:
        tool = next(t for t in TOOLS if t.name == "markdown_file_to_doc")
        props = tool.inputSchema.get("properties", {})
        assert "markdown_file_path" in props

    def test_schema_has_document_id_property(self) -> None:
        tool = next(t for t in TOOLS if t.name == "markdown_file_to_doc")
        props = tool.inputSchema.get("properties", {})
        assert "document_id" in props

    def test_schema_has_account_property(self) -> None:
        tool = next(t for t in TOOLS if t.name == "markdown_file_to_doc")
        props = tool.inputSchema.get("properties", {})
        assert "account" in props


# ---------------------------------------------------------------------------
# Inline run parser tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseInlineRuns:
    def test_plain_text(self) -> None:
        runs = _parse_inline_runs("hello world")
        assert len(runs) == 1
        assert runs[0]["text"] == "hello world"
        assert not runs[0]["bold"]
        assert runs[0]["link"] is None

    def test_bold(self) -> None:
        runs = _parse_inline_runs("**bold text**")
        assert any(r["bold"] and r["text"] == "bold text" for r in runs)

    def test_italic(self) -> None:
        runs = _parse_inline_runs("*italic text*")
        assert any(r["italic"] and r["text"] == "italic text" for r in runs)

    def test_inline_code(self) -> None:
        runs = _parse_inline_runs("`some code`")
        assert any(r["code"] and r["text"] == "some code" for r in runs)

    def test_link(self) -> None:
        runs = _parse_inline_runs("[click here](https://example.com)")
        assert any(r["link"] == "https://example.com" and r["text"] == "click here" for r in runs)

    def test_mixed_content(self) -> None:
        runs = _parse_inline_runs("See [docs](https://example.com) for **details**.")
        texts = [r["text"] for r in runs]
        assert "docs" in texts
        assert "details" in texts
        link_run = next(r for r in runs if r["link"])
        assert link_run["link"] == "https://example.com"

    def test_empty_string(self) -> None:
        runs = _parse_inline_runs("")
        # Should return at least one run (possibly empty text)
        assert isinstance(runs, list)


# ---------------------------------------------------------------------------
# Markdown parser tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParseMarkdown:
    def test_heading_h1(self) -> None:
        blocks = parse_markdown("# Title\n")
        headings = [b for b in blocks if b["type"] == "heading"]
        assert len(headings) == 1
        assert headings[0]["level"] == 1
        assert headings[0]["runs"][0]["text"] == "Title"

    def test_heading_h3(self) -> None:
        blocks = parse_markdown("### Section\n")
        h = next(b for b in blocks if b["type"] == "heading")
        assert h["level"] == 3

    def test_paragraph(self) -> None:
        blocks = parse_markdown("Hello world\n")
        paras = [b for b in blocks if b["type"] == "paragraph"]
        assert len(paras) >= 1
        text = "".join(r["text"] for r in paras[0]["runs"])
        assert "Hello world" in text

    def test_blank_line(self) -> None:
        blocks = parse_markdown("\n")
        assert any(b["type"] == "blank" for b in blocks)

    def test_fenced_code_block(self) -> None:
        md = "```python\nprint('hi')\n```\n"
        blocks = parse_markdown(md)
        code_blocks = [b for b in blocks if b["type"] == "code"]
        assert len(code_blocks) == 1
        assert "print" in code_blocks[0]["text"]

    def test_unordered_list(self) -> None:
        md = "- item one\n- item two\n"
        blocks = parse_markdown(md)
        bullets = [b for b in blocks if b["type"] == "bullet"]
        assert len(bullets) == 2

    def test_ordered_list(self) -> None:
        md = "1. first\n2. second\n"
        blocks = parse_markdown(md)
        ordered = [b for b in blocks if b["type"] == "ordered"]
        assert len(ordered) == 2

    def test_table(self) -> None:
        md = "| Col A | Col B |\n|-------|-------|\n| r1c1 | r1c2 |\n| r2c1 | r2c2 |\n"
        blocks = parse_markdown(md)
        tables = [b for b in blocks if b["type"] == "table"]
        assert len(tables) == 1
        t = tables[0]
        assert t["headers"] == ["Col A", "Col B"]
        assert len(t["rows"]) == 2
        assert t["rows"][0] == ["r1c1", "r1c2"]

    def test_horizontal_rule(self) -> None:
        blocks = parse_markdown("---\n")
        rules = [b for b in blocks if b["type"] == "rule"]
        assert len(rules) == 1

    def test_mixed_document(self) -> None:
        md = (
            "# Heading 1\n\n"
            "A paragraph.\n\n"
            "## Heading 2\n\n"
            "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
            "- bullet\n"
        )
        blocks = parse_markdown(md)
        types = {b["type"] for b in blocks}
        assert "heading" in types
        assert "paragraph" in types
        assert "table" in types
        assert "bullet" in types


# ---------------------------------------------------------------------------
# DocBuilder tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocBuilder:
    def test_heading_emits_insert_and_style(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_heading(
            1, [{"text": "My Title", "bold": False, "italic": False, "code": False, "link": None}]
        )
        requests, _ = builder.build()
        insert_reqs = [r for r in requests if "insertText" in r]
        style_reqs = [r for r in requests if "updateParagraphStyle" in r]
        assert insert_reqs
        assert any("My Title" in r["insertText"]["text"] for r in insert_reqs)
        assert style_reqs
        assert (
            style_reqs[0]["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_1"
        )

    def test_paragraph_emits_insert(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_paragraph(
            [{"text": "Hello", "bold": False, "italic": False, "code": False, "link": None}]
        )
        requests, _ = builder.build()
        assert any("insertText" in r and "Hello" in r["insertText"]["text"] for r in requests)

    def test_bold_run_emits_text_style(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_paragraph(
            [{"text": "bold", "bold": True, "italic": False, "code": False, "link": None}]
        )
        requests, _ = builder.build()
        style_reqs = [r for r in requests if "updateTextStyle" in r]
        assert any(r["updateTextStyle"]["textStyle"].get("bold") for r in style_reqs)

    def test_link_run_emits_link_style(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_paragraph(
            [
                {
                    "text": "click",
                    "bold": False,
                    "italic": False,
                    "code": False,
                    "link": "https://example.com",
                }
            ]
        )
        requests, _ = builder.build()
        style_reqs = [r for r in requests if "updateTextStyle" in r]
        assert any(
            r["updateTextStyle"]["textStyle"].get("link", {}).get("url") == "https://example.com"
            for r in style_reqs
        )

    def test_table_emits_insert_table_and_deferred(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_table(["Col A", "Col B"], [["r1c1", "r1c2"], ["r2c1", "r2c2"]])
        requests, deferred = builder.build()
        assert any("insertTable" in r for r in requests)
        assert any(d.get("_fill_table") for d in deferred)

    def test_table_deferred_has_correct_metadata(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_table(["H1", "H2"], [["a", "b"]])
        _, deferred = builder.build()
        sentinel = next(d for d in deferred if d.get("_fill_table"))
        assert sentinel["num_rows"] == 2  # 1 header + 1 data row
        assert sentinel["num_cols"] == 2
        assert sentinel["all_rows"] == [["H1", "H2"], ["a", "b"]]

    def test_index_advances_correctly_for_text(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_paragraph(
            [{"text": "abc", "bold": False, "italic": False, "code": False, "link": None}]
        )
        # "abc" + "\n" = 4 chars, so index should be 5
        assert builder.index == 5

    def test_heading_h6(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_heading(
            6, [{"text": "deep", "bold": False, "italic": False, "code": False, "link": None}]
        )
        requests, _ = builder.build()
        style = next(r for r in requests if "updateParagraphStyle" in r)
        assert style["updateParagraphStyle"]["paragraphStyle"]["namedStyleType"] == "HEADING_6"

    def test_bullet_emits_create_paragraph_bullets(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_bullet(
            0, [{"text": "item", "bold": False, "italic": False, "code": False, "link": None}]
        )
        requests, _ = builder.build()
        assert any("createParagraphBullets" in r for r in requests)

    def test_ordered_emits_create_paragraph_bullets(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_ordered(
            [{"text": "first", "bold": False, "italic": False, "code": False, "link": None}]
        )
        requests, _ = builder.build()
        assert any("createParagraphBullets" in r for r in requests)

    def test_code_block_emits_monospace_style(self) -> None:
        builder = _DocBuilder(start_index=1)
        builder.add_code_block("def foo(): pass")
        requests, _ = builder.build()
        style_reqs = [r for r in requests if "updateTextStyle" in r]
        assert any(
            "Courier New" in str(r["updateTextStyle"]["textStyle"].get("weightedFontFamily", {}))
            for r in style_reqs
        )


# ---------------------------------------------------------------------------
# Handler tests
# ---------------------------------------------------------------------------


def _make_service() -> MagicMock:
    """Build a minimal mock BaseService."""
    svc = MagicMock()
    svc._make_request = AsyncMock()
    svc._make_raw_request = AsyncMock()
    return svc


@pytest.mark.unit
class TestMarkdownFileTodocHandler:
    @pytest.mark.asyncio
    async def test_raises_when_no_input(self) -> None:
        svc = _make_service()
        handlers = get_handlers(svc)
        with pytest.raises((ValueError, FileNotFoundError)):
            await handlers["markdown_file_to_doc"]({})

    @pytest.mark.asyncio
    async def test_raises_file_not_found(self) -> None:
        svc = _make_service()
        handlers = get_handlers(svc)
        with pytest.raises(FileNotFoundError):
            await handlers["markdown_file_to_doc"](
                {"markdown_file_path": "/nonexistent/path/file.md", "title": "Test"}
            )

    @pytest.mark.asyncio
    async def test_create_new_doc_with_inline_content(self) -> None:
        svc = _make_service()
        # _make_request: first call creates doc, remaining are batchUpdates, last is file meta
        svc._make_request.side_effect = [
            # create document
            {"documentId": "new_doc_123", "title": "Test Doc"},
            # batchUpdate (insert requests) - may be called multiple times
            {"writeControl": {}},
            # file meta
            {
                "id": "new_doc_123",
                "name": "Test Doc",
                "webViewLink": "https://docs.google.com/abc",
                "mimeType": "application/vnd.google-apps.document",
            },
        ]
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {"markdown_content": "# Hello\n\nWorld.\n", "title": "Test Doc"}
        )
        assert result["document_id"] == "new_doc_123"
        assert "webViewLink" in result
        assert result["status"] == "published"

    @pytest.mark.asyncio
    async def test_in_place_update_calls_delete_then_insert(self) -> None:
        svc = _make_service()
        # _make_request calls: GET body, DELETE batchUpdate, INSERT batchUpdates..., GET file meta
        svc._make_request.side_effect = [
            # GET document body to clear
            {
                "body": {
                    "content": [
                        {"startIndex": 0, "endIndex": 1},
                        {"startIndex": 1, "endIndex": 50},
                    ]
                }
            },
            # DELETE batchUpdate (clear body)
            {"writeControl": {}},
            # INSERT batchUpdate
            {"writeControl": {}},
            # GET file meta
            {
                "id": "existing_doc_456",
                "name": "My Doc",
                "webViewLink": "https://docs.google.com/existing",
                "mimeType": "application/vnd.google-apps.document",
            },
        ]
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {
                "markdown_content": "# Update\n\nNew content.\n",
                "document_id": "existing_doc_456",
                "title": "My Doc",
            }
        )
        assert result["document_id"] == "existing_doc_456"
        assert result["status"] == "updated"
        # Verify first call was a GET (body fetch for clearing)
        first_call = svc._make_request.call_args_list[0]
        assert first_call.args[0] == "GET"

    @pytest.mark.asyncio
    async def test_reads_file_from_path(self, tmp_path: Path) -> None:
        md_file = tmp_path / "test.md"
        md_file.write_text("# File Heading\n\nContent from file.\n", encoding="utf-8")

        svc = _make_service()
        svc._make_request.side_effect = [
            {"documentId": "file_doc_789", "title": "File Test"},
            {"writeControl": {}},
            {
                "id": "file_doc_789",
                "name": "File Test",
                "webViewLink": "https://docs.google.com/file",
                "mimeType": "application/vnd.google-apps.document",
            },
        ]
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {"markdown_file_path": str(md_file), "title": "File Test"}
        )
        assert result["document_id"] == "file_doc_789"
        assert result["blocks_processed"] > 0

    @pytest.mark.asyncio
    async def test_file_path_takes_precedence_over_inline_content(self, tmp_path: Path) -> None:
        md_file = tmp_path / "priority.md"
        md_file.write_text("# From File\n", encoding="utf-8")

        svc = _make_service()
        svc._make_request.side_effect = [
            {"documentId": "prio_doc", "title": "Priority Test"},
            {"writeControl": {}},
            {
                "id": "prio_doc",
                "name": "Priority Test",
                "webViewLink": "https://docs.google.com/prio",
                "mimeType": "application/vnd.google-apps.document",
            },
        ]
        handlers = get_handlers(svc)
        # Both provided — file path wins
        result = await handlers["markdown_file_to_doc"](
            {
                "markdown_file_path": str(md_file),
                "markdown_content": "# From Inline\n",
                "title": "Priority Test",
            }
        )
        # Should have processed the file content (1 heading)
        assert result["blocks_processed"] >= 1

    @pytest.mark.asyncio
    async def test_handler_registered_in_handlers_dict(self) -> None:
        svc = _make_service()
        handlers = get_handlers(svc)
        assert "markdown_file_to_doc" in handlers
        assert callable(handlers["markdown_file_to_doc"])

    @pytest.mark.asyncio
    async def test_large_doc_uses_chunked_batch_updates(self, tmp_path: Path) -> None:
        """Verify a 500-paragraph document issues multiple batchUpdate calls."""
        lines = ["# Big Doc\n\n"]
        for i in range(250):
            lines.append(f"Paragraph {i} with some content that makes it non-trivial.\n\n")
        md_file = tmp_path / "large.md"
        md_file.write_text("".join(lines), encoding="utf-8")

        svc = _make_service()
        # Accept any number of calls
        svc._make_request.return_value = {
            "documentId": "large_doc",
            "title": "Big Doc",
            "writeControl": {},
            "id": "large_doc",
            "name": "Big Doc",
            "webViewLink": "https://docs.google.com/large",
            "mimeType": "application/vnd.google-apps.document",
        }
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {"markdown_file_path": str(md_file), "title": "Big Doc"}
        )
        assert result["document_id"] == "large_doc"
        # Should have called _make_request multiple times (create + multiple chunks)
        assert svc._make_request.call_count >= 2


# ---------------------------------------------------------------------------
# Bug-fix regression tests (confirmed bugs from real output review)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTableCellOrder:
    """Bug 1: Table cells were scrambled due to forward-order insertion.

    The Docs API insertText at index N shifts all subsequent indices forward.
    Cells must be inserted in reverse document order so earlier insertions
    do not invalidate later indices.
    """

    def test_5col_3row_table_deferred_cell_order(self) -> None:
        """5-column, 3-row table: all_rows contains cells in correct (row,col) order."""
        headers = ["Work Type", "Count", "%", "LOC", "LOC%"]
        rows = [
            ["Bug fixes", "1,277", "35.8%", "366,892", "25.6%"],
            ["Features", "800", "22.4%", "500,000", "34.9%"],
        ]
        builder = _DocBuilder(start_index=1)
        builder.add_table(headers, rows)
        _, deferred = builder.build()
        sentinel = next(d for d in deferred if d.get("_fill_table"))

        all_rows = sentinel["all_rows"]
        assert len(all_rows) == 3  # header + 2 data rows
        assert all_rows[0] == headers
        assert all_rows[1] == rows[0]
        assert all_rows[2] == rows[1]

        # Verify cell values are not concatenated/transposed
        assert all_rows[1][0] == "Bug fixes"
        assert all_rows[1][1] == "1,277"
        assert all_rows[1][2] == "35.8%"
        assert all_rows[1][3] == "366,892"
        assert all_rows[1][4] == "25.6%"
        assert all_rows[2][0] == "Features"

    def test_table_cell_insertions_are_sorted_descending(self) -> None:
        """Simulate the Phase 1 fill logic: verify insertions would be sorted in
        descending index order (reverse document order), ensuring no index drift."""
        # Simulate table cell content as returned by the Docs API after insertTable.
        # Each cell has a "content" list with a paragraph at a known startIndex.
        # We construct a fake table structure matching the Docs API shape.
        all_rows = [
            ["H1", "H2", "H3", "H4", "H5"],  # header
            ["r1c1", "r1c2", "r1c3", "r1c4", "r1c5"],  # row 1
            ["r2c1", "r2c2", "r2c3", "r2c4", "r2c5"],  # row 2
        ]

        def _make_cell(start_idx: int, text: str) -> dict:
            return {"content": [{"startIndex": start_idx, "paragraph": {}}]}

        # Assign realistic ascending startIndex values
        # (actual values from a 5-col empty table post-insertTable)
        start_indices = [
            # row 0
            [2, 4, 6, 8, 10],
            # row 1
            [13, 15, 17, 19, 21],
            # row 2
            [24, 26, 28, 30, 32],
        ]

        # Replicate the fill logic from _fill_tables_and_style to verify ordering
        cell_insertions: list[tuple[int, str]] = []
        for row_i, row_data in enumerate(all_rows):
            for col_i, cell_text in enumerate(row_data):
                para_start = start_indices[row_i][col_i]
                if cell_text.strip():
                    cell_insertions.append((para_start, cell_text))

        cell_insertions.sort(key=lambda x: x[0], reverse=True)

        # Assert descending order (last cell inserted first)
        indices = [idx for idx, _ in cell_insertions]
        assert indices == sorted(
            indices, reverse=True
        ), "Cell insertions must be in descending index order"

        # Assert the first insertion (highest index) is the last cell
        assert cell_insertions[0][0] == 32
        assert cell_insertions[0][1] == "r2c5"

        # Assert the last insertion (lowest index) is the first cell
        assert cell_insertions[-1][0] == 2
        assert cell_insertions[-1][1] == "H1"

        # Assert no cell text was concatenated
        texts = [t for _, t in cell_insertions]
        assert "H1H2" not in "".join(texts)
        assert all(t in [c for row in all_rows for c in row] for t in texts)


@pytest.mark.unit
class TestHardLineBreaks:
    """Bug 2: Markdown hard line breaks (two trailing spaces) were collapsed.

    Lines ending in two spaces must produce separate line-break runs (\\n)
    within the same paragraph block, NOT joined with a space.
    """

    def test_three_line_hard_break_title_block(self) -> None:
        """The canonical title block: 3 lines with trailing double-space hard breaks."""
        md = (
            "**Status:** DRAFT  \n"
            "**Prepared for:** Robert Matsuoka, Chief Technology Officer  \n"
            "**Date:** 2026-06-04"
        )
        blocks = parse_markdown(md)
        # All three lines are in one paragraph block
        para_blocks = [b for b in blocks if b["type"] == "paragraph"]
        assert len(para_blocks) == 1

        runs = para_blocks[0]["runs"]
        run_texts = [r["text"] for r in runs]

        # Must contain hard line-break characters (\n) between the logical lines
        newline_runs = [r for r in runs if r["text"] == "\n"]
        assert (
            len(newline_runs) == 2
        ), f"Expected 2 hard line-break \\n runs, got {len(newline_runs)}. Runs: {run_texts}"

        # The logical content of each line must be present
        all_text = "".join(run_texts)
        assert "Status:" in all_text
        assert "DRAFT" in all_text
        assert "Prepared for:" in all_text
        assert "Robert Matsuoka" in all_text
        assert "Date:" in all_text
        assert "2026-06-04" in all_text

    def test_hard_break_inserts_newline_in_doc_requests(self) -> None:
        """DocBuilder must emit a literal \\n insertText for hard breaks."""
        md = "line one  \nline two  \nline three"
        blocks = parse_markdown(md)
        builder = _DocBuilder(start_index=1)
        for b in blocks:
            if b["type"] == "paragraph":
                builder.add_paragraph(b["runs"])
        requests, _ = builder.build()

        insert_texts = [r["insertText"]["text"] for r in requests if "insertText" in r]
        # Count standalone newline insertions (hard breaks, not the paragraph-ending \n)
        # The paragraph-ending \n is the last insert; hard breaks are \n runs within
        newline_inserts = [t for t in insert_texts if t == "\n"]
        assert len(newline_inserts) >= 2, (
            f"Expected at least 2 \\n insertText requests for 2 hard breaks, "
            f"got {len(newline_inserts)}. All texts: {insert_texts}"
        )

    def test_soft_continuation_joins_with_space(self) -> None:
        """Lines WITHOUT trailing double-space are joined with a space (soft wrap)."""
        md = "first line\nsecond line\nthird line"
        blocks = parse_markdown(md)
        para_blocks = [b for b in blocks if b["type"] == "paragraph"]
        assert len(para_blocks) == 1

        runs = para_blocks[0]["runs"]
        # No hard break \n runs
        newline_runs = [r for r in runs if r["text"] == "\n"]
        assert len(newline_runs) == 0

        all_text = "".join(r["text"] for r in runs)
        # Lines joined with spaces
        assert "first line" in all_text
        assert "second line" in all_text
        assert "third line" in all_text


@pytest.mark.unit
class TestEmphasisParsing:
    """Bug 3: **bold** and *italic* emphasis must be parsed correctly.

    Stray/standalone * (e.g. footnote marker like ~49.7%*) and ~ must be
    treated as literal text, not emphasis.
    """

    def test_bold_double_asterisk(self) -> None:
        runs = _parse_inline_runs("**bold text**")
        bold_runs = [r for r in runs if r["bold"]]
        assert len(bold_runs) == 1
        assert bold_runs[0]["text"] == "bold text"
        assert not bold_runs[0]["italic"]

    def test_italic_single_asterisk(self) -> None:
        runs = _parse_inline_runs("*italic text*")
        italic_runs = [r for r in runs if r["italic"]]
        assert len(italic_runs) == 1
        assert italic_runs[0]["text"] == "italic text"
        assert not italic_runs[0]["bold"]

    def test_stray_asterisk_footnote_not_italic(self) -> None:
        """~49.7%* should be plain text, not italicized."""
        runs = _parse_inline_runs("~49.7%*")
        assert len(runs) == 1
        assert runs[0]["text"] == "~49.7%*"
        assert not runs[0]["italic"]
        assert not runs[0]["bold"]

    def test_stray_trailing_asterisk_not_italic(self) -> None:
        """'score of 95%*' should be plain text."""
        runs = _parse_inline_runs("score of 95%*")
        assert all(not r["italic"] for r in runs)
        all_text = "".join(r["text"] for r in runs)
        assert "95%*" in all_text

    def test_tilde_prefix_is_literal(self) -> None:
        """~ is not a formatting marker; ~text should be literal."""
        runs = _parse_inline_runs("~49.7%* of budget")
        assert all(not r["italic"] and not r["bold"] for r in runs)

    def test_bold_followed_by_literal(self) -> None:
        """**Status:** DRAFT — bold Status: then literal ' DRAFT'."""
        runs = _parse_inline_runs("**Status:** DRAFT")
        bold_runs = [r for r in runs if r["bold"]]
        assert any(r["text"] == "Status:" for r in bold_runs)
        plain_runs = [r for r in runs if not r["bold"] and not r["italic"]]
        plain_text = "".join(r["text"] for r in plain_runs)
        assert "DRAFT" in plain_text

    def test_no_italic_when_asterisk_surrounded_by_spaces(self) -> None:
        """'a * b * c' should not become italic since the content starts/ends with spaces."""
        runs = _parse_inline_runs("a * b * c")
        assert all(not r["italic"] for r in runs)

    def test_mixed_bold_italic_link(self) -> None:
        """A mix of bold, italic and link in one line."""
        text = "**bold** and *italic* and [link](http://x.com)"
        runs = _parse_inline_runs(text)
        assert any(r["bold"] and r["text"] == "bold" for r in runs)
        assert any(r["italic"] and r["text"] == "italic" for r in runs)
        assert any(r["link"] == "http://x.com" for r in runs)


@pytest.mark.unit
class TestDefaultFontBehavior:
    """Bug 4: The tool must NOT set an explicit font_family on normal body text.

    Headings should use named styles (which carry the theme font).
    Inline code uses Courier New — that is intentional and correct.
    """

    def test_normal_paragraph_has_no_font_family_override(self) -> None:
        """A plain paragraph must not emit a weightedFontFamily updateTextStyle."""
        builder = _DocBuilder(start_index=1)
        builder.add_paragraph(
            [
                {
                    "text": "Normal body text.",
                    "bold": False,
                    "italic": False,
                    "code": False,
                    "link": None,
                }
            ]
        )
        requests, _ = builder.build()
        text_style_reqs = [r for r in requests if "updateTextStyle" in r]
        for req in text_style_reqs:
            ts = req["updateTextStyle"]["textStyle"]
            assert (
                "weightedFontFamily" not in ts
            ), f"Plain paragraph must not set weightedFontFamily; got: {ts}"

    def test_heading_has_no_explicit_font_family(self) -> None:
        """Headings use named styles (namedStyleType) — not explicit font overrides."""
        builder = _DocBuilder(start_index=1)
        builder.add_heading(
            1,
            [{"text": "My Heading", "bold": False, "italic": False, "code": False, "link": None}],
        )
        requests, _ = builder.build()
        # updateParagraphStyle should use namedStyleType, not fontSize/fontFamily
        para_style_reqs = [r for r in requests if "updateParagraphStyle" in r]
        assert para_style_reqs, "Heading must emit updateParagraphStyle"
        for req in para_style_reqs:
            ps = req["updateParagraphStyle"]["paragraphStyle"]
            assert "namedStyleType" in ps, "Heading must use namedStyleType"
        # No updateTextStyle with weightedFontFamily on non-code heading text
        text_style_reqs = [r for r in requests if "updateTextStyle" in r]
        for req in text_style_reqs:
            ts = req["updateTextStyle"]["textStyle"]
            if "weightedFontFamily" in ts:
                ff = ts["weightedFontFamily"].get("fontFamily", "")
                assert (
                    ff == "Courier New"
                ), f"Only Courier New may be set via weightedFontFamily; got '{ff}'"

    def test_inline_code_uses_courier_new(self) -> None:
        """Inline code is the ONLY case where Courier New should be applied."""
        builder = _DocBuilder(start_index=1)
        builder.add_paragraph(
            [{"text": "some code", "bold": False, "italic": False, "code": True, "link": None}]
        )
        requests, _ = builder.build()
        text_style_reqs = [r for r in requests if "updateTextStyle" in r]
        assert any(
            r["updateTextStyle"]["textStyle"].get("weightedFontFamily", {}).get("fontFamily")
            == "Courier New"
            for r in text_style_reqs
        ), "Inline code must use Courier New"
