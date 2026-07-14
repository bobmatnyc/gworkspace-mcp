"""Unit tests for the docs.sync drift/conflict snapshot bookkeeping (Phase D).

Covers:
- ``appProperties`` <-> ``SyncSnapshot`` round-trip (parse + build), including
  the "predates this feature" (all-missing-keys) case.
- ``read_snapshot``/``write_snapshot`` against a mocked ``svc._make_request``
  (Drive ``files.get``/``files.update``, no live API).
- ``classify``'s five states: no_snapshot, in_sync, doc_drifted, md_drifted,
  conflict.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from gworkspace_mcp.server.services.docs.sync.snapshot import (
    SyncSnapshot,
    app_properties_from_snapshot,
    classify,
    hash_markdown,
    read_snapshot,
    snapshot_from_app_properties,
    write_snapshot,
)


def _service_returning(response: dict[str, Any]) -> MagicMock:
    svc = MagicMock()
    svc._make_request = AsyncMock(return_value=response)
    return svc


@pytest.mark.unit
class TestSnapshotParsing:
    def test_missing_app_properties_is_empty(self) -> None:
        snap = snapshot_from_app_properties(None)
        assert snap.is_empty
        assert snap == SyncSnapshot(None, None, None, None)

    def test_round_trip_through_app_properties(self) -> None:
        props = app_properties_from_snapshot("rev-9", hash_markdown("hi"), "accepted")
        snap = snapshot_from_app_properties(props)
        assert snap.doc_revision == "rev-9"
        assert snap.md_hash == hash_markdown("hi")
        assert snap.read_suggestions == "accepted"
        assert snap.timestamp is not None
        assert not snap.is_empty

    def test_none_values_omitted_not_stringified(self) -> None:
        props = app_properties_from_snapshot(None, None, "accepted")
        assert "gworkspace_mcp_sync_doc_revision" not in props
        assert "gworkspace_mcp_sync_md_hash" not in props
        assert snapshot_from_app_properties(props).is_empty

    def test_hash_is_stable_and_content_sensitive(self) -> None:
        assert hash_markdown("a") == hash_markdown("a")
        assert hash_markdown("a") != hash_markdown("b")


@pytest.mark.unit
class TestReadWriteSnapshot:
    @pytest.mark.asyncio
    async def test_read_snapshot_parses_drive_response(self) -> None:
        svc = _service_returning({"appProperties": {"gworkspace_mcp_sync_doc_revision": "rev-1"}})
        snap = await read_snapshot(svc, "doc1")
        assert snap.doc_revision == "rev-1"
        url = svc._make_request.call_args.args[1]
        assert url.endswith("/files/doc1")
        assert svc._make_request.call_args.kwargs["params"] == {"fields": "appProperties"}

    @pytest.mark.asyncio
    async def test_write_snapshot_patches_drive_file(self) -> None:
        svc = _service_returning({})
        await write_snapshot(
            svc, "doc1", doc_revision="rev-2", md_hash="abc", read_suggestions="rejected"
        )
        method, url = svc._make_request.call_args.args[:2]
        body = svc._make_request.call_args.kwargs["json_data"]
        assert method == "PATCH"
        assert url.endswith("/files/doc1")
        assert body["appProperties"]["gworkspace_mcp_sync_doc_revision"] == "rev-2"
        assert body["appProperties"]["gworkspace_mcp_sync_md_hash"] == "abc"
        assert body["appProperties"]["gworkspace_mcp_sync_read_suggestions"] == "rejected"
        assert "gworkspace_mcp_sync_timestamp" in body["appProperties"]


@pytest.mark.unit
class TestClassify:
    def _snap(self, doc_rev: str | None, md_hash: str | None) -> SyncSnapshot:
        return SyncSnapshot(
            doc_revision=doc_rev, md_hash=md_hash, read_suggestions="accepted", timestamp="1"
        )

    def test_no_snapshot_when_never_synced(self) -> None:
        empty = SyncSnapshot(None, None, None, None)
        state = classify(empty, current_doc_revision="rev-1", current_md_hash="h1")
        assert state == "no_snapshot"

    def test_in_sync_when_neither_side_moved(self) -> None:
        snap = self._snap("rev-1", "h1")
        assert classify(snap, current_doc_revision="rev-1", current_md_hash="h1") == "in_sync"

    def test_doc_drifted_when_only_doc_revision_moved(self) -> None:
        snap = self._snap("rev-1", "h1")
        state = classify(snap, current_doc_revision="rev-2", current_md_hash="h1")
        assert state == "doc_drifted"

    def test_md_drifted_when_only_hash_moved(self) -> None:
        snap = self._snap("rev-1", "h1")
        state = classify(snap, current_doc_revision="rev-1", current_md_hash="h2")
        assert state == "md_drifted"

    def test_conflict_when_both_moved(self) -> None:
        snap = self._snap("rev-1", "h1")
        state = classify(snap, current_doc_revision="rev-2", current_md_hash="h2")
        assert state == "conflict"
