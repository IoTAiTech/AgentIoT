# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Contract-gap goal optimization tests."""

import json

from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import create_app


def test_project_goal_optimization_exposes_real_remaining_gaps(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "goal-optimization.db"))

    response = client.get("/api/project/goal-optimization")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["schema_version"] == "agentiot.phase-readiness.v2"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["current_phase"] == "Phase 1"
    assert body["summary"]["token_window_count"] == 11
    assert body["summary"]["memory_policy_status"] == "ready"
    assert body["summary"]["configured_model_credentials"] == []
    assert body["summary"]["ai_model_score"] < 99.99
    assert body["summary"]["ai_model_route_ready"] is False
    assert body["summary"]["ai_model_route_decision_state"] == "customer_action_required"
    assert body["summary"]["ai_model_route_delivery_mode"] == "owner_decision_required"
    assert body["summary"]["phase_closure_task_count"] >= 7
    assert body["summary"]["phase_closure_ready_task_count"] == 3
    assert body["summary"]["phase_closure_review_ready_task_count"] >= 1
    assert body["summary"]["phase1_evidence_status_date"] == "2026-08-09"
    assert body["summary"]["phase1_contract_milestone_count"] == 7
    assert body["summary"]["phase1_due_milestone_count"] == 6
    assert body["summary"]["phase1_ready_milestone_count"] == 3
    assert body["summary"]["phase1_overdue_milestone_count"] == 3
    assert body["summary"]["phase1_in_progress_milestone_count"] == 1
    assert body["summary"]["phase_closure_owner_task_count"] >= 4
    assert [
        (
            item["phase"],
            item["technical_readiness_percent"],
            item["technical_gap_percent"],
        )
        for item in body["phase_distance"]
    ] == [("Phase 1", 38, 62), ("Phase 2", 0, 100), ("Phase 3", 0, 100)]
    assert all(item["closure_task_ids"] for item in body["phase_distance"])
    assert all("completion_percent" not in item for item in body["phase_distance"])
    assert all("remaining_percent" not in item for item in body["phase_distance"])
    closure_tasks = {item["task_id"]: item for item in body["phase_closure_tasks"]}
    assert {
        "phase1-m1-1-workshop-evidence",
        "phase1-m1-2-architecture-design",
        "phase1-m1-3-hardware-procurement-evidence",
        "phase1-m1-4-ui-ux-design",
        "phase1-m1-5-mqtt-rest-backend",
        "phase1-m1-6-physical-firmware-validation",
        "phase1-m1-7-consolidation-handover",
        "phase1-commercial-baseline-review",
        "phase2-production-hardening-controls",
        "phase2-model-route-owner-decision",
        "phase2-production-owner-signoff",
        "phase3-customer-release-package",
        "phase3-business-plan-presentation-review",
        "phase3-final-acceptance-signoff",
    }.issubset(closure_tasks)
    assert closure_tasks["phase1-m1-1-workshop-evidence"]["status"] == (
        "external_evidence_required"
    )
    assert closure_tasks["phase1-m1-1-workshop-evidence"][
        "overdue"
    ] is True
    assert closure_tasks["phase1-m1-2-architecture-design"]["status"] == "ready"
    assert closure_tasks["phase1-m1-3-hardware-procurement-evidence"][
        "overdue"
    ] is True
    assert closure_tasks["phase1-m1-4-ui-ux-design"]["status"] == "ready"
    assert closure_tasks["phase1-m1-5-mqtt-rest-backend"]["status"] == "ready"
    assert closure_tasks["phase1-m1-6-physical-firmware-validation"]["status"] == (
        "hardware_evidence_required"
    )
    assert closure_tasks["phase1-m1-7-consolidation-handover"]["status"] == (
        "in_progress"
    )
    for task in closure_tasks.values():
        assert task["phase"] in {"Phase 1", "Phase 2", "Phase 3"}
        assert task["work_type"]
        assert task["owner_agent_id"]
        assert task["acceptance_gate"]
        assert task["evidence_endpoint"]
        assert task["next_action"]
        assert isinstance(task["can_close_by_code"], bool)
        assert isinstance(task["customer_decision_required"], bool)
        assert task["must_not_fake"] is True
    phase1_task = closure_tasks["phase1-commercial-baseline-review"]
    assert phase1_task["status"] == "review_ready"
    assert phase1_task["evidence_endpoint"] == (
        "docs/customer/phase1/COMMERCIAL_BASELINE_EVIDENCE.en.md"
    )
    assert phase1_task["can_close_by_code"] is False
    assert phase1_task["customer_decision_required"] is True
    assert phase1_task["requires_secret"] is False
    hardening_task = closure_tasks["phase2-production-hardening-controls"]
    assert hardening_task["status"] == "owner_decision_required"
    assert hardening_task["can_close_by_code"] is False
    assert hardening_task["customer_decision_required"] is True
    assert hardening_task["requires_secret"] is True
    assert "do not close this by code" in hardening_task["next_action"]
    assert closure_tasks["phase2-model-route-owner-decision"]["status"] == (
        "owner_decision_required"
    )
    assert closure_tasks["phase2-model-route-owner-decision"]["requires_secret"] is True
    assert closure_tasks["phase3-customer-release-package"]["status"] in {
        "ready",
        "action_required",
    }
    goals = {item["goal_id"]: item for item in body["optimized_goals"]}
    assert set(goals) == {
        "keep-release-drift-clear",
        "close-ai-model-route-decision",
        "enforce-token-memory-governance",
        "preserve-operational-ui-quality",
        "close-production-customer-signoff",
    }
    assert goals["close-ai-model-route-decision"]["priority"] == "P0"
    assert goals["close-ai-model-route-decision"]["status"] == "review_required"
    assert goals["close-ai-model-route-decision"]["evidence_endpoint"] == (
        "/api/production/approval-package"
    )
    assert goals["enforce-token-memory-governance"]["priority"] == "P0"
    assert goals["enforce-token-memory-governance"]["status"] == "ready"
    assert goals["preserve-operational-ui-quality"]["evidence_endpoint"] == (
        "/api/ui/quality-gate"
    )
    assert goals["close-production-customer-signoff"]["evidence_endpoint"] == (
        "/api/production/hardening"
    )
    assert body["privacy"] == {
        "customer_safe": True,
        "raw_prompts_returned": False,
        "credential_values_returned": False,
        "internal_work_logs_returned": False,
        "admin_write_endpoints_returned": False,
    }
    serialized = json.dumps(body).lower()
    assert "sk-" not in serialized
    assert "/api/admin/" not in serialized
    assert '"method":"patch"' not in serialized
    blocked_instruction_phrase = "system" + " " + "prompt"
    blocked_windows_prefix = "c" + ":" + "\\\\"
    assert blocked_instruction_phrase not in serialized
    assert blocked_windows_prefix not in serialized


def test_project_goal_board_alias_matches_goal_optimization(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "goal-board.db"))

    canonical = client.get("/api/project/goal-optimization")
    alias = client.get("/api/project/goal-board")

    assert canonical.status_code == 200
    assert alias.status_code == 200
    assert alias.json() == canonical.json()


def test_project_phase_distance_board_exposes_closure_distance(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "phase-distance.db"))

    canonical = client.get("/api/project/goal-optimization")
    response = client.get("/api/project/phase-distance")

    assert canonical.status_code == 200
    assert response.status_code == 200
    body = response.json()
    goal_body = canonical.json()
    assert body["version"] == __version__
    assert body["schema_version"] == "agentiot.phase-readiness.v2"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["current_phase"] == "Phase 1"
    assert body["phase_distance"] == goal_body["phase_distance"]
    assert body["phase_closure_tasks"] == goal_body["phase_closure_tasks"]
    assert body["summary"]["open_phase_closure_task_count"] == 11
    assert "remaining_phase_distance" not in body["summary"]
    assert body["summary"]["phase1_evidence_status_date"] == "2026-08-09"
    assert body["summary"]["phase1_due_milestone_count"] == 6
    assert body["summary"]["phase1_ready_milestone_count"] == 3
    assert body["summary"]["phase1_overdue_milestone_count"] == 3
    assert body["summary"]["phase_closure_task_count"] == (
        goal_body["summary"]["phase_closure_task_count"]
    )
    assert body["summary"]["phase_closure_owner_task_count"] == (
        goal_body["summary"]["phase_closure_owner_task_count"]
    )
    serialized = json.dumps(body).lower()
    assert "/api/admin/" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_commercial_review_does_not_advance_contract_phase(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "phase-one-closure.db"))

    decision = client.patch(
        "/api/admin/production/decisions/phase-1-closure",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": (
                "Phase 1 commercial baseline and foundation deliverables "
                "approved for closure."
            ),
        },
    )
    response = client.get("/api/project/phase-distance")

    assert decision.status_code == 200
    assert response.status_code == 200
    body = response.json()
    phases = {item["phase"]: item for item in body["phase_distance"]}
    assert phases["Phase 1"]["technical_readiness_percent"] == 50
    assert phases["Phase 1"]["technical_gap_percent"] == 50
    assert phases["Phase 1"]["contractual_milestone_progress"] == "not_calculated"
    assert phases["Phase 1"]["customer_acceptance_claimed"] is False
    closure_tasks = {item["task_id"]: item for item in body["phase_closure_tasks"]}
    phase1_task = closure_tasks["phase1-commercial-baseline-review"]
    assert phase1_task["status"] == "ready"
    assert phase1_task["customer_decision_required"] is False
    assert body["current_phase"] == "Phase 1"
    assert body["summary"]["open_phase_closure_task_count"] == 10
    serialized = json.dumps(body).lower()
    assert "unit-admin-sentinel" not in serialized
    assert "api_key" not in serialized


def test_project_goal_optimization_accepts_owner_fallback_route_decision(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "goal-route-decision.db"))

    decision = client.patch(
        "/api/admin/production/decisions/ai-model-route-approval",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Fallback-only route accepted until approved model credentials are supplied.",
        },
    )
    response = client.get("/api/project/goal-optimization")

    assert decision.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["ai_model_score"] < 99.99
    assert body["summary"]["ai_model_route_ready"] is True
    assert body["summary"]["ai_model_route_decision_state"] == "approved"
    assert body["summary"]["ai_model_route_delivery_mode"] == "fallback_only_accepted"
    goals = {item["goal_id"]: item for item in body["optimized_goals"]}
    route_goal = goals["close-ai-model-route-decision"]
    assert route_goal["status"] == "ready"
    assert route_goal["evidence_endpoint"] == "/api/production/approval-package"
    assert "fallback" in route_goal["next_action"].lower()
    serialized = json.dumps(body).lower()
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_project_goal_optimization_uses_hardening_control_readiness(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "goal-hardening.db"))
    control_ids = [
        "runtime-mode",
        "trusted-hosts",
        "operator-write-gate",
        "identity-provider",
        "mqtt-broker-subscriber",
        "interactive-api-documentation",
        "reverse-proxy-tls",
        "backup-retention",
        "clean-customer-release",
        "customer-feedback-loop",
    ]

    for control_id in control_ids:
        response = client.patch(
            f"/api/admin/production/readiness-controls/{control_id}",
            headers={"X-Admin-Token": "unit-admin-sentinel"},
            json={
                "state": "ready",
                "owner": "production-owner",
                "evidence": f"{control_id} readiness evidence recorded.",
            },
        )
        assert response.status_code == 200

    hardening = client.get("/api/production/hardening").json()
    assert hardening["status"] == "ok"
    assert hardening["ready"] is True
    assert hardening["next_gate"] == "production_owner_decision"

    body = client.get("/api/project/goal-optimization").json()
    goals = {item["goal_id"]: item for item in body["optimized_goals"]}
    assert goals["close-production-customer-signoff"]["status"] == "ready"
    assert body["status"] == "review_required"
