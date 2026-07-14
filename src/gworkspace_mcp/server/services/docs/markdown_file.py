"""markdown_file_to_doc: robust Markdown-to-Google-Doc tool.

Fixes three failure modes of publish_markdown_to_doc:
1. Server-side file reading — no inline content required, so large docs (700+ lines)
   are never truncated by context limits or output-token limits.
2. Tables with borders — uses the Docs API updateTableCellStyle directly, guaranteeing
   visible borders even after Drive import (which drops DOCX table borders).
3. In-place update — when document_id is supplied, clears the existing body and
   re-inserts; the shareable link is preserved.
"""

from __future__ import annotations

import json
import logging
import secrets
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE, DRIVE_API_BASE
from gworkspace_mcp.server.services.docs.sync import differ, patch_planner, serializer

# The block intermediate-representation (IR) and Markdown parser were relocated
# to ``sync.blocks`` so the Markdown encoder (this module) and the native
# Docs-JSON serializer (``sync.serializer``) share one IR.  These names are
# re-imported here — NOT re-implemented — so existing callers/tests that import
# ``parse_markdown`` / ``_parse_inline_runs`` / ``_HEADING_STYLE`` etc. from
# ``markdown_file`` keep working unchanged.
from gworkspace_mcp.server.services.docs.sync.blocks import (  # noqa: F401  (re-export)
    _HEADING_STYLE,
    _is_separator_row,
    _parse_inline_runs,
    _parse_table,
    _strip_inline_md,
    parse_markdown,
)

# ``_DocBuilder`` was relocated to ``sync.doc_builder`` (same relocate-and-
# re-export pattern) so both this module's create/rebuild path and the Phase B
# diff/patch path (``sync.patch_planner``) can import it without a circular
# dependency.  Re-imported — NOT forked — for backward compatibility.
from gworkspace_mcp.server.services.docs.sync.doc_builder import (  # noqa: F401  (re-export)
    _DocBuilder,
)

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Max requests per batchUpdate call.  Google Docs API allows up to 2000
# requests per batchUpdate, but sending very large batches increases the
# risk of hitting per-request payload size limits.  We use a conservative
# chunk size that comfortably handles 700-line documents.
# ---------------------------------------------------------------------------
_BATCH_CHUNK_SIZE = 200

# Border style applied to every table cell
_TABLE_BORDER = {
    "color": {"color": {"rgbColor": {"red": 0.4, "green": 0.4, "blue": 0.4}}},
    "width": {"magnitude": 0.75, "unit": "PT"},
    "dashStyle": "SOLID",
}

# Header row background (blue-grey)
_HEADER_BG = {"red": 0.2, "green": 0.35, "blue": 0.6}

# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

TOOLS: list[Tool] = [
    Tool(
        name="markdown_file_to_doc",
        description=(
            "Convert a Markdown file to a fully-formatted Google Doc with real table borders, "
            "inline hyperlinks, and correct heading styles.  Reads the file server-side so "
            "large documents (700+ lines / 70 KB+) are never truncated.  "
            "When document_id is supplied, the existing document is updated IN PLACE with a "
            "minimal diff/patch (only the changed paragraphs/tables are touched; unrelated "
            "content and the shareable link are preserved) — re-running with unchanged "
            "markdown is a no-op.  Set force_rebuild=true to instead hard-reset the document "
            "(clear the whole body and rebuild from scratch).  Omit document_id to create a "
            "new document.  "
            "REQUIRED: supply at least one of markdown_file_path (preferred for large files) "
            "or markdown_content (for small inline documents).  If both are provided, "
            "markdown_file_path takes precedence."
        ),
        inputSchema={
            "type": "object",
            "anyOf": [
                {"required": ["markdown_file_path"]},
                {"required": ["markdown_content"]},
            ],
            "properties": {
                "markdown_file_path": {
                    "type": "string",
                    "description": (
                        "Absolute path to the Markdown file on the server.  "
                        "The server reads the file directly — do NOT pass inline content here.  "
                        "Supply this OR markdown_content (at least one is required)."
                    ),
                },
                "markdown_content": {
                    "type": "string",
                    "description": (
                        "Inline Markdown content.  Alternative to markdown_file_path for small "
                        "documents.  Supply this OR markdown_file_path (at least one is required).  "
                        "If both are supplied, markdown_file_path takes precedence."
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Document title.  Required when creating a new document.",
                },
                "document_id": {
                    "type": "string",
                    "description": (
                        "Existing Google Doc ID to update in-place.  By default, only the "
                        "minimal set of changed paragraphs/tables is patched (a full diff "
                        "against the live document) — unrelated content and the shareable link "
                        "are preserved.  Use force_rebuild=true for a full hard reset instead.  "
                        "Omit to create a new document."
                    ),
                },
                "force_rebuild": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Only meaningful with document_id.  When true, skip the minimal diff/"
                        "patch update and instead hard-reset the document: clear the entire "
                        "body and rebuild it from scratch, exactly like the pre-diff-engine "
                        "behavior.  Use this escape hatch if a document's structure has drifted "
                        "in a way the diff engine can't reconcile cleanly.  Default false."
                    ),
                },
                "folder_id": {
                    "type": "string",
                    "description": "Drive folder ID for the new document (ignored when document_id is supplied).",
                },
                "account": {
                    "type": "string",
                    "description": (
                        "Google account profile to use.  Omit to use the default account.  "
                        "Use 'workspace accounts list' to see available profiles."
                    ),
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Async builder — uses Google Docs API to fill table cells and apply styles
# ---------------------------------------------------------------------------


async def _fill_tables_and_style(
    svc: BaseService,
    document_id: str,
    deferred: list[dict[str, Any]],
) -> None:
    """For each deferred fill_table sentinel: re-fetch the doc, find the table,
    fill all cells with text + apply borders + header styling."""
    if not deferred:
        return

    fill_sentinels = [d for d in deferred if d.get("_fill_table")]
    if not fill_sentinels:
        return

    # Re-fetch document to get actual indices after all insertions
    doc = await svc._make_request(
        "GET",
        f"{DOCS_API_BASE}/documents/{document_id}",
        params={"fields": "body(content(table,startIndex,endIndex))"},
    )
    body_content: list[dict[str, Any]] = doc.get("body", {}).get("content", [])

    # Collect tables in document order.  We match sentinels to tables by their
    # sequential position (first sentinel → first table, etc.) rather than by
    # start_index, because the stored table_start_index values come from the
    # builder's pre-insertion estimates which do not account for the pre-table
    # paragraph the API inserts, nor for index shifts caused by earlier inserts.
    doc_tables: list[dict[str, Any]] = [elem for elem in body_content if "table" in elem]

    if len(doc_tables) != len(fill_sentinels):
        logger.warning(
            "Table count mismatch: doc has %d tables, builder has %d sentinels",
            len(doc_tables),
            len(fill_sentinels),
        )

    for sentinel_idx, sentinel in enumerate(fill_sentinels):
        if sentinel_idx >= len(doc_tables):
            logger.warning("No doc table for sentinel %d", sentinel_idx)
            continue
        table_elem = doc_tables[sentinel_idx]

        all_rows: list[list[str]] = sentinel["all_rows"]
        num_cols: int = sentinel["num_cols"]
        num_rows: int = sentinel["num_rows"]
        # Capture the table's actual start_index from the Phase 1 fetch.
        table_actual_start: int = table_elem.get("startIndex", 0)

        table_rows: list[dict[str, Any]] = table_elem.get("table", {}).get("tableRows", [])

        # --- Phase 1: fill cell text ---
        # IMPORTANT: insertText at a given index shifts all subsequent indices
        # forward by the length of the inserted text.  To avoid index drift we
        # must insert cells in REVERSE document order (last cell first).  That
        # way each insertion does not affect the indices of cells that still
        # need to be filled.
        cell_insertions: list[tuple[int, str]] = []  # (para_start_index, text)
        for row_i, row_data in enumerate(all_rows):
            if row_i >= len(table_rows):
                break
            cells = table_rows[row_i].get("tableCells", [])
            for col_i, cell_text in enumerate(row_data[:num_cols]):
                if col_i >= len(cells):
                    break
                if not cell_text.strip():
                    continue
                cell_content = cells[col_i].get("content", [])
                if not cell_content:
                    continue
                # Insert into the first paragraph's start
                para_start = cell_content[0].get("startIndex", 0)
                if para_start:
                    cell_insertions.append((para_start, cell_text))

        # Sort descending by index so each insert does not shift later indices
        cell_insertions.sort(key=lambda x: x[0], reverse=True)
        text_requests: list[dict[str, Any]] = [
            {
                "insertText": {
                    "location": {"index": para_start},
                    "text": cell_text,
                }
            }
            for para_start, cell_text in cell_insertions
        ]

        if text_requests:
            await _batch_update(svc, document_id, text_requests)

        # --- Phase 2: apply borders + header styling ---
        # Re-fetch the single table (by its sentinel index in doc order) to get
        # updated cell indices after text was inserted into it.
        doc2 = await svc._make_request(
            "GET",
            f"{DOCS_API_BASE}/documents/{document_id}",
            params={"fields": "body(content(table,startIndex,endIndex))"},
        )
        body2: list[dict[str, Any]] = doc2.get("body", {}).get("content", [])
        # Tables in doc order; pick the same sentinel_idx-th table.
        # After inserting text into cells the table shifts forward, so we
        # can no longer rely on startIndex.  The table's relative position
        # (its ordinal in the document) is stable.
        doc_tables2 = [e for e in body2 if "table" in e]
        if sentinel_idx >= len(doc_tables2):
            logger.warning("Could not re-locate table %d for styling after text fill", sentinel_idx)
            continue
        target_table_elem = doc_tables2[sentinel_idx]
        if target_table_elem is None:
            logger.warning(
                "Could not re-locate table for styling (rows=%d, cols=%d)", num_rows, num_cols
            )
            continue

        new_ts = target_table_elem.get("startIndex", table_actual_start)
        style_requests: list[dict[str, Any]] = []

        for row_i in range(num_rows):
            is_header = row_i == 0
            for col_i in range(num_cols):
                cell_style: dict[str, Any] = {
                    "borderTop": _TABLE_BORDER,
                    "borderBottom": _TABLE_BORDER,
                    "borderLeft": _TABLE_BORDER,
                    "borderRight": _TABLE_BORDER,
                }
                field_keys = ["borderTop", "borderBottom", "borderLeft", "borderRight"]

                if is_header:
                    cell_style["backgroundColor"] = {"color": {"rgbColor": _HEADER_BG}}
                    field_keys.append("backgroundColor")

                style_requests.append(
                    {
                        "updateTableCellStyle": {
                            "tableCellStyle": cell_style,
                            "fields": ",".join(field_keys),
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": {"index": new_ts},
                                    "rowIndex": row_i,
                                    "columnIndex": col_i,
                                },
                                "rowSpan": 1,
                                "columnSpan": 1,
                            },
                        }
                    }
                )

        # Bold header text
        table_rows2 = target_table_elem.get("table", {}).get("tableRows", [])
        if table_rows2:
            header_cells = table_rows2[0].get("tableCells", [])
            for cell in header_cells:
                content = cell.get("content", [])
                if content:
                    for para_elem in content:
                        para = para_elem.get("paragraph", {})
                        for el in para.get("elements", []):
                            tr = el.get("textRun")
                            if tr:
                                run_start = el.get("startIndex", 0)
                                run_end = el.get("endIndex", run_start)
                                if run_start < run_end:
                                    style_requests.append(
                                        {
                                            "updateTextStyle": {
                                                "range": {
                                                    "startIndex": run_start,
                                                    "endIndex": run_end,
                                                },
                                                "textStyle": {"bold": True},
                                                "fields": "bold",
                                            }
                                        }
                                    )

        if style_requests:
            await _batch_update(svc, document_id, style_requests)


async def _batch_update(
    svc: BaseService,
    document_id: str,
    requests: list[dict[str, Any]],
    write_control: dict[str, Any] | None = None,
) -> None:
    """Issue batchUpdate requests in safe chunks.

    ``write_control`` (e.g. ``{"requiredRevisionId": "..."}``), if given, is
    attached only to the FIRST chunk — the diff/patch path's optimistic-
    concurrency check (RFC section 10 risk #3): the API rejects a stale batch
    with a 400 if the document changed since the revision was captured.
    Subsequent chunks in the same call omit it, since the document's revision
    has necessarily moved on after the first chunk lands — re-checking against
    the original revision would always look stale.
    """
    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    for idx, i in enumerate(range(0, len(requests), _BATCH_CHUNK_SIZE)):
        chunk = requests[i : i + _BATCH_CHUNK_SIZE]
        body: dict[str, Any] = {"requests": chunk}
        if write_control and idx == 0:
            body["writeControl"] = write_control
        await svc._make_request("POST", url, json_data=body)


# ---------------------------------------------------------------------------
# Path-traversal guard helper
# ---------------------------------------------------------------------------


def _is_path_under(path: Path, root: Path) -> bool:
    """Return True if *path* is equal to or a descendant of *root*.

    Why: Prevents path-traversal attacks where a caller supplies a path like
    /etc/passwd to read arbitrary system files.
    What: Uses Path.is_relative_to (Python 3.9+) to check containment after
    both paths have been resolved (symlinks expanded, .. collapsed).
    Test: Assert True for Path('/home/user/docs/file.md') under Path('/home/user');
    assert False for Path('/etc/passwd') under Path('/home/user').
    """
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


async def _insert_blocks_in_segments(
    svc: BaseService,
    document_id: str,
    blocks: list[dict[str, Any]],
    start_index: int,
) -> int:
    """Insert a block list into a document in table-bounded segments.

    Why: After insertTable, the deferred cell-fill pass inserts N characters
    into the newly-created cells.  Any content emitted by the builder AFTER a
    table uses self.index values derived from an arithmetic estimate of the
    table's structural size — an estimate that cannot account for cell-text
    insertions that have not yet happened.  Emitting all subsequent blocks in
    a single batchUpdate therefore causes index drift: paragraphs land inside
    the table rather than after it.

    Fix: split blocks into table-bounded segments.  For each segment we:
      (a) add all non-table blocks to a builder until we hit a table block,
      (b) add the table to the builder (which does NOT advance self.index),
      (c) issue all pending insert_requests,
      (d) call _fill_tables_and_style for just this table,
      (e) re-fetch the document's true end index,
      (f) start a fresh builder at that end index for the next segment.
    Content that follows the last table (or a document with no tables) is
    emitted in a single batchUpdate without any intervening re-fetch.

    Shared by both the full-document create/rebuild path and the diff/patch
    path's table-structural-change segments (``sync.patch_planner``'s
    ``TableReplaceOp`` handling) — the exact same reuse the RFC calls for
    rather than reimplementing table insertion twice.

    Returns the total number of insert requests issued.
    """
    total_insert_requests = 0
    current_index = start_index
    i = 0
    n_blocks = len(blocks)

    while i < n_blocks:
        builder = _DocBuilder(start_index=current_index)
        segment_deferred: list[dict[str, Any]] = []

        # Consume blocks until (and including) the next table, or until end.
        hit_table = False
        while i < n_blocks:
            block = blocks[i]
            btype = block["type"]
            i += 1
            if btype == "heading":
                builder.add_heading(block["level"], block["runs"])
            elif btype == "paragraph":
                builder.add_paragraph(block["runs"])
            elif btype == "code":
                builder.add_code_block(block["text"])
            elif btype == "table":
                builder.add_table(block["headers"], block["rows"])
                # Stop after the table so we can fill it and re-fetch before
                # emitting blocks that follow.
                hit_table = True
                break
            elif btype == "bullet":
                builder.add_bullet(block["depth"], block["runs"])
            elif btype == "ordered":
                builder.add_ordered(block["runs"], block.get("depth", 0))
            elif btype == "blank":
                builder.add_blank()
            elif btype == "rule":
                builder.add_rule()

        insert_requests, segment_deferred = builder.build()

        if insert_requests:
            await _batch_update(svc, document_id, insert_requests)
            total_insert_requests += len(insert_requests)
            logger.info(
                "Segment: inserted %d requests into document %s (hit_table=%s)",
                len(insert_requests),
                document_id,
                hit_table,
            )

        if hit_table and segment_deferred:
            await _fill_tables_and_style(svc, document_id, segment_deferred)

            if i < n_blocks:
                # Re-fetch the document's true end index so subsequent blocks
                # are anchored to the actual document state, not an estimate.
                doc_state = await svc._make_request(
                    "GET",
                    f"{DOCS_API_BASE}/documents/{document_id}",
                    params={"fields": "body(content(endIndex))"},
                )
                body_items = doc_state.get("body", {}).get("content", [])
                if body_items:
                    # The last structural element's endIndex is the document end.
                    # We insert starting at endIndex - 1 (before the final newline).
                    last_end = body_items[-1].get("endIndex", current_index + 1)
                    current_index = max(1, last_end - 1)
                else:
                    # A real Google Doc body always contains at least one structural
                    # element (the terminal newline paragraph).  An empty body list
                    # indicates an unexpected API response — silently fabricating an
                    # index here would corrupt all subsequent inserts by placing them
                    # at an arbitrary position.  Raise so the caller surfaces the
                    # problem rather than producing a silently broken document.
                    logger.warning(
                        "Re-fetched document %s has no body content elements after table fill; "
                        "cannot derive a safe insert index — aborting to prevent index corruption.",
                        document_id,
                    )
                    raise RuntimeError(
                        f"Document {document_id!r} returned an empty body content list after "
                        "table fill.  This indicates an unexpected API state.  Cannot safely "
                        "compute a post-table insert index; aborting to avoid corrupting "
                        "subsequent inserts."
                    )
                logger.info("Re-fetched document end index after table fill: %d", current_index)

    return total_insert_requests


async def _apply_diff_patch(
    svc: BaseService,
    document_id: str,
    new_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Update an existing document in place via minimal diff/patch (Phase B).

    This is the DEFAULT behavior for the ``document_id`` branch: fetch the
    live document, serialize it into the same block IR ``parse_markdown``
    produces (``sync.serializer``), diff the two block lists
    (``sync.differ``), and apply only the minimal set of batchUpdate requests
    needed to reconcile them (``sync.patch_planner``) — never a full-body
    clear-and-rebuild.  Re-running with unchanged Markdown against an
    already-synced document issues zero requests (idempotent).

    Table structural changes are still whole-table replace (RFC section 4):
    delete the old table's range (if any) and reinsert via the same
    ``_insert_blocks_in_segments``/``add_table``/``_fill_tables_and_style``
    pipeline the create/rebuild path already uses — 100% request-construction
    reuse, just scoped to the changed region instead of the whole document.
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

    requests_issued = 0
    if plan.requests:
        await _batch_update(
            svc,
            document_id,
            plan.requests,
            write_control=plan.write_control_kwargs().get("writeControl"),
        )
        requests_issued += len(plan.requests)

    # Table structural changes: highest original-document anchor first, so an
    # earlier (higher-anchored) segment's delete+reinsert never invalidates
    # indices a later (lower-anchored) table op still depends on — the same
    # descending-order rule patch_planner already applies to Round 1.
    for table_op in sorted(plan.table_ops, key=lambda t: t.anchor, reverse=True):
        if table_op.old_range is not None:
            start, end = table_op.old_range
            await _batch_update(
                svc,
                document_id,
                [{"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}}],
            )
            anchor = start
        else:
            anchor = table_op.anchor
        requests_issued += await _insert_blocks_in_segments(
            svc, document_id, table_op.new_blocks, anchor
        )

    return {
        "status": "no_changes" if requests_issued == 0 else "updated",
        "document_id": document_id,
        "revision_id": revision_id,
        "blocks_processed": len(new_blocks),
        "requests_issued": requests_issued,
        "blocks_matched": plan.matched,
        "blocks_inserted": plan.inserted,
        "blocks_deleted": plan.deleted,
        "blocks_modified": plan.modified,
    }


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


async def _markdown_file_to_doc(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Convert a Markdown file (or inline content) to a Google Doc.

    Steps:
    1. Read the markdown (from file path or inline content).
    2. Parse into blocks.
    3. When ``document_id`` is supplied (default): diff against the live
       document and apply a minimal in-place patch (``_apply_diff_patch`` —
       Phase B). Otherwise, or when ``force_rebuild=True``, fall through to
       the create-or-clear-and-rebuild path below.
    4. Create or clear the target document (new documents, or an explicit
       ``force_rebuild`` "hard reset" of an existing one).
    5. Issue insert requests in chunks.
    6. Post-process: fill table cells, apply borders, heading styles.
    7. Return document id + webViewLink.
    """
    markdown_file_path = arguments.get("markdown_file_path")
    markdown_content = arguments.get("markdown_content")
    title = arguments.get("title", "Untitled Document")
    document_id: str | None = arguments.get("document_id")
    folder_id: str | None = arguments.get("folder_id")
    force_rebuild = bool(arguments.get("force_rebuild", False))

    # --- 1. Read markdown ---
    if markdown_file_path:
        path = Path(markdown_file_path).resolve()
        # Path-traversal guard: only allow reads under the current working directory,
        # the user's home directory, or the system temp directory.
        # This blocks /etc/passwd and other system files while keeping the tool
        # practical for local MCP server usage (tmp files, home-dir docs, project files).
        allowed_roots = (
            Path.cwd().resolve(),
            Path.home().resolve(),
            Path(tempfile.gettempdir()).resolve(),
        )
        if not any(_is_path_under(path, root) for root in allowed_roots):
            raise ValueError(
                f"Path '{markdown_file_path}' is outside allowed directories "
                f"({', '.join(str(r) for r in allowed_roots)}). "
                "Only paths under the current working directory, your home directory, "
                "or the system temp directory are permitted."
            )
        if not path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {markdown_file_path}")
        markdown_content = path.read_text(encoding="utf-8")
        logger.info("Read %d chars from %s", len(markdown_content), markdown_file_path)
    elif not markdown_content:
        raise ValueError("Either markdown_file_path or markdown_content must be provided")

    # --- 2. Parse ---
    blocks = parse_markdown(markdown_content)
    logger.info("Parsed %d blocks from markdown", len(blocks))

    # --- 3. In-place update: minimal diff/patch (default) ---
    # RFC section 8 Phase B: this supersedes the old clear-and-rebuild branch
    # as the default for document_id updates.  The destructive rebuild remains
    # available as an explicit "hard reset" escape hatch (force_rebuild=True)
    # per the RFC's back-compat recommendation, rather than being removed.
    if document_id and not force_rebuild:
        diff_result = await _apply_diff_patch(svc, document_id, blocks)
        file_meta = await svc._make_request(
            "GET",
            f"{DRIVE_API_BASE}/files/{document_id}",
            params={"fields": "id,name,webViewLink,mimeType"},
        )
        return {
            **diff_result,
            "title": file_meta.get("name", title),
            "webViewLink": file_meta.get("webViewLink"),
            "mimeType": file_meta.get("mimeType"),
        }

    # --- 4. Create or clear target document ---
    if document_id:
        # force_rebuild=True: explicit hard reset — clear the body then re-insert.
        doc = await svc._make_request(
            "GET",
            f"{DOCS_API_BASE}/documents/{document_id}",
            params={"fields": "body(content(startIndex,endIndex))"},
        )
        body_content = doc.get("body", {}).get("content", [])
        if body_content:
            last_end = body_content[-1].get("endIndex", 1)
            if last_end > 1:
                # Delete everything except the trailing paragraph marker (index 0)
                del_requests: list[dict[str, Any]] = [
                    {
                        "deleteContentRange": {
                            "range": {
                                "startIndex": 1,
                                "endIndex": last_end - 1,
                            }
                        }
                    }
                ]
                await _batch_update(svc, document_id, del_requests)
        start_index = 1
    else:
        # Create new document
        if folder_id:
            gdoc_metadata: dict[str, Any] = {
                "name": title,
                "mimeType": "application/vnd.google-apps.document",
                "parents": [folder_id],
            }
            boundary = secrets.token_hex(16)
            body_str = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(gdoc_metadata)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: text/plain\r\n\r\n"
                f"\r\n--{boundary}--"
            )
            upload_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true"
            response = await svc._make_raw_request(
                "POST",
                upload_url,
                content=body_str.encode("utf-8"),
                headers={"Content-Type": f"multipart/related; boundary={boundary}"},
                timeout=60.0,
            )
            result = response.json()
            document_id = result.get("id")
        else:
            create_resp = await svc._make_request(
                "POST",
                f"{DOCS_API_BASE}/documents",
                json_data={"title": title},
            )
            document_id = create_resp.get("documentId")
        start_index = 1

    if not document_id:
        raise RuntimeError("Failed to create or identify target document")

    # --- 4. Build and issue requests in table-bounded segments ---
    total_insert_requests = await _insert_blocks_in_segments(svc, document_id, blocks, start_index)

    # --- 5. Fetch webViewLink ---
    file_meta = await svc._make_request(
        "GET",
        f"{DRIVE_API_BASE}/files/{document_id}",
        params={"fields": "id,name,webViewLink,mimeType"},
    )

    return {
        "status": "published" if not arguments.get("document_id") else "updated",
        "document_id": document_id,
        "title": file_meta.get("name", title),
        "webViewLink": file_meta.get("webViewLink"),
        "mimeType": file_meta.get("mimeType"),
        "blocks_processed": len(blocks),
        "requests_issued": total_insert_requests,
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for markdown_file_to_doc handler."""
    return {
        "markdown_file_to_doc": lambda args: _markdown_file_to_doc(svc, args),
    }
