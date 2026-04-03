"""Gmail labels and filters sub-module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
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
]


# =============================================================================
# Handler functions
# =============================================================================


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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail label and filter handlers."""
    return {
        "list_gmail_labels": lambda args: _list_gmail_labels(svc, args),
        "create_gmail_label": lambda args: _create_gmail_label(svc, args),
        "delete_gmail_label": lambda args: _delete_gmail_label(svc, args),
        "list_gmail_filters": lambda args: _list_gmail_filters(svc, args),
        "create_gmail_filter": lambda args: _create_gmail_filter(svc, args),
        "delete_gmail_filter": lambda args: _delete_gmail_filter(svc, args),
    }
