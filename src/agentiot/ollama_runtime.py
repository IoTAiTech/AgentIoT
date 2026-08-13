# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

"""Ollama endpoint selection and failover metadata."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse, urlunparse


PRIMARY_ENDPOINT_ENV = "AGENTIOT_OLLAMA_PRIMARY_URL"
SECONDARY_ENDPOINT_ENV = "AGENTIOT_OLLAMA_SECONDARY_URL"
LEGACY_ENDPOINT_ENV = "AGENTIOT_OLLAMA_CHAT_URL"
DEFAULT_ENDPOINT = "http://127.0.0.1:11434/api/chat"


def normalize_ollama_url(value: str, api_path: str = "/api/chat") -> str:
    """Normalize a configured Ollama origin or API URL to one API path."""

    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Ollama endpoint must use HTTP(S) with a host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Ollama endpoint cannot contain credentials or query data")
    port = parsed.port
    if port is None:
        raise ValueError("Ollama endpoint requires an explicit port")
    path = api_path if api_path.startswith("/") else "/" + api_path
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    return urlunparse((parsed.scheme, f"{host}:{port}", path, "", "", ""))


def ollama_endpoint_candidates(configured_url: str | None = None) -> list[dict[str, str]]:
    """Return ordered primary/secondary descriptors without cross-disabling."""

    primary = (
        (configured_url or "").strip()
        or os.getenv(PRIMARY_ENDPOINT_ENV, "").strip()
        or os.getenv(LEGACY_ENDPOINT_ENV, "").strip()
        or DEFAULT_ENDPOINT
    )
    secondary = os.getenv(SECONDARY_ENDPOINT_ENV, "").strip()
    candidates = [("primary", primary), ("secondary", secondary)]
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for role, value in candidates:
        if not value:
            continue
        try:
            chat_url = normalize_ollama_url(value, "/api/chat")
        except (ValueError, UnicodeError):
            result.append(
                {
                    "role": role,
                    "reference": "invalid configuration",
                    "transport": "UNAVAILABLE",
                    "configuration_error": "invalid_endpoint",
                }
            )
            continue
        if chat_url in seen:
            continue
        seen.add(chat_url)
        parsed = urlparse(chat_url)
        result.append(
            {
                "role": role,
                "chat_url": chat_url,
                "version_url": normalize_ollama_url(chat_url, "/api/version"),
                "tags_url": normalize_ollama_url(chat_url, "/api/tags"),
                "reference": f"{parsed.hostname}:{parsed.port}",
                "transport": parsed.scheme.upper(),
            }
        )
    return result


def public_ollama_endpoint_summary(
    endpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return customer-safe failover metadata without private host references."""

    roles = [
        str(item.get("role") or "")
        for item in endpoints
        if not item.get("configuration_error")
    ]
    return {
        "endpoint_count": len(endpoints),
        "primary_configured": "primary" in roles,
        "secondary_configured": "secondary" in roles,
        "failover_configured": {"primary", "secondary"}.issubset(set(roles)),
    }
