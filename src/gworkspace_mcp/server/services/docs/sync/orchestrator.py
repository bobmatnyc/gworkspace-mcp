"""``sync_markdown_doc`` orchestrator (RFC Phase D).

Wires Phases A-C plus drift/conflict snapshotting (``sync.snapshot``) into the
single user-facing MCP tool the RFC (section 7) specifies: given a Markdown
source (file path and/or inline content) and a ``document_id``, reconcile the
two in the requested ``direction``, applying the requested ``mode`` and
``on_conflict`` policy.

- ``direction=md_to_doc``: reuses ``differ``/``patch_planner`` (Phase B) via
  ``markdown_file._apply_diff_patch`` for the actual minimal in-place patch —
  imported lazily (inside the handler, not at module scope) specifically to
  avoid a circular import: ``markdown_file.py`` imports several names from
  this ``sync`` package at module load time, so importing it back from here
  eagerly would race the package's own ``__init__`` order. A local, per-call
  import sidesteps that cleanly without duplicating the table-structural
  replace / index-ordering logic that already lives there.
- ``direction=doc_to_md``: delegates entirely to ``writeback.doc_to_markdown``
  (Phase C).
- ``direction=auto``: uses ``snapshot.classify`` to pick a side (RFC section 6).
- ``mode=preview``/``dry_run=True``: computes the plan (differ + patch_planner)
  without issuing any ``batchUpdate`` call.
- ``mode=suggest``: capability-probed (RFC section 5.3) -- attempts
  ``writeControl.writeMode="SUGGEST"``; any failure (exception, or a
  non-``ALL_SAVED``/``NO_UPDATES_REQUESTED`` ``commentUpdateState`` before the
  call even lands) degrades to the ``preview`` result rather than silently
  committing a direct edit. Table-structural ops are never attempted in
  suggest mode (the RFC documents ``updateTableColumnProperties`` -- used by
  every table replace -- as explicitly unsupported in Developer Preview) and
  are reported wholesale in ``deferred_requests`` instead.

**RFC deviations (explicit)**: no local sidecar (``.gworkspace-sync/*.json``)
is implemented -- see ``snapshot.py``'s module docstring. Without the exact
last-synced Markdown text as a merge base, this orchestrator cannot do the
RFC's per-block 3-way compare; conflict detection and ``on_conflict`` handling
therefore operate at whole-document granularity (a single conflict summary
entry, not the RFC's per-block ``conflicts`` list with ``block_index``). This
is the RFC's own documented "sidecar absent" fallback (section 6), and is the
*safe* direction to simplify in: a whole-document conflict still means "flag"
skips the entire write rather than guessing per block.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx
from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE, DRIVE_API_BASE
from gworkspace_mcp.server.services.docs.sync import differ, patch_planner, serializer, snapshot
from gworkspace_mcp.server.services.docs.sync.blocks import parse_markdown
from gworkspace_mcp.server.services.docs.sync.writeback import (
    _resolve_write_path,
    doc_to_markdown,
)

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

_DIRECTIONS = ("md_to_doc", "doc_to_md", "auto")
_MODES = ("direct", "suggest", "preview")
_ON_CONFLICT_POLICIES = ("flag", "markdown_wins", "doc_wins", "suggest")
_READ_SUGGESTIONS = ("accepted", "rejected", "annotate")

# commentUpdateState values that mean "the suggestion wrapper itself is fine"
# (RFC section 5.2/10 risk #2) -- anything else means the text change may have
# landed while the "this was a suggestion" metadata failed to save, which must
# be surfaced loudly rather than treated as a clean suggest-mode success.
_SUGGEST_OK_STATES = frozenset({"ALL_SAVED", "NO_UPDATES_REQUESTED", None})

TOOLS: list[Tool] = [
    Tool(
        name="sync_markdown_doc",
        description=(
            "Bidirectionally reconcile a Markdown source with a Google Doc via a minimal, "
            "in-place diff/patch (never a destructive full-body rebuild). "
            "direction='md_to_doc' pushes Markdown changes into the Doc; 'doc_to_md' pulls "
            "the Doc's current content back out as faithful GFM Markdown; 'auto' (default) "
            "picks a side using the last-synced snapshot (Drive appProperties): only the "
            "drifted side is applied, and if BOTH sides changed since the last sync the run "
            "is flagged as a conflict rather than guessing. "
            "mode='direct' (default) applies the patch immediately; 'preview' (or dry_run=true) "
            "computes and returns the plan without writing anything; 'suggest' attempts to "
            "author the edit as a reviewable Google Docs suggestion (Developer Preview API, "
            "capability-probed every call) and gracefully falls back to 'preview' -- never a "
            "silent direct commit -- if suggestion authoring isn't available for this account. "
            "on_conflict controls what happens when both sides drifted: 'flag' (default) skips "
            "the write and reports the conflict; 'markdown_wins'/'doc_wins' proceed with that "
            "side anyway; 'suggest' forces mode=suggest (capability-probed) for the conflicting "
            "edit instead of overwriting either side. "
            "read_suggestions controls how pending Google Docs suggestions are read on the "
            "doc_to_md side: 'accepted' (default) serializes the doc as if suggestions were "
            "already accepted; 'rejected' serializes the pre-suggestion baseline; 'annotate' "
            "is not yet supported. "
            "REQUIRED: document_id, plus at least one of markdown_file_path (server-side read, "
            "and the doc_to_md write destination) or markdown_content (inline)."
        ),
        inputSchema={
            "type": "object",
            "anyOf": [
                {"required": ["markdown_file_path", "document_id"]},
                {"required": ["markdown_content", "document_id"]},
            ],
            "properties": {
                "markdown_file_path": {
                    "type": "string",
                    "description": (
                        "Absolute path to the Markdown file on the server. Read as the "
                        "md_to_doc source (server-side, so large files are never truncated) "
                        "and/or written as the doc_to_md destination."
                    ),
                },
                "markdown_content": {
                    "type": "string",
                    "description": (
                        "Inline Markdown content. Used as the md_to_doc source when "
                        "markdown_file_path is absent or does not yet exist."
                    ),
                },
                "document_id": {
                    "type": "string",
                    "description": "Target Google Doc id. Required -- this tool never creates "
                    "a new document (use markdown_file_to_doc for that).",
                },
                "direction": {
                    "type": "string",
                    "enum": list(_DIRECTIONS),
                    "default": "auto",
                },
                "mode": {
                    "type": "string",
                    "enum": list(_MODES),
                    "default": "direct",
                },
                "on_conflict": {
                    "type": "string",
                    "enum": list(_ON_CONFLICT_POLICIES),
                    "default": "flag",
                },
                "read_suggestions": {
                    "type": "string",
                    "enum": list(_READ_SUGGESTIONS),
                    "default": "accepted",
                },
                "write_markdown_file": {
                    "type": "boolean",
                    "default": True,
                    "description": "For doc_to_md: whether to write markdown_file_path to disk.",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Equivalent to mode='preview'.",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default "
                    "account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Markdown source resolution
# ---------------------------------------------------------------------------


def _read_markdown_source(
    markdown_file_path: str | None, markdown_content: str | None
) -> str | None:
    """Resolve "the current Markdown text" for classification/md_to_doc.

    Mirrors ``markdown_file``'s file-path-takes-precedence convention, but
    tolerates a missing file (returns ``None``) rather than raising -- a
    ``doc_to_md`` pull may name ``markdown_file_path`` purely as a write
    *destination* that doesn't exist yet. Callers that actually need source
    text (``md_to_doc``) must raise themselves when this returns ``None``.
    """
    if markdown_file_path:
        path = _resolve_write_path(markdown_file_path)
        if path.is_file():
            return path.read_text(encoding="utf-8")
        if markdown_content:
            return markdown_content
        return None
    return markdown_content


async def _peek_doc_revision(svc: BaseService, document_id: str) -> str | None:
    """Lightweight ``revisionId``-only fetch, used for drift classification
    before deciding which (possibly expensive) direction to run."""
    url = f"{DOCS_API_BASE}/documents/{document_id}"
    response = await svc._make_request("GET", url, params={"fields": "revisionId"})
    return response.get("revisionId")


def _resolve_direction(
    direction_arg: str, state: snapshot.SyncState, on_conflict: str
) -> tuple[str, bool]:
    """Pick a concrete direction and whether this run is a flagged conflict.

    Returns ``(direction, is_flagged_conflict)``. ``is_flagged_conflict`` is
    True only when the state is ``conflict`` AND ``on_conflict == "flag"`` --
    the caller must then skip all writes and report ``status="conflict"``.
    For any other ``on_conflict`` policy, a conflict state still resolves to a
    concrete direction (the policy's chosen side), and it is up to the mode
    layer (``suggest``) to make that resolution non-destructive when
    ``on_conflict == "suggest"``.
    """
    if direction_arg != "auto":
        if direction_arg not in _DIRECTIONS:
            raise ValueError(f"Unknown direction={direction_arg!r}; expected one of {_DIRECTIONS}")
        return direction_arg, state == "conflict" and on_conflict == "flag"

    if state == "conflict":
        if on_conflict == "flag":
            return "md_to_doc", True  # direction is moot; caller skips anyway
        if on_conflict == "doc_wins":
            return "doc_to_md", False
        # "markdown_wins" and "suggest" both push the Markdown side; "suggest"
        # additionally forces mode=suggest at the call site (RFC section 6/5.3).
        return "md_to_doc", False

    if state == "doc_drifted":
        return "doc_to_md", False
    # "md_drifted", "in_sync", and "no_snapshot" all default to pushing
    # Markdown -- for "in_sync"/"no_snapshot" this is a safe idempotent no-op
    # (Phase B guarantees zero requests when nothing changed) or first-sync
    # bootstrap, respectively.
    return "md_to_doc", False


# ---------------------------------------------------------------------------
# md_to_doc: plan (shared by preview + suggest) and the three mode appliers
# ---------------------------------------------------------------------------


async def _plan_md_to_doc(
    svc: BaseService, document_id: str, new_blocks: list[dict[str, Any]]
) -> tuple[patch_planner.PatchPlan, str | None]:
    """Fetch the live Doc and compute the (unapplied) minimal patch plan.

    Pure planning -- issues exactly one ``GET``, never a ``batchUpdate``.
    Shared by ``mode="preview"`` and the planning half of ``mode="suggest"``.
    """
    doc = await svc._make_request("GET", f"{DOCS_API_BASE}/documents/{document_id}")
    old_with_ranges = serializer.doc_json_to_blocks_with_ranges(doc)
    old_blocks = [b for b, _s, _e in old_with_ranges]
    old_ranges = [(s, e) for _b, s, e in old_with_ranges]
    doc_end_index = serializer.document_end_index(doc)
    revision_id = doc.get("revisionId")

    diff_ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(
        diff_ops, old_ranges, doc_end_index, required_revision_id=revision_id
    )
    return plan, revision_id


def _blocks_summary(plan: patch_planner.PatchPlan, conflicted: int = 0) -> dict[str, int]:
    return {
        "matched": plan.matched,
        "inserted": plan.inserted,
        "deleted": plan.deleted,
        "modified": plan.modified,
        "conflicted": conflicted,
    }


async def _preview_md_to_doc(
    svc: BaseService, document_id: str, new_blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    """``mode="preview"`` (and ``dry_run=True``): compute and return the plan
    without writing anything."""
    plan, revision_id = await _plan_md_to_doc(svc, document_id, new_blocks)
    planned_requests = len(plan.requests) + len(plan.table_ops)
    return {
        "status": "dry_run" if planned_requests else "no_changes",
        "mode_applied": "preview",
        "revision_id": revision_id,
        "blocks": _blocks_summary(plan),
        "requests_issued": 0,
        "deferred_requests": [
            {"reason": "preview_mode_table_structural_change", "anchor": t.anchor}
            for t in plan.table_ops
        ],
    }


async def _apply_md_to_doc_direct(
    svc: BaseService, document_id: str, new_blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    """``mode="direct"``: reuse Phase B's battle-tested apply path verbatim.

    Local import (not module-level) -- see the module docstring for why.
    """
    from gworkspace_mcp.server.services.docs.markdown_file import _apply_diff_patch

    result = await _apply_diff_patch(svc, document_id, new_blocks)
    return {
        "status": "no_changes" if result["status"] == "no_changes" else "synced",
        "mode_applied": "direct",
        "revision_id": result.get("revision_id"),
        "blocks": {
            "matched": result["blocks_matched"],
            "inserted": result["blocks_inserted"],
            "deleted": result["blocks_deleted"],
            "modified": result["blocks_modified"],
            "conflicted": 0,
        },
        "requests_issued": result["requests_issued"],
        "deferred_requests": [],
    }


async def _apply_md_to_doc_suggest(
    svc: BaseService, document_id: str, new_blocks: list[dict[str, Any]]
) -> dict[str, Any]:
    """``mode="suggest"``: capability-probed suggestion authoring (RFC 5.3).

    Table-structural ops are never attempted here (the RFC documents
    ``updateTableColumnProperties`` -- used by every whole-table replace -- as
    explicitly unsupported in Developer Preview) and are reported wholesale in
    ``deferred_requests``. Any failure to author the (non-table) requests as
    suggestions -- an exception, or a ``commentUpdateState`` other than
    ``ALL_SAVED``/``NO_UPDATES_REQUESTED`` -- degrades the WHOLE result to the
    ``preview`` shape rather than committing a direct edit: this method never
    calls ``batchUpdate`` without ``writeControl.writeMode="SUGGEST"`` set, so
    a failed attempt cannot silently downgrade to a direct commit.
    """
    plan, revision_id = await _plan_md_to_doc(svc, document_id, new_blocks)
    deferred = [
        {"reason": "suggest_mode_table_structural_change_unsupported", "anchor": t.anchor}
        for t in plan.table_ops
    ]

    if not plan.requests:
        return {
            "status": "no_changes",
            "mode_applied": "suggest",
            "revision_id": revision_id,
            "blocks": _blocks_summary(plan),
            "requests_issued": 0,
            "deferred_requests": deferred,
            "suggestion_capability": True,
            "comment_update_state": "NO_UPDATES_REQUESTED",
        }

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    write_control: dict[str, Any] = {"writeMode": "SUGGEST"}
    if revision_id:
        write_control["requiredRevisionId"] = revision_id
    body = {"requests": plan.requests, "writeControl": write_control}

    try:
        response = await svc._make_request("POST", url, json_data=body)
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        logger.warning(
            "suggest-mode batchUpdate failed for %s; degrading to preview: %s",
            document_id,
            exc,
        )
        degraded = await _preview_md_to_doc(svc, document_id, new_blocks)
        degraded["suggestion_capability"] = False
        degraded["warning"] = (
            "Suggestion authoring (Developer Preview writeControl.writeMode=SUGGEST) is "
            "unavailable for this account/document; degraded to mode='preview'. No edits "
            "were applied."
        )
        return degraded

    comment_state = response.get("commentUpdateState")
    ok = comment_state in _SUGGEST_OK_STATES
    result: dict[str, Any] = {
        "status": "synced",
        "mode_applied": "suggest",
        "revision_id": revision_id,
        "blocks": _blocks_summary(plan),
        "requests_issued": len(plan.requests),
        "deferred_requests": deferred,
        "suggestion_capability": ok,
        "comment_update_state": comment_state,
    }
    if not ok:
        # RFC section 10 risk #2: the text change may have committed as a
        # direct edit while the "this was a suggestion" wrapper failed to
        # save. The edit already landed (requests_issued is accurate) --
        # surface this loudly rather than only logging it.
        result["warning"] = (
            f"Suggestion metadata may have failed to save (commentUpdateState="
            f"{comment_state!r}); the text change may have been committed as a DIRECT "
            "edit rather than a reviewable suggestion."
        )
    return result


async def _run_md_to_doc(
    svc: BaseService,
    document_id: str,
    markdown_text: str | None,
    mode: str,
) -> dict[str, Any]:
    if markdown_text is None:
        raise ValueError(
            "md_to_doc requires Markdown source text: supply markdown_content, or "
            "markdown_file_path pointing at an existing file."
        )
    new_blocks = parse_markdown(markdown_text)
    if mode == "preview":
        return await _preview_md_to_doc(svc, document_id, new_blocks)
    if mode == "suggest":
        return await _apply_md_to_doc_suggest(svc, document_id, new_blocks)
    return await _apply_md_to_doc_direct(svc, document_id, new_blocks)


async def _run_doc_to_md(
    svc: BaseService,
    document_id: str,
    *,
    read_suggestions: str,
    markdown_file_path: str | None,
    write_markdown_file: bool,
    mode: str,
) -> dict[str, Any]:
    if mode == "preview":
        write_markdown_file = False
    result = await doc_to_markdown(
        svc,
        document_id,
        read_suggestions=read_suggestions,
        markdown_file_path=markdown_file_path,
        write_markdown_file=write_markdown_file,
    )
    return {
        "status": "dry_run" if mode == "preview" else "synced",
        "mode_applied": "preview" if mode == "preview" else "direct",
        "revision_id": result["revision_id"],
        "blocks": {"matched": 0, "inserted": 0, "deleted": 0, "modified": 0, "conflicted": 0},
        "requests_issued": 0,
        "deferred_requests": [],
        "markdown_content": result["markdown_content"],
        "markdown_file_path": result["markdown_file_path"],
    }


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


async def _sync_markdown_doc(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Reconcile a Markdown source with a Google Doc (RFC section 7)."""
    document_id: str = arguments["document_id"]
    markdown_file_path = arguments.get("markdown_file_path")
    markdown_content = arguments.get("markdown_content")
    direction_arg = arguments.get("direction", "auto")
    mode = arguments.get("mode", "direct")
    on_conflict = arguments.get("on_conflict", "flag")
    read_suggestions = arguments.get("read_suggestions", "accepted")
    write_markdown_file = bool(arguments.get("write_markdown_file", True))
    if bool(arguments.get("dry_run", False)):
        mode = "preview"

    if mode not in _MODES:
        raise ValueError(f"Unknown mode={mode!r}; expected one of {_MODES}")
    if on_conflict not in _ON_CONFLICT_POLICIES:
        raise ValueError(
            f"Unknown on_conflict={on_conflict!r}; expected one of {_ON_CONFLICT_POLICIES}"
        )

    markdown_text = _read_markdown_source(markdown_file_path, markdown_content)
    md_hash = snapshot.hash_markdown(markdown_text) if markdown_text is not None else None

    snap = await snapshot.read_snapshot(svc, document_id)
    current_doc_revision = await _peek_doc_revision(svc, document_id)
    # When we have no local markdown text to hash (e.g. a doc_to_md-only call
    # naming a not-yet-created output path), there is no signal that the
    # Markdown side moved -- treat it as unchanged rather than as a spurious
    # drift/conflict trigger.
    classify_md_hash = md_hash if md_hash is not None else snap.md_hash
    state = snapshot.classify(
        snap, current_doc_revision=current_doc_revision, current_md_hash=classify_md_hash
    )

    direction, is_conflict = _resolve_direction(direction_arg, state, on_conflict)
    forced_suggest = state == "conflict" and on_conflict == "suggest" and direction == "md_to_doc"
    effective_mode = "suggest" if forced_suggest else mode

    file_meta = await svc._make_request(
        "GET",
        f"{DRIVE_API_BASE}/files/{document_id}",
        params={"fields": "id,name,webViewLink,mimeType"},
    )

    if is_conflict:
        result: dict[str, Any] = {
            "status": "conflict",
            "direction_applied": direction,
            "mode_applied": effective_mode,
            "blocks": {"matched": 0, "inserted": 0, "deleted": 0, "modified": 0, "conflicted": 1},
            "requests_issued": 0,
            "deferred_requests": [],
            "conflicts": [
                {
                    "snapshot_doc_revision": snap.doc_revision,
                    "current_doc_revision": current_doc_revision,
                    "snapshot_md_hash": snap.md_hash,
                    "current_md_hash": classify_md_hash,
                }
            ],
        }
    elif direction == "md_to_doc":
        result = await _run_md_to_doc(svc, document_id, markdown_text, effective_mode)
        result["direction_applied"] = "md_to_doc"
        result.setdefault("conflicts", [])
    else:
        result = await _run_doc_to_md(
            svc,
            document_id,
            read_suggestions=read_suggestions,
            markdown_file_path=markdown_file_path,
            write_markdown_file=write_markdown_file,
            mode=effective_mode,
        )
        result["direction_applied"] = "doc_to_md"
        result.setdefault("conflicts", [])

    # Snapshot write-back: only after an actually-applied (non-preview,
    # non-conflict) sync, and only a best-effort -- a failure here must not
    # unwind an already-successful Doc/Markdown write.
    if not is_conflict and result.get("mode_applied") != "preview":
        try:
            new_doc_revision = result.get("revision_id") or current_doc_revision
            new_md_hash = (
                snapshot.hash_markdown(result["markdown_content"])
                if direction == "doc_to_md" and result.get("markdown_content") is not None
                else md_hash
            )
            await snapshot.write_snapshot(
                svc,
                document_id,
                doc_revision=new_doc_revision,
                md_hash=new_md_hash,
                read_suggestions=read_suggestions,
            )
        except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
            logger.warning("Failed to write sync snapshot for %s: %s", document_id, exc)

    result["document_id"] = document_id
    result["webViewLink"] = file_meta.get("webViewLink")
    result["markdown_file_path"] = result.get("markdown_file_path", markdown_file_path)
    result.setdefault("markdown_content", markdown_text)
    return result


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for the sync_markdown_doc handler."""
    return {
        "sync_markdown_doc": lambda args: _sync_markdown_doc(svc, args),
    }
