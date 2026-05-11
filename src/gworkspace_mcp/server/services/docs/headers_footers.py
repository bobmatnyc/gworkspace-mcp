"""Google Docs headers and footers management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import Tool

from gworkspace_mcp.server.constants import DOCS_API_BASE

if TYPE_CHECKING:
    from gworkspace_mcp.server.base import BaseService


TOOLS: list[Tool] = [
    Tool(
        name="manage_document_header_footer",
        description=(
            "Manage headers and footers on a Google Doc. Actions: "
            "'get' — return existing header/footer IDs and a content preview; "
            "'create_header' / 'create_footer' — add a new default header or footer; "
            "'update_header' / 'update_footer' — insert text into a header or footer (requires header_id/footer_id); "
            "'delete_header' / 'delete_footer' — remove a header or footer."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "get",
                        "create_header",
                        "create_footer",
                        "update_header",
                        "update_footer",
                        "delete_header",
                        "delete_footer",
                    ],
                },
                "document_id": {"type": "string"},
                "header_id": {
                    "type": "string",
                    "description": "Header ID (required for update_header and delete_header)",
                },
                "footer_id": {
                    "type": "string",
                    "description": "Footer ID (required for update_footer and delete_footer)",
                },
                "text": {
                    "type": "string",
                    "description": "Text to insert (required for update_header and update_footer)",
                },
                "account": {
                    "type": "string",
                    "description": "Google account profile to use. Omit to use the default account. Use 'workspace accounts list' to see available profiles.",
                },
            },
            "required": ["action", "document_id"],
        },
    ),
]


# =============================================================================
# Helpers
# =============================================================================


def _extract_segment_text(segment: dict[str, Any]) -> str:
    parts: list[str] = []
    for elem in segment.get("content", []):
        paragraph = elem.get("paragraph")
        if not paragraph:
            continue
        for p_elem in paragraph.get("elements", []):
            text_run = p_elem.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return "".join(parts)


# =============================================================================
# Handler
# =============================================================================


async def _manage_document_header_footer(
    svc: BaseService, arguments: dict[str, Any]
) -> dict[str, Any]:
    action = arguments["action"]
    document_id = arguments["document_id"]
    batch_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

    if action == "get":
        url = f"{DOCS_API_BASE}/documents/{document_id}"
        doc = await svc._make_request(
            "GET",
            url,
            params={"fields": "documentStyle,headers,footers"},
        )
        doc_style = (doc or {}).get("documentStyle", {}) or {}
        headers_obj: dict[str, Any] = (doc or {}).get("headers", {}) or {}
        footers_obj: dict[str, Any] = (doc or {}).get("footers", {}) or {}

        headers_out: list[dict[str, Any]] = []
        for header_id, header in headers_obj.items():
            preview = _extract_segment_text(header)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            headers_out.append({"header_id": header_id, "content_preview": preview})

        footers_out: list[dict[str, Any]] = []
        for footer_id, footer in footers_obj.items():
            preview = _extract_segment_text(footer)
            if len(preview) > 200:
                preview = preview[:200] + "..."
            footers_out.append({"footer_id": footer_id, "content_preview": preview})

        return {
            "document_id": document_id,
            "default_header_id": doc_style.get("defaultHeaderId"),
            "default_footer_id": doc_style.get("defaultFooterId"),
            "headers": headers_out,
            "footers": footers_out,
        }

    if action in ("create_header", "create_footer"):
        request_type = "createHeader" if action == "create_header" else "createFooter"
        response = await svc._make_request(
            "POST",
            batch_url,
            json_data={
                "requests": [
                    {
                        request_type: {
                            "type": "DEFAULT",
                            "sectionBreakLocation": {"index": 0},
                        }
                    }
                ]
            },
        )
        replies = response.get("replies", [])
        new_id = None
        if replies:
            reply = replies[0]
            if action == "create_header":
                new_id = (reply.get("createHeader") or {}).get("headerId")
            else:
                new_id = (reply.get("createFooter") or {}).get("footerId")
        key = "header_id" if action == "create_header" else "footer_id"
        return {
            "status": "created",
            "action": action,
            "document_id": document_id,
            key: new_id,
        }

    if action in ("update_header", "update_footer"):
        text = arguments.get("text")
        if text is None:
            return {"error": f"text is required for {action} action"}
        segment_id_key = "header_id" if action == "update_header" else "footer_id"
        segment_id = arguments.get(segment_id_key)
        if not segment_id:
            return {"error": f"{segment_id_key} is required for {action} action"}

        await svc._make_request(
            "POST",
            batch_url,
            json_data={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": 0, "segmentId": segment_id},
                            "text": text,
                        }
                    }
                ]
            },
        )
        return {
            "status": "updated",
            "action": action,
            "document_id": document_id,
            segment_id_key: segment_id,
            "text_length": len(text),
        }

    if action == "delete_header":
        header_id = arguments.get("header_id") or ""
        if not header_id:
            return {"error": "header_id is required for delete_header action"}
        await svc._make_request(
            "POST",
            batch_url,
            json_data={"requests": [{"deleteHeader": {"headerId": header_id}}]},
        )
        return {
            "status": "deleted",
            "action": action,
            "document_id": document_id,
            "header_id": header_id,
        }

    if action == "delete_footer":
        footer_id = arguments.get("footer_id") or ""
        if not footer_id:
            return {"error": "footer_id is required for delete_footer action"}
        await svc._make_request(
            "POST",
            batch_url,
            json_data={"requests": [{"deleteFooter": {"footerId": footer_id}}]},
        )
        return {
            "status": "deleted",
            "action": action,
            "document_id": document_id,
            "footer_id": footer_id,
        }

    return {"error": f"Unknown action '{action}'"}


def get_handlers(svc: BaseService) -> dict[str, Any]:
    """Return name->callable mapping for Docs header/footer handlers."""
    return {
        "manage_document_header_footer": lambda args: _manage_document_header_footer(svc, args),
    }
