# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-29

"""Secure admin-session and dual-Ollama health contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from agentiot import app as app_module
from agentiot.app import (
    ADMIN_PASSWORD_FAILURE_LIMIT,
    create_app,
    invoke_model_provider,
    local_model_address_allowed,
    model_auth_headers_for_endpoint,
)
from agentiot.ollama_runtime import (
    ollama_endpoint_candidates,
    public_ollama_endpoint_summary,
)
from conftest import admin_token_headers


ROOT_PAGE = (
    Path(__file__).resolve().parents[1] / "src" / "agentiot" / "root_page.html"
)


def test_ollama_endpoint_candidates_use_primary_then_secondary(monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_PRIMARY_URL",
        "http://ollama.example.internal:11434/",
    )
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_SECONDARY_URL",
        "http://ollama.example.internal:11434/api/chat",
    )

    endpoints = ollama_endpoint_candidates()

    assert [item["role"] for item in endpoints] == ["primary", "secondary"]
    assert [item["chat_url"] for item in endpoints] == [
        "http://ollama.example.internal:11434/api/chat",
        "http://ollama.example.internal:11434/api/chat",
    ]
    assert endpoints[0]["tags_url"].endswith("/api/tags")
    assert endpoints[1]["version_url"].endswith("/api/version")


def test_invalid_secondary_does_not_disable_a_valid_primary(monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_PRIMARY_URL",
        "http://ollama.example.internal:11434",
    )
    monkeypatch.setenv("AGENTIOT_OLLAMA_SECONDARY_URL", "not-a-url")

    endpoints = ollama_endpoint_candidates()
    summary = public_ollama_endpoint_summary(endpoints)

    assert endpoints[0]["role"] == "primary"
    assert endpoints[0]["chat_url"] == "http://ollama.example.internal:11434/api/chat"
    assert endpoints[1] == {
        "role": "secondary",
        "reference": "invalid configuration",
        "transport": "UNAVAILABLE",
        "configuration_error": "invalid_endpoint",
    }
    assert summary["primary_configured"] is True
    assert summary["secondary_configured"] is False
    assert summary["failover_configured"] is False


def test_local_model_network_policy_rejects_link_local_metadata_addresses() -> None:
    assert local_model_address_allowed("127.0.0.1") is True
    assert local_model_address_allowed("ollama.example.internal") is True
    assert local_model_address_allowed("169.254.169.254") is False


def test_local_model_credentials_are_scoped_to_one_exact_origin() -> None:
    material = {
        "api_key": "local-auth-sentinel",
        "endpoint_url": "https://ollama.example.internal:11434/api/chat",
    }

    primary = model_auth_headers_for_endpoint(
        material, "https://ollama.example.internal:11434/api/tags"
    )
    secondary = model_auth_headers_for_endpoint(
        material, "https://ollama.example.internal:11434/api/chat"
    )

    assert primary == {"Authorization": "Bearer local-auth-sentinel"}
    assert secondary == {}


def test_local_model_credentials_fail_closed_for_cleartext_and_dns_hosts() -> None:
    assert model_auth_headers_for_endpoint(
        {
            "api_key": "local-auth-sentinel",
            "endpoint_url": "http://ollama.example.internal:11434/api/chat",
        },
        "http://ollama.example.internal:11434/api/chat",
    ) == {}
    assert model_auth_headers_for_endpoint(
        {
            "api_key": "local-auth-sentinel",
            "endpoint_url": "https://models.internal.test/api/chat",
        },
        "https://models.internal.test/api/chat",
    ) == {}


def test_local_model_credentials_without_an_endpoint_fail_closed() -> None:
    assert model_auth_headers_for_endpoint(
        {"api_key": "local-auth-sentinel"},
        "http://ollama.example.internal:11434/api/chat",
    ) == {}


def test_local_model_runtime_fails_over_without_returning_endpoint(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_PRIMARY_URL",
        "http://ollama.example.internal:11434",
    )
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_SECONDARY_URL",
        "http://ollama.example.internal:11434",
    )
    calls: list[str] = []

    def fake_post_local_model_json(*, url, payload, auth_headers=None, timeout_s=18):
        calls.append(url)
        if "ollama.example.internal" in url:
            raise OSError("primary unavailable")
        return {
            "created_at": "2026-07-16T18:00:00Z",
            "message": {"content": "grounded response"},
            "prompt_eval_count": 8,
            "eval_count": 3,
        }

    monkeypatch.setattr(
        app_module,
        "post_local_model_json",
        fake_post_local_model_json,
    )
    result = invoke_model_provider(
        {
            "provider": "local",
            "model": "qwen3:8b",
            "quality_profile": "grounded-operations",
            "max_context_chars": 6000,
            "grounding_required": True,
            "runtime_enabled": True,
            "allowed_tools": [],
        },
        "bounded health request",
    )

    assert result["status"] == "completed"
    assert result["endpoint_role"] == "secondary"
    assert calls == [
        "http://ollama.example.internal:11434/api/chat",
        "http://ollama.example.internal:11434/api/chat",
    ]
    assert "endpoint_url" not in result


def test_admin_password_creates_short_lived_session_without_password_replay(
    tmp_path,
    monkeypatch,
) -> None:
    admin_value = "strong-admin-password-" + "a" * 32
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", admin_value)
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-" + "a" * 64)
    app = create_app(database_path=tmp_path / "admin-session.db")

    with TestClient(app) as client:
        denied = client.post(
            "/api/auth/admin-session",
            json={"username": "admin", "password": "wrong-password"},
        )
        created = client.post(
            "/api/auth/admin-session",
            json={"username": "admin", "password": admin_value},
        )
        session_token = created.json()["session_token"]
        settings = client.get(
            "/api/admin/service-operations/settings",
            headers={"X-Admin-Token": session_token},
        )

    assert denied.status_code == 401
    assert created.status_code == 201
    assert settings.status_code == 200
    payload = created.json()
    assert payload["username"] == "admin"
    assert payload["expires_in_seconds"] <= 1800
    assert len(session_token) > 80
    assert admin_value not in json.dumps(payload)


def test_admin_password_lockout_happens_before_password_comparison(
    tmp_path,
    monkeypatch,
) -> None:
    admin_value = "strong-admin-password-" + ("a" * 32)
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", admin_value)
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-" + "a" * 64)
    comparisons = 0
    original_compare = app_module.secrets.compare_digest

    def tracked_compare(left, right):
        nonlocal comparisons
        comparisons += 1
        return original_compare(left, right)

    monkeypatch.setattr(app_module.secrets, "compare_digest", tracked_compare)
    app = create_app(database_path=tmp_path / "admin-lockout.db")
    with TestClient(app) as client:
        for _attempt in range(ADMIN_PASSWORD_FAILURE_LIMIT):
            assert client.post(
                "/api/auth/admin-session",
                json={"username": "admin", "password": "wrong-password"},
            ).status_code == 401
        blocked = client.post(
            "/api/auth/admin-session",
            json={"username": "admin", "password": admin_value},
        )
    assert blocked.status_code == 429
    assert comparisons == ADMIN_PASSWORD_FAILURE_LIMIT


def test_production_admin_session_rejects_a_short_password(
    tmp_path,
    monkeypatch,
) -> None:
    admin_value = "short"
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", admin_value)
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-" + "a" * 64)
    app = create_app(database_path=tmp_path / "short-admin-password.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/admin-session",
            json={"username": "admin", "password": admin_value},
        )
        security = client.get("/api/security/status")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Admin password does not meet production policy"
    )
    assert security.status_code == 200
    assert security.json()["admin_password_strength"] == "weak"
    assert admin_value not in security.text


def test_production_requires_explicit_override_for_a_temporary_password(
    tmp_path,
    monkeypatch,
) -> None:
    admin_value = "eight888"
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", admin_value)
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-" + "a" * 64)
    monkeypatch.delenv("AGENTIOT_ALLOW_TEMPORARY_ADMIN_PASSWORD", raising=False)
    app = create_app(database_path=tmp_path / "temporary-admin-password.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/auth/admin-session",
            json={"username": "admin", "password": admin_value},
        )
        security = client.get("/api/security/status")

    assert response.status_code == 503
    assert security.json()["admin_password_strength"] == "temporary"
    assert security.json()["temporary_admin_password_allowed"] is False


def test_production_data_requires_auth_and_admin_session_unlocks_reads(
    tmp_path,
    monkeypatch,
) -> None:
    admin_value = "strong-admin-password-" + "a" * 32
    operator_value = "strong-operator-" + "o" * 64
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", operator_value)
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-" + "a" * 64)
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", admin_value)
    app = create_app(database_path=tmp_path / "authenticated-data.db")
    app.state.http_service_probe = lambda contract, timeout_seconds: {
        "service_id": contract["service_id"],
        "status": "healthy",
        "http_status": 200,
        "latency_ms": 1,
        "security": {
            "state": "complete",
            "score": 100,
            "present": 4,
            "required": 4,
        },
        "issue_code": None,
        "checked_at": "2026-07-16T18:00:00Z",
        "timeout_seconds": timeout_seconds,
    }

    with TestClient(app) as client:
        created = client.post(
            "/api/assets",
            headers={"X-Operator-Token": operator_value},
            json={
                "asset_id": "private-production-asset",
                "name": "Private Production Asset",
            },
        )
        root = client.get("/")
        denied = {
            path: client.get(path).status_code
            for path in (
                "/api/assets",
                "/api/devices",
                "/api/telemetry",
                "/api/alerts",
                "/api/recovery/proposals",
                "/api/cmdb/configuration-items",
                "/api/config/profiles",
                "/api/firmware/drift",
                "/api/simulation/runs",
                "/api/plugins/hardware-simulator/runs",
                "/api/operations/summary",
                "/api/operations/workbench",
                "/api/operations/next-best-action",
                "/api/operations/command-center",
                "/api/operations/bootstrap/status",
                "/api/system/observability",
                "/api/system/operational-truth",
                "/api/services/http",
                "/api/hardware/discovery/candidates",
            )
        }
        login = client.post(
            "/api/auth/admin-session",
            json={"username": "admin", "password": admin_value},
        )
        session_headers = {"X-Admin-Token": login.json()["session_token"]}
        authorized = client.get("/api/assets", headers=session_headers)
        discovery_candidates = client.get(
            "/api/hardware/discovery/candidates",
            headers=session_headers,
        )
        service_check = client.post(
            "/api/services/http/self-check",
            headers=session_headers,
            json={},
        )
        security = client.get("/api/security/status")

    assert created.status_code == 201
    assert set(denied.values()) == {401}
    assert "private-production-asset" not in root.text
    assert "Private Production Asset" not in root.text
    assert login.status_code == 201
    assert authorized.status_code == 200
    assert authorized.json()["items"][0]["asset_id"] == "private-production-asset"
    assert discovery_candidates.status_code == 200
    assert discovery_candidates.json()["items"] == []
    assert service_check.status_code == 200
    assert service_check.json()["summary"]["total"] == 11
    assert service_check.json()["summary"]["healthy"] == 11
    assert security.json()["admin_password_strength"] == "strong"
    assert security.json()["temporary_admin_password_allowed"] is False


def test_agent_and_llm_health_checks_both_endpoints_and_all_agents(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_PRIMARY_URL",
        "http://ollama.example.internal:11434",
    )
    monkeypatch.setenv(
        "AGENTIOT_OLLAMA_SECONDARY_URL",
        "http://ollama.example.internal:11434",
    )
    monkeypatch.setenv("AGENTIOT_AI_LOCAL_MODEL", "qwen3:8b")

    def fake_get_local_model_json(*, url, auth_headers=None, timeout_s=8):
        if url.endswith("/api/version"):
            return {"version": "0.24.0"}
        return {"models": [{"name": "qwen3:8b"}]}

    def fake_post_local_model_json(*, url, payload, auth_headers=None, timeout_s=18):
        return {
            "created_at": "2026-07-16T18:00:00Z",
            "message": {"content": "OK"},
            "prompt_eval_count": 4,
            "eval_count": 1,
        }

    monkeypatch.setattr(
        app_module,
        "get_local_model_json",
        fake_get_local_model_json,
    )
    monkeypatch.setattr(
        app_module,
        "post_local_model_json",
        fake_post_local_model_json,
    )
    app = create_app(database_path=tmp_path / "agent-llm-health.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        )
        latest = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["llm_status"] == "healthy"
    assert payload["summary"]["endpoint_total"] == 2
    assert payload["summary"]["endpoint_healthy"] == 2
    assert payload["summary"]["dual_endpoint_inference_verified"] is True
    assert payload["summary"]["inference_requests"] == 2
    assert payload["summary"]["agent_total"] == 7
    assert payload["summary"]["agent_healthy"] == 0
    assert payload["summary"]["agent_degraded"] == 7
    assert payload["summary"]["agent_workflows_executed"] == 0
    assert all(item["inference_status"] == "completed" for item in payload["endpoints"])
    assert all(item["status"] == "degraded" for item in payload["agents"])
    assert all(
        item["health_basis"] == "configuration_and_shared_model_route_only"
        and item["workflow_executed"] is False
        for item in payload["agents"]
    )
    serialized = json.dumps(payload).lower()
    assert '"answer"' not in serialized
    assert '"prompt"' not in serialized
    assert latest.status_code == 200
    assert latest.json()["run_id"] == payload["run_id"]


def test_metadata_only_probe_never_claims_endpoint_or_agent_health(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_OLLAMA_PRIMARY_URL", "http://ollama.example.internal:11434")
    monkeypatch.setenv("AGENTIOT_OLLAMA_SECONDARY_URL", "http://ollama.example.internal:11434")
    monkeypatch.setenv("AGENTIOT_AI_LOCAL_MODEL", "qwen3:8b")
    monkeypatch.setattr(
        app_module,
        "get_local_model_json",
        lambda *, url, auth_headers=None, timeout_s=8: (
            {"version": "0.24.0"}
            if url.endswith("/api/version")
            else {"models": [{"name": "qwen3:8b"}]}
        ),
    )

    with TestClient(create_app(database_path=tmp_path / "metadata-health.db")) as client:
        response = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": False},
        )

    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["llm_status"] == "degraded"
    assert payload["summary"]["endpoint_healthy"] == 0
    assert payload["summary"]["endpoint_reachable"] == 2
    assert payload["summary"]["dual_endpoint_inference_verified"] is False
    assert payload["summary"]["agent_healthy"] == 0
    assert all(item["status"] == "reachable_unverified" for item in payload["endpoints"])


def test_partial_or_single_inference_cannot_claim_dual_endpoint_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_OLLAMA_PRIMARY_URL", "http://ollama.example.internal:11434")
    monkeypatch.setenv("AGENTIOT_OLLAMA_SECONDARY_URL", "http://ollama.example.internal:11434")
    monkeypatch.setenv("AGENTIOT_AI_LOCAL_MODEL", "qwen3:8b")
    monkeypatch.setattr(
        app_module,
        "get_local_model_json",
        lambda *, url, auth_headers=None, timeout_s=8: (
            {"version": "0.24.0"}
            if url.endswith("/api/version")
            else {"models": [{"name": "qwen3:8b"}]}
        ),
    )

    def one_failed_inference(*, url, payload, auth_headers=None, timeout_s=18):
        if "ollama.example.internal" in url:
            raise TimeoutError("secondary unavailable")
        return {"message": {"content": "OK"}, "prompt_eval_count": 2, "eval_count": 1}

    monkeypatch.setattr(app_module, "post_local_model_json", one_failed_inference)
    with TestClient(create_app(database_path=tmp_path / "partial-health.db")) as client:
        partial = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        ).json()

    assert partial["llm_status"] == "degraded"
    assert partial["summary"]["endpoint_healthy"] == 1
    assert partial["summary"]["dual_endpoint_inference_verified"] is False

    monkeypatch.delenv("AGENTIOT_OLLAMA_SECONDARY_URL")
    monkeypatch.setattr(
        app_module,
        "post_local_model_json",
        lambda **_kwargs: {
            "message": {"content": "OK"},
            "prompt_eval_count": 2,
            "eval_count": 1,
        },
    )
    with TestClient(create_app(database_path=tmp_path / "single-health.db")) as client:
        single = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        ).json()

    assert single["llm_status"] == "healthy"
    assert single["summary"]["endpoint_total"] == 1
    assert single["summary"]["dual_endpoint_inference_verified"] is False
    assert single["summary"]["agent_healthy"] == 0


def configure_successful_shared_llm_probe(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_OLLAMA_PRIMARY_URL", "http://ollama.example.internal:11434")
    monkeypatch.setenv("AGENTIOT_OLLAMA_SECONDARY_URL", "http://ollama.example.internal:11434")
    monkeypatch.setenv("AGENTIOT_AI_LOCAL_MODEL", "qwen3:8b")
    monkeypatch.setattr(
        app_module,
        "get_local_model_json",
        lambda *, url, auth_headers=None, timeout_s=8: (
            {"version": "0.24.0"}
            if url.endswith("/api/version")
            else {"models": [{"name": "qwen3:8b"}]}
        ),
    )
    monkeypatch.setattr(
        app_module,
        "post_local_model_json",
        lambda **_kwargs: {
            "message": {"content": "OK"},
            "prompt_eval_count": 2,
            "eval_count": 1,
        },
    )


def test_agent_health_receipt_expiry_clears_positive_indicators(
    tmp_path,
    monkeypatch,
) -> None:
    configure_successful_shared_llm_probe(monkeypatch)
    app = create_app(database_path=tmp_path / "agent-health-expiry.db")
    with TestClient(app) as client:
        completed = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        )
        assert completed.status_code == 200
        expired_at = (
            datetime.now(UTC)
            - timedelta(seconds=app_module.MODEL_CONNECTIVITY_CHECK_TTL_SECONDS + 1)
        ).isoformat()
        with app.state.store.connect() as connection:
            connection.execute(
                "UPDATE audit_events SET created_at = ? "
                "WHERE event_type LIKE 'ai.agent_llm_health.%'",
                (expired_at,),
            )
        latest = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        ).json()

    assert latest["status"] == "stale"
    assert latest["llm_status"] == "unverified"
    assert latest["freshness"]["status"] == "stale"
    assert latest["freshness"]["configuration_match"] is True
    assert latest["summary"]["endpoint_healthy"] == 0
    assert latest["summary"]["agent_healthy"] == 0
    assert latest["measured_summary"]["endpoint_healthy"] == 2
    assert all(item["status"] == "unverified" for item in latest["agents"])


def test_agent_health_configuration_change_supersedes_previous_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    configure_successful_shared_llm_probe(monkeypatch)
    app = create_app(database_path=tmp_path / "agent-health-config-change.db")
    with TestClient(app) as client:
        completed = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        )
        assert completed.status_code == 200
        monkeypatch.setenv(
            "AGENTIOT_OLLAMA_SECONDARY_URL",
            "http://192.0.2.31:11500",
        )
        latest = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        ).json()

    assert latest["status"] == "configuration_changed"
    assert latest["freshness"]["configuration_match"] is False
    assert latest["summary"]["endpoint_healthy"] == 0
    assert latest["measured_summary"]["endpoint_healthy"] == 2
    assert all(item["llm_status"] == "unverified" for item in latest["agents"])


def test_agent_health_model_and_effective_secret_rotation_invalidate_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    configure_successful_shared_llm_probe(monkeypatch)
    app = create_app(database_path=tmp_path / "agent-health-secret-rotation.db")
    with TestClient(app) as client:
        completed = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        )
        assert completed.status_code == 200

        monkeypatch.setenv("AGENTIOT_AI_LOCAL_MODEL", "qwen3:14b")
        model_changed = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        ).json()
        assert model_changed["status"] == "configuration_changed"

        monkeypatch.setenv("AGENTIOT_AI_LOCAL_MODEL", "qwen3:8b")
        original_material = app.state.store.model_secret_material
        monkeypatch.setattr(
            app.state.store,
            "model_secret_material",
            lambda provider: {
                **original_material(provider),
                "api_key": "rotated-secret-value",
            },
        )
        secret_changed = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        ).json()

    assert secret_changed["status"] == "configuration_changed"
    assert secret_changed["freshness"]["configuration_match"] is False
    assert secret_changed["summary"]["endpoint_healthy"] == 0


def test_failed_agent_health_attempt_supersedes_old_success(
    tmp_path,
    monkeypatch,
) -> None:
    configure_successful_shared_llm_probe(monkeypatch)
    app = create_app(database_path=tmp_path / "agent-health-failed-attempt.db")
    with TestClient(app) as client:
        completed = client.post(
            "/api/admin/ai/agent-health/check",
            headers=admin_token_headers(monkeypatch),
            json={"include_inference": True},
        )
        assert completed.status_code == 200

        def fail_health_check(*_args, **_kwargs):
            raise RuntimeError("forced bounded health failure")

        monkeypatch.setattr(
            app_module,
            "run_agent_llm_health_check",
            fail_health_check,
        )
        with pytest.raises(RuntimeError):
            client.post(
                "/api/admin/ai/agent-health/check",
                headers=admin_token_headers(monkeypatch),
                json={"include_inference": True},
            )
        latest = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        ).json()

    assert latest["status"] == "failed"
    assert latest["llm_status"] == "unverified"
    assert latest["summary"]["endpoint_healthy"] == 0
    assert latest["summary"]["agent_healthy"] == 0


def test_unscoped_legacy_agent_health_receipt_fails_closed(
    tmp_path,
    monkeypatch,
) -> None:
    app = create_app(database_path=tmp_path / "agent-health-invalid.db")
    app.state.store.add_audit_event(
        event_type="ai.agent_llm_health.completed",
        subject_id="legacy-unscoped",
        actor="test",
        detail="{}",
    )
    with TestClient(app) as client:
        latest = client.get(
            "/api/admin/ai/agent-health",
            headers=admin_token_headers(monkeypatch),
        ).json()

    assert latest["status"] == "invalid"
    assert latest["llm_status"] == "unverified"
    assert latest["summary"]["endpoint_healthy"] == 0
    assert latest["summary"]["agent_healthy"] == 0


def test_settings_unlocks_admin_session_and_renders_agent_health() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    for expected in (
        'id="advanced-admin-password"',
        'id="advanced-admin-login"',
        "Sign In",
        "Run Shared LLM Probe",
        "workflows not exercised",
        "evidenceState !== 'fresh'",
        'id="advanced-ollama-endpoints-body"',
        'id="advanced-agent-health-body"',
        "async function loginAdminSession",
        "async function loadAdminSettings",
        "/api/auth/login",
        "controlPath('ai', 'agent-health', 'check')",
        "browserSession = result",
        "const adminEnabled = hasAdminAccess();",
        "if (!hasOperatorAccess()) {",
        "function bindSessionAvailability()",
        "Operator sign-in is required for write actions.",
        "const AUTHENTICATED_DATA_PATHS = new Set([",
        "INITIAL_OPERATIONAL_STATE.status === 'authentication_required'",
        "AUTHENTICATED_DATA_PATHS.has(pathname)",
        "function authenticatedDataPathLocked(path)",
        "await refreshData();",
        "if (endpoints.length) {",
        "Checking configured Ollama endpoints; agent workflows are not exercised...",
        "Shared LLM probe failed; agent workflows were not exercised:",
    ):
        assert expected in body
    for forbidden in (
        'id="admin-token"',
        'id="operator-token"',
        "getAdminAccessToken",
        "getOperatorToken",
        "headers['X-Admin-Token']",
        "headers['X-Operator-Token']",
        "Checking all agent routes and both Ollama endpoints...",
        "Agent and LLM health check failed:",
    ):
        assert forbidden not in body
    assert (
        '<button class="primary" type="submit" '
        'data-requires-access="admin-control">Save Service Settings</button>'
    ) in body
    assert "localStorage.setItem('admin" not in body
    assert 'localStorage.setItem("admin' not in body


def test_visual_qa_recognizes_password_backed_browser_identity() -> None:
    runner = (
        ROOT_PAGE.parents[2] / "tools" / "run_visual_qa.js"
    ).read_text(encoding="utf-8")

    assert "async function authenticateVisualContext" in runner
    assert "context.request.post(baseUrl + '/api/auth/login'" in runner
    assert "browser identity login did not produce a ready session" in runner
    assert "admin password control unavailable" not in runner
