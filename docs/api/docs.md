# Docs API Reference

Complete reference for the 11 Docs tools provided by gworkspace-mcp.

## Overview

Docs tools enable creating, reading, and editing Google Docs, including tab management and comment features.

| Category | Tools |
|----------|-------|
| Document Operations | `create_document`, `get_document`, `append_to_document` |
| Content Conversion | `upload_markdown_as_doc`, `render_mermaid_to_doc` |
| Tab Management | `list_document_tabs`, `get_tab_content`, `create_document_tab`, `update_tab_properties`, `move_tab` |
| Comments | `list_document_comments`, `add_document_comment`, `reply_to_comment` |

---

## Document Operations

### create_document

Create a new Google Doc.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | Document title |

**Example**:
```json
{
  "title": "Project Proposal - Q1 2024"
}
```

**Returns**:
- `documentId`: Document ID (use for other operations)
- `title`: Document title
- `revisionId`: Initial revision ID
- `documentUrl`: Link to open in browser

---

### get_document

Get the content and structure of a Google Doc.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `document_id` | string | Yes | - | Google Doc ID |
| `include_tabs_content` | boolean | No | false | Include tab content |

**Example**:
```json
{
  "document_id": "1abc123def456xyz"
}
```

**With tabs**:
```json
{
  "document_id": "1abc123def456xyz",
  "include_tabs_content": true
}
```

**Returns**:
- `title`: Document title
- `body`: Document body content
- `tabs`: Tab information (if requested)
- `namedStyles`: Style definitions
- `revisionId`: Current revision

---

### append_to_document

Append text to the end of an existing Google Doc.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Google Doc ID |
| `text` | string | Yes | Text to append |

**Example**:
```json
{
  "document_id": "1abc123def456xyz",
  "text": "\n\n## Meeting Notes - January 15\n\n- Discussed project timeline\n- Action items assigned"
}
```

**Returns**: Confirmation and updated document info.

**Note**: Text is appended at the very end of the document.

---

## Content Conversion

### upload_markdown_as_doc

Convert Markdown content to Google Docs format and upload to Drive.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Document name (no extension) |
| `markdown_content` | string | Yes | - | Markdown content |
| `parent_id` | string | No | - | Parent folder ID in Drive |
| `output_format` | string | No | "gdoc" | `gdoc` or `docx` |

**Example**:
```json
{
  "name": "Technical Specification",
  "markdown_content": "# Technical Specification\n\n## Overview\n\nThis document describes...\n\n## Requirements\n\n- Feature A\n- Feature B\n\n## Architecture\n\n```python\ndef main():\n    pass\n```",
  "output_format": "gdoc"
}
```

**Returns**:
- `file_id`: Created file ID
- `web_view_link`: Link to open document

**Requirements**: [pandoc](https://pandoc.org/) must be installed.

**Supported Markdown features**:
- Headers (H1-H6)
- Bold, italic, strikethrough
- Lists (ordered and unordered)
- Code blocks (syntax highlighting)
- Links and images
- Tables
- Blockquotes

---

### render_mermaid_to_doc

Render a Mermaid diagram and insert it into a Google Doc.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `document_id` | string | Yes | - | Target Google Doc ID |
| `mermaid_code` | string | Yes | - | Mermaid diagram code |
| `insert_index` | integer | No | - | Insert position (end if not specified) |
| `image_format` | string | No | "svg" | `svg` or `png` |
| `width_pt` | integer | No | - | Image width in points |
| `height_pt` | integer | No | - | Image height in points |

**Example - Flowchart**:
```json
{
  "document_id": "1abc123def456xyz",
  "mermaid_code": "graph TD\n    A[Start] --> B{Decision}\n    B -->|Yes| C[Action 1]\n    B -->|No| D[Action 2]\n    C --> E[End]\n    D --> E",
  "image_format": "svg"
}
```

**Example - Sequence diagram**:
```json
{
  "document_id": "1abc123def456xyz",
  "mermaid_code": "sequenceDiagram\n    participant A as User\n    participant B as System\n    A->>B: Request\n    B-->>A: Response"
}
```

**Example - Class diagram**:
```json
{
  "document_id": "1abc123def456xyz",
  "mermaid_code": "classDiagram\n    class User {\n        +String name\n        +login()\n    }"
}
```

**Returns**: Confirmation with image details.

**Requirements**: [@mermaid-js/mermaid-cli](https://github.com/mermaid-js/mermaid-cli) must be installed.

**Supported diagram types**:
- Flowcharts
- Sequence diagrams
- Class diagrams
- State diagrams
- Entity relationship diagrams
- Gantt charts
- Pie charts

---

## Tab Management

Google Docs can have multiple tabs (similar to browser tabs). These tools manage document tabs.

### list_document_tabs

List all tabs in a Google Doc.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Google Doc ID |

**Example**:
```json
{
  "document_id": "1abc123def456xyz"
}
```

**Returns**: List of tabs with:
- `tabId`: Tab ID (use for other operations)
- `title`: Tab title
- `index`: Tab position
- `nestingLevel`: Nesting depth (0 = root)
- `iconEmoji`: Tab icon emoji
- `parentTabId`: Parent tab ID (for nested tabs)

---

### get_tab_content

Get content from a specific tab.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Google Doc ID |
| `tab_id` | string | Yes | Tab ID |

**Example**:
```json
{
  "document_id": "1abc123def456xyz",
  "tab_id": "t.abc123"
}
```

**Returns**:
- Tab metadata (title, index, etc.)
- Tab text content

---

### create_document_tab

Create a new tab in a Google Doc.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Google Doc ID |
| `title` | string | Yes | Tab title |
| `icon_emoji` | string | No | Tab icon emoji |
| `parent_tab_id` | string | No | Parent tab for nesting |
| `index` | integer | No | Position (0 = first) |

**Example - Simple tab**:
```json
{
  "document_id": "1abc123def456xyz",
  "title": "Requirements"
}
```

**Example - Tab with emoji**:
```json
{
  "document_id": "1abc123def456xyz",
  "title": "Design",
  "icon_emoji": "🎨"
}
```

**Example - Nested tab**:
```json
{
  "document_id": "1abc123def456xyz",
  "title": "Subtopic",
  "parent_tab_id": "t.parent123",
  "index": 0
}
```

**Returns**: New tab ID and details.

---

### update_tab_properties

Update tab title or icon.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Google Doc ID |
| `tab_id` | string | Yes | Tab ID to update |
| `title` | string | No | New title |
| `icon_emoji` | string | No | New icon emoji |

**Example**:
```json
{
  "document_id": "1abc123def456xyz",
  "tab_id": "t.abc123",
  "title": "Updated Requirements",
  "icon_emoji": "📋"
}
```

**Returns**: Confirmation.

---

### move_tab

Move a tab to a new position or parent.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | Yes | Google Doc ID |
| `tab_id` | string | Yes | Tab ID to move |
| `new_parent_tab_id` | string | No | New parent (empty = root) |
| `new_index` | integer | No | New position |

**Example - Move to root**:
```json
{
  "document_id": "1abc123def456xyz",
  "tab_id": "t.abc123",
  "new_parent_tab_id": "",
  "new_index": 0
}
```

**Example - Nest under parent**:
```json
{
  "document_id": "1abc123def456xyz",
  "tab_id": "t.abc123",
  "new_parent_tab_id": "t.parent456"
}
```

**Returns**: Confirmation.

---

## Comments

### list_document_comments

List all comments on a Google Doc.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `file_id` | string | Yes | - | Document file ID |
| `include_deleted` | boolean | No | false | Include deleted comments |
| `max_results` | integer | No | 100 | Maximum comments |

**Example**:
```json
{
  "file_id": "1abc123def456xyz"
}
```

**Returns**: List of comments with:
- `id`: Comment ID
- `content`: Comment text
- `author`: Author info
- `createdTime`: Creation time
- `modifiedTime`: Last modified
- `resolved`: Whether resolved
- `replies`: List of replies

---

### add_document_comment

Add a new comment to a document.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | string | Yes | Document file ID |
| `content` | string | Yes | Comment text |
| `anchor` | string | No | JSON anchor location |

**Example**:
```json
{
  "file_id": "1abc123def456xyz",
  "content": "Consider adding more detail to this section."
}
```

**Returns**: Created comment ID and details.

**Style guidelines for comments**:
- Be brief and direct (1-2 sentences)
- Focus on specific, actionable feedback
- Use imperative mood ("Add error handling" not "You might want to add...")

---

### reply_to_comment

Reply to an existing comment.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | string | Yes | Document file ID |
| `comment_id` | string | Yes | Comment ID to reply to |
| `content` | string | Yes | Reply text |

**Example**:
```json
{
  "file_id": "1abc123def456xyz",
  "comment_id": "AABBCC123",
  "content": "Done. Added the requested details."
}
```

**Returns**: Created reply ID and details.

---

## Common Workflows

### Create Documentation from Markdown

```
1. upload_markdown_as_doc(
     name="API Documentation",
     markdown_content="# API Docs\n\n..."
   )
```

### Add Architecture Diagram to Doc

```
1. render_mermaid_to_doc(
     document_id="...",
     mermaid_code="graph TD\n    A-->B"
   )
```

### Organize Large Document with Tabs

```
1. create_document(title="Project Documentation")
2. create_document_tab(document_id=..., title="Overview", icon_emoji="📖")
3. create_document_tab(document_id=..., title="Technical Specs", icon_emoji="⚙️")
4. create_document_tab(document_id=..., title="Timeline", icon_emoji="📅")
```

### Review Document Comments

```
1. list_document_comments(file_id="...")
2. Review each comment
3. reply_to_comment(file_id=..., comment_id=..., content="Addressed")
```

## Document ID Discovery

### From URL

Google Docs URLs contain the document ID:

```
https://docs.google.com/document/d/1abc123def456xyz/edit
                                   ^^^^^^^^^^^^^^^^ Document ID
```

### From Drive Search

```json
{
  "query": "name = 'Project Proposal' and mimeType = 'application/vnd.google-apps.document'"
}
```

## Related Documentation

- [Gmail API](gmail.md)
- [Calendar API](calendar.md)
- [Drive API](drive.md)
- [Tasks API](tasks.md)
