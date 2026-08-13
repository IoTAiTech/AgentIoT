# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

import asyncio
import json
import re
import urllib.error
import urllib.request

from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError
import pytest

from agentiot.app import (
    AUTH_FAILURE_LIMIT,
    JWKS_RESPONSE_MAX_BYTES,
    NoJwksRedirectHandler,
    REQUEST_BODY_MAX_BYTES_ENV,
    SafePyJWKClient,
    create_app,
)
from conftest import (
    admin_token_headers,
    configure_offhost_restore_receipt,
    make_test_jwt,
    seed_bearer_assignment,
)


def invoke_asgi_post_without_client_content_length(
    app, body_chunks: list[bytes], extra_headers: list[tuple[bytes, bytes]] | None = None
) -> tuple[int, dict]:
    async def run_request() -> tuple[int, dict]:
        messages = [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(body_chunks) - 1,
            }
            for index, chunk in enumerate(body_chunks)
        ]
        sent: list[dict] = []
        headers = [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
        ]
        headers.extend(extra_headers or [])
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/chat",
            "raw_path": b"/api/chat",
            "query_string": b"",
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def receive() -> dict:
            if messages:
                return messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict) -> None:
            sent.append(message)

        await app(scope, receive, send)
        status = next(
            item["status"] for item in sent if item["type"] == "http.response.start"
        )
        body = b"".join(
            item.get("body", b"") for item in sent if item["type"] == "http.response.body"
        )
        return status, json.loads(body.decode("utf-8"))

    return asyncio.run(run_request())


def test_security_headers_are_present_on_browser_page(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "headers.db"))

    response = client.get("/")

    assert response.status_code == 200
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "connect-src 'self'" in csp
    assert "'unsafe-inline'" not in csp
    assert "unsafe-eval" not in csp
    nonce_match = re.search(r"script-src 'self' 'nonce-([^']+)'", csp)
    assert nonce_match is not None
    nonce = nonce_match.group(1)
    assert f"style-src 'self' 'nonce-{nonce}'" in csp
    assert response.text.count(f'nonce="{nonce}"') == 3
    assert re.search(r"\sstyle=", response.text) is None
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "geolocation=(), microphone=(), camera=()"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["cross-origin-embedder-policy"] == "require-corp"

    about = client.get("/about")
    assert about.status_code == 200
    assert "'unsafe-inline'" not in about.headers["content-security-policy"]
    assert re.search(r'<style nonce="[^"]+">', about.text)


def test_production_mode_disables_openapi_and_docs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app(database_path=tmp_path / "production.db"))

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/healthz").status_code == 200


def test_production_rejects_disallowed_host_header(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app(database_path=tmp_path / "trusted-host.db"))

    response = client.get("/healthz", headers={"host": "unexpected.example"})

    assert response.status_code == 400


def test_development_mode_keeps_openapi_for_engineering(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "development")
    client = TestClient(create_app(database_path=tmp_path / "development.db"))

    assert client.get("/openapi.json").status_code == 200


def test_security_status_reports_safe_public_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app(database_path=tmp_path / "security-status.db"))

    response = client.get("/api/security/status")

    assert response.status_code == 200
    body = response.json()
    assert body["operator_write_gate"] is True
    assert body["operator_token_configured"] is True
    assert body["production_mode"] is True
    assert body["openapi_enabled"] is False
    assert body["security_headers"]["content-security-policy"]
    assert body["security_headers"]["x-frame-options"] == "DENY"
    assert body["secret_delivery"]["operator_token"] == "environment"
    assert body["secret_delivery"]["admin_token"] == "not_configured"
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_security_status_reports_file_secret_delivery_without_values(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "development")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("AGENTIOT_ADMIN_TOKEN", raising=False)
    operator_secret = tmp_path / "operator-token"
    admin_secret = tmp_path / "admin-token"
    operator_secret.write_text("file-operator-token-value-strong-123456", encoding="utf-8")
    admin_secret.write_text("file-admin-token-value-strong-123456", encoding="utf-8")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN_FILE", str(operator_secret))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN_FILE", str(admin_secret))
    client = TestClient(create_app(database_path=tmp_path / "secret-file.db"))

    response = client.get("/api/security/status")

    assert response.status_code == 200
    body = response.json()
    assert body["operator_token_configured"] is True
    assert body["operator_token_strength"] == "strong"
    assert body["admin_token_strength"] == "strong"
    assert body["secret_delivery"]["operator_token"] == "secret_file"
    assert body["secret_delivery"]["admin_token"] == "secret_file"
    assert str(operator_secret) not in response.text
    assert str(admin_secret) not in response.text
    assert "file-operator-token-value-strong-123456" not in response.text
    assert "file-admin-token-value-strong-123456" not in response.text


def test_security_status_rejects_invalid_production_secret_path(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN_FILE", str(tmp_path / "blocked-token"))
    client = TestClient(create_app(database_path=tmp_path / "invalid-secret-file.db"))

    body = client.get("/api/security/status").json()

    assert body["operator_token_configured"] is False
    assert body["operator_token_strength"] == "not_configured"
    assert body["secret_delivery"]["operator_token"] == "invalid_file"


def test_production_mode_requires_trusted_host_allowlist(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.delenv("AGENTIOT_ALLOWED_HOSTS", raising=False)

    try:
        create_app(database_path=tmp_path / "missing-hosts.db")
    except RuntimeError as error:
        assert "AGENTIOT_ALLOWED_HOSTS" in str(error)
    else:
        raise AssertionError("production startup must require AGENTIOT_ALLOWED_HOSTS")


def test_cors_is_closed_until_origin_is_explicitly_allowed(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENTIOT_CORS_ALLOWED_ORIGINS", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "cors-closed.db"))

    response = client.get("/healthz", headers={"Origin": "https://portal.example.test"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_only_configured_origin(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTIOT_CORS_ALLOWED_ORIGINS", "https://portal.example.test"
    )
    client = TestClient(create_app(database_path=tmp_path / "cors-allowed.db"))

    allowed = client.get("/healthz", headers={"Origin": "https://portal.example.test"})
    blocked = client.get("/healthz", headers={"Origin": "https://evil.example.test"})

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://portal.example.test"
    assert blocked.status_code == 200
    assert "access-control-allow-origin" not in blocked.headers


def test_cors_allows_put_for_model_service_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTIOT_CORS_ALLOWED_ORIGINS", "https://portal.example.test"
    )
    client = TestClient(create_app(database_path=tmp_path / "cors-put.db"))

    response = client.options(
        "/api/admin/ai/model-services/openai/credentials",
        headers={
            "Origin": "https://portal.example.test",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "Content-Type,X-Admin-Token",
        },
    )

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]


def test_production_rejects_wildcard_cors_origin(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_CORS_ALLOWED_ORIGINS", "*")

    try:
        create_app(database_path=tmp_path / "cors-wildcard.db")
    except RuntimeError as error:
        assert "Wildcard CORS origin" in str(error)
    else:
        raise AssertionError("production startup must reject wildcard CORS")


def test_write_request_over_body_limit_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(REQUEST_BODY_MAX_BYTES_ENV, "128")
    client = TestClient(create_app(database_path=tmp_path / "body-limit.db"))

    response = client.post("/api/chat", json={"message": "x" * 512})

    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large"


def test_small_write_request_under_body_limit_is_allowed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(REQUEST_BODY_MAX_BYTES_ENV, "512")
    client = TestClient(create_app(database_path=tmp_path / "body-limit-small.db"))

    response = client.post("/api/chat", json={"message": "status"})

    assert response.status_code == 200
    assert response.json()["answer"]


def test_chunked_write_request_without_content_length_is_limited(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv(REQUEST_BODY_MAX_BYTES_ENV, "128")
    app = create_app(database_path=tmp_path / "body-limit-chunked.db")
    body = json.dumps({"message": "x" * 512}).encode("utf-8")

    status, payload = invoke_asgi_post_without_client_content_length(
        app, [body[:64], body[64:]]
    )

    assert status == 413
    assert payload["detail"] == "Request body too large"


def test_misstated_small_content_length_is_still_stream_limited(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv(REQUEST_BODY_MAX_BYTES_ENV, "128")
    app = create_app(database_path=tmp_path / "body-limit-misstated.db")
    body = json.dumps({"message": "x" * 512}).encode("utf-8")

    status, payload = invoke_asgi_post_without_client_content_length(
        app, [body[:32], body[32:]], extra_headers=[(b"content-length", b"10")]
    )

    assert status == 413
    assert payload["detail"] == "Request body too large"


def test_invalid_body_limit_configuration_fails_startup(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(REQUEST_BODY_MAX_BYTES_ENV, "0")

    try:
        create_app(database_path=tmp_path / "body-limit-invalid.db")
    except RuntimeError as error:
        assert REQUEST_BODY_MAX_BYTES_ENV in str(error)
    else:
        raise AssertionError("startup must reject an invalid request body limit")


def test_readyz_reports_database_and_operator_token_state(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ready.db"))

    response = client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["database_persistent"] is True
    assert body["database_path_configured"] is True
    assert body["runtime_mode"] == "development"
    assert body["operator_token_configured"] is True
    assert body["identity_provider_configured"] is False


def test_readyz_accepts_identity_provider_without_operator_token(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "ready-idp.db"))

    response = client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["operator_token_configured"] is True
    assert body["identity_provider_configured"] is True


def test_identity_provider_accepts_file_backed_shared_secret_for_writes(
    tmp_path, monkeypatch
) -> None:
    idp_key = "".join(("file-backed-", "idp-validation-key"))
    secret_file = tmp_path / "idp_shared_secret"
    secret_file.write_text(idp_key, encoding="utf-8")
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET_FILE", str(secret_file))
    client = TestClient(create_app(database_path=tmp_path / "idp-secret-file.db"))
    seed_bearer_assignment(client, monkeypatch)
    token = make_test_jwt(secret=idp_key)

    response = client.post(
        "/api/assets",
        headers={"Authorization": f"Bearer {token}"},
        json={"asset_id": "idp-secret-file-asset", "name": "IDP File Asset"},
    )
    ready = client.get("/readyz")

    assert response.status_code == 201
    assert ready.json()["identity_provider_configured"] is True
    assert idp_key not in response.text
    assert str(secret_file) not in ready.text


def test_production_rejects_identity_secret_file_outside_runtime_mount(
    tmp_path, monkeypatch
) -> None:
    secret_file = tmp_path / "idp_shared_secret"
    secret_file.write_text("unsafe-idp-secret", encoding="utf-8")
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET_FILE", str(secret_file))
    client = TestClient(create_app(database_path=tmp_path / "idp-prod-secret.db"))

    ready = client.get("/readyz")
    access = client.get("/api/access/policy")

    assert ready.json()["identity_provider_configured"] is False
    assert access.json()["identity_provider"]["shared_secret_configured"] is False
    assert "unsafe-idp-secret" not in ready.text
    assert str(secret_file) not in access.text


def test_production_readyz_rejects_weak_operator_token_without_identity(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.delenv("AGENTIOT_IDP_ISSUER", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_AUDIENCE", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_JWKS_URL", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "ready-weak-token.db"))

    ready = client.get("/readyz")
    security = client.get("/api/security/status")

    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert security.status_code == 200
    assert security.json()["operator_token_strength"] == "weak"
    assert "unit-" + "operator-" + "sentinel" not in security.text


def test_production_rejects_matching_weak_operator_token_without_writes(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    app = create_app(database_path=tmp_path / "weak-operator-token.db")
    client = TestClient(app)

    rejected = client.post(
        "/api/assets",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
        json={"asset_id": "blocked-asset", "name": "Blocked Asset"},
    )

    assert rejected.status_code == 503
    assert rejected.json()["detail"] == "Operator authentication unavailable"
    assert app.state.store.list_rows("assets") == []


def test_production_rejects_weak_admin_token_for_control_plane_actions(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "strong-runtime-token-" + ("a" * 64))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-" + "admin-" + "sentinel")
    monkeypatch.delenv("AGENTIOT_IDP_ISSUER", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_AUDIENCE", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_JWKS_URL", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "weak-admin-token.db"))

    ready = client.get("/readyz")
    security = client.get("/api/security/status")
    rejected = client.get(
        "/api/admin/production/action-plan",
        headers={"X-Admin-Token": "unit-" + "admin-" + "sentinel"},
    )

    assert ready.status_code == 503
    assert ready.json()["status"] == "not_ready"
    assert security.status_code == 200
    assert security.json()["admin_token_strength"] == "weak"
    assert rejected.status_code == 503
    assert rejected.json()["detail"] == "Admin authentication unavailable"
    assert "unit-" + "admin-" + "sentinel" not in rejected.text


def test_production_accepts_a_strong_admin_token_for_control_plane_actions(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "strong-runtime-token-" + ("a" * 64))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-admin-token-" + ("b" * 64))
    monkeypatch.delenv("AGENTIOT_IDP_ISSUER", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_AUDIENCE", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_JWKS_URL", raising=False)
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    client = TestClient(create_app(database_path=tmp_path / "strong-admin-token.db"))

    ready = client.get("/readyz")
    accepted = client.get(
        "/api/admin/production/action-plan",
        headers={"X-Admin-Token": "strong-admin-token-" + ("b" * 64)},
    )

    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert accepted.status_code == 200


def test_production_readyz_accepts_strong_operator_token_without_identity(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "strong-runtime-token-" + ("a" * 64))
    monkeypatch.delenv("AGENTIOT_IDP_ISSUER", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_AUDIENCE", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_JWKS_URL", raising=False)
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    client = TestClient(create_app(database_path=tmp_path / "ready-strong-token.db"))

    ready = client.get("/readyz")
    security = client.get("/api/security/status")

    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["database_persistent"] is True
    assert security.status_code == 200
    assert security.json()["operator_token_strength"] == "strong"


def test_production_readyz_requires_persistent_database_path(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "strong-runtime-token-" + ("a" * 64))
    monkeypatch.delenv("AGENTIOT_DB_PATH", raising=False)
    client = TestClient(create_app())

    ready = client.get("/readyz")

    assert ready.status_code == 503
    body = ready.json()
    assert body["status"] == "not_ready"
    assert body["database"] == "ok"
    assert body["database_persistent"] is False
    assert body["database_path_configured"] is False


def test_private_or_http_jwks_url_is_not_configured(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    rejected_urls = (
        "http://127.0.0.1/jwks.json",
        "https://[::1]/jwks.json",
        "https://169.254.169.254/latest/meta-data",
        "https://localhost/jwks.json",
        "https://user:pass@idp.example.test/jwks.json",
        "https://idp.example.test/" + ("a" * 230),
    )

    for index, jwks_url in enumerate(rejected_urls):
        monkeypatch.setenv("AGENTIOT_IDP_JWKS_URL", jwks_url)
        client = TestClient(create_app(database_path=tmp_path / f"ready-jwks-{index}.db"))

        ready = client.get("/readyz")
        access = client.get("/api/access/policy")

        assert ready.status_code == 503
        assert ready.json()["identity_provider_configured"] is False
        assert access.status_code == 200
        assert access.json()["identity_provider"]["state"] == "not_configured"
        assert access.json()["identity_provider"]["jwks_configured"] is False
        assert access.json()["identity_provider"]["jwks_security_state"] == "rejected"
        assert jwks_url not in access.text


def test_dns_resolved_private_jwks_url_is_not_configured(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_JWKS_URL", "https://jwks.example.test/jwks.json")
    monkeypatch.setattr(
        "agentiot.app.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("10.0.0.5", 443))],
    )
    client = TestClient(create_app(database_path=tmp_path / "ready-dns-jwks.db"))

    ready = client.get("/readyz")
    access = client.get("/api/access/policy")

    assert ready.status_code == 503
    assert ready.json()["identity_provider_configured"] is False
    assert access.status_code == 200
    assert access.json()["identity_provider"]["state"] == "not_configured"
    assert access.json()["identity_provider"]["jwks_security_state"] == "rejected"
    assert "10.0.0.5" not in access.text


class FakeJwksResponse:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self.payload = payload
        self.headers = {"content-type": content_type}

    def __enter__(self) -> "FakeJwksResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.payload


class FakeJwksOpener:
    def __init__(self, payload: bytes, content_type: str) -> None:
        self.payload = payload
        self.content_type = content_type

    def open(self, request, timeout: int) -> FakeJwksResponse:
        assert request.full_url == "https://jwks.example.test/jwks.json"
        assert timeout == 1
        return FakeJwksResponse(self.payload, self.content_type)


def mock_public_jwks_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        "agentiot.app.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )


def test_jwks_redirect_handler_blocks_redirect_without_target_leak() -> None:
    handler = NoJwksRedirectHandler()
    request = urllib.request.Request("https://jwks.example.test/jwks.json")

    with pytest.raises(urllib.error.HTTPError) as error:
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://127.0.0.1/jwks.json",
        )

    assert error.value.code == 302
    assert "127.0.0.1" not in str(error.value)


def test_safe_jwks_client_fetches_bounded_json(monkeypatch) -> None:
    mock_public_jwks_dns(monkeypatch)
    monkeypatch.setattr(
        "agentiot.app.urllib.request.build_opener",
        lambda *_handlers: FakeJwksOpener(b'{"keys":[]}', "application/json"),
    )

    data = SafePyJWKClient(
        "https://jwks.example.test/jwks.json",
        timeout=1,
    ).fetch_data()

    assert data == {"keys": []}


def test_safe_jwks_client_disables_ambient_proxy_handlers(monkeypatch) -> None:
    mock_public_jwks_dns(monkeypatch)
    captured_handlers: list[object] = []

    def fake_build_opener(*handlers):
        captured_handlers.extend(handlers)
        return FakeJwksOpener(b'{"keys":[]}', "application/json")

    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.test:8080")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example.test:8080")
    monkeypatch.setattr("agentiot.app.urllib.request.build_opener", fake_build_opener)

    data = SafePyJWKClient(
        "https://jwks.example.test/jwks.json",
        timeout=1,
    ).fetch_data()

    assert data == {"keys": []}
    proxy_handlers = [
        handler
        for handler in captured_handlers
        if handler.__class__.__name__ == "ProxyHandler"
    ]
    assert proxy_handlers
    assert proxy_handlers[0].proxies == {}


def test_safe_jwks_client_rejects_non_json_without_url_leak(monkeypatch) -> None:
    mock_public_jwks_dns(monkeypatch)
    monkeypatch.setattr(
        "agentiot.app.urllib.request.build_opener",
        lambda *_handlers: FakeJwksOpener(b"<html></html>", "text/html"),
    )

    with pytest.raises(PyJWKClientConnectionError) as error:
        SafePyJWKClient(
            "https://jwks.example.test/jwks.json",
            timeout=1,
        ).fetch_data()

    assert "JWKS fetch failed" in str(error.value)
    assert "jwks.example.test" not in str(error.value)


def test_safe_jwks_client_does_not_cache_failed_fetch(monkeypatch) -> None:
    mock_public_jwks_dns(monkeypatch)
    cached_values: list[object] = []

    class RecordingCache:
        def put(self, value: object) -> None:
            cached_values.append(value)

    monkeypatch.setattr(
        "agentiot.app.urllib.request.build_opener",
        lambda *_handlers: FakeJwksOpener(b"<html></html>", "text/html"),
    )
    client = SafePyJWKClient(
        "https://jwks.example.test/jwks.json",
        timeout=1,
    )
    client.jwk_set_cache = RecordingCache()

    with pytest.raises(PyJWKClientConnectionError):
        client.fetch_data()

    assert cached_values == []


def test_safe_jwks_client_rejects_oversized_body_without_url_leak(monkeypatch) -> None:
    mock_public_jwks_dns(monkeypatch)
    monkeypatch.setattr(
        "agentiot.app.urllib.request.build_opener",
        lambda *_handlers: FakeJwksOpener(
            b"x" * (JWKS_RESPONSE_MAX_BYTES + 1),
            "application/json",
        ),
    )

    with pytest.raises(PyJWKClientConnectionError) as error:
        SafePyJWKClient(
            "https://jwks.example.test/jwks.json",
            timeout=1,
        ).fetch_data()

    assert "JWKS fetch failed" in str(error.value)
    assert "jwks.example.test" not in str(error.value)


def test_failed_operator_auth_is_rate_limited(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "auth-rate-limit.db"))

    for attempt in range(AUTH_FAILURE_LIMIT):
        response = client.post(
            "/api/assets",
            headers={"X-Operator-Token": f"wrong-{attempt}"},
            json={"asset_id": f"blocked-{attempt}", "name": "Blocked"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/assets",
        headers={"X-Operator-Token": "wrong-limited"},
        json={"asset_id": "blocked-limited", "name": "Blocked"},
    )

    assert limited.status_code == 429
    assert limited.json()["detail"] == "Authentication rate limit exceeded"


def test_readyz_accepts_operator_token_file_without_exposing_secret(
    tmp_path, monkeypatch
) -> None:
    token_file = tmp_path / "operator.token"
    token_file.write_text("file-operator-token", encoding="utf-8")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN_FILE", str(token_file))
    client = TestClient(create_app(database_path=tmp_path / "ready-token-file.db"))

    response = client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["operator_token_configured"] is True
    assert body["identity_provider_configured"] is False
    assert "file-operator-token" not in response.text


def test_production_rejects_secret_file_outside_runtime_secret_mount(
    tmp_path, monkeypatch
) -> None:
    token_file = tmp_path / "operator.token"
    token_file.write_text("file-operator-token", encoding="utf-8")
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_SHARED_SECRET", raising=False)
    monkeypatch.delenv("AGENTIOT_IDP_JWKS_URL", raising=False)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN_FILE", str(token_file))
    client = TestClient(create_app(database_path=tmp_path / "ready-token-file-prod.db"))

    response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["operator_token_configured"] is False
    assert "file-operator-token" not in response.text


def test_operator_token_file_authorizes_write_without_exposing_secret(
    tmp_path, monkeypatch
) -> None:
    token_file = tmp_path / "operator.token"
    token_file.write_text("file-operator-token", encoding="utf-8")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN_FILE", str(token_file))
    client = TestClient(create_app(database_path=tmp_path / "write-token-file.db"))

    response = client.post(
        "/api/qa/continuous-mission",
        headers={"X-Operator-Token": "file-operator-token"},
        json={"duration_minutes": 60, "question_rounds": 60},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert "file-operator-token" not in response.text


def test_operator_token_file_runs_runtime_evidence_routes_without_exposing_secret(
    tmp_path,
    monkeypatch,
) -> None:
    runtime_value = "file-" + "runtime-" + "token-" + ("a" * 40)
    token_file = tmp_path / "operator.token"
    token_file.write_text(runtime_value, encoding="utf-8")
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN_FILE", str(token_file))
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    monkeypatch.setattr(
        "agentiot.app.source_worktree_state",
        lambda: {
            "state": "clean",
            "dirty": False,
            "git_available": True,
            "changed_tracked_file_count": 0,
            "checked_path_count": 10,
            "scope": "tracked_delivery_sources",
        },
    )
    client = TestClient(create_app(database_path=tmp_path / "runtime-routes.db"))
    headers = {"X-Operator-Token": runtime_value}

    release = client.post("/api/release/mission/run", headers=headers, json={})
    qa = client.post(
        "/api/qa/challenge-runs",
        headers=headers,
        json={"profile": "grounded-operations", "cases": 8},
    )
    drift = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": True},
    )
    audit = client.get("/api/audit/events")

    assert release.status_code == 201
    assert release.json()["status"] == "completed"
    assert qa.status_code == 201
    assert qa.json()["status"] == "completed"
    assert drift.status_code == 200
    assert drift.json()["review_result"] == "PASS"
    for response in (release, qa, drift, audit):
        assert runtime_value not in response.text


def test_drift_control_run_rejects_report_read_only_bearer_scope(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "drift-read-scope.db"))
    seed_bearer_assignment(client, monkeypatch, scopes=["report:read"])
    read_only_token = make_test_jwt(scope="report:read")

    response = client.post(
        "/api/project/drift-control/run",
        headers={"Authorization": f"Bearer {read_only_token}"},
        json={"force": True},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Scope required: agent:run"


def test_drift_control_run_accepts_agent_run_bearer_scope(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "drift-run-scope.db"))
    seed_bearer_assignment(client, monkeypatch, scopes=["agent:run"])
    run_token = make_test_jwt(scope="agent:run")

    response = client.post(
        "/api/project/drift-control/run",
        headers={"Authorization": f"Bearer {run_token}"},
        json={"force": True},
    )

    assert response.status_code == 200
    assert response.json()["recording"]["status"] == "recorded"


def test_gap_discovery_run_rejects_report_read_only_bearer_scope(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "gap-read-scope.db"))
    seed_bearer_assignment(client, monkeypatch, scopes=["report:read"])
    read_only_token = make_test_jwt(scope="report:read")

    response = client.post(
        "/api/project/gap-discovery/run",
        headers={"Authorization": f"Bearer {read_only_token}"},
        json={"force": True},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Scope required: agent:run"


def test_gap_discovery_run_accepts_agent_run_bearer_scope(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "gap-run-scope.db"))
    seed_bearer_assignment(client, monkeypatch, scopes=["agent:run"])
    run_token = make_test_jwt(scope="agent:run")

    response = client.post(
        "/api/project/gap-discovery/run",
        headers={"Authorization": f"Bearer {run_token}"},
        json={"force": True},
    )

    assert response.status_code == 200
    assert response.json()["recording"]["status"] == "recorded"


def test_demo_reset_is_disabled_in_production(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    strong_operator_token = "strong-runtime-token-" + ("a" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", strong_operator_token)
    client = TestClient(create_app(database_path=tmp_path / "reset-production.db"))

    response = client.post(
        "/api/demo/reset",
        headers={"X-Operator-Token": strong_operator_token},
        json={"confirmed_by": "operator"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Demo reset is disabled in production"


def test_public_surfaces_redact_control_plane_internals(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "public-redaction.db"))
    headers = admin_token_headers(monkeypatch)
    marker = "Redaction regression marker for managed agent playbook."

    update = client.patch(
        "/api/admin/agents/operations_coordinator",
        headers=headers,
        json={"instruction_template": marker},
    )
    assert update.status_code == 200
    assert marker in update.text

    protected_read_paths = (
        "/api/admin/agents",
        "/api/admin/agents/prompt-contracts",
        "/api/admin/agents/operations_coordinator/prompt-contract/history",
        "/api/admin/prompts",
        "/api/admin/prompts/assistant.system.default",
    )
    public_paths = (
        "/api/reports/dashboard",
        "/api/operations/evidence",
        "/api/delivery/evidence-pack",
        "/api/release/evidence-console",
        "/api/assistant/quality-report",
        "/api/assistant/workbench",
        "/api/assistant/coworker-quality",
        "/api/assistant/sessions",
        "/api/assistant/bdd-suggestions",
        "/api/audit/events",
    )
    forbidden_home = "/" + "home" + "/" + "iot"
    forbidden_host = ".".join(["192", "168", "50", "40"])
    blocked_fragments = (
        marker,
        "admin@example.test",
        forbidden_home,
        forbidden_host,
        "unit-" + "operator-" + "sentinel",
        "sk" + "-proj",
    )

    for path in protected_read_paths:
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.json()["detail"] in {
            "Operator token required",
            "Admin token or bearer required",
        }

    for path in public_paths:
        response = client.get(path)
        assert response.status_code == 200, path
        body = response.text
        for fragment in blocked_fragments:
            assert fragment not in body, path

    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="agent-redaction-reader",
        scopes=["agent:read"],
    )
    read_token = make_test_jwt(subject="agent-redaction-reader", scope="agent:read")
    reader_headers = {"Authorization": f"Bearer {read_token}"}
    read_agents = client.get("/api/admin/agents", headers=reader_headers).json()
    assert read_agents["detail_level"] == "customer_safe_summary"
    assert all(agent["playbook_redacted"] for agent in read_agents["agents"])
    assert all(
        agent["instruction_template"] == "redacted_public_view"
        for agent in read_agents["agents"]
    )
    read_contracts = client.get(
        "/api/admin/agents/prompt-contracts", headers=reader_headers
    )
    assert read_contracts.status_code == 200
    for fragment in blocked_fragments:
        assert fragment not in read_contracts.text

    public_audit = client.get("/api/audit/events").json()["items"]
    assert set(public_audit[-1]) == {"event_type", "created_at"}

    admin_agents = client.get(
        "/api/admin/agents",
        headers=headers,
    ).json()
    assert admin_agents["detail_level"] == "full"
    assert marker in str(admin_agents)


def test_sensitive_operational_collections_require_operator_read_scope(
    tmp_path, monkeypatch
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "collection-read-scope.db"))
    operator_headers = {"X-Operator-Token": "unit-operator-sentinel"}

    for path in (
        "/api/agents/tasks",
        "/api/ai/evaluations/runs",
        "/api/evidence/findings",
    ):
        assert client.get(path).status_code == 401, path
        scoped = client.get(path, headers=operator_headers)
        assert scoped.status_code == 200, path
        assert scoped.json()["items"] == []

    for index in range(14):
        response = client.post(
            "/api/devices",
            headers=operator_headers,
            json={"device_id": f"audit-device-{index}", "name": f"Device {index}"},
        )
        assert response.status_code == 201

    list_rows_calls: list[str] = []
    original_list_rows = client.app.state.store.list_rows

    def tracked_list_rows(table: str):
        list_rows_calls.append(table)
        return original_list_rows(table)

    monkeypatch.setattr(client.app.state.store, "list_rows", tracked_list_rows)
    public_audit = client.get("/api/audit/events")
    assert public_audit.status_code == 200
    assert "audit_events" not in list_rows_calls
    assert len(public_audit.json()["items"]) == 12
    assert all(
        set(item) == {"event_type", "created_at"}
        for item in public_audit.json()["items"]
    )

    scoped_audit = client.get(
        "/api/audit/events?limit=5",
        headers=operator_headers,
    )
    assert scoped_audit.status_code == 200
    assert list_rows_calls == []
    first_page = scoped_audit.json()
    assert len(first_page["items"]) == 5
    assert isinstance(first_page["next_cursor"], int)
    assert all("actor" in item and "detail" in item for item in first_page["items"])

    second_page = client.get(
        f"/api/audit/events?limit=5&before_id={first_page['next_cursor']}",
        headers=operator_headers,
    )
    assert second_page.status_code == 200
    assert list_rows_calls == []
    second_items = second_page.json()["items"]
    assert len(second_items) == 5
    assert {
        item["audit_event_id"] for item in first_page["items"]
    }.isdisjoint({item["audit_event_id"] for item in second_items})

    oversized_page = client.get(
        "/api/audit/events?limit=201",
        headers=operator_headers,
    )
    assert oversized_page.status_code == 422


def test_viewer_audit_access_is_server_redacted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "viewer-audit.db"))
    operator_headers = {"X-Operator-Token": "unit-operator-sentinel"}
    created = client.post(
        "/api/devices",
        headers=operator_headers,
        json={"device_id": "viewer-audit-device", "name": "Viewer audit device"},
    )
    assert created.status_code == 201
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="viewer-audit-user",
        role="viewer",
        scopes=["report:read"],
    )
    token = make_test_jwt(
        subject="viewer-audit-user",
        role="viewer",
        scope="report:read",
    )

    response = client.get(
        "/api/audit/events?limit=25",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["next_cursor"] is None
    assert payload["items"]
    assert all(set(item) == {"event_type", "created_at"} for item in payload["items"])


def test_production_public_admin_and_assistant_surfaces_are_redacted(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    strong_operator_token = "strong-runtime-token-" + ("a" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", strong_operator_token)
    client = TestClient(create_app(database_path=tmp_path / "production-redaction.db"))

    preview = client.post("/api/chat", json={"message": "public redaction check"})
    assert preview.status_code == 401
    assert preview.json()["detail"] == "Operator token required"
    chat = client.post(
        "/api/chat",
        headers={"X-Operator-Token": strong_operator_token},
        json={"message": "operator redaction check"},
    )
    assert chat.status_code == 200
    assert chat.json()["session"]["persistence"]["ledger_written"] is True

    admin_model_services = client.get("/api/admin/ai/model-services")
    assert admin_model_services.status_code == 401
    admin_access_roles = client.get("/api/admin/access/roles")
    admin_access_users = client.get("/api/admin/access/users")
    assert admin_access_roles.status_code == 401
    assert admin_access_users.status_code == 401

    model_services = client.get("/api/ai/model-services")
    assert model_services.status_code == 200
    model_body = model_services.json()
    assert model_body["credentials"]
    assert all(item["detail_level"] == "customer_safe_summary" for item in model_body["credentials"])
    assert "api_key_fingerprint" not in model_services.text
    assert "api_key_env_var" not in model_services.text
    assert "password_env_var" not in model_services.text
    assert "updated_by" not in model_services.text
    assert model_body["privacy"]["credential_fingerprints_returned"] is False
    assert model_body["privacy"]["credential_env_refs_returned"] is False

    ledger = client.get("/api/assistant/interactions")
    assert ledger.status_code == 200
    ledger_body = ledger.json()
    assert ledger_body["summary"]["total"] == 1
    assert '"prompt_hash":' not in ledger.text
    assert '"session_id":' not in ledger.text
    assert '"message_id":' not in ledger.text
    assert "actor" not in ledger.text
    assert ledger_body["privacy"]["prompt_hash_returned"] == "false"

    gap = client.get("/api/release/gap-closure-console")
    assert gap.status_code == 200
    gap_body = gap.json()
    assert all(
        item["run_endpoint"] == "redacted_operator_view"
        for item in gap_body["gate_closure_plan"]
    )
    assert "safe_command" not in gap.text
    assert "X-Operator-Token" not in gap.text
    assert '"request_body":' not in gap.text
    assert gap_body["privacy"]["operator_runbook_returned"] == "false"
