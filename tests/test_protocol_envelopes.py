# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Tests for customer-safe A2A and MCP protocol envelopes."""

from agentiot.protocol_envelopes import (
    a2a_jsonrpc_error,
    a2a_jsonrpc_success,
    a2a_stream_event,
    mcp_jsonrpc_error,
    mcp_jsonrpc_success,
    mcp_safe_query,
    mcp_safe_top_k,
    mcp_tool_result,
    mcp_validate_tool_arguments,
)


def test_jsonrpc_envelopes_are_stable_and_customer_safe() -> None:
    assert mcp_jsonrpc_success("m1", {"ok": True}) == {
        "jsonrpc": "2.0",
        "id": "m1",
        "result": {"ok": True},
    }
    assert a2a_jsonrpc_success(7, {"sent": True})["result"] == {"sent": True}
    assert mcp_jsonrpc_error("m2", -32601, "Method not found.") == {
        "jsonrpc": "2.0",
        "id": "m2",
        "error": {"code": -32601, "message": "Method not found."},
    }
    assert a2a_jsonrpc_error(None, -32600, "Invalid JSON-RPC version.")["id"] is None


def test_mcp_tool_result_keeps_structured_payload_and_bounds_text() -> None:
    payload = {"summary": "x" * 4100, "count": 2}
    result = mcp_tool_result(payload)

    assert result["structuredContent"] == payload
    assert result["content"][0]["type"] == "text"
    assert len(result["content"][0]["text"]) == 4000
    assert result["isError"] is False


def test_safe_mcp_arguments_are_bounded() -> None:
    assert mcp_safe_query({"query": "  pump status  "}, "fallback") == "pump status"
    assert mcp_safe_query({"query": "x" * 200}, "fallback") == "x" * 160
    assert mcp_safe_query({"query": "   "}, "fallback") == "fallback"
    assert mcp_safe_top_k({"top_k": 99}) == 5
    assert mcp_safe_top_k({"top_k": 0}) == 1
    assert mcp_safe_top_k({"top_k": "bad"}, default=4) == 4


def test_mcp_schema_validation_reports_supported_errors() -> None:
    schema = {
        "type": "object",
        "required": ["query", "top_k"],
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "minLength": 3, "maxLength": 8},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 5},
        },
    }

    assert mcp_validate_tool_arguments(schema, {"query": "pump", "top_k": 3}) == []
    errors = mcp_validate_tool_arguments(
        schema,
        {"query": "xy", "top_k": True, "extra": "blocked"},
    )

    assert "unexpected field: extra" in errors
    assert "query is too short" in errors
    assert "top_k must be an integer" in errors


def test_a2a_stream_event_compacts_payload_without_ascii_loss() -> None:
    event = a2a_stream_event("a2a.ready", {"agent": "prüfung", "count": 2})

    assert event == 'event: a2a.ready\ndata: {"agent":"prüfung","count":2}\n\n'
