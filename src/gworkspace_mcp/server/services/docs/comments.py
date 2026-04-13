"""Google Docs comments sub-module: list, add, and reply to comments."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DRIVE_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="manage_document_comments",
        description=(
            "Manage comments on a Google Docs, Sheets, or Slides file. Actions: "
            "'list' — list all comments with author, timestamps, resolved status, and replies; "
            "'add' — add a new comment to the file; "
            "'reply' — reply to an existing comment."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "add", "reply"],
                    "description": "Operation to perform on document comments",
                },
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "content": {
                    "type": "string",
                    "description": "Comment or reply text (required for add and reply actions)",
                },
                "comment_id": {
                    "type": "string",
                    "description": "ID of the comment to reply to (required for reply action)",
                },
                "anchor": {
                    "type": "string",
                    "description": "Optional JSON string specifying the anchor location in the document (add action only)",
                },
                "include_deleted": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include deleted comments (list action only)",
                },
                "max_results": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of comments to return (list action only)",
                },
            },
            "required": ["action", "file_id"],
        },
    ),
]


# =============================================================================
# Handler functions
# =============================================================================


async def _manage_document_comments(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Unified handler for comment list, add, and reply operations."""
    action = arguments["action"]
    file_id = arguments["file_id"]

    if action == "list":
        include_deleted = arguments.get("include_deleted", False)
        max_results = arguments.get("max_results", 100)

        url = f"{DRIVE_API_BASE}/files/{file_id}/comments"
        params = {
            "fields": "comments(id,content,author(displayName,emailAddress),createdTime,modifiedTime,resolved,deleted,quotedFileContent,replies(id,content,author(displayName,emailAddress),createdTime,modifiedTime,deleted))",
            "pageSize": min(max_results, 100),
            "includeDeleted": str(include_deleted).lower(),
        }

        response = await svc._make_request("GET", url, params=params)

        comments = response.get("comments", [])
        if not comments:
            return {"comments": [], "count": 0, "message": "No comments found on this document."}

        formatted_comments = []
        for comment in comments:
            author = comment.get("author", {})
            quoted = comment.get("quotedFileContent", {})

            formatted_comment: dict[str, Any] = {
                "id": comment.get("id"),
                "author_name": author.get("displayName", "Unknown"),
                "author_email": author.get("emailAddress", ""),
                "created_time": comment.get("createdTime", ""),
                "modified_time": comment.get("modifiedTime", ""),
                "resolved": comment.get("resolved", False),
                "deleted": comment.get("deleted", False),
                "content": comment.get("content", ""),
            }

            if quoted.get("value"):
                quoted_text = quoted.get("value", "")
                if len(quoted_text) > 200:
                    quoted_text = quoted_text[:200] + "..."
                formatted_comment["quoted_text"] = quoted_text

            replies = comment.get("replies", [])
            if replies:
                formatted_replies = []
                for reply in replies:
                    reply_author = reply.get("author", {})
                    formatted_replies.append(
                        {
                            "id": reply.get("id"),
                            "author_name": reply_author.get("displayName", "Unknown"),
                            "author_email": reply_author.get("emailAddress", ""),
                            "created_time": reply.get("createdTime", ""),
                            "modified_time": reply.get("modifiedTime", ""),
                            "deleted": reply.get("deleted", False),
                            "content": reply.get("content", ""),
                        }
                    )
                formatted_comment["replies"] = formatted_replies
                formatted_comment["reply_count"] = len(formatted_replies)

            formatted_comments.append(formatted_comment)

        return {"comments": formatted_comments, "count": len(formatted_comments)}

    if action == "add":
        content = arguments.get("content")
        if not content:
            return {"error": "content is required for add action"}
        anchor = arguments.get("anchor")

        url = f"{DRIVE_API_BASE}/files/{file_id}/comments"
        params = {
            "fields": "id,content,author(displayName,emailAddress),createdTime,modifiedTime,resolved",
        }

        body: dict[str, Any] = {"content": content}
        if anchor:
            try:
                body["anchor"] = json.loads(anchor) if isinstance(anchor, str) else anchor
            except json.JSONDecodeError:
                body["anchor"] = anchor

        response = await svc._make_request("POST", url, params=params, json_data=body)

        author = response.get("author", {})
        return {
            "id": response.get("id"),
            "content": response.get("content", ""),
            "author_name": author.get("displayName", "Unknown"),
            "author_email": author.get("emailAddress", ""),
            "created_time": response.get("createdTime", ""),
            "modified_time": response.get("modifiedTime", ""),
            "resolved": response.get("resolved", False),
            "message": "Comment added successfully.",
        }

    if action == "reply":
        comment_id = arguments.get("comment_id")
        content = arguments.get("content")
        if not comment_id:
            return {"error": "comment_id is required for reply action"}
        if not content:
            return {"error": "content is required for reply action"}

        url = f"{DRIVE_API_BASE}/files/{file_id}/comments/{comment_id}/replies"
        params = {
            "fields": "id,content,author(displayName,emailAddress),createdTime,modifiedTime",
        }
        body = {"content": content}

        response = await svc._make_request("POST", url, params=params, json_data=body)

        author = response.get("author", {})
        return {
            "id": response.get("id"),
            "content": response.get("content", ""),
            "author_name": author.get("displayName", "Unknown"),
            "author_email": author.get("emailAddress", ""),
            "created_time": response.get("createdTime", ""),
            "modified_time": response.get("modifiedTime", ""),
            "comment_id": comment_id,
            "message": "Reply added successfully.",
        }

    return {"error": f"Unknown action '{action}'. Valid actions: list, add, reply"}


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs comment handlers."""
    return {
        "manage_document_comments": lambda args: _manage_document_comments(svc, args),
    }
