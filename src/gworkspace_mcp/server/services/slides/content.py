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
        name="add_slide_content",
        description=(
            "Add content to a Google Slides slide. "
            "type='text_box': add a plain text box (presentation_id, slide_id, text required). "
            "type='formatted_text_box': add a text box with font formatting (presentation_id, slide_id, text required; optional font_size, bold, italic, font_color). "
            "type='image': add an image from URL (presentation_id, slide_id, image_url required). "
            "type='bulleted_list': create a new slide with a bulleted list (presentation_id, slide_index, bullet_points required; optional title)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "description": "Content type to add: 'text_box', 'formatted_text_box', 'image', 'bulleted_list'",
                    "enum": ["text_box", "formatted_text_box", "image", "bulleted_list"],
                },
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID (required for all types)",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Object ID of the target slide (required for text_box, formatted_text_box, image)",
                },
                "slide_index": {
                    "type": "integer",
                    "description": "Zero-based position to insert the new slide (required for bulleted_list)",
                },
                "text": {
                    "type": "string",
                    "description": "Text content (required for text_box, formatted_text_box, bulleted_list)",
                },
                "image_url": {
                    "type": "string",
                    "description": "URL of the image to insert, must be publicly accessible (required for image)",
                },
                "x_pt": {
                    "type": "number",
                    "description": "X position in points from left edge (default: 100; text_box, formatted_text_box, image)",
                    "default": 100,
                },
                "y_pt": {
                    "type": "number",
                    "description": "Y position in points from top edge (default: 100; text_box, formatted_text_box, image)",
                    "default": 100,
                },
                "width_pt": {
                    "type": "number",
                    "description": "Width in points (default: 300; text_box, formatted_text_box, image)",
                    "default": 300,
                },
                "height_pt": {
                    "type": "number",
                    "description": "Height in points (default: 50 for text_box, 100 for formatted_text_box, 200 for image)",
                },
                "font_size": {
                    "type": "number",
                    "description": "Font size in points (default: 14; formatted_text_box only)",
                    "default": 14,
                },
                "bold": {
                    "type": "boolean",
                    "description": "Bold formatting (formatted_text_box only)",
                    "default": False,
                },
                "italic": {
                    "type": "boolean",
                    "description": "Italic formatting (formatted_text_box only)",
                    "default": False,
                },
                "font_color": {
                    "type": "object",
                    "description": "Font color in RGB format with keys red, green, blue (0–1 each; formatted_text_box only)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "title": {
                    "type": "string",
                    "description": "Slide title (optional; bulleted_list only)",
                },
                "bullet_points": {
                    "type": "array",
                    "description": "Array of bullet point strings (required for bulleted_list)",
                    "items": {"type": "string"},
                },
                "title_font_size": {
                    "type": "number",
                    "description": "Title font size in points (default: 24; bulleted_list only)",
                    "default": 24,
                },
                "bullet_font_size": {
                    "type": "number",
                    "description": "Bullet point font size in points (default: 16; bulleted_list only)",
                    "default": 16,
                },
            },
            "required": ["type", "presentation_id"],
        },
    ),
    Tool(
        name="format_slide",
        description=(
            "Format elements in a Google Slides slide. "
            "action='format_text': apply text styling to a range in a shape (presentation_id, slide_id, shape_id, start_index, end_index required; optional bold, italic, font_size, font_color). "
            "action='set_background': set slide background color or image (presentation_id, slide_id, background_type required; color required for COLOR, image_url required for IMAGE). "
            "action='apply_layout': apply a predefined layout to a slide (presentation_id, slide_id, layout_type required)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Formatting action: 'format_text', 'set_background', 'apply_layout'",
                    "enum": ["format_text", "set_background", "apply_layout"],
                },
                "presentation_id": {
                    "type": "string",
                    "description": "Google Slides presentation ID (required for all actions)",
                },
                "slide_id": {
                    "type": "string",
                    "description": "Object ID of the slide (required for all actions)",
                },
                "shape_id": {
                    "type": "string",
                    "description": "Object ID of the text shape (required for format_text)",
                },
                "start_index": {
                    "type": "integer",
                    "description": "Start character index for formatting range (required for format_text)",
                },
                "end_index": {
                    "type": "integer",
                    "description": "End character index for formatting range (required for format_text)",
                },
                "bold": {
                    "type": "boolean",
                    "description": "Bold formatting (format_text only)",
                },
                "italic": {
                    "type": "boolean",
                    "description": "Italic formatting (format_text only)",
                },
                "font_size": {
                    "type": "number",
                    "description": "Font size in points (format_text only)",
                },
                "font_color": {
                    "type": "object",
                    "description": "Font color in RGB format with keys red, green, blue (0–1 each; format_text only)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "background_type": {
                    "type": "string",
                    "description": "Background type (required for set_background): 'COLOR' or 'IMAGE'",
                    "enum": ["COLOR", "IMAGE"],
                },
                "color": {
                    "type": "object",
                    "description": "Background color in RGB format (required when background_type is COLOR)",
                    "properties": {
                        "red": {"type": "number", "minimum": 0, "maximum": 1},
                        "green": {"type": "number", "minimum": 0, "maximum": 1},
                        "blue": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "image_url": {
                    "type": "string",
                    "description": "URL of background image (required when background_type is IMAGE)",
                },
                "layout_type": {
                    "type": "string",
                    "description": "Predefined layout to apply (required for apply_layout)",
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
            "required": ["action", "presentation_id", "slide_id"],
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


# =============================================================================
# Dispatcher functions
# =============================================================================


async def _add_slide_content(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch add_slide_content type to appropriate handler."""
    content_type = arguments.get("type")
    if content_type == "text_box":
        if "slide_id" not in arguments:
            raise ValueError("slide_id is required for type='text_box'")
        if "text" not in arguments:
            raise ValueError("text is required for type='text_box'")
        return await _add_text_box(svc, arguments)
    elif content_type == "formatted_text_box":
        if "slide_id" not in arguments:
            raise ValueError("slide_id is required for type='formatted_text_box'")
        if "text" not in arguments:
            raise ValueError("text is required for type='formatted_text_box'")
        return await _add_formatted_text_box(svc, arguments)
    elif content_type == "image":
        if "slide_id" not in arguments:
            raise ValueError("slide_id is required for type='image'")
        if "image_url" not in arguments:
            raise ValueError("image_url is required for type='image'")
        return await _add_image(svc, arguments)
    elif content_type == "bulleted_list":
        if "slide_index" not in arguments:
            raise ValueError("slide_index is required for type='bulleted_list'")
        if "bullet_points" not in arguments:
            raise ValueError("bullet_points is required for type='bulleted_list'")
        return await _create_bulleted_list_slide(svc, arguments)
    else:
        raise ValueError(
            f"Unknown type: {content_type!r}. "
            "Use 'text_box', 'formatted_text_box', 'image', or 'bulleted_list'."
        )


async def _format_slide(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch format_slide action to appropriate handler."""
    action = arguments.get("action")
    if action == "format_text":
        if "shape_id" not in arguments:
            raise ValueError("shape_id is required for action='format_text'")
        if "start_index" not in arguments:
            raise ValueError("start_index is required for action='format_text'")
        if "end_index" not in arguments:
            raise ValueError("end_index is required for action='format_text'")
        return await _format_text_in_slide(svc, arguments)
    elif action == "set_background":
        if "background_type" not in arguments:
            raise ValueError("background_type is required for action='set_background'")
        return await _set_slide_background(svc, arguments)
    elif action == "apply_layout":
        if "layout_type" not in arguments:
            raise ValueError("layout_type is required for action='apply_layout'")
        return await _apply_slide_layout(svc, arguments)
    else:
        raise ValueError(
            f"Unknown action: {action!r}. Use 'format_text', 'set_background', or 'apply_layout'."
        )


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Slides content handlers."""
    return {
        "add_slide_content": lambda args: _add_slide_content(svc, args),
        "format_slide": lambda args: _format_slide(svc, args),
    }
