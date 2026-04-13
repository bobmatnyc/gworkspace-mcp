"""Google Calendar service module for MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import CALENDAR_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="manage_calendars",
        description=(
            "Manage Google Calendars. Actions: list (all calendars), create, update, delete."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": ["list", "create", "update", "delete"],
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (required for update, delete)",
                },
                "summary": {
                    "type": "string",
                    "description": "Calendar title/name (required for create; optional for update)",
                },
                "description": {
                    "type": "string",
                    "description": "Calendar description (optional)",
                },
                "timezone": {
                    "type": "string",
                    "description": "Calendar timezone (e.g., 'America/New_York', optional)",
                },
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="manage_events",
        description=(
            "Manage Google Calendar events. "
            "Actions: list (events in a calendar), create, update, delete."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Operation to perform",
                    "enum": ["list", "create", "update", "delete"],
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar ID (default: 'primary')",
                    "default": "primary",
                },
                "event_id": {
                    "type": "string",
                    "description": "Event ID (required for update, delete)",
                },
                "summary": {
                    "type": "string",
                    "description": "Event title (required for create; optional for update)",
                },
                "description": {
                    "type": "string",
                    "description": "Event description (optional)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in RFC3339 format, e.g. '2024-01-15T10:00:00Z' (required for create; optional for update)",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in RFC3339 format, e.g. '2024-01-15T11:00:00Z' (required for create; optional for update)",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses (optional)",
                },
                "location": {
                    "type": "string",
                    "description": "Event location (optional)",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the event, e.g. 'America/New_York' (create only, optional)",
                },
                "recurrence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "RRULE strings for recurring events, e.g. ['RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR'] (optional)",
                },
                "time_min": {
                    "type": "string",
                    "description": "Start time filter in RFC3339 format (list only, optional)",
                },
                "time_max": {
                    "type": "string",
                    "description": "End time filter in RFC3339 format (list only, optional)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of events to return (list only, default: 10)",
                    "default": 10,
                },
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="query_free_busy",
        description="Query free/busy information for calendars",
        inputSchema={
            "type": "object",
            "properties": {
                "time_min": {
                    "type": "string",
                    "description": "Start of the interval in RFC3339 format (e.g., '2024-01-15T00:00:00Z')",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of the interval in RFC3339 format (e.g., '2024-01-16T00:00:00Z')",
                },
                "calendar_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Calendar IDs to query (default: ['primary'])",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the query (default: 'UTC')",
                },
            },
            "required": ["time_min", "time_max"],
        },
    ),
]


async def _list_calendars(svc: BaseService, _: dict[str, Any]) -> dict[str, Any]:
    """List all calendars accessible by the user."""
    url = f"{CALENDAR_API_BASE}/users/me/calendarList"
    response = await svc._make_request("GET", url)
    calendars = []
    for item in response.get("items", []):
        calendars.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "description": item.get("description"),
                "access_role": item.get("accessRole"),
                "primary": item.get("primary", False),
            }
        )
    return {"calendars": calendars, "count": len(calendars)}


async def _create_calendar(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new calendar."""
    summary = arguments["summary"]
    description = arguments.get("description")
    timezone = arguments.get("timezone")

    url = f"{CALENDAR_API_BASE}/calendars"
    calendar_body: dict[str, Any] = {"summary": summary}
    if description:
        calendar_body["description"] = description
    if timezone:
        calendar_body["timeZone"] = timezone

    response = await svc._make_request("POST", url, json_data=calendar_body)
    return {
        "status": "created",
        "id": response.get("id"),
        "summary": response.get("summary"),
        "description": response.get("description"),
        "timezone": response.get("timeZone"),
    }


async def _update_calendar(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update an existing calendar's properties."""
    calendar_id = arguments["calendar_id"]
    summary = arguments.get("summary")
    description = arguments.get("description")
    timezone = arguments.get("timezone")

    update_body: dict[str, Any] = {}
    if summary:
        update_body["summary"] = summary
    if description:
        update_body["description"] = description
    if timezone:
        update_body["timeZone"] = timezone

    if not update_body:
        raise ValueError(
            "At least one field (summary, description, or timezone) must be provided for update"
        )

    url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}"
    response = await svc._make_request("PATCH", url, json_data=update_body)
    return {
        "status": "updated",
        "id": response.get("id"),
        "summary": response.get("summary"),
        "description": response.get("description"),
        "timezone": response.get("timeZone"),
    }


async def _delete_calendar(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a calendar."""
    calendar_id = arguments["calendar_id"]
    if calendar_id == "primary":
        raise ValueError("Cannot delete the primary calendar")
    url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}"
    await svc._make_request("DELETE", url)
    return {"status": "deleted", "calendar_id": calendar_id}


async def _get_events(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get events from a calendar."""
    calendar_id = arguments.get("calendar_id", "primary")
    time_min = arguments.get("time_min")
    time_max = arguments.get("time_max")
    max_results = arguments.get("max_results", 10)

    url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events"
    params: dict[str, Any] = {
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max

    response = await svc._make_request("GET", url, params=params)
    events = []
    for item in response.get("items", []):
        start = item.get("start", {})
        end = item.get("end", {})
        events.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "description": item.get("description"),
                "start": start.get("dateTime") or start.get("date"),
                "end": end.get("dateTime") or end.get("date"),
                "location": item.get("location"),
                "attendees": [a.get("email") for a in item.get("attendees", [])],
            }
        )
    return {"events": events, "count": len(events)}


async def _create_event(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new calendar event."""
    calendar_id = arguments.get("calendar_id", "primary")
    summary = arguments["summary"]
    start_time = arguments["start_time"]
    end_time = arguments["end_time"]
    description = arguments.get("description")
    attendees = arguments.get("attendees", [])
    location = arguments.get("location")
    timezone = arguments.get("timezone")
    recurrence = arguments.get("recurrence")

    url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events"
    event_body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if timezone:
        event_body["start"]["timeZone"] = timezone
        event_body["end"]["timeZone"] = timezone
    if description:
        event_body["description"] = description
    if attendees:
        event_body["attendees"] = [{"email": email} for email in attendees]
    if location:
        event_body["location"] = location
    if recurrence:
        event_body["recurrence"] = recurrence

    response = await svc._make_request("POST", url, json_data=event_body)
    return {
        "status": "created",
        "id": response.get("id"),
        "summary": response.get("summary"),
        "start": response.get("start", {}).get("dateTime"),
        "end": response.get("end", {}).get("dateTime"),
        "html_link": response.get("htmlLink"),
        "recurrence": response.get("recurrence"),
    }


async def _update_event(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update an existing calendar event."""
    calendar_id = arguments.get("calendar_id", "primary")
    event_id = arguments["event_id"]

    get_url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
    existing = await svc._make_request("GET", get_url)

    update_body: dict[str, Any] = {}
    if "summary" in arguments:
        update_body["summary"] = arguments["summary"]
    if "description" in arguments:
        update_body["description"] = arguments["description"]
    if "start_time" in arguments:
        update_body["start"] = {"dateTime": arguments["start_time"]}
        if existing.get("start", {}).get("timeZone"):
            update_body["start"]["timeZone"] = existing["start"]["timeZone"]
    if "end_time" in arguments:
        update_body["end"] = {"dateTime": arguments["end_time"]}
        if existing.get("end", {}).get("timeZone"):
            update_body["end"]["timeZone"] = existing["end"]["timeZone"]
    if "attendees" in arguments:
        update_body["attendees"] = [{"email": email} for email in arguments["attendees"]]
    if "location" in arguments:
        update_body["location"] = arguments["location"]
    if "recurrence" in arguments:
        update_body["recurrence"] = arguments["recurrence"]

    response = await svc._make_request("PATCH", get_url, json_data=update_body)
    return {
        "status": "updated",
        "id": response.get("id"),
        "summary": response.get("summary"),
        "start": response.get("start", {}).get("dateTime"),
        "end": response.get("end", {}).get("dateTime"),
        "html_link": response.get("htmlLink"),
        "recurrence": response.get("recurrence"),
    }


async def _delete_event(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a calendar event."""
    calendar_id = arguments.get("calendar_id", "primary")
    event_id = arguments["event_id"]
    url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
    await svc._make_delete_request(url)
    return {"status": "deleted", "event_id": event_id}


async def _query_free_busy(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Query free/busy information for calendars."""
    time_min = arguments["time_min"]
    time_max = arguments["time_max"]
    calendar_ids = arguments.get("calendar_ids", ["primary"])
    timezone = arguments.get("timezone", "UTC")

    url = f"{CALENDAR_API_BASE}/freeBusy"
    request_body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": timezone,
        "items": [{"id": cal_id} for cal_id in calendar_ids],
    }
    response = await svc._make_request("POST", url, json_data=request_body)

    calendars_info = {}
    for cal_id, cal_data in response.get("calendars", {}).items():
        calendars_info[cal_id] = {
            "busy": cal_data.get("busy", []),
            "errors": cal_data.get("errors", []),
        }

    return {
        "time_min": time_min,
        "time_max": time_max,
        "timezone": timezone,
        "calendars": calendars_info,
    }


async def _manage_calendars(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch manage_calendars actions."""
    action = arguments["action"]
    if action == "list":
        return await _list_calendars(svc, arguments)
    if action == "create":
        if "summary" not in arguments:
            raise ValueError("summary is required for action 'create'")
        return await _create_calendar(svc, arguments)
    if action == "update":
        if "calendar_id" not in arguments:
            raise ValueError("calendar_id is required for action 'update'")
        return await _update_calendar(svc, arguments)
    if action == "delete":
        if "calendar_id" not in arguments:
            raise ValueError("calendar_id is required for action 'delete'")
        return await _delete_calendar(svc, arguments)
    raise ValueError(f"Unknown action '{action}' for manage_calendars")


async def _manage_events(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch manage_events actions."""
    action = arguments["action"]
    if action == "list":
        return await _get_events(svc, arguments)
    if action == "create":
        if "summary" not in arguments:
            raise ValueError("summary is required for action 'create'")
        if "start_time" not in arguments:
            raise ValueError("start_time is required for action 'create'")
        if "end_time" not in arguments:
            raise ValueError("end_time is required for action 'create'")
        return await _create_event(svc, arguments)
    if action == "update":
        if "event_id" not in arguments:
            raise ValueError("event_id is required for action 'update'")
        return await _update_event(svc, arguments)
    if action == "delete":
        if "event_id" not in arguments:
            raise ValueError("event_id is required for action 'delete'")
        return await _delete_event(svc, arguments)
    raise ValueError(f"Unknown action '{action}' for manage_events")


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all calendar tool handlers.

    Args:
        svc: BaseService instance providing HTTP helpers.

    Returns:
        Dictionary mapping tool names to async callables.
    """
    return {
        "manage_calendars": lambda args: _manage_calendars(svc, args),
        "manage_events": lambda args: _manage_events(svc, args),
        "query_free_busy": lambda args: _query_free_busy(svc, args),
    }
