"""Google Slides content sub-module: text boxes, images, formatting, backgrounds, lists."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import SLIDES_API_BASE
from gworkspace_mcp.server.services.slides.core import EMU_PER_PT

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService

TOOLS: list[Tool] = [
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


# =============================================================================
# Handler functions
# =============================================================================


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
    """Return name->callable mapping for Slides content handlers."""
    return {
        "add_text_box": lambda args: _add_text_box(svc, args),
        "add_image": lambda args: _add_image(svc, args),
        "format_text_in_slide": lambda args: _format_text_in_slide(svc, args),
        "add_formatted_text_box": lambda args: _add_formatted_text_box(svc, args),
        "set_slide_background": lambda args: _set_slide_background(svc, args),
        "create_bulleted_list_slide": lambda args: _create_bulleted_list_slide(svc, args),
        "apply_slide_layout": lambda args: _apply_slide_layout(svc, args),
    }
