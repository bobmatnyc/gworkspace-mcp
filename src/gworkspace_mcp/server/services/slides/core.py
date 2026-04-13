"""Google Slides core sub-module: read, create, manage slides."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DRIVE_API_BASE, SLIDES_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

EMU_PER_PT = 12700  # English Metric Units per point

TOOLS: list[Tool] = [
    Tool(
        name="get_slides",
        description=(
            "Read Google Slides data. "
            "action='list': search presentations in Drive (optional query, max_results). "
            "action='get_presentation': get metadata for a presentation (presentation_id required). "
            "action='get_slide': get content of a specific slide (presentation_id, slide_index required). "
            "action='get_text': extract all text from a presentation (presentation_id required)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Operation to perform: 'list', 'get_presentation', 'get_slide', 'get_text'",
                    "enum": ["list", "get_presentation", "get_slide", "get_text"],
                },
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID (required for get_presentation, get_slide, get_text)",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "Zero-based index of the slide to retrieve (required for get_slide)",
                },
                "query": {
                    "type": "string",
                    "description": "Search query to filter presentations (list only). Leave empty to list all.",
                    "default": "",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of presentations to return (list only, default: 10)",
                    "default": 10,
                },
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="manage_slides",
        description=(
            "Create or modify a Google Slides presentation or its slides. "
            "action='create': create a new presentation (title required). "
            "action='add_slide': add a new slide (presentation_id required; optional layout, insertion_index). "
            "action='delete_slide': delete a slide (presentation_id, slide_id required). "
            "action='update_text': update text in a shape (presentation_id, slide_id, shape_id, text required)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Operation to perform: 'create', 'add_slide', 'delete_slide', 'update_text'",
                    "enum": ["create", "add_slide", "delete_slide", "update_text"],
                },
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID (required except for create)",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the new presentation (required for create)",
                },
                "layout": {
                    "type": "string",
                    "description": "Predefined layout type for add_slide (default: 'BLANK')",
                    "default": "BLANK",
                    "enum": [
                        "BLANK",
                        "TITLE",
                        "TITLE_AND_BODY",
                        "TITLE_AND_TWO_COLUMNS",
                        "TITLE_ONLY",
                        "ONE_COLUMN_TEXT",
                        "MAIN_POINT",
                        "SECTION_HEADER",
                        "CAPTION_ONLY",
                        "BIG_NUMBER",
                    ],
                },
                "insertion_index": {
                    "type": "integer",
                    "description": "Zero-based index where to insert the slide (add_slide only). Adds at end if omitted.",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Object ID of the slide (required for delete_slide and update_text)",
                },
                "shape_id": {
                    "type": "string",
                    "description": "Object ID of the shape/placeholder containing text (required for update_text)",
                },
                "text": {
                    "type": "string",
                    "description": "New text content to set in the shape (required for update_text)",
                },
            },
            "required": ["action"],
        },
    ),
]


# =============================================================================
# Helper functions
# =============================================================================


def _extract_text_from_elements(text_elements: list[dict[str, Any]]) -> str:
    """Extract plain text from Slides text elements."""
    text_parts = []
    for element in text_elements:
        if "textRun" in element:
            text_parts.append(element["textRun"].get("content", ""))
    return "".join(text_parts)


# =============================================================================
# Handler functions
# =============================================================================


async def _list_presentations(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """List/search Google Slides presentations in Drive."""
    query = arguments.get("query", "")
    max_results = arguments.get("max_results", 10)

    drive_query = "mimeType='application/vnd.google-apps.presentation'"
    if query:
        drive_query += f" and name contains '{query}'"

    url = f"{DRIVE_API_BASE}/files"
    params = {
        "q": drive_query,
        "pageSize": max_results,
        "fields": "files(id,name,mimeType,modifiedTime,owners,webViewLink)",
        "orderBy": "modifiedTime desc",
        "includeItemsFromAllDrives": "true",
        "supportsAllDrives": "true",
    }
    response = await svc._make_request("GET", url, params=params)

    presentations = []
    for item in response.get("files", []):
        presentations.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "modified_time": item.get("modifiedTime"),
                "owners": [o.get("emailAddress") for o in item.get("owners", [])],
                "web_link": item.get("webViewLink"),
            }
        )

    return {"presentations": presentations, "count": len(presentations)}


async def _get_presentation(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get presentation metadata and structure."""
    presentation_id = arguments["presentation_id"]
    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}"
    response = await svc._make_request("GET", url)

    slides = []
    for slide in response.get("slides", []):
        slides.append(
            {
                "object_id": slide.get("objectId"),
                "layout": slide.get("slideProperties", {}).get("layoutObjectId"),
            }
        )

    masters = [{"object_id": master.get("objectId")} for master in response.get("masters", [])]

    layouts = []
    for layout in response.get("layouts", []):
        layout_props = layout.get("layoutProperties", {})
        layouts.append(
            {
                "object_id": layout.get("objectId"),
                "name": layout_props.get("name"),
                "display_name": layout_props.get("displayName"),
            }
        )

    return {
        "presentation_id": response.get("presentationId"),
        "title": response.get("title"),
        "page_size": response.get("pageSize"),
        "slide_count": len(slides),
        "slides": slides,
        "masters": masters,
        "layouts": layouts,
        "locale": response.get("locale"),
    }


async def _get_slide(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Get content of a specific slide."""
    presentation_id = arguments["presentation_id"]
    slide_index = arguments["slide_index"]

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}"
    response = await svc._make_request("GET", url)

    slides = response.get("slides", [])
    if slide_index < 0 or slide_index >= len(slides):
        raise ValueError(
            f"Slide index {slide_index} out of range. "
            f"Presentation has {len(slides)} slides (0 to {len(slides) - 1})."
        )

    slide = slides[slide_index]
    slide_id = slide.get("objectId")

    elements = []
    for element in slide.get("pageElements", []):
        element_info: dict[str, Any] = {
            "object_id": element.get("objectId"),
            "size": element.get("size"),
            "transform": element.get("transform"),
        }

        if "shape" in element:
            shape = element["shape"]
            element_info["type"] = "shape"
            element_info["shape_type"] = shape.get("shapeType")
            if "text" in shape:
                text_elements = shape["text"].get("textElements", [])
                element_info["text"] = _extract_text_from_elements(text_elements)
            if "placeholder" in shape:
                element_info["placeholder_type"] = shape["placeholder"].get("type")
        elif "image" in element:
            image = element["image"]
            element_info["type"] = "image"
            element_info["source_url"] = image.get("sourceUrl")
            element_info["content_url"] = image.get("contentUrl")
        elif "table" in element:
            element_info["type"] = "table"
            element_info["rows"] = element["table"].get("rows")
            element_info["columns"] = element["table"].get("columns")
        elif "line" in element:
            element_info["type"] = "line"
        elif "video" in element:
            element_info["type"] = "video"
            element_info["video_url"] = element["video"].get("url")
        elif "wordArt" in element:
            element_info["type"] = "word_art"
        elif "sheetsChart" in element:
            element_info["type"] = "sheets_chart"
        else:
            element_info["type"] = "unknown"

        elements.append(element_info)

    return {
        "presentation_id": presentation_id,
        "slide_index": slide_index,
        "slide_id": slide_id,
        "element_count": len(elements),
        "elements": elements,
    }


async def _get_presentation_text(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Extract all text from a presentation."""
    presentation_id = arguments["presentation_id"]
    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}"
    response = await svc._make_request("GET", url)

    slides_text = []
    for i, slide in enumerate(response.get("slides", [])):
        slide_texts = []
        for element in slide.get("pageElements", []):
            if "shape" in element and "text" in element["shape"]:
                text_elements = element["shape"]["text"].get("textElements", [])
                text = _extract_text_from_elements(text_elements)
                if text.strip():
                    slide_texts.append(text.strip())
        slides_text.append(
            {
                "slide_index": i,
                "slide_id": slide.get("objectId"),
                "text_content": slide_texts,
            }
        )

    all_text = []
    for slide in slides_text:
        if slide["text_content"]:
            all_text.append(f"--- Slide {slide['slide_index'] + 1} ---")
            all_text.extend(slide["text_content"])

    return {
        "presentation_id": presentation_id,
        "title": response.get("title"),
        "slide_count": len(slides_text),
        "slides": slides_text,
        "combined_text": "\n".join(all_text),
    }


async def _create_presentation(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Create a new Google Slides presentation."""
    title = arguments["title"]
    url = f"{SLIDES_API_BASE}/presentations"
    response = await svc._make_request("POST", url, json_data={"title": title})
    return {
        "status": "created",
        "presentation_id": response.get("presentationId"),
        "title": response.get("title"),
        "url": f"https://docs.google.com/presentation/d/{response.get('presentationId')}/edit",
    }


async def _add_slide(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add a new slide to a presentation."""
    presentation_id = arguments["presentation_id"]
    layout = arguments.get("layout", "BLANK")
    insertion_index = arguments.get("insertion_index")

    new_slide_id = f"slide_{uuid.uuid4().hex[:8]}"
    create_slide_request: dict[str, Any] = {
        "createSlide": {
            "objectId": new_slide_id,
            "slideLayoutReference": {"predefinedLayout": layout},
        }
    }
    if insertion_index is not None:
        create_slide_request["createSlide"]["insertionIndex"] = insertion_index

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"
    response = await svc._make_request("POST", url, json_data={"requests": [create_slide_request]})

    replies = response.get("replies", [])
    created_slide_id = new_slide_id
    if replies and "createSlide" in replies[0]:
        created_slide_id = replies[0]["createSlide"].get("objectId", new_slide_id)

    return {
        "status": "created",
        "presentation_id": presentation_id,
        "slide_id": created_slide_id,
        "layout": layout,
        "insertion_index": insertion_index,
    }


async def _delete_slide(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Delete a slide from a presentation."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"
    request_body = {"requests": [{"deleteObject": {"objectId": slide_id}}]}
    await svc._make_request("POST", url, json_data=request_body)

    return {"status": "deleted", "presentation_id": presentation_id, "slide_id": slide_id}


async def _update_slide_text(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Update text in a shape on a slide."""
    presentation_id = arguments["presentation_id"]
    shape_id = arguments["shape_id"]
    text = arguments["text"]

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"
    request_body = {
        "requests": [
            {"deleteText": {"objectId": shape_id, "textRange": {"type": "ALL"}}},
            {"insertText": {"objectId": shape_id, "text": text, "insertionIndex": 0}},
        ]
    }
    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "updated",
        "presentation_id": presentation_id,
        "shape_id": shape_id,
        "text_length": len(text),
    }


async def _get_slides(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch get_slides action to appropriate handler."""
    action = arguments.get("action")
    if action == "list":
        return await _list_presentations(svc, arguments)
    elif action == "get_presentation":
        if "presentation_id" not in arguments:
            raise ValueError("presentation_id is required for action='get_presentation'")
        return await _get_presentation(svc, arguments)
    elif action == "get_slide":
        if "presentation_id" not in arguments:
            raise ValueError("presentation_id is required for action='get_slide'")
        if "slide_index" not in arguments:
            raise ValueError("slide_index is required for action='get_slide'")
        return await _get_slide(svc, arguments)
    elif action == "get_text":
        if "presentation_id" not in arguments:
            raise ValueError("presentation_id is required for action='get_text'")
        return await _get_presentation_text(svc, arguments)
    else:
        raise ValueError(
            f"Unknown action: {action!r}. Use 'list', 'get_presentation', 'get_slide', or 'get_text'."
        )


async def _manage_slides(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch manage_slides action to appropriate handler."""
    action = arguments.get("action")
    if action == "create":
        if "title" not in arguments:
            raise ValueError("title is required for action='create'")
        return await _create_presentation(svc, arguments)
    elif action == "add_slide":
        if "presentation_id" not in arguments:
            raise ValueError("presentation_id is required for action='add_slide'")
        return await _add_slide(svc, arguments)
    elif action == "delete_slide":
        if "presentation_id" not in arguments:
            raise ValueError("presentation_id is required for action='delete_slide'")
        if "slide_id" not in arguments:
            raise ValueError("slide_id is required for action='delete_slide'")
        return await _delete_slide(svc, arguments)
    elif action == "update_text":
        if "presentation_id" not in arguments:
            raise ValueError("presentation_id is required for action='update_text'")
        if "slide_id" not in arguments:
            raise ValueError("slide_id is required for action='update_text'")
        if "shape_id" not in arguments:
            raise ValueError("shape_id is required for action='update_text'")
        if "text" not in arguments:
            raise ValueError("text is required for action='update_text'")
        return await _update_slide_text(svc, arguments)
    else:
        raise ValueError(
            f"Unknown action: {action!r}. Use 'create', 'add_slide', 'delete_slide', or 'update_text'."
        )


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Slides core handlers."""
    return {
        "get_slides": lambda args: _get_slides(svc, args),
        "manage_slides": lambda args: _manage_slides(svc, args),
    }
