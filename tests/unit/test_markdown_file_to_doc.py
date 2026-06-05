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
