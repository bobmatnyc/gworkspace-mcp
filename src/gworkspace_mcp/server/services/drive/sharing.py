"""Google Drive sharing sub-module: permissions and ownership."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DRIVE_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="manage_file_permissions",
        description=(
            "List, share, update, remove, or transfer ownership of permissions on a "
            "Google Drive file or folder. Use action='list' to see who has access, "
            "'share' to grant access, 'update' to change a permission's role, "
            "'remove' to revoke access, or 'transfer' to change ownership."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "share", "update", "remove", "transfer"],
                    "description": (
                        "Operation to perform: list (get all permissions), "
                        "share (grant access), update (change role), "
                        "remove (revoke access), transfer (change owner)"
                    ),
                },
                "file_id": {
                    "type": "string",
                    "description": "ID of the file or folder",
                },
                "permission_id": {
                    "type": "string",
                    "description": "Permission ID (required for update and remove actions; from list action)",
                },
                "type": {
                    "type": "string",
                    "enum": ["user", "group", "domain", "anyone"],
                    "description": (
                        "Type of grantee (share action only): user (individual), "
                        "group (Google Group), domain (all users in domain), "
                        "anyone (public link)"
                    ),
                },
                "role": {
                    "type": "string",
                    "enum": [
                        "owner",
                        "organizer",
                        "fileOrganizer",
                        "writer",
                        "commenter",
                        "reader",
                    ],
                    "description": (
                        "Permission level (share and update actions): "
                        "reader (view only), commenter, writer (edit), "
                        "fileOrganizer, organizer, owner"
                    ),
                },
                "email_address": {
                    "type": "string",
                    "description": "Email address of the user or group (share action for user/group type; also used for transfer)",
                },
                "domain": {
                    "type": "string",
                    "description": "Domain name (share action for domain type, e.g., 'company.com')",
                },
                "send_notification": {
                    "type": "boolean",
                    "description": "Send email notification to the user (share action only, default: true)",
                    "default": True,
                },
                "new_owner_email": {
                    "type": "string",
                    "description": "Email address of the new owner (transfer action only)",
                },
            },
            "required": ["action", "file_id"],
        },
    ),
]


# =============================================================================
# Helper functions
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
    perm_type = arguments.get("type")
    role = arguments.get("role")
    email_address = arguments.get("email_address")
    domain = arguments.get("domain")
    send_notification = arguments.get("send_notification", True)

    if not perm_type:
        return {"error": "type is required for share action (user, group, domain, or anyone)"}
    if not role:
        return {"error": "role is required for share action"}
    if perm_type in ("user", "group") and not email_address:
        return {"error": f"email_address is required for type '{perm_type}'"}
    if perm_type == "domain" and not domain:
        return {"error": "domain is required for type 'domain'"}

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
    permission_id = arguments.get("permission_id")
    role = arguments.get("role")

    if not permission_id:
        return {"error": "permission_id is required for update action"}
    if not role:
        return {"error": "role is required for update action"}

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
    permission_id = arguments.get("permission_id")

    if not permission_id:
        return {"error": "permission_id is required for remove action"}

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
    new_owner_email = arguments.get("new_owner_email") or arguments.get("email_address")

    if not new_owner_email:
        return {"error": "new_owner_email is required for transfer action"}

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


# =============================================================================
# Dispatcher
# =============================================================================


async def _manage_file_permissions(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch to the appropriate permissions handler based on action."""
    action = arguments.get("action")
    if action == "list":
        return await _list_file_permissions(svc, arguments)
    elif action == "share":
        return await _share_file(svc, arguments)
    elif action == "update":
        return await _update_file_permission(svc, arguments)
    elif action == "remove":
        return await _remove_file_permission(svc, arguments)
    elif action == "transfer":
        return await _transfer_file_ownership(svc, arguments)
    else:
        return {
            "error": (
                f"Unknown action '{action}'. Must be one of: list, share, update, remove, transfer."
            )
        }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Drive sharing handlers."""
    return {
        "manage_file_permissions": lambda args: _manage_file_permissions(svc, args),
    }
