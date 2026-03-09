---
name: gworkspace-mcp
description: Google Workspace MCP + Python API - Use MCP tools interactively or drive Gmail, Calendar, Drive, Docs, Sheets, Slides, and Tasks programmatically via the Python package.
version: 1.0.0
category: integration
author: gworkspace-mcp
license: MIT
progressive_disclosure:
  entry_point:
    summary: "Two interfaces: MCP tools (Claude calls them directly) or Python API (your code calls Google APIs using stored OAuth credentials). Use MCP for interactive tasks; use Python API for automation and custom logic."
    when_to_use: "Any task involving Gmail, Calendar, Drive, Docs, Sheets, Slides, or Tasks — whether Claude is performing the action or your Python code is."
    quick_start: "MCP: just use the tools. Python API: `from gworkspace_mcp.auth import OAuthManager; creds = OAuthManager().get_credentials()`"
context_limit: 900
tags:
  - google-workspace
  - gmail
  - calendar
  - drive
  - docs
  - sheets
  - slides
  - tasks
  - mcp
  - oauth
  - python
  - automation
requires_tools: []
---

# gworkspace-mcp: MCP Tools + Python API

## Interface Decision Guide

| Situation | Use |
|-----------|-----|
| Claude performing an action in an interactive session | **MCP tools** (call directly) |
| Python script automating Google Workspace | **Python API** |
| Need data not covered by MCP tools | **Python API** with `googleapiclient` |
| Bulk/batch operations in code | **Python API** |
| Claude reading data then passing to Python logic | **Both** — MCP to fetch, Python to process |
| Embedding the MCP server in your own app | `GoogleWorkspaceServer` / `create_server()` |

---

## Authentication (Shared by Both Interfaces)

Run once per project directory:
```bash
gworkspace-mcp setup
```

Tokens are stored at `./.gworkspace-mcp/tokens.json` (project-local).

### Get Credentials for Python API

```python
from gworkspace_mcp.auth import OAuthManager, TokenStatus

manager = OAuthManager()

# Check status before use
status, stored = manager.get_status()
# status is one of: TokenStatus.VALID, EXPIRED, MISSING, INVALID

# Get google.oauth2.credentials.Credentials object
credentials = manager.get_credentials()  # None if not authenticated

# Auto-refresh if expired
token = await manager.refresh_if_needed()
```

### Scopes Granted by Setup

```python
from gworkspace_mcp.auth import GOOGLE_WORKSPACE_SCOPES
# Includes: calendar, gmail.modify, drive, documents, tasks, spreadsheets, presentations
```

---

## MCP Tools Reference

MCP tools are called directly by Claude. All tools use the stored OAuth token automatically.

### Gmail (21 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `search_gmail_messages` | `query`, `max_results` | Search with Gmail query syntax |
| `get_gmail_message_content` | `message_id` | Full content + attachment metadata |
| `download_gmail_attachment` | `message_id`, `attachment_id`, `file_path` | Save attachment to disk |
| `send_email` | `to`, `subject`, `body`, `cc`, `bcc` | Send plain or HTML email |
| `reply_to_email` | `message_id`, `body` | Reply preserving thread |
| `create_draft` | `to`, `subject`, `body` | Create draft without sending |
| `list_gmail_labels` | — | All labels for the account |
| `create_gmail_label` | `name`, `color` | Create new label |
| `delete_gmail_label` | `label_id` | Delete label |
| `modify_gmail_message` | `message_id`, `add_labels`, `remove_labels` | Change labels |
| `archive_gmail_message` | `message_id` | Remove from inbox |
| `trash_gmail_message` | `message_id` | Move to trash |
| `untrash_gmail_message` | `message_id` | Restore from trash |
| `mark_gmail_as_read` | `message_id` | Mark read |
| `mark_gmail_as_unread` | `message_id` | Mark unread |
| `star_gmail_message` | `message_id` | Add star |
| `unstar_gmail_message` | `message_id` | Remove star |
| `batch_modify_gmail_messages` | `message_ids[]`, `add_labels`, `remove_labels` | Bulk label change |
| `batch_archive_gmail_messages` | `message_ids[]` | Bulk archive |
| `batch_trash_gmail_messages` | `message_ids[]` | Bulk trash |
| `batch_mark_gmail_read` | `message_ids[]` | Bulk mark read |

**Gmail search syntax examples:**
```
from:boss@company.com subject:budget after:2024/01/01
has:attachment larger:5M is:unread label:important
```

### Calendar (10 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `list_calendars` | — | All accessible calendars |
| `create_calendar` | `summary`, `description`, `timezone` | New calendar |
| `update_calendar` | `calendar_id`, `summary`, `description` | Edit calendar |
| `delete_calendar` | `calendar_id` | Delete (not primary) |
| `get_events` | `calendar_id`, `time_min`, `time_max`, `max_results` | Events in range |
| `create_event` | `summary`, `start`, `end`, `attendees[]`, `location` | New event |
| `update_event` | `calendar_id`, `event_id`, `summary`, `start`, `end` | Edit event |
| `delete_event` | `calendar_id`, `event_id` | Delete event |
| `search_events` | `query`, `calendar_id`, `time_min`, `time_max` | Search events |
| `query_free_busy` | `emails[]`, `time_min`, `time_max` | Availability check |

**Time format:** RFC3339 — `"2024-03-15T10:00:00-07:00"` or `"2024-03-15T10:00:00Z"`

### Drive (17 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `search_drive_files` | `query`, `max_results` | Search with Drive query |
| `get_drive_file_content` | `file_id` | Read file content |
| `create_drive_folder` | `name`, `parent_id` | New folder |
| `upload_drive_file` | `file_path`, `name`, `parent_id`, `mime_type` | Upload local file |
| `delete_drive_file` | `file_id` | Delete file/folder |
| `move_drive_file` | `file_id`, `new_parent_id` | Move file |
| `list_drive_contents` | `folder_id`, `max_results` | List folder contents |
| `upload_to_drive` | `file_path`, `folder_id` | Upload with auto mime type |
| `share_drive_file` | `file_id`, `email`, `role` | Share with user |
| `get_drive_file_metadata` | `file_id` | File details and metadata |
| `copy_drive_file` | `file_id`, `name`, `parent_id` | Duplicate file |
| `create_drive_shortcut` | `target_id`, `name`, `parent_id` | Drive shortcut |
| `update_drive_file` | `file_id`, `name`, `content` | Update file content |
| `export_drive_file` | `file_id`, `mime_type`, `output_path` | Export Google Doc to PDF/docx |
| `download_drive_folder` | `folder_id`, `local_path` | Download folder (requires rclone) |
| `sync_drive_folder` | `folder_id`, `local_path` | Sync folder (requires rclone) |
| `list_shared_drives` | — | List all shared drives |

**Drive query syntax:** `name contains 'report' and mimeType = 'application/pdf' and modifiedTime > '2024-01-01'`

### Docs (16 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `create_document` | `title`, `content` | New Google Doc |
| `get_document` | `document_id` | Read doc content |
| `append_to_document` | `document_id`, `content` | Add text at end |
| `upload_markdown_as_doc` | `markdown_content`, `title`, `folder_id` | Markdown → Google Doc |
| `publish_markdown_to_doc` | `document_id`, `markdown_content` | Replace doc with markdown |
| `list_document_comments` | `document_id` | All comments |
| `add_document_comment` | `document_id`, `content`, `anchor` | New comment |
| `reply_to_comment` | `document_id`, `comment_id`, `content` | Reply to comment |
| `list_document_tabs` | `document_id` | List doc tabs |
| `get_tab_content` | `document_id`, `tab_id` | Read specific tab |
| `create_document_tab` | `document_id`, `title` | Add new tab |
| `update_tab_properties` | `document_id`, `tab_id`, `title` | Rename tab |
| `move_tab` | `document_id`, `tab_id`, `index` | Reorder tab |
| `format_text_in_document` | `document_id`, `start_index`, `end_index`, `bold`, `italic`, `font_size` | Text formatting |
| `apply_heading_style` | `document_id`, `start_index`, `end_index`, `heading_level` | H1-H6 |
| `insert_table_in_document` | `document_id`, `rows`, `columns`, `index` | Insert table |

### Sheets (12 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `create_spreadsheet` | `title`, `sheets[]` | New spreadsheet |
| `get_spreadsheet_data` | `spreadsheet_id` | Full spreadsheet metadata |
| `list_spreadsheet_sheets` | `spreadsheet_id` | All sheets/tabs |
| `get_sheet_values` | `spreadsheet_id`, `range` | Read cell range (A1 notation) |
| `update_sheet_values` | `spreadsheet_id`, `range`, `values[][]` | Write cells |
| `append_sheet_values` | `spreadsheet_id`, `range`, `values[][]` | Append rows |
| `clear_sheet_values` | `spreadsheet_id`, `range` | Clear cells |
| `add_sheet` | `spreadsheet_id`, `title`, `index`, `tab_color` | Add new tab |
| `format_cells` | `spreadsheet_id`, `range`, `background_color`, `bold`, `font_size` | Cell formatting |
| `set_number_format` | `spreadsheet_id`, `range`, `format_type` | Currency/date/percent |
| `merge_cells` | `spreadsheet_id`, `range`, `merge_type` | Merge cells |
| `create_chart` | `spreadsheet_id`, `sheet_id`, `chart_type`, `data_range`, `title` | Bar/line/pie chart |

**Range notation:** `"Sheet1!A1:D10"` or `"A1:B5"` (defaults to first sheet)

### Slides (15 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `create_presentation` | `title` | New presentation |
| `get_presentation` | `presentation_id` | Full presentation data |
| `list_presentations` | `max_results` | All presentations in Drive |
| `get_presentation_text` | `presentation_id` | All text content |
| `get_slide` | `presentation_id`, `slide_id` | Single slide data |
| `add_slide` | `presentation_id`, `layout`, `index` | New slide |
| `delete_slide` | `presentation_id`, `slide_id` | Remove slide |
| `update_slide_text` | `presentation_id`, `slide_id`, `element_id`, `text` | Replace text |
| `add_text_box` | `presentation_id`, `slide_id`, `text`, `x`, `y`, `width`, `height` | Add text box |
| `add_image` | `presentation_id`, `slide_id`, `image_url`, `x`, `y`, `width`, `height` | Embed image |
| `format_text_in_slide` | `presentation_id`, `slide_id`, `element_id`, `bold`, `font_size`, `color` | Format text |
| `set_slide_background` | `presentation_id`, `slide_id`, `color` | Background color |
| `apply_slide_layout` | `presentation_id`, `slide_id`, `layout` | Change layout |
| `create_bulleted_list_slide` | `presentation_id`, `title`, `bullets[]` | Slide with bullet list |
| `add_formatted_text_box` | `presentation_id`, `slide_id`, `text`, `bold`, `font_size`, `color` | Styled text box |

### Tasks (10 tools)

| Tool | Key Parameters | Description |
|------|---------------|-------------|
| `list_task_lists` | — | All task lists |
| `get_task_list` | `tasklist_id` | Single task list |
| `create_task_list` | `title` | New task list |
| `update_task_list` | `tasklist_id`, `title` | Rename list |
| `delete_task_list` | `tasklist_id` | Delete list |
| `list_tasks` | `tasklist_id`, `show_completed` | Tasks in a list |
| `get_task` | `tasklist_id`, `task_id` | Single task |
| `create_task` | `tasklist_id`, `title`, `notes`, `due` | New task |
| `update_task` | `tasklist_id`, `task_id`, `title`, `notes`, `due` | Edit task |
| `complete_task` | `tasklist_id`, `task_id` | Mark complete |
| `delete_task` | `tasklist_id`, `task_id` | Delete task |
| `move_task` | `tasklist_id`, `task_id`, `parent`, `previous` | Reorder/reparent |

---

## Python API Usage

Use the Python API when your code (not Claude) needs to drive Google Workspace — automation scripts, data pipelines, custom integrations.

### Setup

```python
from gworkspace_mcp.auth import OAuthManager
from googleapiclient.discovery import build

manager = OAuthManager()
credentials = manager.get_credentials()
# credentials is google.oauth2.credentials.Credentials
# Ready to pass to any googleapiclient service
```

### Gmail

```python
service = build('gmail', 'v1', credentials=credentials)

# Search messages
results = service.users().messages().list(
    userId='me',
    q='from:boss@company.com is:unread'
).execute()
messages = results.get('messages', [])

# Get full message
msg = service.users().messages().get(
    userId='me',
    id=messages[0]['id'],
    format='full'
).execute()

# Send email
import base64
from email.mime.text import MIMEText

message = MIMEText('Hello World')
message['to'] = 'recipient@example.com'
message['subject'] = 'Test'
raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
service.users().messages().send(
    userId='me',
    body={'raw': raw}
).execute()

# Batch modify labels
service.users().messages().batchModify(
    userId='me',
    body={
        'ids': ['msg1', 'msg2'],
        'addLabelIds': ['STARRED'],
        'removeLabelIds': ['UNREAD']
    }
).execute()
```

### Calendar

```python
service = build('calendar', 'v3', credentials=credentials)

# List upcoming events
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()

events = service.events().list(
    calendarId='primary',
    timeMin=now,
    maxResults=10,
    singleEvents=True,
    orderBy='startTime'
).execute()

# Create event
event = service.events().insert(
    calendarId='primary',
    body={
        'summary': 'Team Meeting',
        'start': {'dateTime': '2024-03-15T10:00:00-07:00'},
        'end': {'dateTime': '2024-03-15T11:00:00-07:00'},
        'attendees': [{'email': 'colleague@company.com'}],
    }
).execute()

# Free/busy query
fb = service.freebusy().query(body={
    'timeMin': '2024-03-15T00:00:00Z',
    'timeMax': '2024-03-16T00:00:00Z',
    'items': [{'id': 'primary'}, {'id': 'other@company.com'}]
}).execute()
```

### Drive

```python
service = build('drive', 'v3', credentials=credentials)

# Search files
results = service.files().list(
    q="mimeType='application/pdf' and modifiedTime > '2024-01-01'",
    fields='files(id, name, size, modifiedTime)',
    pageSize=50
).execute()

# Upload file
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload('report.pdf', mimetype='application/pdf')
file = service.files().create(
    body={'name': 'Q1 Report', 'parents': ['folder_id']},
    media_body=media,
    fields='id'
).execute()

# Download file
from googleapiclient.http import MediaIoBaseDownload
import io

request = service.files().get_media(fileId='file_id')
fh = io.BytesIO()
downloader = MediaIoBaseDownload(fh, request)
done = False
while not done:
    _, done = downloader.next_chunk()

# Export Google Doc as PDF
request = service.files().export_media(
    fileId='doc_id',
    mimeType='application/pdf'
)
```

### Sheets

```python
service = build('sheets', 'v4', credentials=credentials)
ss = service.spreadsheets()

# Read values
result = ss.values().get(
    spreadsheetId='spreadsheet_id',
    range='Sheet1!A1:D10'
).execute()
rows = result.get('values', [])

# Write values
ss.values().update(
    spreadsheetId='spreadsheet_id',
    range='Sheet1!A1',
    valueInputOption='USER_ENTERED',
    body={'values': [['Name', 'Score'], ['Alice', 95], ['Bob', 87]]}
).execute()

# Append rows
ss.values().append(
    spreadsheetId='spreadsheet_id',
    range='Sheet1!A:A',
    valueInputOption='USER_ENTERED',
    body={'values': [['New Row', 'Data']]}
).execute()

# Batch update (formatting, merges, etc.)
ss.batchUpdate(
    spreadsheetId='spreadsheet_id',
    body={'requests': [
        {'repeatCell': {
            'range': {'sheetId': 0, 'startRowIndex': 0, 'endRowIndex': 1},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
            'fields': 'userEnteredFormat.textFormat.bold'
        }}
    ]}
).execute()
```

### Docs

```python
service = build('docs', 'v1', credentials=credentials)

# Read document
doc = service.documents().get(documentId='doc_id').execute()
content = doc.get('body', {}).get('content', [])

# Create document
doc = service.documents().create(
    body={'title': 'New Document'}
).execute()

# Batch update (insert text, format, etc.)
service.documents().batchUpdate(
    documentId='doc_id',
    body={'requests': [
        {'insertText': {
            'location': {'index': 1},
            'text': 'Hello World\n'
        }},
        {'updateTextStyle': {
            'range': {'startIndex': 1, 'endIndex': 6},
            'textStyle': {'bold': True},
            'fields': 'bold'
        }}
    ]}
).execute()
```

### Slides

```python
service = build('slides', 'v1', credentials=credentials)

# Get presentation
prs = service.presentations().get(
    presentationId='prs_id'
).execute()
slides = prs.get('slides', [])

# Create presentation
prs = service.presentations().create(
    body={'title': 'Q1 Review'}
).execute()

# Batch update slides
service.presentations().batchUpdate(
    presentationId='prs_id',
    body={'requests': [
        {'insertText': {
            'objectId': 'element_id',
            'text': 'Updated title'
        }}
    ]}
).execute()
```

---

## Embedding the MCP Server (Advanced)

Run the MCP server programmatically inside your own application:

```python
import asyncio
from gworkspace_mcp.server import GoogleWorkspaceServer, create_server

# Option 1: Quick create
server = create_server()
asyncio.run(server.run())

# Option 2: Full control
server = GoogleWorkspaceServer()
# server.storage  → TokenStorage instance
# server.manager  → OAuthManager instance
# server.server   → underlying mcp.server.Server
asyncio.run(server.run())
```

---

## Combined Patterns

### Pattern 1: Claude discovers, Python processes

```python
# In your code: get credentials
from gworkspace_mcp.auth import OAuthManager
creds = OAuthManager().get_credentials()

# Claude (via MCP): search_gmail_messages query="invoice from:vendor@co.com"
# Claude returns message IDs → pass to Python for bulk processing

from googleapiclient.discovery import build
gmail = build('gmail', 'v1', credentials=creds)
for msg_id in message_ids_from_claude:
    msg = gmail.users().messages().get(userId='me', id=msg_id).execute()
    # custom processing...
```

### Pattern 2: Python automation + Claude narration

```python
# Python creates the spreadsheet and populates data
sheets = build('sheets', 'v4', credentials=creds)
ss = sheets.spreadsheets().create(body={'title': 'Report'}).execute()
sheets.spreadsheets().values().update(
    spreadsheetId=ss['spreadsheetId'],
    range='A1', valueInputOption='USER_ENTERED',
    body={'values': data_rows}
).execute()

# Then Claude (via MCP) formats it:
# format_cells spreadsheetId=... range="A1:Z1" bold=true
# create_chart spreadsheetId=... chart_type="bar" ...
```

### Pattern 3: Token reuse — avoid double authentication

```python
from gworkspace_mcp.auth import OAuthManager, TokenStorage

# Both MCP server and your code share the same token storage
storage = TokenStorage()  # reads .gworkspace-mcp/tokens.json
manager = OAuthManager(storage=storage)
creds = manager.get_credentials()
# No re-authentication needed — same tokens the MCP server uses
```

---

## Error Handling

```python
from gworkspace_mcp.auth import OAuthManager, TokenStatus
from googleapiclient.errors import HttpError

manager = OAuthManager()
status, stored = manager.get_status()

if status == TokenStatus.MISSING:
    raise RuntimeError("Run 'gworkspace-mcp setup' first")
elif status == TokenStatus.EXPIRED:
    token = await manager.refresh_if_needed()
elif status == TokenStatus.INVALID:
    raise RuntimeError("Token corrupted — run 'gworkspace-mcp setup' to re-authenticate")

try:
    result = service.users().messages().list(userId='me', q='...').execute()
except HttpError as e:
    if e.resp.status == 401:
        # Token expired mid-session — refresh and retry
        await manager.refresh_if_needed()
    elif e.resp.status == 429:
        # Rate limited — back off
        import time; time.sleep(2)
    else:
        raise
```

---

## Quick Reference

```python
# Auth
from gworkspace_mcp.auth import OAuthManager, TokenStatus, GOOGLE_WORKSPACE_SCOPES
manager = OAuthManager()
creds = manager.get_credentials()         # → google.oauth2.credentials.Credentials
status, stored = manager.get_status()     # → (TokenStatus, StoredToken | None)
await manager.refresh_if_needed()         # → refreshes if expired

# Server
from gworkspace_mcp.server import create_server, GoogleWorkspaceServer
server = create_server()

# Build any Google service client
from googleapiclient.discovery import build
gmail   = build('gmail',         'v1', credentials=creds)
cal     = build('calendar',      'v3', credentials=creds)
drive   = build('drive',         'v3', credentials=creds)
docs    = build('docs',          'v1', credentials=creds)
sheets  = build('sheets',        'v4', credentials=creds)
slides  = build('slides',        'v1', credentials=creds)
tasks   = build('tasks',         'v1', credentials=creds)
```
