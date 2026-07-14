"""Drift/conflict snapshot bookkeeping (RFC section 6).

Detects whether the Doc and/or the Markdown side changed since the last
successful sync, using two independent, cheap signals:

- The Doc's ``revisionId`` (every ``documents.get`` already returns one) —
  a mismatch against the last-synced revision means "the doc changed since we
  last touched it" (from any source, including a human).
- A ``sha256`` of the Markdown content at last-sync time — a mismatch against
  the current file/content hash means "the Markdown changed since last sync".

**Storage** — Drive ``appProperties`` (a private, per-app string-keyed metadata
map on the Drive ``File`` resource): travels with the file itself, survives
moves/renames, requires no new storage subsystem (``DRIVE_API_BASE`` is already
a first-class import in this package). Keys, matching the RFC exactly:

    gworkspace_mcp_sync_doc_revision
    gworkspace_mcp_sync_md_hash
    gworkspace_mcp_sync_read_suggestions
    gworkspace_mcp_sync_timestamp

No local sidecar file is implemented in this phase (see module-level deviation
note in ``orchestrator.py``): the RFC's 3-way (base/local/remote) conflict
model needs the *exact* last-synced Markdown text as a merge base, which
``appProperties`` alone cannot hold economically. Without it, conflict
detection degrades to the RFC's own documented fallback (section 6, "If the
sidecar is absent... fall back to the coarser hash-only drift signal") — this
module always operates in that degraded-but-documented mode.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Literal

from gworkspace_mcp.server.constants import DRIVE_API_BASE

SyncState = Literal["no_snapshot", "in_sync", "doc_drifted", "md_drifted", "conflict"]

_KEY_DOC_REVISION = "gworkspace_mcp_sync_doc_revision"
_KEY_MD_HASH = "gworkspace_mcp_sync_md_hash"
_KEY_READ_SUGGESTIONS = "gworkspace_mcp_sync_read_suggestions"
_KEY_TIMESTAMP = "gworkspace_mcp_sync_timestamp"


@dataclass(frozen=True)
class SyncSnapshot:
    """The last-synced state recorded for one (document_id, markdown) pair."""

    doc_revision: str | None
    md_hash: str | None
    read_suggestions: str | None
    timestamp: str | None

    @property
    def is_empty(self) -> bool:
        return self.doc_revision is None and self.md_hash is None


def hash_markdown(markdown_content: str) -> str:
    """``sha256`` hex digest of Markdown content, for drift comparison."""
    return hashlib.sha256(markdown_content.encode("utf-8")).hexdigest()


def snapshot_from_app_properties(app_properties: dict[str, Any] | None) -> SyncSnapshot:
    """Parse a Drive ``File.appProperties`` dict into a ``SyncSnapshot``.

    Missing keys (no prior sync, or a file predating this feature) yield an
    all-``None`` (``is_empty``) snapshot rather than raising.
    """
    props = app_properties or {}
    return SyncSnapshot(
        doc_revision=props.get(_KEY_DOC_REVISION),
        md_hash=props.get(_KEY_MD_HASH),
        read_suggestions=props.get(_KEY_READ_SUGGESTIONS),
        timestamp=props.get(_KEY_TIMESTAMP),
    )


def app_properties_from_snapshot(
    doc_revision: str | None,
    md_hash: str | None,
    read_suggestions: str,
) -> dict[str, str]:
    """Build the ``appProperties`` payload for a freshly-completed sync.

    Values that are ``None`` (e.g. a Doc response with no ``revisionId``) are
    omitted rather than written as the string ``"None"``.
    """
    payload: dict[str, str] = {
        _KEY_READ_SUGGESTIONS: read_suggestions,
        _KEY_TIMESTAMP: str(int(time.time())),
    }
    if doc_revision is not None:
        payload[_KEY_DOC_REVISION] = doc_revision
    if md_hash is not None:
        payload[_KEY_MD_HASH] = md_hash
    return payload


async def read_snapshot(svc: Any, document_id: str) -> SyncSnapshot:
    """Fetch the current ``appProperties`` snapshot for ``document_id`` via Drive."""
    url = f"{DRIVE_API_BASE}/files/{document_id}"
    response = await svc._make_request("GET", url, params={"fields": "appProperties"})
    return snapshot_from_app_properties(response.get("appProperties"))


async def write_snapshot(
    svc: Any,
    document_id: str,
    *,
    doc_revision: str | None,
    md_hash: str | None,
    read_suggestions: str,
) -> None:
    """Persist a fresh snapshot to ``document_id``'s Drive ``appProperties``
    immediately after a successful sync (RFC section 6: capture the revision
    *after* our own edits, not before, since our own writes also bump it)."""
    url = f"{DRIVE_API_BASE}/files/{document_id}"
    payload = app_properties_from_snapshot(doc_revision, md_hash, read_suggestions)
    await svc._make_request("PATCH", url, json_data={"appProperties": payload})


def classify(
    snapshot: SyncSnapshot,
    *,
    current_doc_revision: str | None,
    current_md_hash: str | None,
) -> SyncState:
    """Classify drift/conflict state from a snapshot and the two sides' current
    signals (RFC section 6).

    - ``no_snapshot``: never synced before (or the Drive file predates this
      feature) — the caller should treat this as "sync catch-up", not a
      conflict.
    - ``in_sync``: neither side moved since the last sync.
    - ``doc_drifted``: only the Doc changed (a human edited it) — safe to pull
      (``doc_to_md``) or, for ``md_to_doc``, still safe to push since the
      differ diffs against the Doc's *current* live state (RFC section 6: this
      is "sync catch-up", not a conflict).
    - ``md_drifted``: only the Markdown side changed — safe to push
      (``md_to_doc``).
    - ``conflict``: **both** sides changed since the last sync. Without a local
      sidecar holding the exact last-synced Markdown text (see module
      docstring), this module cannot distinguish "both changed but agree" from
      "both changed and disagree" — so it conservatively reports ``conflict``
      whenever both signals moved, which is the documented degraded fallback
      the RFC accepts for a sidecar-less setup, and is the *safe* direction to
      err in the `on_conflict="flag"` default (never silently overwrite).
    """
    if snapshot.is_empty:
        return "no_snapshot"

    doc_changed = (
        snapshot.doc_revision is not None and snapshot.doc_revision != current_doc_revision
    )
    md_changed = snapshot.md_hash is not None and snapshot.md_hash != current_md_hash

    if doc_changed and md_changed:
        return "conflict"
    if doc_changed:
        return "doc_drifted"
    if md_changed:
        return "md_drifted"
    return "in_sync"
