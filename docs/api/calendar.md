# Calendar API Reference

Complete reference for the 10 Calendar tools provided by google-workspace-mcp.

## Overview

Calendar tools enable managing Google Calendar events and calendars.

| Category | Tools |
|----------|-------|
| Calendar Management | `list_calendars`, `create_calendar`, `update_calendar`, `delete_calendar` |
| Event Management | `get_events`, `create_event`, `update_event`, `delete_event` |

---

## Calendar Management

### list_calendars

List all calendars accessible by the authenticated user.

**Parameters**: None

**Example**:
```json
{}
```

**Returns**: List of calendars with:
- `id`: Calendar ID (use for other operations)
- `summary`: Calendar name
- `description`: Calendar description
- `timezone`: Calendar timezone
- `accessRole`: Your access level (`owner`, `writer`, `reader`)
- `primary`: Whether this is the primary calendar

**Note**: The primary calendar ID is typically your email address or "primary".

---

### create_calendar

Create a new calendar.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `summary` | string | Yes | - | Calendar name/title |
| `description` | string | No | - | Calendar description |
| `timezone` | string | No | - | Timezone (e.g., "America/New_York") |

**Example**:
```json
{
  "summary": "Project Deadlines",
  "description": "Important project milestone dates",
  "timezone": "America/Los_Angeles"
}
```

**Returns**: Created calendar details including the new calendar ID.

**Timezone examples**:
- `America/New_York`
- `America/Los_Angeles`
- `Europe/London`
- `Asia/Tokyo`
- `UTC`

---

### update_calendar

Update an existing calendar's properties.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calendar_id` | string | Yes | Calendar ID to update |
| `summary` | string | No | New calendar name |
| `description` | string | No | New description |
| `timezone` | string | No | New timezone |

**Example**:
```json
{
  "calendar_id": "abc123@group.calendar.google.com",
  "summary": "Project Deadlines (Q1)",
  "description": "Q1 2024 project milestones"
}
```

**Returns**: Updated calendar details.

**Note**: Only provide fields you want to change.

---

### delete_calendar

Delete a calendar.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calendar_id` | string | Yes | Calendar ID to delete |

**Example**:
```json
{
  "calendar_id": "abc123@group.calendar.google.com"
}
```

**Returns**: Confirmation of deletion.

**Warning**:
- Cannot delete the primary calendar
- Deleting a calendar removes all its events
- This action cannot be undone

---

## Event Management

### get_events

Get events from a calendar within a time range.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `calendar_id` | string | No | "primary" | Calendar ID |
| `time_min` | string | No | - | Start time (RFC3339) |
| `time_max` | string | No | - | End time (RFC3339) |
| `max_results` | integer | No | 10 | Maximum events to return |

**Example**:
```json
{
  "calendar_id": "primary",
  "time_min": "2024-01-01T00:00:00Z",
  "time_max": "2024-01-31T23:59:59Z",
  "max_results": 50
}
```

**Returns**: List of events with:
- `id`: Event ID
- `summary`: Event title
- `description`: Event description
- `start`: Start time
- `end`: End time
- `location`: Event location
- `attendees`: List of attendees
- `status`: Event status (`confirmed`, `tentative`, `cancelled`)
- `htmlLink`: Link to view in Google Calendar

**RFC3339 Format**:
```
2024-01-15T10:00:00Z        # UTC
2024-01-15T10:00:00-05:00   # Eastern Time
2024-01-15T10:00:00+09:00   # Japan Time
```

---

### create_event

Create a new calendar event.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `summary` | string | Yes | - | Event title |
| `start_time` | string | Yes | - | Start time (RFC3339) |
| `end_time` | string | Yes | - | End time (RFC3339) |
| `calendar_id` | string | No | "primary" | Calendar ID |
| `description` | string | No | - | Event description |
| `location` | string | No | - | Event location |
| `attendees` | array | No | - | List of attendee emails |
| `timezone` | string | No | - | Event timezone |

**Example - Simple event**:
```json
{
  "summary": "Team Standup",
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T10:30:00Z"
}
```

**Example - Full event with attendees**:
```json
{
  "summary": "Project Review Meeting",
  "description": "Quarterly project status review",
  "start_time": "2024-01-15T14:00:00-05:00",
  "end_time": "2024-01-15T15:00:00-05:00",
  "location": "Conference Room A",
  "attendees": ["john@example.com", "jane@example.com", "boss@example.com"],
  "timezone": "America/New_York"
}
```

**Returns**: Created event details including the event ID.

**Notes**:
- Attendees receive email invitations
- All-day events use date format: `2024-01-15` (without time)

---

### update_event

Update an existing calendar event.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `event_id` | string | Yes | - | Event ID to update |
| `calendar_id` | string | No | "primary" | Calendar ID |
| `summary` | string | No | - | New event title |
| `description` | string | No | - | New description |
| `start_time` | string | No | - | New start time |
| `end_time` | string | No | - | New end time |
| `location` | string | No | - | New location |
| `attendees` | array | No | - | New attendee list |

**Example - Reschedule event**:
```json
{
  "event_id": "abc123xyz",
  "start_time": "2024-01-16T14:00:00Z",
  "end_time": "2024-01-16T15:00:00Z"
}
```

**Example - Add attendees**:
```json
{
  "event_id": "abc123xyz",
  "attendees": ["john@example.com", "jane@example.com", "newperson@example.com"]
}
```

**Returns**: Updated event details.

**Note**: When updating attendees, provide the complete list (not just additions).

---

### delete_event

Delete a calendar event.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `event_id` | string | Yes | - | Event ID to delete |
| `calendar_id` | string | No | "primary" | Calendar ID |

**Example**:
```json
{
  "event_id": "abc123xyz",
  "calendar_id": "primary"
}
```

**Returns**: Confirmation of deletion.

**Note**: Deleting an event with attendees may send cancellation notifications.

---

## Common Workflows

### View Week's Schedule

```
1. get_events(
     time_min="2024-01-15T00:00:00Z",
     time_max="2024-01-21T23:59:59Z",
     max_results=100
   )
```

### Schedule a Meeting Series

For recurring meetings, create individual events or use Google Calendar directly (recurring event support not yet implemented).

### Find Free Time

```
1. get_events(time_min=start, time_max=end, max_results=100)
2. Analyze gaps between events
```

### Move Meeting to Different Calendar

```
1. get_events from source calendar to find event details
2. create_event on destination calendar with same details
3. delete_event from source calendar
```

## Date/Time Handling

### RFC3339 Format

All times should be in RFC3339 format:

```
# UTC (Zulu time)
2024-01-15T10:00:00Z

# With timezone offset
2024-01-15T10:00:00-05:00  # Eastern Time
2024-01-15T10:00:00+00:00  # UTC explicit
2024-01-15T10:00:00+09:00  # Japan Time
```

### All-Day Events

For all-day events, use date-only format:

```
# All-day event on January 15
start: "2024-01-15"
end: "2024-01-16"  # Next day (exclusive)
```

### Common Timezones

| Timezone ID | Description |
|-------------|-------------|
| `America/New_York` | Eastern Time |
| `America/Chicago` | Central Time |
| `America/Denver` | Mountain Time |
| `America/Los_Angeles` | Pacific Time |
| `Europe/London` | UK Time |
| `Europe/Paris` | Central European |
| `Asia/Tokyo` | Japan Time |
| `Asia/Shanghai` | China Time |
| `UTC` | Coordinated Universal Time |

## Related Documentation

- [Gmail API](gmail.md)
- [Drive API](drive.md)
- [Docs API](docs.md)
- [Tasks API](tasks.md)
