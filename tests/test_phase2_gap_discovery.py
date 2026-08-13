# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Six-hour project gap-discovery API tests."""

import json

from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import create_app

OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_project_gap_discovery_exposes_customer_safe_6_hour_gap_board(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    client = TestClient(create_app(database_path=tmp_path / "gap-discovery.db"))

    response = client.get("/api/project/gap-discovery")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["cadence_hours"] == 6
    assert body["current_phase"] == "Phase 1"
    assert body["customer_acceptance_claimed"] is False
    assert body["summary"]["open_gap_count"] == len(body["gaps"])
    assert body["summary"]["engineering_closeable_count"] == body["gap_summary"]["engineering_closeable_count"]
    assert body["summary"]["customer_decision_gap_count"] == body["gap_summary"]["customer_decision_gap_count"]
    assert body["summary"]["review_result"] == body["review_result"]
    assert body["summary"]["next_action"] == body["next_action"]
    assert body["summary"]["release_kpi_score"] == body["kpi_sla"]["release_kpi_score"]
    assert body["summary"]["release_sla_gap"] == body["kpi_sla"]["release_sla_gap"]
    assert body["summary"]["open_phase_closure_task_count"] == body["kpi_sla"]["open_phase_closure_task_count"]
    assert body["summary"]["customer_safe"] is True
    assert body["gap_summary"]["open_gap_count"] == len(body["gaps"])
    assert body["gap_summary"]["p0_count"] >= 1
    assert body["kpi_sla"]["daily_review_sla_hours"] == 6
    assert body["kpi_sla"]["open_gap_count"] == len(body["gaps"])
    assert body["kpi_sla"]["scanned_document_count"] > 0
    assert body["kpi_sla"]["public_document_count"] > 0
    assert body["kpi_sla"]["missing_spdx_public_count"] == 0
    assert body["kpi_sla"]["missing_version_public_count"] == 0
    assert body["kpi_sla"]["document_inventory_status"] == "ready"
    assert body["kpi_sla"]["rag_grounding_gap_count"] == 0
    assert body["kpi_sla"]["rag_maintenance_item_count"] >= 1
    assert body["review_window"]["cadence_hours"] == 6
    assert any(
        source["reference"] == "/api/project/drift-control"
        for source in body["checked_sources"]
    )
    assert any(
        source["source"] == "Dashboard document inventory"
        for source in body["checked_sources"]
    )
    assert body["document_inventory"]["status"] == "ready"
    assert body["document_inventory"]["customer_safe"] is True
    assert body["document_inventory"]["file_names_returned"] is False
    assert body["document_inventory"]["missing_spdx_public_count"] == 0
    assert body["document_inventory"]["missing_version_public_count"] == 0
    assert body["document_inventory"]["missing_public_document_classes"] == []
    document_class_ids = {
        item["class_id"] for item in body["document_inventory"]["document_class_statuses"]
    }
    assert set(body["document_inventory"]["covered_document_classes"]) == document_class_ids
    assert {
        "readme",
        "contract_traceability",
        "customer_delivery",
        "architecture_decisions",
        "governance",
        "document_indexes",
    } <= document_class_ids
    assert all(
        item["status"] == "ready"
        for item in body["document_inventory"]["document_class_statuses"]
    )
    assert not any(
        gap["gap_id"] == "dashboard-document-inventory-open"
        for gap in body["gaps"]
    )
    assert any(
        link["endpoint"] == "/api/project/gap-discovery/run"
        for link in body["evidence_links"]
    )
    assert any(
        gap["gap_id"] == "ai-model-route-decision-open"
        for gap in body["gaps"]
    )
    assert any(
        gap["gap_id"] == "production-action-plan-open"
        for gap in body["gaps"]
    )
    phase_gap = next(
        gap for gap in body["gaps"] if gap["gap_id"] == "phase-acceptance-distance-open"
    )
    assert phase_gap["closure_task_count"] >= 7
    assert phase_gap["ready_closure_task_count"] == 3
    assert phase_gap["review_ready_closure_task_count"] >= 1
    assert "phase2-model-route-owner-decision" in phase_gap["closure_task_ids"]
    assert phase_gap["can_close_by_code"] is False
    assert phase_gap["customer_decision_required"] is True
    assert phase_gap["requires_secret"] is True
    assert phase_gap["next_closure_task"]["must_not_fake"] is True
    assert phase_gap["next_closure_task"]["task_id"] == (
        "phase1-m1-1-workshop-evidence"
    )
    assert phase_gap["next_closure_task"]["can_close_by_code"] is False
    assert phase_gap["next_closure_task"]["customer_decision_required"] is True
    assert phase_gap["next_closure_task"]["status"] == "external_evidence_required"
    assert not any(
        gap["gap_id"] == "rag-grounding-gap-open"
        for gap in body["gaps"]
    )
    for gap in body["gaps"]:
        assert gap["closeability"]
        assert isinstance(gap["can_close_by_code"], bool)
        assert isinstance(gap["customer_decision_required"], bool)
        assert isinstance(gap["requires_secret"], bool)
        assert isinstance(gap["requires_external_evidence"], bool)
        assert gap["must_not_fake"] is True
    ai_route_gap = next(
        gap for gap in body["gaps"] if gap["gap_id"] == "ai-model-route-decision-open"
    )
    assert ai_route_gap["can_close_by_code"] is False
    assert ai_route_gap["customer_decision_required"] is True
    assert ai_route_gap["requires_secret"] is True
    provider_quality_gap = next(
        gap
        for gap in body["gaps"]
        if gap["gap_id"] == "assistant-provider-quality-evidence-open"
    )
    assert provider_quality_gap["can_close_by_code"] is False
    assert provider_quality_gap["customer_decision_required"] is True
    assert provider_quality_gap["requires_secret"] is True
    assert provider_quality_gap["requires_external_evidence"] is True
    assert body["gap_summary"]["engineering_closeable_count"] >= 0
    assert body["gap_summary"]["customer_decision_gap_count"] >= 1
    assert body["gap_summary"]["secret_required_gap_count"] >= 1
    assert body["gap_summary"]["external_evidence_gap_count"] >= 1
    assert body["kpi_sla"]["mcp_tool_count"] >= 6
    assert not any(
        gap["gap_id"] == "mcp-tool-coverage-narrow"
        for gap in body["gaps"]
    )
    assert {agent["agent_id"] for agent in body["required_agents"]} >= {
        "product_delivery_manager",
        "software_release_controller",
        "quality_test_controller",
        "ui_experience_controller",
    }
    assert body["privacy"] == {
        "customer_safe": True,
        "raw_prompts_returned": False,
        "credential_values_returned": False,
        "internal_work_logs_returned": False,
        "local_paths_returned": False,
        "admin_write_endpoints_returned": False,
    }
    serialized = json.dumps(body).lower()
    assert "/api/admin/" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized
    assert "private " + "prompt" not in serialized
    assert "system " + "prompt" not in serialized
    assert "c" + ":\\" not in serialized
    blocked_server_path = "/" + "home" + "/" + "iot"
    assert blocked_server_path not in serialized
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_gap_discovery_does_not_create_engineering_loop_for_owner_only_actions(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_TLS_TERMINATION", "reverse-proxy")
    monkeypatch.setenv(
        "AGENTIOT_OPERATOR_TOKEN",
        "9f4b8e12c7a34d90aa61f3d2b5c0e7789a2c4e6f8d1b3a5c7e9f0a12b4c6d8e0",
    )
    monkeypatch.setenv(
        "AGENTIOT_ADMIN_TOKEN",
        "6d8e0b4c2a10f9e7c5a3b1d8f6e4c2a9877e0c5b2d3f16aa09d43a7c21e8b4f9",
    )
    client = TestClient(create_app(database_path=tmp_path / "gap-owner-only.db"))

    action_plan = client.get("/api/production/action-plan").json()
    assert action_plan["summary"]["engineering_closeable_action_count"] == 0
    assert action_plan["status"] == "action_required"
    assert "do not close these by code" in action_plan["next_action"]

    response = client.get("/api/project/gap-discovery")

    assert response.status_code == 200
    body = response.json()
    gap_ids = {gap["gap_id"] for gap in body["gaps"]}
    assert body["summary"]["production_engineering_closeable_action_count"] == 0
    assert body["summary"]["customer_decision_gap_count"] >= 1
    assert "production-action-plan-open" not in gap_ids
    assert "customer-owner-decisions-open" in gap_ids
    assert all(
        gap["gap_id"] != "production-action-plan-open"
        or gap["can_close_by_code"] is False
        for gap in body["gaps"]
    )


def test_project_gap_discovery_run_records_audit_and_finding(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "gap1234")
    client = TestClient(create_app(database_path=tmp_path / "gap-run.db"))

    response = client.post(
        "/api/project/gap-discovery/run",
        headers=OPERATOR_HEADERS,
        json={"force": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["source_commit"] == "gap1234"
    assert body["recording"]["status"] == "recorded"
    assert body["recording"]["audit_event_id"] > 0
    assert body["recording"]["finding_id"].startswith("finding-")
    assert body["recording"]["subject_id"].startswith("gap-discovery-")
    assert body["last_recorded_review"]["review_result"] == body["review_result"]
    assert body["last_recorded_review"]["open_gap_count"] == len(body["gaps"])
    assert body["review_window"]["window_state"] == "current"

    audit_events = client.get("/api/audit/events").json()["items"]
    assert any(
        item["event_type"] == "project.gap_discovery.reviewed"
        for item in audit_events
    )
    findings = client.get("/api/evidence/findings", headers=OPERATOR_HEADERS).json()["items"]
    assert any(item["source"] == "project_gap_discovery" for item in findings)
    serialized = response.text.lower()
    assert "/api/admin/" not in serialized
    assert "system " + "prompt" not in serialized
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_project_gap_discovery_run_skips_current_window(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "gap5678")
    client = TestClient(create_app(database_path=tmp_path / "gap-skip.db"))

    first = client.post(
        "/api/project/gap-discovery/run",
        headers=OPERATOR_HEADERS,
        json={"force": True},
    )
    second = client.post(
        "/api/project/gap-discovery/run",
        headers=OPERATOR_HEADERS,
        json={"force": False},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["recording"]["status"] == "recorded"
    assert second.json()["recording"]["status"] == "skipped_current_window"
    assert second.json()["review_window"]["window_state"] == "current"


def test_project_gap_discovery_run_requires_operator_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "gap-auth.db"))

    response = client.post(
        "/api/project/gap-discovery/run",
        json={"force": True},
    )

    assert response.status_code in {401, 503}
