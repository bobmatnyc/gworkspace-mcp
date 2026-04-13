"""Gmail settings sub-module: vacation responder, signature, and rich formatting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
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
        name="manage_gmail_settings",
        description=(
            "Manage Gmail account settings. "
            "Actions: 'get_vacation' (get vacation auto-reply settings), "
            "'set_vacation' (enable/update vacation auto-reply), "
            "'set_signature' (set the HTML email signature)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_vacation", "set_vacation", "set_signature"],
                    "description": "Setting operation to perform",
                },
                "enable_auto_reply": {
                    "type": "boolean",
                    "description": "Whether to enable vacation auto-reply (required for action=set_vacation)",
                },
                "response_subject": {
                    "type": "string",
                    "description": "Subject for auto-reply messages (for action=set_vacation)",
                },
                "response_body_plain_text": {
                    "type": "string",
                    "description": "Plain text body for auto-reply messages (for action=set_vacation)",
                },
                "response_body_html": {
                    "type": "string",
                    "description": "HTML body for auto-reply messages (for action=set_vacation)",
                },
                "restrict_to_contacts": {
                    "type": "boolean",
                    "description": "Only send auto-reply to contacts (for action=set_vacation, default: false)",
                },
                "restrict_to_domain": {
                    "type": "boolean",
                    "description": "Only send auto-reply to same domain (for action=set_vacation, default: false)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Vacation start time in RFC3339 format (for action=set_vacation)",
                },
                "end_time": {
                    "type": "string",
                    "description": "Vacation end time in RFC3339 format (for action=set_vacation)",
                },
                "signature_html": {
                    "type": "string",
                    "description": "HTML signature content (required for action=set_signature)",
                },
            },
            "required": ["action"],
        },
    ),
]


# =============================================================================
# Handler functions
# =============================================================================


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


async def _manage_gmail_settings(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Manage Gmail settings: get_vacation, set_vacation, or set_signature."""
    action = arguments["action"]

    if action == "get_vacation":
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

    if action == "set_vacation":
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

    # action == "set_signature"
    signature_html = arguments["signature_html"]
    url = f"{GMAIL_API_BASE}/users/me/settings/sendAs/me"
    await svc._make_request("PATCH", url, json_data={"signature": signature_html})

    return {"status": "updated", "signature_html": signature_html}


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail settings handlers."""
    return {
        "format_email_content": lambda args: _format_email_content(svc, args),
        "manage_gmail_settings": lambda args: _manage_gmail_settings(svc, args),
    }
