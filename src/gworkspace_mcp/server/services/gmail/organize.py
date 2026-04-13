"""Gmail message organisation sub-module: modify labels, archive, trash, star, read/unread."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="modify_gmail_messages",
        description=(
            "Modify one or more Gmail messages. Accepts a single message ID (string) or a list. "
            "Actions: 'archive' (remove INBOX), 'trash' (move to trash), 'untrash' (restore from trash), "
            "'mark_read' (remove UNREAD), 'mark_unread' (add UNREAD), 'star' (add STARRED), "
            "'unstar' (remove STARRED), 'label' (add/remove arbitrary label IDs). "
            "Batch operations use Gmail's batchModify API for efficiency."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "archive",
                        "trash",
                        "untrash",
                        "mark_read",
                        "mark_unread",
                        "star",
                        "unstar",
                        "label",
                    ],
                    "description": "Operation to perform on the message(s)",
                },
                "message_ids": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                    ],
                    "description": "Message ID (string) or list of message IDs to modify",
                },
                "add_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to add (used with action=label)",
                },
                "remove_label_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Label IDs to remove (used with action=label)",
                },
            },
            "required": ["action", "message_ids"],
        },
    ),
]


# =============================================================================
# Handler functions
# =============================================================================


async def _modify_gmail_messages(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Modify one or more Gmail messages based on the requested action."""
    action = arguments["action"]
    raw_ids = arguments["message_ids"]

    # Normalize message_ids to list
    message_ids: list[str] = [raw_ids] if isinstance(raw_ids, str) else list(raw_ids)

    if not message_ids:
        return {"status": "no_messages", "message": "No message IDs provided", "count": 0}

    count = len(message_ids)

    # -------------------------------------------------------------------------
    # Actions that use individual per-message endpoints (trash / untrash)
    # -------------------------------------------------------------------------
    if action in ("trash", "untrash"):
        endpoint = "trash" if action == "trash" else "untrash"

        async def _call_individual(msg_id: str) -> tuple[str, bool]:
            try:
                url = f"{GMAIL_API_BASE}/users/me/messages/{msg_id}/{endpoint}"
                await svc._make_request("POST", url)
                return msg_id, True
            except Exception:
                return msg_id, False

        results = await asyncio.gather(
            *[_call_individual(mid) for mid in message_ids], return_exceptions=True
        )

        success_count = sum(1 for r in results if isinstance(r, tuple) and r[1])
        failed_count = count - success_count
        status = "messages_trashed" if action == "trash" else "messages_untrashed"
        return {"status": status, "success_count": success_count, "failed_count": failed_count}

    # -------------------------------------------------------------------------
    # Actions that map to batchModify label operations
    # -------------------------------------------------------------------------
    action_label_map: dict[str, tuple[list[str], list[str]]] = {
        "archive": ([], ["INBOX"]),
        "mark_read": ([], ["UNREAD"]),
        "mark_unread": (["UNREAD"], []),
        "star": (["STARRED"], []),
        "unstar": ([], ["STARRED"]),
    }

    if action in action_label_map:
        add_ids, remove_ids = action_label_map[action]
    else:
        # action == "label"
        add_ids = arguments.get("add_label_ids", [])
        remove_ids = arguments.get("remove_label_ids", [])

    batch_body: dict[str, Any] = {"ids": message_ids}
    if add_ids:
        batch_body["addLabelIds"] = add_ids
    if remove_ids:
        batch_body["removeLabelIds"] = remove_ids

    url = f"{GMAIL_API_BASE}/users/me/messages/batchModify"
    await svc._make_request("POST", url, json_data=batch_body)

    status_map = {
        "archive": "messages_archived",
        "mark_read": "messages_marked_read",
        "mark_unread": "messages_marked_unread",
        "star": "messages_starred",
        "unstar": "messages_unstarred",
        "label": "messages_labeled",
    }

    return {
        "status": status_map.get(action, "messages_modified"),
        "count": count,
        "add_label_ids": add_ids,
        "remove_label_ids": remove_ids,
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail organisation handlers."""
    return {
        "modify_gmail_messages": lambda args: _modify_gmail_messages(svc, args),
    }
