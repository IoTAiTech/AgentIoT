# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.17 | Date: 2026-07-14

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from agentiot.app import create_app


def test_runtime_observability_api_returns_customer_safe_live_shape(tmp_path) -> None:
    """The public endpoint returns a stable, read-only platform snapshot."""

    with TestClient(create_app(database_path=tmp_path / "observability.db")) as client:
        response = client.get("/api/system/observability")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "observed_at",
        "freshness",
        "process",
        "load",
        "memory",
        "disk",
        "network",
        "components",
        "issues",
        "next_action",
    }
    assert payload["freshness"] == {"state": "fresh", "age_seconds": 0}
    assert set(payload["components"]) == {"api", "database", "mqtt", "rest"}
    assert payload["components"]["api"]["state"] == "available"
    assert isinstance(payload["issues"], list)
    assert isinstance(payload["next_action"], str)
    assert "cpu_percent" not in payload["load"]


def test_runtime_observability_fallbacks_are_deterministic_and_non_disclosing() -> None:
    """Missing host telemetry reports safe unavailable states rather than errors."""

    from agentiot.runtime_observability import collect_runtime_observability

    def unavailable(*_args, **_kwargs):
        raise OSError("host details must not escape")

    payload = collect_runtime_observability(
        data_volume_path="/unavailable",
        observed_at="2026-07-14T12:00:00Z",
        components={
            "api": {"state": "available"},
            "database": {"state": "available"},
            "mqtt": {"state": "not_configured"},
            "rest": {"state": "idle_no_rest_devices"},
        },
        read_text=lambda _path: None,
        getloadavg=unavailable,
        cpu_count=lambda: None,
        disk_usage=unavailable,
    )

    assert payload["observed_at"] == "2026-07-14T12:00:00Z"
    assert payload["process"] == {"state": "unavailable"}
    assert payload["load"] == {"state": "unavailable", "cpu_count": None}
    assert payload["memory"] == {"state": "unavailable"}
    assert payload["disk"] == {"state": "unavailable"}
    assert payload["network"] == {"state": "unavailable"}
    assert payload["issues"]
    assert "host details" not in json.dumps(payload).lower()


def test_runtime_observability_excludes_sensitive_host_details_and_is_documented(tmp_path) -> None:
    """The contract cannot leak host identity, interfaces, paths, or raw failures."""

    with TestClient(create_app(database_path=tmp_path / "observability-safety.db")) as client:
        response = client.get("/api/system/observability")
        schema = client.get("/openapi.json").json()

    assert response.status_code == 200
    serialized = json.dumps(response.json()).lower()
    forbidden = (
        "hostname",
        "ip_address",
        "mac_address",
        "interface_name",
        "process_list",
        "local_path",
        "raw_error",
        "secret",
    )
    assert not any(value in serialized for value in forbidden)
    assert "/api/system/observability" in schema["paths"]
    assert "get" in schema["paths"]["/api/system/observability"]
