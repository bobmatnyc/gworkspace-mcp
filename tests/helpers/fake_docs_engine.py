"""A tiny in-memory model of a Google Doc's text buffer, for testing that a
planned batchUpdate request list actually reconciles indices correctly —
without any live API call.

Only text-shape matters here (RFC section 9's "did this batch of index-based
ops actually reconcile correctly" question), so this engine tracks a single
1-indexed character buffer and applies ``insertText``/``deleteContentRange``
verbatim. Style-only requests (``updateTextStyle``, ``updateParagraphStyle``,
``createParagraphBullets``, ``updateTableCellStyle``, ...) are no-ops on the
buffer — they don't shift anything, matching the RFC's own reasoning for why
they can be interleaved freely.

Google Docs bodies are 1-indexed (index 0 doesn't exist), so the buffer is
padded with a single throwaway character at position 0.
"""

from __future__ import annotations

from typing import Any


class FakeDocsEngine:
    """Minimal text-buffer model for verifying index-based edit plans."""

    def __init__(self, initial_text: str = "") -> None:
        # index 0 is a dummy pad so buffer[i] lines up with Docs' 1-indexing.
        self._buf: list[str] = ["\x00", *initial_text]

    @property
    def text(self) -> str:
        """The buffer's content, excluding the index-0 pad."""
        return "".join(self._buf[1:])

    def end_index(self) -> int:
        """The position just past the last real character (mirrors
        ``document_end_index``: the whole buffer's length including the pad)."""
        return len(self._buf)

    def apply(self, requests: list[dict[str, Any]]) -> None:
        """Apply requests in the given order — callers must supply them
        already ordered descending by index (as ``patch_planner`` guarantees)."""
        for req in requests:
            self.apply_one(req)

    def apply_one(self, req: dict[str, Any]) -> None:
        if "insertText" in req:
            spec = req["insertText"]
            index = spec["location"]["index"]
            text = spec["text"]
            self._buf[index:index] = list(text)
        elif "deleteContentRange" in req:
            rng = req["deleteContentRange"]["range"]
            start, end = rng["startIndex"], rng["endIndex"]
            del self._buf[start:end]
        # Style-only requests: no-op on the text buffer by design.
