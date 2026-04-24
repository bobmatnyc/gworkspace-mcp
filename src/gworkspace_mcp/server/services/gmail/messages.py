"""Gmail messages sub-module: compose, send, reply, drafts, and attachments."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="search_gmail_messages",
        description="Search Gmail messages using a query string",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g., 'from:user@example.com subject:meeting')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of messages to return (default: 10)",
                    "default": 10,
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_gmail_message_content",
        description="Get the full content of a Gmail message by ID, including any attachments metadata",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="download_gmail_attachment",
        description=(
            "Download a Gmail message attachment. By default saves to a local file; "
            "set return_content=true to return the base64-encoded attachment content in the response."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID containing the attachment",
                },
                "attachment_id": {
                    "type": "string",
                    "description": "Attachment ID from get_gmail_message_content response",
                },
                "save_path": {
                    "type": "string",
                    "description": "Absolute local path to save the attachment (required when return_content is false)",
                },
                "return_content": {
                    "type": "boolean",
                    "description": "If true, return base64-encoded attachment content in the response instead of saving to disk. Default false.",
                    "default": False,
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["message_id", "attachment_id"],
        },
    ),
    Tool(
        name="list_message_attachments",
        description=(
            "List all attachments on a Gmail message without downloading content. "
            "Returns attachment metadata: attachmentId, filename, mimeType, size."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account.",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="compose_email",
        description=(
            "Compose and send emails, create drafts, send existing drafts, or reply to messages. "
            "Actions: 'send' (send immediately), 'draft' (save as draft), "
            "'send_draft' (send an existing draft by draft_id), 'reply' (reply to a message by message_id)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send", "draft", "send_draft", "reply"],
                    "description": "Action to perform",
                },
                "to": {
                    "type": "string",
                    "description": "Recipient email address(es), comma-separated (required for send/draft)",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject (required for send/draft)",
                },
                "body": {
                    "type": "string",
                    "description": "Email body — plain text by default; ignored if html_body is provided",
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML email body; overrides body and sets content-type to text/html",
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipients, comma-separated",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC recipients, comma-separated",
                },
                "attachments": {
                    "type": "array",
                    "description": (
                        "List of attachments. Each item is either a local file path string "
                        "(e.g. '/tmp/report.pdf') or an object with "
                        "{ 'filename': str, 'mimeType': str, 'content': str (base64) } for inline content, "
                        "or { 'filename': str, 'driveFileId': str } for Drive files."
                    ),
                    "items": {
                        "oneOf": [
                            {"type": "string", "description": "Absolute local file path"},
                            {
                                "type": "object",
                                "properties": {
                                    "filename": {"type": "string"},
                                    "mimeType": {"type": "string"},
                                    "content": {
                                        "type": "string",
                                        "description": "base64-encoded content",
                                    },
                                },
                                "required": ["filename", "content"],
                            },
                            {
                                "type": "object",
                                "properties": {
                                    "filename": {"type": "string"},
                                    "driveFileId": {"type": "string"},
                                },
                                "required": ["filename", "driveFileId"],
                            },
                        ]
                    },
                },
                "draft_id": {
                    "type": "string",
                    "description": "Draft ID to send (required for action=send_draft)",
                },
                "message_id": {
                    "type": "string",
                    "description": "Original message ID to reply to (required for action=reply)",
                },
                "in_reply_to": {
                    "type": "string",
                    "description": "Message-ID header for threading (used with action=draft)",
                },
                "thread_id": {
                    "type": "string",
                    "description": "Gmail thread ID to associate the draft with (used with action=draft)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action"],
        },
    ),
]


# =============================================================================
# Helper functions
# =============================================================================


def _extract_message_body(payload: dict[str, Any]) -> str:
    """Extract message body from Gmail payload.

    Handles both simple and multipart messages.
    """
    import base64

    # Simple message with body data
    if "body" in payload and payload["body"].get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # Multipart message
    parts = payload.get("parts", [])
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        elif mime_type.startswith("multipart/"):
            # Recursively extract from nested parts
            result = _extract_message_body(part)
            if result:
                return result

    # Fallback to HTML if no plain text
    for part in parts:
        if part.get("mimeType") == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return ""


def _extract_attachments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract attachment metadata from Gmail message payload.

    Recursively walks multipart payloads to find all attachment parts.
    """
    attachments: list[dict[str, Any]] = []
    body_data = payload.get("body", {})
    if body_data.get("attachmentId"):
        attachments.append(
            {
                "filename": payload.get("filename", "attachment"),
                "mimeType": payload.get("mimeType", "application/octet-stream"),
                "size": body_data.get("size", 0),
                "attachmentId": body_data["attachmentId"],
            }
        )
    for part in payload.get("parts", []):
        attachments.extend(_extract_attachments(part))
    return attachments


#: Maximum total size of all attachments in a single email (Gmail's limit is 25MB).
MAX_ATTACHMENT_TOTAL_BYTES = 25 * 1024 * 1024  # 26214400


def _build_email_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    attachments: list[str | dict[str, Any]] | None = None,
    html: bool = False,
) -> str:
    """Build an RFC 2822 email message and return its base64url-encoded form.

    Why: Gmail's send endpoint expects base64url-encoded RFC 2822 bytes; centralizing
    construction here keeps attachment handling (local paths, inline base64, Drive refs)
    consistent across send/draft/reply flows.
    What: Builds a MIMEText (no attachments) or MIMEMultipart (with attachments) message,
    enforcing a 25MB total attachment cap. Supports three attachment forms:
      - str: absolute local file path (opened and read from disk)
      - dict with 'content': inline base64-encoded bytes + filename (+ optional mimeType)
      - dict with 'driveFileId': currently raises ValueError (future enhancement)
    Test: Build with each attachment form, decode the result, and assert Content-Disposition
    headers + filenames. Pass >25MB of data and assert ValueError is raised.
    """
    import base64
    import mimetypes
    import os
    from email import encoders as email_encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    content_subtype = "html" if html else "plain"

    if attachments:
        # Pre-resolve each attachment into (filename, mime_type, bytes) and validate total size
        resolved: list[tuple[str, str, bytes]] = []
        total_size = 0
        for item in attachments:
            if isinstance(item, str):
                path = item
                detected_mime, _ = mimetypes.guess_type(path)
                mime = detected_mime or "application/octet-stream"
                with open(path, "rb") as f:
                    file_data = f.read()
                filename = os.path.basename(path)
                resolved.append((filename, mime, file_data))
            elif isinstance(item, dict):
                if "driveFileId" in item:
                    raise ValueError(
                        "driveFileId attachments not yet supported; "
                        "download the file first and use a local path or base64 content."
                    )
                if "content" not in item or "filename" not in item:
                    raise ValueError(
                        "Inline attachment dicts require both 'filename' and 'content' fields."
                    )
                filename = item["filename"]
                try:
                    file_data = base64.b64decode(item["content"], validate=True)
                except Exception as exc:
                    raise ValueError(
                        f"Attachment '{filename}' has invalid base64 content: {exc}"
                    ) from exc
                mime = item.get("mimeType") or (
                    mimetypes.guess_type(filename)[0] or "application/octet-stream"
                )
                resolved.append((filename, mime, file_data))
            else:
                raise ValueError(
                    f"Unsupported attachment type: {type(item).__name__}. "
                    "Expected str path or dict."
                )

            total_size += len(resolved[-1][2])
            if total_size > MAX_ATTACHMENT_TOTAL_BYTES:
                raise ValueError(
                    f"Total attachment size {total_size} bytes exceeds "
                    f"{MAX_ATTACHMENT_TOTAL_BYTES} bytes (25MB) limit."
                )

        message: MIMEMultipart | MIMEText = MIMEMultipart("mixed")
        message.attach(MIMEText(body, content_subtype))
        for filename, mime, file_data in resolved:
            main_type, sub_type = (
                mime.split("/", 1) if "/" in mime else ("application", "octet-stream")
            )
            part = MIMEBase(main_type, sub_type)
            part.set_payload(file_data)
            email_encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=filename,
            )
            message.attach(part)  # type: ignore[union-attr]
    else:
        message = MIMEText(body, content_subtype)

    message["to"] = to
    message["subject"] = subject

    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references

    # thread_id is not part of the email headers — it's passed in the API body
    _ = thread_id

    return base64.urlsafe_b64encode(message.as_bytes()).decode()


# =============================================================================
# Handler functions
# =============================================================================


async def _search_gmail_messages(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search Gmail messages using parallel fetching."""
    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 10)

    url = f"{GMAIL_API_BASE}/users/me/messages"
    params = {"q": query, "maxResults": max_results}

    response = await svc._make_request("GET", url, params=params)

    message_list = response.get("messages", [])
    if not message_list:
        return {"messages": [], "count": 0}

    async def fetch_message_detail(msg_id: str) -> dict[str, Any]:
        msg_url = f"{GMAIL_API_BASE}/users/me/messages/{msg_id}"
        return await svc._make_request("GET", msg_url, params={"format": "metadata"})

    details = await asyncio.gather(
        *[fetch_message_detail(msg["id"]) for msg in message_list],
        return_exceptions=True,
    )

    messages = []
    for msg, msg_detail in zip(message_list, details, strict=False):
        if isinstance(msg_detail, BaseException):
            logger.warning("Failed to fetch message %s: %s", msg["id"], msg_detail)
            continue

        detail: dict[str, Any] = msg_detail
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}

        messages.append(
            {
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "subject": headers.get("Subject"),
                "from": headers.get("From"),
                "to": headers.get("To"),
                "date": headers.get("Date"),
                "snippet": detail.get("snippet"),
            }
        )

    return {"messages": messages, "count": len(messages)}


async def _get_gmail_message_content(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get full content of a Gmail message."""
    message_id = arguments["message_id"]

    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
    response = await svc._make_request("GET", url, params={"format": "full"})

    headers = {h["name"]: h["value"] for h in response.get("payload", {}).get("headers", [])}

    payload = response.get("payload", {})
    body = _extract_message_body(payload)
    attachments = _extract_attachments(payload)

    return {
        "id": response.get("id"),
        "thread_id": response.get("threadId"),
        "subject": headers.get("Subject"),
        "from": headers.get("From"),
        "to": headers.get("To"),
        "cc": headers.get("Cc"),
        "date": headers.get("Date"),
        "body": body,
        "labels": response.get("labelIds", []),
        "attachments": attachments,
    }


async def _list_message_attachments(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List attachments on a Gmail message without downloading their content.

    Why: Callers frequently need to enumerate attachments (filename/mime/size) to decide
    which ones to download; fetching each attachment payload just to inspect metadata is
    wasteful. This returns only the metadata extracted from the message payload.
    What: Fetches the message with format=full and extracts attachment metadata via
    _extract_attachments. Returns a list of {attachmentId, filename, mimeType, size}.
    Test: Mock svc._make_request to return a payload with nested multipart attachments;
    assert the returned count matches and each entry has the expected metadata fields.
    """
    message_id = arguments["message_id"]
    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
    response = await svc._make_request("GET", url, params={"format": "full"})
    payload = response.get("payload", {})
    attachments = _extract_attachments(payload)
    return {
        "message_id": message_id,
        "attachments": attachments,
        "count": len(attachments),
    }


async def _download_gmail_attachment(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Download a Gmail attachment to disk or return its base64 content inline.

    Why: Agents sometimes need attachment bytes in-context (e.g. pass to another tool)
    without writing to disk; at the same time the save-to-file path is still the common
    case. A single tool supports both modes via return_content.
    What: If return_content is True, fetches the message payload to resolve
    filename/mimeType, downloads the attachment bytes, and returns them base64-encoded.
    Otherwise, requires save_path, ensures it is inside $HOME, writes bytes to disk,
    and returns {saved_to, size}.
    Test: Call with return_content=True and a mocked attachment response; assert the
    response dict contains filename, mimeType, base64 content, and size. Call with
    return_content=False and a tmp_path save_path; assert file is written and response
    contains saved_to + size.
    """
    import base64
    import os
    from pathlib import Path

    message_id = arguments["message_id"]
    attachment_id = arguments["attachment_id"]
    return_content = bool(arguments.get("return_content", False))
    save_path = arguments.get("save_path")

    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}"
    response = await svc._make_request("GET", url)
    raw_data = response.get("data", "")
    data = base64.urlsafe_b64decode(raw_data + "==")

    if return_content:
        # Look up metadata from the message payload for filename + mimeType
        msg_url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
        msg_response = await svc._make_request("GET", msg_url, params={"format": "full"})
        payload = msg_response.get("payload", {})
        attachments_meta = _extract_attachments(payload)
        matched = next(
            (a for a in attachments_meta if a.get("attachmentId") == attachment_id),
            None,
        )
        filename = matched.get("filename", "attachment") if matched else "attachment"
        mime_type = (
            matched.get("mimeType", "application/octet-stream")
            if matched
            else "application/octet-stream"
        )
        return {
            "filename": filename,
            "mimeType": mime_type,
            "content": base64.b64encode(data).decode("ascii"),
            "size": len(data),
        }

    if not save_path:
        return {"error": "save_path is required when return_content is false."}

    _resolved_save = Path(save_path).expanduser().resolve()
    _home = Path.home().resolve()
    if not str(_resolved_save).startswith(str(_home)):
        return {
            "error": f"save_path must be within home directory ({_home}). Got: {_resolved_save}"
        }

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(data)

    return {"saved_to": save_path, "size": len(data)}


async def _compose_email(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Compose emails: send, draft, send_draft, or reply."""
    action = arguments["action"]

    if action == "send_draft":
        draft_id = arguments["draft_id"]
        url = f"{GMAIL_API_BASE}/users/me/drafts/send"
        response = await svc._make_request("POST", url, json_data={"id": draft_id})
        return {
            "status": "sent",
            "message_id": response.get("id"),
            "thread_id": response.get("threadId"),
        }

    if action == "reply":
        message_id = arguments["message_id"]
        body = arguments.get("body", "")
        html_body = arguments.get("html_body")
        attachments = arguments.get("attachments")

        orig_url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
        original = await svc._make_request("GET", orig_url, params={"format": "metadata"})

        thread_id = original.get("threadId")
        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}

        reply_to = headers.get("Reply-To") or headers.get("From", "")
        original_subject = headers.get("Subject", "")
        message_id_header = headers.get("Message-ID")

        reply_subject = (
            original_subject
            if original_subject.lower().startswith("re:")
            else f"Re: {original_subject}"
        )

        use_html = html_body is not None
        actual_body = html_body if use_html else body

        raw_message = _build_email_message(
            to=reply_to,
            subject=reply_subject,
            body=actual_body or "",
            in_reply_to=message_id_header,
            references=message_id_header,
            attachments=attachments,
            html=use_html,
        )

        url = f"{GMAIL_API_BASE}/users/me/messages/send"
        response = await svc._make_request(
            "POST", url, json_data={"raw": raw_message, "threadId": thread_id}
        )

        return {
            "status": "reply_sent",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "in_reply_to": message_id,
        }

    # action in ("send", "draft")
    to = arguments["to"]
    subject = arguments["subject"]
    body = arguments.get("body", "") or ""
    html_body = arguments.get("html_body")
    cc = arguments.get("cc")
    bcc = arguments.get("bcc")
    attachments = arguments.get("attachments")
    in_reply_to = arguments.get("in_reply_to")
    thread_id = arguments.get("thread_id")

    use_html = html_body is not None
    actual_body = html_body if use_html else body

    raw_message = _build_email_message(
        to,
        subject,
        actual_body or "",
        cc,
        bcc,
        thread_id=thread_id,
        in_reply_to=in_reply_to,
        attachments=attachments,
        html=use_html,
    )

    if action == "send":
        url = f"{GMAIL_API_BASE}/users/me/messages/send"
        response = await svc._make_request("POST", url, json_data={"raw": raw_message})
        return {
            "status": "sent",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "label_ids": response.get("labelIds", []),
        }

    # action == "draft"
    message_body: dict[str, Any] = {"raw": raw_message}
    if thread_id:
        message_body["threadId"] = thread_id

    url = f"{GMAIL_API_BASE}/users/me/drafts"
    response = await svc._make_request("POST", url, json_data={"message": message_body})
    return {
        "status": "draft_created",
        "draft_id": response.get("id"),
        "message_id": response.get("message", {}).get("id"),
        "thread_id": response.get("message", {}).get("threadId"),
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail message handlers."""
    return {
        "search_gmail_messages": lambda args: _search_gmail_messages(svc, args),
        "get_gmail_message_content": lambda args: _get_gmail_message_content(svc, args),
        "download_gmail_attachment": lambda args: _download_gmail_attachment(svc, args),
        "list_message_attachments": lambda args: _list_message_attachments(svc, args),
        "compose_email": lambda args: _compose_email(svc, args),
    }
