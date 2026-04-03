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
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="download_gmail_attachment",
        description="Download a Gmail message attachment to a local file path",
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
                    "description": "Absolute local path to save the attachment",
                },
            },
            "required": ["message_id", "attachment_id", "save_path"],
        },
    ),
    Tool(
        name="send_email",
        description="Send an email message, optionally with file attachments",
        inputSchema={
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address(es), comma-separated for multiple",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject",
                },
                "body": {
                    "type": "string",
                    "description": "Email body (plain text)",
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
                    "items": {"type": "string"},
                    "description": "List of absolute local file paths to attach to the email",
                },
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="create_draft",
        description="Create an email draft without sending it, optionally as a reply on an existing thread",
        inputSchema={
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address(es), comma-separated for multiple",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject",
                },
                "body": {
                    "type": "string",
                    "description": "Email body (plain text or HTML)",
                },
                "cc": {
                    "type": "string",
                    "description": "CC recipients, comma-separated",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC recipients, comma-separated",
                },
                "in_reply_to": {
                    "type": "string",
                    "description": "Message-ID header of the message to reply to (for threading)",
                },
                "thread_id": {
                    "type": "string",
                    "description": "Gmail thread ID to associate the draft with",
                },
                "html": {
                    "type": "boolean",
                    "description": "If true, body is treated as HTML content (default false)",
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of absolute local file paths to attach to the draft",
                },
            },
            "required": ["to", "subject", "body"],
        },
    ),
    Tool(
        name="send_draft",
        description="Send an existing Gmail draft by its draft ID",
        inputSchema={
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "string",
                    "description": "The Gmail draft ID to send",
                },
            },
            "required": ["draft_id"],
        },
    ),
    Tool(
        name="reply_to_email",
        description="Reply to an existing email thread, optionally with file attachments",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Original message ID to reply to",
                },
                "body": {
                    "type": "string",
                    "description": "Reply body (plain text)",
                },
                "attachments": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of absolute local file paths to attach to the reply",
                },
            },
            "required": ["message_id", "body"],
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


def _build_email_message(
    to: str,
    subject: str,
    body: str,
    cc: str | None = None,
    bcc: str | None = None,
    thread_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    attachments: list[str] | None = None,
    html: bool = False,
) -> str:
    """Build RFC 2822 email message and return base64url encoded."""
    import base64
    import mimetypes
    import os
    from email import encoders as email_encoders
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    content_subtype = "html" if html else "plain"

    if attachments:
        message: MIMEMultipart | MIMEText = MIMEMultipart("mixed")
        message.attach(MIMEText(body, content_subtype))
        for path in attachments:
            detected_mime, _ = mimetypes.guess_type(path)
            main_type, sub_type = (detected_mime or "application/octet-stream").split("/", 1)
            with open(path, "rb") as f:
                file_data = f.read()
            part = MIMEBase(main_type, sub_type)
            part.set_payload(file_data)
            email_encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(path),
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


async def _download_gmail_attachment(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Download a Gmail message attachment to a local file."""
    import base64
    import os
    from pathlib import Path

    message_id = arguments["message_id"]
    attachment_id = arguments["attachment_id"]
    save_path = arguments["save_path"]

    _resolved_save = Path(save_path).expanduser().resolve()
    _home = Path.home().resolve()
    if not str(_resolved_save).startswith(str(_home)):
        return {
            "error": f"save_path must be within home directory ({_home}). Got: {_resolved_save}"
        }

    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}"
    response = await svc._make_request("GET", url)

    raw_data = response.get("data", "")
    data = base64.urlsafe_b64decode(raw_data + "==")

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(data)

    return {"saved_to": save_path, "size": len(data)}


async def _send_email(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Send an email message."""
    to = arguments["to"]
    subject = arguments["subject"]
    body = arguments["body"]
    cc = arguments.get("cc")
    bcc = arguments.get("bcc")
    attachments = arguments.get("attachments")

    raw_message = _build_email_message(to, subject, body, cc, bcc, attachments=attachments)

    url = f"{GMAIL_API_BASE}/users/me/messages/send"
    response = await svc._make_request("POST", url, json_data={"raw": raw_message})

    return {
        "status": "sent",
        "id": response.get("id"),
        "thread_id": response.get("threadId"),
        "label_ids": response.get("labelIds", []),
    }


async def _create_draft(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create an email draft without sending it."""
    to = arguments["to"]
    subject = arguments["subject"]
    body = arguments["body"]
    cc = arguments.get("cc")
    bcc = arguments.get("bcc")
    in_reply_to = arguments.get("in_reply_to")
    thread_id = arguments.get("thread_id")
    html = bool(arguments.get("html", False))
    attachments = arguments.get("attachments")

    raw_message = _build_email_message(
        to,
        subject,
        body,
        cc,
        bcc,
        in_reply_to=in_reply_to,
        attachments=attachments,
        html=html,
    )

    message_body: dict[str, Any] = {"raw": raw_message}
    if thread_id:
        message_body["threadId"] = thread_id

    url = f"{GMAIL_API_BASE}/users/me/drafts"
    response = await svc._make_request("POST", url, json_data={"message": message_body})

    return {
        "draft_id": response.get("id"),
        "message_id": response.get("message", {}).get("id"),
        "thread_id": response.get("message", {}).get("threadId"),
    }


async def _send_draft(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Send an existing Gmail draft."""
    draft_id = arguments["draft_id"]

    url = f"{GMAIL_API_BASE}/users/me/drafts/send"
    response = await svc._make_request("POST", url, json_data={"id": draft_id})

    return {
        "message_id": response.get("id"),
        "thread_id": response.get("threadId"),
        "status": "sent",
    }


async def _reply_to_email(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Reply to an existing email thread."""
    message_id = arguments["message_id"]
    body = arguments["body"]
    attachments = arguments.get("attachments")

    orig_url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
    original = await svc._make_request("GET", orig_url, params={"format": "metadata"})

    thread_id = original.get("threadId")
    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}

    reply_to = headers.get("Reply-To") or headers.get("From", "")
    original_subject = headers.get("Subject", "")
    message_id_header = headers.get("Message-ID")

    if not original_subject.lower().startswith("re:"):
        reply_subject = f"Re: {original_subject}"
    else:
        reply_subject = original_subject

    raw_message = _build_email_message(
        to=reply_to,
        subject=reply_subject,
        body=body,
        in_reply_to=message_id_header,
        references=message_id_header,
        attachments=attachments,
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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail message handlers."""
    return {
        "search_gmail_messages": lambda args: _search_gmail_messages(svc, args),
        "get_gmail_message_content": lambda args: _get_gmail_message_content(svc, args),
        "download_gmail_attachment": lambda args: _download_gmail_attachment(svc, args),
        "send_email": lambda args: _send_email(svc, args),
        "create_draft": lambda args: _create_draft(svc, args),
        "send_draft": lambda args: _send_draft(svc, args),
        "reply_to_email": lambda args: _reply_to_email(svc, args),
    }
