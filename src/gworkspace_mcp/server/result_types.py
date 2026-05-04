"""Helpers for building MCP tool result content blocks.

Why: Centralizes construction of MCP `TextContent`/`ImageContent` results so
tools can return either JSON (default) or pre-built content blocks (e.g.
binary images) without repeating boilerplate at every call site.
What: Provides `text_result()` for the standard JSON-text path and
`image_result()` for binary image returns with an optional caption.
Test: See `tests/unit/test_result_types.py` — verifies content composition
for both helpers and the pass-through behaviour in `handle_call_tool`.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.types import ImageContent, TextContent


def image_result(
    base64_data: str,
    mime_type: str,
    caption: str | None = None,
) -> list[TextContent | ImageContent]:
    """Build an MCP tool result containing an image (and optional caption).

    Why: MCP tools that return rendered images (e.g. Mermaid diagrams) need
    to emit binary data alongside descriptive text in a single response.
    What: Returns a list with an optional leading `TextContent` caption
    followed by an `ImageContent` carrying base64-encoded bytes.
    Test: Assert with caption returns 2 items (text+image), without caption
    returns 1 item (image only); see test_result_types.py.
    """
    content: list[TextContent | ImageContent] = []
    if caption:
        content.append(TextContent(type="text", text=caption))
    content.append(ImageContent(type="image", data=base64_data, mimeType=mime_type))
    return content


def text_result(data: Any, indent: int = 2) -> list[TextContent | ImageContent]:
    """Build a standard JSON text result (current default behaviour).

    Why: Most tools return structured dicts; centralizing the JSON-encoding
    keeps formatting consistent and makes the dispatch loop in `server.py`
    trivially simple. The return type matches `image_result()` so both
    helpers can flow through the same MCP `call_tool` return signature
    (`list[TextContent | ImageContent]`) without invariance issues.
    What: Returns a single-element list containing a `TextContent` whose
    text is `json.dumps(data, indent=indent)`.
    Test: Assert returned list has length 1 and `json.loads(result[0].text)`
    round-trips the original input.
    """
    content: list[TextContent | ImageContent] = [
        TextContent(type="text", text=json.dumps(data, indent=indent))
    ]
    return content
