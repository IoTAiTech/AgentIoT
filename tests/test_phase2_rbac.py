# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

from fastapi.testclient import TestClient

from conftest import (
    admin_token_headers,
    make_test_jwt,
    make_test_rs256_jwt,
    seed_bearer_assignment,
)
from agentiot.app import ACCESS_ROLES, OperatorContext, create_app


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_operator_token_context_uses_central_role_catalogue() -> None:
    operator_role = next(item for item in ACCESS_ROLES if item["role"] == "operator")

    assert OperatorContext().scopes == operator_role["scopes"]


def test_write_endpoint_requires_operator_token(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rbac.db"))

    response = client.post(
        "/api/assets",
        json={"asset_id": "greenhouse-rbac", "name": "RBAC Greenhouse"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Operator token required"
    assert client.get("/api/assets").json()["items"] == []


def test_write_endpoint_accepts_configured_operator_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "configured-token")
    client = TestClient(create_app(database_path=tmp_path / "rbac-token.db"))

    rejected = client.post(
        "/api/assets",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
        json={"asset_id": "greenhouse-rbac", "name": "RBAC Greenhouse"},
    )
    accepted = client.post(
        "/api/assets",
        headers={"X-Operator-Token": "configured-token"},
        json={"asset_id": "greenhouse-rbac", "name": "RBAC Greenhouse"},
    )

    assert rejected.status_code == 401
    assert accepted.status_code == 201
    assert accepted.json()["asset_id"] == "greenhouse-rbac"


def test_recovery_approval_requires_operator_token_before_audit(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rbac-approval.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-rbac", "name": "Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-rbac", "metric": "temperature_c", "value": 91.0},
    )
    proposal_id = client.get("/api/recovery/proposals").json()["items"][0]["proposal_id"]

    response = client.post(
        f"/api/recovery/proposals/{proposal_id}/approve",
        json={"approved_by": "operator"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Operator token required"
    event_types = [
        item["event_type"] for item in client.get("/api/audit/events").json()["items"]
    ]
    assert "recovery.approved" not in event_types


def test_write_endpoint_accepts_configured_bearer_operator(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "bearer-rbac.db"))
    seed_bearer_assignment(client, monkeypatch)
    token = make_test_jwt()

    response = client.post(
        "/api/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": "greenhouse-bearer", "name": "Bearer Greenhouse"},
    )

    assert response.status_code == 201
    assert response.json()["asset_id"] == "greenhouse-bearer"


def test_write_endpoint_accepts_rs256_jwks_bearer_operator(
    tmp_path, monkeypatch
) -> None:
    token, public_key = make_test_rs256_jwt()
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
    client = TestClient(create_app(database_path=tmp_path / "bearer-rs-rbac.db"))
    seed_bearer_assignment(client, monkeypatch, subject="operator-rs256@example.test")

    response = client.post(
        "/api/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": "greenhouse-rs", "name": "RS Greenhouse"},
    )

    assert response.status_code == 201
    assert response.json()["asset_id"] == "greenhouse-rs"


def test_rs256_jwks_bearer_rejects_private_jwks_url(
    tmp_path, monkeypatch
) -> None:
    token, _public_key = make_test_rs256_jwt()
    rejected_urls = (
        "https://127.0.0.1/jwks.json",
        "https://[::1]/jwks.json",
        "https://169.254.169.254/latest/meta-data",
        "https://localhost/jwks.json",
        "https://user:pass@idp.example.test/jwks.json",
        "http://idp.example.test/jwks.json",
    )

    class BlockedJWKClient:
        def __init__(self, _url: str) -> None:
            raise AssertionError("unsafe JWKS URL must be rejected before fetch")

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setattr("agentiot.app.PyJWKClient", BlockedJWKClient)

    for index, jwks_url in enumerate(rejected_urls):
        monkeypatch.setenv("AGENTIOT_IDP_JWKS_URL", jwks_url)
        client = TestClient(create_app(database_path=tmp_path / f"jwks-{index}.db"))
        response = client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            json={"asset_id": f"greenhouse-jwks-{index}", "name": "Unsafe JWKS"},
        )

        assert response.status_code == 503, jwks_url
        assert response.json()["detail"] == "Identity provider not configured"
        assert jwks_url not in response.text


def test_rs256_jwks_bearer_rejects_dns_resolved_private_jwks_url(
    tmp_path, monkeypatch
) -> None:
    token, _public_key = make_test_rs256_jwt()
    private_resolutions = (
        "127.0.0.1",
        "10.0.0.5",
        "169.254.169.254",
        "fd00::1",
    )

    class BlockedJWKClient:
        def __init__(self, _url: str) -> None:
            raise AssertionError("DNS-unsafe JWKS URL must be rejected before fetch")

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_JWKS_URL", "https://jwks.example.test/jwks.json")
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setattr("agentiot.app.PyJWKClient", BlockedJWKClient)

    for index, address in enumerate(private_resolutions):
        monkeypatch.setattr(
            "agentiot.app.socket.getaddrinfo",
            lambda *_args, address=address, **_kwargs: [
                (None, None, None, None, (address, 443))
            ],
        )
        client = TestClient(create_app(database_path=tmp_path / f"jwks-dns-{index}.db"))
        response = client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            json={"asset_id": f"greenhouse-dns-{index}", "name": "Unsafe DNS"},
        )

        assert response.status_code == 503, address
        assert response.json()["detail"] == "Identity provider not configured"
        assert address not in response.text


def test_expired_bearer_token_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "expired-bearer.db"))
    token = make_test_jwt(expires_in=-1)

    response = client.post(
        "/api/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": "greenhouse-expired", "name": "Expired Greenhouse"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token expired"


def test_oidc_rejects_missing_exp_or_stable_subject(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "required-claims.db"))
    tokens = (
        make_test_jwt(include_exp=False),
        make_test_jwt(subject=None),
        make_test_jwt(subject=""),
        make_test_jwt(subject="   "),
        make_test_jwt(subject=None, preferred_username="legacy-operator"),
    )

    for index, token in enumerate(tokens):
        response = client.post(
            "/api/assets",
            headers={"Authorization": f"Bearer {token}"},
            json={"asset_id": f"invalid-claims-{index}", "name": "Invalid claims"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid bearer token"


def test_viewer_bearer_token_cannot_write_even_with_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "viewer-bearer.db"))
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="viewer-user",
        role="viewer",
        scopes=["device:write"],
    )
    token = make_test_jwt(subject="viewer-user", role="viewer", scope="device:write")

    response = client.post(
        "/api/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": "greenhouse-viewer", "name": "Viewer Greenhouse"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Scope required: device:write"


def test_admin_access_reads_require_admin_credential(tmp_path, monkeypatch) -> None:
    client = TestClient(create_app(database_path=tmp_path / "invalid-read-token.db"))

    anonymous_roles = client.get("/api/admin/access/roles")
    anonymous_users = client.get("/api/admin/access/users")
    rejected = client.get(
        "/api/admin/access/roles",
        headers={"X-Operator-Token": "invalid-token"},
    )
    accepted_roles = client.get(
        "/api/admin/access/roles",
        headers=admin_token_headers(monkeypatch),
    )

    assert anonymous_roles.status_code == 401
    assert anonymous_users.status_code == 401
    assert rejected.status_code == 401
    assert rejected.json()["detail"] == "Admin token or bearer required"
    assert accepted_roles.status_code == 200


def test_optional_admin_read_rejects_invalid_bearer_credential(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "invalid-read-bearer.db"))
    token = make_test_jwt(expires_in=-1)

    response = client.get(
        "/api/admin/agents",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token expired"
