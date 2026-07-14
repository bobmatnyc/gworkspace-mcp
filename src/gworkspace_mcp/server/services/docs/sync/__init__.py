"""docs.sync — bidirectional Markdown <-> Google Doc sync engine.

Phase A (native serialization):
- ``blocks``: the shared block intermediate-representation (IR) plus the
  Markdown parser (``parse_markdown`` / ``_parse_inline_runs``). Relocated here
  verbatim from ``markdown_file.py`` so that both the Markdown encoder and the
  native Docs-JSON serializer target a single shared IR. ``markdown_file``
  re-imports these names for backward compatibility.
- ``serializer``: native Docs-JSON -> block IR -> GFM Markdown serializer and
  the Markdown -> block IR entry point (``markdown_to_blocks``).

Phase B (minimal in-place diff MD -> Doc):
- ``doc_builder``: ``_DocBuilder``, relocated verbatim from ``markdown_file.py``
  (re-imported there for backward compatibility) so both the create/rebuild
  path and the diff/patch path share one request-building implementation.
- ``differ``: two-level (block + inline) diff over the block IR.
- ``patch_planner``: translates a diff into a minimal, correctly-ordered
  ``batchUpdate`` request list plus structural table-replace ops.

Phase C (Doc -> Markdown write-back):
- ``writeback``: fetches a Doc (honoring readable-suggestion view modes) and
  serializes it back to GFM Markdown on disk and/or inline.

Phase D (drift/conflict snapshot + user-facing tool):
- ``snapshot``: Drive-``appProperties``-backed drift/conflict bookkeeping —
  detects whether the Doc and/or Markdown side changed since the last sync.
- ``orchestrator``: registers the ``sync_markdown_doc`` MCP tool, wiring
  direction (``md_to_doc``/``doc_to_md``/``auto``), mode
  (``direct``/``suggest``/``preview``), and ``on_conflict`` handling on top of
  Phases A-C plus ``snapshot``.

This package's ``TOOLS``/``get_handlers`` (from ``orchestrator``) are merged
into ``docs/__init__.py`` alongside the other Docs submodules, the same
aggregation pattern every other tool group in this server uses.
"""

from __future__ import annotations

from typing import Any

from gworkspace_mcp.server.services.docs.sync import (
    blocks,
    differ,
    doc_builder,
    orchestrator,
    patch_planner,
    serializer,
    snapshot,
    writeback,
)

TOOLS = orchestrator.TOOLS


def get_handlers(svc: Any) -> dict[str, Any]:
    """Return name->callable mapping for this package's MCP tool(s)."""
    return orchestrator.get_handlers(svc)


__all__ = [
    "blocks",
    "differ",
    "doc_builder",
    "orchestrator",
    "patch_planner",
    "serializer",
    "snapshot",
    "writeback",
    "TOOLS",
    "get_handlers",
]
