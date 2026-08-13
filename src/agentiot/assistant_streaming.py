# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Customer-safe assistant streaming helpers."""

from __future__ import annotations

import json
from typing import Any


def assistant_sse_event(event: str, payload: dict[str, Any]) -> str:
    """Serialize one customer-safe Server-Sent Event."""

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return f"event: {event}\ndata: {body}\n\n"


def assistant_answer_chunks(answer: str, chunk_size: int = 220) -> list[str]:
    """Split assistant text into bounded streaming chunks."""

    clean = answer.strip()
    if not clean:
        return [""]
    chunks: list[str] = []
    remaining = clean
    while remaining:
        if len(remaining) <= chunk_size:
            chunks.append(remaining)
            break
        split_at = remaining.rfind(" ", 0, chunk_size)
        if split_at < max(80, chunk_size // 2):
            split_at = chunk_size
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    return chunks


def assistant_provider_runtime_stream_view(response: Any) -> dict[str, Any] | None:
    """Return provider metadata safe for stream clients."""

    if not response.provider_runtime:
        return None
    allowed = {"status", "reason", "provider", "model", "request_id"}
    return {
        key: value
        for key, value in response.provider_runtime.items()
        if key in allowed
    }
