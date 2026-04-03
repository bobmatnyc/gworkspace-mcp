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
        name="list_document_comments",
        description="List all comments on a Google Docs, Sheets, or Slides file. Returns comment content, author, timestamps, resolved status, and replies.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "include_deleted": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include deleted comments",
                },
                "max_results": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of comments to return",
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="add_document_comment",
        description="Add a new comment to a Google Docs, Sheets, or Slides file. Comments appear in the document's comment sidebar. Write concise, actionable comments.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "content": {
                    "type": "string",
                    "description": "The comment text.",
                },
                "anchor": {
                    "type": "string",
                    "description": "Optional JSON string specifying the anchor location in the document (for anchored comments)",
                },
            },
            "required": ["file_id", "content"],
        },
    ),
    Tool(
        name="reply_to_comment",
        description="Reply to an existing comment on a Google Docs, Sheets, or Slides file.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Google Drive file ID (from the document URL)",
                },
                "comment_id": {
                    "type": "string",
                    "description": "The ID of the comment to reply to (from list_document_comments)",
                },
                "content": {
                    "type": "string",
                    "description": "The reply text.",
                },
            },
            "required": ["file_id", "comment_id", "content"],
        },
    ),
]


# =============================================================================
# Handler functions
# =============================================================================


async def _list_document_comments(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    file_id = arguments["file_id"]
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


async def _add_document_comment(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    file_id = arguments["file_id"]
    content = arguments["content"]
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


async def _reply_to_comment(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    file_id = arguments["file_id"]
    comment_id = arguments["comment_id"]
    content = arguments["content"]

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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs comment handlers."""
    return {
        "list_document_comments": lambda args: _list_document_comments(svc, args),
        "add_document_comment": lambda args: _add_document_comment(svc, args),
        "reply_to_comment": lambda args: _reply_to_comment(svc, args),
    }
