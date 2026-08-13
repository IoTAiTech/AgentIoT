# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Customer-safe A2A and MCP protocol envelope helpers."""

from __future__ import annotations

import json
from typing import Any


def mcp_jsonrpc_success(request_id: str | int | None, result: dict[str, Any]) -> dict[str, Any]:
    """Return a JSON-RPC success envelope."""

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def mcp_jsonrpc_error(
    request_id: str | int | None, code: int, message: str
) -> dict[str, Any]:
    """Return a JSON-RPC error envelope without leaking internals."""

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def mcp_tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Package tool output as MCP content plus structured content."""

    text = json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
    return {
        "resultType": "complete",
        "content": [{"type": "text", "text": text[:4000]}],
        "structuredContent": payload,
        "isError": False,
    }


def mcp_safe_query(arguments: dict[str, Any], default: str) -> str:
    """Return a bounded, prompt-free query for read-only MCP tools."""

    value = str(arguments.get("query", default)).strip()
    return value[:160] or default


def mcp_safe_top_k(arguments: dict[str, Any], default: int = 3) -> int:
    """Return a bounded retrieval count."""

    try:
        value = int(arguments.get("top_k", default))
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, 5))


def mcp_validate_tool_arguments(
    schema: dict[str, Any], arguments: dict[str, Any]
) -> list[str]:
    """Validate the supported MCP JSON Schema subset before tool execution."""

    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    additional_allowed = schema.get("additionalProperties", True) is not False
    errors: list[str] = []

    for key in required:
        if key not in arguments:
            errors.append(f"missing required field: {key}")
    if not additional_allowed:
        for key in arguments:
            if key not in properties:
                errors.append(f"unexpected field: {key}")

    for key, value in arguments.items():
        rule = properties.get(key)
        if not isinstance(rule, dict):
            continue
        expected_type = rule.get("type")
        if expected_type == "string":
            if not isinstance(value, str):
                errors.append(f"{key} must be a string")
                continue
            min_length = int(rule.get("minLength", 0) or 0)
            max_length = int(rule.get("maxLength", 160) or 160)
            if len(value) < min_length:
                errors.append(f"{key} is too short")
            if len(value) > max_length:
                errors.append(f"{key} is too long")
        elif expected_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"{key} must be an integer")
                continue
            minimum = rule.get("minimum")
            maximum = rule.get("maximum")
            if isinstance(minimum, int) and value < minimum:
                errors.append(f"{key} is below minimum")
            if isinstance(maximum, int) and value > maximum:
                errors.append(f"{key} is above maximum")
    return errors


def a2a_jsonrpc_success(
    request_id: str | int | None, result: dict[str, Any]
) -> dict[str, Any]:
    """Return an A2A JSON-RPC success envelope."""

    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def a2a_jsonrpc_error(
    request_id: str | int | None, code: int, message: str
) -> dict[str, Any]:
    """Return an A2A JSON-RPC error envelope without leaking internals."""

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def a2a_stream_event(event: str, payload: dict[str, Any]) -> str:
    """Serialize one customer-safe A2A SSE event."""

    data = json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"
