# Drive API Reference

Complete reference for the 17 Drive tools provided by google-workspace-mcp.

## Overview

Drive tools enable file search, upload, download, and folder management.

| Category | Tools |
|----------|-------|
| Read | `search_drive_files`, `get_drive_file_content` |
| Write | `create_drive_folder`, `upload_drive_file`, `delete_drive_file`, `move_drive_file` |
| Sync (rclone) | `list_drive_contents`, `download_drive_folder`, `upload_to_drive`, `sync_drive_folder` |

**Note**: Tools marked "rclone" require [rclone](https://rclone.org/) to be installed.

---

## Read Operations

### search_drive_files

Search Google Drive files using query string.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `max_results` | integer | No | 10 | Maximum files to return |

**Query Syntax**:

Simple search (auto-wrapped in `fullText contains`):
```json
{
  "query": "quarterly report"
}
```

Drive API query syntax:
```json
{
  "query": "name contains 'report' and mimeType = 'application/pdf'"
}
```

**Query Examples**:

| Query | Description |
|-------|-------------|
| `name contains 'report'` | Files with "report" in name |
| `fullText contains 'budget'` | Files containing "budget" |
| `mimeType = 'application/pdf'` | PDF files only |
| `mimeType = 'application/vnd.google-apps.folder'` | Folders only |
| `mimeType = 'application/vnd.google-apps.document'` | Google Docs |
| `mimeType = 'application/vnd.google-apps.spreadsheet'` | Google Sheets |
| `modifiedTime > '2024-01-01'` | Modified after date |
| `'folder_id' in parents` | Files in specific folder |
| `trashed = false` | Not in trash |
| `starred = true` | Starred files |
| `sharedWithMe = true` | Shared with you |

**Combined queries**:
```
name contains 'Q4' and mimeType = 'application/pdf' and modifiedTime > '2024-01-01'
```

**Returns**: List of files with:
- `id`: File ID (use for other operations)
- `name`: File name
- `mimeType`: File type
- `modifiedTime`: Last modified
- `size`: File size (bytes)
- `webViewLink`: Link to view in browser
- `parents`: Parent folder IDs

---

### get_drive_file_content

Get the content of a text file by ID.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | string | Yes | Google Drive file ID |

**Example**:
```json
{
  "file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
}
```

**Returns**: File content as text.

**Supported file types**:
- Plain text files (`.txt`, `.md`, `.csv`, etc.)
- Google Docs (exported as plain text)

**Note**: For binary files (images, PDFs), use `download_drive_folder` instead.

---

## Write Operations

### create_drive_folder

Create a new folder in Google Drive.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Folder name |
| `parent_id` | string | No | Parent folder ID (root if not specified) |

**Example - Root folder**:
```json
{
  "name": "New Project"
}
```

**Example - Nested folder**:
```json
{
  "name": "Documents",
  "parent_id": "1abc123def456"
}
```

**Returns**: Created folder ID and details.

---

### upload_drive_file

Upload a text file to Google Drive.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | File name |
| `content` | string | Yes | - | File content (text) |
| `mime_type` | string | No | "text/plain" | MIME type |
| `parent_id` | string | No | - | Parent folder ID |

**Example**:
```json
{
  "name": "meeting-notes.md",
  "content": "# Meeting Notes\n\n## Date: 2024-01-15\n\n- Item 1\n- Item 2",
  "mime_type": "text/markdown",
  "parent_id": "1abc123def456"
}
```

**Common MIME types**:

| Type | MIME Type |
|------|-----------|
| Plain text | `text/plain` |
| Markdown | `text/markdown` |
| CSV | `text/csv` |
| JSON | `application/json` |
| HTML | `text/html` |

**Returns**: Uploaded file ID and details.

**Note**: For binary files or large uploads, use `upload_to_drive` instead.

---

### delete_drive_file

Delete a file or folder from Google Drive.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | string | Yes | File or folder ID to delete |

**Example**:
```json
{
  "file_id": "1abc123def456"
}
```

**Returns**: Confirmation of deletion.

**Warning**:
- Deleting a folder deletes all contents
- This action bypasses trash and is permanent

---

### move_drive_file

Move a file to a different folder.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_id` | string | Yes | File ID to move |
| `new_parent_id` | string | Yes | Destination folder ID |

**Example**:
```json
{
  "file_id": "1abc123def456",
  "new_parent_id": "1xyz789ghi012"
}
```

**Returns**: Updated file details.

---

## Rclone Operations

These tools require [rclone](https://rclone.org/) to be installed. They enable advanced file sync operations.

### list_drive_contents

List contents of a Drive folder with detailed metadata.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `path` | string | No | "" | Drive path (e.g., "Documents/Reports") |
| `recursive` | boolean | No | false | List subdirectories |
| `files_only` | boolean | No | false | Show only files |
| `include_hash` | boolean | No | false | Include MD5 hash |
| `max_depth` | integer | No | -1 | Max recursion depth |

**Example**:
```json
{
  "path": "Projects/2024",
  "recursive": true,
  "max_depth": 2
}
```

**Returns**: Structured JSON with:
- File path
- Size
- Modification time
- File ID
- MD5 hash (if requested)

---

### download_drive_folder

Download a folder from Drive to local filesystem.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `drive_path` | string | Yes | - | Path in Google Drive |
| `local_path` | string | Yes | - | Local destination |
| `google_docs_format` | string | No | "docx" | Export format for Google Docs |
| `exclude` | array | No | - | Patterns to exclude |
| `dry_run` | boolean | No | false | Preview without downloading |

**Example**:
```json
{
  "drive_path": "Projects/Reports",
  "local_path": "/Users/me/Downloads/Reports",
  "google_docs_format": "pdf",
  "exclude": ["*.tmp", ".DS_Store"],
  "dry_run": true
}
```

**Export formats**:

| Format | Extension | Best For |
|--------|-----------|----------|
| `docx` | .docx | Microsoft Word |
| `pdf` | .pdf | Archival |
| `odt` | .odt | LibreOffice |
| `txt` | .txt | Plain text |
| `xlsx` | .xlsx | Spreadsheets |
| `csv` | .csv | Data export |
| `pptx` | .pptx | Presentations |

**Returns**: Download summary with file counts and sizes.

---

### upload_to_drive

Upload a local folder to Google Drive.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `local_path` | string | Yes | - | Local folder path |
| `drive_path` | string | Yes | - | Destination in Drive |
| `convert_to_google_docs` | boolean | No | false | Convert Office files |
| `exclude` | array | No | - | Patterns to exclude |
| `dry_run` | boolean | No | false | Preview without uploading |

**Example**:
```json
{
  "local_path": "/Users/me/Documents/Project",
  "drive_path": "Projects/New Project",
  "exclude": ["node_modules/**", ".git/**", "*.log"],
  "dry_run": false
}
```

**Returns**: Upload summary.

---

### sync_drive_folder

Sync files between local filesystem and Google Drive.

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `source` | string | Yes | - | Source path |
| `destination` | string | Yes | - | Destination path |
| `dry_run` | boolean | No | true | Preview changes |
| `delete_extra` | boolean | No | false | Delete files not in source |
| `exclude` | array | No | - | Patterns to exclude |
| `include` | array | No | - | Patterns to include |

**Path formats**:
- Local: `/Users/me/Documents/Project`
- Drive: `drive:Projects/Project`

**Example - Download sync (Drive to local)**:
```json
{
  "source": "drive:Projects/Active",
  "destination": "/Users/me/Projects/Active",
  "dry_run": true
}
```

**Example - Upload sync (local to Drive)**:
```json
{
  "source": "/Users/me/Projects/Active",
  "destination": "drive:Projects/Active",
  "exclude": ["node_modules/**", ".git/**"],
  "dry_run": true
}
```

**Returns**: Sync summary showing files transferred, updated, and deleted.

**Warning**: Use `dry_run: true` first to preview changes. Setting `delete_extra: true` will permanently delete files in the destination that don't exist in the source.

---

## Common Workflows

### Backup Project to Drive

```
1. upload_to_drive(
     local_path="/path/to/project",
     drive_path="Backups/ProjectName",
     exclude=["node_modules/**", ".git/**", "*.log"]
   )
```

### Organize Files

```
1. search_drive_files(query="name contains 'invoice'")
2. create_drive_folder(name="Invoices/2024")
3. move_drive_file(file_id=..., new_parent_id=...)
```

### Download Project Files

```
1. list_drive_contents(path="Projects/Current", recursive=true)
2. download_drive_folder(
     drive_path="Projects/Current",
     local_path="/path/to/local",
     dry_run=true
   )
3. download_drive_folder(..., dry_run=false)  # Execute after review
```

### Mirror Local Folder to Drive

```
1. sync_drive_folder(
     source="/local/folder",
     destination="drive:Remote/Folder",
     dry_run=true
   )
2. Review changes
3. sync_drive_folder(..., dry_run=false)
```

## File ID Discovery

### From URL

Google Drive URLs contain the file ID:

```
https://drive.google.com/file/d/1abc123def456/view
                              ^^^^^^^^^^^^^^^ File ID

https://docs.google.com/document/d/1xyz789ghi012/edit
                                   ^^^^^^^^^^^^^^^ Document ID
```

### From Search

Use `search_drive_files` to find file IDs:

```json
{
  "query": "name = 'Quarterly Report.pdf'"
}
```

## Related Documentation

- [Gmail API](gmail.md)
- [Calendar API](calendar.md)
- [Docs API](docs.md)
- [Tasks API](tasks.md)
