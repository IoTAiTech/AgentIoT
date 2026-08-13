# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Tests for customer-safe assistant streaming helpers."""

from types import SimpleNamespace

from agentiot.assistant_streaming import (
    assistant_answer_chunks,
    assistant_provider_runtime_stream_view,
    assistant_sse_event,
)


def test_assistant_sse_event_sorts_and_compacts_payload() -> None:
    event = assistant_sse_event("route", {"z": 2, "a": 1})

    assert event == 'event: route\ndata: {"a":1,"z":2}\n\n'


def test_assistant_answer_chunks_are_bounded_and_nonempty() -> None:
    answer = ("alpha " * 30).strip()
    chunks = assistant_answer_chunks(answer, chunk_size=90)

    assert len(chunks) > 1
    assert all(1 <= len(chunk) <= 90 for chunk in chunks)
    assert " ".join(chunks) == answer
    assert assistant_answer_chunks("   ") == [""]


def test_provider_runtime_stream_view_redacts_payload_material() -> None:
    response = SimpleNamespace(
        provider_runtime={
            "status": "rejected",
            "reason": "grounding_failed",
            "provider": "local",
            "model": "demo",
            "request_id": "req-1",
            "answer": "must not stream",
            "instructions": "private" " prompt",
        }
    )

    assert assistant_provider_runtime_stream_view(response) == {
        "status": "rejected",
        "reason": "grounding_failed",
        "provider": "local",
        "model": "demo",
        "request_id": "req-1",
    }
