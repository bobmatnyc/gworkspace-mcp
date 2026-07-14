"""Two-level block/inline differ (RFC section 4).

Pure functions over the shared block IR (``sync.blocks``) — no Docs API, no
document positions. This module answers "what changed" as a structured,
testable op list; ``sync.patch_planner`` turns that answer into actual
``batchUpdate`` requests against real document indices.

Level 1 — block level: fingerprint each block as ``(type, normalized_text)``
and run ``difflib.SequenceMatcher.get_opcodes()`` over ``old_blocks`` (serialized
from the live Doc) vs. ``new_blocks`` (parsed from target Markdown).

Level 2 — inline level: when a ``replace`` op pairs exactly one old and one new
block of the same type (and, for headings, the same level) and their plain-text
similarity clears ``INLINE_SIMILARITY_THRESHOLD``, compute the minimal changed
character span via a second ``SequenceMatcher`` pass instead of treating the
whole block as delete+insert.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal

OpTag = Literal["equal", "insert", "delete", "replace"]

# Below this plain-text similarity ratio, a 1:1 replace is cheaper (and just as
# correct) to treat as whole-block delete+insert rather than a scoped edit.
INLINE_SIMILARITY_THRESHOLD = 0.5

# Block types eligible for inline (sub-block) diffing.  Tables are excluded —
# per RFC section 4, table changes are always whole-table replace in Phase B.
# Code blocks are excluded — a code block is a single opaque text blob most
# naturally replaced wholesale.
_INLINE_DIFFABLE_TYPES = frozenset({"paragraph", "heading", "bullet", "ordered"})


@dataclass(frozen=True)
class InlineEdit:
    """The minimal changed character span within a single block's plain text.

    ``old_start``/``old_end`` index into the *old* block's plain text (the
    substring to remove); ``new_text`` is the replacement to insert at that
    position. Everything outside ``[old_start, old_end)`` is unchanged and
    must not be touched.
    """

    old_start: int
    old_end: int
    new_text: str


@dataclass(frozen=True)
class BlockDiffOp:
    """One ``difflib`` opcode range translated to block-list slices.

    ``old_start``/``old_end`` and ``new_start``/``new_end`` are indices into
    the caller's ``old_blocks``/``new_blocks`` lists (Python slice semantics:
    ``old_blocks[old_start:old_end]``). ``inline_edit`` is set only for a 1:1
    ``replace`` of matching-type blocks whose similarity clears the threshold —
    when set, the planner should emit a scoped edit instead of a whole-block
    replace.
    """

    tag: OpTag
    old_start: int
    old_end: int
    new_start: int
    new_end: int
    old_blocks: list[dict[str, Any]]
    new_blocks: list[dict[str, Any]]
    inline_edit: InlineEdit | None = None


def plain_text(block: dict[str, Any]) -> str:
    """Render a block's plain text for fingerprinting/similarity comparisons.

    Strips inline styling (bold/italic/code/link markers), matching the RFC's
    "normalized = plain text with inline styling markers stripped".
    """
    btype = block["type"]
    if btype in ("heading", "paragraph", "bullet", "ordered"):
        return "".join(r["text"] for r in block.get("runs", []))
    if btype == "code":
        return block.get("text", "")
    if btype == "table":
        headers = block.get("headers", []) or []
        rows = block.get("rows", []) or []
        return "\t".join(headers) + "\n" + "\n".join("\t".join(row) for row in rows)
    return ""  # rule, blank — structural only, no text to compare


def _fingerprint(block: dict[str, Any]) -> tuple[str, str]:
    """``(type, normalized_text)`` — the block-level diff unit (RFC section 4).

    Heading level is folded into the type component so a level change (e.g.
    H1 -> H2 of otherwise-identical text) is a genuine block-level change, not
    an "equal" match.
    """
    btype = block["type"]
    if btype == "heading":
        btype = f"heading:{block.get('level')}"
    return (btype, plain_text(block))


def diff_blocks(
    old_blocks: list[dict[str, Any]], new_blocks: list[dict[str, Any]]
) -> list[BlockDiffOp]:
    """Diff two block lists, returning ordered ``BlockDiffOp`` s covering both
    lists in full (mirrors ``SequenceMatcher.get_opcodes()``'s contract: the
    ranges are contiguous and exhaustive)."""
    old_fp = [_fingerprint(b) for b in old_blocks]
    new_fp = [_fingerprint(b) for b in new_blocks]
    matcher = SequenceMatcher(a=old_fp, b=new_fp, autojunk=False)

    ops: list[BlockDiffOp] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_slice = old_blocks[i1:i2]
        new_slice = new_blocks[j1:j2]
        inline_edit = None
        if tag == "replace" and len(old_slice) == 1 and len(new_slice) == 1:
            inline_edit = _try_inline_edit(old_slice[0], new_slice[0])
        ops.append(
            BlockDiffOp(
                tag=tag,  # type: ignore[arg-type]  # difflib's tag literals match OpTag
                old_start=i1,
                old_end=i2,
                new_start=j1,
                new_end=j2,
                old_blocks=old_slice,
                new_blocks=new_slice,
                inline_edit=inline_edit,
            )
        )
    return ops


def _try_inline_edit(old_block: dict[str, Any], new_block: dict[str, Any]) -> InlineEdit | None:
    """Attempt a scoped inline edit for a 1:1 same-type block replace.

    Returns None when the pair isn't eligible (different type/heading level,
    non-diffable type) or falls below the similarity threshold — the caller
    then falls back to whole-block delete+insert.
    """
    if old_block["type"] != new_block["type"]:
        return None
    if old_block["type"] not in _INLINE_DIFFABLE_TYPES:
        return None
    if old_block["type"] == "heading" and old_block.get("level") != new_block.get("level"):
        return None

    old_text = plain_text(old_block)
    new_text = plain_text(new_block)
    if old_text == new_text:
        return None  # text identical; any difference is style-only (see planner)

    ratio = SequenceMatcher(a=old_text, b=new_text, autojunk=False).ratio()
    if ratio <= INLINE_SIMILARITY_THRESHOLD:
        return None

    return diff_inline_text(old_text, new_text)


def diff_inline_text(old_text: str, new_text: str) -> InlineEdit:
    """Compute the minimal contiguous changed span between two plain strings.

    Merges every non-``equal`` opcode from a character-level ``SequenceMatcher``
    into a single ``[old_start, old_end)`` span (Docs edits are contiguous:
    one ``deleteContentRange`` + one ``insertText``), trimming any common
    prefix/suffix outside that span.
    """
    if old_text == new_text:
        return InlineEdit(old_start=len(old_text), old_end=len(old_text), new_text="")

    matcher = SequenceMatcher(a=old_text, b=new_text, autojunk=False)
    changed = [oc for oc in matcher.get_opcodes() if oc[0] != "equal"]
    if not changed:
        return InlineEdit(old_start=len(old_text), old_end=len(old_text), new_text="")

    first, last = changed[0], changed[-1]
    old_start, old_end = first[1], last[2]
    new_start, new_end = first[3], last[4]
    return InlineEdit(old_start=old_start, old_end=old_end, new_text=new_text[new_start:new_end])
