"""Integration-style tests for the default (Phase B) in-place diff/patch path
of ``markdown_file_to_doc``'s ``document_id`` branch.

Unlike ``test_markdown_file_to_doc.py``'s ``force_rebuild=True`` test (which
exercises the explicit destructive "hard reset" escape hatch), these tests
drive the DEFAULT behavior end-to-end through the real handler with a mocked
``svc._make_request``: fetch the live document, diff against target Markdown,
apply a minimal patch. No live Google API calls — all document state is
hand-built Docs-JSON fixtures.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from gworkspace_mcp.server.services.docs.markdown_file import get_handlers
from gworkspace_mcp.server.services.docs.sync.blocks import parse_markdown


def _build_doc_json(markdown: str, revision_id: str = "rev1") -> dict[str, Any]:
    """Build minimal Docs-JSON for a plain heading/paragraph/blank Markdown
    string — enough structure for the serializer to reproduce it exactly."""
    blocks = parse_markdown(markdown)
    content: list[dict[str, Any]] = []
    idx = 1
    for block in blocks:
        btype = block["type"]
        style: dict[str, Any] | None = None
        if btype == "blank":
            text = "\n"
        elif btype == "heading":
            text = "".join(r["text"] for r in block["runs"]) + "\n"
            style = {"namedStyleType": f"HEADING_{block['level']}"}
        else:  # paragraph
            text = "".join(r["text"] for r in block["runs"]) + "\n"
        start = idx
        end = idx + len(text)
        paragraph: dict[str, Any] = {
            "elements": [{"startIndex": start, "endIndex": end, "textRun": {"content": text}}]
        }
        if style:
            paragraph["paragraphStyle"] = style
        content.append({"startIndex": start, "endIndex": end, "paragraph": paragraph})
        idx = end
    return {
        "documentId": "doc1",
        "revisionId": revision_id,
        "body": {"content": content},
        "lists": {},
    }


def _make_service() -> MagicMock:
    svc = MagicMock()
    svc._make_request = AsyncMock()
    return svc


@pytest.mark.unit
class TestDiffPatchDefaultPath:
    @pytest.mark.asyncio
    async def test_idempotent_when_doc_already_matches_markdown(self) -> None:
        """Re-running unchanged markdown against an already-synced doc must
        issue ZERO batchUpdate requests — the key Phase B correctness property."""
        md = "# Title\n\nHello world.\n"
        doc_json = _build_doc_json(md)

        svc = _make_service()

        async def dispatch(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
            if method == "GET" and "/files/" in url:
                return {
                    "id": "doc1",
                    "name": "Doc",
                    "webViewLink": "https://docs.google.com/doc1",
                    "mimeType": "application/vnd.google-apps.document",
                }
            if method == "GET":
                return doc_json
            raise AssertionError(f"Unexpected call: {method} {url}")

        svc._make_request.side_effect = dispatch
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {"markdown_content": md, "document_id": "doc1", "title": "Doc"}
        )

        assert result["status"] == "no_changes"
        assert result["requests_issued"] == 0
        # No POST (batchUpdate) call should have been made at all.
        post_calls = [c for c in svc._make_request.call_args_list if c.args and c.args[0] == "POST"]
        assert post_calls == []

    @pytest.mark.asyncio
    async def test_single_word_change_issues_minimal_patch(self) -> None:
        """A single changed word must NOT trigger a full-body delete — the
        default path is a minimal, scoped patch, not a clear-and-rebuild."""
        old_md = "# Title\n\nHello world.\n"
        new_md = "# Title\n\nHello there world.\n"
        doc_json = _build_doc_json(old_md)

        svc = _make_service()
        batch_calls: list[list[dict[str, Any]]] = []

        async def dispatch(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
            if method == "GET" and "/files/" in url:
                return {
                    "id": "doc1",
                    "name": "Doc",
                    "webViewLink": "https://docs.google.com/doc1",
                    "mimeType": "application/vnd.google-apps.document",
                }
            if method == "GET":
                return doc_json
            if method == "POST" and ":batchUpdate" in url:
                requests = kwargs.get("json_data", {}).get("requests", [])
                batch_calls.append(requests)
                return {"writeControl": {}}
            raise AssertionError(f"Unexpected call: {method} {url}")

        svc._make_request.side_effect = dispatch
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {"markdown_content": new_md, "document_id": "doc1", "title": "Doc"}
        )

        assert result["status"] == "updated"
        # Exactly one batchUpdate call, with a small number of requests — not a
        # whole-body deleteContentRange over the entire old document.
        assert len(batch_calls) == 1
        requests = batch_calls[0]
        assert not any(
            "deleteContentRange" in r
            and r["deleteContentRange"]["range"]["startIndex"] == 1
            and r["deleteContentRange"]["range"]["endIndex"]
            == doc_json["body"]["content"][-1]["endIndex"] - 1
            for r in requests
        )
        assert len(requests) <= 2  # a scoped insertText (+ optional style reapply)

    @pytest.mark.asyncio
    async def test_default_path_uses_full_get_not_restricted_fields(self) -> None:
        """The diff path needs full paragraph/table/list detail, unlike the old
        destructive path's narrow ``fields`` projection — verify no restrictive
        ``fields`` param is sent on the initial document fetch."""
        md = "Just text.\n"
        doc_json = _build_doc_json(md)
        svc = _make_service()

        async def dispatch(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
            if method == "GET" and "/files/" in url:
                return {"id": "doc1", "name": "Doc", "webViewLink": "x", "mimeType": "y"}
            if method == "GET":
                assert "params" not in kwargs or "fields" not in kwargs.get("params", {})
                return doc_json
            raise AssertionError(f"Unexpected call: {method} {url}")

        svc._make_request.side_effect = dispatch
        handlers = get_handlers(svc)
        result = await handlers["markdown_file_to_doc"](
            {"markdown_content": md, "document_id": "doc1", "title": "Doc"}
        )
        assert result["status"] == "no_changes"
