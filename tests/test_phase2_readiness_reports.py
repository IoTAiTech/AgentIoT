# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import create_app
from conftest import admin_token_headers


def test_settings_endpoint_reports_customer_safe_readiness(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app(database_path=tmp_path / "settings.db"))

    response = client.get("/api/settings")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["items"]) >= 5
    controls = {item["control"]: item for item in body["items"]}
    assert controls["Runtime mode"]["state"] == "production"
    assert controls["Operator write gate"]["state"] == "enabled"
    assert controls["API documentation"]["state"] == "hidden in production"
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_reports_endpoint_returns_phase_delivery_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "reports.db"))

    response = client.get("/api/reports")

    assert response.status_code == 200
    body = response.json()
    report_ids = {item["report_id"] for item in body["items"]}
    assert "phase-2-operational-console" in report_ids
    assert "secure-access-baseline" in report_ids
    assert "next-gate-identity-provider" in report_ids


def test_dashboard_report_package_returns_visual_chart_metadata(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "visual-reports.db"))

    response = client.get("/api/reports/dashboard", headers=admin_token_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    chart_ids = {item["chart_id"] for item in body["charts"]}
    assert {
        "operations-readiness",
        "runtime-records",
        "agent-coverage",
        "assistant-quality",
        "release-remediation-actions",
        "evidence-action-priority",
        "evidence-action-status",
    }.issubset(chart_ids)
    for chart in body["charts"]:
        assert chart["type"] == "bar"
        assert chart["unit"] in {
            "score",
            "records",
            "agents",
            "runs",
            "findings",
            "profiles",
            "cases",
            "actions",
            "tokens",
            "MB",
        }
        assert chart["series"]
        assert all("label" in item and "value" in item for item in chart["series"])
    report_ids = {item["report_id"] for item in body["reports"]}
    assert "release-remediation-plan" in report_ids
    assert body["release_mission"]["remediation_plan"]["target_success_rate"] == 99.99
    assert len(body["reports"]) >= 6
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_project_phase_board_reports_operational_next_steps(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "phases.db"))

    response = client.get("/api/project/phases")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["current_phase"] == "Phase 1"
    assert body["prepared_for"] == "GreeNovaX"
    assert len(body["items"]) == 3
    phase_1 = body["items"][0]
    phase_2 = body["items"][1]
    assert phase_1["phase"] == "Phase 1"
    assert phase_1["state"] == "active_foundation"
    assert "operational cockpit" in phase_1["next_action"]
    assert "physical checks" in phase_1["runtime_next_action"]
    assert phase_1["runtime_snapshot"]["devices"] == 1
    assert phase_1["runtime_snapshot"]["open_alerts"] == 1
    assert phase_2["phase"] == "Phase 2"
    assert phase_2["state"] == "planned_after_phase1_gate"
    assert "gated" in phase_2["next_action"]


def test_commercial_owner_review_does_not_advance_project_phase(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "phases-approved.db"))

    decision = client.patch(
        "/api/admin/production/decisions/phase-1-closure",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Phase 1 foundation approved for closure.",
        },
    )
    phases_response = client.get("/api/project/phases")
    distance_response = client.get("/api/project/phase-distance")
    fanout_response = client.get("/api/qc/fan-out")

    assert decision.status_code == 200
    assert phases_response.status_code == 200
    assert distance_response.status_code == 200
    assert fanout_response.status_code == 200
    phases_body = phases_response.json()
    distance_body = distance_response.json()
    fanout_body = fanout_response.json()
    assert phases_body["current_phase"] == "Phase 1"
    assert distance_body["current_phase"] == "Phase 1"
    assert fanout_body["current_phase"] == "Phase 1"
    phase_1 = phases_body["items"][0]
    phase_2 = phases_body["items"][1]
    assert phase_1["state"] == "active_foundation"
    assert phase_1["technical_owner_decision_recorded"] is True
    assert phase_1["contractual_milestone_progress"] == "not_calculated"
    assert phase_1["customer_acceptance_claimed"] is False
    assert phase_2["state"] == "planned_after_phase1_gate"
    assert phase_2["contractual_milestone_progress"] == "not_calculated"
    assert phase_2["customer_acceptance_claimed"] is False
    assert fanout_body["summary"]["phase_2_technical_readiness_percent"] == 0
