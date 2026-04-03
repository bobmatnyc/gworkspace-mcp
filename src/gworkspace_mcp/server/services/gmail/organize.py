"""Gmail message organisation sub-module: modify, archive, trash, read/unread, star, batch."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import GMAIL_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
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
]


# =============================================================================
# Handler functions
# =============================================================================


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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Gmail organisation handlers."""
    return {
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
    }
