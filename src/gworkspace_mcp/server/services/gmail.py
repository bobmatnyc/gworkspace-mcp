"""Google Gmail service module for MCP server."""

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
    # Gmail Label Management
    Tool(
        name="list_gmail_labels",
        description="List all Gmail labels (system and custom)",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="create_gmail_label",
        description="Create a custom Gmail label. Use '/' for nesting (e.g., 'Work/Projects')",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Label name (use '/' for nesting, e.g., 'Work/Projects')",
                },
                "label_list_visibility": {
                    "type": "string",
                    "enum": ["labelShow", "labelShowIfUnread", "labelHide"],
                    "description": "Visibility in label list (default: labelShow)",
                },
                "message_list_visibility": {
                    "type": "string",
                    "enum": ["show", "hide"],
                    "description": "Visibility in message list (default: show)",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="delete_gmail_label",
        description="Delete a custom Gmail label (cannot delete system labels)",
        inputSchema={
            "type": "object",
            "properties": {
                "label_id": {
                    "type": "string",
                    "description": "Label ID to delete",
                },
            },
            "required": ["label_id"],
        },
    ),
    # Gmail Filter Management
    Tool(
        name="list_gmail_filters",
        description="List all Gmail filters (auto-filtering rules)",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="create_gmail_filter",
        description="Create a Gmail filter to automatically process incoming messages",
        inputSchema={
            "type": "object",
            "properties": {
                "from_address": {
                    "type": "string",
                    "description": "Filter by sender email address",
                },
                "to_address": {
                    "type": "string",
                    "description": "Filter by recipient email address",
                },
                "subject": {
                    "type": "string",
                    "description": "Filter by subject contains text",
                },
                "query": {
                    "type": "string",
                    "description": "Gmail search query for advanced filtering (e.g., 'has:attachment larger:5M')",
                },
                "has_attachment": {
                    "type": "boolean",
                    "description": "Filter messages with attachments",
                },
                "add_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to add to matching messages",
                },
                "remove_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to remove (use 'INBOX' to archive)",
                },
                "mark_as_read": {
                    "type": "boolean",
                    "description": "Mark matching messages as read",
                },
                "star": {
                    "type": "boolean",
                    "description": "Star matching messages",
                },
                "forward_to": {
                    "type": "string",
                    "description": "Forward matching messages to this email address",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="delete_gmail_filter",
        description="Delete a Gmail filter by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "filter_id": {
                    "type": "string",
                    "description": "Filter ID to delete",
                },
            },
            "required": ["filter_id"],
        },
    ),
    # Gmail Message Management
    Tool(
        name="modify_gmail_message",
        description="Add or remove labels from a Gmail message (core label operation)",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to modify",
                },
                "add_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to add (e.g., ['STARRED', 'IMPORTANT'])",
                },
                "remove_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to remove (e.g., ['UNREAD', 'INBOX'])",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="archive_gmail_message",
        description="Archive a Gmail message (removes from INBOX, keeps in All Mail)",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to archive",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="trash_gmail_message",
        description="Move a Gmail message to trash",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to trash",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="untrash_gmail_message",
        description="Restore a Gmail message from trash",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to restore from trash",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="mark_gmail_as_read",
        description="Mark a Gmail message as read",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to mark as read",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="mark_gmail_as_unread",
        description="Mark a Gmail message as unread",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to mark as unread",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="star_gmail_message",
        description="Add star to a Gmail message",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to star",
                },
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="unstar_gmail_message",
        description="Remove star from a Gmail message",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to unstar",
                },
            },
            "required": ["message_id"],
        },
    ),
    # Gmail Batch Operations
    Tool(
        name="batch_modify_gmail_messages",
        description="Add or remove labels from multiple Gmail messages at once. Uses Gmail's efficient batch API.",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to modify",
                },
                "add_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to add (e.g., ['STARRED', 'IMPORTANT', or custom label IDs])",
                },
                "remove_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to remove (e.g., ['UNREAD', 'INBOX'])",
                },
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="batch_archive_gmail_messages",
        description="Archive multiple Gmail messages at once (removes INBOX label, keeps in All Mail)",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to archive",
                },
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="batch_trash_gmail_messages",
        description="Move multiple Gmail messages to trash at once",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to trash",
                },
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="batch_mark_gmail_as_read",
        description="Mark multiple Gmail messages as read at once",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to mark as read",
                },
            },
            "required": ["message_ids"],
        },
    ),
    Tool(
        name="batch_delete_gmail_messages",
        description="Permanently delete multiple Gmail messages at once (CAUTION: cannot be undone)",
        inputSchema={
            "type": "object",
            "properties": {
                "message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message IDs to permanently delete",
                },
            },
            "required": ["message_ids"],
        },
    ),
    # Gmail Vacation Settings
    Tool(
        name="get_vacation_settings",
        description="Get the current vacation auto-reply settings for Gmail",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="set_vacation_settings",
        description="Set vacation auto-reply settings for Gmail",
        inputSchema={
            "type": "object",
            "properties": {
                "enable_auto_reply": {
                    "type": "boolean",
                    "description": "Whether to enable vacation auto-reply",
                },
                "response_subject": {
                    "type": "string",
                    "description": "Subject for auto-reply messages (optional)",
                },
                "response_body_plain_text": {
                    "type": "string",
                    "description": "Plain text body for auto-reply messages",
                },
                "response_body_html": {
                    "type": "string",
                    "description": "HTML body for auto-reply messages (optional)",
                },
                "restrict_to_contacts": {
                    "type": "boolean",
                    "description": "Only send reply to contacts (default: false)",
                },
                "restrict_to_domain": {
                    "type": "boolean",
                    "description": "Only send reply to same domain (default: false)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in RFC3339 format (optional)",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in RFC3339 format (optional)",
                },
            },
            "required": ["enable_auto_reply"],
        },
    ),
    # Gmail Formatting Tools
    Tool(
        name="format_email_content",
        description="Format email content with bold, italic, and underline text for HTML emails.",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Plain text content to format",
                },
                "bold_ranges": {
                    "type": "array",
                    "description": "Array of start/end positions for bold formatting",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                        },
                        "required": ["start", "end"],
                    },
                },
                "italic_ranges": {
                    "type": "array",
                    "description": "Array of start/end positions for italic formatting",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                        },
                        "required": ["start", "end"],
                    },
                },
                "underline_ranges": {
                    "type": "array",
                    "description": "Array of start/end positions for underline formatting",
                    "items": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                        },
                        "required": ["start", "end"],
                    },
                },
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="set_email_signature",
        description="Set or update the HTML email signature for the authenticated Gmail user.",
        inputSchema={
            "type": "object",
            "properties": {
                "signature_html": {
                    "type": "string",
                    "description": "HTML signature content with basic formatting",
                },
            },
            "required": ["signature_html"],
        },
    ),
    Tool(
        name="create_formatted_email",
        description="Create a rich text email with HTML formatting including bold, italic, underline, and basic styling.",
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
                "html_body": {
                    "type": "string",
                    "description": "HTML-formatted email body",
                },
                "cc": {
                    "type": "string",
                    "description": "CC email address(es), comma-separated (optional)",
                },
                "bcc": {
                    "type": "string",
                    "description": "BCC email address(es), comma-separated (optional)",
                },
                "send_immediately": {
                    "type": "boolean",
                    "description": "Whether to send immediately (true) or create as draft (false)",
                    "default": False,
                },
            },
            "required": ["to", "subject", "html_body"],
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


async def _list_gmail_labels(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all Gmail labels."""
    url = f"{GMAIL_API_BASE}/users/me/labels"
    response = await svc._make_request("GET", url)

    labels = []
    for label in response.get("labels", []):
        labels.append(
            {
                "id": label.get("id"),
                "name": label.get("name"),
                "type": label.get("type"),
                "message_list_visibility": label.get("messageListVisibility"),
                "label_list_visibility": label.get("labelListVisibility"),
            }
        )

    system_labels = sorted(
        [lbl for lbl in labels if lbl["type"] == "system"], key=lambda x: x["name"]
    )
    user_labels = sorted([lbl for lbl in labels if lbl["type"] == "user"], key=lambda x: x["name"])

    return {
        "total": len(labels),
        "system_labels": system_labels,
        "user_labels": user_labels,
    }


async def _create_gmail_label(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a custom Gmail label."""
    name = arguments["name"]
    label_list_visibility = arguments.get("label_list_visibility", "labelShow")
    message_list_visibility = arguments.get("message_list_visibility", "show")

    url = f"{GMAIL_API_BASE}/users/me/labels"
    label_body = {
        "name": name,
        "labelListVisibility": label_list_visibility,
        "messageListVisibility": message_list_visibility,
    }

    response = await svc._make_request("POST", url, json_data=label_body)

    return {
        "status": "label_created",
        "id": response.get("id"),
        "name": response.get("name"),
        "type": response.get("type"),
        "label_list_visibility": response.get("labelListVisibility"),
        "message_list_visibility": response.get("messageListVisibility"),
    }


async def _delete_gmail_label(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a custom Gmail label."""
    label_id = arguments["label_id"]

    url = f"{GMAIL_API_BASE}/users/me/labels/{label_id}"
    await svc._make_delete_request(url)

    return {
        "status": "label_deleted",
        "label_id": label_id,
    }


async def _list_gmail_filters(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all Gmail filters."""
    url = f"{GMAIL_API_BASE}/users/me/settings/filters"
    response = await svc._make_request("GET", url)

    filters = []
    for f in response.get("filter", []):
        criteria = f.get("criteria", {})
        action = f.get("action", {})

        filters.append(
            {
                "id": f.get("id"),
                "criteria": {
                    "from": criteria.get("from"),
                    "to": criteria.get("to"),
                    "subject": criteria.get("subject"),
                    "query": criteria.get("query"),
                    "has_attachment": criteria.get("hasAttachment"),
                    "negated_query": criteria.get("negatedQuery"),
                    "size": criteria.get("size"),
                    "size_comparison": criteria.get("sizeComparison"),
                },
                "action": {
                    "add_label_ids": action.get("addLabelIds", []),
                    "remove_label_ids": action.get("removeLabelIds", []),
                    "forward": action.get("forward"),
                },
            }
        )

    return {
        "total": len(filters),
        "filters": filters,
    }


async def _create_gmail_filter(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a Gmail filter."""
    criteria: dict[str, Any] = {}
    if from_addr := arguments.get("from_address"):
        criteria["from"] = from_addr
    if to_addr := arguments.get("to_address"):
        criteria["to"] = to_addr
    if subject := arguments.get("subject"):
        criteria["subject"] = subject
    if query := arguments.get("query"):
        criteria["query"] = query
    if arguments.get("has_attachment"):
        criteria["hasAttachment"] = True

    action: dict[str, Any] = {}
    if add_labels := arguments.get("add_label_ids"):
        action["addLabelIds"] = add_labels
    if remove_labels := arguments.get("remove_label_ids"):
        action["removeLabelIds"] = remove_labels
    if arguments.get("mark_as_read"):
        action.setdefault("removeLabelIds", []).append("UNREAD")
    if arguments.get("star"):
        action.setdefault("addLabelIds", []).append("STARRED")
    if forward_to := arguments.get("forward_to"):
        action["forward"] = forward_to

    filter_body = {
        "criteria": criteria,
        "action": action,
    }

    url = f"{GMAIL_API_BASE}/users/me/settings/filters"
    response = await svc._make_request("POST", url, json_data=filter_body)

    return {
        "status": "filter_created",
        "id": response.get("id"),
        "criteria": {
            "from": response.get("criteria", {}).get("from"),
            "to": response.get("criteria", {}).get("to"),
            "subject": response.get("criteria", {}).get("subject"),
            "query": response.get("criteria", {}).get("query"),
            "has_attachment": response.get("criteria", {}).get("hasAttachment"),
        },
        "action": {
            "add_label_ids": response.get("action", {}).get("addLabelIds", []),
            "remove_label_ids": response.get("action", {}).get("removeLabelIds", []),
            "forward": response.get("action", {}).get("forward"),
        },
    }


async def _delete_gmail_filter(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a Gmail filter by ID."""
    filter_id = arguments["filter_id"]

    url = f"{GMAIL_API_BASE}/users/me/settings/filters/{filter_id}"
    await svc._make_delete_request(url)

    return {
        "status": "filter_deleted",
        "filter_id": filter_id,
    }


async def _modify_gmail_message(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add or remove labels from a Gmail message."""
    message_id = arguments["message_id"]
    add_label_ids = arguments.get("add_label_ids", [])
    remove_label_ids = arguments.get("remove_label_ids", [])

    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/modify"
    modify_body: dict[str, Any] = {}

    if add_label_ids:
        modify_body["addLabelIds"] = add_label_ids
    if remove_label_ids:
        modify_body["removeLabelIds"] = remove_label_ids

    response = await svc._make_request("POST", url, json_data=modify_body)

    return {
        "status": "message_modified",
        "id": response.get("id"),
        "thread_id": response.get("threadId"),
        "label_ids": response.get("labelIds", []),
    }


async def _archive_gmail_message(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Archive a Gmail message (removes from INBOX)."""
    message_id = arguments["message_id"]

    result = await _modify_gmail_message(
        svc,
        {
            "message_id": message_id,
            "remove_label_ids": ["INBOX"],
        },
    )

    return {
        "status": "message_archived",
        "id": result.get("id"),
        "thread_id": result.get("thread_id"),
        "label_ids": result.get("label_ids", []),
    }


async def _trash_gmail_message(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Move a Gmail message to trash."""
    message_id = arguments["message_id"]

    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/trash"
    response = await svc._make_request("POST", url)

    return {
        "status": "message_trashed",
        "id": response.get("id"),
        "thread_id": response.get("threadId"),
        "label_ids": response.get("labelIds", []),
    }


async def _untrash_gmail_message(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Restore a Gmail message from trash."""
    message_id = arguments["message_id"]

    url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/untrash"
    response = await svc._make_request("POST", url)

    return {
        "status": "message_restored",
        "id": response.get("id"),
        "thread_id": response.get("threadId"),
        "label_ids": response.get("labelIds", []),
    }


async def _mark_gmail_as_read(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Mark a Gmail message as read."""
    message_id = arguments["message_id"]

    result = await _modify_gmail_message(
        svc,
        {
            "message_id": message_id,
            "remove_label_ids": ["UNREAD"],
        },
    )

    return {
        "status": "message_marked_as_read",
        "id": result.get("id"),
        "thread_id": result.get("thread_id"),
        "label_ids": result.get("label_ids", []),
    }


async def _mark_gmail_as_unread(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Mark a Gmail message as unread."""
    message_id = arguments["message_id"]

    result = await _modify_gmail_message(
        svc,
        {
            "message_id": message_id,
            "add_label_ids": ["UNREAD"],
        },
    )

    return {
        "status": "message_marked_as_unread",
        "id": result.get("id"),
        "thread_id": result.get("thread_id"),
        "label_ids": result.get("label_ids", []),
    }


async def _star_gmail_message(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add star to a Gmail message."""
    message_id = arguments["message_id"]

    result = await _modify_gmail_message(
        svc,
        {
            "message_id": message_id,
            "add_label_ids": ["STARRED"],
        },
    )

    return {
        "status": "message_starred",
        "id": result.get("id"),
        "thread_id": result.get("thread_id"),
        "label_ids": result.get("label_ids", []),
    }


async def _unstar_gmail_message(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Remove star from a Gmail message."""
    message_id = arguments["message_id"]

    result = await _modify_gmail_message(
        svc,
        {
            "message_id": message_id,
            "remove_label_ids": ["STARRED"],
        },
    )

    return {
        "status": "message_unstarred",
        "id": result.get("id"),
        "thread_id": result.get("thread_id"),
        "label_ids": result.get("label_ids", []),
    }


async def _batch_modify_gmail_messages(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Add or remove labels from multiple Gmail messages using batch API."""
    message_ids = arguments.get("message_ids", [])
    add_label_ids = arguments.get("add_label_ids", [])
    remove_label_ids = arguments.get("remove_label_ids", [])

    if not message_ids:
        return {
            "status": "no_messages",
            "message": "No message IDs provided",
            "modified_count": 0,
        }

    url = f"{GMAIL_API_BASE}/users/me/messages/batchModify"
    batch_body: dict[str, Any] = {"ids": message_ids}

    if add_label_ids:
        batch_body["addLabelIds"] = add_label_ids
    if remove_label_ids:
        batch_body["removeLabelIds"] = remove_label_ids

    await svc._make_request("POST", url, json_data=batch_body)

    return {
        "status": "messages_modified",
        "modified_count": len(message_ids),
        "add_label_ids": add_label_ids,
        "remove_label_ids": remove_label_ids,
    }


async def _batch_archive_gmail_messages(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Archive multiple Gmail messages at once."""
    message_ids = arguments.get("message_ids", [])

    if not message_ids:
        return {
            "status": "no_messages",
            "message": "No message IDs provided",
            "archived_count": 0,
        }

    result = await _batch_modify_gmail_messages(
        svc,
        {
            "message_ids": message_ids,
            "remove_label_ids": ["INBOX"],
        },
    )

    return {
        "status": "messages_archived",
        "archived_count": result.get("modified_count", 0),
    }


async def _batch_trash_gmail_messages(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Move multiple Gmail messages to trash at once."""
    message_ids = arguments.get("message_ids", [])

    if not message_ids:
        return {
            "status": "no_messages",
            "message": "No message IDs provided",
            "trashed_count": 0,
            "failed_count": 0,
        }

    async def trash_single(msg_id: str) -> tuple[str, bool]:
        try:
            url = f"{GMAIL_API_BASE}/users/me/messages/{msg_id}/trash"
            await svc._make_request("POST", url)
            return msg_id, True
        except Exception:
            return msg_id, False

    results = await asyncio.gather(
        *[trash_single(msg_id) for msg_id in message_ids], return_exceptions=True
    )

    success_count = sum(1 for r in results if isinstance(r, tuple) and r[1])
    failed_count = len(message_ids) - success_count

    return {
        "status": "messages_trashed",
        "trashed_count": success_count,
        "failed_count": failed_count,
    }


async def _batch_mark_gmail_as_read(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Mark multiple Gmail messages as read at once."""
    message_ids = arguments.get("message_ids", [])

    if not message_ids:
        return {
            "status": "no_messages",
            "message": "No message IDs provided",
            "marked_count": 0,
        }

    result = await _batch_modify_gmail_messages(
        svc,
        {
            "message_ids": message_ids,
            "remove_label_ids": ["UNREAD"],
        },
    )

    return {
        "status": "messages_marked_as_read",
        "marked_count": result.get("modified_count", 0),
    }


async def _batch_delete_gmail_messages(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Permanently delete multiple Gmail messages at once."""
    message_ids = arguments.get("message_ids", [])

    if not message_ids:
        return {
            "status": "no_messages",
            "message": "No message IDs provided",
            "deleted_count": 0,
        }

    url = f"{GMAIL_API_BASE}/users/me/messages/batchDelete"
    await svc._make_request("POST", url, json_data={"ids": message_ids})

    return {
        "status": "messages_deleted",
        "deleted_count": len(message_ids),
        "warning": "Messages permanently deleted (cannot be undone)",
    }


async def _get_vacation_settings(
    svc: BaseService,
    arguments: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any]:
    """Get the current vacation auto-reply settings for Gmail."""
    url = f"{GMAIL_API_BASE}/users/me/settings/vacation"
    response = await svc._make_request("GET", url)

    return {
        "enable_auto_reply": response.get("enableAutoReply", False),
        "response_subject": response.get("responseSubject"),
        "response_body_plain_text": response.get("responseBodyPlainText"),
        "response_body_html": response.get("responseBodyHtml"),
        "restrict_to_contacts": response.get("restrictToContacts", False),
        "restrict_to_domain": response.get("restrictToDomain", False),
        "start_time": response.get("startTime"),
        "end_time": response.get("endTime"),
    }


async def _set_vacation_settings(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Set vacation auto-reply settings for Gmail."""
    url = f"{GMAIL_API_BASE}/users/me/settings/vacation"

    settings_body: dict[str, Any] = {
        "enableAutoReply": arguments["enable_auto_reply"],
    }

    if "response_subject" in arguments:
        settings_body["responseSubject"] = arguments["response_subject"]
    if "response_body_plain_text" in arguments:
        settings_body["responseBodyPlainText"] = arguments["response_body_plain_text"]
    if "response_body_html" in arguments:
        settings_body["responseBodyHtml"] = arguments["response_body_html"]
    if "restrict_to_contacts" in arguments:
        settings_body["restrictToContacts"] = arguments["restrict_to_contacts"]
    if "restrict_to_domain" in arguments:
        settings_body["restrictToDomain"] = arguments["restrict_to_domain"]
    if "start_time" in arguments:
        from datetime import datetime

        dt = datetime.fromisoformat(arguments["start_time"].replace("Z", "+00:00"))
        settings_body["startTime"] = str(int(dt.timestamp() * 1000))
    if "end_time" in arguments:
        from datetime import datetime

        dt = datetime.fromisoformat(arguments["end_time"].replace("Z", "+00:00"))
        settings_body["endTime"] = str(int(dt.timestamp() * 1000))

    response = await svc._make_request("PUT", url, json_data=settings_body)

    return {
        "status": "updated",
        "enable_auto_reply": response.get("enableAutoReply", False),
        "response_subject": response.get("responseSubject"),
        "response_body_plain_text": response.get("responseBodyPlainText"),
        "restrict_to_contacts": response.get("restrictToContacts", False),
        "restrict_to_domain": response.get("restrictToDomain", False),
    }


async def _format_email_content(
    svc: BaseService,
    arguments: dict[str, Any],  # noqa: ARG001
) -> dict[str, Any]:
    """Format email content with HTML formatting."""
    import html

    content = arguments["content"]
    bold_ranges = arguments.get("bold_ranges", [])
    italic_ranges = arguments.get("italic_ranges", [])
    underline_ranges = arguments.get("underline_ranges", [])

    html_content = html.escape(content)

    all_ranges = []
    for r in bold_ranges:
        all_ranges.append((r["start"], r["end"], "bold"))
    for r in italic_ranges:
        all_ranges.append((r["start"], r["end"], "italic"))
    for r in underline_ranges:
        all_ranges.append((r["start"], r["end"], "underline"))

    all_ranges.sort(key=lambda x: x[0], reverse=True)

    for start, end, format_type in all_ranges:
        if format_type == "bold":
            html_content = (
                html_content[:start] + "<b>" + html_content[start:end] + "</b>" + html_content[end:]
            )
        elif format_type == "italic":
            html_content = (
                html_content[:start] + "<i>" + html_content[start:end] + "</i>" + html_content[end:]
            )
        elif format_type == "underline":
            html_content = (
                html_content[:start] + "<u>" + html_content[start:end] + "</u>" + html_content[end:]
            )

    return {
        "status": "formatted",
        "original_content": content,
        "html_content": html_content,
        "formatting_applied": {
            "bold_ranges": len(bold_ranges),
            "italic_ranges": len(italic_ranges),
            "underline_ranges": len(underline_ranges),
        },
    }


async def _set_email_signature(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Set HTML email signature for the user."""
    signature_html = arguments["signature_html"]

    url = f"{GMAIL_API_BASE}/users/me/settings/sendAs/me"
    await svc._make_request("PATCH", url, json_data={"signature": signature_html})

    return {
        "status": "updated",
        "signature_html": signature_html,
    }


async def _create_formatted_email(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a rich text email with HTML formatting."""
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    to = arguments["to"]
    subject = arguments["subject"]
    html_body = arguments["html_body"]
    cc = arguments.get("cc")
    bcc = arguments.get("bcc")
    send_immediately = arguments.get("send_immediately", False)

    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    html_part = MIMEText(html_body, "html")
    msg.attach(html_part)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    request_body: dict[str, Any]
    if send_immediately:
        url = f"{GMAIL_API_BASE}/users/me/messages/send"
        request_body = {"raw": raw_message}
    else:
        url = f"{GMAIL_API_BASE}/users/me/drafts"
        request_body = {"message": {"raw": raw_message}}

    response = await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "sent" if send_immediately else "draft_created",
        "to": to,
        "subject": subject,
        "message_id": response.get("id"),
        "thread_id": response.get("threadId"),
    }


# =============================================================================
# Handler registry
# =============================================================================


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all Gmail handlers."""
    return {
        "search_gmail_messages": lambda args: _search_gmail_messages(svc, args),
        "get_gmail_message_content": lambda args: _get_gmail_message_content(svc, args),
        "download_gmail_attachment": lambda args: _download_gmail_attachment(svc, args),
        "send_email": lambda args: _send_email(svc, args),
        "create_draft": lambda args: _create_draft(svc, args),
        "send_draft": lambda args: _send_draft(svc, args),
        "reply_to_email": lambda args: _reply_to_email(svc, args),
        "list_gmail_labels": lambda args: _list_gmail_labels(svc, args),
        "create_gmail_label": lambda args: _create_gmail_label(svc, args),
        "delete_gmail_label": lambda args: _delete_gmail_label(svc, args),
        "list_gmail_filters": lambda args: _list_gmail_filters(svc, args),
        "create_gmail_filter": lambda args: _create_gmail_filter(svc, args),
        "delete_gmail_filter": lambda args: _delete_gmail_filter(svc, args),
        "modify_gmail_message": lambda args: _modify_gmail_message(svc, args),
        "archive_gmail_message": lambda args: _archive_gmail_message(svc, args),
        "trash_gmail_message": lambda args: _trash_gmail_message(svc, args),
        "untrash_gmail_message": lambda args: _untrash_gmail_message(svc, args),
        "mark_gmail_as_read": lambda args: _mark_gmail_as_read(svc, args),
        "mark_gmail_as_unread": lambda args: _mark_gmail_as_unread(svc, args),
        "star_gmail_message": lambda args: _star_gmail_message(svc, args),
        "unstar_gmail_message": lambda args: _unstar_gmail_message(svc, args),
        "batch_modify_gmail_messages": lambda args: _batch_modify_gmail_messages(svc, args),
        "batch_archive_gmail_messages": lambda args: _batch_archive_gmail_messages(svc, args),
        "batch_trash_gmail_messages": lambda args: _batch_trash_gmail_messages(svc, args),
        "batch_mark_gmail_as_read": lambda args: _batch_mark_gmail_as_read(svc, args),
        "batch_delete_gmail_messages": lambda args: _batch_delete_gmail_messages(svc, args),
        "get_vacation_settings": lambda args: _get_vacation_settings(svc, args),
        "set_vacation_settings": lambda args: _set_vacation_settings(svc, args),
        "format_email_content": lambda args: _format_email_content(svc, args),
        "set_email_signature": lambda args: _set_email_signature(svc, args),
        "create_formatted_email": lambda args: _create_formatted_email(svc, args),
    }
