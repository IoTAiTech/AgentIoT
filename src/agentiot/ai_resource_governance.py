# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""AI model usage and memory-governance helpers."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any


def estimate_token_count(text: str | None) -> int:
    """Estimate tokens for providers that do not return usage metadata."""

    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def parse_usage_timestamp(value: str) -> datetime:
    """Parse persisted UTC timestamps for usage-window calculations."""

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def provider_token_count(value: Any, fallback: int) -> int:
    """Return a safe non-negative provider token counter."""

    try:
        if isinstance(value, bool):
            raise ValueError
        count = int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback
    return count if count >= 0 else fallback


def system_memory_mb() -> int:
    """Return an approximate physical memory budget for recommendations."""

    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return max(512, int((pages * page_size) / (1024 * 1024)))
    except (AttributeError, OSError, ValueError):
        return int(os.getenv("AGENTIOT_MEMORY_AVAILABLE_MB", "2048"))


def extract_provider_token_usage(
    provider: str, payload: dict[str, Any], prompt: str, answer: str
) -> dict[str, Any]:
    """Normalize provider usage counters or estimate them when unavailable."""

    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    gemini_usage = (
        payload.get("usageMetadata")
        if isinstance(payload.get("usageMetadata"), dict)
        else {}
    )
    if provider == "openai":
        input_tokens = provider_token_count(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or None,
            estimate_token_count(prompt),
        )
        output_tokens = provider_token_count(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or None,
            estimate_token_count(answer),
        )
        source = "provider_reported" if usage else "estimated"
    elif provider == "gemini":
        input_tokens = provider_token_count(
            gemini_usage.get("promptTokenCount"),
            estimate_token_count(prompt),
        )
        output_tokens = provider_token_count(
            gemini_usage.get("candidatesTokenCount"),
            estimate_token_count(answer),
        )
        source = "provider_reported" if gemini_usage else "estimated"
    elif provider == "huggingface":
        input_tokens = provider_token_count(
            usage.get("prompt_tokens"),
            estimate_token_count(prompt),
        )
        output_tokens = provider_token_count(
            usage.get("completion_tokens"),
            estimate_token_count(answer),
        )
        source = "provider_reported" if usage else "estimated"
    else:
        input_tokens = estimate_token_count(prompt)
        output_tokens = estimate_token_count(answer)
        source = "estimated"
    return {
        "input_tokens": max(0, input_tokens),
        "output_tokens": max(0, output_tokens),
        "total_tokens": max(0, input_tokens + output_tokens),
        "source": source,
    }
