# Gmail API Reference

Complete reference for the 18 Gmail tools provided by gworkspace-mcp.

## Overview

Gmail tools enable email search, composition, organization, and batch operations.

| Category | Tools |
|----------|-------|
| Read | `search_gmail_messages`, `get_gmail_message_content` |
| Compose | `send_email`, `reply_to_email`, `create_draft` |
| Labels | `list_gmail_labels`, `create_gmail_label`, `delete_gmail_label`, `modify_gmail_message` |
| Organize | `archive_gmail_message`, `trash_gmail_message`, `untrash_gmail_message` |
| Status | `mark_gmail_as_read`, `mark_gmail_as_unread`, `star_gmail_message`, `unstar_gmail_message` |
| Batch | `batch_modify_gmail_messages`, `batch_archive_gmail_messages`, `batch_trash_gmail_messages`, `batch_mark_gmail_as_read`, `batch_delete_gmail_messages` |

---

## Read Operations

### search_gmail_messages

Search Gmail messages using Gmail query syntax.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Gmail search query |
| `max_results` | integer | No | 10 | Maximum messages to return |

**Query Syntax Examples**:

| Query | Description |
|-------|-------------|
| `from:user@example.com` | Emails from specific sender |
| `to:user@example.com` | Emails to specific recipient |
| `subject:meeting` | Subject contains "meeting" |
| `is:unread` | Unread emails |
| `is:starred` | Starred emails |
| `has:attachment` | Emails with attachments |
| `after:2024/01/01` | Emails after date |
| `before:2024/12/31` | Emails before date |
| `newer_than:7d` | Emails from last 7 days |
| `older_than:30d` | Emails older than 30 days |
| `label:work` | Emails with label |
| `in:inbox` | Emails in inbox |
| `in:sent` | Sent emails |

**Combined queries**:
```
from:boss@company.com subject:urgent is:unread
newer_than:7d has:attachment filename:pdf
```

**Example**:
```json
{
  "query": "from:john@example.com subject:project newer_than:30d",
  "max_results": 20
}
```

**Returns**: List of message summaries with ID, subject, from, date, and snippet.

---

### get_gmail_message_content

Get the full content of a Gmail message by ID.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Gmail message ID |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

**Returns**: Full message content including headers, body (plain text and HTML), and attachment info.

---

## Compose Operations

### send_email

Send a new email message.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to` | string | Yes | Recipient(s), comma-separated |
| `subject` | string | Yes | Email subject |
| `body` | string | Yes | Email body (plain text) |
| `cc` | string | No | CC recipients, comma-separated |
| `bcc` | string | No | BCC recipients, comma-separated |

**Example**:
```json
{
  "to": "john@example.com, jane@example.com",
  "subject": "Meeting Tomorrow",
  "body": "Hi team,\n\nReminder about our meeting tomorrow at 10am.\n\nBest,\nSender",
  "cc": "manager@example.com"
}
```

**Returns**: Sent message ID and confirmation.

---

### reply_to_email

Reply to an existing email thread.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Original message ID to reply to |
| `body` | string | Yes | Reply body (plain text) |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd",
  "body": "Thanks for the update. I'll review and get back to you."
}
```

**Returns**: Reply message ID and confirmation.

**Note**: The reply maintains the thread and uses "Re:" prefix automatically.

---

### create_draft

Create an email draft.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to` | string | Yes | Recipient(s), comma-separated |
| `subject` | string | Yes | Email subject |
| `body` | string | Yes | Email body (plain text) |
| `cc` | string | No | CC recipients |
| `bcc` | string | No | BCC recipients |

**Example**:
```json
{
  "to": "team@example.com",
  "subject": "Weekly Update - Draft",
  "body": "This week's accomplishments:\n\n1. ...\n2. ..."
}
```

**Returns**: Draft ID and confirmation.

---

## Label Operations

### list_gmail_labels

List all Gmail labels (system and custom).

**Parameters**: None

**Example**:
```json
{}
```

**Returns**: List of labels with:
- `id`: Label ID (use this for other operations)
- `name`: Display name
- `type`: "system" or "user"
- `messageListVisibility`: Visibility setting
- `labelListVisibility`: Visibility setting

**Common System Labels**:

| Label ID | Purpose |
|----------|---------|
| `INBOX` | Inbox |
| `SENT` | Sent mail |
| `DRAFT` | Drafts |
| `TRASH` | Trash |
| `SPAM` | Spam |
| `STARRED` | Starred |
| `IMPORTANT` | Important |
| `UNREAD` | Unread marker |
| `CATEGORY_PERSONAL` | Personal category |
| `CATEGORY_SOCIAL` | Social category |
| `CATEGORY_PROMOTIONS` | Promotions category |
| `CATEGORY_UPDATES` | Updates category |
| `CATEGORY_FORUMS` | Forums category |

---

### create_gmail_label

Create a custom Gmail label.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Label name (use `/` for nesting) |
| `label_list_visibility` | string | No | `labelShow`, `labelShowIfUnread`, `labelHide` |
| `message_list_visibility` | string | No | `show`, `hide` |

**Example**:
```json
{
  "name": "Work/Projects/Active",
  "label_list_visibility": "labelShow",
  "message_list_visibility": "show"
}
```

**Returns**: Created label ID and details.

**Note**: Nested labels use `/` separator. Parent labels are created automatically if needed.

---

### delete_gmail_label

Delete a custom Gmail label.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `label_id` | string | Yes | Label ID to delete |

**Example**:
```json
{
  "label_id": "Label_123456"
}
```

**Returns**: Confirmation of deletion.

**Note**: System labels cannot be deleted. Messages with the deleted label are not deleted.

---

### modify_gmail_message

Add or remove labels from a message.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID to modify |
| `add_label_ids` | array | No | Label IDs to add |
| `remove_label_ids` | array | No | Label IDs to remove |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd",
  "add_label_ids": ["STARRED", "Label_123"],
  "remove_label_ids": ["UNREAD"]
}
```

**Returns**: Updated message details.

---

## Organize Operations

### archive_gmail_message

Archive a message (remove from inbox, keep in All Mail).

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID to archive |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

**Returns**: Confirmation.

**Note**: Archived messages are accessible via search or All Mail.

---

### trash_gmail_message

Move a message to trash.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID to trash |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

**Returns**: Confirmation.

**Note**: Trashed messages are automatically deleted after 30 days.

---

### untrash_gmail_message

Restore a message from trash.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID to restore |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

**Returns**: Confirmation.

---

## Status Operations

### mark_gmail_as_read

Mark a message as read.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

---

### mark_gmail_as_unread

Mark a message as unread.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

---

### star_gmail_message

Add a star to a message.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

---

### unstar_gmail_message

Remove star from a message.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message ID |

**Example**:
```json
{
  "message_id": "18d5e7f1234abcd"
}
```

---

## Batch Operations

Batch operations are more efficient for bulk actions, using Gmail's batch API.

### batch_modify_gmail_messages

Add or remove labels from multiple messages.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_ids` | array | Yes | List of message IDs |
| `add_label_ids` | array | No | Labels to add |
| `remove_label_ids` | array | No | Labels to remove |

**Example**:
```json
{
  "message_ids": ["msg1", "msg2", "msg3"],
  "add_label_ids": ["Label_Work"],
  "remove_label_ids": ["UNREAD"]
}
```

---

### batch_archive_gmail_messages

Archive multiple messages at once.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_ids` | array | Yes | List of message IDs to archive |

**Example**:
```json
{
  "message_ids": ["msg1", "msg2", "msg3", "msg4", "msg5"]
}
```

---

### batch_trash_gmail_messages

Move multiple messages to trash.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_ids` | array | Yes | List of message IDs to trash |

**Example**:
```json
{
  "message_ids": ["msg1", "msg2", "msg3"]
}
```

---

### batch_mark_gmail_as_read

Mark multiple messages as read.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_ids` | array | Yes | List of message IDs |

**Example**:
```json
{
  "message_ids": ["msg1", "msg2", "msg3"]
}
```

---

### batch_delete_gmail_messages

Permanently delete multiple messages.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_ids` | array | Yes | List of message IDs to delete |

**Example**:
```json
{
  "message_ids": ["msg1", "msg2"]
}
```

**Warning**: This permanently deletes messages. They cannot be recovered. Use `batch_trash_gmail_messages` for recoverable deletion.

---

## Common Workflows

### Email Triage

```
1. search_gmail_messages(query="is:unread newer_than:1d")
2. Review messages
3. batch_mark_gmail_as_read(message_ids=[...])
4. batch_archive_gmail_messages(message_ids=[...]) for processed emails
```

### Newsletter Management

```
1. create_gmail_label(name="Newsletters")
2. search_gmail_messages(query="from:newsletter@example.com")
3. batch_modify_gmail_messages(message_ids=[...], add_label_ids=["Label_xxx"])
```

### Inbox Zero

```
1. search_gmail_messages(query="in:inbox older_than:7d")
2. batch_archive_gmail_messages(message_ids=[...])
```

## Related Documentation

- [Calendar API](calendar.md)
- [Drive API](drive.md)
- [Docs API](docs.md)
- [Tasks API](tasks.md)
