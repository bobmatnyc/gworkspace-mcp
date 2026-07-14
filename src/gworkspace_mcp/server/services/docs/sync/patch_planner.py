"""Translate a block diff (``sync.differ``) into ordered Docs batchUpdate requests.

Pure, testable planning only — no network calls. Two kinds of output:

- ``requests``: a flat, minimal, correctly-ordered list of non-table
  ``batchUpdate`` request dicts (insertText/deleteContentRange/updateTextStyle/
  updateParagraphStyle/createParagraphBullets), ready to send in one
  ``batchUpdate`` call.
- ``table_ops``: structural table replacements that need the existing
  re-fetch-based segment pipeline (``add_table`` / ``_fill_tables_and_style``
  in ``markdown_file.py``) rather than a flat request list, because Docs only
  reveals real cell indices after the structural insert commits. Per RFC
  section 4, Phase B ships whole-table-replace as the only table diff
  strategy; cell-level diffing is deferred.

Index-shifting correctness (RFC section 4): each non-table diff op becomes one
self-contained ``LogicalEdit`` anchored at a single *original*-document index.
Docs applies ``batchUpdate`` requests strictly in array order against the
state left by the previous request, so as long as edits are emitted in
descending order of their anchor, a higher-anchored edit's own insert/delete
traffic never touches (and therefore never invalidates) the indices any
lower-anchored edit still depends on — the same technique
``_fill_tables_and_style`` already uses for cell fills, generalized to whole
block-level edits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gworkspace_mcp.server.services.docs.sync.differ import BlockDiffOp
from gworkspace_mcp.server.services.docs.sync.doc_builder import _DocBuilder


@dataclass
class TableReplaceOp:
    """A structural table change requiring the re-fetch-based segment pipeline.

    ``old_range`` is the old table's ``(start_index, end_index)`` in the live
    document, or ``None`` for a pure insertion (no old table to remove).
    ``new_blocks`` are the blocks to insert at ``anchor`` after the old range
    (if any) is deleted — may include a table block plus any interleaved
    non-table blocks from the same diff-op slice, inserted via the existing
    ``_DocBuilder``/``add_table`` machinery exactly as the create-document path
    already does.
    """

    anchor: int
    old_range: tuple[int, int] | None
    new_blocks: list[dict[str, Any]]


@dataclass
class PatchPlan:
    """Result of planning a diff: what to send, and a change summary."""

    requests: list[dict[str, Any]] = field(default_factory=list)
    table_ops: list[TableReplaceOp] = field(default_factory=list)
    matched: int = 0
    inserted: int = 0
    deleted: int = 0
    modified: int = 0
    # ``writeControl`` body (RFC section 10 risk #3: optimistic concurrency).
    # Sibling of "requests" in the batchUpdate POST body, not a request itself —
    # callers do ``json_data={"requests": plan.requests, **plan.write_control_kwargs()}``.
    required_revision_id: str | None = None

    def write_control_kwargs(self) -> dict[str, Any]:
        """``{"writeControl": {...}}`` if a revision id was supplied, else ``{}``.

        Merge into the ``batchUpdate`` POST body's top level so the API rejects
        a stale batch with a 400 (someone edited the doc since we diffed it)
        instead of silently corrupting indices.
        """
        if not self.required_revision_id:
            return {}
        return {"writeControl": {"requiredRevisionId": self.required_revision_id}}


@dataclass
class _LogicalEdit:
    """One self-contained, internally-ordered edit anchored at one original
    document index.  See module docstring for why sorting by ``anchor``
    descending and concatenating each edit's already-correct internal request
    order is sufficient for global correctness."""

    anchor: int
    requests: list[dict[str, Any]]


def _has_table(blocks: list[dict[str, Any]]) -> bool:
    return any(b["type"] == "table" for b in blocks)


def plan_patch(
    diff_ops: list[BlockDiffOp],
    old_ranges: list[tuple[int, int]],
    doc_end_index: int,
    required_revision_id: str | None = None,
) -> PatchPlan:
    """Plan a minimal, ordered patch from a block diff.

    ``old_ranges`` must be parallel to the ``old_blocks`` list the diff was
    computed from (index i's ``(start_index, end_index)`` in the live
    document) — e.g. from ``serializer.doc_json_to_blocks_with_ranges``.
    ``doc_end_index`` is the safe append-at-end position (e.g. from
    ``serializer.document_end_index``), used when a pure insertion lands after
    the last existing block.
    """
    plan = PatchPlan(required_revision_id=required_revision_id)
    edits: list[_LogicalEdit] = []

    for op in diff_ops:
        if op.tag == "equal":
            plan.matched += len(op.old_blocks)
            continue

        if _has_table(op.old_blocks) or _has_table(op.new_blocks):
            plan.table_ops.append(_plan_table_op(op, old_ranges, doc_end_index))
            _tally(plan, op)
            continue

        if op.tag == "delete":
            edits.append(_plan_delete(op, old_ranges))
        elif op.tag == "insert":
            edits.append(_plan_insert(op, old_ranges, doc_end_index))
        elif op.inline_edit is not None:
            edits.append(_plan_scoped_replace(op, old_ranges))
        else:
            edits.append(_plan_whole_replace(op, old_ranges))

        _tally(plan, op)

    # Highest original-document anchor first — see module docstring.
    edits.sort(key=lambda e: e.anchor, reverse=True)
    for edit in edits:
        plan.requests.extend(edit.requests)

    return plan


def _tally(plan: PatchPlan, op: BlockDiffOp) -> None:
    if op.tag == "insert":
        plan.inserted += len(op.new_blocks)
    elif op.tag == "delete":
        plan.deleted += len(op.old_blocks)
    elif op.tag == "replace":
        plan.modified += max(len(op.old_blocks), len(op.new_blocks))


# =============================================================================
# Non-table logical edits
# =============================================================================


def _plan_delete(op: BlockDiffOp, old_ranges: list[tuple[int, int]]) -> _LogicalEdit:
    start = old_ranges[op.old_start][0]
    end = old_ranges[op.old_end - 1][1]
    return _LogicalEdit(anchor=start, requests=[_delete_range_request(start, end)])


def _plan_insert(
    op: BlockDiffOp, old_ranges: list[tuple[int, int]], doc_end_index: int
) -> _LogicalEdit:
    anchor = old_ranges[op.old_start][0] if op.old_start < len(old_ranges) else doc_end_index
    requests = _render_blocks_insert(op.new_blocks, start_index=anchor)
    return _LogicalEdit(anchor=anchor, requests=requests)


def _plan_whole_replace(op: BlockDiffOp, old_ranges: list[tuple[int, int]]) -> _LogicalEdit:
    """Delete the whole old block range, then insert the new blocks in its
    place — used whenever a 1:1 scoped edit doesn't apply (different types,
    multi-block ranges, or below the inline-similarity threshold)."""
    start = old_ranges[op.old_start][0]
    end = old_ranges[op.old_end - 1][1]
    requests = [_delete_range_request(start, end)]
    requests.extend(_render_blocks_insert(op.new_blocks, start_index=start))
    return _LogicalEdit(anchor=start, requests=requests)


def _plan_scoped_replace(op: BlockDiffOp, old_ranges: list[tuple[int, int]]) -> _LogicalEdit:
    """A 1:1 same-type replace with a minimal ``InlineEdit`` — delete/insert
    only the changed character span, then reapply full-paragraph styling from
    the new block's runs (cheap and idempotent, per RFC section 4)."""
    edit = op.inline_edit
    assert edit is not None  # only called when the differ found one
    new_block = op.new_blocks[0]
    block_start = old_ranges[op.old_start][0]

    requests: list[dict[str, Any]] = []
    del_start = block_start + edit.old_start
    del_end = block_start + edit.old_end
    if del_end > del_start:
        requests.append(_delete_range_request(del_start, del_end))
    if edit.new_text:
        requests.append(_insert_text_request(del_start, edit.new_text))

    # Reapply styling over the whole paragraph using its NEW (post-edit) runs.
    # style_only=True reuses _DocBuilder's exact run-walking/index logic to
    # compute style requests without re-inserting text that's already correct.
    requests.extend(_style_requests_for_block(new_block, block_start))

    return _LogicalEdit(anchor=block_start, requests=requests)


def _render_blocks_insert(blocks: list[dict[str, Any]], start_index: int) -> list[dict[str, Any]]:
    """Build ascending insertText/style requests for a run of NEW (non-table)
    blocks via ``_DocBuilder``, exactly as the create-document path does — the
    only difference is the builder starts at ``start_index`` (an insertion
    point inside an existing document) instead of 1."""
    builder = _DocBuilder(start_index=start_index)
    for block in blocks:
        _add_block(builder, block)
    requests, _deferred = builder.build()
    return requests


def _style_requests_for_block(block: dict[str, Any], start_index: int) -> list[dict[str, Any]]:
    """Style-only pass over a single block's current runs, anchored at
    ``start_index`` — reuses ``_DocBuilder`` in ``style_only`` mode so the
    request shapes are identical to the create-document path."""
    builder = _DocBuilder(start_index=start_index)
    _add_block(builder, block, style_only=True)
    requests, _deferred = builder.build()
    return requests


def _add_block(builder: _DocBuilder, block: dict[str, Any], style_only: bool = False) -> None:
    btype = block["type"]
    if btype == "heading":
        builder.add_heading(block["level"], block["runs"], style_only=style_only)
    elif btype == "paragraph":
        builder.add_paragraph(block["runs"], style_only=style_only)
    elif btype == "code":
        if style_only:
            return  # code blocks aren't eligible for scoped inline edits
        builder.add_code_block(block["text"])
    elif btype == "bullet":
        builder.add_bullet(block["depth"], block["runs"], style_only=style_only)
    elif btype == "ordered":
        builder.add_ordered(block["runs"], block.get("depth", 0), style_only=style_only)
    elif btype == "blank":
        # A blank block is just an empty paragraph — add_paragraph([]) inserts
        # (or, in style_only mode, merely advances past) its trailing "\n".
        builder.add_paragraph([], style_only=style_only)
    elif btype == "rule":
        builder.add_rule()
    # "table" is never routed here — table blocks are handled via TableReplaceOp.


# =============================================================================
# Table structural changes (whole-table replace — RFC section 4)
# =============================================================================


def _plan_table_op(
    op: BlockDiffOp, old_ranges: list[tuple[int, int]], doc_end_index: int
) -> TableReplaceOp:
    old_range: tuple[int, int] | None = None
    if op.old_blocks:
        old_range = (old_ranges[op.old_start][0], old_ranges[op.old_end - 1][1])
        anchor = old_range[0]
    elif op.old_start < len(old_ranges):
        anchor = old_ranges[op.old_start][0]
    else:
        anchor = doc_end_index
    return TableReplaceOp(anchor=anchor, old_range=old_range, new_blocks=op.new_blocks)


# =============================================================================
# Request builders
# =============================================================================


def _delete_range_request(start: int, end: int) -> dict[str, Any]:
    return {"deleteContentRange": {"range": {"startIndex": start, "endIndex": end}}}


def _insert_text_request(start: int, text: str) -> dict[str, Any]:
    return {"insertText": {"location": {"index": start}, "text": text}}
