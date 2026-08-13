# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from agentiot.app import create_app
from conftest import make_test_jwt, make_test_rs256_jwt

OPERATOR_TOKEN_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def configure_device_ingest(
    tmp_path,
    monkeypatch,
    credentials: dict[str, str],
) -> None:
    credential_file = tmp_path / "edge-ingest-credentials.json"
    credential_file.write_text(json.dumps(credentials), encoding="utf-8")
    monkeypatch.setenv(
        "AGENTIOT_EDGE_INGEST_CREDENTIALS_FILE",
        str(credential_file),
    )


def configure_idp(monkeypatch) -> None:
    """Enable deterministic local JWT validation for bearer scope tests."""

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")


def admin_token_headers(monkeypatch) -> dict[str, str]:
    """Return bootstrap admin-token headers for assignment setup."""

    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    return {"X-Admin-Token": "unit-admin-sentinel"}


def assign_bearer_user(
    client: TestClient,
    headers: dict[str, str],
    subject: str,
    *,
    role: str = "operator",
    scopes: list[str] | None = None,
    status: str = "active",
) -> None:
    """Create a local assignment for an opaque bearer subject."""

    response = client.patch(
        f"/api/admin/access/users/{subject}",
        headers=headers,
        json={
            "role": role,
            "scopes": scopes or ["device:write", "telemetry:write"],
            "status": status,
            "note": "Test access assignment without contact data.",
        },
    )
    assert response.status_code == 200


def test_browser_login_gate_also_protects_customer_data_apis(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_REQUIRE_BROWSER_LOGIN", "1")
    client = TestClient(create_app(database_path=tmp_path / "browser-data-gate.db"))

    unauthenticated = client.get("/api/operations/summary")
    authenticated = client.get(
        "/api/operations/summary",
        headers=OPERATOR_TOKEN_HEADERS,
    )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 200


def test_device_ingest_token_is_write_only_bound_and_replay_safe(
    tmp_path,
    monkeypatch,
) -> None:
    device_token = "edge-ingest-a-" + ("x" * 64)
    second_token = "edge-ingest-b-" + ("y" * 64)
    configure_device_ingest(
        tmp_path,
        monkeypatch,
        {
            "edge-thermal-1": device_token,
            "edge-thermal-2": second_token,
        },
    )
    client = TestClient(create_app(database_path=tmp_path / "edge-ingest.db"))
    for device_id in ("edge-thermal-1", "edge-thermal-2"):
        registered = client.post(
            "/api/devices",
            headers=OPERATOR_TOKEN_HEADERS,
            json={"device_id": device_id, "name": "Edge thermal sensor"},
        )
        assert registered.status_code == 201
    sample = {
        "device_id": "edge-thermal-1",
        "metric": "temperature_c",
        "value": 52.78,
        "unit": "C",
        "sample_id": "a" * 32,
        "sampled_at": datetime.now(UTC).isoformat(),
    }

    assert client.post(
        "/api/devices/edge-thermal-1/telemetry",
        json=sample,
    ).status_code == 401
    assert client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": "wrong-token"},
        json=sample,
    ).status_code == 401

    accepted = client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": device_token},
        json=sample,
    )
    assert accepted.status_code == 201
    assert "edge-ingest-" not in accepted.text

    cross_device = client.post(
        "/api/devices/edge-thermal-2/telemetry",
        headers={"X-Device-Ingest-Token": device_token},
        json={**sample, "device_id": "edge-thermal-2", "sample_id": "b" * 32},
    )
    assert cross_device.status_code == 401
    mismatch = client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": device_token},
        json={**sample, "device_id": "another-device"},
    )
    assert mismatch.status_code == 400

    replay = client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": device_token},
        json=sample,
    )
    assert replay.status_code == 201
    assert replay.json()["telemetry_id"] == accepted.json()["telemetry_id"]
    assert replay.json()["idempotent_replay"] is True
    conflicting_replay = client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": device_token},
        json={**sample, "value": 53.1},
    )
    assert conflicting_replay.status_code == 409
    telemetry = client.get("/api/telemetry", headers=OPERATOR_TOKEN_HEADERS)
    assert telemetry.status_code == 200
    assert len(telemetry.json()["items"]) == 1

    unrelated_write = client.post(
        "/api/assets",
        headers={"X-Device-Ingest-Token": device_token},
        json={"asset_id": "forbidden-asset", "name": "Forbidden"},
    )
    assert unrelated_write.status_code == 401
    audit = client.get("/api/audit/events", headers=OPERATOR_TOKEN_HEADERS)
    assert audit.status_code == 200
    assert device_token not in audit.text
    assert "telemetry.edge_ingested" in audit.text


def test_device_ingest_endpoint_fails_closed_without_runtime_configuration(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AGENTIOT_EDGE_INGEST_CREDENTIALS_FILE", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "edge-ingest-off.db"))

    response = client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": "unused-" + ("x" * 64)},
        json={
            "device_id": "edge-thermal-1",
            "metric": "temperature_c",
            "value": 52.78,
            "unit": "C",
            "sample_id": "a" * 32,
            "sampled_at": datetime.now(UTC).isoformat(),
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Device ingestion authentication unavailable"


def test_device_ingest_rejects_stale_future_and_privileged_credentials(
    tmp_path,
    monkeypatch,
) -> None:
    privileged_token = "privileged-" + ("p" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", privileged_token)
    configure_device_ingest(
        tmp_path,
        monkeypatch,
        {"edge-thermal-1": privileged_token},
    )
    client = TestClient(create_app(database_path=tmp_path / "edge-time.db"))
    base = {
        "device_id": "edge-thermal-1",
        "metric": "temperature_c",
        "value": 52.78,
        "unit": "C",
        "sample_id": "c" * 32,
    }

    unavailable = client.post(
        "/api/devices/edge-thermal-1/telemetry",
        headers={"X-Device-Ingest-Token": privileged_token},
        json={**base, "sampled_at": datetime.now(UTC).isoformat()},
    )
    assert unavailable.status_code == 503

    edge_token = "edge-only-" + ("e" * 64)
    configure_device_ingest(
        tmp_path,
        monkeypatch,
        {"edge-thermal-1": edge_token},
    )
    for sampled_at in (
        datetime.now(UTC) - timedelta(days=2),
        datetime.now(UTC) + timedelta(minutes=10),
    ):
        response = client.post(
            "/api/devices/edge-thermal-1/telemetry",
            headers={"X-Device-Ingest-Token": edge_token},
            json={**base, "sampled_at": sampled_at.isoformat()},
        )
        assert response.status_code == 400


def test_device_ingest_rate_limit_cannot_be_evaded_by_rotating_device_ids(
    tmp_path,
    monkeypatch,
) -> None:
    configure_device_ingest(
        tmp_path,
        monkeypatch,
        {"edge-thermal-1": "edge-only-" + ("e" * 64)},
    )
    client = TestClient(create_app(database_path=tmp_path / "edge-rate.db"))
    statuses = []
    for index in range(21):
        device_id = f"unknown-edge-{index}"
        response = client.post(
            f"/api/devices/{device_id}/telemetry",
            headers={"X-Device-Ingest-Token": "wrong-token"},
            json={
                "device_id": device_id,
                "metric": "temperature_c",
                "value": 52.78,
                "unit": "C",
                "sample_id": f"{index:032x}",
                "sampled_at": datetime.now(UTC).isoformat(),
            },
        )
        statuses.append(response.status_code)

    assert statuses[:20] == [401] * 20
    assert statuses[20] == 429


def test_access_policy_reports_roles_scopes_and_idp_status(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "access-policy.db"))

    response = client.get("/api/access/policy")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["identity_provider"]["state"] == "not_configured"
    assert body["identity_provider"]["issuer_configured"] is False
    assert body["identity_provider"]["shared_secret_configured"] is False
    role_names = {role["role"] for role in body["roles"]}
    assert {"viewer", "operator", "admin"}.issubset(role_names)
    operator = next(role for role in body["roles"] if role["role"] == "operator")
    assert "telemetry:write" in operator["scopes"]
    assert "recovery:approve" in operator["scopes"]
    assert "agent:run" in operator["scopes"]
    assert "panel:operate:read" in operator["scopes"]
    assert body["human_approval_required"] is True
    assert body["scope_catalog"]["default_decision"] == "deny"


def test_access_policy_exposes_granular_default_deny_scope_catalog(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "scope-catalog.db"))

    response = client.get("/api/access/policy")

    assert response.status_code == 200
    catalog = response.json()["scope_catalog"]
    assert catalog["role_policy"] == "built_in_operator_admin_bearer_only"
    assert catalog["unknown_bearer_role_decision"] == "deny"
    assert "panel:operate:read" in {
        item["scope"] for item in catalog["panel_scopes"]
    }
    assert "agent:ai_diagnosis_agent:run" in {
        item["scope"] for item in catalog["agent_action_scopes"]
    }
    assert "data:telemetry:write" in {
        item["scope"] for item in catalog["data_scopes"]
    }
    assert "admin:access:manage" in {
        item["scope"] for item in catalog["admin_scopes"]
    }
    assert catalog["scope_count"] >= 24


def test_root_page_exposes_access_policy_without_secret_material() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Access Policy" in response.text
    assert "/api/access/policy" in response.text
    assert "id=\"access-policy-body\"" in response.text
    assert "Identity Provider" in response.text
    assert "id=\"identity-provider-body\"" in response.text


def test_access_policy_reports_configured_identity_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "idp-policy.db"))

    response = client.get("/api/access/policy")

    assert response.status_code == 200
    body = response.json()
    assert body["identity_provider"]["state"] == "configured"
    assert body["identity_provider"]["issuer_configured"] is True
    assert body["identity_provider"]["audience_configured"] is True
    assert body["identity_provider"]["shared_secret_configured"] is True
    assert body["identity_provider"]["token_algorithm"] == "HS256"
    assert body["identity_provider"]["validation_method"] == "shared_secret"
    assert "test-idp-validation-key" not in response.text


def test_access_policy_reports_rs256_jwks_identity_provider(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_JWKS_URL", "https://idp.example.test/jwks.json")
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setattr(
        "agentiot.app.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    client = TestClient(create_app(database_path=tmp_path / "idp-rs-policy.db"))

    response = client.get("/api/access/policy")

    assert response.status_code == 200
    body = response.json()
    assert body["identity_provider"]["state"] == "configured"
    assert body["identity_provider"]["jwks_configured"] is True
    assert body["identity_provider"]["shared_secret_configured"] is False
    assert body["identity_provider"]["token_algorithm"] == "RS256"
    assert body["identity_provider"]["validation_method"] == "jwks"
    assert "jwks.json" not in response.text


def test_bearer_token_validation_reports_actor_role_and_scopes(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "idp-validate.db"))
    assign_bearer_user(
        client,
        admin_token_headers(monkeypatch),
        "operator-user",
        scopes=["device:write", "telemetry:write", "recovery:approve"],
    )
    token = make_test_jwt(subject="operator-user")

    response = client.post(
        "/api/access/token/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "valid"
    assert body["actor"] == "operator-user"
    assert body["role"] == "operator"
    assert "device:write" in body["scopes"]
    assert body["provider"] == "bearer-token+assignment"


def test_bearer_token_validation_accepts_list_audience(tmp_path, monkeypatch) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "idp-list-aud.db"))
    assign_bearer_user(client, admin_token_headers(monkeypatch), "list-audience-user")
    token = make_test_jwt(
        subject="list-audience-user",
        audience=["other-audience", "agentiot-dashboard"],
    )

    response = client.post(
        "/api/access/token/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "valid"


def test_rs256_jwks_bearer_token_validation(
    tmp_path, monkeypatch
) -> None:
    token, public_key = make_test_rs256_jwt(subject="operator-rs256")
    monkeypatch.setattr(
        "agentiot.app.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )

    class FakeSigningKey:
        key = public_key

    class FakeJWKClient:
        def __init__(self, _url: str) -> None:
            self.url = _url

        def get_signing_key_from_jwt(self, _token: str) -> FakeSigningKey:
            return FakeSigningKey()

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_JWKS_URL", "https://idp.example.test/jwks.json")
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setattr("agentiot.app.PyJWKClient", FakeJWKClient)
    client = TestClient(create_app(database_path=tmp_path / "idp-rs-validate.db"))
    assign_bearer_user(
        client,
        admin_token_headers(monkeypatch),
        "operator-rs256",
        scopes=["device:write", "telemetry:write", "recovery:approve"],
    )

    response = client.post(
        "/api/access/token/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "valid"
    assert body["actor"] == "operator-rs256"
    assert body["role"] == "operator"
    assert "telemetry:write" in body["scopes"]
    assert "jwks.json" not in response.text


def test_unassigned_bearer_role_is_denied_before_device_write(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "custom-role-scope.db"))
    device_only_token = make_test_jwt(
        subject="field-device@example.test",
        role="field-device",
        scope="device:write",
    )

    device_response = client.post(
        "/api/devices",
        headers={"Authorization": f"Bearer {device_only_token}"},
        json={"device_id": "scoped-device", "name": "Scoped Device"},
    )
    assert device_response.status_code == 403
    assert device_response.json()["detail"] == "Access assignment required"
    assert client.get("/api/devices").json()["items"] == []


def test_unassigned_bearer_role_is_denied_before_telemetry_write(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "custom-telemetry-scope.db"))
    client.post(
        "/api/devices",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
        json={"device_id": "telemetry-scoped-device", "name": "Telemetry Scoped"},
    )
    telemetry_token = make_test_jwt(
        subject="field-telemetry@example.test",
        role="field-telemetry",
        scope="telemetry:write",
    )

    response = client.post(
        "/api/telemetry",
        headers={"Authorization": f"Bearer {telemetry_token}"},
        json={
            "device_id": "telemetry-scoped-device",
            "metric": "temperature_c",
            "value": 83.0,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access assignment required"


def test_active_user_assignment_limits_bearer_scopes(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "assigned-scope.db"))
    admin_headers = admin_token_headers(monkeypatch)
    client.patch(
        "/api/admin/access/users/field-operator",
        headers=admin_headers,
        json={
            "role": "operator",
            "scopes": ["telemetry:write"],
            "status": "active",
            "note": "Restrict pilot operator to telemetry ingestion.",
        },
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_TOKEN_HEADERS,
        json={"device_id": "assigned-device", "name": "Assigned Device"},
    )
    token = make_test_jwt(
        subject="field-operator",
        role="operator",
        scope="device:write telemetry:write",
    )

    device_response = client.post(
        "/api/devices",
        headers={"Authorization": f"Bearer {token}"},
        json={"device_id": "assigned-device", "name": "Assigned Device"},
    )
    telemetry_response = client.post(
        "/api/telemetry",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "device_id": "assigned-device",
            "metric": "temperature_c",
            "value": 21.0,
        },
    )

    assert device_response.status_code == 403
    assert device_response.json()["detail"] == "Scope required: device:write"
    assert telemetry_response.status_code == 201


def test_disabled_user_assignment_blocks_bearer_access(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "disabled-assignment.db"))
    admin_headers = admin_token_headers(monkeypatch)
    client.patch(
        "/api/admin/access/users/blocked-operator",
        headers=admin_headers,
        json={
            "role": "operator",
            "scopes": ["device:write", "telemetry:write"],
            "status": "disabled",
            "note": "Disabled local access assignment.",
        },
    )
    token = make_test_jwt(
        subject="blocked-operator",
        role="operator",
        scope="device:write telemetry:write",
    )

    response = client.post(
        "/api/devices",
        headers={"Authorization": f"Bearer {token}"},
        json={"device_id": "blocked-device", "name": "Blocked Device"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access assignment disabled"
    assert client.get("/api/devices").json()["items"] == []


def test_review_required_user_assignment_blocks_bearer_validation(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "review-assignment.db"))
    admin_headers = admin_token_headers(monkeypatch)
    client.patch(
        "/api/admin/access/users/review-operator",
        headers=admin_headers,
        json={
            "role": "operator",
            "scopes": ["device:write"],
            "status": "review_required",
            "note": "Requires owner review before activation.",
        },
    )
    token = make_test_jwt(
        subject="review-operator",
        role="operator",
        scope="device:write",
    )

    response = client.post(
        "/api/access/token/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access assignment requires review"


def test_custom_role_assignment_allows_only_assigned_scope(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "custom-assignment.db"))
    admin_headers = admin_token_headers(monkeypatch)
    client.patch(
        "/api/admin/access/roles/field-telemetry",
        headers=admin_headers,
        json={
            "description": "Telemetry-only field service role.",
            "scopes": ["telemetry:write"],
        },
    )
    client.patch(
        "/api/admin/access/users/field-telemetry-user",
        headers=admin_headers,
        json={
            "role": "field-telemetry",
            "scopes": ["device:write", "telemetry:write"],
            "status": "active",
            "note": "Assignment cannot exceed the telemetry-only custom role policy.",
        },
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_TOKEN_HEADERS,
        json={"device_id": "custom-role-device", "name": "Custom Role Device"},
    )
    token = make_test_jwt(
        subject="field-telemetry-user",
        role="field-telemetry",
        scope="device:write telemetry:write",
    )

    device_response = client.post(
        "/api/devices",
        headers={"Authorization": f"Bearer {token}"},
        json={"device_id": "custom-role-device", "name": "Custom Role Device"},
    )
    telemetry_response = client.post(
        "/api/telemetry",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "device_id": "custom-role-device",
            "metric": "temperature_c",
            "value": 23.0,
        },
    )

    assert device_response.status_code == 403
    assert device_response.json()["detail"] == "Scope required: device:write"
    assert telemetry_response.status_code == 201


def test_admin_scope_is_enforced_per_control_plane_area(
    tmp_path, monkeypatch
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "admin-scope-area.db"))
    assign_bearer_user(
        client,
        admin_token_headers(monkeypatch),
        "access-admin",
        role="admin",
        scopes=["access:manage"],
    )
    access_admin = make_test_jwt(
        subject="access-admin",
        role="admin",
        scope="access:manage",
    )

    role_response = client.patch(
        "/api/admin/access/roles/scope-reviewer",
        headers={"Authorization": f"Bearer {access_admin}"},
        json={
            "description": "Scope reviewer for access policy validation.",
            "scopes": ["report:read"],
        },
    )
    agent_response = client.patch(
        "/api/admin/agents/operations_coordinator",
        headers={"Authorization": f"Bearer {access_admin}"},
        json={"mode": "observe_only"},
    )

    assert role_response.status_code == 200
    assert agent_response.status_code == 403
    assert agent_response.json()["detail"] == "Admin scope required: agent:manage"
