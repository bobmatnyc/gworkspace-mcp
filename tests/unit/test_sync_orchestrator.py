"""Unit tests for the sync_markdown_doc orchestrator (Phase D).

End-to-end through the real handler (``get_handlers``) with a single mocked
``svc._make_request`` dispatch function -- no live Google API calls. Covers:
- Tool registration + schema shape.
- Explicit md_to_doc: idempotent no-op, and a real minimal patch.
- Explicit doc_to_md: delegates to writeback, writes the markdown file.
- direction="auto": no-snapshot/md-drifted -> md_to_doc; doc-drifted -> doc_to_md.
- Conflict (both sides drifted): on_conflict="flag" (default) skips all writes.
- mode="preview": plans without ever issuing a batchUpdate.
- mode="suggest": capability probe failure degrades to preview -- no direct
  commit is ever attempted as a fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from gworkspace_mcp.server.services.docs.sync import snapshot
from gworkspace_mcp.server.services.docs.sync.orchestrator import TOOLS, get_handlers
from tests.unit.test_markdown_file_diff_path import _build_doc_json

_MD = "# Title\n\nHello world.\n"
_MD_CHANGED = "# Title\n\nHello there world.\n"


def _drive_meta() -> dict[str, Any]:
    return {
        "id": "doc1",
        "name": "Doc",
        "webViewLink": "https://docs.google.com/doc1",
        "mimeType": "application/vnd.google-apps.document",
    }


class _FakeService:
    """Records every call and routes it by (method, url, params) shape."""

    def __init__(
        self,
        doc_json: dict[str, Any],
        app_properties: dict[str, str] | None = None,
        *,
        raise_on_suggest: bool = False,
        comment_update_state: str | None = "ALL_SAVED",
    ) -> None:
        self.doc_json = doc_json
        self.app_properties = app_properties or {}
        self.raise_on_suggest = raise_on_suggest
        self.comment_update_state = comment_update_state
        self.batch_calls: list[tuple[list[dict[str, Any]], dict[str, Any]]] = []
        self.patch_calls: list[dict[str, Any]] = []
        self._make_request = AsyncMock(side_effect=self._dispatch)

    async def _dispatch(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        params = kwargs.get("params", {}) or {}

        if method == "GET" and "/files/" in url:
            if params.get("fields") == "appProperties":
                return {"appProperties": self.app_properties}
            return _drive_meta()

        if method == "GET" and "/documents/" in url:
            if params.get("fields") == "revisionId":
                return {"revisionId": self.doc_json.get("revisionId")}
            return self.doc_json

        if method == "POST" and ":batchUpdate" in url:
            body = kwargs.get("json_data", {}) or {}
            requests = body.get("requests", [])
            write_control = body.get("writeControl", {}) or {}
            self.batch_calls.append((requests, write_control))
            if write_control.get("writeMode") == "SUGGEST":
                if self.raise_on_suggest:
                    request = httpx.Request("POST", url)
                    response = httpx.Response(400, request=request)
                    raise httpx.HTTPStatusError("simulated", request=request, response=response)
                return {"commentUpdateState": self.comment_update_state}
            return {}

        if method == "PATCH" and "/files/" in url:
            self.patch_calls.append(kwargs.get("json_data", {}))
            return {}

        raise AssertionError(f"Unexpected call: {method} {url} params={params}")


@pytest.mark.unit
class TestToolRegistration:
    def test_sync_markdown_doc_registered_with_expected_schema(self) -> None:
        tool = next(t for t in TOOLS if t.name == "sync_markdown_doc")
        props = tool.inputSchema["properties"]
        assert set(props["direction"]["enum"]) == {"md_to_doc", "doc_to_md", "auto"}
        assert set(props["mode"]["enum"]) == {"direct", "suggest", "preview"}
        assert set(props["on_conflict"]["enum"]) == {
            "flag",
            "markdown_wins",
            "doc_wins",
            "suggest",
        }
        assert "account" in props
        assert tool.inputSchema["required"] == ["document_id"]


@pytest.mark.unit
class TestExplicitMdToDoc:
    @pytest.mark.asyncio
    async def test_idempotent_no_op(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json)
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {"markdown_content": _MD, "document_id": "doc1", "direction": "md_to_doc"}
        )
        assert result["status"] == "no_changes"
        assert result["direction_applied"] == "md_to_doc"
        assert result["requests_issued"] == 0
        assert svc.batch_calls == []
        # A no-op sync still records a fresh snapshot (revision + hash).
        assert len(svc.patch_calls) == 1

    @pytest.mark.asyncio
    async def test_applies_minimal_patch_when_changed(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json)
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {"markdown_content": _MD_CHANGED, "document_id": "doc1", "direction": "md_to_doc"}
        )
        assert result["status"] == "synced"
        assert result["requests_issued"] > 0
        assert len(svc.batch_calls) == 1


@pytest.mark.unit
class TestExplicitDocToMd:
    @pytest.mark.asyncio
    async def test_writes_markdown_file(self, tmp_path: Path) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json)
        handlers = get_handlers(svc)
        out = tmp_path / "out.md"
        result = await handlers["sync_markdown_doc"](
            {
                "markdown_file_path": str(out),
                "document_id": "doc1",
                "direction": "doc_to_md",
            }
        )
        assert result["status"] == "synced"
        assert result["direction_applied"] == "doc_to_md"
        assert out.read_text(encoding="utf-8") == result["markdown_content"]
        assert svc.batch_calls == []  # doc_to_md never issues Docs batchUpdate calls
        assert len(svc.patch_calls) == 1  # snapshot write


@pytest.mark.unit
class TestAutoDirection:
    @pytest.mark.asyncio
    async def test_no_snapshot_pushes_markdown(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json, app_properties={})
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {"markdown_content": _MD_CHANGED, "document_id": "doc1", "direction": "auto"}
        )
        assert result["direction_applied"] == "md_to_doc"
        assert result["status"] == "synced"

    @pytest.mark.asyncio
    async def test_doc_drifted_pulls_markdown(self, tmp_path: Path) -> None:
        doc_json = _build_doc_json(_MD)
        md_hash = snapshot.hash_markdown(_MD)
        # Snapshot's stored doc revision differs from the doc's current
        # revision -> only the Doc side moved -> auto picks doc_to_md.
        props = snapshot.app_properties_from_snapshot("stale-rev", md_hash, "accepted")
        svc = _FakeService(doc_json, app_properties=props)
        handlers = get_handlers(svc)
        out = tmp_path / "out.md"
        result = await handlers["sync_markdown_doc"](
            {"markdown_file_path": str(out), "document_id": "doc1", "direction": "auto"}
        )
        assert result["direction_applied"] == "doc_to_md"
        assert svc.batch_calls == []


@pytest.mark.unit
class TestConflict:
    @pytest.mark.asyncio
    async def test_flag_default_skips_all_writes(self) -> None:
        doc_json = _build_doc_json(_MD)  # current revision == "rev1"
        # Snapshot disagrees with BOTH the current doc revision and the
        # current markdown hash -> both sides drifted -> conflict.
        props = snapshot.app_properties_from_snapshot(
            "stale-rev", snapshot.hash_markdown("stale markdown"), "accepted"
        )
        svc = _FakeService(doc_json, app_properties=props)
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {"markdown_content": _MD_CHANGED, "document_id": "doc1", "direction": "auto"}
        )
        assert result["status"] == "conflict"
        assert result["blocks"]["conflicted"] == 1
        assert result["requests_issued"] == 0
        assert svc.batch_calls == []
        assert svc.patch_calls == []  # no snapshot write on a flagged conflict


@pytest.mark.unit
class TestPreviewMode:
    @pytest.mark.asyncio
    async def test_plans_without_writing(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json)
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {
                "markdown_content": _MD_CHANGED,
                "document_id": "doc1",
                "direction": "md_to_doc",
                "mode": "preview",
            }
        )
        assert result["status"] == "dry_run"
        assert result["mode_applied"] == "preview"
        assert result["requests_issued"] == 0
        assert svc.batch_calls == []
        assert svc.patch_calls == []  # preview never records a snapshot

    @pytest.mark.asyncio
    async def test_dry_run_flag_is_equivalent(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json)
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {
                "markdown_content": _MD_CHANGED,
                "document_id": "doc1",
                "direction": "md_to_doc",
                "dry_run": True,
            }
        )
        assert result["mode_applied"] == "preview"
        assert svc.batch_calls == []


@pytest.mark.unit
class TestSuggestModeCapabilityProbe:
    @pytest.mark.asyncio
    async def test_unavailable_suggest_degrades_to_preview_no_direct_commit(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json, raise_on_suggest=True)
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {
                "markdown_content": _MD_CHANGED,
                "document_id": "doc1",
                "direction": "md_to_doc",
                "mode": "suggest",
            }
        )
        assert result["mode_applied"] == "preview"
        assert result["suggestion_capability"] is False
        assert "warning" in result
        assert result["requests_issued"] == 0
        # Exactly one batchUpdate attempt (the failed SUGGEST probe) -- no
        # second, direct-mode fallback call was ever made.
        assert len(svc.batch_calls) == 1
        assert svc.batch_calls[0][1].get("writeMode") == "SUGGEST"
        assert svc.patch_calls == []  # a degraded/preview result never snapshots

    @pytest.mark.asyncio
    async def test_available_suggest_reports_success(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(doc_json, raise_on_suggest=False, comment_update_state="ALL_SAVED")
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {
                "markdown_content": _MD_CHANGED,
                "document_id": "doc1",
                "direction": "md_to_doc",
                "mode": "suggest",
            }
        )
        assert result["mode_applied"] == "suggest"
        assert result["suggestion_capability"] is True
        assert result["requests_issued"] > 0
        assert len(svc.batch_calls) == 1
        assert svc.batch_calls[0][1].get("writeMode") == "SUGGEST"

    @pytest.mark.asyncio
    async def test_partial_failure_comment_update_state_surfaces_warning(self) -> None:
        doc_json = _build_doc_json(_MD)
        svc = _FakeService(
            doc_json, raise_on_suggest=False, comment_update_state="ALL_FAILED_UNKNOWN_REASON"
        )
        handlers = get_handlers(svc)
        result = await handlers["sync_markdown_doc"](
            {
                "markdown_content": _MD_CHANGED,
                "document_id": "doc1",
                "direction": "md_to_doc",
                "mode": "suggest",
            }
        )
        assert result["suggestion_capability"] is False
        assert "warning" in result
        # The text change itself DID commit (this is the risk #2 scenario) --
        # requests_issued reflects that, unlike the pre-flight probe failure.
        assert result["requests_issued"] > 0
