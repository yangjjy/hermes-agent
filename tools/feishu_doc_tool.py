"""Feishu Document Tool -- read document content via Feishu/Lark API.

Provides ``feishu_doc_read`` for reading document content as plain text.
Uses the same lazy-import + BaseRequest pattern as feishu_comment.py.
"""

import re
from urllib.parse import urlsplit

from tools.feishu_lark import (
    _check_feishu,
    build_request,
    get_client,
    raw_body,
    response_data,
    set_client)
from tools.registry import registry, tool_error, tool_result

_RAW_CONTENT_URI = "/open-apis/docx/v1/documents/:document_id/raw_content"
_WIKI_NODE_URI = "/open-apis/wiki/v2/spaces/get_node"

FEISHU_DOC_READ_SCHEMA = {
    "name": "feishu_doc_read",
    "description": (
        "Read an authorized Feishu/Lark cloud document or Wiki document as plain text, "
        "from a shared URL or document token in a DM or document comment. "
        "For Wiki documents pass the full /wiki/ URL."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "doc_token": {
                "type": "string",
                "description": "A full /docx/ or /wiki/ URL, or a cloud document token.",
            },
        },
        "required": ["doc_token"],
    },
}


def _document_reference(value):
    """Extract a token, never dispatch to a user-supplied URL."""
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return "docx", value
    url = urlsplit(value)
    host = url.hostname or ""
    allowed_host = any(host == domain or host.endswith("." + domain) for domain in ("feishu.cn", "larksuite.com"))
    match = re.fullmatch(r"/(docx|wiki)/([A-Za-z0-9_-]+)/?", url.path)
    if url.scheme != "https" or not allowed_host or url.username or url.password or not match:
        raise ValueError("Expected a Feishu/Lark /docx/ or /wiki/ URL or a document token")
    return match.group(1), match.group(2)


def _resolve_document(client, kind, token):
    if kind != "wiki":
        return token
    response = client.request(build_request("GET", _WIKI_NODE_URI, queries=[("token", token)]))
    if getattr(response, "code", None) != 0:
        raise ValueError(f"Wiki node access failed: code={getattr(response, 'code', None)}")
    node = response_data(response).get("node", {})
    if not isinstance(node, dict) or node.get("obj_type") != "docx":
        raise ValueError("Wiki target is not a supported cloud document")
    token = node.get("obj_token", "")
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
        raise ValueError("Wiki node returned no valid document token")
    return token


def _handle_feishu_doc_read(args: dict, **kwargs) -> str:
    doc_token = args.get("doc_token", "").strip()
    if not doc_token:
        return tool_error("doc_token is required")
    client = get_client()
    if client is None:
        return tool_error("Feishu client not available in this turn")
    try:
        kind, token = _document_reference(doc_token)
        doc_token = _resolve_document(client, kind, token)
        request = build_request("GET", _RAW_CONTENT_URI, paths={"document_id": doc_token})
    except ValueError as exc:
        return tool_error(str(exc))
    except ImportError:
        return tool_error("lark_oapi not installed")

    # Handlers run synchronously in a worker thread (no event loop): call the blocking client.
    response = client.request(request)
    code = getattr(response, "code", None)
    if code != 0:
        return tool_error(f"Failed to read document: code={code} msg={getattr(response, 'msg', 'unknown error')}")

    body = raw_body(response)
    if body is not None:
        try:
            return tool_result(success=True, content=body.get("data", {}).get("content", ""))
        except AttributeError:
            pass
    data = getattr(response, "data", None)  # fallback: the typed response.data
    if data:
        content = data.get("content", "") if isinstance(data, dict) else getattr(data, "content", str(data))
        return tool_result(success=True, content=content)
    return tool_error("No content returned from document API")


registry.register(
    name="feishu_doc_read", toolset="feishu_doc", schema=FEISHU_DOC_READ_SCHEMA, handler=_handle_feishu_doc_read,
    check_fn=_check_feishu, requires_env=[], is_async=False, description="Read Feishu document content",
    emoji="\U0001f4c4")
