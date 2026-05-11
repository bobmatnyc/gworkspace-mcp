"""Google Docs templates and named-style management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE, DRIVE_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService


NAMED_STYLE_TYPES = [
    "NORMAL_TEXT",
    "TITLE",
    "SUBTITLE",
    "HEADING_1",
    "HEADING_2",
    "HEADING_3",
    "HEADING_4",
    "HEADING_5",
    "HEADING_6",
]


TOOLS: list[Tool] = [
    Tool(
        name="create_document_from_template",
        description=(
            "Create a new Google Doc by copying a template document, optionally replacing "
            "placeholder strings in the body. Placeholders should be wrapped in double curly braces, "
            "e.g. {{NAME}}. Pass replacements as a mapping of placeholder names (without braces) to values."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "ID of the source template document to copy",
                },
                "title": {
                    "type": "string",
                    "description": "Title of the new document",
                },
                "replacements": {
                    "type": "object",
                    "description": "Mapping of placeholder names to replacement values. Each KEY is matched as {{KEY}}.",
                    "additionalProperties": {"type": "string"},
                },
                "destination_folder_id": {
                    "type": "string",
                    "description": "Optional Drive folder ID to place the new document in",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["template_id", "title"],
        },
    ),
    Tool(
        name="get_document_named_styles",
        description=(
            "Get the named style definitions (NORMAL_TEXT, TITLE, SUBTITLE, HEADING_1..6) for a "
            "Google Doc, including font family, size, weight, color, and paragraph spacing."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id"],
        },
    ),
    Tool(
        name="update_document_named_styles",
        description=(
            "Update one or more named style definitions in a Google Doc. Each style update can "
            "modify text formatting (bold, italic, font_size, font_family, text_color) and/or "
            "paragraph formatting (alignment, line_spacing, space_above, space_below)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "styles": {
                    "type": "array",
                    "description": "List of named style updates to apply",
                    "items": {
                        "type": "object",
                        "properties": {
                            "named_style_type": {
                                "type": "string",
                                "enum": NAMED_STYLE_TYPES,
                            },
                            "text_style": {
                                "type": "object",
                                "properties": {
                                    "bold": {"type": "boolean"},
                                    "italic": {"type": "boolean"},
                                    "underline": {"type": "boolean"},
                                    "font_size": {"type": "number"},
                                    "font_family": {"type": "string"},
                                    "text_color": {
                                        "type": "object",
                                        "properties": {
                                            "red": {"type": "number"},
                                            "green": {"type": "number"},
                                            "blue": {"type": "number"},
                                        },
                                    },
                                },
                            },
                            "paragraph_style": {
                                "type": "object",
                                "properties": {
                                    "alignment": {
                                        "type": "string",
                                        "enum": ["START", "CENTER", "END", "JUSTIFIED"],
                                    },
                                    "line_spacing": {"type": "number"},
                                    "space_above": {"type": "number"},
                                    "space_below": {"type": "number"},
                                },
                            },
                        },
                        "required": ["named_style_type"],
                    },
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["document_id", "styles"],
        },
    ),
]


# =============================================================================
# Handlers
# =============================================================================


async def _create_document_from_template(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    template_id = arguments["template_id"]
    title = arguments["title"]
    replacements: dict[str, str] = arguments.get("replacements") or {}
    destination_folder_id = arguments.get("destination_folder_id")

    # Step 1: Copy the template via Drive API
    copy_url = f"{DRIVE_API_BASE}/files/{template_id}/copy"
    copy_body: dict[str, Any] = {"name": title}
    if destination_folder_id:
        copy_body["parents"] = [destination_folder_id]

    copy_resp = await svc._make_request(
        "POST",
        copy_url,
        params={"fields": "id,name,webViewLink"},
        json_data=copy_body,
    )

    new_doc_id = copy_resp.get("id")
    web_view_link = copy_resp.get("webViewLink", "")

    # Step 2: Apply text replacements
    replacements_applied = 0
    if new_doc_id and replacements:
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": f"{{{{{key}}}}}", "matchCase": True},
                    "replaceText": value,
                }
            }
            for key, value in replacements.items()
        ]
        batch_url = f"{DOCS_API_BASE}/documents/{new_doc_id}:batchUpdate"
        await svc._make_request("POST", batch_url, json_data={"requests": requests})
        replacements_applied = len(requests)

    return {
        "status": "created",
        "document_id": new_doc_id,
        "title": copy_resp.get("name", title),
        "web_view_link": web_view_link,
        "replacements_applied": replacements_applied,
    }


async def _get_document_named_styles(svc: BaseService, arguments: dict[str, Any]) -> dict[str, Any]:
    document_id = arguments["document_id"]
    url = f"{DOCS_API_BASE}/documents/{document_id}"
    doc = await svc._make_request("GET", url, params={"fields": "namedStyles"})

    named_styles_data = (doc or {}).get("namedStyles", {}).get("styles", [])
    parsed: list[dict[str, Any]] = []

    for style in named_styles_data:
        text_style = style.get("textStyle", {}) or {}
        paragraph_style = style.get("paragraphStyle", {}) or {}

        weighted_font = text_style.get("weightedFontFamily", {}) or {}
        font_size_obj = text_style.get("fontSize", {}) or {}
        foreground = text_style.get("foregroundColor", {}).get("color", {}).get("rgbColor")

        space_above = paragraph_style.get("spaceAbove", {}) or {}
        space_below = paragraph_style.get("spaceBelow", {}) or {}

        parsed.append(
            {
                "named_style_type": style.get("namedStyleType"),
                "text_style": {
                    "font_family": weighted_font.get("fontFamily"),
                    "font_weight": weighted_font.get("weight"),
                    "font_size": font_size_obj.get("magnitude"),
                    "bold": text_style.get("bold"),
                    "italic": text_style.get("italic"),
                    "underline": text_style.get("underline"),
                    "foreground_color": foreground,
                },
                "paragraph_style": {
                    "alignment": paragraph_style.get("alignment"),
                    "line_spacing": paragraph_style.get("lineSpacing"),
                    "space_above": space_above.get("magnitude"),
                    "space_below": space_below.get("magnitude"),
                },
            }
        )

    return {"named_styles": parsed, "count": len(parsed)}


def _build_named_style_request(style_spec: dict[str, Any]) -> dict[str, Any] | None:
    """Build a single updateNamedStyle request from a high-level spec."""
    named_style_type = style_spec.get("named_style_type")
    if not named_style_type:
        return None

    text_style_spec: dict[str, Any] = style_spec.get("text_style") or {}
    paragraph_style_spec: dict[str, Any] = style_spec.get("paragraph_style") or {}

    text_style: dict[str, Any] = {}
    text_fields: list[str] = []
    if "bold" in text_style_spec:
        text_style["bold"] = text_style_spec["bold"]
        text_fields.append("bold")
    if "italic" in text_style_spec:
        text_style["italic"] = text_style_spec["italic"]
        text_fields.append("italic")
    if "underline" in text_style_spec:
        text_style["underline"] = text_style_spec["underline"]
        text_fields.append("underline")
    if "font_size" in text_style_spec:
        text_style["fontSize"] = {
            "magnitude": text_style_spec["font_size"],
            "unit": "PT",
        }
        text_fields.append("fontSize")
    if "font_family" in text_style_spec:
        text_style["weightedFontFamily"] = {"fontFamily": text_style_spec["font_family"]}
        text_fields.append("weightedFontFamily")
    if "text_color" in text_style_spec:
        text_style["foregroundColor"] = {"color": {"rgbColor": text_style_spec["text_color"]}}
        text_fields.append("foregroundColor")

    paragraph_style: dict[str, Any] = {}
    paragraph_fields: list[str] = []
    if "alignment" in paragraph_style_spec:
        paragraph_style["alignment"] = paragraph_style_spec["alignment"]
        paragraph_fields.append("alignment")
    if "line_spacing" in paragraph_style_spec:
        paragraph_style["lineSpacing"] = paragraph_style_spec["line_spacing"]
        paragraph_fields.append("lineSpacing")
    if "space_above" in paragraph_style_spec:
        paragraph_style["spaceAbove"] = {
            "magnitude": paragraph_style_spec["space_above"],
            "unit": "PT",
        }
        paragraph_fields.append("spaceAbove")
    if "space_below" in paragraph_style_spec:
        paragraph_style["spaceBelow"] = {
            "magnitude": paragraph_style_spec["space_below"],
            "unit": "PT",
        }
        paragraph_fields.append("spaceBelow")

    if not text_fields and not paragraph_fields:
        return None

    named_style: dict[str, Any] = {"namedStyleType": named_style_type}
    if text_style:
        named_style["textStyle"] = text_style
    if paragraph_style:
        named_style["paragraphStyle"] = paragraph_style

    request: dict[str, Any] = {"updateNamedStyle": {"namedStyle": named_style}}
    if text_fields:
        request["updateNamedStyle"]["textStyleFields"] = ",".join(text_fields)
    if paragraph_fields:
        request["updateNamedStyle"]["paragraphStyleFields"] = ",".join(paragraph_fields)

    return request


async def _update_document_named_styles(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    document_id = arguments["document_id"]
    styles: list[dict[str, Any]] = arguments.get("styles") or []

    requests: list[dict[str, Any]] = []
    applied_types: list[str] = []
    for spec in styles:
        req = _build_named_style_request(spec)
        if req:
            requests.append(req)
            applied_types.append(spec.get("named_style_type", ""))

    if not requests:
        return {"status": "no_styles_applied", "document_id": document_id}

    url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
    await svc._make_request("POST", url, json_data={"requests": requests})

    return {
        "status": "updated",
        "document_id": document_id,
        "styles_applied": applied_types,
        "count": len(applied_types),
    }


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs templates handlers."""
    return {
        "create_document_from_template": lambda args: _create_document_from_template(svc, args),
        "get_document_named_styles": lambda args: _get_document_named_styles(svc, args),
        "update_document_named_styles": lambda args: _update_document_named_styles(svc, args),
    }
