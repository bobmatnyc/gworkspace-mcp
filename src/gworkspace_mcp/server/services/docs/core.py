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
    }
