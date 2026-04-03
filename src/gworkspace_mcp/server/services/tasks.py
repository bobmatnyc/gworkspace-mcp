"""Google Tasks service module for MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import TASKS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    # Google Tasks API - Task Lists Operations
    Tool(
        name="list_task_lists",
        description="List all task lists for the authenticated user",
        inputSchema={
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of task lists to return (default: 100)",
                    "default": 100,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_task_list",
        description="Get a specific task list by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID",
                },
            },
            "required": ["tasklist_id"],
        },
    ),
    Tool(
        name="create_task_list",
        description="Create a new task list",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the new task list",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="update_task_list",
        description="Update an existing task list",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title for the task list",
                },
            },
            "required": ["tasklist_id", "title"],
        },
    ),
    Tool(
        name="delete_task_list",
        description="Delete a task list",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID to delete",
                },
            },
            "required": ["tasklist_id"],
        },
    ),
    # Google Tasks API - Tasks Operations
    Tool(
        name="list_tasks",
        description="List all tasks in a task list",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default' for the default list)",
                    "default": "@default",
                },
                "show_completed": {
                    "type": "boolean",
                    "description": "Include completed tasks (default: true)",
                    "default": True,
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "Include hidden tasks (default: false)",
                    "default": False,
                },
                "due_min": {
                    "type": "string",
                    "description": "Lower bound for due date (RFC3339 format)",
                },
                "due_max": {
                    "type": "string",
                    "description": "Upper bound for due date (RFC3339 format)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of tasks to return (default: 100)",
                    "default": 100,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_task",
        description="Get a specific task by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default')",
                    "default": "@default",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="search_tasks",
        description="Search tasks across all task lists by title or notes content",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to match against task titles and notes",
                },
                "show_completed": {
                    "type": "boolean",
                    "description": "Include completed tasks in search (default: true)",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="create_task",
        description="Create a new task in a task list",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default')",
                    "default": "@default",
                },
                "title": {
                    "type": "string",
                    "description": "Task title",
                },
                "notes": {
                    "type": "string",
                    "description": "Task notes/description",
                },
                "due": {
                    "type": "string",
                    "description": "Due date in RFC3339 format (e.g., '2024-01-15T00:00:00Z')",
                },
                "parent": {
                    "type": "string",
                    "description": "Parent task ID for creating subtasks",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="update_task",
        description="Update an existing task",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default')",
                    "default": "@default",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID to update",
                },
                "title": {
                    "type": "string",
                    "description": "New task title",
                },
                "notes": {
                    "type": "string",
                    "description": "New task notes/description",
                },
                "due": {
                    "type": "string",
                    "description": "New due date in RFC3339 format",
                },
                "status": {
                    "type": "string",
                    "description": "Task status: 'needsAction' or 'completed'",
                    "enum": ["needsAction", "completed"],
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="complete_task",
        description="Mark a task as completed",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default')",
                    "default": "@default",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID to complete",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="delete_task",
        description="Delete a task",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default')",
                    "default": "@default",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID to delete",
                },
            },
            "required": ["task_id"],
        },
    ),
    Tool(
        name="move_task",
        description="Move a task to a different position or make it a subtask",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_id": {
                    "type": "string",
                    "description": "Task list ID (default: '@default')",
                    "default": "@default",
                },
                "task_id": {
                    "type": "string",
                    "description": "Task ID to move",
                },
                "parent": {
                    "type": "string",
                    "description": "New parent task ID (to make this task a subtask)",
                },
                "previous": {
                    "type": "string",
                    "description": "Task ID to position this task after",
                },
            },
            "required": ["task_id"],
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

    matching_tasks = []
    for task_list in lists_response.get("items", []):
        tasklist_id = task_list.get("id")
        tasklist_title = task_list.get("title")

        tasks_url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"
        params = {
            "showCompleted": str(show_completed).lower(),
            "maxResults": 100,
        }
        tasks_response = await svc._make_request("GET", tasks_url, params=params)

        for task in tasks_response.get("items", []):
            title = task.get("title", "").lower()
            notes = task.get("notes", "").lower()
            if query in title or query in notes:
                formatted = _format_task(task)
                formatted["tasklist_id"] = tasklist_id
                formatted["tasklist_title"] = tasklist_title
                matching_tasks.append(formatted)

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


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all tasks tool handlers.

    Args:
        svc: BaseService instance providing HTTP helpers.

    Returns:
        Dictionary mapping tool names to async callables.
    """
    return {
        "list_task_lists": lambda args: _list_task_lists(svc, args),
        "get_task_list": lambda args: _get_task_list(svc, args),
        "create_task_list": lambda args: _create_task_list(svc, args),
        "update_task_list": lambda args: _update_task_list(svc, args),
        "delete_task_list": lambda args: _delete_task_list(svc, args),
        "list_tasks": lambda args: _list_tasks(svc, args),
        "get_task": lambda args: _get_task(svc, args),
        "search_tasks": lambda args: _search_tasks(svc, args),
        "create_task": lambda args: _create_task(svc, args),
        "update_task": lambda args: _update_task(svc, args),
        "complete_task": lambda args: _complete_task(svc, args),
        "delete_task": lambda args: _delete_task(svc, args),
        "move_task": lambda args: _move_task(svc, args),
    }
