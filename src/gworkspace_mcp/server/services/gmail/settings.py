"""Gmail settings sub-module: vacation responder, signature, and rich formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
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
# Handler functions
# =============================================================================


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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail settings handlers."""
    return {
        "get_vacation_settings": lambda args: _get_vacation_settings(svc, args),
        "set_vacation_settings": lambda args: _set_vacation_settings(svc, args),
        "format_email_content": lambda args: _format_email_content(svc, args),
        "set_email_signature": lambda args: _set_email_signature(svc, args),
        "create_formatted_email": lambda args: _create_formatted_email(svc, args),
    }
