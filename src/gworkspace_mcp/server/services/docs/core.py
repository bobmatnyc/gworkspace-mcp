"""Google Docs core sub-module: create, read, append, and tab management."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx
from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

logger = logging.getLogger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="create_document",
        description="Create a new Google Doc with the given title. Returns the document ID and URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="append_to_document",
        description="Append plain text to the end of an existing Google Doc. Requires document_id and text.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "text": {
                    "type": "string",
                    "description": "Text to append",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "text"],
        },
    ),
    Tool(
        name="get_document",
        description="Get the content and structure of a Google Doc. Optionally include tab content for documents with multiple tabs.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "include_tabs_content": {
                    "type": "boolean",
                    "description": "Whether to include tab content (default: False). Set to True for documents with tabs.",
                    "default": False,
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="manage_document_tabs",
        description=(
            "Manage tabs in a Google Doc. Actions: "
            "'list' — list all tabs with metadata; "
            "'get_content' — get text content of a specific tab; "
            "'create' — create a new tab; "
            "'update' — update tab title or icon; "
            "'move' — move tab to a new position or parent."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "get_content", "create", "update", "move"],
                    "description": "Operation to perform on document tabs",
                },
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID (required for get_content, update, move)",
                },
                "title": {
                    "type": "string",
                    "description": "Tab title (required for create, optional for update)",
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "Icon emoji for the tab (create/update only, optional)",
                },
                "parent_tab_id": {
                    "type": "string",
                    "description": "Parent tab ID for nested tabs (create/move only, optional)",
                },
                "index": {
                    "type": "integer",
                    "description": "Position index for the tab (create/move only, optional)",
                },
                "new_parent_tab_id": {
                    "type": "string",
                    "description": "New parent tab ID for move action. Use empty string to move to root level.",
                },
                "new_index": {
                    "type": "integer",
                    "description": "New position index for move action",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action", "document_id"],
        },
    ),
    Tool(
        name="get_document_structure",
        description=(
            "Return a structured paragraph list from a Google Doc body, with start/end indices "
            "for each paragraph. This is the prerequisite for index-based editing tools "
            "(insert_text_in_document, delete_range_in_document, move_paragraph_in_document, "
            "format_paragraph_in_document). Also returns table indices and document title."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="replace_text_in_document",
        description=(
            "Find-and-replace text throughout a Google Doc using replaceAllText batchUpdate. "
            "Returns the count of replacements made."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "find_text": {
                    "type": "string",
                    "description": "Text to find",
                },
                "replace_text": {
                    "type": "string",
                    "description": "Replacement text",
                },
                "match_case": {
                    "type": "boolean",
                    "description": "Case-sensitive matching (default: True)",
                    "default": True,
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "find_text", "replace_text"],
        },
    ),
    Tool(
        name="insert_text_in_document",
        description=(
            "Insert text at a specific document index. Use get_document_structure to find valid "
            "indices."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "text": {
                    "type": "string",
                    "description": "Text to insert",
                },
                "index": {
                    "type": "integer",
                    "description": "Document index position",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "text", "index"],
        },
    ),
    Tool(
        name="delete_range_in_document",
        description=(
            "Delete content between startIndex and endIndex in a Google Doc using "
            "deleteContentRange batchUpdate."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "start_index": {
                    "type": "integer",
                    "description": "Start index (inclusive)",
                },
                "end_index": {
                    "type": "integer",
                    "description": "End index (exclusive)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "start_index", "end_index"],
        },
    ),
    Tool(
        name="move_paragraph_in_document",
        description=(
            "Move a paragraph from one location to another within a Google Doc. This is a "
            "cut-and-paste operation: the source range text is read, inserted at the destination, "
            "and the original range is deleted. Use get_document_structure to find indices."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "source_start_index": {
                    "type": "integer",
                    "description": "startIndex of the paragraph to move",
                },
                "source_end_index": {
                    "type": "integer",
                    "description": "endIndex of the paragraph to move",
                },
                "destination_index": {
                    "type": "integer",
                    "description": "Where to insert the paragraph",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": [
                "document_id",
                "source_start_index",
                "source_end_index",
                "destination_index",
            ],
        },
    ),
    Tool(
        name="format_paragraph_in_document",
        description=(
            "Apply paragraph-level formatting to a range using updateParagraphStyle batchUpdate. "
            "Supports heading style, alignment, indentation, and spacing. At least one formatting "
            "option must be provided."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "start_index": {
                    "type": "integer",
                    "description": "Start index of the paragraph range",
                },
                "end_index": {
                    "type": "integer",
                    "description": "End index of the paragraph range",
                },
                "heading_style": {
                    "type": "string",
                    "description": "Named style: NORMAL_TEXT, HEADING_1..HEADING_6, TITLE, SUBTITLE",
                },
                "alignment": {
                    "type": "string",
                    "enum": ["START", "CENTER", "END", "JUSTIFIED"],
                    "description": "Paragraph alignment",
                },
                "indent_first_line_pt": {
                    "type": "number",
                    "description": "First line indent in points",
                },
                "indent_start_pt": {
                    "type": "number",
                    "description": "Left indent in points",
                },
                "space_above_pt": {
                    "type": "number",
                    "description": "Space before paragraph in points",
                },
                "space_below_pt": {
                    "type": "number",
                    "description": "Space after paragraph in points",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "start_index", "end_index"],
        },
    ),
    Tool(
        name="create_document_tab",
        description="Create a new tab in a Google Doc. Requires document_id and title. Optionally specify icon_emoji, parent_tab_id, or index. Prefer manage_document_tabs action='create' for consistency.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "title": {
                    "type": "string",
                    "description": "Tab title",
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "Icon emoji for the tab (optional)",
                },
                "parent_tab_id": {
                    "type": "string",
                    "description": "Parent tab ID for nested tabs (optional)",
                },
                "index": {
                    "type": "integer",
                    "description": "Position index for the tab (optional)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "title"],
        },
    ),
]


# =============================================================================
# Helper functions (shared with other docs sub-modules)
# =============================================================================


def _extract_doc_text(body: dict[str, Any]) -> str:
    """Extract plain text from a Google Docs body structure."""
    text_parts = []
    for element in body.get("content", []):
        if "paragraph" in element:
            for para_element in element["paragraph"].get("elements", []):
                if "textRun" in para_element:
                    text_parts.append(para_element["textRun"].get("content", ""))
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    cell_text = _extract_doc_text(cell)
                    if cell_text:
                        text_parts.append(cell_text)
                        text_parts.append("\t")
                text_parts.append("\n")
    return "".join(text_parts)


def _extract_tables(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract table structural indices from a Google Docs body.

    Why: ``apply_table_style`` and ``format_table_cells`` need ``table_start_index``,
    but ``get_document`` previously only returned a flattened text string —
    callers had no way to discover the table indices. Surfacing them here
    closes that gap without an extra round-trip.
    What: Iterates ``body.content`` looking for elements containing a ``table``
    field. For each, records ``table_start_index`` (the element's startIndex),
    ``num_rows``, ``num_columns``, and a short ``section_hint`` made from text
    of the immediately preceding paragraph (helps callers identify which
    table is which when several appear in the same doc).
    Test: Build a fake body with a paragraph followed by a table element with
    rows=3, columns=2, startIndex=42; assert the returned list has one entry
    with table_start_index=42, num_rows=3, num_columns=2, and a non-empty
    section_hint drawn from the paragraph text.
    """
    tables: list[dict[str, Any]] = []
    content = body.get("content", []) or []
    prev_text = ""

    for element in content:
        if "paragraph" in element:
            # Capture text from this paragraph for use as the next table's hint.
            para_parts: list[str] = []
            for para_element in element["paragraph"].get("elements", []):
                if "textRun" in para_element:
                    para_parts.append(para_element["textRun"].get("content", ""))
            collected = "".join(para_parts).strip()
            if collected:
                prev_text = collected
            continue

        if "table" in element:
            table = element["table"]
            tables.append(
                {
                    "table_start_index": element.get("startIndex"),
                    "num_rows": table.get("rows"),
                    "num_columns": table.get("columns"),
                    # Trim to keep responses compact while still useful.
                    "section_hint": prev_text[:200],
                }
            )
            # Tables don't contribute to the next hint; reset to avoid stale text.
            prev_text = ""

    return tables


def _format_tabs(tabs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format tab information for response."""
    formatted_tabs = []
    for tab in tabs:
        tab_props = tab.get("tabProperties", {})
        formatted_tab: dict[str, Any] = {
            "tab_id": tab_props.get("tabId"),
            "title": tab_props.get("title", ""),
            "index": tab_props.get("index", 0),
            "nesting_level": tab_props.get("nestingLevel", 0),
        }
        if "iconEmoji" in tab_props:
            formatted_tab["icon_emoji"] = tab_props["iconEmoji"]
        if "parentTabId" in tab_props:
            formatted_tab["parent_tab_id"] = tab_props["parentTabId"]
        formatted_tabs.append(formatted_tab)
    return formatted_tabs


# =============================================================================
# Handler functions
# =============================================================================


async def _create_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    title = arguments["title"]
    url = f"{DOCS_API_BASE}/documents"
    response = await svc._make_request("POST", url, json_data={"title": title})
    return {
        "status": "created",
        "document_id": response.get("documentId"),
        "title": response.get("title"),
        "revision_id": response.get("revisionId"),
    }


async def _append_to_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    text = arguments["text"]

    get_url = f"{DOCS_API_BASE}/documents/{document_id}"
    doc = await svc._make_request("GET", get_url)

    content = doc.get("body", {}).get("content", [])
    if content:
        last_element = content[-1]
        end_index = last_element.get("endIndex", 1)
        insert_index = max(1, end_index - 1)
    else:
        insert_index = 1

    update_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {
        "requests": [
            {
                "insertText": {
                    "location": {"index": insert_index},
                    "text": text,
                }
            }
        ]
    }

    await svc._make_request("POST", update_url, json_data=body)

    return {
        "status": "appended",
        "document_id": document_id,
        "text_length": len(text),
    }


async def _get_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    include_tabs = arguments.get("include_tabs_content", False)

    # Exclude large unused objects (inlineObjects, positionedObjects, headers,
    # footers, footnotes) to reduce response payload by ~60-80%.
    # Separate field masks: pandoc/DOCX-uploaded docs reject requests that
    # include `tabs` in the field mask together with includeTabsContent=true.
    _FIELDS_WITH_TABS = "documentId,title,body,namedStyles,tabs,revisionId"
    _FIELDS_NO_TABS = "documentId,title,body,namedStyles,revisionId"

    url = f"{DOCS_API_BASE}/documents/{document_id}"
    params: dict[str, Any] = {
        "fields": _FIELDS_WITH_TABS if include_tabs else _FIELDS_NO_TABS,
    }
    if include_tabs:
        params["includeTabsContent"] = "true"

    try:
        response = await svc._make_request("GET", url, params=params)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400 and include_tabs:
            # Pandoc/DOCX-uploaded documents do not support the tabs API.
            # Retry without tabs and surface a warning so callers know.
            logger.warning(
                "get_document: 400 error with tabs request for %s; "
                "retrying without tabs (pandoc/DOCX-uploaded document).",
                document_id,
            )
            params = {"fields": _FIELDS_NO_TABS}
            response = await svc._make_request("GET", url, params=params)
            warning: str | None = (
                "Document does not support tabs API; returned without tab content."
            )
        else:
            raise
    else:
        warning = None

    # For documents that use tabs, `body` is empty; content lives inside each
    # tab's `documentTab.body`.  Fall back to the top-level `body` only when
    # no tabs are present (classic / single-tab documents).
    tabs = response.get("tabs", [])
    tables: list[dict[str, Any]] = []
    if tabs:
        text_parts: list[str] = []
        for tab in tabs:
            tab_body = tab.get("documentTab", {}).get("body", {})
            tab_text = _extract_doc_text(tab_body)
            if tab_text:
                text_parts.append(tab_text)
            tables.extend(_extract_tables(tab_body))
        text_content = "\n".join(text_parts)
    else:
        body = response.get("body", {})
        text_content = _extract_doc_text(body)
        tables = _extract_tables(body)

    result: dict[str, Any] = {
        "document_id": response.get("documentId"),
        "title": response.get("title"),
        "revision_id": response.get("revisionId"),
        "text_content": text_content,
        "tables": tables,
    }

    if include_tabs and tabs:
        result["tabs"] = _format_tabs(tabs)

    if warning is not None:
        result["warning"] = warning

    return result


async def _manage_document_tabs(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Unified handler for all tab management operations."""
    action = arguments["action"]
    document_id = arguments["document_id"]

    if action == "list":
        url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
        response = await svc._make_request("GET", url)
        tabs = response.get("tabs", [])
        if not tabs:
            return {
                "document_id": document_id,
                "tabs": [],
                "count": 0,
                "message": "Document has no tabs or only a single tab",
            }
        formatted_tabs = _format_tabs(tabs)
        return {"document_id": document_id, "tabs": formatted_tabs, "count": len(formatted_tabs)}

    if action == "get_content":
        tab_id = arguments.get("tab_id")
        if not tab_id:
            return {"error": "tab_id is required for get_content action"}
        url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
        response = await svc._make_request("GET", url)
        tabs = response.get("tabs", [])
        target_tab = None
        for tab in tabs:
            if tab.get("tabProperties", {}).get("tabId") == tab_id:
                target_tab = tab
                break
        if not target_tab:
            return {
                "error": f"Tab '{tab_id}' not found in document",
                "document_id": document_id,
                "available_tabs": [
                    t.get("tabProperties", {}).get("tabId") for t in tabs if "tabProperties" in t
                ],
            }
        tab_props = target_tab.get("tabProperties", {})
        tab_body = target_tab.get("documentTab", {}).get("body", {})
        text_content = _extract_doc_text(tab_body)
        result: dict[str, Any] = {
            "document_id": document_id,
            "tab_id": tab_id,
            "title": tab_props.get("title", ""),
            "index": tab_props.get("index", 0),
            "nesting_level": tab_props.get("nestingLevel", 0),
            "text_content": text_content,
        }
        if "iconEmoji" in tab_props:
            result["icon_emoji"] = tab_props["iconEmoji"]
        if "parentTabId" in tab_props:
            result["parent_tab_id"] = tab_props["parentTabId"]
        return result

    if action == "create":
        title = arguments.get("title")
        if not title:
            return {"error": "title is required for create action"}
        icon_emoji = arguments.get("icon_emoji")
        parent_tab_id = arguments.get("parent_tab_id")
        index = arguments.get("index")
        create_tab_request: dict[str, Any] = {"createTab": {"tabProperties": {"title": title}}}
        if icon_emoji:
            create_tab_request["createTab"]["tabProperties"]["iconEmoji"] = icon_emoji
        if parent_tab_id:
            create_tab_request["createTab"]["tabProperties"]["parentTabId"] = parent_tab_id
        if index is not None:
            create_tab_request["createTab"]["tabProperties"]["index"] = index
        url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        response = await svc._make_request(
            "POST", url, json_data={"requests": [create_tab_request]}
        )
        replies = response.get("replies", [])
        if replies and "createTab" in replies[0]:
            created_tab = replies[0]["createTab"]
            return {
                "status": "created",
                "document_id": document_id,
                "tab_id": created_tab.get("tabId"),
                "title": title,
            }
        return {"status": "created", "document_id": document_id, "title": title}

    if action == "update":
        tab_id = arguments.get("tab_id")
        if not tab_id:
            return {"error": "tab_id is required for update action"}
        title = arguments.get("title")
        icon_emoji = arguments.get("icon_emoji")
        if not title and not icon_emoji:
            return {
                "error": "At least one of 'title' or 'icon_emoji' must be provided",
                "document_id": document_id,
                "tab_id": tab_id,
            }
        update_request: dict[str, Any] = {
            "updateTabProperties": {
                "tabId": tab_id,
                "tabProperties": {},
                "fields": [],
            }
        }
        if title:
            update_request["updateTabProperties"]["tabProperties"]["title"] = title
            update_request["updateTabProperties"]["fields"].append("title")
        if icon_emoji:
            update_request["updateTabProperties"]["tabProperties"]["iconEmoji"] = icon_emoji
            update_request["updateTabProperties"]["fields"].append("iconEmoji")
        update_request["updateTabProperties"]["fields"] = ",".join(
            update_request["updateTabProperties"]["fields"]
        )
        url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        await svc._make_request("POST", url, json_data={"requests": [update_request]})
        return {
            "status": "updated",
            "document_id": document_id,
            "tab_id": tab_id,
            "updated_fields": update_request["updateTabProperties"]["fields"].split(","),
        }

    if action == "move":
        tab_id = arguments.get("tab_id")
        if not tab_id:
            return {"error": "tab_id is required for move action"}
        new_parent_tab_id = arguments.get("new_parent_tab_id")
        new_index = arguments.get("new_index")
        if new_parent_tab_id is None and new_index is None:
            return {
                "error": "At least one of 'new_parent_tab_id' or 'new_index' must be provided",
                "document_id": document_id,
                "tab_id": tab_id,
            }
        move_request: dict[str, Any] = {
            "updateTabProperties": {
                "tabId": tab_id,
                "tabProperties": {},
                "fields": [],
            }
        }
        if new_parent_tab_id is not None:
            if new_parent_tab_id == "":
                move_request["updateTabProperties"]["tabProperties"]["parentTabId"] = None
            else:
                move_request["updateTabProperties"]["tabProperties"]["parentTabId"] = (
                    new_parent_tab_id
                )
            move_request["updateTabProperties"]["fields"].append("parentTabId")
        if new_index is not None:
            move_request["updateTabProperties"]["tabProperties"]["index"] = new_index
            move_request["updateTabProperties"]["fields"].append("index")
        move_request["updateTabProperties"]["fields"] = ",".join(
            move_request["updateTabProperties"]["fields"]
        )
        url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        await svc._make_request("POST", url, json_data={"requests": [move_request]})
        return {
            "status": "moved",
            "document_id": document_id,
            "tab_id": tab_id,
            "updated_fields": move_request["updateTabProperties"]["fields"].split(","),
        }

    return {
        "error": f"Unknown action '{action}'. Valid actions: list, get_content, create, update, move"
    }


def _get_paragraph_style(paragraph: dict[str, Any]) -> str:
    """Extract the named paragraph style (e.g. NORMAL_TEXT, HEADING_1)."""
    return paragraph.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")


def _get_paragraph_alignment(paragraph: dict[str, Any]) -> str:
    """Extract paragraph alignment, defaulting to START (LEFT-equivalent)."""
    return paragraph.get("paragraphStyle", {}).get("alignment", "START")


def _get_paragraph_text(paragraph: dict[str, Any]) -> str:
    """Concatenate all textRun content within a paragraph element."""
    parts: list[str] = []
    for el in paragraph.get("elements", []):
        text_run = el.get("textRun")
        if text_run:
            parts.append(text_run.get("content", ""))
    return "".join(parts)


async def _get_document_structure(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """Return paragraph-level structure for index-based editing.

    Why: Index-based edits (insert, delete, move, format) require knowing the
    document's startIndex/endIndex boundaries. Without this, callers must
    re-fetch and parse the raw doc themselves. Surfacing the structure once
    avoids that duplication.
    What: Fetches the document, walks ``body.content`` and emits a list of
    paragraphs with index, start_index, end_index, text, style, alignment,
    and is_list_item flags. Tables are surfaced via the existing helper.
    Test: Stub _make_request to return a body with two paragraphs and a table;
    assert paragraphs has two entries with correct indices and text, and
    tables list contains the table entry.
    """
    document_id = arguments["document_id"]
    url = f"{DOCS_API_BASE}/documents/{document_id}"
    response = await svc._make_request("GET", url)

    body = response.get("body", {})
    paragraphs: list[dict[str, Any]] = []
    para_index = 0
    for element in body.get("content", []) or []:
        para = element.get("paragraph")
        if para is None:
            continue
        text = _get_paragraph_text(para)
        paragraphs.append(
            {
                "index": para_index,
                "start_index": element.get("startIndex"),
                "end_index": element.get("endIndex"),
                "text": text,
                "style": _get_paragraph_style(para),
                "alignment": _get_paragraph_alignment(para),
                "is_list_item": "bullet" in para,
            }
        )
        para_index += 1

    tables = _extract_tables(body)

    return {
        "document_id": response.get("documentId"),
        "title": response.get("title"),
        "revision_id": response.get("revisionId"),
        "paragraphs": paragraphs,
        "tables": tables,
    }


async def _replace_text_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """Find-and-replace text in a Google Doc using replaceAllText.

    Why: ``replaceAllText`` is the most efficient way to update repeated
    strings without computing indices. Wrapping it as a tool removes the
    need for callers to construct the batchUpdate body themselves.
    What: Issues a single ``replaceAllText`` batchUpdate request and returns
    the count from ``replies[0].replaceAllText.occurrencesChanged``.
    Test: Stub _make_request to return ``replies=[{replaceAllText:{occurrencesChanged:3}}]``;
    assert the result reports replacements_made=3 with the supplied texts.
    """
    document_id = arguments["document_id"]
    find_text = arguments["find_text"]
    replace_text = arguments["replace_text"]
    match_case = arguments.get("match_case", True)

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {
        "requests": [
            {
                "replaceAllText": {
                    "containsText": {
                        "text": find_text,
                        "matchCase": match_case,
                    },
                    "replaceText": replace_text,
                }
            }
        ]
    }
    response = await svc._make_request("POST", url, json_data=body)

    replies = response.get("replies", []) or []
    occurrences = 0
    if replies:
        occurrences = replies[0].get("replaceAllText", {}).get("occurrencesChanged", 0) or 0

    return {
        "replacements_made": occurrences,
        "find_text": find_text,
        "replace_text": replace_text,
    }


async def _insert_text_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """Insert text at a specific document index.

    Why: Targeted inserts are essential for index-based edits where appending
    is insufficient. This is the lightweight counterpart to ``append_to_document``.
    What: Issues a single ``insertText`` batchUpdate request at the supplied
    index.
    Test: Stub _make_request and assert it was called with a request body
    containing ``{insertText: {location: {index: <i>}, text: <text>}}``.
    """
    document_id = arguments["document_id"]
    text = arguments["text"]
    index = arguments["index"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {
        "requests": [
            {
                "insertText": {
                    "location": {"index": index},
                    "text": text,
                }
            }
        ]
    }
    await svc._make_request("POST", url, json_data=body)

    return {"success": True, "text": text, "index": index}


async def _delete_range_in_document(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
    """Delete content between startIndex and endIndex.

    Why: Provides the inverse of ``insertText`` so callers can remove ranges
    discovered via ``get_document_structure``.
    What: Issues a single ``deleteContentRange`` batchUpdate. Returns the
    number of characters deleted (end_index - start_index).
    Test: Stub _make_request and assert the batch body contains
    ``deleteContentRange`` with the supplied range; assert the response
    reports chars_deleted as end-start.
    """
    document_id = arguments["document_id"]
    start_index = arguments["start_index"]
    end_index = arguments["end_index"]

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {
        "requests": [
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    }
                }
            }
        ]
    }
    await svc._make_request("POST", url, json_data=body)

    return {
        "success": True,
        "start_index": start_index,
        "end_index": end_index,
        "chars_deleted": max(0, end_index - start_index),
    }


async def _move_paragraph_in_document(  # pyright: ignore[reportUnusedFunction]
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Cut-and-paste a paragraph from one index range to another.

    Why: Reordering paragraphs is a common editing operation that requires a
    read + insert + delete sequence with careful index adjustment.
    What: 1) reads the doc and extracts paragraph text in the source range;
    2) inserts that text at destination_index; 3) deletes the original range,
    accounting for the index shift when destination > source.
    Test: Stub _make_request to return a body with a known paragraph; assert
    the resulting batchUpdate sequence contains an insertText at destination
    and a deleteContentRange shifted by len(text) when destination > source.
    """
    document_id = arguments["document_id"]
    source_start = arguments["source_start_index"]
    source_end = arguments["source_end_index"]
    destination = arguments["destination_index"]

    # 1. Read the source paragraph text.
    get_url = f"{DOCS_API_BASE}/documents/{document_id}"
    doc = await svc._make_request("GET", get_url)
    body = doc.get("body", {})

    moved_text = ""
    for element in body.get("content", []) or []:
        el_start = element.get("startIndex")
        el_end = element.get("endIndex")
        if el_start is None or el_end is None:
            continue
        # Paragraph fully contained in the requested source range.
        if el_start >= source_start and el_end <= source_end and "paragraph" in element:
            moved_text += _get_paragraph_text(element["paragraph"])

    if not moved_text:
        return {
            "success": False,
            "error": "No paragraph text found in source range",
            "source_start_index": source_start,
            "source_end_index": source_end,
        }

    text_len = source_end - source_start

    # 2. Issue insert + delete in a single batch. If destination > source_end,
    # the delete range is unaffected (insertion happens after). If destination
    # falls before the source, the source range shifts forward by text_len.
    if destination <= source_start:
        delete_start = source_start + text_len
        delete_end = source_end + text_len
    elif destination >= source_end:
        delete_start = source_start
        delete_end = source_end
    else:
        # Destination inside source range — ambiguous; reject.
        return {
            "success": False,
            "error": "destination_index must lie outside [source_start_index, source_end_index]",
        }

    update_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    requests_body: dict[str, Any] = {
        "requests": [
            {
                "insertText": {
                    "location": {"index": destination},
                    "text": moved_text,
                }
            },
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": delete_start,
                        "endIndex": delete_end,
                    }
                }
            },
        ]
    }
    await svc._make_request("POST", update_url, json_data=requests_body)

    return {"success": True, "moved_text": moved_text[:100]}


async def _format_paragraph_in_document(  # pyright: ignore[reportUnusedFunction]
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Apply paragraph-level styling via updateParagraphStyle.

    Why: ``format_document_range`` covers a broader surface but does not
    expose space_above/space_below or named heading styles in a single
    paragraph-focused call. This tool provides a focused entry point.
    What: Builds a single ``updateParagraphStyle`` request, populating only
    the supplied properties and assembling the matching ``fields`` mask.
    Test: Stub _make_request, supply alignment=CENTER and heading_style=HEADING_2;
    assert the fields mask includes ``alignment,namedStyleType`` (order-
    insensitive) and styles_applied lists both entries.
    """
    document_id = arguments["document_id"]
    start_index = arguments["start_index"]
    end_index = arguments["end_index"]

    paragraph_style: dict[str, Any] = {}
    fields: list[str] = []
    applied: list[str] = []

    heading_style = arguments.get("heading_style")
    if heading_style:
        paragraph_style["namedStyleType"] = heading_style
        fields.append("namedStyleType")
        applied.append("heading_style")

    alignment = arguments.get("alignment")
    if alignment:
        paragraph_style["alignment"] = alignment
        fields.append("alignment")
        applied.append("alignment")

    indent_first = arguments.get("indent_first_line_pt")
    if indent_first is not None:
        paragraph_style["indentFirstLine"] = {"magnitude": indent_first, "unit": "PT"}
        fields.append("indentFirstLine")
        applied.append("indent_first_line_pt")

    indent_start = arguments.get("indent_start_pt")
    if indent_start is not None:
        paragraph_style["indentStart"] = {"magnitude": indent_start, "unit": "PT"}
        fields.append("indentStart")
        applied.append("indent_start_pt")

    space_above = arguments.get("space_above_pt")
    if space_above is not None:
        paragraph_style["spaceAbove"] = {"magnitude": space_above, "unit": "PT"}
        fields.append("spaceAbove")
        applied.append("space_above_pt")

    space_below = arguments.get("space_below_pt")
    if space_below is not None:
        paragraph_style["spaceBelow"] = {"magnitude": space_below, "unit": "PT"}
        fields.append("spaceBelow")
        applied.append("space_below_pt")

    if not paragraph_style:
        return {
            "success": False,
            "error": (
                "At least one of heading_style, alignment, indent_first_line_pt, "
                "indent_start_pt, space_above_pt, space_below_pt must be provided"
            ),
        }

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {
        "requests": [
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": start_index, "endIndex": end_index},
                    "paragraphStyle": paragraph_style,
                    "fields": ",".join(fields),
                }
            }
        ]
    }
    await svc._make_request("POST", url, json_data=body)

    return {
        "success": True,
        "start_index": start_index,
        "end_index": end_index,
        "styles_applied": applied,
    }


async def _create_document_tab(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    title = arguments["title"]
    icon_emoji = arguments.get("icon_emoji")
    parent_tab_id = arguments.get("parent_tab_id")
    index = arguments.get("index")

    create_tab_request: dict[str, Any] = {
        "createTab": {
            "tabProperties": {
                "title": title,
            }
        }
    }

    if icon_emoji:
        create_tab_request["createTab"]["tabProperties"]["iconEmoji"] = icon_emoji
    if parent_tab_id:
        create_tab_request["createTab"]["tabProperties"]["parentTabId"] = parent_tab_id
    if index is not None:
        create_tab_request["createTab"]["tabProperties"]["index"] = index

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {"requests": [create_tab_request]}
    response = await svc._make_request("POST", url, json_data=body)

    replies = response.get("replies", [])
    if replies and "createTab" in replies[0]:
        created_tab = replies[0]["createTab"]
        return {
            "status": "created",
            "document_id": document_id,
            "tab_id": created_tab.get("tabId"),
            "title": title,
        }

    return {"status": "created", "document_id": document_id, "title": title}


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs core and tab handlers."""
    return {
        "create_document": lambda args: _create_document(svc, args),
        "append_to_document": lambda args: _append_to_document(svc, args),
        "get_document": lambda args: _get_document(svc, args),
        "manage_document_tabs": lambda args: _manage_document_tabs(svc, args),
        "create_document_tab": lambda args: _create_document_tab(svc, args),
        "get_document_structure": lambda args: _get_document_structure(svc, args),
        "replace_text_in_document": lambda args: _replace_text_in_document(svc, args),
        "insert_text_in_document": lambda args: _insert_text_in_document(svc, args),
        "delete_range_in_document": lambda args: _delete_range_in_document(svc, args),
        "move_paragraph_in_document": lambda args: _move_paragraph_in_document(svc, args),
        "format_paragraph_in_document": lambda args: _format_paragraph_in_document(svc, args),
    }
