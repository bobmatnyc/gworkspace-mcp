"""Unit tests for the docs.sync Doc -> Markdown write-back (Phase C).

Covers:
- ``read_suggestions`` -> ``suggestionsViewMode`` mapping, including the deferred
  ``annotate`` stretch goal and the unknown-value guard (RFC section 5.3).
- ``doc_to_markdown`` against the golden Docs-JSON fixtures: faithful GFM
  including tables with header rows, and a Doc -> MD -> parse round-trip that is
  a fixed point.
- The fetch honors the resolved suggestions view mode and full field mask (no
  live API -- ``AsyncMock``-stubbed ``svc._make_request``).
- A fixture carrying a pending suggestion serializes per the ``accepted``
  policy (suggested-insertion text present; ``suggested*`` annotations ignored).
- File write-back: path returned + on-disk content matches, write can be
  suppressed, and out-of-tree paths are refused.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from gworkspace_mcp.server.services.docs.sync.serializer import (
    blocks_to_markdown,
    doc_json_to_blocks,
    markdown_to_blocks,
)
from gworkspace_mcp.server.services.docs.sync.writeback import (
    doc_json_to_markdown,
    doc_to_markdown,
    resolve_suggestions_view_mode,
)

_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "docs_json"
_GOLDEN_FIXTURES = ["headings_and_inline", "lists", "table", "code_and_rule"]


def _load(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _service_returning(document: dict[str, Any]) -> MagicMock:
    svc = MagicMock()
    svc._make_request = AsyncMock(return_value=document)
    return svc


# ---------------------------------------------------------------------------
# read_suggestions -> suggestionsViewMode mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSuggestionsViewMode:
    def test_accepted_maps_to_preview_accepted(self) -> None:
        assert resolve_suggestions_view_mode("accepted") == "PREVIEW_SUGGESTIONS_ACCEPTED"

    def test_rejected_maps_to_preview_without(self) -> None:
        assert resolve_suggestions_view_mode("rejected") == "PREVIEW_WITHOUT_SUGGESTIONS"

    def test_annotate_is_deferred(self) -> None:
        # RFC section 5.3: inline annotation of pending suggestions is a stretch
        # goal explicitly outside the Doc->MD phase; refuse rather than emit the
        # raw SUGGESTIONS_INLINE view (which would leak deletion text).
        with pytest.raises(NotImplementedError):
            resolve_suggestions_view_mode("annotate")

    def test_unknown_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            resolve_suggestions_view_mode("bogus")


# ---------------------------------------------------------------------------
# Golden-fixture Doc -> MD fidelity + round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDocToMarkdownFixtures:
    @pytest.mark.parametrize("name", _GOLDEN_FIXTURES)
    @pytest.mark.asyncio
    async def test_writeback_matches_serializer_pipeline(self, name: str) -> None:
        doc = _load(name)
        svc = _service_returning(doc)
        result = await doc_to_markdown(svc, "doc1")
        expected = blocks_to_markdown(doc_json_to_blocks(doc))
        assert result["markdown_content"] == expected
        assert result["direction_applied"] == "doc_to_md"

    @pytest.mark.parametrize("name", _GOLDEN_FIXTURES)
    @pytest.mark.asyncio
    async def test_round_trip_is_fixed_point(self, name: str) -> None:
        """Doc -> MD -> parse -> MD reproduces the same Markdown (RFC section 9)."""
        doc = _load(name)
        svc = _service_returning(doc)
        result = await doc_to_markdown(svc, "doc1")
        md = result["markdown_content"]
        assert blocks_to_markdown(markdown_to_blocks(md)) == md

    @pytest.mark.asyncio
    async def test_table_writeback_has_header_separator_row(self) -> None:
        doc = _load("table")
        svc = _service_returning(doc)
        md = (await doc_to_markdown(svc, "doc1"))["markdown_content"]
        assert "| Name | Role | Notes |" in md
        assert "| --- | --- | --- |" in md
        assert "| Ada | Engineer | first **programmer** |" in md

    def test_doc_json_to_markdown_is_pure_wrapper(self) -> None:
        doc = _load("headings_and_inline")
        assert doc_json_to_markdown(doc) == blocks_to_markdown(doc_json_to_blocks(doc))


# ---------------------------------------------------------------------------
# Fetch behavior: suggestions view mode + field mask
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchBehavior:
    @pytest.mark.asyncio
    async def test_accepted_requests_accepted_view_mode(self) -> None:
        doc = _load("suggestions_accepted")
        svc = _service_returning(doc)
        result = await doc_to_markdown(svc, "doc-suggest-1", read_suggestions="accepted")

        _method, url = svc._make_request.call_args.args[:2]
        params = svc._make_request.call_args.kwargs["params"]
        assert url.endswith("/documents/doc-suggest-1")
        assert params["suggestionsViewMode"] == "PREVIEW_SUGGESTIONS_ACCEPTED"
        assert "body" in params["fields"] and "lists" in params["fields"]
        assert result["suggestions_view_mode"] == "PREVIEW_SUGGESTIONS_ACCEPTED"
        assert result["revision_id"] == "rev-suggest-1"
        assert result["status"] == "read"  # no file path supplied

    @pytest.mark.asyncio
    async def test_rejected_requests_without_suggestions_view_mode(self) -> None:
        doc = _load("suggestions_accepted")
        svc = _service_returning(doc)
        await doc_to_markdown(svc, "doc-suggest-1", read_suggestions="rejected")
        params = svc._make_request.call_args.kwargs["params"]
        assert params["suggestionsViewMode"] == "PREVIEW_WITHOUT_SUGGESTIONS"

    @pytest.mark.asyncio
    async def test_pending_suggestion_serialized_as_accepted(self) -> None:
        """The suggested-insertion run's text is present in the accepted view,
        and the residual ``suggestedInsertionIds`` annotation is ignored."""
        doc = _load("suggestions_accepted")
        svc = _service_returning(doc)
        md = (await doc_to_markdown(svc, "doc-suggest-1"))["markdown_content"]
        assert md == "The quick brown fox.\n"


# ---------------------------------------------------------------------------
# File write-back
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFileWriteBack:
    @pytest.mark.asyncio
    async def test_writes_file_and_returns_path(self, tmp_path: Path) -> None:
        doc = _load("headings_and_inline")
        svc = _service_returning(doc)
        out = tmp_path / "out.md"
        result = await doc_to_markdown(svc, "doc1", markdown_file_path=str(out))

        assert result["status"] == "written"
        assert result["markdown_file_path"] == str(out.resolve())
        assert out.read_text(encoding="utf-8") == result["markdown_content"]

    @pytest.mark.asyncio
    async def test_write_can_be_suppressed(self, tmp_path: Path) -> None:
        doc = _load("headings_and_inline")
        svc = _service_returning(doc)
        out = tmp_path / "skip.md"
        result = await doc_to_markdown(
            svc, "doc1", markdown_file_path=str(out), write_markdown_file=False
        )
        assert result["status"] == "read"
        assert result["markdown_file_path"] is None
        assert not out.exists()

    @pytest.mark.asyncio
    async def test_creates_missing_parent_dirs(self, tmp_path: Path) -> None:
        doc = _load("headings_and_inline")
        svc = _service_returning(doc)
        out = tmp_path / "nested" / "deep" / "out.md"
        await doc_to_markdown(svc, "doc1", markdown_file_path=str(out))
        assert out.is_file()

    @pytest.mark.asyncio
    async def test_out_of_tree_path_refused(self) -> None:
        doc = _load("headings_and_inline")
        svc = _service_returning(doc)
        with pytest.raises(ValueError):
            await doc_to_markdown(svc, "doc1", markdown_file_path="/etc/passwd.md")
