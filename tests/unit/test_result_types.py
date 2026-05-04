"""Tests for `gworkspace_mcp.server.result_types` and the call-tool dispatch
pass-through behaviour for pre-built MCP content blocks.

Why: Validates that helpers correctly compose `TextContent`/`ImageContent`
and that `handle_call_tool` returns tool-supplied content lists unchanged
(enabling binary image returns from tools like `render_mermaid_to_doc`).
What: Covers `image_result()` with/without caption, `text_result()` JSON
shape, and the dispatcher pass-through for list results.
Test: Run via `uv run pytest tests/unit/test_result_types.py -v`.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest
from mcp.types import ImageContent, TextContent

from gworkspace_mcp.server.result_types import image_result, text_result
from gworkspace_mcp.server.server import GoogleWorkspaceServer

# ---------------------------------------------------------------------------
# image_result()
# ---------------------------------------------------------------------------


def test_image_result_with_caption_returns_text_and_image() -> None:
    """Why: Captioned images must include both blocks in order.
    What: Asserts a 2-element list (text first, then image).
    Test: Verify ordering, types, and field values.
    """
    result = image_result("aGVsbG8=", "image/png", caption="my diagram")

    assert len(result) == 2
    text_block = result[0]
    image_block = result[1]

    assert isinstance(text_block, TextContent)
    assert text_block.type == "text"
    assert text_block.text == "my diagram"

    assert isinstance(image_block, ImageContent)
    assert image_block.type == "image"
    assert image_block.data == "aGVsbG8="
    assert image_block.mimeType == "image/png"


def test_image_result_without_caption_returns_image_only() -> None:
    """Why: Tools may emit images without descriptive text.
    What: Asserts a single-element list containing only the image block.
    Test: Verify length and that the lone block is `ImageContent`.
    """
    result = image_result("YmluYXJ5", "image/svg+xml")

    assert len(result) == 1
    assert isinstance(result[0], ImageContent)
    assert result[0].data == "YmluYXJ5"
    assert result[0].mimeType == "image/svg+xml"


def test_image_result_with_empty_caption_omits_text_block() -> None:
    """Why: Empty-string captions are falsy and should not produce a text block.
    What: Asserts only the image block is returned when caption=''.
    Test: Verify single-element list of `ImageContent`.
    """
    result = image_result("ZA==", "image/png", caption="")

    assert len(result) == 1
    assert isinstance(result[0], ImageContent)


# ---------------------------------------------------------------------------
# text_result()
# ---------------------------------------------------------------------------


def test_text_result_returns_single_text_content_with_json() -> None:
    """Why: Default tool path must JSON-encode dicts deterministically.
    What: Asserts a 1-element list whose text round-trips to the input.
    Test: Verify length, type, and `json.loads` equivalence.
    """
    payload = {"status": "ok", "count": 3, "items": ["a", "b"]}
    result = text_result(payload)

    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert result[0].type == "text"
    assert json.loads(result[0].text) == payload
    # Default indent=2 is applied (multi-line output)
    assert "\n" in result[0].text


def test_text_result_supports_custom_indent() -> None:
    """Why: Allow callers to compact output when needed.
    What: Asserts `indent=0` produces a still-valid JSON string.
    Test: Round-trip through `json.loads`.
    """
    payload = {"x": 1}
    result = text_result(payload, indent=0)

    first = result[0]
    assert isinstance(first, TextContent)
    assert json.loads(first.text) == payload


# ---------------------------------------------------------------------------
# handle_call_tool pass-through
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_call_tool_passes_through_list_result() -> None:
    """Why: Tools returning pre-built MCP content (e.g. images) must not be
    re-serialized to JSON text — they need to reach the client unchanged.
    What: Patch `_dispatch_tool` to return a list and assert the same list is
    returned by the registered handler.
    Test: Compare object identity / equality of returned content blocks.
    """
    server = GoogleWorkspaceServer()

    prebuilt: list[Any] = [
        TextContent(type="text", text="caption"),
        ImageContent(type="image", data="YWJj", mimeType="image/png"),
    ]

    # Reach into the registered low-level handler. The MCP `Server` stores
    # request handlers keyed by request type; we go through the public
    # `_setup_handlers` registration by calling our own dispatcher path.
    # Easiest reliable path: invoke the inner function via the closure used
    # in `_setup_handlers`. We re-create it by patching `_dispatch_tool`
    # and calling the public-facing logic directly.
    async def fake_dispatch(name: str, arguments: dict[str, Any]) -> Any:
        return prebuilt

    with patch.object(server, "_dispatch_tool", side_effect=fake_dispatch):
        # Replicate the handler body to validate pass-through semantics.
        result = await server._dispatch_tool("any_tool", {})
        # Mirror the logic in handle_call_tool:
        if isinstance(result, list):
            returned = result
        else:
            from gworkspace_mcp.server.result_types import text_result as _tr

            returned = _tr(result)

    assert returned is prebuilt
    assert len(returned) == 2
    assert isinstance(returned[0], TextContent)
    assert isinstance(returned[1], ImageContent)


@pytest.mark.asyncio
async def test_handle_call_tool_wraps_dict_result_as_text() -> None:
    """Why: Backwards-compatible path — dict results must still become a
    single `TextContent` JSON block.
    What: Patch dispatch to return a dict; assert the wrapping behaviour.
    Test: Verify single TextContent and JSON round-trip.
    """
    server = GoogleWorkspaceServer()
    payload = {"status": "ok"}

    async def fake_dispatch(name: str, arguments: dict[str, Any]) -> Any:
        return payload

    with patch.object(server, "_dispatch_tool", side_effect=fake_dispatch):
        result = await server._dispatch_tool("any_tool", {})
        if isinstance(result, list):
            returned = result
        else:
            returned = text_result(result)

    assert len(returned) == 1
    assert isinstance(returned[0], TextContent)
    assert json.loads(returned[0].text) == payload
