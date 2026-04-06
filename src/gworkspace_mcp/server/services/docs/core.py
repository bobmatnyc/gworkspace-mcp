"""Google Docs core sub-module: create, read, append, and tab management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
    Tool(
        name="create_document",
        description="Create a new Google Doc",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Document title",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="append_to_document",
        description="Append text to an existing Google Doc",
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
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="list_document_tabs",
        description="List all tabs in a Google Doc with their metadata (tabId, title, index, nestingLevel, iconEmoji, parentTabId).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="get_tab_content",
        description="Get the content from a specific tab in a Google Doc.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID (from list_document_tabs)",
                },
            },
            "required": ["document_id", "tab_id"],
        },
    ),
    Tool(
        name="create_document_tab",
        description="Create a new tab in a Google Doc.",
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
            },
            "required": ["document_id", "title"],
        },
    ),
    Tool(
        name="update_tab_properties",
        description="Update properties of an existing tab (title, iconEmoji).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID to update (from list_document_tabs)",
                },
                "title": {
                    "type": "string",
                    "description": "New tab title (optional)",
                },
                "icon_emoji": {
                    "type": "string",
                    "description": "New icon emoji (optional)",
                },
            },
            "required": ["document_id", "tab_id"],
        },
    ),
    Tool(
        name="move_tab",
        description="Move a tab to a new position or change its parent (nesting level).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "Google Doc ID",
                },
                "tab_id": {
                    "type": "string",
                    "description": "Tab ID to move (from list_document_tabs)",
                },
                "new_parent_tab_id": {
                    "type": "string",
                    "description": "New parent tab ID (optional). Use empty string to move to root level.",
                },
                "new_index": {
                    "type": "integer",
                    "description": "New position index (optional)",
                },
            },
            "required": ["document_id", "tab_id"],
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
    include_tabs_content = arguments.get("include_tabs_content", False)

    # Always request tab content so modern tabbed documents return non-empty body.
    url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"

    response = await svc._make_request("GET", url)

    # For documents that use tabs, `body` is empty; content lives inside each
    # tab's `documentTab.body`.  Fall back to the top-level `body` only when
    # no tabs are present (classic / single-tab documents).
    tabs = response.get("tabs", [])
    if tabs:
        text_parts: list[str] = []
        for tab in tabs:
            tab_body = tab.get("documentTab", {}).get("body", {})
            tab_text = _extract_doc_text(tab_body)
            if tab_text:
                text_parts.append(tab_text)
        text_content = "\n".join(text_parts)
    else:
        text_content = _extract_doc_text(response.get("body", {}))

    result: dict[str, Any] = {
        "document_id": response.get("documentId"),
        "title": response.get("title"),
        "revision_id": response.get("revisionId"),
        "text_content": text_content,
    }

    if include_tabs_content and tabs:
        result["tabs"] = _format_tabs(tabs)

    return result


async def _list_document_tabs(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]

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


async def _get_tab_content(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    tab_id = arguments["tab_id"]

    url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
    response = await svc._make_request("GET", url)

    tabs = response.get("tabs", [])
    target_tab = None
    for tab in tabs:
        tab_props = tab.get("tabProperties", {})
        if tab_props.get("tabId") == tab_id:
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


async def _update_tab_properties(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    tab_id = arguments["tab_id"]
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
    body = {"requests": [update_request]}
    await svc._make_request("POST", url, json_data=body)

    return {
        "status": "updated",
        "document_id": document_id,
        "tab_id": tab_id,
        "updated_fields": update_request["updateTabProperties"]["fields"].split(","),
    }


async def _move_tab(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    tab_id = arguments["tab_id"]
    new_parent_tab_id = arguments.get("new_parent_tab_id")
    new_index = arguments.get("new_index")

    if new_parent_tab_id is None and new_index is None:
        return {
            "error": "At least one of 'new_parent_tab_id' or 'new_index' must be provided",
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

    if new_parent_tab_id is not None:
        if new_parent_tab_id == "":
            update_request["updateTabProperties"]["tabProperties"]["parentTabId"] = None
        else:
            update_request["updateTabProperties"]["tabProperties"]["parentTabId"] = (
                new_parent_tab_id
            )
        update_request["updateTabProperties"]["fields"].append("parentTabId")

    if new_index is not None:
        update_request["updateTabProperties"]["tabProperties"]["index"] = new_index
        update_request["updateTabProperties"]["fields"].append("index")

    update_request["updateTabProperties"]["fields"] = ",".join(
        update_request["updateTabProperties"]["fields"]
    )

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    body = {"requests": [update_request]}
    await svc._make_request("POST", url, json_data=body)

    return {
        "status": "moved",
        "document_id": document_id,
        "tab_id": tab_id,
        "updated_fields": update_request["updateTabProperties"]["fields"].split(","),
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs core and tab handlers."""
    return {
        "create_document": lambda args: _create_document(svc, args),
        "append_to_document": lambda args: _append_to_document(svc, args),
        "get_document": lambda args: _get_document(svc, args),
        "list_document_tabs": lambda args: _list_document_tabs(svc, args),
        "get_tab_content": lambda args: _get_tab_content(svc, args),
        "create_document_tab": lambda args: _create_document_tab(svc, args),
        "update_tab_properties": lambda args: _update_tab_properties(svc, args),
        "move_tab": lambda args: _move_tab(svc, args),
    }
