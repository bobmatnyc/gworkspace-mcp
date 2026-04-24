"""Unit tests for Gmail attachment handling (issue #15).

Covers:
- `_build_email_message` with string path, inline base64 dict, and driveFileId dict
- Size-limit enforcement (>25MB)
- `_list_message_attachments` handler
- `_download_gmail_attachment` handler in both save-to-disk and return_content modes
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from gworkspace_mcp.server.services.gmail.messages import (
    MAX_ATTACHMENT_TOTAL_BYTES,
    TOOLS,
    _build_email_message,
    _download_gmail_attachment,
    _list_message_attachments,
    get_handlers,
)


def _decode_raw(raw: str) -> bytes:
    """Decode the base64url-encoded RFC 2822 output of _build_email_message."""
    return base64.urlsafe_b64decode(raw.encode() + b"==")


# =============================================================================
# Tool schema / registration sanity
# =============================================================================


@pytest.mark.unit
class TestAttachmentTools:
    """Verify new tools are registered with the expected shape."""

    def test_list_message_attachments_tool_present(self) -> None:
        names = [t.name for t in TOOLS]
        assert "list_message_attachments" in names

    def test_download_gmail_attachment_no_longer_requires_save_path(self) -> None:
        tool = next(t for t in TOOLS if t.name == "download_gmail_attachment")
        required = tool.inputSchema.get("required", [])
        assert "save_path" not in required
        assert "message_id" in required
        assert "attachment_id" in required

    def test_download_gmail_attachment_has_return_content(self) -> None:
        tool = next(t for t in TOOLS if t.name == "download_gmail_attachment")
        props = tool.inputSchema["properties"]
        assert "return_content" in props
        assert props["return_content"]["type"] == "boolean"

    def test_compose_email_attachments_schema_is_oneof(self) -> None:
        tool = next(t for t in TOOLS if t.name == "compose_email")
        items = tool.inputSchema["properties"]["attachments"]["items"]
        assert "oneOf" in items
        assert len(items["oneOf"]) == 3


# =============================================================================
# _build_email_message
# =============================================================================


@pytest.mark.unit
class TestBuildEmailMessageAttachments:
    """Tests for the three attachment forms in _build_email_message."""

    def test_string_path_attachment(self, tmp_path: Path) -> None:
        f = tmp_path / "report.txt"
        f.write_bytes(b"hello world")

        raw = _build_email_message(
            to="to@example.com",
            subject="s",
            body="b",
            attachments=[str(f)],
        )

        decoded = _decode_raw(raw).decode("utf-8", errors="replace")
        assert "Content-Disposition" in decoded
        assert "report.txt" in decoded
        # Base64 of "hello world" = "aGVsbG8gd29ybGQ="
        assert "aGVsbG8gd29ybGQ" in decoded

    def test_inline_base64_dict_attachment(self) -> None:
        content = base64.b64encode(b"inline-payload").decode("ascii")
        raw = _build_email_message(
            to="to@example.com",
            subject="s",
            body="b",
            attachments=[
                {
                    "filename": "inline.bin",
                    "mimeType": "application/octet-stream",
                    "content": content,
                }
            ],
        )

        decoded = _decode_raw(raw).decode("utf-8", errors="replace")
        assert "inline.bin" in decoded
        assert "application/octet-stream" in decoded
        # Base64 of "inline-payload" = "aW5saW5lLXBheWxvYWQ="
        assert "aW5saW5lLXBheWxvYWQ" in decoded

    def test_inline_base64_missing_content_raises(self) -> None:
        with pytest.raises(ValueError, match="filename.*content"):
            _build_email_message(
                to="to@example.com",
                subject="s",
                body="b",
                attachments=[{"filename": "x.bin"}],
            )

    def test_inline_base64_invalid_content_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid base64"):
            _build_email_message(
                to="to@example.com",
                subject="s",
                body="b",
                attachments=[{"filename": "bad.bin", "content": "!!!not-base64!!!"}],
            )

    def test_drive_file_id_raises_not_supported_error(self) -> None:
        with pytest.raises(ValueError, match="driveFileId attachments not yet supported"):
            _build_email_message(
                to="to@example.com",
                subject="s",
                body="b",
                attachments=[{"filename": "doc.pdf", "driveFileId": "abc123"}],
            )

    def test_size_limit_exceeded_raises(self) -> None:
        # One byte over the limit — use base64 to avoid creating a huge temp file on disk.
        oversized = b"x" * (MAX_ATTACHMENT_TOTAL_BYTES + 1)
        content = base64.b64encode(oversized).decode("ascii")
        with pytest.raises(ValueError, match="exceeds"):
            _build_email_message(
                to="to@example.com",
                subject="s",
                body="b",
                attachments=[
                    {
                        "filename": "big.bin",
                        "content": content,
                    }
                ],
            )

    def test_unsupported_attachment_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported attachment type"):
            _build_email_message(
                to="to@example.com",
                subject="s",
                body="b",
                attachments=[12345],  # type: ignore[list-item]
            )

    def test_no_attachments_produces_simple_text(self) -> None:
        raw = _build_email_message(
            to="to@example.com",
            subject="s",
            body="plain body",
        )
        decoded = _decode_raw(raw).decode("utf-8", errors="replace")
        assert "plain body" in decoded
        assert "multipart/mixed" not in decoded


# =============================================================================
# _list_message_attachments
# =============================================================================


def _make_svc_with_response(response: dict[str, Any]) -> MagicMock:
    """Build a mock BaseService whose _make_request is an AsyncMock returning response."""
    svc = MagicMock()
    svc._make_request = AsyncMock(return_value=response)
    return svc


@pytest.mark.unit
class TestListMessageAttachments:
    """Tests for the _list_message_attachments handler."""

    @pytest.mark.asyncio
    async def test_returns_attachment_metadata(self) -> None:
        payload = {
            "payload": {
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": "aGVsbG8="}},
                    {
                        "mimeType": "application/pdf",
                        "filename": "report.pdf",
                        "body": {"attachmentId": "att-1", "size": 1024},
                    },
                    {
                        "mimeType": "image/png",
                        "filename": "chart.png",
                        "body": {"attachmentId": "att-2", "size": 2048},
                    },
                ]
            }
        }
        svc = _make_svc_with_response(payload)

        result = await _list_message_attachments(svc, {"message_id": "msg-42"})

        assert result["message_id"] == "msg-42"
        assert result["count"] == 2
        assert {a["attachmentId"] for a in result["attachments"]} == {"att-1", "att-2"}
        by_id = {a["attachmentId"]: a for a in result["attachments"]}
        assert by_id["att-1"]["filename"] == "report.pdf"
        assert by_id["att-1"]["mimeType"] == "application/pdf"
        assert by_id["att-1"]["size"] == 1024

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_attachments(self) -> None:
        svc = _make_svc_with_response({"payload": {"parts": []}})
        result = await _list_message_attachments(svc, {"message_id": "m"})
        assert result["count"] == 0
        assert result["attachments"] == []


# =============================================================================
# _download_gmail_attachment
# =============================================================================


@pytest.mark.unit
class TestDownloadGmailAttachment:
    """Tests for _download_gmail_attachment in save-to-disk and inline modes."""

    @pytest.mark.asyncio
    async def test_save_to_disk_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # The handler restricts save_path to $HOME; point $HOME at tmp_path so the
        # test works regardless of platform-specific tmp locations (e.g. macOS /private/var).
        monkeypatch.setenv("HOME", str(tmp_path))

        # Gmail returns base64url-encoded bytes
        payload_bytes = b"file-content"
        encoded = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")

        svc = MagicMock()
        svc._make_request = AsyncMock(return_value={"data": encoded})

        save_path = tmp_path / "dl" / "out.bin"
        result = await _download_gmail_attachment(
            svc,
            {
                "message_id": "m",
                "attachment_id": "a",
                "save_path": str(save_path),
                "return_content": False,
            },
        )

        assert result["saved_to"] == str(save_path)
        assert result["size"] == len(payload_bytes)
        assert save_path.read_bytes() == payload_bytes

    @pytest.mark.asyncio
    async def test_return_content_mode(self) -> None:
        payload_bytes = b"inline-bytes"
        encoded = base64.urlsafe_b64encode(payload_bytes).decode().rstrip("=")

        # First call returns attachment data; second call returns message metadata
        svc = MagicMock()
        svc._make_request = AsyncMock(
            side_effect=[
                {"data": encoded},
                {
                    "payload": {
                        "parts": [
                            {
                                "mimeType": "text/plain",
                                "filename": "note.txt",
                                "body": {"attachmentId": "att-9", "size": len(payload_bytes)},
                            }
                        ]
                    }
                },
            ]
        )

        result = await _download_gmail_attachment(
            svc,
            {
                "message_id": "m",
                "attachment_id": "att-9",
                "return_content": True,
            },
        )

        assert result["filename"] == "note.txt"
        assert result["mimeType"] == "text/plain"
        assert result["size"] == len(payload_bytes)
        assert base64.b64decode(result["content"]) == payload_bytes

    @pytest.mark.asyncio
    async def test_missing_save_path_when_not_returning_content(self) -> None:
        svc = MagicMock()
        svc._make_request = AsyncMock(return_value={"data": ""})

        result = await _download_gmail_attachment(
            svc,
            {"message_id": "m", "attachment_id": "a"},
        )

        assert "error" in result
        assert "save_path" in result["error"]

    @pytest.mark.asyncio
    async def test_save_path_outside_home_rejected(self) -> None:
        svc = MagicMock()
        svc._make_request = AsyncMock(return_value={"data": ""})

        result = await _download_gmail_attachment(
            svc,
            {
                "message_id": "m",
                "attachment_id": "a",
                "save_path": "/etc/evil.bin",
            },
        )

        assert "error" in result
        assert "home directory" in result["error"]


# =============================================================================
# Handler registration
# =============================================================================


@pytest.mark.unit
class TestHandlerRegistration:
    def test_list_message_attachments_handler_registered(self) -> None:
        svc = MagicMock()
        handlers = get_handlers(svc)
        assert "list_message_attachments" in handlers
        assert "download_gmail_attachment" in handlers
        assert callable(handlers["list_message_attachments"])
