# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

"""Contract tests for the bounded HTTP(S) service operations console."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agentiot.app import create_app
from agentiot import service_operations
from agentiot.service_operations import public_service_inventory
from conftest import (
    TEST_IDP_KEY,
    admin_token_headers,
    make_test_jwt,
    seed_bearer_assignment,
)


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}
CHECKED_AT = "2026-07-16T16:00:00Z"
SERVICE_MODULE = (
    Path(__file__).resolve().parents[1] / "src" / "agentiot" / "service_operations.py"
)


def fake_probe_with(statuses: dict[str, str]):
    """Return a deterministic fixed-contract probe for API tests."""

    def probe(contract: dict, timeout_seconds: float) -> dict:
        status = statuses.get(contract["service_id"], "healthy")
        http_status = 200 if status == "healthy" else 503
        return {
            "service_id": contract["service_id"],
            "status": status,
            "http_status": http_status,
            "latency_ms": 12,
            "security": {
                "state": "complete",
                "score": 100,
                "present": 4,
                "required": 4,
            },
            "issue_code": None if status == "healthy" else "http_5xx",
            "checked_at": CHECKED_AT,
            "timeout_seconds": timeout_seconds,
        }

    return probe


def test_full_http_services_table_is_fixed_customer_safe_and_not_ssrf_driven(
    tmp_path,
) -> None:
    app = create_app(database_path=tmp_path / "service-table.db")
    app.state.http_service_probe = fake_probe_with({})

    with TestClient(app) as client:
        response = client.get(
            "/api/services/http?url=http://169.254.169.254/latest/meta-data"
        )

    assert response.status_code == 200
    payload = response.json()
    service_ids = {item["service_id"] for item in payload["items"]}
    assert {
        "dashboard-ui",
        "health-api",
        "readiness-api",
        "operational-truth",
        "cmdb",
        "mqtt-adapter",
        "rest-adapter",
        "agent-orchestration",
        "ai-routing",
        "reports",
        "settings",
    }.issubset(service_ids)
    dashboard = next(item for item in payload["items"] if item["service_id"] == "dashboard-ui")
    assert dashboard["surface"] == "/dashboard"
    assert dashboard["access"] == "authenticated in production"
    assert payload["summary"]["total"] == len(payload["items"])
    assert payload["policy"]["discovery"] == "fixed_product_contracts_only"
    assert payload["policy"]["arbitrary_targets_accepted"] is False
    serialized = json.dumps(payload).lower()
    assert "169.254.169.254" not in serialized
    assert "probe_url" not in serialized
    assert "bind_address" not in serialized
    assert "process_id" not in serialized


def test_self_check_requires_operator_and_persists_bounded_results(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "self-check.db")
    app.state.http_service_probe = fake_probe_with({})

    with TestClient(app) as client:
        denied = client.post("/api/services/http/self-check", json={})
        accepted = client.post(
            "/api/services/http/self-check",
            headers=OPERATOR_HEADERS,
            json={},
        )
        table = client.get("/api/services/http")

    assert denied.status_code == 401
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["status"] == "completed"
    assert payload["summary"]["healthy"] == payload["summary"]["total"]
    assert payload["summary"]["down"] == 0
    assert payload["audit_event_id"] > 0
    assert all(item["checked_at"] == CHECKED_AT for item in table.json()["items"])


def test_solve_issues_creates_hitl_proposals_without_execution(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "solve-issues.db")
    app.state.http_service_probe = fake_probe_with({"readiness-api": "degraded"})

    with TestClient(app) as client:
        response = client.post(
            "/api/services/http/solve-issues",
            headers=OPERATOR_HEADERS,
            json={},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "proposals_prepared"
    assert payload["summary"]["unresolved"] == 1
    assert payload["summary"]["proposals_prepared"] == 1
    proposal = payload["proposals"][0]
    assert proposal["service_id"] == "readiness-api"
    assert proposal["requires_human_approval"] is True
    assert proposal["execution_allowed"] is False
    assert proposal["execution_state"] == "awaiting_human_approval"
    assert proposal["owner_agent_id"] == "alert_recovery_agent"
    assert proposal["tool_executed"] is False


def test_service_health_proposal_can_be_approved_and_is_idempotent(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "service-proposal-lifecycle.db")
    app.state.http_service_probe = fake_probe_with({"readiness-api": "degraded"})

    with TestClient(app) as client:
        prepared = client.post(
            "/api/services/http/solve-issues",
            headers=OPERATOR_HEADERS,
            json={},
        ).json()["proposals"][0]
        approved = client.post(
            f"/api/assistant/tool-proposals/{prepared['proposal_id']}/approve",
            headers=OPERATOR_HEADERS,
            json={},
        )
        audit_count_after_approval = len(app.state.store.list_rows("audit_events"))
        repeated = client.post(
            "/api/services/http/solve-issues",
            headers=OPERATOR_HEADERS,
            json={},
        )
        audit_events = app.state.store.list_rows("audit_events")

    assert approved.status_code == 200
    approval = approved.json()
    assert approval["status"] == "approved_recorded"
    assert approval["target"]["type"] == "service_health_review"
    assert approval["target"]["service_id"] == "readiness-api"
    assert approval["target"]["host_command_executed"] is False
    assert approval["proposal"]["execution_allowed"] is False
    assert repeated.status_code == 200
    repeated_proposal = repeated.json()["proposals"][0]
    assert repeated_proposal["proposal_id"] == prepared["proposal_id"]
    assert repeated_proposal["execution_state"] == "approved_recorded"
    assert len(audit_events) == audit_count_after_approval + 1
    assert sum(
        1
        for item in audit_events
        if item["event_type"] == "assistant.tool_proposal.prepared"
    ) == 1


def test_viewer_cannot_overwrite_a_service_health_proposal(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", TEST_IDP_KEY)
    subject = "service-viewer@example.test"
    token = make_test_jwt(
        subject=subject,
        role="viewer",
        scope="agent:read",
    )
    app = create_app(database_path=tmp_path / "viewer-overwrite.db")
    app.state.http_service_probe = fake_probe_with({"health-api": "down"})

    with TestClient(app) as client:
        prepared = client.post(
            "/api/services/http/solve-issues",
            headers=OPERATOR_HEADERS,
            json={},
        ).json()["proposals"][0]
        seed_bearer_assignment(
            client,
            monkeypatch,
            subject=subject,
            role="viewer",
            scopes=["agent:read"],
        )
        response = client.post(
            "/api/assistant/tool-proposals/prepare",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "proposal_id": prepared["proposal_id"],
                "tool_id": "/api/services/http/self-check",
                "owner_agent_id": "alert_recovery_agent",
                "requires_human_approval": True,
            },
        )
        persisted = app.state.store.get_assistant_tool_proposal(
            prepared["proposal_id"]
        )

    assert response.status_code == 403
    assert persisted["execution_state"] == "awaiting_human_approval"
    assert persisted["owner_agent_id"] == "alert_recovery_agent"


def test_auto_heal_only_rechecks_and_escalates_unresolved_work(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "auto-heal.db")
    app.state.http_service_probe = fake_probe_with({"health-api": "down"})

    with TestClient(app) as client:
        first = client.post(
            "/api/services/http/self-check",
            headers=OPERATOR_HEADERS,
            json={},
        )
        app.state.http_service_probe = fake_probe_with({})
        healed = client.post(
            "/api/services/http/auto-heal",
            headers=OPERATOR_HEADERS,
            json={},
        )

    assert first.status_code == 200
    assert healed.status_code == 200
    payload = healed.json()
    assert payload["status"] == "rechecked"
    assert payload["summary"]["recovered"] == 1
    assert payload["summary"]["unresolved"] == 0
    assert payload["summary"]["commands_executed"] == 0
    assert payload["summary"]["proposals_prepared"] == 0
    assert payload["policy"]["host_commands_allowed"] is False


def test_auto_heal_control_discloses_approval_first_boundary() -> None:
    body = (
        Path(__file__).resolve().parents[1] / "src" / "agentiot" / "root_page.html"
    ).read_text(encoding="utf-8")

    assert ">Auto Heal Review</button>" in body
    assert "Host actions remain approval-gated; no host command was executed." in body
    assert "Review the Action Queue for approval." in body


def test_auto_heal_respects_the_configured_failure_threshold(
    tmp_path,
    monkeypatch,
) -> None:
    app = create_app(database_path=tmp_path / "auto-heal-threshold.db")
    app.state.http_service_probe = fake_probe_with({"health-api": "down"})

    with TestClient(app) as client:
        client.patch(
            "/api/admin/service-operations/settings",
            headers=admin_token_headers(monkeypatch),
            json={"failure_threshold": 3},
        )
        client.post(
            "/api/services/http/self-check",
            headers=OPERATOR_HEADERS,
            json={},
        )
        below_threshold = client.post(
            "/api/services/http/auto-heal",
            headers=OPERATOR_HEADERS,
            json={},
        )
        at_threshold = client.post(
            "/api/services/http/auto-heal",
            headers=OPERATOR_HEADERS,
            json={},
        )

    assert below_threshold.status_code == 200
    assert below_threshold.json()["summary"]["proposals_prepared"] == 0
    assert at_threshold.status_code == 200
    assert at_threshold.json()["summary"]["proposals_prepared"] == 1


def test_http_status_classification_respects_the_contract_access_boundary() -> None:
    assert service_operations.status_from_http(302, "public") == (
        "degraded",
        "unexpected_redirect",
    )
    assert service_operations.status_from_http(401, "public") == (
        "degraded",
        "unexpected_auth_gate",
    )
    assert service_operations.status_from_http(403, "public status") == (
        "degraded",
        "unexpected_auth_gate",
    )
    assert service_operations.status_from_http(
        401,
        "authenticated in production",
    ) == (
        "degraded",
        "authenticated_probe_required",
    )
    assert service_operations.status_from_http(
        401,
        "authenticated in production",
        authenticated_probe=True,
    ) == (
        "degraded",
        "authenticated_probe_rejected",
    )
    assert service_operations.status_from_http(
        403,
        "public status / admin changes",
    ) == (
        "degraded",
        "unexpected_auth_gate",
    )


def test_protected_service_probe_sends_only_the_explicit_operator_header(
    monkeypatch,
) -> None:
    captured_headers: dict[str, str] = {}
    calls = 0

    class ProbeResponse:
        status = 200
        headers = {}

        def read(self, _limit):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class ProbeOpener:
        def open(self, request, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise service_operations.urllib.error.HTTPError(
                    request.full_url,
                    401,
                    "Unauthorized",
                    {},
                    None,
                )
            captured_headers.update(dict(request.header_items()))
            assert timeout == 1.5
            return ProbeResponse()

    monkeypatch.setattr(
        service_operations.urllib.request,
        "build_opener",
        lambda *_handlers: ProbeOpener(),
    )

    result = service_operations.probe_http_service(
        {
            "service_id": "protected-test",
            "endpoint": "/api/protected-test",
            "access": "authenticated in production",
        },
        auth_headers={"X-Operator-Token": "operator-probe-sentinel"},
    )

    assert captured_headers["X-operator-token"] == "operator-probe-sentinel"
    assert result["status"] == "healthy"
    assert result["issue_code"] is None


def test_browser_dashboard_probe_accepts_only_its_exact_login_redirect(
    monkeypatch,
) -> None:
    class LoginRedirectProbe:
        def open(self, request, timeout):
            assert timeout == 1.5
            raise service_operations.urllib.error.HTTPError(
                request.full_url,
                303,
                "See Other",
                {"Location": "/login?next=/dashboard"},
                None,
            )

    monkeypatch.setattr(
        service_operations.urllib.request,
        "build_opener",
        lambda *_handlers: LoginRedirectProbe(),
    )

    result = service_operations.probe_http_service(
        {
            "service_id": "dashboard-ui",
            "endpoint": "/dashboard",
            "access": "authenticated in production",
            "unauthenticated_gate": "login_redirect",
        },
        auth_headers={"X-Operator-Token": "operator-probe-sentinel"},
    )

    assert result["status"] == "healthy"
    assert result["http_status"] == 303
    assert result["issue_code"] is None


def test_protected_service_probe_rejects_a_missing_authentication_gate(
    monkeypatch,
) -> None:
    class OpenResponse:
        status = 200
        headers = {}

        def read(self, _limit):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class OpenProbe:
        def open(self, _request, timeout):
            assert timeout == 1.5
            return OpenResponse()

    monkeypatch.setattr(
        service_operations.urllib.request,
        "build_opener",
        lambda *_handlers: OpenProbe(),
    )

    result = service_operations.probe_http_service(
        {
            "service_id": "protected-test",
            "endpoint": "/api/protected-test",
            "access": "authenticated in production",
        },
        auth_headers={"X-Operator-Token": "operator-probe-sentinel"},
    )

    assert result["status"] == "degraded"
    assert result["issue_code"] == "authentication_gate_missing"


def test_service_inventory_reports_truthful_aggregate_state() -> None:
    unchecked = public_service_inventory([])
    healthy = public_service_inventory(
        [
            {
                "service_id": service_id,
                "status": "healthy",
                "security_json": "{}",
                "checked_at": CHECKED_AT,
            }
            for service_id in {
                "dashboard-ui",
                "health-api",
                "readiness-api",
                "operational-truth",
                "cmdb",
                "mqtt-adapter",
                "rest-adapter",
                "agent-orchestration",
                "ai-routing",
                "reports",
                "settings",
            }
        ]
    )
    attention = public_service_inventory(
        [
            {
                "service_id": "health-api",
                "status": "down",
                "security_json": "{}",
                "checked_at": CHECKED_AT,
            }
        ]
    )

    assert unchecked["status"] == "not_checked"
    assert healthy["status"] == "healthy"
    assert attention["status"] == "attention_required"


def test_service_operations_settings_are_admin_only_and_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    app = create_app(database_path=tmp_path / "service-settings.db")

    with TestClient(app) as client:
        denied = client.get("/api/admin/service-operations/settings")
        headers = admin_token_headers(monkeypatch)
        current = client.get(
            "/api/admin/service-operations/settings",
            headers=headers,
        )
        invalid = client.patch(
            "/api/admin/service-operations/settings",
            headers=headers,
            json={"interval_minutes": 0, "failure_threshold": 99},
        )
        updated = client.patch(
            "/api/admin/service-operations/settings",
            headers=headers,
            json={
                "auto_heal_enabled": True,
                "interval_minutes": 15,
                "failure_threshold": 3,
            },
        )

    assert denied.status_code == 401
    assert current.status_code == 200
    assert invalid.status_code == 422
    assert updated.status_code == 200
    payload = updated.json()
    assert payload["settings"]["auto_heal_enabled"] is True
    assert payload["settings"]["interval_minutes"] == 15
    assert payload["settings"]["failure_threshold"] == 3
    assert payload["audit_event_id"] > 0


def test_debug_dump_is_admin_only_downloadable_and_strictly_sanitized(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SENTINEL_PRIVATE_PASSWORD", "must-never-escape")
    app = create_app(database_path=tmp_path / "private-runtime-path.db")
    app.state.http_service_probe = fake_probe_with({})

    with TestClient(app) as client:
        client.post(
            "/api/services/http/self-check",
            headers=OPERATOR_HEADERS,
            json={},
        )
        denied = client.post("/api/system/debug-dump", json={})
        response = client.post(
            "/api/system/debug-dump",
            headers=admin_token_headers(monkeypatch),
            json={},
        )

    assert denied.status_code == 401
    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="agentiot-debug-dump-'
    )
    payload = response.json()
    assert payload["schema_version"] == "agentiot.debug-dump.v1"
    assert payload["checksum"].startswith("sha256:")
    assert payload["privacy"]["environment_included"] is False
    assert payload["privacy"]["credentials_included"] is False
    assert payload["privacy"]["raw_logs_included"] is False
    serialized = json.dumps(payload).lower()
    for forbidden in (
        "must-never-escape",
        str(tmp_path).lower(),
        "password",
        "api_key",
        "access_token",
        "local_path",
        "probe_url",
        "query_string",
        "environment_variables",
        "raw_headers",
        "fingerprint",
    ):
        assert forbidden not in serialized


def test_service_operations_source_forbids_host_command_execution() -> None:
    assert SERVICE_MODULE.exists()
    source = SERVICE_MODULE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "subprocess",
        "os.system",
        "shell=true",
        "systemctl",
        "docker ",
        "popen(",
        "nmcli",
    ):
        assert forbidden not in source
    assert "fixed_product_contracts_only" in source
    assert "arbitrary_targets_accepted" in source


def test_scheduled_self_probe_never_blocks_the_application_event_loop() -> None:
    app_source = (
        Path(__file__).resolve().parents[1] / "src" / "agentiot" / "app.py"
    ).read_text(encoding="utf-8")

    loop_start = app_source.index("async def service_operations_loop")
    loop_end = app_source.index("\n\nasync def gap_discovery_review_loop", loop_start)
    loop_source = app_source[loop_start:loop_end]

    assert "await asyncio.to_thread(" in loop_source
    assert "run_http_service_checks," in loop_source
