# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

import json

from fastapi.testclient import TestClient

from agentiot.app import OWNER_DECISION_STATES, create_app
from conftest import (
    admin_token_headers,
    configure_offhost_restore_receipt,
    make_test_jwt,
    seed_bearer_assignment,
)


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def configured_idp(monkeypatch) -> None:
    """Configure deterministic bearer validation for admin decision tests."""

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")


def test_owner_approval_package_lists_customer_decisions(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "owner-approval.db"))

    response = client.get("/api/production/approval-package")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "owner_review_required"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["next_gate"] == "production_owner_signoff"
    assert body["summary"]["decision_count"] == len(body["decision_items"])
    assert body["summary"]["open_decision_count"] >= 1
    assert body["summary"]["customer_decision_required"] is True
    assert body["summary"]["hardening_readiness_score"] >= 0
    assert body["summary"]["next_owner_action"]
    decision_ids = {item["decision_id"] for item in body["decision_items"]}
    assert "hosting-owner" in decision_ids
    assert "reverse-proxy-tls" in decision_ids
    assert "backup-retention" in decision_ids
    assert "customer-feedback" in decision_ids
    assert "mqtt-broker-subscriber" in decision_ids
    assert "ai-model-route-approval" in decision_ids
    assert "phase-1-closure" in decision_ids
    links = {item["endpoint"] for item in body["evidence_links"]}
    assert "/api/production/hardening" in links
    assert "/api/customer/feedback/summary" in links
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_production_action_plan_turns_open_gates_into_customer_safe_tasks(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "production-action-plan.db"))

    response = client.get("/api/production/action-plan")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["open_control_count"] >= 1
    assert body["summary"]["open_decision_count"] >= 1
    assert body["summary"]["customer_decision_required"] is True
    assert body["summary"]["blocking_categories"]["customer_decision"] >= 1
    assert body["summary"]["blocking_categories"]["customer_runtime_config"] >= 1
    assert body["summary"]["secret_free_close_count"] >= 1
    assert body["summary"]["engineering_closeable_action_count"] >= 1
    actions = {item["action_id"]: item for item in body["actions"]}
    display_actions = body["display_actions"]
    assert display_actions
    assert len(display_actions) < len(body["actions"])
    assert any(item["occurrence_count"] > 1 for item in display_actions)
    rendered_display = json.dumps(display_actions)
    assert "grouped customer runtime config actions" not in rendered_display
    assert "grouped customer decision actions" not in rendered_display
    assert any(
        item["label"] == "Identity provider and MQTT broker setup"
        for item in display_actions
    )
    assert any(
        item["label"] == "Production go-live decisions"
        for item in display_actions
    )
    for item in display_actions:
        assert item["customer_safe"] is True
        assert item["source_action_ids"]
        assert item["occurrence_count"] == len(item["source_action_ids"])
        assert item["blocking_category"] in body["summary"]["blocking_categories"]
        assert "/api/admin" not in json.dumps(item)
        assert '"method"' not in json.dumps(item)
    customer_runtime_packets = [
        item for item in display_actions
        if item["blocking_category"] == "customer_runtime_config"
    ]
    assert any(
        item["customer_secret_required_count"] >= 1
        for item in customer_runtime_packets
    )
    assert "control-runtime-mode" in actions
    assert "decision-ai-model-route-approval" in actions
    assert actions["control-runtime-mode"]["blocking_category"] == "development_visible"
    assert actions["control-runtime-mode"]["can_close_without_customer_secret"] is True
    assert actions["control-runtime-mode"]["evidence_endpoint"] == (
        "/api/production/hardening"
    )
    assert "run_endpoint" not in actions["control-runtime-mode"]
    assert "method" not in actions["control-runtime-mode"]
    assert actions["decision-ai-model-route-approval"]["customer_decision_required"] is True
    assert (
        actions["decision-ai-model-route-approval"]["blocking_category"]
        == "customer_decision"
    )
    assert (
        actions["decision-ai-model-route-approval"][
            "can_close_without_customer_secret"
        ]
        is False
    )
    assert "formal customer acceptance" in actions[
        "decision-ai-model-route-approval"
    ]["approval_boundary"]
    assert actions["decision-ai-model-route-approval"]["evidence_endpoint"] == (
        "/api/production/approval-package"
    )
    assert "run_endpoint" not in actions["decision-ai-model-route-approval"]
    assert "method" not in actions["decision-ai-model-route-approval"]
    assert body["evidence_links"][0]["endpoint"] == "/api/production/hardening"
    assert "/api/admin/production" not in response.text
    assert '"method":"PATCH"' not in response.text
    assert "unit-" + "operator-" + "sentinel" not in response.text
    forbidden_home = "/" + "home" + "/" + "iot"
    forbidden_host = ".".join(["192", "168", "50", "40"])
    assert forbidden_home not in response.text
    assert forbidden_host not in response.text



def test_owner_decision_brief_turns_actions_into_manager_questions(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "owner-brief.db"))

    response = client.get("/api/production/owner-decision-brief")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["question_count"] == len(body["questions"])
    assert body["summary"]["question_count"] >= 1
    assert body["summary"]["p0_question_count"] >= 1
    assert body["summary"]["phase2_closure_policy"] == "owner_decision_required"
    assert body["summary"]["phase2_owner_question_status"] == "open"
    assert body["summary"]["contractual_milestone_progress"] == "not_calculated"
    assert body["summary"]["customer_acceptance_claimed"] is False
    assert body["summary"]["phase12_union_ready"] is False
    assert body["summary"]["must_not_fake"] is True
    assert "P0 owner questions" in body["next_action"]
    assert "fallback-only" in body["next_action"]
    rendered_questions = json.dumps(body["questions"])
    assert "grouped customer runtime config actions" not in rendered_questions
    assert "grouped customer decision actions" not in rendered_questions
    assert "Identity provider and MQTT broker setup" in rendered_questions
    assert "Production go-live decisions" in rendered_questions
    assert body["privacy"]["customer_safe"] is True
    assert body["privacy"]["admin_write_endpoints_returned"] is False
    question_text = json.dumps(body["questions"])
    assert "?" in question_text
    assert "ai model" in question_text.lower() or "customer decision" in question_text.lower()
    for item in body["questions"]:
        assert item["customer_safe"] is True
        assert item["question_id"].startswith("owner-question-")
        assert item["question"].endswith("?")
        assert item["required_evidence"]
        assert item["answer_options"]
        assert item["acceptance_impact"]
        assert item["owner_agent_id"]
        assert item["evidence_endpoint"].startswith("/api/")
        assert item["source_action_ids"]
    assert "/api/admin" not in response.text
    assert '"method"' not in response.text
    assert '"PATCH"' not in response.text
    assert "unit-" + "operator-" + "sentinel" not in response.text
    assert "/home/" not in response.text
    assert "C:" not in response.text


def test_owner_decision_brief_is_rendered_in_customer_dashboard(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "owner-brief-ui.db"))

    response = client.get("/")

    assert response.status_code == 200
    page = response.text
    assert 'id="owner-decision-brief"' in page
    assert 'id="owner-decision-brief-body"' in page
    assert "Owner Decision Brief" in page
    assert "loadJson('/api/production/owner-decision-brief')" in page
    assert "renderOwnerDecisionBrief(ownerDecisionBrief)" in page
    assert "/api/admin/production/action-plan" not in page



def test_admin_production_action_plan_exposes_write_guidance_only_to_admin(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "admin-action-plan.db"))

    public_response = client.get("/api/production/action-plan")
    anonymous_admin = client.get("/api/admin/production/action-plan")
    admin_response = client.get(
        "/api/admin/production/action-plan",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
    )

    assert public_response.status_code == 200
    assert anonymous_admin.status_code == 401
    assert admin_response.status_code == 200
    assert "/api/admin/production" not in public_response.text
    assert '"method":"PATCH"' not in public_response.text
    body = admin_response.json()
    assert body["admin_console_endpoint"] == "/api/admin/production/action-plan"
    assert body["summary"]["required_scope"] == "access:manage"
    assert body["summary"]["admin_action_count"] == len(body["actions"])
    actions = {item["action_id"]: item for item in body["actions"]}
    runtime_action = actions["control-runtime-mode"]
    assert runtime_action["method"] == "PATCH"
    assert runtime_action["admin_endpoint"] == (
        "/api/admin/production/readiness-controls/runtime-mode"
    )
    assert runtime_action["required_scope"] == "access:manage"
    assert "request_schema" in runtime_action
    ai_route = actions["decision-ai-model-route-approval"]
    assert ai_route["admin_endpoint"] == (
        "/api/admin/production/decisions/ai-model-route-approval"
    )
    assert ai_route["method"] == "PATCH"
    assert ai_route["required_scope"] == "admin:delivery:approve"
    assert "formal customer acceptance" in ai_route["approval_boundary"]
    assert body["privacy"]["public_exposure"] is False
    assert body["privacy"]["credential_values_returned"] is False
    assert "unit-" + "admin-" + "sentinel" not in admin_response.text
    assert "/home/" not in admin_response.text
    assert "C:" not in admin_response.text


def test_production_action_plan_omits_closed_runtime_controls(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app(database_path=tmp_path / "production-runtime.db"))

    response = client.get("/api/production/action-plan")

    assert response.status_code == 200
    body = response.json()
    actions = {item["action_id"]: item for item in body["actions"]}
    assert "control-runtime-mode" not in actions
    assert "control-trusted-hosts" not in actions
    assert "control-interactive-api-documentation" not in actions
    assert "control-mqtt-broker-subscriber" in actions
    assert (
        actions["control-mqtt-broker-subscriber"]["blocking_category"]
        == "customer_runtime_config"
    )
    assert (
        actions["control-mqtt-broker-subscriber"][
            "can_close_without_customer_secret"
        ]
        is False
    )
    assert "decision-hosting-owner" in actions
    assert "decision-ai-model-route-approval" in actions
    assert actions["decision-hosting-owner"]["blocking_category"] == "customer_decision"
    assert body["summary"]["customer_decision_required"] is True
    assert body["summary"]["engineering_closeable_action_count"] >= 1




def test_production_preflight_reports_secret_free_customer_actions(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "production-preflight.db"))

    response = client.get("/api/production/preflight")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["checked_control_count"] == 5
    assert body["summary"]["customer_secret_required_count"] == 2
    assert body["summary"]["recordable_without_secret_count"] == 3
    checks = {item["check_id"]: item for item in body["checks"]}
    assert checks["reverse-proxy-tls"]["state"] == "customer_action_required"
    assert checks["backup-retention"]["state"] == "customer_action_required"
    assert checks["backup-restore-test"]["state"] == "review_required"
    assert checks["identity-provider"]["state"] == "customer_action_required"
    assert checks["identity-provider"]["can_close_without_customer_secret"] is False
    assert checks["mqtt-broker-subscriber"]["state"] == "customer_action_required"
    assert checks["mqtt-broker-subscriber"]["can_close_without_customer_secret"] is False
    links = {item["endpoint"] for item in body["evidence_links"]}
    assert "/api/production/hardening" in links
    assert "/api/production/action-plan" in links
    assert "/api/access/policy" in links
    assert "/api/adapters/mqtt/broker/status" in links
    assert "/api/admin/production" not in response.text
    assert "unit-" + "operator-" + "sentinel" not in response.text
    assert "/home/" not in response.text
    assert "C:" not in response.text


def test_production_preflight_ready_when_tls_backup_and_restore_are_configured(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver,demo.greenovax.example")
    monkeypatch.setenv("AGENTIOT_TLS_TERMINATION", "reverse-proxy")
    monkeypatch.setenv("AGENTIOT_TLS_CERT_SOURCE", "customer-ca")
    monkeypatch.setenv("AGENTIOT_PUBLIC_ACCESS_URL", "https://demo.greenovax.example:8040")
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "encrypted daily retention metadata")
    monkeypatch.setenv("AGENTIOT_BACKUP_RETENTION_DAYS", "90")
    monkeypatch.setenv("AGENTIOT_BACKUP_CADENCE_HOURS", "12")
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "unit-idp-validation-key")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "mqtt.customer.example")
    monkeypatch.setenv("AGENTIOT_MQTT_TOPIC_PREFIX", "agentiot")
    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    strong_operator_token = "preflight-production-operator-" + ("a" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", strong_operator_token)
    client = TestClient(create_app(database_path=tmp_path / "production-preflight-ready.db"))
    client.app.state.mqtt_broker.connected = True
    seed_response = client.post(
        "/api/assets",
        headers={"X-Operator-Token": strong_operator_token},
        json={"asset_id": "preflight-ready-asset", "name": "Preflight Ready Asset"},
    )
    assert seed_response.status_code == 201
    restore_response = client.post(
        "/api/admin/production/restore-test",
        headers=admin_token_headers(monkeypatch),
        json={},
    )
    assert restore_response.status_code == 200

    response = client.get("/api/production/preflight")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["summary"]["ready_count"] == 5
    assert body["summary"]["action_required_count"] == 0
    checks = {item["check_id"]: item for item in body["checks"]}
    assert checks["identity-provider"]["state"] == "ready"
    assert checks["mqtt-broker-subscriber"]["state"] == "ready"
    assert checks["mqtt-broker-subscriber"]["runtime_signals"]["broker_configured"] is True
    tls = checks["reverse-proxy-tls"]["runtime_signals"]
    assert tls["tls_termination_mode"] == "reverse-proxy"
    assert tls["trusted_hosts_configured"] is True
    assert tls["browser_trusted"] is True
    assert tls["certificate_source"] == "customer-ca"
    assert tls["public_access_url"] == "https://demo.greenovax.example:8040"
    backup = checks["backup-retention"]["runtime_signals"]
    assert backup["retention_days"] == 90
    assert backup["cadence_hours"] == 12
    assert backup["restore_test_state"] == "recorded"
    assert backup["policy_fingerprint"]
    assert "encrypted daily retention metadata" not in response.text
    assert body["privacy"]["credential_values_returned"] is False
    assert body["privacy"]["backup_paths_returned"] is False


def test_production_preflight_requires_browser_trust_for_self_signed_tls(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver,demo.greenovax.example")
    monkeypatch.setenv("AGENTIOT_TLS_TERMINATION", "reverse-proxy")
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "encrypted daily retention metadata")
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "unit-idp-validation-key")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "mqtt.customer.example")
    monkeypatch.setenv("AGENTIOT_MQTT_TOPIC_PREFIX", "agentiot")
    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    strong_operator_token = "tls-production-operator-" + ("b" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", strong_operator_token)
    client = TestClient(create_app(database_path=tmp_path / "production-preflight-tls.db"))
    client.app.state.mqtt_broker.connected = True
    seed_response = client.post(
        "/api/assets",
        headers={"X-Operator-Token": strong_operator_token},
        json={"asset_id": "preflight-tls-asset", "name": "Preflight TLS Asset"},
    )
    assert seed_response.status_code == 201
    restore_response = client.post(
        "/api/admin/production/restore-test",
        headers=admin_token_headers(monkeypatch),
        json={},
    )
    assert restore_response.status_code == 200

    response = client.get("/api/production/preflight")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["summary"]["ready_count"] == 4
    checks = {item["check_id"]: item for item in body["checks"]}
    tls = checks["reverse-proxy-tls"]
    assert tls["state"] == "review_required"
    assert tls["next_gate"] == "trusted_tls_certificate_review"
    assert tls["runtime_signals"]["tls_termination_mode"] == "reverse-proxy"
    assert tls["runtime_signals"]["certificate_source"] == "self-signed-lab"
    assert tls["runtime_signals"]["browser_trusted"] is False
    assert "Browser-trusted" in tls["required_evidence"]
    assert "BEGIN " not in response.text
    assert "PRIVATE KEY" not in response.text

def test_feedback_summary_aggregates_customer_feedback(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "feedback-summary.db"))

    for area, rating in [("production-readiness", 5), ("demo", 4)]:
        accepted = client.post(
            "/api/customer/feedback",
            headers=OPERATOR_HEADERS,
            json={
                "reviewer_role": "customer-reviewer",
                "area": area,
                "rating": rating,
                "comment": f"{area} review accepted.",
            },
        )
        assert accepted.status_code == 201

    response = client.get("/api/customer/feedback/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["feedback_count"] == 2
    assert body["average_rating"] == 4.5
    assert body["areas"]["production-readiness"] == 1
    assert body["areas"]["demo"] == 1
    assert body["stored_contact_data"] is False
    assert body["next_gate"] == "production_owner_feedback_review"


def test_owner_approval_reflects_feedback_summary(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "approval-feedback.db"))
    accepted = client.post(
        "/api/customer/feedback",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_role": "customer-reviewer",
            "area": "production-readiness",
            "rating": 5,
            "comment": "Ready for owner decision.",
        },
    )
    assert accepted.status_code == 201

    response = client.get("/api/production/approval-package")

    assert response.status_code == 200
    decisions = {item["decision_id"]: item for item in response.json()["decision_items"]}
    assert decisions["customer-feedback"]["state"] == "ready_for_review"
    assert "1 feedback" in decisions["customer-feedback"]["evidence"]


def test_admin_can_record_owner_decision_with_audit(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "owner-decisions.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.patch(
        "/api/admin/production/decisions/hosting-owner",
        headers=headers,
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Hosting owner decision recorded for review package.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["decision"]["decision_id"] == "hosting-owner"
    assert body["decision"]["state"] == "approved"
    anonymous = client.get("/api/admin/production/decisions")
    decisions = client.get(
        "/api/admin/production/decisions", headers=headers
    ).json()["items"]
    assert anonymous.status_code == 401
    assert anonymous.json()["detail"] == "Admin token or bearer required"
    hosting = next(item for item in decisions if item["decision_id"] == "hosting-owner")
    assert hosting["source"] == "owner_decision"
    assert hosting["decided_by"] == "production-owner"
    owner_package = client.get("/api/production/approval-package").json()
    owner_items = {item["decision_id"]: item for item in owner_package["decision_items"]}
    assert owner_items["hosting-owner"]["state"] == "approved"
    audit = client.get("/api/audit/events", headers=headers).json()["items"]
    assert audit[-1]["event_type"] == "owner.decision.updated"
    assert audit[-1]["subject_id"] == "hosting-owner"


def test_owner_decision_write_requires_delivery_approval_scope(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "owner-scope.db"))
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="delivery-admin",
        role="admin",
        scopes=["admin:delivery:approve"],
    )
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="access-admin",
        role="admin",
        scopes=["access:manage"],
    )
    delivery_token = make_test_jwt(
        subject="delivery-admin",
        role="admin",
        scope="admin:delivery:approve",
    )
    access_token = make_test_jwt(
        subject="access-admin",
        role="admin",
        scope="access:manage",
    )

    allowed = client.patch(
        "/api/admin/production/decisions/hosting-owner",
        headers={"Authorization": f"Bearer {delivery_token}"},
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Hosting owner decision recorded for review package.",
        },
    )
    denied = client.patch(
        "/api/admin/production/decisions/hosting-owner",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Access admin must not approve owner decisions.",
        },
    )

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["detail"] == (
        "Admin scope required: admin:delivery:approve"
    )


def test_admin_can_record_phase_one_closure_decision_with_audit(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "phase-one-decision.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}

    response = client.patch(
        "/api/admin/production/decisions/phase-1-closure",
        headers=headers,
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": (
                "Phase 1 commercial baseline and foundation deliverables "
                "approved for closure."
            ),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["decision"]["decision_id"] == "phase-1-closure"
    assert body["decision"]["state"] == "approved"
    package = client.get("/api/production/approval-package").json()
    decisions = {item["decision_id"]: item for item in package["decision_items"]}
    phase_one = decisions["phase-1-closure"]
    assert phase_one["source"] == "owner_decision"
    assert phase_one["decided_by"] == "production-owner"
    assert "approved" in phase_one["evidence"].lower()
    assert "unit-admin-sentinel" not in json.dumps(package)
    audit = client.get("/api/audit/events", headers=headers).json()["items"]
    assert audit[-1]["event_type"] == "owner.decision.updated"
    assert audit[-1]["subject_id"] == "phase-1-closure"


def test_owner_decision_rejects_contact_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "owner-decision-contact.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}

    response = client.patch(
        "/api/admin/production/decisions/hosting-owner",
        headers=headers,
        json={
            "state": "approved",
            "decided_by": "owner@example.test",
            "decision_note": "Do not store contact data.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Contact data is not accepted"
    decisions = client.get(
        "/api/admin/production/decisions", headers=headers
    ).json()["items"]
    hosting = next(item for item in decisions if item["decision_id"] == "hosting-owner")
    assert hosting["source"] == "system"


def test_phase_one_owner_decision_rejects_secret_and_private_path(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "phase-one-secret.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}

    for decision_note in [
        "Do not store " + "sk-" + "owner-secret in the phase one note.",
        "Do not store C:\\private\\phase-one evidence paths.",
        "Do not store /home/" + "iot/private-phase-one evidence paths.",
        "Do not store /root/private-phase-one evidence paths.",
        "Do not store AGENTIOT_" + "ADMIN_TOKEN in the phase one note.",
        "Do not store GEMINI_" + "API_KEY in the phase one note.",
        "Do not store ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789 tokens.",
        "Do not store HF_" + "TOKEN in the phase one note.",
    ]:
        response = client.patch(
            "/api/admin/production/decisions/phase-1-closure",
            headers=headers,
            json={
                "state": "approved",
                "decided_by": "production-owner",
                "decision_note": decision_note,
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Sensitive owner decision material is not accepted"
        )

    decisions = client.get(
        "/api/admin/production/decisions", headers=headers
    ).json()["items"]
    phase_one = next(
        item for item in decisions if item["decision_id"] == "phase-1-closure"
    )
    assert phase_one["source"] == "system"
    assert "sk-" + "owner-secret" not in json.dumps(decisions)
    assert "C:\\private" not in json.dumps(decisions)
    assert "/home/" + "iot" not in json.dumps(decisions)
    assert "/root/private" not in json.dumps(decisions)
    assert "AGENTIOT_" + "ADMIN_TOKEN" not in json.dumps(decisions)
    assert "GEMINI_" + "API_KEY" not in json.dumps(decisions)
    assert "ghp_" not in json.dumps(decisions)
    assert "HF_" + "TOKEN" not in json.dumps(decisions)


def test_admin_can_record_ai_model_route_owner_decision_without_secret_leak(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "owner-ai-route.db"))

    response = client.patch(
        "/api/admin/production/decisions/ai-model-route-approval",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Fallback-only route accepted until model credentials are approved.",
        },
    )

    assert response.status_code == 200
    package = client.get("/api/production/approval-package").json()
    decisions = {item["decision_id"]: item for item in package["decision_items"]}
    ai_route = decisions["ai-model-route-approval"]
    assert ai_route["state"] == "approved"
    assert ai_route["source"] == "owner_decision"
    assert "fallback" in ai_route["evidence"].lower()
    links = {item["endpoint"] for item in package["evidence_links"]}
    assert "/api/ai/routing" in links
    assert "/api/ai/model-benchmarks" in links
    assert "/api/ai/evaluations/runs" in links
    assert "test-" + "admin-" + "token" not in response.text
    assert "sk-" not in response.text.lower()
    assert "api_key" not in response.text.lower()


def test_admin_can_record_production_readiness_control_with_audit(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "readiness-control.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}

    response = client.patch(
        "/api/admin/production/readiness-controls/reverse-proxy-tls",
        headers=headers,
        json={
            "state": "ready",
            "owner": "production-owner",
            "evidence": "Reverse proxy TLS owner evidence recorded for review.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["control"]["control_id"] == "reverse-proxy-tls"
    assert body["control"]["state"] == "ready"
    anonymous = client.get("/api/admin/production/readiness-controls")
    controls = client.get(
        "/api/admin/production/readiness-controls", headers=headers
    ).json()["items"]
    assert anonymous.status_code == 401
    assert anonymous.json()["detail"] == "Admin token or bearer required"
    tls = next(item for item in controls if item["control_id"] == "reverse-proxy-tls")
    assert tls["source"] == "readiness_control"
    assert tls["owner"] == "production-owner"
    hardening = client.get("/api/production/hardening").json()
    tls_public = next(
        item for item in hardening["items"] if item["control_id"] == "reverse-proxy-tls"
    )
    assert tls_public["source"] == "readiness_control"
    assert tls_public["state"] == "ready"
    audit = client.get("/api/audit/events", headers=headers).json()["items"]
    assert audit[-1]["event_type"] == "production.control.updated"
    assert audit[-1]["subject_id"] == "reverse-proxy-tls"


def test_production_readiness_control_rejects_contact_data(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "readiness-contact.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}

    response = client.patch(
        "/api/admin/production/readiness-controls/reverse-proxy-tls",
        headers=headers,
        json={
            "state": "ready",
            "owner": "owner@example.test",
            "evidence": "Do not store contact data.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Contact data is not accepted"
    controls = client.get(
        "/api/admin/production/readiness-controls", headers=headers
    ).json()["items"]
    tls = next(item for item in controls if item["control_id"] == "reverse-proxy-tls")
    assert tls["source"] == "system"


def test_production_readiness_control_rejects_secrets_and_private_paths(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "readiness-sensitive.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}
    secret_like = "sk-" + "owner-secret"
    private_unix_path = "/" + "home" + "/" + "iot" + "/" + "private-backup.sqlite"
    private_windows_path = "C" + ":\\" + "temp" + "\\" + "private-backup.sqlite"

    for evidence in (
        f"Validated with {secret_like} and approved.",
        f"Restore evidence stored at {private_unix_path}.",
        f"Temporary review copy at {private_windows_path}.",
    ):
        response = client.patch(
            "/api/admin/production/readiness-controls/reverse-proxy-tls",
            headers=headers,
            json={
                "state": "ready",
                "owner": "production-owner",
                "evidence": evidence,
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Sensitive production readiness material is not accepted"
        )

    for endpoint in (
        "/api/production/hardening",
        "/api/production/action-plan",
        "/api/production/preflight",
    ):
        public_response = client.get(endpoint)
        lowered = public_response.text.lower()
        assert secret_like not in lowered
        assert "/" + "home" + "/" not in lowered
        assert ("c" + ":\\" + "temp") not in lowered


def test_production_public_access_rejects_private_tailnet_and_ip_urls(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver,demo.greenovax.example")
    monkeypatch.setenv("AGENTIOT_TLS_TERMINATION", "reverse-proxy")
    monkeypatch.setenv("AGENTIOT_TLS_CERT_SOURCE", "customer-ca")
    monkeypatch.setenv("AGENTIOT_TLS_BROWSER_TRUSTED", "true")
    private_tailnet_host = ".".join(["100", "109", "247", "47"])
    monkeypatch.setenv(
        "AGENTIOT_PUBLIC_ACCESS_URL",
        f"https://{private_tailnet_host}:8040/private-review",
    )
    client = TestClient(create_app(database_path=tmp_path / "private-public-url.db"))

    preflight = client.get("/api/production/preflight")
    hardening = client.get("/api/production/hardening")

    assert preflight.status_code == 200
    assert hardening.status_code == 200
    assert private_tailnet_host not in preflight.text
    assert private_tailnet_host not in hardening.text
    tls = next(
        item
        for item in preflight.json()["checks"]
        if item["check_id"] == "reverse-proxy-tls"
    )
    assert tls["runtime_signals"]["public_access_configured"] is False
    assert tls["runtime_signals"]["public_access_url"] is None


def test_owner_package_can_reach_owner_approved_after_all_decisions(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "owner-approved.db"))
    for decision_id in [
        "phase-1-closure",
        "production-hardening",
        "hosting-owner",
        "reverse-proxy-tls",
        "backup-retention",
        "identity-provider",
        "mqtt-broker-subscriber",
        "ai-model-route-approval",
        "customer-feedback",
        "phase-2-closure",
    ]:
        response = client.patch(
            f"/api/admin/production/decisions/{decision_id}",
            headers={"X-Admin-Token": "unit-admin-sentinel"},
            json={
                "state": "approved",
                "decided_by": "production-owner",
                "decision_note": "Decision approved for owner review evidence.",
            },
        )
        assert response.status_code == 200

    package = client.get("/api/production/approval-package").json()

    assert package["status"] == "owner_approved"
    assert package["next_gate"] == "phase_3_final_acceptance"


def test_public_owner_and_handoff_surfaces_do_not_expose_admin_decision_paths(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "public-owner-safe.db"))

    for endpoint in (
        "/api/production/approval-package",
        "/api/delivery/handoff-console",
    ):
        response = client.get(endpoint)

        assert response.status_code == 200
        assert "/api/admin/production/decisions" not in response.text
        assert "/api/production/approval-package" in response.text
        assert "unit-" + "operator-" + "sentinel" not in response.text


def test_owner_approval_package_lists_mqtt_field_validation_decision(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-owner-decision.db"))

    response = client.get("/api/production/approval-package")

    assert response.status_code == 200
    decisions = {item["decision_id"]: item for item in response.json()["decision_items"]}
    mqtt = decisions["mqtt-broker-subscriber"]
    assert mqtt["state"] == "customer_action_required"
    assert "field connectivity evidence" in mqtt["evidence"]
    assert "password" not in response.text.lower()
    assert "certificate material" not in response.text.lower()
    assert "/api/admin/production/decisions" not in response.text


def test_owner_decision_form_covers_recordable_approval_decisions(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "owner-form-coverage.db"))

    approval = client.get("/api/production/approval-package").json()
    root_page = client.get("/").text
    recordable_ids = {
        item["decision_id"]
        for item in approval["decision_items"]
        if item["decision_id"] != "release-baseline"
    }

    for decision_id in recordable_ids:
        assert f'<option value="{decision_id}">' in root_page


def test_owner_decision_form_covers_backend_decision_states(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "owner-state-coverage.db"))

    root_page = client.get("/").text

    for state in OWNER_DECISION_STATES:
        assert f'<option value="{state}">' in root_page
