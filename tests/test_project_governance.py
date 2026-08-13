# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

"""Tests for customer-safe project governance helpers."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from agentiot.project_governance import (
    dashboard_document_inventory,
    parse_audit_timestamp,
    project_drift_review_window,
    project_phase_closure_tasks,
    project_phase_distance,
    project_gap_review_window,
)


def write_public_doc(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<!-- SPDX-License-Identifier: MIT -->\n"
        "# Project: AgentIoT Dashboard\n"
        "# Version: 0.152.8\n"
    )


def test_review_windows_parse_utc_and_cadence_states() -> None:
    assert parse_audit_timestamp(None) is None
    assert parse_audit_timestamp("not-a-date") is None
    assert parse_audit_timestamp("2026-06-30T01:02:03").tzinfo == UTC

    old_review = {"created_at": (datetime.now(UTC) - timedelta(hours=25)).isoformat()}
    fresh_review = {"created_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()}

    gap_window = project_gap_review_window(old_review)
    drift_window = project_drift_review_window(fresh_review)

    assert gap_window["cadence_hours"] == 6
    assert gap_window["window_state"] == "review_due"
    assert drift_window["cadence_hours"] == 6
    assert drift_window["window_state"] == "current"
    assert project_gap_review_window(None)["window_state"] == "needs_first_recorded_review"
    assert project_drift_review_window({"created_at": "bad"})["window_state"] == "review_timestamp_invalid"


def test_dashboard_document_inventory_is_customer_safe_and_detects_internal_docs(tmp_path) -> None:
    for relative in (
        "README.en.md",
        "README.de.md",
        "CHANGELOG.md",
        "NOTICE.md",
        "docs/customer/ACCEPTANCE_CHECKLIST.en.md",
        "docs/customer/DOCUMENT_INDEX.en.md",
        "docs/customer/phase2/ACCESS_ROLE_POLICY.en.md",
        "docs/contract/CONTRACT_TRACEABILITY.en.md",
        "docs/adr/ADR_0001.en.md",
    ):
        write_public_doc(tmp_path / relative)

    ready = dashboard_document_inventory(False, repo_root=tmp_path)
    assert ready["status"] == "ready"
    assert ready["customer_safe"] is True
    assert ready["file_names_returned"] is False
    assert ready["missing_spdx_public_count"] == 0
    assert ready["missing_version_public_count"] == 0
    assert ready["missing_public_document_classes"] == []
    class_statuses = {
        item["class_id"]: item for item in ready["document_class_statuses"]
    }
    assert set(ready["covered_document_classes"]) == set(class_statuses)
    assert class_statuses["readme"]["document_count"] == 2
    assert class_statuses["contract_traceability"]["document_count"] == 1
    assert class_statuses["governance"]["status"] == "ready"
    assert class_statuses["document_indexes"]["status"] == "ready"
    assert all("file" not in key for item in ready["document_class_statuses"] for key in item)

    write_public_doc(tmp_path / "internal/BUILD_PLAN.md")
    production = dashboard_document_inventory(True, repo_root=tmp_path)
    assert production["status"] == "review_required"
    assert production["internal_governance_runtime_exposed"] is True
    assert production["internal_governance_document_count"] == 1


def test_dashboard_document_inventory_reports_missing_classes_without_filenames(tmp_path) -> None:
    write_public_doc(tmp_path / "README.en.md")
    write_public_doc(tmp_path / "CHANGELOG.md")

    inventory = dashboard_document_inventory(False, repo_root=tmp_path)

    assert inventory["status"] == "review_required"
    assert "notice" in inventory["missing_public_document_classes"]
    assert "contract_traceability" in inventory["missing_public_document_classes"]
    assert inventory["customer_safe"] is True
    serialized = str(inventory)
    assert "README.en.md" not in serialized
    assert "CONTRACT_TRACEABILITY" not in serialized


def test_phase_closure_helpers_keep_owner_gaps_explicit() -> None:
    tasks = project_phase_closure_tasks(
        hardening={
            "ready": False,
            "next_gate": "configure runtime",
            "items": [
                {
                    "control_id": "identity-provider",
                    "state": "customer_action_required",
                }
            ],
        },
        route_decision={
            "ready": False,
            "delivery_mode": "owner_decision_required",
            "evidence_endpoint": "/api/production/approval-package",
            "next_action": "record owner route decision",
        },
        release={
            "summary": {"sla_gap": 0, "gates_ready": 4, "gates_total": 4},
            "production_acceptance": {"state": "action_required"},
        },
        drift={"review_result": "PASS"},
    )

    closure = {item["task_id"]: item for item in tasks}
    assert closure["phase2-production-hardening-controls"]["status"] == (
        "owner_decision_required"
    )
    assert closure["phase2-production-hardening-controls"]["requires_secret"] is True
    assert closure["phase2-production-hardening-controls"]["can_close_by_code"] is False
    assert closure["phase3-customer-release-package"]["status"] == "ready"
    assert all(item["must_not_fake"] is True for item in tasks)

    distance = project_phase_distance(tasks)

    assert [
        (
            item["phase"],
            item["technical_readiness_percent"],
            item["technical_gap_percent"],
        )
        for item in distance
    ] == [("Phase 1", 38, 62), ("Phase 2", 0, 100), ("Phase 3", 33, 67)]
    assert all(item["closure_task_ids"] for item in distance)
    assert distance[0]["metric_scope"] == "technical_closure_task_readiness"
    assert distance[0]["metric_label"] == "Foundation technical closure tasks"
    assert distance[0]["contractual_milestone_progress"] == "not_calculated"
    assert distance[0]["customer_acceptance_claimed"] is False


def test_phase_closure_helpers_accept_phase_one_owner_approval() -> None:
    tasks = project_phase_closure_tasks(
        hardening={"ready": True, "items": []},
        route_decision={
            "ready": True,
            "delivery_mode": "fallback_only_accepted",
            "evidence_endpoint": "/api/production/approval-package",
            "next_action": "maintain fallback boundary",
        },
        release={
            "summary": {"sla_gap": 0, "gates_ready": 4, "gates_total": 4},
            "production_acceptance": {"state": "action_required"},
        },
        drift={"review_result": "PASS"},
        phase1_closure_decision={
            "state": "approved",
            "decision_id": "phase-1-closure",
        },
    )

    closure = {item["task_id"]: item for item in tasks}
    phase1 = closure["phase1-commercial-baseline-review"]
    assert phase1["status"] == "ready"
    assert phase1["customer_decision_required"] is False
    assert phase1["requires_secret"] is False
    assert phase1["requires_external_evidence"] is True
    assert phase1["must_not_fake"] is True

    distance = project_phase_distance(tasks)
    assert distance[0]["phase"] == "Phase 1"
    assert distance[0]["technical_readiness_percent"] == 50
    assert distance[0]["technical_gap_percent"] == 50
    assert distance[0]["metric_scope"] == "technical_closure_task_readiness"
    assert distance[0]["metric_label"] == "Foundation technical closure tasks"
    assert distance[0]["contractual_milestone_progress"] == "not_calculated"


def test_phase_closure_helpers_reject_wrong_owner_decision_id() -> None:
    tasks = project_phase_closure_tasks(
        hardening={"ready": True, "items": []},
        route_decision={
            "ready": True,
            "delivery_mode": "fallback_only_accepted",
            "evidence_endpoint": "/api/production/approval-package",
            "next_action": "maintain fallback boundary",
        },
        release={
            "summary": {"sla_gap": 0, "gates_ready": 4, "gates_total": 4},
            "production_acceptance": {"state": "action_required"},
        },
        drift={"review_result": "PASS"},
        phase1_closure_decision={
            "state": "approved",
            "decision_id": "hosting-owner",
        },
    )

    closure = {item["task_id"]: item for item in tasks}
    phase1 = closure["phase1-commercial-baseline-review"]
    assert phase1["status"] == "review_ready"
    assert phase1["customer_decision_required"] is True

    distance = project_phase_distance(tasks)
    assert distance[0]["phase"] == "Phase 1"
    assert distance[0]["technical_readiness_percent"] == 38
    assert distance[0]["technical_gap_percent"] == 62
