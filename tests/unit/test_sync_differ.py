"""Unit tests for docs.sync.differ (Phase B, RFC section 4).

Pure block-list tests — no Docs API, no positions. Covers block-level
equal/insert/delete/replace opcodes, the inline-similarity gate, block-type
changes, and heading-level changes.
"""

from __future__ import annotations

from gworkspace_mcp.server.services.docs.sync import differ
from gworkspace_mcp.server.services.docs.sync.blocks import parse_markdown

# ---------------------------------------------------------------------------
# Block-level diff
# ---------------------------------------------------------------------------


def test_identical_blocks_are_all_equal() -> None:
    md = "# Title\n\nSome text.\n"
    blocks = parse_markdown(md)
    ops = differ.diff_blocks(blocks, blocks)
    assert all(op.tag == "equal" for op in ops)
    assert sum(op.old_end - op.old_start for op in ops) == len(blocks)


def test_pure_insertion_detected() -> None:
    old = parse_markdown("# Title\n\nFirst.\n")
    new = parse_markdown("# Title\n\nFirst.\n\nSecond.\n")
    ops = differ.diff_blocks(old, new)
    tags = [op.tag for op in ops]
    assert "insert" in tags
    insert_op = next(op for op in ops if op.tag == "insert")
    assert insert_op.old_start == insert_op.old_end  # no old blocks consumed
    assert len(insert_op.new_blocks) >= 1


def test_pure_deletion_detected() -> None:
    old = parse_markdown("# Title\n\nFirst.\n\nSecond.\n")
    new = parse_markdown("# Title\n\nFirst.\n")
    ops = differ.diff_blocks(old, new)
    tags = [op.tag for op in ops]
    assert "delete" in tags
    delete_op = next(op for op in ops if op.tag == "delete")
    assert delete_op.new_start == delete_op.new_end  # no new blocks produced


def test_unrelated_blocks_bracket_the_change() -> None:
    """A change in the middle leaves the surrounding blocks as 'equal'."""
    old = parse_markdown("# Title\n\nUnchanged before.\n\nOld middle.\n\nUnchanged after.\n")
    new = parse_markdown("# Title\n\nUnchanged before.\n\nNew middle.\n\nUnchanged after.\n")
    ops = differ.diff_blocks(old, new)
    equal_ops = [op for op in ops if op.tag == "equal"]
    assert len(equal_ops) >= 2


# ---------------------------------------------------------------------------
# Inline (scoped) diff within a 1:1 replace
# ---------------------------------------------------------------------------


def test_single_word_change_yields_inline_edit_not_whole_block() -> None:
    old = parse_markdown("Hello world.\n")
    new = parse_markdown("Hello there world.\n")
    ops = differ.diff_blocks(old, new)
    replace_op = next(op for op in ops if op.tag == "replace")
    assert replace_op.inline_edit is not None
    edit = replace_op.inline_edit
    assert edit.new_text.strip() == "there"
    # The edit must be a SMALL span, not the whole paragraph text.
    assert edit.old_end - edit.old_start < len(differ.plain_text(old[0]))


def test_completely_different_text_falls_back_to_whole_block() -> None:
    old = parse_markdown("The quick brown fox jumps.\n")
    new = parse_markdown("Zzyzx unrelated content here now.\n")
    ops = differ.diff_blocks(old, new)
    replace_op = next(op for op in ops if op.tag == "replace")
    assert replace_op.inline_edit is None


def test_heading_level_change_is_not_inline_diffable() -> None:
    old = parse_markdown("# Title\n")
    new = parse_markdown("## Title\n")
    ops = differ.diff_blocks(old, new)
    replace_op = next(op for op in ops if op.tag == "replace")
    # Same text, different level -> not eligible for a scoped inline edit.
    assert replace_op.inline_edit is None
    assert replace_op.old_blocks[0]["level"] == 1
    assert replace_op.new_blocks[0]["level"] == 2


def test_paragraph_to_heading_type_change_is_not_inline_diffable() -> None:
    old = parse_markdown("Just a paragraph.\n")
    new = parse_markdown("# Just a paragraph.\n")
    ops = differ.diff_blocks(old, new)
    replace_op = next(op for op in ops if op.tag == "replace")
    assert replace_op.inline_edit is None


def test_style_only_change_is_invisible_at_block_level() -> None:
    """Block fingerprints are (type, normalized_text); a pure styling change
    (text unchanged, bold added) is indistinguishable from "equal" at the
    block-diff level — the same design the RFC uses for tables ("unchanged
    purely on text equality"). This is an accepted, documented limitation:
    styling-only edits are not synced by the block differ in Phase B."""
    old = parse_markdown("plain text\n")
    new = parse_markdown("**plain text**\n")
    ops = differ.diff_blocks(old, new)
    assert all(op.tag == "equal" for op in ops)


# ---------------------------------------------------------------------------
# Table blocks: whole-block treatment (never inline-diffed)
# ---------------------------------------------------------------------------


def test_table_cell_change_is_whole_block_replace() -> None:
    old = parse_markdown("| A | B |\n|---|---|\n| 1 | 2 |\n")
    new = parse_markdown("| A | B |\n|---|---|\n| 1 | 9 |\n")
    ops = differ.diff_blocks(old, new)
    replace_op = next(op for op in ops if op.tag == "replace")
    assert replace_op.old_blocks[0]["type"] == "table"
    assert replace_op.inline_edit is None


def test_unchanged_table_is_equal() -> None:
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    blocks = parse_markdown(md)
    ops = differ.diff_blocks(blocks, blocks)
    assert all(op.tag == "equal" for op in ops)


# ---------------------------------------------------------------------------
# diff_inline_text — the character-level primitive
# ---------------------------------------------------------------------------


def test_diff_inline_text_identical_is_empty_edit() -> None:
    edit = differ.diff_inline_text("same", "same")
    assert edit.new_text == ""
    assert edit.old_start == edit.old_end


def test_diff_inline_text_pure_append() -> None:
    edit = differ.diff_inline_text("Hello", "Hello world")
    assert edit.new_text == " world"
    assert edit.old_start == edit.old_end == len("Hello")


def test_diff_inline_text_pure_prepend() -> None:
    edit = differ.diff_inline_text("world", "Hello world")
    assert edit.new_text == "Hello "
    assert edit.old_start == edit.old_end == 0


def test_diff_inline_text_middle_replacement_trims_common_affixes() -> None:
    edit = differ.diff_inline_text("aaXbb", "aaYYbb")
    assert edit.old_start == 2
    assert edit.old_end == 3
    assert edit.new_text == "YY"
