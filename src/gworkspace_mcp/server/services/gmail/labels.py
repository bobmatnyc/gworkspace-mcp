"""Gmail labels and filters sub-module."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="manage_gmail_labels",
        description=(
            "Manage Gmail labels. "
            "Actions: 'list' (list all labels), 'create' (create a new label), 'delete' (delete a label by ID)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create", "delete"],
                    "description": "Operation to perform",
                },
                "name": {
                    "type": "string",
                    "description": "Label name for action=create (use '/' for nesting, e.g., 'Work/Projects')",
                },
                "label_id": {
                    "type": "string",
                    "description": "Label ID for action=delete",
                },
                "label_list_visibility": {
                    "type": "string",
                    "enum": ["labelShow", "labelShowIfUnread", "labelHide"],
                    "description": "Visibility in label list for action=create (default: labelShow)",
                },
                "message_list_visibility": {
                    "type": "string",
                    "enum": ["show", "hide"],
                    "description": "Visibility in message list for action=create (default: show)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="manage_gmail_filters",
        description=(
            "Manage Gmail filters (auto-filtering rules). "
            "Actions: 'list' (list all filters), 'create' (create a new filter), 'delete' (delete a filter by ID)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create", "delete"],
                    "description": "Operation to perform",
                },
                "filter_id": {
                    "type": "string",
                    "description": "Filter ID for action=delete",
                },
                "from_address": {
                    "type": "string",
                    "description": "Filter by sender email address (for action=create)",
                },
                "to_address": {
                    "type": "string",
                    "description": "Filter by recipient email address (for action=create)",
                },
                "subject": {
                    "type": "string",
                    "description": "Filter by subject contains text (for action=create)",
                },
                "query": {
                    "type": "string",
                    "description": "Gmail search query for advanced filtering, e.g., 'has:attachment larger:5M' (for action=create)",
                },
                "has_attachment": {
                    "type": "boolean",
                    "description": "Filter messages with attachments (for action=create)",
                },
                "add_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to add to matching messages (for action=create)",
                },
                "remove_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to remove from matching messages, use 'INBOX' to archive (for action=create)",
                },
                "mark_as_read": {
                    "type": "boolean",
                    "description": "Mark matching messages as read (for action=create)",
                },
                "star": {
                    "type": "boolean",
                    "description": "Star matching messages (for action=create)",
                },
                "forward_to": {
                    "type": "string",
                    "description": "Forward matching messages to this email address (for action=create)",
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
# Handler functions
# =============================================================================


async def _manage_gmail_labels(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Manage Gmail labels: list, create, or delete."""
    action = arguments["action"]

    if action == "list":
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
        user_labels = sorted(
            [lbl for lbl in labels if lbl["type"] == "user"], key=lambda x: x["name"]
        )

        return {
            "total": len(labels),
            "system_labels": system_labels,
            "user_labels": user_labels,
        }

    if action == "create":
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

    # action == "delete"
    label_id = arguments["label_id"]
    url = f"{GMAIL_API_BASE}/users/me/labels/{label_id}"
    await svc._make_delete_request(url)

    return {"status": "label_deleted", "label_id": label_id}


async def _manage_gmail_filters(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Manage Gmail filters: list, create, or delete."""
    action = arguments["action"]

    if action == "list":
        url = f"{GMAIL_API_BASE}/users/me/settings/filters"
        response = await svc._make_request("GET", url)

        filters = []
        for f in response.get("filter", []):
            criteria = f.get("criteria", {})
            action_data = f.get("action", {})

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
                        "add_label_ids": action_data.get("addLabelIds", []),
                        "remove_label_ids": action_data.get("removeLabelIds", []),
                        "forward": action_data.get("forward"),
                    },
                }
            )

        return {"total": len(filters), "filters": filters}

    if action == "create":
        filter_criteria: dict[str, Any] = {}
        if from_addr := arguments.get("from_address"):
            filter_criteria["from"] = from_addr
        if to_addr := arguments.get("to_address"):
            filter_criteria["to"] = to_addr
        if subject := arguments.get("subject"):
            filter_criteria["subject"] = subject
        if query := arguments.get("query"):
            filter_criteria["query"] = query
        if arguments.get("has_attachment"):
            filter_criteria["hasAttachment"] = True

        filter_action: dict[str, Any] = {}
        if add_labels := arguments.get("add_label_ids"):
            filter_action["addLabelIds"] = add_labels
        if remove_labels := arguments.get("remove_label_ids"):
            filter_action["removeLabelIds"] = remove_labels
        if arguments.get("mark_as_read"):
            filter_action.setdefault("removeLabelIds", []).append("UNREAD")
        if arguments.get("star"):
            filter_action.setdefault("addLabelIds", []).append("STARRED")
        if forward_to := arguments.get("forward_to"):
            filter_action["forward"] = forward_to

        filter_body = {"criteria": filter_criteria, "action": filter_action}

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

    # action == "delete"
    filter_id = arguments["filter_id"]
    url = f"{GMAIL_API_BASE}/users/me/settings/filters/{filter_id}"
    await svc._make_delete_request(url)

    return {"status": "filter_deleted", "filter_id": filter_id}


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail label and filter handlers."""
    return {
        "manage_gmail_labels": lambda args: _manage_gmail_labels(svc, args),
        "manage_gmail_filters": lambda args: _manage_gmail_filters(svc, args),
    }
