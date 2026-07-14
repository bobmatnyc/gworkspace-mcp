"""Doc -> Markdown write-back (RFC Phase C).

Reusable library plumbing for the ``direction=doc_to_md`` half of the sync
engine: fetch a Google Doc's native JSON, run it through the Phase A serializer
(``doc_json_to_blocks`` -> ``blocks_to_markdown``) to produce faithful GFM
Markdown, and write that Markdown out to disk and/or return it inline.

This module registers **no MCP tool**. Per the RFC (section 7 / phase table),
the user-facing ``sync_markdown_doc`` tool, ``direction=auto`` detection, and
the drift/conflict 3-way compare (sidecar + ``appProperties``) are later phases
(D/E). Phase C is the pure, mockable write-back function those phases call.

Readable suggestions (RFC section 5.1/5.3, GA): the ``documents.get`` call
carries a ``suggestionsViewMode`` derived from ``read_suggestions``:

- ``accepted`` (default) -> ``PREVIEW_SUGGESTIONS_ACCEPTED``: serialize the doc
  as if every pending suggestion were already accepted. This is the RFC's
  recommended default -- the "future state" of the doc -- and keeps
  suggestion-marker noise out of the synced Markdown. The API returns the
  accepted content inline (suggested insertions present as regular text,
  suggested deletions removed); the serializer simply ignores the residual
  ``suggestedInsertionIds``/``suggestedDeletionIds`` annotations.
- ``rejected`` -> ``PREVIEW_WITHOUT_SUGGESTIONS``: serialize the accepted
  baseline only (pending suggestions dropped).
- ``annotate`` -> ``SUGGESTIONS_INLINE``: the RFC scopes CriticMarkup-style
  inline annotation of pending suggestions as a stretch goal explicitly *not*
  part of the initial Doc->MD phase (it needs the serializer to track
  suggestion-id spans). Requesting it here raises ``NotImplementedError``
  rather than silently emitting the inline view, which would leak
  suggested-deletion text into the Markdown as if it were live content.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gworkspace_mcp.server.constants import DOCS_API_BASE
from gworkspace_mcp.server.services.docs.sync import serializer

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

# Field mask for the Doc->MD fetch. The serializer walks ``body.content``
# (paragraphs + tables, including any residual ``suggested*`` annotations, which
# live inside ``body``) and resolves ordered-vs-unordered lists via the
# top-level ``lists`` map; ``revisionId`` is captured for the Phase D snapshot.
_WRITEBACK_FIELDS = "documentId,title,body,lists,revisionId"

# read_suggestions -> Docs API suggestionsViewMode (RFC section 5.3).
_SUGGESTIONS_VIEW_MODE: dict[str, str] = {
    "accepted": "PREVIEW_SUGGESTIONS_ACCEPTED",
    "rejected": "PREVIEW_WITHOUT_SUGGESTIONS",
    "annotate": "SUGGESTIONS_INLINE",
}

DEFAULT_READ_SUGGESTIONS = "accepted"


def resolve_suggestions_view_mode(read_suggestions: str) -> str:
    """Map a ``read_suggestions`` value to a Docs ``suggestionsViewMode``.

    Raises ``ValueError`` for an unknown value and ``NotImplementedError`` for
    ``annotate`` (a deferred stretch goal -- see the module docstring).
    """
    if read_suggestions not in _SUGGESTIONS_VIEW_MODE:
        valid = ", ".join(sorted(_SUGGESTIONS_VIEW_MODE))
        raise ValueError(
            f"Unknown read_suggestions={read_suggestions!r}; expected one of: {valid}."
        )
    if read_suggestions == "annotate":
        raise NotImplementedError(
            "read_suggestions='annotate' (inline CriticMarkup annotation of pending "
            "suggestions) is a deferred stretch goal per the sync RFC and is not part of "
            "the Doc->Markdown write-back phase. Use 'accepted' (default) or 'rejected'."
        )
    return _SUGGESTIONS_VIEW_MODE[read_suggestions]


def _resolve_write_path(markdown_file_path: str) -> Path:
    """Resolve + guard a Markdown output path against traversal writes.

    Mirrors ``markdown_file._is_path_under``'s allow-list (cwd / home / system
    temp): an agent-supplied path must land under one of those roots so the
    write-back never clobbers arbitrary files (e.g. dotfiles, ``/etc``).
    """
    path = Path(markdown_file_path).resolve()
    allowed_roots = (
        Path.cwd().resolve(),
        Path.home().resolve(),
        Path(tempfile.gettempdir()).resolve(),
    )
    if not any(_is_under(path, root) for root in allowed_roots):
        raise ValueError(
            f"Path '{markdown_file_path}' is outside allowed directories "
            f"({', '.join(str(r) for r in allowed_roots)}). "
            "Only paths under the current working directory, your home directory, "
            "or the system temp directory are permitted."
        )
    return path


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def doc_json_to_markdown(document: dict[str, Any]) -> str:
    """Serialize an in-hand ``documents.get`` response JSON to GFM Markdown.

    Pure convenience wrapper over the Phase A pipeline
    (``doc_json_to_blocks`` -> ``blocks_to_markdown``) so callers that already
    hold the document JSON don't reach across two modules. No network.
    """
    return serializer.blocks_to_markdown(serializer.doc_json_to_blocks(document))


async def doc_to_markdown(
    svc: BaseService,
    document_id: str,
    *,
    read_suggestions: str = DEFAULT_READ_SUGGESTIONS,
    markdown_file_path: str | None = None,
    write_markdown_file: bool = True,
) -> dict[str, Any]:
    """Fetch a Doc and write it back out as faithful GFM Markdown (RFC Phase C).

    Fetches ``documents.get`` with the ``suggestionsViewMode`` derived from
    ``read_suggestions``, serializes the response to Markdown, optionally writes
    it to ``markdown_file_path``, and returns the Markdown plus the metadata a
    later orchestrator (Phase D) needs to record a snapshot (``revision_id``,
    the view mode used).

    Args:
        svc: Authenticated service exposing ``_make_request``.
        document_id: Target Google Doc id.
        read_suggestions: ``accepted`` (default) | ``rejected`` (``annotate`` is
            deferred -- see ``resolve_suggestions_view_mode``).
        markdown_file_path: Where to write the Markdown, if writing is enabled.
        write_markdown_file: When True and a path is given, write the file.

    Returns:
        A result dict (a subset of the RFC section 7 ``sync_markdown_doc`` shape,
        scoped to the Doc->MD direction) with ``markdown_content`` always set.
    """
    view_mode = resolve_suggestions_view_mode(read_suggestions)

    url = f"{DOCS_API_BASE}/documents/{document_id}"
    params = {"fields": _WRITEBACK_FIELDS, "suggestionsViewMode": view_mode}
    document = await svc._make_request("GET", url, params=params)

    markdown = doc_json_to_markdown(document)

    written_path: str | None = None
    if markdown_file_path and write_markdown_file:
        path = _resolve_write_path(markdown_file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
        written_path = str(path)
        logger.info(
            "Wrote %d chars of Markdown to %s (doc %s, view=%s)",
            len(markdown),
            written_path,
            document_id,
            view_mode,
        )

    return {
        "status": "written" if written_path else "read",
        "direction_applied": "doc_to_md",
        "document_id": document.get("documentId", document_id),
        "title": document.get("title"),
        "revision_id": document.get("revisionId"),
        "read_suggestions": read_suggestions,
        "suggestions_view_mode": view_mode,
        "markdown_content": markdown,
        "markdown_file_path": written_path,
    }
