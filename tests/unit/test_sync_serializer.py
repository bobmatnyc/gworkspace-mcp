"""Unit tests for the docs.sync serializer (Phase A).

Covers:
- Native Docs-JSON -> block IR (``doc_json_to_blocks``) for headings, inline
  styles, links, code blocks, ordered/unordered/nested lists, tables (with
  header rows), horizontal rules, and merged-cell flattening.
- block IR -> GFM Markdown (``blocks_to_markdown``) against hand-written golden
  strings per checked-in fixture.
- Round-trip / fidelity: fixture -> serializer -> Markdown -> parse_markdown ->
  serializer is a fixed point (the RFC's core round-trip claim), with no live
  API calls (fixtures only).
- The block-IR relocation is a re-export, not a fork.

All fixtures live under ``tests/fixtures/docs_json/*.json`` and mirror the shape
a ``documents.get`` response has for docs produced by this codebase's own
Markdown encoder.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gworkspace_mcp.server.services.docs.sync import blocks as blocks_mod
from gworkspace_mcp.server.services.docs.sync.serializer import (
    blocks_to_markdown,
    doc_json_to_blocks,
    markdown_to_blocks,
)

_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "docs_json"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


# Hand-written expected GFM for each golden fixture (RFC section 9).
_EXPECTED_MD: dict[str, str] = {
    "headings_and_inline": (
        "# Document Title\n"
        "\n"
        "Intro with **bold**, *italic*, `code`, and a [link](https://example.com).\n"
        "\n"
        "## Subsection\n"
        "\n"
        "Plain paragraph text.\n"
    ),
    "lists": (
        "- Top bullet\n"
        "  - Nested bullet\n"
        "- Second top bullet\n"
        "\n"
        "1. First step\n"
        "2. Second step\n"
        "  1. Nested step\n"
    ),
    "table": (
        "## People\n"
        "\n"
        "| Name | Role | Notes |\n"
        "| --- | --- | --- |\n"
        "| Ada | Engineer | first **programmer** |\n"
        "| Alan | Scientist | theory |\n"
    ),
    "code_and_rule": (
        "Before the code.\n"
        "\n"
        "```\n"
        "def greet(name):\n"
        '    return f"hi {name}"\n'
        "```\n"
        "\n"
        "---\n"
        "\n"
        "After the rule.\n"
    ),
}


# ---------------------------------------------------------------------------
# Docs-JSON -> Markdown golden-fixture fidelity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocJsonToMarkdown:
    @pytest.mark.parametrize("name", sorted(_EXPECTED_MD))
    def test_serializes_to_expected_gfm(self, name: str) -> None:
        doc = _load(name)
        md = blocks_to_markdown(doc_json_to_blocks(doc))
        assert md == _EXPECTED_MD[name]

    @pytest.mark.parametrize("name", sorted(_EXPECTED_MD))
    def test_round_trip_is_fixed_point(self, name: str) -> None:
        """Doc -> MD -> blocks -> MD reproduces the exact same Markdown."""
        doc = _load(name)
        md = blocks_to_markdown(doc_json_to_blocks(doc))
        reparsed = markdown_to_blocks(md)
        assert blocks_to_markdown(reparsed) == md

    @pytest.mark.parametrize("name", sorted(_EXPECTED_MD))
    def test_doc_blocks_match_markdown_blocks(self, name: str) -> None:
        """The serializer emits the SAME block IR that parse_markdown produces
        from the equivalent Markdown — the property that makes diffing possible."""
        doc = _load(name)
        doc_blocks = doc_json_to_blocks(doc)
        md_blocks = markdown_to_blocks(_EXPECTED_MD[name])
        assert doc_blocks == md_blocks


# ---------------------------------------------------------------------------
# Per-construct block-IR assertions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHeadingsAndInline:
    def test_heading_levels(self) -> None:
        blocks = doc_json_to_blocks(_load("headings_and_inline"))
        headings = [b for b in blocks if b["type"] == "heading"]
        assert [h["level"] for h in headings] == [1, 2]
        assert headings[0]["runs"][0]["text"] == "Document Title"

    def test_inline_styles_decoded(self) -> None:
        blocks = doc_json_to_blocks(_load("headings_and_inline"))
        para = next(
            b
            for b in blocks
            if b["type"] == "paragraph" and any("bold" == r["text"] for r in b["runs"])
        )
        by_text = {r["text"]: r for r in para["runs"]}
        assert by_text["bold"]["bold"] is True
        assert by_text["italic"]["italic"] is True
        assert by_text["code"]["code"] is True
        assert by_text["link"]["link"] == "https://example.com"

    def test_blank_paragraphs_become_blank_blocks(self) -> None:
        blocks = doc_json_to_blocks(_load("headings_and_inline"))
        assert any(b["type"] == "blank" for b in blocks)


@pytest.mark.unit
class TestLists:
    def test_unordered_and_nested(self) -> None:
        blocks = doc_json_to_blocks(_load("lists"))
        bullets = [b for b in blocks if b["type"] == "bullet"]
        assert [b["depth"] for b in bullets] == [0, 1, 0]

    def test_ordered_numbering_and_reset(self) -> None:
        blocks = doc_json_to_blocks(_load("lists"))
        ordered = [b for b in blocks if b["type"] == "ordered"]
        # Two top-level steps numbered 1,2 then a nested step restarting at 1.
        assert [(o["index"], o["depth"]) for o in ordered] == [(1, 0), (2, 0), (1, 1)]

    def test_glyph_symbol_is_unordered(self) -> None:
        blocks = doc_json_to_blocks(_load("lists"))
        # L1 uses glyphSymbol -> all bullet, never ordered.
        assert all(b["type"] != "ordered" for b in blocks[:3])


@pytest.mark.unit
class TestTables:
    def test_header_and_rows(self) -> None:
        blocks = doc_json_to_blocks(_load("table"))
        table = next(b for b in blocks if b["type"] == "table")
        assert table["headers"] == ["Name", "Role", "Notes"]
        assert table["rows"][0] == ["Ada", "Engineer", "first **programmer**"]
        assert table["rows"][1] == ["Alan", "Scientist", "theory"]

    def test_merged_cell_is_flattened(self) -> None:
        """A cell with columnSpan=2 duplicates its text across covered columns."""
        merged_doc = {
            "body": {
                "content": [
                    {
                        "table": {
                            "columns": 3,
                            "tableRows": [
                                {
                                    "tableCells": [
                                        _cell("A"),
                                        _cell("B"),
                                        _cell("C"),
                                    ]
                                },
                                {
                                    "tableCells": [
                                        _cell("wide", column_span=2),
                                        _cell("z"),
                                    ]
                                },
                            ],
                        }
                    }
                ]
            },
            "lists": {},
        }
        table = doc_json_to_blocks(merged_doc)[0]
        assert table["headers"] == ["A", "B", "C"]
        # The merged cell text is duplicated into both spanned positions.
        assert table["rows"][0] == ["wide", "wide", "z"]

    def test_multi_paragraph_cell_joined_with_br(self) -> None:
        doc = {
            "body": {
                "content": [
                    {
                        "table": {
                            "columns": 1,
                            "tableRows": [
                                {"tableCells": [_cell("Head")]},
                                {
                                    "tableCells": [
                                        {
                                            "content": [
                                                _para("line one"),
                                                _para("line two"),
                                            ]
                                        }
                                    ]
                                },
                            ],
                        }
                    }
                ]
            },
            "lists": {},
        }
        table = doc_json_to_blocks(doc)[0]
        assert table["rows"][0] == ["line one<br>line two"]


@pytest.mark.unit
class TestCodeAndRule:
    def test_multiline_code_block_merged(self) -> None:
        blocks = doc_json_to_blocks(_load("code_and_rule"))
        code = next(b for b in blocks if b["type"] == "code")
        assert code["text"] == 'def greet(name):\n    return f"hi {name}"'

    def test_horizontal_rule_from_border_bottom(self) -> None:
        blocks = doc_json_to_blocks(_load("code_and_rule"))
        assert any(b["type"] == "rule" for b in blocks)

    def test_whole_paragraph_courier_is_code_block(self) -> None:
        courier = {"weightedFontFamily": {"fontFamily": "Courier New"}}
        doc = {
            "body": {"content": [_para("x = 1", style=None, run_style=courier)]},
            "lists": {},
        }
        blocks = doc_json_to_blocks(doc)
        assert blocks[0]["type"] == "code"
        assert blocks[0]["text"] == "x = 1"

    def test_partial_courier_run_is_inline_code(self) -> None:
        courier = {"weightedFontFamily": {"fontFamily": "Courier New"}}
        doc = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "call ", "textStyle": {}}},
                                {"textRun": {"content": "func()", "textStyle": courier}},
                                {"textRun": {"content": " now\n", "textStyle": {}}},
                            ]
                        }
                    }
                ]
            },
            "lists": {},
        }
        blocks = doc_json_to_blocks(doc)
        assert blocks[0]["type"] == "paragraph"
        code_run = next(r for r in blocks[0]["runs"] if r["code"])
        assert code_run["text"] == "func()"


# ---------------------------------------------------------------------------
# blocks_to_markdown pipe-escaping + entry-point aliasing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSerializerDetails:
    def test_pipe_in_cell_is_escaped(self) -> None:
        block = {"type": "table", "headers": ["a"], "rows": [["x|y"]]}
        md = blocks_to_markdown([block])
        assert "x\\|y" in md

    def test_markdown_to_blocks_is_parse_markdown(self) -> None:
        md = "# Hi\n\nBody.\n"
        assert markdown_to_blocks(md) == blocks_mod.parse_markdown(md)

    def test_body_or_full_document_accepted(self) -> None:
        doc = _load("headings_and_inline")
        from_full = doc_json_to_blocks(doc)
        from_body = doc_json_to_blocks({"body": doc["body"], "lists": doc.get("lists", {})})
        assert from_full == from_body


# ---------------------------------------------------------------------------
# Relocation is a re-export, not a fork
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelocationIntegrity:
    def test_markdown_file_reexports_blocks_ir(self) -> None:
        from gworkspace_mcp.server.services.docs import markdown_file

        # Same function objects — proving no duplicated/forked logic.
        assert markdown_file.parse_markdown is blocks_mod.parse_markdown
        assert markdown_file._parse_inline_runs is blocks_mod._parse_inline_runs
        assert markdown_file._HEADING_STYLE is blocks_mod._HEADING_STYLE


# ---------------------------------------------------------------------------
# Small builders for inline fixtures
# ---------------------------------------------------------------------------


def _para(
    text: str,
    style: dict[str, Any] | None = None,
    run_style: dict[str, Any] | None = None,
) -> dict[str, Any]:
    para: dict[str, Any] = {
        "elements": [{"textRun": {"content": text + "\n", "textStyle": run_style or {}}}]
    }
    if style is not None:
        para["paragraphStyle"] = style
    return {"paragraph": para}


def _cell(text: str, column_span: int = 1, row_span: int = 1) -> dict[str, Any]:
    cell: dict[str, Any] = {"content": [_para(text)]}
    if column_span != 1 or row_span != 1:
        cell["tableCellStyle"] = {"columnSpan": column_span, "rowSpan": row_span}
    return cell
