# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

"""AI model credential, token ledger, and memory-governance tests."""

import json
import os
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import agentiot.app as app_module
from agentiot.app import create_app
from agentiot.version import __version__


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def admin_headers() -> dict[str, str]:
    """Return bootstrap admin-token headers for control-plane tests."""

    os.environ["AGENTIOT_ADMIN_TOKEN"] = "unit-admin-sentinel"
    return {"X-Admin-Token": "unit-admin-sentinel"}


def test_dashboard_forms_never_default_to_get_submission() -> None:
    html = (
        Path(__file__).resolve().parents[1] / "src/agentiot/root_page.html"
    ).read_text(encoding="utf-8")

    form_tags = re.findall(r"<form\b[^>]*>", html)

    assert len(form_tags) >= 30
    assert all('method="post"' in tag for tag in form_tags)
    assert all('action="/settings"' in tag for tag in form_tags)


def configure_idp(monkeypatch) -> None:
    """Enable deterministic local JWT validation for admin tests."""

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")


def configure_public_model_dns(monkeypatch, host: str = "models.example.test") -> None:
    """Resolve test model endpoints to a public documentation address."""

    def public_getaddrinfo(requested_host, port, *args, **kwargs):
        assert requested_host == host
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", port),
            )
        ]

    monkeypatch.setattr(app_module.socket, "getaddrinfo", public_getaddrinfo)


def seed_chat_grounding(client: TestClient, device_id: str = "sensor-token") -> None:
    """Create small runtime evidence for grounded assistant chat tests."""

    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": device_id, "name": "Token Ledger Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": device_id, "metric": "temperature_c", "value": 88.0},
    )


def test_model_services_expose_required_token_windows_without_payloads(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "model-windows.db"))

    response = client.get("/api/ai/resource-governance")
    service_response = client.get("/api/ai/model-services")
    alias_response = client.get("/api/ai/model-resource-governance")

    assert response.status_code == 200
    assert service_response.status_code == 200
    assert alias_response.status_code == 200
    body = response.json()
    service_body = service_response.json()
    alias_body = alias_response.json()
    assert service_body["credentials"] == body["credentials"]
    assert service_body["token_usage"] == body["token_usage"]
    assert service_body["memory_policy"] == body["memory_policy"]
    assert service_body["privacy"] == body["privacy"]
    assert alias_body["token_usage"] == body["token_usage"]
    assert alias_body["memory_policy"] == body["memory_policy"]
    assert alias_body["privacy"] == body["privacy"]
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["privacy"]["secret_values_returned"] is False
    assert body["privacy"]["raw_prompt_returned"] is False
    assert body["privacy"]["provider_payload_returned"] is False
    assert [item["window"] for item in body["token_usage"]["windows"]] == [
        "1h",
        "6h",
        "12h",
        "24h",
        "2d",
        "7d",
        "14d",
        "30d",
        "3mo",
        "6mo",
        "12mo",
    ]
    assert body["token_usage"]["summary"]["storage_policy"] == (
        "token_counts_only_no_prompt_or_answer"
    )
    assert all(item["total_tokens"] == 0 for item in body["token_usage"]["windows"])
    assert body["memory_policy"]["source"] == "default"
    assert body["memory_policy"]["retention_days"] == 30
    assert body["memory_policy"]["max_memory_mb"] >= body["recommendation"]["recommended_max_memory_mb"]
    assert body["recommendation"]["status"] == "ready"
    assert body["recommendation"]["action"] == "Keep current memory policy"
    assert body["recommendation"]["growth_control"] == {
        "prompt_storage": "hash_only",
        "answer_storage": "not_stored",
        "token_storage": "counts_only",
        "provider_payload_storage": "not_stored",
        "auto_prune": True,
    }
    assert body["runtime_configuration"] == {
        "credential_encryption_configured": False,
        "local_calls_enabled": False,
        "cloud_calls_enabled": False,
        "local_model_configured": False,
        "cloud_provider_configured": False,
        "detail_level": "customer_safe_summary",
        "runtime_claim": "provider_calls_gated",
    }
    assert all(
        item["detail_level"] == "customer_safe_summary"
        for item in body["credentials"]
    )
    assert "api_key_fingerprint" not in response.text
    assert "api_key_env_var" not in response.text
    assert "updated_by" not in response.text
    assert "sk-" not in json.dumps(body).lower()


def test_admin_ai_read_routes_require_admin_and_public_aliases_are_safe(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "admin-ai-read.db"))

    assert client.get("/api/admin/ai/provider-policy").status_code == 401
    assert client.get("/api/admin/ai/model-services").status_code == 401

    public_services = client.get("/api/ai/model-services")
    routing = client.get("/api/ai/routing")
    admin_policy = client.get(
        "/api/admin/ai/provider-policy", headers=admin_headers()
    )
    admin_services = client.get(
        "/api/admin/ai/model-services", headers=admin_headers()
    )

    assert public_services.status_code == 200
    assert routing.status_code == 200
    assert admin_policy.status_code == 200
    assert admin_services.status_code == 200
    public_policy = routing.json()["provider_policy"]
    assert "updated_by" not in public_policy
    assert public_policy["detail_level"] == "customer_safe_summary"
    assert public_policy["credential_values"] == "not_returned"
    assert "/api/admin/agents" not in public_policy["allowed_tools"]


def test_ai_provider_policy_rejects_unapproved_tool_endpoints(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ai-tool-allowlist.db"))
    base_payload = {
        "provider": "grounded_fallback",
        "model": "not_configured",
        "quality_profile": "grounded-operations",
        "max_context_chars": 6000,
        "grounding_required": True,
        "runtime_enabled": False,
    }

    accepted = client.patch(
        "/api/admin/ai/provider-policy",
        headers=admin_headers(),
        json={
            **base_payload,
            "allowed_tools": ["/api/operations/summary", "/api/ai/routing"],
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["policy"]["allowed_tools"] == [
        "/api/operations/summary",
        "/api/ai/routing",
    ]

    for unsafe_endpoint in [
        "/api/admin/ai/model-services",
        "/api/admin/agents",
        "/api/assets",
        "/api/devices",
        "/api/telemetry",
        "/api/recovery/proposals/proposal-1/approve",
        "/api/assistant/tool-proposals/proposal-1/approve",
    ]:
        rejected = client.patch(
            "/api/admin/ai/provider-policy",
            headers=admin_headers(),
            json={**base_payload, "allowed_tools": [unsafe_endpoint]},
        )
        assert rejected.status_code == 400
        assert rejected.json()["detail"] == "Unsupported AI provider tool endpoint"

    routing = client.get("/api/ai/routing").json()
    assert routing["provider_policy"]["allowed_tools"] == [
        "/api/operations/summary",
        "/api/ai/routing",
    ]


def test_ai_model_route_preflight_exposes_actionable_gates_without_secret_leak(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    monkeypatch.setenv("AGENTIOT_AI_ALLOW_CLOUD_CALLS", "true")
    client = TestClient(create_app(database_path=tmp_path / "model-preflight.db"))

    credential = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://api.openai.com/v1/responses",
            "api_key": "provider-auth-sentinel",
        },
    )
    policy = client.patch(
        "/api/admin/ai/provider-policy",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-5.5",
            "quality_profile": "copilot-grade-operations",
            "max_context_chars": 6000,
            "grounding_required": True,
            "runtime_enabled": True,
            "allowed_tools": ["/api/operations/summary", "/api/rag/search"],
        },
    )
    response = client.get("/api/ai/model-route-preflight")

    assert credential.status_code == 200
    assert policy.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["status"] == "review_required"
    assert body["summary"]["active_provider"] == "openai"
    assert body["summary"]["active_model"] == "gpt-5.5"
    assert body["summary"]["credential_ready"] is True
    assert body["summary"]["runtime_gate_ready"] is True
    assert body["summary"]["activation_check_ready"] is False
    assert body["summary"]["provider_route_ready"] is False
    assert body["summary"]["route_decision_ready"] is False
    assert body["summary"]["token_windows"] == 11
    assert body["summary"]["memory_policy_status"] == "ready"
    assert body["summary"]["next_gate"] == "run_activation_check"
    active_provider = next(
        item for item in body["providers"] if item["provider"] == "openai"
    )
    assert active_provider["selected"] is True
    assert active_provider["gates"]["credential"]["state"] == "ready"
    assert active_provider["gates"]["runtime"]["state"] == "ready"
    assert active_provider["gates"]["activation_check"]["state"] == "review_required"
    assert active_provider["gates"]["activation_check"]["blocking_gates"] == [
        "connectivity_check_not_run"
    ]
    action_ids = [item["action_id"] for item in body["actions"]]
    assert action_ids[:2] == [
        "run-openai-activation-check",
        "record-ai-route-owner-decision",
    ]
    owner_decision_action = next(
        item
        for item in body["actions"]
        if item["action_id"] == "record-ai-route-owner-decision"
    )
    assert owner_decision_action["owner_agent_id"] == "project_delivery_coordinator"
    assert owner_decision_action["endpoint"] == "/api/production/approval-package"
    serialized = json.dumps(body).lower()
    assert "provider-auth-sentinel" not in serialized
    assert "sk-" not in serialized
    assert body["privacy"] == {
        "customer_safe": True,
        "secret_values_returned": False,
        "raw_prompts_returned": False,
        "provider_payloads_returned": False,
        "local_runtime_url_returned": False,
    }


def test_ai_model_route_preflight_accepts_owner_fallback_decision_without_provider_action(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "preflight-fallback.db"))

    decision = client.patch(
        "/api/admin/production/decisions/ai-model-route-approval",
        headers=admin_headers(),
        json={
            "state": "approved",
            "decided_by": "production-owner",
            "decision_note": "Fallback-only route accepted until approved model credentials are supplied.",
        },
    )
    response = client.get("/api/ai/model-route-preflight")

    assert decision.status_code == 200
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["summary"]["route_decision_ready"] is True
    assert body["summary"]["route_decision_state"] == "approved"
    assert body["summary"]["route_delivery_mode"] == "fallback_only_accepted"
    assert body["summary"]["provider_runtime_ready"] is False
    assert body["summary"]["provider_route_ready"] is False
    assert body["summary"]["next_gate"] == "ready"
    action_ids = [item["action_id"] for item in body["actions"]]
    assert "select-provider-policy" not in action_ids
    assert "record-ai-route-owner-decision" not in action_ids
    assert "sk-" not in json.dumps(body).lower()


def test_plaintext_secret_requires_encryption_key(monkeypatch, tmp_path) -> None:
    configure_idp(monkeypatch)
    monkeypatch.delenv("AGENTIOT_CREDENTIAL_FERNET_KEY", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "secret-block.db"))

    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={"auth_mode": "api_key", "api_key": "provider-auth-plain-sentinel"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Credential encryption key is not configured"


def test_model_service_rejects_non_provider_secret_env_reference(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    blocked_ref = "AGENTIOT_ADMIN_" + "TOKEN"
    client = TestClient(create_app(database_path=tmp_path / "env-ref-block.db"))

    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://api.openai.com/v1/responses",
            "api_key_env_var": blocked_ref,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported model credential env var reference"
    assert blocked_ref not in response.text


def test_model_service_accepts_provider_scoped_env_reference_without_value_leak(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    provider_token = "provider-" + "auth-" + "sentinel"
    monkeypatch.setenv("OPENAI_API_KEY", provider_token)
    client = TestClient(create_app(database_path=tmp_path / "env-ref-allow.db"))

    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://api.openai.com/v1/responses",
            "api_key_env_var": "OPENAI_API_KEY",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["credential"]["credential_configured"] is True
    assert body["credential"]["api_key_env_var"] == "OPENAI_API_KEY"
    assert provider_token not in response.text

    public_governance = client.get("/api/ai/resource-governance")

    assert public_governance.status_code == 200
    assert "api_key_env_var" not in public_governance.text
    assert "api_key_fingerprint" not in public_governance.text
    assert "updated_by" not in public_governance.text
    assert provider_token not in public_governance.text


def test_credential_encryption_key_file_enables_secret_storage(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    key_file = tmp_path / "credential_fernet_key"
    key_file.write_text(Fernet.generate_key().decode("ascii"), encoding="utf-8")
    monkeypatch.delenv("AGENTIOT_CREDENTIAL_FERNET_KEY", raising=False)
    monkeypatch.setenv("AGENTIOT_CREDENTIAL_FERNET_KEY_FILE", str(key_file))
    client = TestClient(create_app(database_path=tmp_path / "credential-key-file.db"))

    governance = client.get("/api/ai/resource-governance")
    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://api.openai.com/v1/responses",
            "api_key": "provider-" + "auth-" + "sentinel",
        },
    )

    assert governance.status_code == 200
    assert governance.json()["runtime_configuration"][
        "credential_encryption_configured"
    ] is True
    assert response.status_code == 200
    assert response.json()["credential"]["credential_configured"] is True
    assert "provider-" + "auth-" + "sentinel" not in response.text


def test_admin_configures_cloud_and_local_credentials_without_secret_leak(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "model-credentials.db"
    secret_key = "provider-" + "auth-" + "sentinel"
    password = "local-" + "password-" + "value"
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    client = TestClient(create_app(database_path=db_path))

    cloud = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://api.openai.com/v1/responses",
            "api_key": secret_key,
        },
    )
    local = client.put(
        "/api/admin/ai/model-services/local/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "username_password",
            "endpoint_url": "https://127.0.0.1:11434/api/chat",
            "username": "local-operator",
            "password": password,
        },
    )

    assert cloud.status_code == 200
    assert local.status_code == 200
    serialized = json.dumps({"cloud": cloud.json(), "local": local.json()})
    assert secret_key not in serialized
    assert password not in serialized
    assert cloud.json()["credential"]["api_key_configured"] is True
    assert cloud.json()["credential"]["secret_storage"] == "encrypted_at_rest"
    assert local.json()["credential"]["password_configured"] is True

    with sqlite3.connect(db_path) as connection:
        raw_dump = "\n".join(
            str(row)
            for row in connection.execute(
                """
                SELECT provider, username_ciphertext, password_ciphertext,
                       api_key_ciphertext
                FROM ai_model_credentials
                """
            ).fetchall()
        )
    assert secret_key not in raw_dump
    assert password not in raw_dump

    governance = client.get(
        "/api/admin/ai/model-services", headers=admin_headers()
    ).json()
    assert any(
        item["provider"] == "openai" and item["credential_configured"]
        for item in governance["credentials"]
    )
    assert any(
        item["provider"] == "local" and item["credential_configured"]
        for item in governance["credentials"]
    )


def test_authenticated_local_model_configuration_requires_tls_private_ip(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    client = TestClient(create_app(database_path=tmp_path / "local-transport.db"))
    request_body = {
        "auth_mode": "api_key",
        "api_key": "local-auth-sentinel",
    }

    cleartext = client.put(
        "/api/admin/ai/model-services/local/credentials",
        headers=admin_headers(),
        json={
            **request_body,
            "endpoint_url": "http://ollama.example.internal:11434/api/chat",
        },
    )

    def private_getaddrinfo(host, port, type=None):
        assert host == "models.internal.test"
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("ollama.example.internal", port),
            )
        ]

    monkeypatch.setattr(app_module.socket, "getaddrinfo", private_getaddrinfo)
    dns_host = client.put(
        "/api/admin/ai/model-services/local/credentials",
        headers=admin_headers(),
        json={
            **request_body,
            "endpoint_url": "https://models.internal.test/api/chat",
        },
    )

    assert cleartext.status_code == 400
    assert cleartext.json()["detail"] == (
        "Authenticated local model endpoints must use HTTPS"
    )
    assert dns_host.status_code == 400
    assert dns_host.json()["detail"] == (
        "Authenticated local model endpoints must use an approved private IP literal"
    )


def test_cloud_endpoint_rejects_private_network_target(monkeypatch, tmp_path) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    client = TestClient(create_app(database_path=tmp_path / "private-endpoint.db"))

    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "http://127.0.0.1:8080/private",
            "api_key": "provider-auth-sentinel",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Private model endpoint is allowed only for local provider"
    )


def test_cloud_endpoint_rejects_plain_http_target(monkeypatch, tmp_path) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    client = TestClient(create_app(database_path=tmp_path / "http-endpoint.db"))

    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "http://models.example.test/openai/responses",
            "api_key": "provider-auth-sentinel",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cloud model endpoint must use HTTPS"


def test_cloud_endpoint_rejects_private_dns_at_credential_storage(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )

    def private_getaddrinfo(host, port, *args, **kwargs):
        assert host == "models.example.test"
        assert port == 443
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("10.0.0.7", 443),
            )
        ]

    monkeypatch.setattr(app_module.socket, "getaddrinfo", private_getaddrinfo)
    client = TestClient(create_app(database_path=tmp_path / "cloud-private-dns.db"))

    response = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://models.example.test/openai/responses",
            "api_key": "provider-auth-sentinel",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cloud model endpoint resolves to private network"


def test_local_endpoint_rejects_public_dns_at_credential_storage(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )

    def fake_getaddrinfo(host, port, type=None):
        assert host == "models.example.test"
        assert port == 11434
        assert type == app_module.socket.SOCK_STREAM
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8", 11434),
            )
        ]

    monkeypatch.setattr(app_module.socket, "getaddrinfo", fake_getaddrinfo)
    client = TestClient(create_app(database_path=tmp_path / "local-public.db"))

    response = client.put(
        "/api/admin/ai/model-services/local/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "http://models.example.test:11434/api/chat",
            "api_key": "local-auth-sentinel",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Local model endpoint must resolve to local or private network"
    )


def test_local_credentials_require_an_exact_endpoint_scope(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    client = TestClient(create_app(database_path=tmp_path / "local-scope.db"))

    response = client.put(
        "/api/admin/ai/model-services/local/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "api_key": "local-auth-sentinel",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Local credentials require an exact endpoint URL"
    )


def test_cloud_provider_runtime_rejects_private_dns_before_network(
    monkeypatch,
) -> None:
    provider_auth = "provider-" + "auth-" + "sentinel"

    def private_getaddrinfo(host, port, *args, **kwargs):
        assert host == "models.example.test"
        assert port == 443
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("169.254.169.254", 443),
            )
        ]

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("private DNS provider endpoint reached network")

    monkeypatch.setattr(app_module.socket, "getaddrinfo", private_getaddrinfo)
    monkeypatch.setattr(app_module.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(
        ValueError,
        match="Cloud model endpoint resolves to private network",
    ):
        app_module.post_provider_json(
            provider="openai",
            url="https://models.example.test/openai/responses",
            **{"to" + "ken": provider_auth},
            payload={"model": "gpt-test", "input": "connectivity check"},
        )


def test_cloud_provider_runtime_uses_no_redirect_opener(monkeypatch) -> None:
    provider_auth = "provider-" + "auth-" + "sentinel"
    captured_handlers: list[object] = []

    def public_getaddrinfo(host, port, *args, **kwargs):
        assert host == "models.example.test"
        assert port == 443
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8", 443),
            )
        ]

    class ProviderResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit: int | None = None) -> bytes:
            return json.dumps({"id": "provider-ok", "output_text": "ok"}).encode(
                "utf-8"
            )

    class FakeOpener:
        def open(self, request, timeout: float):
            assert request.full_url == "https://models.example.test/openai/responses"
            assert timeout == 18.0
            return ProviderResponse()

    def fake_build_opener(*handlers):
        captured_handlers.extend(handlers)
        return FakeOpener()

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("cloud provider runtime bypassed redirect guard")

    monkeypatch.setattr(app_module.socket, "getaddrinfo", public_getaddrinfo)
    monkeypatch.setattr(app_module.urllib.request, "build_opener", fake_build_opener)
    monkeypatch.setattr(app_module.urllib.request, "urlopen", fail_urlopen)

    result = app_module.post_provider_json(
        provider="openai",
        url="https://models.example.test/openai/responses",
        **{"to" + "ken": provider_auth},
        payload={"model": "gpt-test", "input": "connectivity check"},
    )

    assert result["id"] == "provider-ok"
    assert any(
        getattr(handler, "__name__", "") == "NoProviderRedirectHandler"
        for handler in captured_handlers
    )


def test_cloud_provider_redirect_handler_blocks_target_leak() -> None:
    handler = app_module.NoProviderRedirectHandler()
    request = app_module.urllib.request.Request(
        "https://models.example.test/openai/responses"
    )

    with pytest.raises(app_module.urllib.error.HTTPError) as error:
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://169.254.169.254/latest/meta-data",
        )

    assert error.value.code == 302
    assert "169.254.169.254" not in str(error.value)


def test_local_model_runtime_uses_no_redirect_opener(monkeypatch) -> None:
    captured_handlers: list[object] = []

    class LocalResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit: int | None = None) -> bytes:
            return json.dumps(
                {"created_at": "local-ok", "message": {"content": "ok"}}
            ).encode("utf-8")

    class FakeOpener:
        def open(self, request, timeout: float):
            assert request.full_url == "https://127.0.0.1:11434/api/chat"
            assert request.get_header("Authorization") == "Bearer local-auth-sentinel"
            assert timeout == 18.0
            return LocalResponse()

    def fake_build_opener(*handlers):
        captured_handlers.extend(handlers)
        return FakeOpener()

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("local model runtime bypassed redirect guard")

    monkeypatch.setattr(app_module.urllib.request, "build_opener", fake_build_opener)
    monkeypatch.setattr(app_module.urllib.request, "urlopen", fail_urlopen)

    result = app_module.post_local_model_json(
        url="https://127.0.0.1:11434/api/chat",
        payload={"model": "local-test", "messages": []},
        auth_headers={"Authorization": "Bearer local-auth-sentinel"},
    )

    assert result["created_at"] == "local-ok"
    assert any(
        getattr(handler, "__name__", "") == "NoProviderRedirectHandler"
        for handler in captured_handlers
    )


def test_local_model_runtime_rejects_credentials_over_cleartext() -> None:
    with pytest.raises(
        ValueError,
        match="Authenticated local model endpoints require HTTPS",
    ):
        app_module.post_local_model_json(
            url="http://127.0.0.1:11434/api/chat",
            payload={"model": "local-test", "messages": []},
            auth_headers={"Authorization": "Bearer local-auth-sentinel"},
        )


def test_local_model_runtime_rejects_credentials_for_dns_host(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        app_module.socket,
        "getaddrinfo",
        lambda host, port, type=None: [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("ollama.example.internal", port),
            )
        ],
    )

    with pytest.raises(
        ValueError,
        match="Authenticated local model endpoints require HTTPS",
    ):
        app_module.post_local_model_json(
            url="https://models.internal.test/api/chat",
            payload={"model": "local-test", "messages": []},
            auth_headers={"Authorization": "Bearer local-auth-sentinel"},
        )


def test_local_model_runtime_rejects_public_dns_before_network(monkeypatch) -> None:
    def fake_getaddrinfo(host, port, type=None):
        assert host == "models.example.test"
        assert port == 443
        assert type == app_module.socket.SOCK_STREAM
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8", 443),
            )
        ]

    def fail_provider_request(*args, **kwargs):
        raise AssertionError("local model endpoint reached public network")

    monkeypatch.setattr(app_module.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(app_module, "open_provider_request", fail_provider_request)

    with pytest.raises(
        ValueError, match="Local model endpoint must resolve to local or private network"
    ):
        app_module.post_local_model_json(
            url="https://models.example.test/ollama/api/chat",
            payload={"model": "local-test", "messages": []},
            auth_headers={"Authorization": "Bearer local-auth-sentinel"},
        )


def test_local_model_runtime_rejects_public_docker_host_dns_before_network(
    monkeypatch,
) -> None:
    def fake_getaddrinfo(host, port, type=None):
        assert host == "host.docker.internal"
        assert port == 11434
        assert type == app_module.socket.SOCK_STREAM
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("8.8.4.4", 11434),
            )
        ]

    def fail_provider_request(*args, **kwargs):
        raise AssertionError("local Docker-host endpoint reached public network")

    monkeypatch.setattr(app_module.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(app_module, "open_provider_request", fail_provider_request)

    with pytest.raises(
        ValueError, match="Local model endpoint must resolve to local or private network"
    ):
        app_module.post_local_model_json(
            url="http://host.docker.internal:11434/api/chat",
            payload={"model": "local-test", "messages": []},
            auth_headers={"Authorization": "Bearer local-auth-sentinel"},
        )


def test_model_runtime_disables_ambient_proxy_handlers(monkeypatch) -> None:
    captured_handlers: list[object] = []

    class ProviderResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, limit: int | None = None) -> bytes:
            return json.dumps({"id": "proxy-safe", "output_text": "ok"}).encode(
                "utf-8"
            )

    class FakeOpener:
        def open(self, request, timeout: float):
            assert request.full_url == "https://models.example.test/openai/responses"
            return ProviderResponse()

    def fake_build_opener(*handlers):
        captured_handlers.extend(handlers)
        return FakeOpener()

    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.test:8080")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example.test:8080")
    monkeypatch.setattr(app_module.urllib.request, "build_opener", fake_build_opener)
    monkeypatch.setattr(
        app_module.socket,
        "getaddrinfo",
        lambda host, port, type=None: [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8", port),
            )
        ],
    )

    request = app_module.urllib.request.Request(
        "https://models.example.test/openai/responses"
    )
    target = app_module.validated_cloud_provider_target("openai", request.full_url)
    with app_module.open_provider_request(request, 18.0, target) as response:
        assert response.read()

    proxy_handlers = [
        handler
        for handler in captured_handlers
        if handler.__class__.__name__ == "ProxyHandler"
    ]
    assert proxy_handlers
    assert proxy_handlers[0].proxies == {}
    assert any(
        handler.__class__.__name__ == "PinnedHTTPSHandler"
        for handler in captured_handlers
    )


def test_local_runtime_connects_only_to_validated_sockaddr(monkeypatch) -> None:
    resolution_calls = 0

    def resolve_once(host, port, type=None):
        nonlocal resolution_calls
        resolution_calls += 1
        assert host == "models.internal.test"
        assert port == 11500
        assert type == app_module.socket.SOCK_STREAM
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("ollama.example.internal", 11500),
            )
        ]

    connected: list[tuple[str, int]] = []

    class FakeSocket:
        def settimeout(self, _timeout):
            return None

        def bind(self, _source):
            return None

        def connect(self, sockaddr):
            connected.append(sockaddr)

        def close(self):
            return None

    monkeypatch.setattr(app_module.socket, "getaddrinfo", resolve_once)
    target = app_module.validated_local_model_target(
        "http://models.internal.test:11500/api/version"
    )
    monkeypatch.setattr(
        app_module.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("hostname was resolved twice")
        ),
    )
    monkeypatch.setattr(app_module.socket, "socket", lambda *_args: FakeSocket())

    connection = app_module._PinnedHTTPConnection(
        "models.internal.test:11500",
        target=target,
        timeout=3,
    )
    connection.connect()

    assert resolution_calls == 1
    assert connected == [("ollama.example.internal", 11500)]
    assert target.hostname == "models.internal.test"
    assert app_module.urlparse(target.url).netloc == "models.internal.test:11500"


def test_cloud_https_pin_preserves_original_sni_and_verification(monkeypatch) -> None:
    monkeypatch.setattr(
        app_module.socket,
        "getaddrinfo",
        lambda host, port, type=None: [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8", port),
            )
        ],
    )
    target = app_module.validated_cloud_provider_target(
        "openai",
        "https://models.example.test/openai/responses",
    )
    connected: list[tuple[str, int]] = []
    sni: list[str] = []

    class FakeSocket:
        def settimeout(self, _timeout):
            return None

        def bind(self, _source):
            return None

        def connect(self, sockaddr):
            connected.append(sockaddr)

        def close(self):
            return None

    class VerifyingContext:
        check_hostname = True
        verify_mode = app_module.ssl.CERT_REQUIRED
        post_handshake_auth = False

        def wrap_socket(self, sock, *, server_hostname):
            sni.append(server_hostname)
            return sock

    monkeypatch.setattr(app_module.socket, "socket", lambda *_args: FakeSocket())
    context = VerifyingContext()
    connection = app_module._PinnedHTTPSConnection(
        "models.example.test",
        target=target,
        timeout=3,
        context=context,
    )
    connection.connect()

    assert connected == [("8.8.8.8", 443)]
    assert sni == ["models.example.test"]
    assert connection._context.check_hostname is True
    assert connection._context.verify_mode == app_module.ssl.CERT_REQUIRED


def test_mixed_safe_and_unsafe_dns_answers_fail_before_socket_creation(
    monkeypatch,
) -> None:
    socket_created = False

    def mixed_cloud(host, port, type=None):
        return [
            (app_module.socket.AF_INET, app_module.socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
            (app_module.socket.AF_INET, app_module.socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
        ]

    def create_socket(*_args, **_kwargs):
        nonlocal socket_created
        socket_created = True
        raise AssertionError("socket must not be created")

    monkeypatch.setattr(app_module.socket, "getaddrinfo", mixed_cloud)
    monkeypatch.setattr(app_module.socket, "socket", create_socket)
    with pytest.raises(ValueError, match="resolves to private network"):
        app_module.validated_cloud_provider_target(
            "openai",
            "https://models.example.test/openai/responses",
        )

    def mixed_local(host, port, type=None):
        return [
            (app_module.socket.AF_INET, app_module.socket.SOCK_STREAM, 6, "", ("ollama.example.internal", port)),
            (app_module.socket.AF_INET, app_module.socket.SOCK_STREAM, 6, "", ("169.254.1.1", port)),
        ]

    monkeypatch.setattr(app_module.socket, "getaddrinfo", mixed_local)
    with pytest.raises(ValueError, match="local or private network"):
        app_module.validated_local_model_target(
            "http://models.internal.test:11500/api/version"
        )
    assert socket_created is False


def test_cloud_provider_runtime_rejects_plain_http_before_network(
    monkeypatch,
) -> None:
    provider_auth = "provider-" + "auth-" + "sentinel"

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("plain HTTP provider endpoint reached network")

    monkeypatch.setattr(app_module.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(ValueError, match="Cloud model endpoint must use HTTPS"):
        app_module.post_provider_json(
            provider="openai",
            url="http://models.example.test/openai/responses",
            **{"to" + "ken": provider_auth},
            payload={"model": "gpt-test", "input": "connectivity check"},
        )


def test_token_usage_ledger_and_memory_policy_are_admin_managed(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "usage-memory.db"))

    usage = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-5.5",
            "input_tokens": 120,
            "output_tokens": 80,
            "source": "manual_audit",
        },
    )
    policy = client.patch(
        "/api/admin/ai/memory-policy",
        headers=admin_headers(),
        json={
            "max_memory_mb": 768,
            "retention_hours": 168,
            "max_session_count": 300,
            "warn_at_percent": 70,
            "auto_prune": True,
        },
    )

    assert usage.status_code == 200
    assert usage.json()["record"]["total_tokens"] == 200
    assert policy.status_code == 200
    assert policy.json()["policy"]["max_memory_mb"] == 768
    assert policy.json()["policy"]["retention_hours"] == 168
    assert policy.json()["recommendation"]["auto_prune_recommended"] is True

    ledger = client.get("/api/ai/usage-ledger").json()
    assert ledger["summary"]["event_count"] == 1
    assert ledger["summary"]["total_tokens"] == 200
    assert all(window["total_tokens"] == 200 for window in ledger["windows"])

    settings = client.get("/api/settings").json()["items"]
    assert any(item["control"] == "AI token ledger" for item in settings)
    assert any(item["control"] == "AI memory policy" for item in settings)
    reports = client.get("/api/reports/dashboard", headers=admin_headers()).json()["reports"]
    assert any(item["report_id"] == "ai-token-usage-ledger" for item in reports)
    assert any(item["report_id"] == "ai-memory-policy" for item in reports)


def test_public_settings_patch_updates_memory_policy_with_admin_scope(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "settings-patch.db"))

    anonymous = client.patch("/api/settings", json={"retention_hours": 96})
    updated = client.patch(
        "/api/settings",
        headers=admin_headers(),
        json={"retention_hours": 96, "max_memory_mb": 512},
    )
    reread = client.get("/api/settings")

    assert anonymous.status_code == 401
    assert updated.status_code == 200
    body = updated.json()
    assert body["status"] == "updated"
    assert body["updated_setting"] == "AI memory policy"
    assert body["policy"]["retention_hours"] == 96
    assert body["policy"]["max_memory_mb"] == 512
    assert body["privacy"]["credential_values_returned"] is False
    assert reread.status_code == 200
    memory_item = next(
        item for item in reread.json()["items"] if item["control"] == "AI memory policy"
    )
    assert "512 MB cap" in memory_item["evidence"]
    assert "96 hour retention" in memory_item["evidence"]


def test_admin_token_usage_read_requires_admin_scope(monkeypatch, tmp_path) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "usage-read-admin.db"))

    recorded = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-test",
            "input_tokens": 1,
            "output_tokens": 2,
            "source": "manual_audit",
        },
    )

    public_ledger = client.get("/api/ai/usage-ledger")
    anonymous_admin_read = client.get("/api/admin/ai/token-usage")
    anonymous_memory_policy = client.get("/api/admin/ai/memory-policy")
    admin_read = client.get("/api/admin/ai/token-usage", headers=admin_headers())
    admin_memory_policy = client.get(
        "/api/admin/ai/memory-policy", headers=admin_headers()
    )

    assert recorded.status_code == 200
    assert public_ledger.status_code == 200
    public_body = public_ledger.json()
    assert public_body["summary"]["total_tokens"] == 3
    assert public_body["privacy"]["latest_events_returned"] is False
    assert "latest_events" not in public_body
    assert "usage_id" not in public_ledger.text
    assert "gpt-test" not in public_ledger.text
    assert "manual_audit" not in public_ledger.text
    assert anonymous_admin_read.status_code == 401
    assert anonymous_admin_read.json()["detail"] == "Admin token or bearer required"
    assert anonymous_memory_policy.status_code == 401
    assert anonymous_memory_policy.json()["detail"] == "Admin token or bearer required"
    assert admin_read.status_code == 200
    admin_body = admin_read.json()
    assert admin_body["summary"]["total_tokens"] == 3
    assert admin_body["privacy"]["latest_events_returned"] is True
    assert admin_body["latest_events"][0]["model"] == "gpt-test"
    assert admin_body["latest_events"][0]["usage_source"] == "manual_audit"
    assert admin_memory_policy.status_code == 200
    assert admin_memory_policy.json()["policy"]["source"] == "default"


def test_fallback_chat_records_counts_only_token_usage(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "fallback-token-ledger.db"))
    prompt = "critical token accounting review for sensor-token"
    seed_chat_grounding(client)

    response = client.post(
        "/api/chat",
        headers=OPERATOR_HEADERS,
        json={"message": prompt},
    )

    assert response.status_code == 200
    body = response.json()
    record = body["token_usage_record"]["record"]
    assert body["token_usage_record"]["audit_event_id"]
    assert record["provider"] == "local"
    assert record["model"] == "non_model_grounded_answer"
    assert record["usage_source"] == "assistant_fallback_estimate"
    assert record["input_tokens"] > 0
    assert record["output_tokens"] > 0
    assert prompt not in response.text

    usage = client.get("/api/ai/resource-governance").json()["token_usage"]
    assert usage["summary"]["event_count"] == 1
    assert usage["summary"]["total_tokens"] == record["total_tokens"]
    assert usage["summary"]["storage_policy"] == "token_counts_only_no_prompt_or_answer"
    assert all(window["total_tokens"] == record["total_tokens"] for window in usage["windows"])


def test_token_usage_ledger_prunes_records_outside_required_windows(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "usage-retention.db"
    client = TestClient(create_app(database_path=db_path))

    stale = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-5.5",
            "input_tokens": 900,
            "output_tokens": 100,
            "source": "manual_audit",
        },
    )
    current = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "gemini",
            "model": "gemini-operations",
            "input_tokens": 20,
            "output_tokens": 30,
            "source": "manual_audit",
        },
    )
    assert stale.status_code == 200
    assert current.status_code == 200
    stale_id = stale.json()["record"]["usage_id"]
    stale_timestamp = (
        datetime.now(UTC) - timedelta(days=370)
    ).replace(microsecond=0).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE ai_token_usage_events SET created_at = ? WHERE usage_id = ?",
            (stale_timestamp, stale_id),
        )

    public_ledger = client.get("/api/ai/usage-ledger").json()
    ledger = client.get("/api/admin/ai/token-usage", headers=admin_headers()).json()

    assert public_ledger["summary"]["event_count"] == 1
    assert public_ledger["summary"]["total_tokens"] == 50
    assert public_ledger["privacy"]["latest_events_returned"] is False
    assert "latest_events" not in public_ledger
    assert ledger["summary"]["event_count"] == 1
    assert ledger["summary"]["total_tokens"] == 50
    assert ledger["summary"]["retention_policy"] == (
        "keep_required_windows_prune_older_than_12mo"
    )
    assert ledger["summary"]["retention_days"] == 365
    assert public_ledger["summary"]["pruned_usage_events"] == 1
    assert all(window["total_tokens"] == 50 for window in ledger["windows"])
    assert [item["usage_id"] for item in ledger["latest_events"]] == [
        current.json()["record"]["usage_id"]
    ]
    serialized = json.dumps(ledger).lower()
    assert ledger["privacy"]["provider_payload_returned"] is False
    assert "provider-auth-sentinel" not in serialized

    with sqlite3.connect(db_path) as connection:
        remaining = connection.execute(
            "SELECT COUNT(*) FROM ai_token_usage_events"
        ).fetchone()[0]
        audit_detail = connection.execute(
            """
            SELECT detail FROM audit_events
            WHERE event_type = ?
            """,
            ("ai.token_usage.retention_pruned",),
        ).fetchone()[0]
    assert remaining == 1
    assert '"pruned_usage_events":1' in audit_detail
    assert '"raw_prompt_stored":false' in audit_detail


def test_assistant_memory_policy_auto_prunes_expired_sessions(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "assistant-memory-prune.db"
    client = TestClient(create_app(database_path=db_path))

    policy = client.patch(
        "/api/admin/ai/memory-policy",
        headers=admin_headers(),
        json={
            "max_memory_mb": 768,
            "retention_hours": 1,
            "max_session_count": 10,
            "warn_at_percent": 70,
            "auto_prune": True,
        },
    )
    assert policy.status_code == 200

    expired = client.post(
        "/api/chat",
        headers=admin_headers(),
        json={
            "message": "expired assistant memory canary",
            "session_id": "expired-memory-session",
            "client_message_id": "expired-memory-message",
        },
    )
    assert expired.status_code == 200
    expired_interaction = expired.json()["session"]["interaction_id"]
    old_timestamp = (datetime.now(UTC) - timedelta(hours=2)).replace(microsecond=0).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE assistant_interactions SET created_at = ? WHERE interaction_id = ?",
            (old_timestamp, expired_interaction),
        )

    active = client.post(
        "/api/chat",
        headers=admin_headers(),
        json={
            "message": "active assistant memory canary",
            "session_id": "active-memory-session",
            "client_message_id": "active-memory-message",
        },
    )

    assert active.status_code == 200
    sessions = client.get("/api/assistant/sessions", headers=admin_headers()).json()
    session_ids = {item["session_id"] for item in sessions["sessions"]}
    assert "active-memory-session" in session_ids
    assert "expired-memory-session" not in session_ids
    assert sessions["summary"]["thread_count"] == 1

    with sqlite3.connect(db_path) as connection:
        expired_rows = connection.execute(
            "SELECT COUNT(*) FROM assistant_interactions WHERE session_id = ?",
            ("expired-memory-session",),
        ).fetchone()[0]
        prune_audits = connection.execute(
            "SELECT detail FROM audit_events WHERE event_type = ?",
            ("ai.memory_policy.pruned",),
        ).fetchall()
    assert expired_rows == 0
    assert prune_audits
    assert any('"expired_interactions":1' in row[0] for row in prune_audits)


def test_assistant_memory_policy_keeps_active_session_tool_proposals(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "assistant-memory-mixed-session.db"
    client = TestClient(create_app(database_path=db_path))

    policy = client.patch(
        "/api/admin/ai/memory-policy",
        headers=admin_headers(),
        json={
            "max_memory_mb": 768,
            "retention_hours": 1,
            "max_session_count": 10,
            "warn_at_percent": 70,
            "auto_prune": True,
        },
    )
    assert policy.status_code == 200

    expired = client.post(
        "/api/chat",
        headers=admin_headers(),
        json={
            "message": "old mixed-session assistant canary",
            "session_id": "mixed-memory-session",
            "client_message_id": "mixed-memory-old",
        },
    )
    assert expired.status_code == 200
    expired_interaction = expired.json()["session"]["interaction_id"]
    old_timestamp = (
        datetime.now(UTC) - timedelta(hours=2)
    ).replace(microsecond=0).isoformat()
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE assistant_interactions SET created_at = ? WHERE interaction_id = ?",
            (old_timestamp, expired_interaction),
        )
        connection.execute(
            """
            INSERT INTO assistant_tool_proposals (
                proposal_id, session_id, tool_id, owner_agent_id,
                execution_state, target_required_scope, audit_event_id,
                finding_id, requires_human_approval, execution_allowed,
                created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "mixed-session-proposal",
                "mixed-memory-session",
                "/api/recovery/proposals/preview/approve",
                "recovery_action_agent",
                "prepared",
                "recovery:approve",
                None,
                None,
                1,
                0,
                "admin@example.test",
                old_timestamp,
                old_timestamp,
            ),
        )

    active = client.post(
        "/api/chat",
        headers=admin_headers(),
        json={
            "message": "active mixed-session assistant canary",
            "session_id": "mixed-memory-session",
            "client_message_id": "mixed-memory-active",
        },
    )

    assert active.status_code == 200
    sessions = client.get("/api/assistant/sessions", headers=admin_headers()).json()
    assert sessions["summary"]["thread_count"] == 1
    assert sessions["sessions"][0]["session_id"] == "mixed-memory-session"

    with sqlite3.connect(db_path) as connection:
        active_rows = connection.execute(
            "SELECT COUNT(*) FROM assistant_interactions WHERE session_id = ?",
            ("mixed-memory-session",),
        ).fetchone()[0]
        proposal_rows = connection.execute(
            "SELECT COUNT(*) FROM assistant_tool_proposals WHERE session_id = ?",
            ("mixed-memory-session",),
        ).fetchone()[0]
    assert active_rows == 1
    assert proposal_rows == 1


def test_assistant_memory_policy_caps_session_count(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "assistant-memory-session-cap.db"
    client = TestClient(create_app(database_path=db_path))

    policy = client.patch(
        "/api/admin/ai/memory-policy",
        headers=admin_headers(),
        json={
            "max_memory_mb": 768,
            "retention_hours": 24,
            "max_session_count": 10,
            "warn_at_percent": 70,
            "auto_prune": True,
        },
    )
    assert policy.status_code == 200

    for index in range(12):
        response = client.post(
            "/api/chat",
            headers=admin_headers(),
            json={
                "message": f"session-cap assistant canary {index}",
                "session_id": f"session-cap-{index:02d}",
                "client_message_id": f"session-cap-message-{index:02d}",
            },
        )
        assert response.status_code == 200

    sessions = client.get("/api/assistant/sessions", headers=admin_headers()).json()
    session_ids = {item["session_id"] for item in sessions["sessions"]}
    assert sessions["summary"]["thread_count"] == 10
    assert "session-cap-11" in session_ids

    with sqlite3.connect(db_path) as connection:
        session_count = connection.execute(
            """
            SELECT COUNT(DISTINCT session_id)
            FROM assistant_interactions
            WHERE session_id LIKE 'session-cap-%'
            """
        ).fetchone()[0]
        prune_audits = connection.execute(
            "SELECT detail FROM audit_events WHERE event_type = ?",
            ("ai.memory_policy.pruned",),
        ).fetchall()
    assert session_count == 10
    assert any('"session_cap_interactions":1' in row[0] for row in prune_audits)


def test_assistant_memory_policy_enforces_metadata_memory_cap(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "assistant-memory-size-cap.db"
    client = TestClient(create_app(database_path=db_path))
    now = datetime.now(UTC).replace(microsecond=0)

    with sqlite3.connect(db_path) as connection:
        for session_index in range(12):
            for turn_index in range(11):
                created_at = (
                    now - timedelta(minutes=120 - session_index)
                ).isoformat()
                interaction_id = f"size-cap-{session_index:02d}-{turn_index:02d}"
                session_id = f"size-cap-session-{session_index:02d}"
                connection.execute(
                    """
                    INSERT INTO assistant_interactions (
                        interaction_id, prompt_hash, prompt_category,
                        response_status, route_json, evidence_count,
                        knowledge_count, requires_human_approval,
                        confidence, actor, outcome, latency_ms, created_at,
                        session_id, message_id, parent_message_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        interaction_id,
                        f"hash-{interaction_id}",
                        "operations",
                        "ready",
                        '["grounded_fallback"]',
                        1,
                        0,
                        0,
                        "medium",
                        "admin@example.test",
                        "success",
                        1,
                        created_at,
                        session_id,
                        f"msg-{interaction_id}",
                        None,
                    ),
                )

    policy = client.patch(
        "/api/admin/ai/memory-policy",
        headers=admin_headers(),
        json={
            "max_memory_mb": 1,
            "retention_hours": 24 * 30,
            "max_session_count": 1000,
            "warn_at_percent": 70,
            "auto_prune": True,
        },
    )
    assert policy.status_code == 200

    with sqlite3.connect(db_path) as connection:
        remaining_interactions = connection.execute(
            "SELECT COUNT(*) FROM assistant_interactions"
        ).fetchone()[0]
        remaining_sessions = connection.execute(
            "SELECT COUNT(DISTINCT session_id) FROM assistant_interactions"
        ).fetchone()[0]
        prune_audits = connection.execute(
            "SELECT detail FROM audit_events WHERE event_type = ?",
            ("ai.memory_policy.pruned",),
        ).fetchall()

    assert remaining_interactions < 132
    assert remaining_sessions < 12
    assert any('"memory_cap_interactions":' in row[0] for row in prune_audits)
    assert policy.json()["recommendation"]["configured_max_memory_mb"] == 1


def test_token_usage_rejects_invalid_provider_and_negative_counts(monkeypatch, tmp_path) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "invalid-token-usage.db"))

    unsupported = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "unsupported",
            "model": "not-used",
            "input_tokens": 1,
            "output_tokens": 1,
            "source": "manual_audit",
        },
    )
    negative = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-5.5",
            "input_tokens": -1,
            "output_tokens": 1,
            "source": "manual_audit",
        },
    )

    assert unsupported.status_code == 400
    assert negative.status_code == 422
    ledger = client.get("/api/ai/usage-ledger").json()
    assert ledger["summary"]["event_count"] == 0


def test_public_token_usage_ledger_ignores_invalid_persisted_timestamps(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    db_path = tmp_path / "invalid-usage-timestamp.db"
    client = TestClient(create_app(database_path=db_path))

    response = client.post(
        "/api/admin/ai/token-usage",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-5.5",
            "input_tokens": 11,
            "output_tokens": 7,
            "source": "manual_audit",
        },
    )
    usage_id = response.json()["record"]["usage_id"]
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE ai_token_usage_events SET created_at = ? WHERE usage_id = ?",
            ("not-a-date", usage_id),
        )

    ledger = client.get("/api/ai/usage-ledger").json()

    assert response.status_code == 200
    assert ledger["summary"]["event_count"] == 0
    assert ledger["summary"]["total_tokens"] == 0
    assert all(window["event_count"] == 0 for window in ledger["windows"])
    assert "latest_events" not in ledger


def test_dashboard_exposes_write_only_model_service_controls(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "model-service-ui.db"))

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="ai-model-services"' in html
    assert 'id="ai-model-service-form"' in html
    assert 'name="provider"' in html
    assert 'value="local"' in html
    assert 'value="openai"' in html
    assert 'value="gemini"' in html
    assert 'value="huggingface"' in html
    assert 'name="auth_mode"' in html
    assert 'name="endpoint_url"' in html
    assert 'name="api_key" type="password"' in html
    assert 'name="api_key_env_var"' in html
    assert 'name="username"' in html
    assert 'name="password" type="password"' in html
    assert 'name="password_env_var"' in html
    assert "controlPutJson(controlPath('ai', 'model-services', provider, 'credentials')" in html
    assert "connectivity-check" in html
    assert "postControlJson" in html
    assert "loadJson('/api/ai/model-services')" in html
    assert "displayAIModelServices" in html
    assert 'id="advanced-model-service-test"' in html
    assert 'id="ai-model-service-test"' in html
    assert "Test Active Provider" in html
    assert "Latest Check" in html
    assert "operatorStatusLabel(latest.status, 'Not tested')" in html
    assert "renderAIModelServices" in html
    assert 'id="ai-memory-policy"' in html
    assert 'id="ai-memory-policy-form"' in html
    assert 'id="advanced-memory-policy-form"' in html
    assert 'name="max_memory_mb"' in html
    assert 'name="retention_hours"' in html
    assert 'name="max_session_count"' in html
    assert 'name="warn_at_percent"' in html
    assert 'name="auto_prune"' in html
    assert "controlPatchJson(controlPath('ai', 'memory-policy')" in html
    assert "renderAIMemoryPolicy" in html
    assert "ai-token-retention-state" in html
    assert "Memory policy saved" in html
    assert "secret_values_returned" not in html
    assert "provider-auth-sentinel" not in html



def test_admin_model_service_connection_test_blocks_without_active_runtime(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "model-test-blocked.db"))

    response = client.post(
        "/api/admin/ai/model-services/openai/connectivity-check",
        headers=admin_headers(),
        json={"probe_label": "blocked_probe"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["version"] == __version__
    assert body["test"]["provider"] == "openai"
    assert body["test"]["runtime_allowed"] is False
    assert body["test"]["usage_recorded"] is False
    assert body["test"]["total_tokens"] == 0
    assert body["finding_id"].startswith("finding-")
    governance = client.get("/api/admin/ai/model-services", headers=admin_headers()).json()
    openai = next(item for item in governance["credentials"] if item["provider"] == "openai")
    assert openai["latest_connectivity_check"]["status"] == "blocked"
    assert "provider_payload_returned" in openai["latest_connectivity_check"]["privacy"]
    assert set(body["test"]["blocking_gates"]) >= {
        "provider_policy_not_active",
        "model_not_configured",
        "credential_not_configured",
        "cloud_runtime_gate_disabled",
        "provider_policy_runtime_disabled",
    }
    assert body["privacy"] == {
        "secret_values_returned": False,
        "raw_prompt_returned": False,
        "answer_text_returned": False,
        "provider_payload_returned": False,
        "local_runtime_url_returned": False,
        "token_counts_only": True,
    }
    assert "sk-" not in response.text.lower()
    assert "Connectivity confirmed" not in response.text


def test_admin_model_service_connection_test_records_usage_without_payload_leak(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    monkeypatch.setenv("AGENTIOT_AI_ALLOW_CLOUD_CALLS", "true")
    configure_public_model_dns(monkeypatch)

    def fake_post_provider_json(**kwargs):
        assert kwargs["token"] == "provider-auth-sentinel"
        assert kwargs["url"] == "https://models.example.test/openai/responses"
        assert "input" in kwargs["payload"]
        return {
            "id": "resp_connection_test",
            "output_text": "Connectivity confirmed for grounded operations.",
            "usage": {"input_tokens": 17, "output_tokens": 5},
        }

    monkeypatch.setattr(app_module, "post_provider_json", fake_post_provider_json)
    client = TestClient(create_app(database_path=tmp_path / "model-test-complete.db"))
    credential = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://models.example.test/openai/responses",
            "api_key": "provider-auth-sentinel",
        },
    )
    policy = client.patch(
        "/api/admin/ai/provider-policy",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-test",
            "quality_profile": "grounded-operations",
            "max_context_chars": 6000,
            "grounding_required": True,
            "runtime_enabled": True,
            "allowed_tools": ["/api/operations/summary", "/api/rag/search"],
        },
    )
    matrix_before = client.get("/api/ai/model-benchmarks").json()
    before_openai = next(
        candidate
        for candidate in matrix_before["tasks"][0]["candidates"]
        if candidate["route"] == "openai_runtime"
    )
    response = client.post(
        "/api/admin/ai/model-services/openai/connectivity-check",
        headers=admin_headers(),
        json={"probe_label": "unit_connection_probe"},
    )
    ledger = client.get("/api/admin/ai/token-usage", headers=admin_headers()).json()
    matrix_after = client.get("/api/ai/model-benchmarks").json()

    assert credential.status_code == 200
    assert policy.status_code == 200
    assert matrix_before["summary"]["runtime_ready_count"] == 0
    assert matrix_before["summary"]["route_decision"]["delivery_mode"] == (
        "provider_activation_evidence_required"
    )
    assert before_openai["runtime_available"] is False
    assert before_openai["status"] == "waiting_for_activation_check"
    assert "connectivity_check_not_run" in before_openai["activation_evidence"]["blocking_gates"]
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["test"]["provider"] == "openai"
    assert body["test"]["model"] == "gpt-test"
    assert body["test"]["runtime_allowed"] is True
    assert body["test"]["credential_configured"] is True
    assert body["test"]["usage_recorded"] is True
    assert body["test"]["input_tokens"] == 17
    assert body["test"]["output_tokens"] == 5
    assert body["test"]["total_tokens"] == 22
    assert body["finding_id"].startswith("finding-")
    assert body["token_usage_record"]["usage_source"] == "connection_test"
    assert ledger["summary"]["total_tokens"] == 22
    assert matrix_after["summary"]["runtime_ready_count"] == 1
    assert matrix_after["summary"]["route_decision"]["delivery_mode"] == "provider_runtime_ready"
    assert {task["recommended_route"] for task in matrix_after["tasks"]} == {"openai_runtime"}
    after_openai = next(
        candidate
        for candidate in matrix_after["tasks"][0]["candidates"]
        if candidate["route"] == "openai_runtime"
    )
    assert after_openai["runtime_available"] is True
    assert after_openai["activation_evidence"]["status"] == "ready"
    assert after_openai["activation_evidence"]["latest_connectivity_check"]["usage_recorded"] is True
    governance = client.get("/api/admin/ai/model-services", headers=admin_headers()).json()
    openai = next(item for item in governance["credentials"] if item["provider"] == "openai")
    assert openai["latest_connectivity_check"]["status"] == "completed"
    assert openai["latest_connectivity_check"]["usage_recorded"] is True
    serialized = json.dumps({"response": body, "ledger": ledger})
    assert "provider-auth-sentinel" not in serialized
    assert "Connectivity confirmed" not in serialized
    assert body["privacy"]["provider_payload_returned"] is False


def test_admin_model_service_connection_test_malformed_response_is_metadata_only(
    monkeypatch,
    tmp_path,
) -> None:
    configure_idp(monkeypatch)
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    monkeypatch.setenv("AGENTIOT_AI_ALLOW_CLOUD_CALLS", "true")
    configure_public_model_dns(monkeypatch)
    payload_probe = "malformed-provider-payload-canary-4421"

    def fake_post_provider_json(**kwargs):
        assert kwargs["token"] == "provider-auth-sentinel"
        return {
            "id": "resp_malformed",
            "output": [{"content": [{"text": 123, "leak": payload_probe}]}],
            "usage": {"input_tokens": "NaN", "output_tokens": 7},
        }

    monkeypatch.setattr(app_module, "post_provider_json", fake_post_provider_json)
    client = TestClient(create_app(database_path=tmp_path / "model-test-malformed.db"))
    credential = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=admin_headers(),
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://models.example.test/openai/responses",
            "api_key": "provider-auth-sentinel",
        },
    )
    policy = client.patch(
        "/api/admin/ai/provider-policy",
        headers=admin_headers(),
        json={
            "provider": "openai",
            "model": "gpt-test",
            "quality_profile": "grounded-operations",
            "max_context_chars": 6000,
            "grounding_required": True,
            "runtime_enabled": True,
            "allowed_tools": ["/api/operations/summary"],
        },
    )

    response = client.post(
        "/api/admin/ai/model-services/openai/connectivity-check",
        headers=admin_headers(),
        json={"probe_label": "malformed_probe"},
    )
    body = response.json()
    surfaces = {
        "response": body,
        "governance": client.get(
            "/api/admin/ai/model-services", headers=admin_headers()
        ).json(),
        "ledger": client.get("/api/admin/ai/token-usage", headers=admin_headers()).json(),
        "audit": client.get("/api/audit/events").json(),
        "findings": client.get("/api/evidence/findings").json(),
    }
    serialized = json.dumps(surfaces)

    assert credential.status_code == 200
    assert policy.status_code == 200
    assert response.status_code == 200
    assert body["status"] == "failed"
    assert body["test"]["provider"] == "openai"
    assert body["test"]["provider_error"] == "empty_response"
    assert body["test"]["answer_chars"] == 0
    assert body["test"]["usage_recorded"] is True
    assert body["test"]["input_tokens"] > 0
    assert body["test"]["output_tokens"] >= 0
    assert body["test"]["total_tokens"] == (
        body["test"]["input_tokens"] + body["test"]["output_tokens"]
    )
    assert body["privacy"]["provider_payload_returned"] is False
    assert payload_probe not in serialized
    assert "resp_malformed" not in serialized
    assert "provider-auth-sentinel" not in serialized
