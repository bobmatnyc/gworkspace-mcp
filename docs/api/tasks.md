# Tasks API Reference

Complete reference for the 10 Tasks tools provided by google-workspace-mcp.

## Overview

Tasks tools enable managing Google Tasks lists and individual tasks.

| Category | Tools |
|----------|-------|
| Task Lists | `list_task_lists`, `get_task_list`, `create_task_list`, `update_task_list`, `delete_task_list` |
| Tasks | `list_tasks`, `get_task`, `search_tasks`, `create_task`, `update_task`, `complete_task`, `delete_task`, `move_task` |

---

## Task List Operations

### list_task_lists

List all task lists for the authenticated user.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `max_results` | integer | No | 100 | Maximum lists to return |

**Example**:
```json
{}
```

**Returns**: List of task lists with:
- `id`: Task list ID (use for other operations)
- `title`: List title
- `updated`: Last update time
- `selfLink`: API link

**Note**: Every Google account has a default task list. Its ID can be referenced as `@default`.

---

### get_task_list

Get a specific task list by ID.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tasklist_id` | string | Yes | Task list ID |

**Example**:
```json
{
  "tasklist_id": "MTIzNDU2Nzg5MA"
}
```

**Returns**: Task list details.

---

### create_task_list

Create a new task list.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Task list title |

**Example**:
```json
{
  "title": "Work Projects"
}
```

**Returns**: Created task list ID and details.

---

### update_task_list

Update an existing task list's title.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tasklist_id` | string | Yes | Task list ID to update |
| `title` | string | Yes | New title |

**Example**:
```json
{
  "tasklist_id": "MTIzNDU2Nzg5MA",
  "title": "Work Projects - Q1"
}
```

**Returns**: Updated task list details.

---

### delete_task_list

Delete a task list.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tasklist_id` | string | Yes | Task list ID to delete |

**Example**:
```json
{
  "tasklist_id": "MTIzNDU2Nzg5MA"
}
```

**Returns**: Confirmation of deletion.

**Warning**: Deleting a task list deletes all tasks within it. This cannot be undone.

---

## Task Operations

### list_tasks

List all tasks in a task list.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tasklist_id` | string | No | "@default" | Task list ID |
| `show_completed` | boolean | No | true | Include completed tasks |
| `show_hidden` | boolean | No | false | Include hidden tasks |
| `due_min` | string | No | - | Due date lower bound (RFC3339) |
| `due_max` | string | No | - | Due date upper bound (RFC3339) |
| `max_results` | integer | No | 100 | Maximum tasks to return |

**Example - All tasks**:
```json
{
  "tasklist_id": "@default"
}
```

**Example - Incomplete tasks only**:
```json
{
  "tasklist_id": "@default",
  "show_completed": false
}
```

**Example - Tasks due this week**:
```json
{
  "tasklist_id": "@default",
  "due_min": "2024-01-15T00:00:00Z",
  "due_max": "2024-01-21T23:59:59Z"
}
```

**Returns**: List of tasks with:
- `id`: Task ID
- `title`: Task title
- `notes`: Task description/notes
- `due`: Due date
- `status`: `needsAction` or `completed`
- `parent`: Parent task ID (for subtasks)
- `position`: Position in list
- `completed`: Completion timestamp

---

### get_task

Get a specific task by ID.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `tasklist_id` | string | No | "@default" | Task list ID |
| `task_id` | string | Yes | - | Task ID |

**Example**:
```json
{
  "task_id": "abc123xyz"
}
```

**Returns**: Full task details.

---

### search_tasks

Search tasks across all task lists by title or notes.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `show_completed` | boolean | No | true | Include completed tasks |

**Example**:
```json
{
  "query": "budget review"
}
```

**Returns**: List of matching tasks from all task lists, including:
- Task details
- Task list information

**Note**: Searches task titles and notes content.

---

### create_task

Create a new task in a task list.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `title` | string | Yes | - | Task title |
| `tasklist_id` | string | No | "@default" | Task list ID |
| `notes` | string | No | - | Task description |
| `due` | string | No | - | Due date (RFC3339) |
| `parent` | string | No | - | Parent task ID (for subtask) |

**Example - Simple task**:
```json
{
  "title": "Review PR #123"
}
```

**Example - Task with details**:
```json
{
  "title": "Complete quarterly report",
  "notes": "Include sales figures and projections for Q2",
  "due": "2024-01-20T00:00:00Z"
}
```

**Example - Subtask**:
```json
{
  "title": "Research competitors",
  "parent": "parentTaskId123"
}
```

**Returns**: Created task ID and details.

---

### update_task

Update an existing task.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task ID to update |
| `tasklist_id` | string | No | "@default" | Task list ID |
| `title` | string | No | - | New title |
| `notes` | string | No | - | New notes |
| `due` | string | No | - | New due date |
| `status` | string | No | - | `needsAction` or `completed` |

**Example - Update title**:
```json
{
  "task_id": "abc123xyz",
  "title": "Review PR #123 (URGENT)"
}
```

**Example - Change due date**:
```json
{
  "task_id": "abc123xyz",
  "due": "2024-01-25T00:00:00Z"
}
```

**Example - Mark incomplete**:
```json
{
  "task_id": "abc123xyz",
  "status": "needsAction"
}
```

**Returns**: Updated task details.

---

### complete_task

Mark a task as completed.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task ID to complete |
| `tasklist_id` | string | No | "@default" | Task list ID |

**Example**:
```json
{
  "task_id": "abc123xyz"
}
```

**Returns**: Updated task with completion status.

**Note**: Completing a parent task may affect subtasks depending on Google Tasks behavior.

---

### delete_task

Delete a task.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task ID to delete |
| `tasklist_id` | string | No | "@default" | Task list ID |

**Example**:
```json
{
  "task_id": "abc123xyz"
}
```

**Returns**: Confirmation of deletion.

**Note**: Deleting a parent task may delete its subtasks.

---

### move_task

Move a task to a different position or make it a subtask.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task ID to move |
| `tasklist_id` | string | No | "@default" | Task list ID |
| `parent` | string | No | - | New parent task ID |
| `previous` | string | No | - | Task to position after |

**Example - Make subtask**:
```json
{
  "task_id": "abc123xyz",
  "parent": "parentTask456"
}
```

**Example - Reorder**:
```json
{
  "task_id": "abc123xyz",
  "previous": "otherTask789"
}
```

**Example - Move to top level**:
```json
{
  "task_id": "abc123xyz",
  "parent": null
}
```

**Returns**: Moved task details.

---

## Common Workflows

### Daily Task Review

```
1. list_tasks(show_completed=false)
2. Review and prioritize
3. complete_task() for finished items
```

### Weekly Planning

```
1. list_task_lists()
2. For each list: list_tasks(due_max="end of week")
3. create_task() for new items
4. update_task() to adjust due dates
```

### Project Task Hierarchy

```
1. create_task(title="Main Project Task")
2. create_task(title="Subtask 1", parent="main_task_id")
3. create_task(title="Subtask 2", parent="main_task_id")
4. create_task(title="Sub-subtask", parent="subtask_1_id")
```

### Find and Complete Tasks

```
1. search_tasks(query="weekly report")
2. Identify the relevant task
3. complete_task(task_id="...")
```

### Reorganize Task Lists

```
1. list_task_lists()
2. create_task_list(title="New Organization")
3. list_tasks(tasklist_id="old_list")
4. For each task: create_task in new list
5. delete_task_list(tasklist_id="old_list")  # Optional cleanup
```

## Date/Time Format

All dates use RFC3339 format:

```
# Full timestamp
2024-01-15T00:00:00Z          # UTC
2024-01-15T00:00:00-05:00     # Eastern Time

# For due dates, time is often midnight UTC
2024-01-15T00:00:00Z
```

## Task Status Values

| Status | Meaning |
|--------|---------|
| `needsAction` | Task is incomplete |
| `completed` | Task is complete |

## Related Documentation

- [Gmail API](gmail.md)
- [Calendar API](calendar.md)
- [Drive API](drive.md)
- [Docs API](docs.md)
