# Feature Gap Analysis: gworkspace-mcp

**Date:** 2026-02-10
**Analyst:** Research Agent
**Project:** /Users/masa/Projects/gworkspace-mcp

## Executive Summary

This analysis evaluates gworkspace-mcp (66 tools across Gmail, Calendar, Drive, Docs, Tasks) against user expectations and competitor offerings. Key findings:

1. **Gmail batch operations are well-implemented** using true Google API batching
2. **Significant gaps exist** in Calendar (recurring events, free/busy), Gmail (filters, signatures), and Drive (permissions management)
3. **No batch operations for Drive, Calendar, Docs, or Tasks** - a major gap for power users
4. **Priority recommendations**: Add recurring events, free/busy queries, Gmail filters, and Drive permissions

---

## 1. Batch Operations Analysis

### 1.1 Existing Batch Operations

| Tool | True API Batching? | Implementation Details |
|------|-------------------|------------------------|
| `batch_modify_gmail_messages` | **YES** | Uses Gmail `batchModify` endpoint correctly |
| `batch_archive_gmail_messages` | **YES** | Delegates to `batch_modify_gmail_messages` with `remove_label_ids: ["INBOX"]` |
| `batch_mark_gmail_as_read` | **YES** | Delegates to `batch_modify_gmail_messages` with `remove_label_ids: ["UNREAD"]` |
| `batch_delete_gmail_messages` | **YES** | Uses Gmail `batchDelete` endpoint correctly |
| `batch_trash_gmail_messages` | **NO** | Concurrent single-message requests (no batch API available) |

**Assessment:** Gmail batch operations are properly implemented. The `batch_trash_gmail_messages` uses concurrent requests because Gmail lacks a native batch trash endpoint - this is the correct approach.

### 1.2 Missing Batch Capabilities

#### Gmail Batch Gaps (Low Priority)
| Missing Operation | Google API Support | Priority |
|-------------------|-------------------|----------|
| `batch_star_gmail_messages` | Via batchModify | LOW |
| `batch_unstar_gmail_messages` | Via batchModify | LOW |
| `batch_mark_gmail_as_unread` | Via batchModify | LOW |
| `batch_untrash_gmail_messages` | No batch API | LOW |

**Recommendation:** These can be easily added using the existing `batch_modify_gmail_messages` pattern. Low priority since single-message operations cover most use cases.

#### Calendar Batch Gaps (MEDIUM Priority)
| Missing Operation | Google API Support | Priority |
|-------------------|-------------------|----------|
| Batch create events | Yes (batch request) | MEDIUM |
| Batch update events | Yes (batch request) | MEDIUM |
| Batch delete events | Yes (batch request) | MEDIUM |
| Batch move events | Yes (batch request) | LOW |

**Recommendation:** Calendar batch operations would benefit users importing events or making bulk changes. Google Calendar API supports batch requests via the standard HTTP batch interface.

#### Drive Batch Gaps (MEDIUM Priority)
| Missing Operation | Google API Support | Priority |
|-------------------|-------------------|----------|
| Batch delete files | Yes (batch request) | MEDIUM |
| Batch move files | Yes (batch request) | MEDIUM |
| Batch update metadata | Yes (batch request) | LOW |
| Batch share files | Yes (batch request) | MEDIUM |

**Recommendation:** Drive batch operations are commonly needed for folder cleanup and bulk sharing. The google-api-python-client supports batch requests natively.

#### Docs Batch Gaps (LOW Priority)
| Missing Operation | Google API Support | Priority |
|-------------------|-------------------|----------|
| Batch document updates | Yes (batchUpdate) | LOW |

**Recommendation:** The Docs API already uses `batchUpdate` internally for append operations. Exposing direct batch updates is lower priority.

#### Tasks Batch Gaps (LOW Priority)
| Missing Operation | Google API Support | Priority |
|-------------------|-------------------|----------|
| Batch create tasks | No native batch | LOW |
| Batch complete tasks | No native batch | LOW |
| Batch delete tasks | No native batch | LOW |

**Recommendation:** Tasks API lacks native batch support. Would require concurrent single-task requests like `batch_trash_gmail_messages`. Lower priority.

---

## 2. Feature Gap Analysis by Service

### 2.1 Gmail Gaps (18 tools implemented)

#### HIGH Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| **Gmail Filters** | Zapier, Make, n8n | HIGH | MEDIUM |
| **Vacation Responder** | Zapier, Make | MEDIUM | LOW |
| **Email Signatures** | Make | MEDIUM | LOW |

**Gmail Filters:** Users frequently want to create/manage auto-filtering rules. The Gmail API supports `users.settings.filters` endpoints.

```
Missing tools:
- list_gmail_filters
- create_gmail_filter
- delete_gmail_filter
```

**Vacation Responder:** Set/get out-of-office auto-reply via `users.settings.vacation` endpoint.

```
Missing tools:
- get_vacation_settings
- set_vacation_settings
```

**Email Signatures:** Manage email signatures via `users.settings.sendAs` endpoint.

```
Missing tools:
- get_email_signature
- set_email_signature
```

#### MEDIUM Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| Gmail Delegates | Limited | MEDIUM | MEDIUM |
| Email Forwarding | Make, n8n | MEDIUM | LOW |
| Thread Operations | Zapier | MEDIUM | LOW |

**Gmail Delegates:** Allow other users to access mailbox (admin feature).

**Email Forwarding:** Manage forwarding addresses via `users.settings.forwardingAddresses`.

**Thread Operations:** Add `archive_gmail_thread`, `delete_gmail_thread` for thread-level operations (vs message-level).

#### LOW Priority Gaps
| Feature | Notes |
|---------|-------|
| Email Templates | Rarely supported in MCP tools |
| Push Notifications | Watch API - complex setup |
| History API | For sync applications |

### 2.2 Calendar Gaps (10 tools implemented)

#### HIGH Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| **Recurring Events** | Zapier, Make, n8n, ALL | CRITICAL | MEDIUM |
| **Free/Busy Query** | Zapier, Make | HIGH | LOW |
| **Event Notifications** | Make | MEDIUM | LOW |

**Recurring Events (CRITICAL):** Documented as "not yet implemented" in `/docs/api/calendar.md`. This is a major gap - users expect RRULE support for weekly meetings, monthly reviews, etc.

```
Required changes:
- create_event: Add recurrence parameter (RRULE string or frequency/interval)
- update_event: Support modifying recurrence
- get_events: Already returns single instances (singleEvents=True)
- New tool: create_recurring_event (optional convenience wrapper)
```

Google Calendar API RRULE format:
```
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR
RRULE:FREQ=MONTHLY;BYMONTHDAY=15
RRULE:FREQ=DAILY;COUNT=10
```

**Free/Busy Query:** Check availability across multiple calendars. Essential for scheduling. Uses `freebusy.query` endpoint.

```
Missing tool:
- query_free_busy(calendars: list, time_min: str, time_max: str)
```

**Event Notifications:** Set reminder times for events (popup, email).

```
Missing in create_event/update_event:
- reminders parameter (list of {method: "popup"|"email", minutes: int})
```

#### MEDIUM Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| Calendar Sharing | Make | MEDIUM | LOW |
| Event Attachments | Zapier | MEDIUM | MEDIUM |
| Conference Data | Zapier, Make | MEDIUM | MEDIUM |

**Calendar Sharing:** Manage calendar ACLs via `calendarList` and `acl` endpoints.

**Event Attachments:** Add file attachments to events (Drive links).

**Conference Data:** Add Google Meet links automatically to events.

#### LOW Priority Gaps
| Feature | Notes |
|---------|-------|
| Color Management | Event/calendar colors |
| Extended Properties | Custom metadata |
| Quick Add | Natural language event creation |

### 2.3 Drive Gaps (17 tools implemented)

#### HIGH Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| **File Sharing/Permissions** | Zapier, Make, n8n, ALL | HIGH | LOW |
| **File Copy** | Zapier, Make | HIGH | LOW |
| **Rename File** | Zapier, Make | HIGH | LOW |

**File Sharing/Permissions (HIGH):** The codebase shows internal permission handling for Mermaid images, but no public tools exist.

```
Missing tools:
- share_drive_file(file_id, email, role, send_notification)
- list_file_permissions(file_id)
- update_file_permission(file_id, permission_id, role)
- remove_file_permission(file_id, permission_id)
- make_file_public(file_id)
- make_file_private(file_id)
```

**File Copy:** Duplicate files within Drive.

```
Missing tool:
- copy_drive_file(file_id, new_name, parent_id)
```

**Rename File:** Currently requires knowing parent folder. Should be simpler.

```
Missing tool:
- rename_drive_file(file_id, new_name)
```

#### MEDIUM Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| Version History | Zapier | MEDIUM | LOW |
| File Watching | Make | MEDIUM | HIGH |
| Starred Files | Zapier | LOW | LOW |
| Trash Management | Make | MEDIUM | LOW |

**Version History:** List and manage file revisions.

```
Missing tools:
- list_file_revisions(file_id)
- download_file_revision(file_id, revision_id)
```

**Trash Management:** Currently `delete_drive_file` permanently deletes. Add:

```
Missing tools:
- trash_drive_file(file_id)
- untrash_drive_file(file_id)
- empty_drive_trash()
- list_trashed_files()
```

#### LOW Priority Gaps
| Feature | Notes |
|---------|-------|
| Shortcuts | Create shortcuts to files |
| Drive Labels | Apply custom labels |
| Drive Activity | Activity feed |

### 2.4 Docs Gaps (11 tools implemented)

#### MEDIUM Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| **Text Formatting** | n8n | MEDIUM | HIGH |
| **Insert Content at Position** | n8n | MEDIUM | MEDIUM |
| **Document Templates** | Make | MEDIUM | MEDIUM |

**Text Formatting:** Current `append_to_document` only adds plain text. Users want bold, italics, headings.

```
Missing capability:
- append_to_document: Add formatting_style parameter
- Or: append_formatted_to_document(document_id, text, style: dict)
```

**Insert Content at Position:** Insert at specific index, not just append.

```
Missing tool:
- insert_text_at_position(document_id, text, index)
```

**Document Templates:** Create docs from templates with variable substitution.

#### LOW Priority Gaps
| Feature | Notes |
|---------|-------|
| Tables | Insert/modify tables |
| Images | Insert images inline |
| Headers/Footers | Document header/footer |
| Page Breaks | Insert page breaks |
| Suggestions Mode | Track changes |
| Resolve Comments | Mark comments resolved |

### 2.5 Tasks Gaps (10 tools implemented)

#### MEDIUM Priority Gaps
| Feature | Competitor Support | User Value | Implementation Complexity |
|---------|-------------------|------------|---------------------------|
| Task Links | Zapier | MEDIUM | LOW |
| Due Date Reminders | Make | MEDIUM | LOW |

**Task Links:** The `links` field allows associating URLs with tasks.

```
Missing in create_task/update_task:
- links parameter (list of {type, description, link})
```

#### LOW Priority Gaps
| Feature | Notes |
|---------|-------|
| Batch Operations | No native API support |
| Task Ordering | Already supported via move_task |

---

## 3. Priority Recommendations

### Tier 1: Critical (Implement Immediately)

1. **Recurring Events in Calendar** (HIGH user value, documented gap)
   - Estimated effort: 4-6 hours
   - Add `recurrence` parameter to `create_event`
   - Test RRULE patterns

2. **Free/Busy Query** (HIGH user value, LOW complexity)
   - Estimated effort: 2-3 hours
   - New `query_free_busy` tool

3. **Drive File Sharing/Permissions** (HIGH user value, LOW complexity)
   - Estimated effort: 4-6 hours
   - 4-6 new tools for permission management

### Tier 2: High Priority (Next Sprint)

4. **Gmail Filters** (HIGH user value, MEDIUM complexity)
   - Estimated effort: 3-4 hours
   - 3 new tools for filter management

5. **File Copy and Rename** (HIGH user value, LOW complexity)
   - Estimated effort: 2 hours
   - 2 simple new tools

6. **Vacation Responder** (MEDIUM user value, LOW complexity)
   - Estimated effort: 2 hours
   - 2 new tools

### Tier 3: Medium Priority (Backlog)

7. **Calendar Batch Operations** (batch create/update/delete events)
8. **Drive Batch Operations** (batch delete/move/share)
9. **Drive Trash Management** (trash vs permanent delete)
10. **Email Signatures**
11. **Event Notifications/Reminders**
12. **Drive Version History**

### Tier 4: Low Priority (Consider Later)

13. Additional Gmail batch operations (star, unstar)
14. Docs text formatting
15. Task links
16. Calendar sharing/ACLs
17. Conference data (Google Meet links)

---

## 4. Competitor Comparison

### Feature Matrix

| Feature | gworkspace-mcp | Zapier | Make | n8n |
|---------|---------------|--------|------|-----|
| **Gmail Search** | YES | YES | YES | YES |
| **Gmail Send** | YES | YES | YES | YES |
| **Gmail Labels** | YES | YES | YES | YES |
| **Gmail Filters** | NO | YES | YES | YES |
| **Gmail Signatures** | NO | NO | YES | NO |
| **Gmail Batch** | YES | NO | NO | NO |
| **Calendar Events** | YES | YES | YES | YES |
| **Recurring Events** | NO | YES | YES | YES |
| **Free/Busy** | NO | YES | YES | NO |
| **Drive Files** | YES | YES | YES | YES |
| **Drive Permissions** | NO | YES | YES | YES |
| **Drive Copy** | NO | YES | YES | YES |
| **Docs Create** | YES | YES | YES | YES |
| **Docs Formatting** | NO | NO | NO | YES |
| **Tasks** | YES | YES | YES | YES |

### Competitive Advantages

gworkspace-mcp **strengths**:
- Gmail batch operations (unique among competitors)
- Document tabs support (rare)
- Mermaid diagram rendering (unique)
- Local MCP integration (vs webhook-based)

### Competitive Disadvantages

gworkspace-mcp **weaknesses**:
- Missing recurring events (critical gap)
- No Drive permissions management
- No Gmail filters
- No free/busy queries
- No batch operations outside Gmail

---

## 5. Implementation Notes

### Batch Request Pattern (google-api-python-client)

For implementing missing batch operations:

```python
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest

def batch_delete_drive_files(service, file_ids):
    """Delete multiple files in a single batch request."""
    batch = service.new_batch_http_request()

    for file_id in file_ids:
        batch.add(
            service.files().delete(fileId=file_id),
            callback=lambda request_id, response, exception: None
        )

    batch.execute()
```

**Note:** The current implementation uses `httpx` directly for REST API calls. To use batch requests, would need to either:
1. Construct multipart/mixed batch requests manually
2. Switch to google-api-python-client for batch-supporting endpoints
3. Use concurrent requests (current approach for `batch_trash_gmail_messages`)

### Recurring Event Format

```python
event_body = {
    "summary": "Weekly Standup",
    "start": {"dateTime": "2024-01-15T10:00:00Z", "timeZone": "America/New_York"},
    "end": {"dateTime": "2024-01-15T10:30:00Z", "timeZone": "America/New_York"},
    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=52"]
}
```

---

## 6. Action Items

### Immediate (This Week)
- [ ] Add `recurrence` parameter to `create_event` tool
- [ ] Implement `query_free_busy` tool
- [ ] Implement basic Drive permissions tools

### Next Sprint
- [ ] Implement Gmail filters tools
- [ ] Add `copy_drive_file` and `rename_drive_file`
- [ ] Add vacation responder tools

### Documentation Updates
- [ ] Update `/docs/api/calendar.md` when recurring events implemented
- [ ] Create `/docs/api/permissions.md` for Drive permissions
- [ ] Update feature matrix in README

---

## Appendix: API Endpoint Reference

### Gmail Settings Endpoints (Missing)
- `GET/PUT /gmail/v1/users/me/settings/vacation`
- `GET/POST/DELETE /gmail/v1/users/me/settings/filters`
- `GET/PUT /gmail/v1/users/me/settings/sendAs/{sendAsEmail}`

### Calendar Endpoints (Missing)
- `POST /calendar/v3/freeBusy` - Free/busy query
- Event `recurrence` field - Already supported by existing endpoint

### Drive Endpoints (Missing)
- `POST /drive/v3/files/{fileId}/permissions` - Create permission
- `GET /drive/v3/files/{fileId}/permissions` - List permissions
- `PATCH /drive/v3/files/{fileId}/permissions/{permissionId}` - Update permission
- `DELETE /drive/v3/files/{fileId}/permissions/{permissionId}` - Delete permission
- `POST /drive/v3/files/{fileId}/copy` - Copy file
- `GET /drive/v3/files/{fileId}/revisions` - List revisions

---

*Research completed: 2026-02-10*
*Output saved to: /Users/masa/Projects/gworkspace-mcp/docs/research/feature-gap-analysis-2026-02-10.md*
