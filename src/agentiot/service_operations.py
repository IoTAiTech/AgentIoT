# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

"""Bounded HTTP service inventory and local application health probes."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any, Mapping
from urllib.parse import urlparse


SERVICE_OPERATIONS_POLICY = {
    "discovery": "fixed_product_contracts_only",
    "arbitrary_targets_accepted": False,
    "host_commands_allowed": False,
    "remediation": "safe_recheck_then_hitl_proposal",
}

HTTP_SERVICE_CONTRACTS: tuple[dict[str, str], ...] = (
    {
        "service_id": "dashboard-ui",
        "name": "Dashboard UI",
        "endpoint": "/dashboard",
        "access": "authenticated in production",
        "transport": "HTTPS edge / HTTP internal",
        "unauthenticated_gate": "login_redirect",
        "owner_agent_id": "ui_ux_experience_auditor",
    },
    {
        "service_id": "health-api",
        "name": "Health API",
        "endpoint": "/healthz",
        "access": "public",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "operations_coordinator",
    },
    {
        "service_id": "readiness-api",
        "name": "Readiness API",
        "endpoint": "/readyz",
        "access": "public",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "operations_coordinator",
    },
    {
        "service_id": "operational-truth",
        "name": "Operational Truth",
        "endpoint": "/api/system/operational-truth",
        "access": "authenticated in production",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "operations_coordinator",
    },
    {
        "service_id": "cmdb",
        "name": "CMDB",
        "endpoint": "/api/cmdb/configuration-items",
        "access": "authenticated in production",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "device_fleet_agent",
    },
    {
        "service_id": "mqtt-adapter",
        "name": "MQTT Adapter",
        "endpoint": "/api/adapters/mqtt/broker/status",
        "access": "public status",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "device_fleet_agent",
    },
    {
        "service_id": "rest-adapter",
        "name": "REST Adapter",
        "endpoint": "/api/adapters/rest/status",
        "access": "public status",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "device_fleet_agent",
    },
    {
        "service_id": "agent-orchestration",
        "name": "Agent Orchestration",
        "endpoint": "/api/orchestration/evidence-matrix",
        "access": "authenticated in production",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "operations_coordinator",
    },
    {
        "service_id": "ai-routing",
        "name": "AI Routing",
        "endpoint": "/api/ai/routing",
        "access": "public readiness",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "ai_diagnosis_agent",
    },
    {
        "service_id": "reports",
        "name": "Reports",
        "endpoint": "/api/reports/dashboard",
        "access": "public summary",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "reporting_compliance_agent",
    },
    {
        "service_id": "settings",
        "name": "Settings",
        "endpoint": "/api/settings",
        "access": "public status / admin changes",
        "transport": "HTTPS edge / HTTP internal",
        "owner_agent_id": "admin_governance_agent",
    },
)

SECURITY_HEADER_NAMES = (
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep the fixed local probe on the configured application origin."""

    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def utc_now() -> str:
    """Return a compact UTC timestamp."""

    return datetime.now(UTC).replace(microsecond=0).isoformat()


def service_contracts() -> list[dict[str, str]]:
    """Return copies of the fixed application service contracts."""

    return [dict(item) for item in HTTP_SERVICE_CONTRACTS]


def internal_base_url() -> str:
    """Return a loopback-only origin for same-application probes."""

    candidate = os.getenv(
        "AGENTIOT_INTERNAL_SERVICE_BASE_URL",
        "http://127.0.0.1:8080",
    ).strip()
    parsed = urlparse(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port is None
    ):
        return "http://127.0.0.1:8080"
    return f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"


def _security_summary(headers: Mapping[str, str]) -> dict[str, Any]:
    normalized = {str(name).lower(): value for name, value in headers.items()}
    present = sum(1 for name in SECURITY_HEADER_NAMES if normalized.get(name))
    required = len(SECURITY_HEADER_NAMES)
    return {
        "state": "complete" if present == required else "partial",
        "score": round((present / required) * 100),
        "present": present,
        "required": required,
    }


def status_from_http(
    http_status: int | None,
    access: str,
    *,
    authenticated_probe: bool = False,
) -> tuple[str, str | None]:
    """Classify reachability without hiding unexpected authentication gates."""

    if http_status is None:
        return "down", "connection_failed"
    if 200 <= http_status < 300:
        return "healthy", None
    if 300 <= http_status < 400:
        return "degraded", "unexpected_redirect"
    if http_status in {401, 403}:
        protected_read = access.lower().startswith(
            ("authenticated", "admin only")
        )
        if protected_read:
            return (
                ("degraded", "authenticated_probe_rejected")
                if authenticated_probe
                else ("degraded", "authenticated_probe_required")
            )
        return "degraded", "unexpected_auth_gate"
    if 400 <= http_status < 500:
        return "degraded", "http_4xx"
    return "down", "http_5xx"


def probe_http_service(
    contract: Mapping[str, str],
    timeout_seconds: float = 1.5,
    *,
    auth_headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Probe one fixed route and verify protected authentication behavior."""

    endpoint = str(contract["endpoint"])
    if not endpoint.startswith("/") or ".." in endpoint or "://" in endpoint:
        raise ValueError("Invalid fixed service endpoint")
    public_headers = {"Accept": "application/json,text/html;q=0.8"}
    request_headers = dict(public_headers)
    if auth_headers:
        for name, value in auth_headers.items():
            if name not in {"X-Operator-Token", "X-Admin-Token"}:
                raise ValueError("Unsupported service probe credential header")
            if value:
                request_headers[name] = value
    opener = urllib.request.build_opener(_NoRedirect())
    bounded_timeout = max(0.1, min(timeout_seconds, 5.0))

    def execute_probe(
        headers_to_send: Mapping[str, str],
    ) -> tuple[int | None, Mapping[str, str], int]:
        request = urllib.request.Request(
            internal_base_url() + endpoint,
            method="GET",
            headers=dict(headers_to_send),
        )
        started = time.monotonic()
        response_headers: Mapping[str, str] = {}
        try:
            with opener.open(request, timeout=bounded_timeout) as response:
                response_status: int | None = int(response.status)
                response_headers = response.headers
                response.read(1025)
        except urllib.error.HTTPError as error:
            response_status = int(error.code)
            response_headers = error.headers
        except (OSError, TimeoutError, urllib.error.URLError):
            response_status = None
        latency_ms = max(0, round((time.monotonic() - started) * 1000))
        return response_status, response_headers, latency_ms

    gate_status: int | None = None
    gate_headers: Mapping[str, str] = {}
    gate_latency_ms = 0
    if auth_headers:
        gate_status, gate_headers, gate_latency_ms = execute_probe(public_headers)
    status_code, headers, latency_ms = execute_probe(request_headers)
    status, issue_code = status_from_http(
        status_code,
        str(contract["access"]),
        authenticated_probe=bool(auth_headers),
    )
    login_redirect_gate = (
        str(contract.get("unauthenticated_gate") or "") == "login_redirect"
    )
    expected_login_location = f"/login?next={endpoint}"
    gate_is_valid = gate_status in {401, 403}
    if login_redirect_gate:
        gate_is_valid = bool(
            gate_status == 303
            and str(gate_headers.get("Location") or "")
            == expected_login_location
        )
        response_is_valid = bool(
            status_code == 303
            and str(headers.get("Location") or "") == expected_login_location
        )
        if gate_is_valid and response_is_valid:
            status = "healthy"
            issue_code = None
    if auth_headers and not gate_is_valid:
        if status == "healthy":
            status = "degraded" if gate_status is not None else "down"
            issue_code = (
                "authentication_gate_missing"
                if gate_status is not None and 200 <= gate_status < 400
                else "authentication_gate_unavailable"
            )
    return {
        "service_id": contract["service_id"],
        "status": status,
        "http_status": status_code,
        "latency_ms": gate_latency_ms + latency_ms,
        "security": _security_summary(headers),
        "issue_code": issue_code,
        "checked_at": utc_now(),
    }


def normalize_probe_result(
    contract: Mapping[str, str],
    result: Mapping[str, Any],
    *,
    previous_failures: int = 0,
) -> dict[str, Any]:
    """Normalize a probe receipt before persistence or display."""

    status = str(result.get("status") or "down").lower()
    if status not in {"healthy", "degraded", "down"}:
        status = "down"
    security = result.get("security")
    if not isinstance(security, Mapping):
        security = {"state": "unavailable", "score": 0, "present": 0, "required": 4}
    http_status = result.get("http_status")
    latency_ms = result.get("latency_ms")
    consecutive_failures = 0 if status == "healthy" else max(0, previous_failures) + 1
    return {
        "service_id": str(contract["service_id"]),
        "status": status,
        "http_status": int(http_status) if isinstance(http_status, int) else None,
        "latency_ms": max(0, int(latency_ms)) if isinstance(latency_ms, (int, float)) else None,
        "security": {
            "state": str(security.get("state") or "unavailable"),
            "score": max(0, min(int(security.get("score") or 0), 100)),
            "present": max(0, int(security.get("present") or 0)),
            "required": max(0, int(security.get("required") or 0)),
        },
        "issue_code": (
            str(result.get("issue_code"))
            if result.get("issue_code")
            else None
        ),
        "checked_at": str(result.get("checked_at") or utc_now()),
        "consecutive_failures": consecutive_failures,
    }


def public_service_inventory(
    health_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge fixed service contracts with their latest persisted health."""

    latest = {str(row["service_id"]): row for row in health_rows}
    items = []
    for contract in HTTP_SERVICE_CONTRACTS:
        row = latest.get(contract["service_id"], {})
        raw_security = row.get("security")
        if raw_security is None and row.get("security_json"):
            try:
                raw_security = json.loads(str(row["security_json"]))
            except json.JSONDecodeError:
                raw_security = None
        security = raw_security if isinstance(raw_security, Mapping) else {
            "state": "not_checked",
            "score": 0,
            "present": 0,
            "required": len(SECURITY_HEADER_NAMES),
        }
        items.append(
            {
                "service_id": contract["service_id"],
                "name": contract["name"],
                "surface": contract["endpoint"],
                "access": contract["access"],
                "transport": contract["transport"],
                "owner_agent_id": contract["owner_agent_id"],
                "status": str(row.get("status") or "not_checked"),
                "http_status": row.get("http_status"),
                "latency_ms": row.get("latency_ms"),
                "security": dict(security),
                "issue_code": row.get("issue_code"),
                "checked_at": row.get("checked_at"),
                "consecutive_failures": int(row.get("consecutive_failures") or 0),
            }
        )
    summary = summarize_service_items(items)
    if summary["healthy"] == summary["total"] and summary["total"] > 0:
        aggregate_status = "healthy"
    elif summary["not_checked"] == summary["total"]:
        aggregate_status = "not_checked"
    else:
        aggregate_status = "attention_required"
    return {
        "status": aggregate_status,
        "summary": summary,
        "policy": dict(SERVICE_OPERATIONS_POLICY),
        "items": items,
    }


def summarize_service_items(items: list[Mapping[str, Any]]) -> dict[str, int]:
    """Return deterministic service health totals."""

    return {
        "total": len(items),
        "healthy": sum(1 for item in items if item.get("status") == "healthy"),
        "degraded": sum(1 for item in items if item.get("status") == "degraded"),
        "down": sum(1 for item in items if item.get("status") == "down"),
        "not_checked": sum(1 for item in items if item.get("status") == "not_checked"),
    }


def payload_checksum(payload: Mapping[str, Any]) -> str:
    """Return a stable checksum for a customer-safe diagnostics payload."""

    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()
