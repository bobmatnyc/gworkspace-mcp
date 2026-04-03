"""Google Slides service module for MCP server."""

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
        name="list_presentations",
        description="Search for Google Slides presentations in Drive. Returns presentation metadata including ID, name, and modification time.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to filter presentations (e.g., 'quarterly report'). Leave empty to list all presentations.",
                    "default": "",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of presentations to return (default: 10)",
                    "default": 10,
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_presentation",
        description="Get presentation metadata including title, slide count, master slides, and layouts.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID (from the URL)",
                },
            },
            "required": ["presentation_id"],
        },
    ),
    Tool(
        name="get_slide",
        description="Get the content of a specific slide including shapes, text, and images.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "Zero-based index of the slide to retrieve",
                },
            },
            "required": ["presentation_id", "slide_index"],
        },
    ),
    Tool(
        name="get_presentation_text",
        description="Extract all text content from a presentation, organized by slide.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
            },
            "required": ["presentation_id"],
        },
    ),
    # Google Slides API - Writing Operations
    Tool(
        name="create_presentation",
        description="Create a new Google Slides presentation with the specified title.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title for the new presentation",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="add_slide",
        description="Add a new slide to a presentation. Can specify layout and insertion index.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "layout": {
                    "type": "string",
                    "description": "Predefined layout type: 'BLANK', 'TITLE', 'TITLE_AND_BODY', 'TITLE_AND_TWO_COLUMNS', 'TITLE_ONLY', 'ONE_COLUMN_TEXT', 'MAIN_POINT', 'SECTION_HEADER', 'CAPTION_ONLY', 'BIG_NUMBER'",
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
                    "description": "Zero-based index where to insert the slide. If not specified, adds at the end.",
                },
            },
            "required": ["presentation_id"],
        },
    ),
    Tool(
        name="delete_slide",
        description="Delete a slide from a presentation by its object ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Object ID of the slide to delete (from get_presentation or get_slide)",
                },
            },
            "required": ["presentation_id", "slide_id"],
        },
    ),
    Tool(
        name="update_slide_text",
        description="Update the text content in a shape or placeholder on a slide.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "shape_id": {
                    "type": "string",
                    "description": "Object ID of the shape/placeholder containing text",
                },
                "text": {
                    "type": "string",
                    "description": "New text content to set in the shape",
                },
            },
            "required": ["presentation_id", "shape_id", "text"],
        },
    ),
    Tool(
        name="add_text_box",
        description="Add a text box to a slide at the specified position.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Object ID of the slide to add the text box to",
                },
                "text": {
                    "type": "string",
                    "description": "Text content for the text box",
                },
                "x_pt": {
                    "type": "number",
                    "description": "X position in points from left edge (default: 100)",
                    "default": 100,
                },
                "y_pt": {
                    "type": "number",
                    "description": "Y position in points from top edge (default: 100)",
                    "default": 100,
                },
                "width_pt": {
                    "type": "number",
                    "description": "Width of text box in points (default: 300)",
                    "default": 300,
                },
                "height_pt": {
                    "type": "number",
                    "description": "Height of text box in points (default: 50)",
                    "default": 50,
                },
            },
            "required": ["presentation_id", "slide_id", "text"],
        },
    ),
    Tool(
        name="add_image",
        description="Add an image to a slide from a URL.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Object ID of the slide to add the image to",
                },
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to insert (must be publicly accessible)",
                },
                "x_pt": {
                    "type": "number",
                    "description": "X position in points from left edge (default: 100)",
                    "default": 100,
                },
                "y_pt": {
                    "type": "number",
                    "description": "Y position in points from top edge (default: 100)",
                    "default": 100,
                },
                "width_pt": {
                    "type": "number",
                    "description": "Width of image in points (default: 300)",
                    "default": 300,
                },
                "height_pt": {
                    "type": "number",
                    "description": "Height of image in points (default: 200)",
                    "default": 200,
                },
            },
            "required": ["presentation_id", "slide_id", "image_url"],
        },
    ),
    # Google Slides Formatting Tools
    Tool(
        name="format_text_in_slide",
        description="Apply text formatting to specific text ranges in a Google Slides presentation.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Slide object ID",
                },
                "shape_id": {
                    "type": "string",
                    "description": "Text box or shape object ID containing the text",
                },
                "start_index": {
                    "type": "integer",
                    "description": "Start character index for formatting",
                },
                "end_index": {
                    "type": "integer",
                    "description": "End character index for formatting",
                },
                "bold": {
                    "type": "boolean",
                    "description": "Apply bold formatting",
                },
                "italic": {
                    "type": "boolean",
                    "description": "Apply italic formatting",
                },
                "font_size": {
                    "type": "number",
                    "description": "Font size in points",
                },
                "font_color": {
                    "type": "object",
                    "description": "Font color in RGB format",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "required": [
                "presentation_id",
                "slide_id",
                "shape_id",
                "start_index",
                "end_index",
            ],
        },
    ),
    Tool(
        name="add_formatted_text_box",
        description="Add a text box with custom formatting to a Google Slides presentation.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Slide object ID where to add the text box",
                },
                "text": {
                    "type": "string",
                    "description": "Text content for the text box",
                },
                "x_pt": {
                    "type": "number",
                    "description": "X position in points (default: 100)",
                    "default": 100,
                },
                "y_pt": {
                    "type": "number",
                    "description": "Y position in points (default: 100)",
                    "default": 100,
                },
                "width_pt": {
                    "type": "number",
                    "description": "Width in points (default: 300)",
                    "default": 300,
                },
                "height_pt": {
                    "type": "number",
                    "description": "Height in points (default: 100)",
                    "default": 100,
                },
                "font_size": {
                    "type": "number",
                    "description": "Font size in points (default: 14)",
                    "default": 14,
                },
                "bold": {
                    "type": "boolean",
                    "description": "Apply bold formatting",
                    "default": False,
                },
                "italic": {
                    "type": "boolean",
                    "description": "Apply italic formatting",
                    "default": False,
                },
                "font_color": {
                    "type": "object",
                    "description": "Font color in RGB format",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
            "required": ["presentation_id", "slide_id", "text"],
        },
    ),
    Tool(
        name="set_slide_background",
        description="Set the background color or image for a slide in a Google Slides presentation.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Slide object ID",
                },
                "background_type": {
                    "type": "string",
                    "description": "Type of background to set",
                    "enum": ["COLOR", "IMAGE"],
                },
                "color": {
                    "type": "object",
                    "description": "Background color in RGB format (required if background_type is COLOR)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "image_url": {
                    "type": "string",
                    "description": "URL of background image (required if background_type is IMAGE)",
                },
            },
            "required": ["presentation_id", "slide_id", "background_type"],
        },
    ),
    Tool(
        name="create_bulleted_list_slide",
        description="Create a slide with a bulleted list and optional title in a Google Slides presentation.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "Position to insert the new slide (0-based)",
                },
                "title": {
                    "type": "string",
                    "description": "Title for the slide (optional)",
                },
                "bullet_points": {
                    "type": "array",
                    "description": "Array of bullet point text items",
                    "items": {"type": "string"},
                },
                "title_font_size": {
                    "type": "number",
                    "description": "Title font size in points (default: 24)",
                    "default": 24,
                },
                "bullet_font_size": {
                    "type": "number",
                    "description": "Bullet point font size in points (default: 16)",
                    "default": 16,
                },
            },
            "required": ["presentation_id", "slide_index", "bullet_points"],
        },
    ),
    Tool(
        name="apply_slide_layout",
        description="Apply a predefined layout to a slide in a Google Slides presentation.",
        inputSchema={
            "type": "object",
            "properties": {
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Slide object ID",
                },
                "layout_type": {
                    "type": "string",
                    "description": "Type of layout to apply",
                    "enum": [
                        "BLANK",
                        "CAPTION_ONLY",
                        "TITLE",
                        "TITLE_AND_BODY",
                        "TITLE_AND_TWO_COLUMNS",
                        "TITLE_ONLY",
                        "SECTION_HEADER",
                        "SECTION_TITLE_AND_DESCRIPTION",
                        "ONE_COLUMN_TEXT",
                        "MAIN_POINT",
                        "BIG_NUMBER",
                    ],
                },
            },
            "required": ["presentation_id", "slide_id", "layout_type"],
        },
    ),
]


# ---- Helper functions ----


def _extract_text_from_elements(text_elements: list[dict[str, Any]]) -> str:
    """Extract plain text from Slides text elements."""
    text_parts = []
    for element in text_elements:
        if "textRun" in element:
            text_parts.append(element["textRun"].get("content", ""))
    return "".join(text_parts)


# ---- Handler functions ----


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


async def _add_text_box(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add a text box to a slide."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]
    text = arguments["text"]
    x_pt = arguments.get("x_pt", 100)
    y_pt = arguments.get("y_pt", 100)
    width_pt = arguments.get("width_pt", 300)
    height_pt = arguments.get("height_pt", 50)

    text_box_id = f"textbox_{uuid.uuid4().hex[:8]}"
    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"

    request_body = {
        "requests": [
            {
                "createShape": {
                    "objectId": text_box_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": width_pt * EMU_PER_PT, "unit": "EMU"},
                            "height": {"magnitude": height_pt * EMU_PER_PT, "unit": "EMU"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": x_pt * EMU_PER_PT,
                            "translateY": y_pt * EMU_PER_PT,
                            "unit": "EMU",
                        },
                    },
                }
            },
            {"insertText": {"objectId": text_box_id, "text": text, "insertionIndex": 0}},
        ]
    }
    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "created",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "text_box_id": text_box_id,
        "text_length": len(text),
        "position": {"x_pt": x_pt, "y_pt": y_pt},
        "size": {"width_pt": width_pt, "height_pt": height_pt},
    }


async def _add_image(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add an image to a slide from a URL."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]
    image_url = arguments["image_url"]
    x_pt = arguments.get("x_pt", 100)
    y_pt = arguments.get("y_pt", 100)
    width_pt = arguments.get("width_pt", 300)
    height_pt = arguments.get("height_pt", 200)

    image_id = f"image_{uuid.uuid4().hex[:8]}"
    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"

    request_body = {
        "requests": [
            {
                "createImage": {
                    "objectId": image_id,
                    "url": image_url,
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": width_pt * EMU_PER_PT, "unit": "EMU"},
                            "height": {"magnitude": height_pt * EMU_PER_PT, "unit": "EMU"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": x_pt * EMU_PER_PT,
                            "translateY": y_pt * EMU_PER_PT,
                            "unit": "EMU",
                        },
                    },
                }
            }
        ]
    }
    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "created",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "image_id": image_id,
        "image_url": image_url,
        "position": {"x_pt": x_pt, "y_pt": y_pt},
        "size": {"width_pt": width_pt, "height_pt": height_pt},
    }


async def _format_text_in_slide(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Apply text formatting to text in a Google Slides presentation."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]
    shape_id = arguments["shape_id"]
    start_index = arguments["start_index"]
    end_index = arguments["end_index"]

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"
    requests = []

    if "bold" in arguments:
        requests.append(
            {
                "updateTextStyle": {
                    "objectId": shape_id,
                    "textRange": {"startIndex": start_index, "endIndex": end_index},
                    "style": {"bold": arguments["bold"]},
                    "fields": "bold",
                }
            }
        )
    if "italic" in arguments:
        requests.append(
            {
                "updateTextStyle": {
                    "objectId": shape_id,
                    "textRange": {"startIndex": start_index, "endIndex": end_index},
                    "style": {"italic": arguments["italic"]},
                    "fields": "italic",
                }
            }
        )
    if "font_size" in arguments:
        requests.append(
            {
                "updateTextStyle": {
                    "objectId": shape_id,
                    "textRange": {"startIndex": start_index, "endIndex": end_index},
                    "style": {"fontSize": {"magnitude": arguments["font_size"], "unit": "PT"}},
                    "fields": "fontSize",
                }
            }
        )
    if "font_color" in arguments:
        color = arguments["font_color"]
        requests.append(
            {
                "updateTextStyle": {
                    "objectId": shape_id,
                    "textRange": {"startIndex": start_index, "endIndex": end_index},
                    "style": {"foregroundColor": {"opaqueColor": {"rgbColor": color}}},
                    "fields": "foregroundColor",
                }
            }
        )

    if requests:
        await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "formatted",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "shape_id": shape_id,
        "range": {"start_index": start_index, "end_index": end_index},
        "formatting_applied": len(requests),
    }


async def _add_formatted_text_box(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Add a formatted text box to a Google Slides presentation."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]
    text = arguments["text"]
    x_pt = arguments.get("x_pt", 100)
    y_pt = arguments.get("y_pt", 100)
    width_pt = arguments.get("width_pt", 300)
    height_pt = arguments.get("height_pt", 100)
    font_size = arguments.get("font_size", 14)
    bold = arguments.get("bold", False)
    italic = arguments.get("italic", False)
    font_color = arguments.get("font_color")

    text_box_id = f"textbox_{uuid.uuid4().hex[:8]}"
    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"

    requests: list[dict[str, Any]] = [
        {
            "createShape": {
                "objectId": text_box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width_pt * EMU_PER_PT, "unit": "EMU"},
                        "height": {"magnitude": height_pt * EMU_PER_PT, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": x_pt * EMU_PER_PT,
                        "translateY": y_pt * EMU_PER_PT,
                        "unit": "EMU",
                    },
                },
            }
        },
        {"insertText": {"objectId": text_box_id, "text": text, "insertionIndex": 0}},
    ]

    text_style: dict[str, Any] = {}
    if bold:
        text_style["bold"] = True
    if italic:
        text_style["italic"] = True
    if font_size:
        text_style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
    if font_color:
        text_style["foregroundColor"] = {"opaqueColor": {"rgbColor": font_color}}

    if text_style:
        requests.append(
            {
                "updateTextStyle": {
                    "objectId": text_box_id,
                    "textRange": {"startIndex": 0, "endIndex": len(text)},
                    "style": text_style,
                    "fields": ",".join(text_style.keys()),
                }
            }
        )

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "created",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "text_box_id": text_box_id,
        "text": text,
        "position": {"x_pt": x_pt, "y_pt": y_pt},
        "size": {"width_pt": width_pt, "height_pt": height_pt},
        "formatting": {
            "font_size": font_size,
            "bold": bold,
            "italic": italic,
            "font_color": font_color,
        },
    }


async def _set_slide_background(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Set slide background color or image."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]
    background_type = arguments["background_type"]
    color = arguments.get("color")
    image_url = arguments.get("image_url")

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"

    if background_type == "COLOR":
        if not color:
            raise ValueError("color is required for COLOR background type")
        request_body: dict[str, Any] = {
            "requests": [
                {
                    "updateSlideProperties": {
                        "objectId": slide_id,
                        "slideProperties": {
                            "pageBackgroundFill": {"solidFill": {"color": {"rgbColor": color}}}
                        },
                        "fields": "pageBackgroundFill",
                    }
                }
            ]
        }
    else:  # IMAGE
        if not image_url:
            raise ValueError("image_url is required for IMAGE background type")
        request_body = {
            "requests": [
                {
                    "updateSlideProperties": {
                        "objectId": slide_id,
                        "slideProperties": {
                            "pageBackgroundFill": {
                                "stretchedPictureFill": {"contentUrl": image_url}
                            }
                        },
                        "fields": "pageBackgroundFill",
                    }
                }
            ]
        }

    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "updated",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "background_type": background_type,
        "color": color if background_type == "COLOR" else None,
        "image_url": image_url if background_type == "IMAGE" else None,
    }


async def _create_bulleted_list_slide(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Create a slide with bulleted list."""
    presentation_id = arguments["presentation_id"]
    slide_index = arguments["slide_index"]
    title = arguments.get("title")
    bullet_points = arguments["bullet_points"]
    title_font_size = arguments.get("title_font_size", 24)
    bullet_font_size = arguments.get("bullet_font_size", 16)

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"
    slide_id = f"slide_{uuid.uuid4().hex[:8]}"

    requests: list[dict[str, Any]] = [
        {
            "createSlide": {
                "objectId": slide_id,
                "insertionIndex": slide_index,
                "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
            }
        }
    ]

    if title:
        title_id = f"title_{uuid.uuid4().hex[:8]}"
        requests.extend(
            [
                {
                    "createShape": {
                        "objectId": title_id,
                        "shapeType": "TEXT_BOX",
                        "elementProperties": {
                            "pageObjectId": slide_id,
                            "size": {
                                "width": {"magnitude": 8 * 914400, "unit": "EMU"},
                                "height": {"magnitude": 1 * 914400, "unit": "EMU"},
                            },
                            "transform": {
                                "scaleX": 1,
                                "scaleY": 1,
                                "translateX": 0.5 * 914400,
                                "translateY": 0.5 * 914400,
                                "unit": "EMU",
                            },
                        },
                    }
                },
                {"insertText": {"objectId": title_id, "text": title, "insertionIndex": 0}},
                {
                    "updateTextStyle": {
                        "objectId": title_id,
                        "style": {
                            "fontSize": {"magnitude": title_font_size, "unit": "PT"},
                            "bold": True,
                        },
                        "fields": "fontSize,bold",
                    }
                },
            ]
        )

    bullet_text = "\n".join(f"• {point}" for point in bullet_points)
    bullet_id = f"bullets_{uuid.uuid4().hex[:8]}"

    requests.extend(
        [
            {
                "createShape": {
                    "objectId": bullet_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "width": {"magnitude": 8 * 914400, "unit": "EMU"},
                            "height": {"magnitude": 5 * 914400, "unit": "EMU"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": 0.5 * 914400,
                            "translateY": 2 * 914400,
                            "unit": "EMU",
                        },
                    },
                }
            },
            {"insertText": {"objectId": bullet_id, "text": bullet_text, "insertionIndex": 0}},
            {
                "updateTextStyle": {
                    "objectId": bullet_id,
                    "style": {"fontSize": {"magnitude": bullet_font_size, "unit": "PT"}},
                    "fields": "fontSize",
                }
            },
        ]
    )

    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "created",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "slide_index": slide_index,
        "title": title,
        "bullet_points_count": len(bullet_points),
    }


async def _apply_slide_layout(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Apply a predefined layout to a slide."""
    presentation_id = arguments["presentation_id"]
    slide_id = arguments["slide_id"]
    layout_type = arguments["layout_type"]

    url = f"{SLIDES_API_BASE}/presentations/{presentation_id}:batchUpdate"
    request_body = {
        "requests": [
            {
                "updateSlideProperties": {
                    "objectId": slide_id,
                    "slideProperties": {"layoutObjectId": layout_type},
                    "fields": "layoutObjectId",
                }
            }
        ]
    }
    await svc._make_request("POST", url, json_data=request_body)

    return {
        "status": "applied",
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "layout_type": layout_type,
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for all slides tool handlers."""
    return {
        "list_presentations": lambda args: _list_presentations(svc, args),
        "get_presentation": lambda args: _get_presentation(svc, args),
        "get_slide": lambda args: _get_slide(svc, args),
        "get_presentation_text": lambda args: _get_presentation_text(svc, args),
        "create_presentation": lambda args: _create_presentation(svc, args),
        "add_slide": lambda args: _add_slide(svc, args),
        "delete_slide": lambda args: _delete_slide(svc, args),
        "update_slide_text": lambda args: _update_slide_text(svc, args),
        "add_text_box": lambda args: _add_text_box(svc, args),
        "add_image": lambda args: _add_image(svc, args),
        "format_text_in_slide": lambda args: _format_text_in_slide(svc, args),
        "add_formatted_text_box": lambda args: _add_formatted_text_box(svc, args),
        "set_slide_background": lambda args: _set_slide_background(svc, args),
        "create_bulleted_list_slide": lambda args: _create_bulleted_list_slide(svc, args),
        "apply_slide_layout": lambda args: _apply_slide_layout(svc, args),
    }
