"""Google Tasks service module for MCP server."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import TASKS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="manage_task_lists",
        description=(
            "Manage Google Tasks task lists. "
            "Actions: 'list' (max_results optional), 'get' (tasklist_id required), "
            "'create' (title required), 'update' (tasklist_id and title required), "
            "'delete' (tasklist_id required)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": ["list", "get", "create", "update", "delete"],
                },
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (required for get, update, delete)",
                },
                "title": {
                    "type": "string",
                    "description": "Task list title (required for create; optional for update)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of task lists to return (list only, default: 100)",
                    "default": 100,
                },
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="manage_tasks",
        description=(
            "Manage Google Tasks. "
            "Actions: 'list' (tasklist_id optional, defaults to @default; show_completed, due_min, due_max, max_results optional), "
            "'get' (task_id required; tasklist_id optional), "
            "'search' (query required; searches titles and notes across all lists), "
            "'create' (title required; tasklist_id, notes, due, parent optional), "
            "'update' (task_id required; title, notes, due, status optional), "
            "'complete' (task_id required), 'delete' (task_id required), "
            "'move' (task_id required; parent and previous optional for repositioning)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": [
                        "list",
                        "get",
                        "search",
                        "create",
                        "update",
                        "complete",
                        "delete",
                        "move",
                    ],
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID (required for get, update, complete, delete, move)",
                },
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (optional, defaults to '@default')",
                    "default": "@default",
                },
                "title": {
                    "type": "string",
                    "description": "Task title (required for create; optional for update)",
                },
                "notes": {
                    "type": "string",
                    "description": "Task notes/description (optional)",
                },
                "due": {
                    "type": "string",
                    "description": "Due date in RFC3339 format, e.g. '2024-01-15T00:00:00Z' (optional)",
                },
                "status": {
                    "type": "string",
                    "description": "Task status: 'needsAction' or 'completed' (update only)",
                    "enum": ["needsAction", "completed"],
                },
                "parent": {
                    "type": "string",
                    "description": "Parent task ID for subtasks (create or move only)",
                },
                "previous": {
                    "type": "string",
                    "description": "Task ID to position this task after (move only)",
                },
                "query": {
                    "type": "string",
                    "description": "Search string matched against task titles and notes (required for search)",
                },
                "show_completed": {
                    "type": "boolean",
                    "description": "Include completed tasks (list and search only, default: true)",
                    "default": True,
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Include hidden tasks (list only, default: false)",
                    "default": False,
                },
                "due_min": {
                    "type": "string",
                    "description": "Lower bound for due date in RFC3339 format (list only)",
                },
                "due_max": {
                    "type": "string",
                    "description": "Upper bound for due date in RFC3339 format (list only)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return (list only, default: 100)",
                    "default": 100,
                },
            },
            "required": ["action"],
        },
    ),
]


def _format_task(item: dict[str, Any]) -> dict[str, Any]:
    """Format a task item for consistent output.

    Args:
        item: Raw task data from API.

    Returns:
        Formatted task dictionary.
    """
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "notes": item.get("notes"),
        "status": item.get("status"),
        "due": item.get("due"),
        "completed": item.get("completed"),
        "parent": item.get("parent"),
        "position": item.get("position"),
        "updated": item.get("updated"),
        "deleted": item.get("deleted", False),
        "hidden": item.get("hidden", False),
    }


async def _list_task_lists(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all task lists for the user."""
    max_results = arguments.get("max_results", 100)
    url = f"{TASKS_API_BASE}/users/@me/lists"
    params = {"maxResults": max_results}
    response = await svc._make_request("GET", url, params=params)
    task_lists = []
    for item in response.get("items", []):
        task_lists.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "updated": item.get("updated"),
                "self_link": item.get("selfLink"),
            }
        )
    return {"task_lists": task_lists, "count": len(task_lists)}


async def _get_task_list(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get a specific task list by ID."""
    tasklist_id = arguments["tasklist_id"]
    url = f"{TASKS_API_BASE}/users/@me/lists/{tasklist_id}"
    response = await svc._make_request("GET", url)
    return {
        "id": response.get("id"),
        "title": response.get("title"),
        "updated": response.get("updated"),
        "self_link": response.get("selfLink"),
    }


async def _create_task_list(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new task list."""
    title = arguments["title"]
    url = f"{TASKS_API_BASE}/users/@me/lists"
    response = await svc._make_request("POST", url, json_data={"title": title})
    return {
        "status": "created",
        "id": response.get("id"),
        "title": response.get("title"),
        "updated": response.get("updated"),
    }


async def _update_task_list(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update an existing task list."""
    tasklist_id = arguments["tasklist_id"]
    title = arguments["title"]
    url = f"{TASKS_API_BASE}/users/@me/lists/{tasklist_id}"
    response = await svc._make_request("PATCH", url, json_data={"title": title})
    return {
        "status": "updated",
        "id": response.get("id"),
        "title": response.get("title"),
        "updated": response.get("updated"),
    }


async def _delete_task_list(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a task list."""
    tasklist_id = arguments["tasklist_id"]
    url = f"{TASKS_API_BASE}/users/@me/lists/{tasklist_id}"
    await svc._make_delete_request(url)
    return {"status": "deleted", "tasklist_id": tasklist_id}


async def _list_tasks(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List all tasks in a task list."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    show_completed = arguments.get("show_completed", True)
    show_hidden = arguments.get("show_hidden", False)
    due_min = arguments.get("due_min")
    due_max = arguments.get("due_max")
    max_results = arguments.get("max_results", 100)

    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"
    params: dict[str, Any] = {
        "maxResults": max_results,
        "showCompleted": str(show_completed).lower(),
        "showHidden": str(show_hidden).lower(),
    }
    if due_min:
        params["dueMin"] = due_min
    if due_max:
        params["dueMax"] = due_max

    response = await svc._make_request("GET", url, params=params)
    tasks = [_format_task(item) for item in response.get("items", [])]
    return {"tasks": tasks, "count": len(tasks)}


async def _get_task(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get a specific task by ID."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    task_id = arguments["task_id"]
    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"
    response = await svc._make_request("GET", url)
    return _format_task(response)


async def _search_tasks(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search tasks across all task lists by title or notes."""
    query = arguments["query"].lower()
    show_completed = arguments.get("show_completed", True)

    lists_url = f"{TASKS_API_BASE}/users/@me/lists"
    lists_response = await svc._make_request("GET", lists_url)
    task_lists = lists_response.get("items", [])

    async def _search_single_list(tasklist_id: str, tasklist_title: str) -> list[dict[str, Any]]:
        tasks_url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"
        params: dict[str, Any] = {
            "showCompleted": str(show_completed).lower(),
            "maxResults": 100,
        }
        tasks_response = await svc._make_request("GET", tasks_url, params=params)
        matches: list[dict[str, Any]] = []
        for task in tasks_response.get("items", []):
            title = task.get("title", "").lower()
            notes = task.get("notes", "").lower()
            if query in title or query in notes:
                formatted = _format_task(task)
                formatted["tasklist_id"] = tasklist_id
                formatted["tasklist_title"] = tasklist_title
                matches.append(formatted)
        return matches

    results = await asyncio.gather(
        *[_search_single_list(tl.get("id", ""), tl.get("title", "")) for tl in task_lists],
        return_exceptions=True,
    )

    matching_tasks: list[dict[str, Any]] = []
    for result in results:
        if not isinstance(result, BaseException):
            matching_tasks.extend(result)

    return {"tasks": matching_tasks, "count": len(matching_tasks), "query": query}


async def _create_task(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new task in a task list."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    title = arguments["title"]
    notes = arguments.get("notes")
    due = arguments.get("due")
    parent = arguments.get("parent")

    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"
    task_body: dict[str, Any] = {"title": title}
    if notes:
        task_body["notes"] = notes
    if due:
        task_body["due"] = due

    params = {}
    if parent:
        params["parent"] = parent

    response = await svc._make_request(
        "POST", url, params=params if params else None, json_data=task_body
    )
    result = _format_task(response)
    result["status"] = "created"
    return result


async def _update_task(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update an existing task."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    task_id = arguments["task_id"]

    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"
    update_body: dict[str, Any] = {}
    if "title" in arguments:
        update_body["title"] = arguments["title"]
    if "notes" in arguments:
        update_body["notes"] = arguments["notes"]
    if "due" in arguments:
        update_body["due"] = arguments["due"]
    if "status" in arguments:
        update_body["status"] = arguments["status"]

    response = await svc._make_request("PATCH", url, json_data=update_body)
    result = _format_task(response)
    result["update_status"] = "updated"
    return result


async def _complete_task(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Mark a task as completed."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    task_id = arguments["task_id"]
    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"
    response = await svc._make_request("PATCH", url, json_data={"status": "completed"})
    result = _format_task(response)
    result["update_status"] = "completed"
    return result


async def _delete_task(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a task."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    task_id = arguments["task_id"]
    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"
    await svc._make_delete_request(url)
    return {"status": "deleted", "task_id": task_id, "tasklist_id": tasklist_id}


async def _move_task(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Move a task to a different position or make it a subtask."""
    tasklist_id = arguments.get("tasklist_id", "@default")
    task_id = arguments["task_id"]
    parent = arguments.get("parent")
    previous = arguments.get("previous")

    url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}/move"
    params: dict[str, Any] = {}
    if parent:
        params["parent"] = parent
    if previous:
        params["previous"] = previous

    response = await svc._make_request("POST", url, params=params if params else None)
    result = _format_task(response)
    result["move_status"] = "moved"
    return result


async def _manage_task_lists(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch manage_task_lists actions."""
    action = arguments["action"]
    if action == "list":
        return await _list_task_lists(svc, arguments)
    if action == "get":
        if "tasklist_id" not in arguments:
            raise ValueError("tasklist_id is required for action 'get'")
        return await _get_task_list(svc, arguments)
    if action == "create":
        if "title" not in arguments:
            raise ValueError("title is required for action 'create'")
        return await _create_task_list(svc, arguments)
    if action == "update":
        if "tasklist_id" not in arguments:
            raise ValueError("tasklist_id is required for action 'update'")
        if "title" not in arguments:
            raise ValueError("title is required for action 'update'")
        return await _update_task_list(svc, arguments)
    if action == "delete":
        if "tasklist_id" not in arguments:
            raise ValueError("tasklist_id is required for action 'delete'")
        return await _delete_task_list(svc, arguments)
    raise ValueError(f"Unknown action '{action}' for manage_task_lists")


async def _manage_tasks(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch manage_tasks actions."""
    action = arguments["action"]
    if action == "list":
        return await _list_tasks(svc, arguments)
    if action == "get":
        if "task_id" not in arguments:
            raise ValueError("task_id is required for action 'get'")
        return await _get_task(svc, arguments)
    if action == "search":
        if "query" not in arguments:
            raise ValueError("query is required for action 'search'")
        return await _search_tasks(svc, arguments)
    if action == "create":
        if "title" not in arguments:
            raise ValueError("title is required for action 'create'")
        return await _create_task(svc, arguments)
    if action == "update":
        if "task_id" not in arguments:
            raise ValueError("task_id is required for action 'update'")
        return await _update_task(svc, arguments)
    if action == "complete":
        if "task_id" not in arguments:
            raise ValueError("task_id is required for action 'complete'")
        return await _complete_task(svc, arguments)
    if action == "delete":
        if "task_id" not in arguments:
            raise ValueError("task_id is required for action 'delete'")
        return await _delete_task(svc, arguments)
    if action == "move":
        if "task_id" not in arguments:
            raise ValueError("task_id is required for action 'move'")
        return await _move_task(svc, arguments)
    raise ValueError(f"Unknown action '{action}' for manage_tasks")


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all tasks tool handlers.

    Args:
        svc: BaseService instance providing HTTP helpers.

    Returns:
        Dictionary mapping tool names to async callables.
    """
    return {
        "manage_task_lists": lambda args: _manage_task_lists(svc, args),
        "manage_tasks": lambda args: _manage_tasks(svc, args),
    }
