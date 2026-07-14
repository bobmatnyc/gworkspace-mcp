"""Unit tests for docs.sync.patch_planner (Phase B, RFC section 4).

Pure planning tests (no Docs API) plus index-shift correctness verified by
replaying a planned request list against ``FakeDocsEngine`` (an in-memory text
buffer) and asserting the final text matches the target Markdown's blocks.
"""

from __future__ import annotations

from typing import Any

from gworkspace_mcp.server.services.docs.sync import differ, patch_planner
from gworkspace_mcp.server.services.docs.sync.blocks import parse_markdown
from tests.helpers.fake_docs_engine import FakeDocsEngine


def _lay_out(blocks: list[dict[str, Any]]) -> tuple[str, list[tuple[int, int]]]:
    """Render blocks into a contiguous 1-indexed text buffer + parallel
    (start, end) ranges, one per block — a stand-in for what
    ``serializer.doc_json_to_blocks_with_ranges`` returns for a live document,
    built purely from the block IR so these tests need no Docs-JSON fixture."""
    text = ""
    ranges: list[tuple[int, int]] = []
    idx = 1
    for block in blocks:
        chunk = differ.plain_text(block) + "\n"
        ranges.append((idx, idx + len(chunk)))
        text += chunk
        idx += len(chunk)
    return text, ranges


def _plan_for(old_md: str, new_md: str) -> tuple[patch_planner.PatchPlan, FakeDocsEngine, str]:
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)
    doc_end = len(old_text) + 1
    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end)
    engine = FakeDocsEngine(old_text)
    return plan, engine, differ.plain_text  # plain_text unused by caller directly


# ---------------------------------------------------------------------------
# Idempotency — the single most important correctness property
# ---------------------------------------------------------------------------


def test_identical_markdown_produces_zero_requests() -> None:
    md = "# Title\n\nSome paragraph text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    blocks = parse_markdown(md)
    ops = differ.diff_blocks(blocks, blocks)
    _text, ranges = _lay_out(blocks)
    plan = patch_planner.plan_patch(ops, ranges, doc_end_index=len(_text) + 1)
    assert plan.requests == []
    assert plan.table_ops == []


def test_idempotent_across_headings_lists_and_code() -> None:
    md = "# Title\n\n- one\n- two\n\n1. first\n2. second\n\n```\ncode here\n```\n"
    blocks = parse_markdown(md)
    ops = differ.diff_blocks(blocks, blocks)
    _text, ranges = _lay_out(blocks)
    plan = patch_planner.plan_patch(ops, ranges, doc_end_index=len(_text) + 1)
    assert plan.requests == []
    assert plan.table_ops == []


# ---------------------------------------------------------------------------
# Minimality — a single changed word/paragraph must not replace the world
# ---------------------------------------------------------------------------


def test_single_word_change_yields_minimal_ops_only() -> None:
    old_md = "# Title\n\nUnrelated first.\n\nHello world.\n\nUnrelated last.\n"
    new_md = "# Title\n\nUnrelated first.\n\nHello there world.\n\nUnrelated last.\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)
    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    assert plan.table_ops == []
    # Exactly one small insertText — no deleteContentRange over the whole
    # document, no touching of the unrelated surrounding paragraphs.
    assert len(plan.requests) == 1
    (req,) = plan.requests
    assert "insertText" in req
    assert req["insertText"]["text"].strip() == "there"

    # The touched index must fall inside the "Hello world." block's range, not
    # anywhere near the unrelated blocks.  Blocks: heading, blank,
    # "Unrelated first.", blank, "Hello world.", blank, "Unrelated last."
    hello_block_range = old_ranges[4]
    touched_index = req["insertText"]["location"]["index"]
    assert hello_block_range[0] <= touched_index <= hello_block_range[1]


def test_minimal_edit_replays_to_correct_final_text() -> None:
    old_md = "Alpha.\n\nHello world.\n\nOmega.\n"
    new_md = "Alpha.\n\nHello there world.\n\nOmega.\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)
    new_text, _new_ranges = _lay_out(new_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    engine = FakeDocsEngine(old_text)
    engine.apply(plan.requests)
    assert engine.text == new_text


# ---------------------------------------------------------------------------
# Index-shift correctness — multiple edits in one batch
# ---------------------------------------------------------------------------


def test_multiple_scattered_edits_apply_correctly_in_one_batch() -> None:
    """Three independent single-word edits at different document offsets —
    the planner must order them so none corrupts another's indices."""
    old_md = "First alpha line.\n\nSecond beta line.\n\nThird gamma line.\n"
    new_md = "First ALPHA line.\n\nSecond BETA line.\n\nThird GAMMA line.\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)
    new_text, _ = _lay_out(new_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)
    assert len(plan.requests) >= 3  # at least one edit per changed paragraph

    engine = FakeDocsEngine(old_text)
    engine.apply(plan.requests)
    assert engine.text == new_text


def test_insertions_and_deletions_mixed_apply_correctly() -> None:
    old_md = "Keep one.\n\nRemove this one.\n\nKeep two.\n"
    new_md = "Keep one.\n\nKeep two.\n\nBrand new paragraph.\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)
    new_text, _ = _lay_out(new_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    engine = FakeDocsEngine(old_text)
    engine.apply(plan.requests)
    assert engine.text == new_text


def test_requests_are_ordered_descending_by_effective_index() -> None:
    """Delete/insert requests must be emitted highest-index-first so earlier
    (in array order) edits never invalidate indices later edits still need."""
    old_md = "One.\n\nTwo.\n\nThree.\n\nFour.\n"
    new_md = "One!\n\nTwo!\n\nThree!\n\nFour!\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    def _request_index(req: dict[str, Any]) -> int:
        if "insertText" in req:
            return int(req["insertText"]["location"]["index"])
        return int(req["deleteContentRange"]["range"]["startIndex"])

    indices = [_request_index(r) for r in plan.requests]
    assert indices == sorted(indices, reverse=True)


# ---------------------------------------------------------------------------
# Block-type changes
# ---------------------------------------------------------------------------


def test_paragraph_to_heading_change_replays_correctly() -> None:
    old_md = "Just a paragraph.\n"
    new_md = "# Just a paragraph.\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)
    new_text, _ = _lay_out(new_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    engine = FakeDocsEngine(old_text)
    engine.apply(plan.requests)
    assert engine.text == new_text
    # A whole-block replace: delete + re-insert, not a scoped inline edit.
    assert any("deleteContentRange" in r for r in plan.requests)
    assert any("insertText" in r for r in plan.requests)


def test_table_cell_change_is_planned_as_table_op_not_inline() -> None:
    old_md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    new_md = "| A | B |\n|---|---|\n| 1 | 9 |\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    assert plan.requests == []  # nothing routed to the flat Round-1 path
    assert len(plan.table_ops) == 1
    table_op = plan.table_ops[0]
    assert table_op.old_range is not None
    assert table_op.new_blocks[0]["type"] == "table"
    assert table_op.new_blocks[0]["rows"] == [["1", "9"]]


def test_unrelated_table_is_untouched_when_only_text_changes() -> None:
    """A table that hasn't changed must not appear in table_ops at all —
    proof that unrelated content is preserved by construction."""
    old_md = "Intro.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    new_md = "Intro changed.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    old_blocks = parse_markdown(old_md)
    new_blocks = parse_markdown(new_md)
    old_text, old_ranges = _lay_out(old_blocks)

    ops = differ.diff_blocks(old_blocks, new_blocks)
    plan = patch_planner.plan_patch(ops, old_ranges, doc_end_index=len(old_text) + 1)

    assert plan.table_ops == []


# ---------------------------------------------------------------------------
# writeControl / optimistic concurrency
# ---------------------------------------------------------------------------


def test_write_control_kwargs_empty_without_revision_id() -> None:
    plan = patch_planner.PatchPlan()
    assert plan.write_control_kwargs() == {}


def test_write_control_kwargs_present_with_revision_id() -> None:
    plan = patch_planner.PatchPlan(required_revision_id="abc123")
    assert plan.write_control_kwargs() == {"writeControl": {"requiredRevisionId": "abc123"}}
