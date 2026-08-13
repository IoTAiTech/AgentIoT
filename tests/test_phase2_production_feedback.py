# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-10

import json

from fastapi.testclient import TestClient

import agentiot.app as app_module
from agentiot.app import create_app
from tests.conftest import admin_token_headers


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_production_hardening_status_is_customer_safe(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardening.db"))

    response = client.get("/api/production/hardening")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ready"] is False
    assert body["readiness_score"] >= 60
    assert body["next_gate"] == "customer_feedback_and_production_owner_approval"
    controls = {item["control"]: item for item in body["items"]}
    assert controls["Operator write gate"]["state"] == "ready"
    assert controls["Interactive API documentation"]["state"] == "development_visible"
    tls = controls["Browser-trusted reverse-proxy TLS"]
    assert tls["state"] == "customer_action_required"
    assert tls["browser_trusted"] is False
    assert controls["Backup and retention"]["state"] == "customer_action_required"
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_backup_retention_status_redacts_policy_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    monkeypatch.setenv("AGENTIOT_BACKUP_RETENTION_DAYS", "90")
    monkeypatch.setenv("AGENTIOT_BACKUP_CADENCE_HOURS", "12")
    monkeypatch.setenv("AGENTIOT_BACKUP_LAST_RESTORE_TEST_AT", "2026-06-25T12:00:00Z")
    client = TestClient(create_app(database_path=tmp_path / "backup-policy.db"))

    response = client.get("/api/production/backup-retention")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "restore_review_required"
    assert body["policy_configured"] is True
    assert body["retention_days"] == 90
    assert body["cadence_hours"] == 12
    assert body["restore_test_state"] == "manual_timestamp_only"
    assert body["policy_fingerprint"]
    assert body["customer_safe"] is True
    assert "daily encrypted retention" not in response.text


def test_backup_retention_requires_restore_evidence_before_ready(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    client = TestClient(create_app(database_path=tmp_path / "backup-needs-restore.db"))

    response = client.get("/api/production/backup-retention")

    assert response.status_code == 200
    body = response.json()
    assert body["policy_configured"] is True
    assert body["restore_test_state"] == "not_recorded"
    assert body["status"] == "restore_review_required"
    assert body["next_gate"] == "restore_test_review"
    assert "daily encrypted retention" not in response.text

    preflight = client.get("/api/production/preflight").json()
    checks = {item["check_id"]: item for item in preflight["checks"]}
    assert checks["backup-retention"]["state"] == "restore_review_required"
    assert checks["backup-restore-test"]["state"] == "review_required"

def test_backup_retention_becomes_ready_after_stored_restore_evidence(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    client = TestClient(create_app(database_path=tmp_path / "backup-ready-with-restore.db"))
    seed_response = client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "backup-ready-asset", "name": "Backup Ready Asset"},
    )
    assert seed_response.status_code == 201

    restore = client.post(
        "/api/admin/production/restore-test",
        headers=admin_token_headers(monkeypatch),
        json={},
    )

    assert restore.status_code == 200
    backup = client.get("/api/production/backup-retention").json()
    assert backup["status"] == "ready"
    assert backup["restore_test_state"] == "recorded"
    assert backup["restore_evidence_fingerprint"]
    assert backup["restore_verified_tables"] > 0


def test_backup_retention_rejects_stale_restore_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    monkeypatch.setenv("AGENTIOT_BACKUP_CADENCE_HOURS", "24")
    client = TestClient(create_app(database_path=tmp_path / "backup-stale.db"))
    store = client.app.state.store
    event = store.add_audit_event(
        event_type="production.restore_test.completed",
        subject_id="backup-retention",
        actor="admin",
        detail=json.dumps(
            {
                "verified_tables": len(app_module.RESTORE_VERIFICATION_TABLES),
                "checked_records": 0,
                "evidence_fingerprint": "content-proof",
                "table_profile_fingerprint": app_module.restore_table_profile_fingerprint(),
            }
        ),
    )
    with store.connect() as connection:
        connection.execute(
            "UPDATE audit_events SET created_at = ? WHERE audit_event_id = ?",
            ("2020-01-01T00:00:00+00:00", event["audit_event_id"]),
        )

    backup = client.get("/api/production/backup-retention").json()

    assert backup["status"] == "restore_review_required"
    assert backup["restore_test_state"] == "stale"
    assert backup["restore_profile_current"] is True


def test_backup_retention_rejects_obsolete_restore_profile(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    client = TestClient(create_app(database_path=tmp_path / "backup-profile.db"))
    client.app.state.store.add_audit_event(
        event_type="production.restore_test.completed",
        subject_id="backup-retention",
        actor="admin",
        detail=json.dumps(
            {
                "verified_tables": 1,
                "checked_records": 0,
                "evidence_fingerprint": "content-proof",
                "table_profile_fingerprint": "obsolete-profile",
            }
        ),
    )

    backup = client.get("/api/production/backup-retention").json()

    assert backup["status"] == "restore_review_required"
    assert backup["restore_test_state"] == "profile_mismatch"
    assert backup["restore_profile_current"] is False

def test_restore_verification_requires_admin_token(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "restore-gate.db"))

    response = client.post("/api/admin/production/restore-test", json={})
    operator_response = client.post(
        "/api/admin/production/restore-test",
        headers=OPERATOR_HEADERS,
        json={},
    )

    assert response.status_code == 401
    assert operator_response.status_code == 401
    assert "restore-check" not in response.text
    assert "restore-check" not in operator_response.text
    assert "/home/" not in response.text
    assert "C:" not in response.text


def test_restore_verification_records_customer_safe_evidence(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    client = TestClient(create_app(database_path=tmp_path / "restore-proof.db"))
    seed_response = client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "restore-proof-asset", "name": "Restore Proof Asset"},
    )
    assert seed_response.status_code == 201

    response = client.post(
        "/api/admin/production/restore-test",
        headers=admin_token_headers(monkeypatch),
        json={},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "recorded"
    assert body["restore_test_state"] == "recorded"
    assert body["restore_audit_event_id"] >= 1
    assert body["restore_verified_tables"] >= 8
    assert body["restore_checked_records"] >= 1
    assert body["restore_evidence_fingerprint"]
    assert body["customer_safe"] is True
    assert "/home/" not in response.text
    assert "restore-check" not in response.text
    assert "daily encrypted retention" not in response.text

    backup = client.get("/api/production/backup-retention").json()
    assert backup["restore_test_state"] == "recorded"
    assert backup["restore_audit_event_id"] == body["restore_audit_event_id"]
    assert backup["restore_checked_records"] == body["restore_checked_records"]
    assert backup["restore_test_at"]
    assert "daily encrypted retention" not in client.get(
        "/api/production/backup-retention"
    ).text

    preflight = client.get("/api/production/preflight").json()
    checks = {item["check_id"]: item for item in preflight["checks"]}
    assert checks["backup-restore-test"]["state"] == "ready"
    assert (
        checks["backup-restore-test"]["runtime_signals"]["restore_audit_event_id"]
        == body["restore_audit_event_id"]
    )
    assert "/home/" not in client.get("/api/production/preflight").text


def test_restore_integrity_fingerprint_changes_when_restored_content_changes(
    tmp_path, monkeypatch
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "restore-integrity.db"))
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "stable-asset", "name": "Stable Asset"},
    )
    headers = admin_token_headers(monkeypatch)

    first = client.post("/api/admin/production/restore-test", headers=headers, json={})
    update = client.patch(
        "/api/assets/stable-asset",
        headers=OPERATOR_HEADERS,
        json={"name": "Stable Asset Updated"},
    )
    second = client.post("/api/admin/production/restore-test", headers=headers, json={})

    assert first.status_code == 200
    assert update.status_code == 200
    assert second.status_code == 200
    assert first.json()["restore_verified_tables"] == second.json()["restore_verified_tables"]
    assert first.json()["restore_checked_records"] <= second.json()["restore_checked_records"]
    assert first.json()["restore_evidence_fingerprint"] != second.json()[
        "restore_evidence_fingerprint"
    ]
    assert "/home/" not in first.text + second.text
    assert "restore-check" not in first.text + second.text


def test_restore_verification_covers_phase2_runtime_tables() -> None:
    required_phase2_tables = {
        "hardware_discovery_candidates",
        "agent_controls",
        "agent_runs",
        "access_role_policies",
        "access_user_assignments",
        "ai_provider_policies",
        "ai_model_credentials",
        "ai_token_usage_events",
        "ai_memory_policy",
        "ai_analysis_profiles",
        "ai_eval_runs",
        "qa_challenge_runs",
        "rag_knowledge_documents",
        "evidence_findings",
        "assistant_interactions",
        "assistant_tool_proposals",
        "assistant_feedback",
    }

    assert required_phase2_tables.issubset(app_module.RESTORE_VERIFICATION_TABLES)


def test_restore_verification_failure_is_sanitized(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        app_module,
        "RESTORE_VERIFICATION_TABLES",
        app_module.RESTORE_VERIFICATION_TABLES + ("missing_restore_table",),
    )
    client = TestClient(create_app(database_path=tmp_path / "restore-failed.db"))

    response = client.post(
        "/api/admin/production/restore-test",
        headers=admin_token_headers(monkeypatch),
        json={},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Restore verification failed"
    assert "/home/" not in response.text
    assert "missing_restore_table" not in response.text
    assert "restore-check" not in response.text

    backup = client.get("/api/production/backup-retention").json()
    assert backup["restore_test_state"] == "failed"
    assert backup["restore_checked_records"] == 0
    assert backup["next_gate"] == "backup_policy_configuration"
    audit_text = client.get("/api/audit/events").text
    assert "production.restore_test.failed" in audit_text
    assert "missing_restore_table" not in audit_text
    assert "restore-check" not in audit_text


def test_production_hardening_reflects_production_configuration(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver,demo.greenovax.example")
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "daily encrypted retention")
    client = TestClient(create_app(database_path=tmp_path / "hardening-prod.db"))

    response = client.get("/api/production/hardening")

    assert response.status_code == 200
    assert response.json()["ready"] is False
    controls = {item["control"]: item for item in response.json()["items"]}
    assert controls["Runtime mode"]["state"] == "ready"
    assert controls["Trusted hosts"]["state"] == "ready"
    assert controls["Interactive API documentation"]["state"] == "ready"
    assert controls["Identity provider"]["state"] == "ready"
    assert controls["Backup and retention"]["state"] == "restore_review_required"
    approval = client.get("/api/production/approval-package").json()
    decisions = {item["decision_id"]: item for item in approval["decision_items"]}
    assert decisions["backup-retention"]["state"] == "restore_review_required"


def test_production_mode_rejects_wildcard_trusted_hosts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "*")

    try:
        create_app(database_path=tmp_path / "wildcard-host.db")
    except RuntimeError as exc:
        assert "Wildcard trusted host" in str(exc)
    else:
        raise AssertionError("production mode accepted wildcard trusted hosts")


def test_customer_feedback_requires_operator_gate(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "feedback-gate.db"))

    response = client.post(
        "/api/customer/feedback",
        json={
            "reviewer_role": "customer-reviewer",
            "area": "demo",
            "rating": 4,
            "comment": "Demo flow is understandable.",
        },
    )

    assert response.status_code == 401


def test_customer_feedback_is_recorded_without_contact_data(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "feedback.db"))

    response = client.post(
        "/api/customer/feedback",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_role": "customer-reviewer",
            "area": "production-readiness",
            "rating": 5,
            "comment": "Ready for reverse-proxy planning.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "recorded"
    assert body["feedback_id"].startswith("feedback-")
    assert body["stored_contact_data"] is False
    assert "@" not in response.text
    feedback = client.get("/api/customer/feedback").json()["items"]
    assert feedback[0]["area"] == "production-readiness"
    assert feedback[0]["rating"] == 5
    audit = client.get("/api/audit/events").json()["items"]
    assert audit[-1]["event_type"] == "customer.feedback.received"


def test_customer_feedback_rejects_phone_like_contact_data(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "feedback-contact.db"))

    response = client.post(
        "/api/customer/feedback",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_role": "customer-reviewer",
            "area": "production-readiness",
            "rating": 3,
            "comment": "Please call me at 030 1234567 tomorrow.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Contact data is not accepted"
    feedback = client.get("/api/customer/feedback").json()["items"]
    assert feedback == []
