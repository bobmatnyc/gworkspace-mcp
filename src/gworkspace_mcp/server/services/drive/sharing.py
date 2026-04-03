"""Google Drive sharing sub-module: permissions and ownership."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DRIVE_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="list_file_permissions",
        description="List all permissions (who has access) for a Google Drive file or folder",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
            },
            "required": ["file_id"],
        },
    ),
    Tool(
        name="share_file",
        description="Share a Drive file or folder with a user, group, domain, or make it public (anyone with link)",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder to share",
                },
                "type": {
                    "type": "string",
                    "enum": ["user", "group", "domain", "anyone"],
                    "description": "Type of grantee: user (individual), group (Google Group), domain (all users in domain), anyone (public link)",
                },
                "role": {
                    "type": "string",
                    "enum": ["reader", "writer", "commenter"],
                    "description": "Permission level: reader (view only), writer (can edit), commenter (can comment)",
                },
                "email_address": {
                    "type": "string",
                    "description": "Email address (required for user/group type)",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain name (required for domain type, e.g., 'company.com')",
                },
                "send_notification": {
                    "type": "boolean",
                    "description": "Send email notification to the user (default: true, only for user/group type)",
                    "default": True,
                },
            },
            "required": ["file_id", "type", "role"],
        },
    ),
    Tool(
        name="update_file_permission",
        description="Update an existing permission's role on a Drive file or folder",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
                "permission_id": {
                    "type": "string",
                    "description": "Permission ID to update (from list_file_permissions)",
                },
                "role": {
                    "type": "string",
                    "enum": ["reader", "writer", "commenter"],
                    "description": "New permission level",
                },
            },
            "required": ["file_id", "permission_id", "role"],
        },
    ),
    Tool(
        name="remove_file_permission",
        description="Remove a permission (revoke access) from a Drive file or folder",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
                "permission_id": {
                    "type": "string",
                    "description": "Permission ID to remove (from list_file_permissions)",
                },
            },
            "required": ["file_id", "permission_id"],
        },
    ),
    Tool(
        name="transfer_file_ownership",
        description="Transfer ownership of a Drive file to another user. The current owner becomes a writer. Only works for files you own.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "ID of the file to transfer ownership",
                },
                "new_owner_email": {
                    "type": "string",
                    "description": "Email address of the new owner",
                },
            },
            "required": ["file_id", "new_owner_email"],
        },
    ),
]


# =============================================================================
# Handler functions
# =============================================================================


async def _list_file_permissions(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all permissions for a Drive file or folder."""
    file_id = arguments["file_id"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    response = await svc._make_request("GET", url, params={"fields": "*"})

    permissions = []
    for perm in response.get("permissions", []):
        perm_info: dict[str, Any] = {
            "permission_id": perm.get("id"),
            "type": perm.get("type"),
            "role": perm.get("role"),
        }
        if perm.get("emailAddress"):
            perm_info["email_address"] = perm.get("emailAddress")
        if perm.get("displayName"):
            perm_info["display_name"] = perm.get("displayName")
        if perm.get("domain"):
            perm_info["domain"] = perm.get("domain")
        permissions.append(perm_info)

    return {
        "status": "success",
        "file_id": file_id,
        "permissions": permissions,
        "count": len(permissions),
    }


async def _share_file(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Share a Drive file or folder with a user, group, domain, or anyone."""
    file_id = arguments["file_id"]
    perm_type = arguments["type"]
    role = arguments["role"]
    email_address = arguments.get("email_address")
    domain = arguments.get("domain")
    send_notification = arguments.get("send_notification", True)

    if perm_type in ("user", "group") and not email_address:
        return {
            "status": "error",
            "error": f"email_address is required for type '{perm_type}'",
        }
    if perm_type == "domain" and not domain:
        return {
            "status": "error",
            "error": "domain is required for type 'domain'",
        }

    permission: dict[str, Any] = {
        "type": perm_type,
        "role": role,
    }
    if email_address:
        permission["emailAddress"] = email_address
    if domain:
        permission["domain"] = domain

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    params = {"sendNotificationEmail": str(send_notification).lower()}

    response = await svc._make_request("POST", url, params=params, json_data=permission)

    result: dict[str, Any] = {
        "status": "shared",
        "file_id": file_id,
        "permission_id": response.get("id"),
        "type": response.get("type"),
        "role": response.get("role"),
    }
    if response.get("emailAddress"):
        result["email_address"] = response.get("emailAddress")
    if response.get("domain"):
        result["domain"] = response.get("domain")

    return result


async def _update_file_permission(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update an existing permission's role on a Drive file."""
    file_id = arguments["file_id"]
    permission_id = arguments["permission_id"]
    role = arguments["role"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions/{permission_id}"
    response = await svc._make_request("PATCH", url, json_data={"role": role})

    return {
        "status": "updated",
        "file_id": file_id,
        "permission_id": response.get("id"),
        "role": response.get("role"),
        "type": response.get("type"),
    }


async def _remove_file_permission(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Remove a permission from a Drive file or folder."""
    file_id = arguments["file_id"]
    permission_id = arguments["permission_id"]

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions/{permission_id}"
    await svc._make_delete_request(url)

    return {
        "status": "removed",
        "file_id": file_id,
        "permission_id": permission_id,
    }


async def _transfer_file_ownership(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Transfer ownership of a Drive file to another user."""
    file_id = arguments["file_id"]
    new_owner_email = arguments["new_owner_email"]

    permission = {
        "type": "user",
        "role": "owner",
        "emailAddress": new_owner_email,
    }

    url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
    response = await svc._make_request(
        "POST", url, params={"transferOwnership": "true"}, json_data=permission
    )

    return {
        "status": "ownership_transferred",
        "file_id": file_id,
        "new_owner": new_owner_email,
        "permission_id": response.get("id"),
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Drive sharing handlers."""
    return {
        "list_file_permissions": lambda args: _list_file_permissions(svc, args),
        "share_file": lambda args: _share_file(svc, args),
        "update_file_permission": lambda args: _update_file_permission(svc, args),
        "remove_file_permission": lambda args: _remove_file_permission(svc, args),
        "transfer_file_ownership": lambda args: _transfer_file_ownership(svc, args),
    }
