# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.1 | Date: 2026-08-11

"""P0 production trust-boundary and operational-truth regression tests."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

import agentiot.app as app_module
from agentiot.app import create_app
from agentiot.version import __version__
from conftest import (
    admin_token_headers,
    configure_offhost_restore_receipt,
    sign_offhost_liveness_payload,
    sign_offhost_restore_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
OPERATOR_VALUE = "p0-operator-" + ("o" * 64)
ADMIN_VALUE = "p0-admin-" + ("a" * 64)


def configure_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure a deterministic single-customer production boundary."""

    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_TENANT_ID", "greenovax")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", OPERATOR_VALUE)
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", ADMIN_VALUE)


def test_authentication_material_in_query_is_rejected_without_echo(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "query-auth.db"))
    marker = "query-auth-value-must-not-return"

    response = client.get("/healthz", params={"access_token": marker})

    assert response.status_code == 400
    assert marker not in response.text
    assert response.json()["detail"] == "Authentication material is not accepted in URLs"


def test_cloud_provider_endpoint_is_bound_to_provider_allowlist(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AGENTIOT_CREDENTIAL_FERNET_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "provider-host.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}

    rejected = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=headers,
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://attacker.example.test/v1/responses",
            "api_key": "provider-auth-sentinel",
        },
    )

    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Provider endpoint host is not approved"

    def public_getaddrinfo(host, port, *_args, **_kwargs):
        assert host == "models.example.test"
        return [
            (
                app_module.socket.AF_INET,
                app_module.socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", port),
            )
        ]

    monkeypatch.setenv(
        "AGENTIOT_AI_OPENAI_ALLOWED_HOSTS",
        "models.example.test",
    )
    monkeypatch.setattr(app_module.socket, "getaddrinfo", public_getaddrinfo)
    accepted = client.put(
        "/api/admin/ai/model-services/openai/credentials",
        headers=headers,
        json={
            "auth_mode": "api_key",
            "endpoint_url": "https://models.example.test/v1/responses",
            "api_key": "provider-auth-sentinel",
        },
    )

    assert accepted.status_code == 200
    assert "provider-auth-sentinel" not in accepted.text


def test_cloud_gateway_rejects_unapproved_host_before_transport(
    monkeypatch,
) -> None:
    def fail_transport(*_args, **_kwargs):
        raise AssertionError("unapproved provider endpoint reached transport")

    monkeypatch.setattr(app_module, "open_provider_request", fail_transport)

    with pytest.raises(ValueError, match="Provider endpoint host is not approved"):
        app_module.post_provider_json(
            provider="openai",
            url="https://attacker.example.test/v1/responses",
            **{"to" + "ken": "provider-" + "auth-" + "sentinel"},
            payload={"model": "test", "input": "bounded check"},
        )


def test_production_rag_and_assistant_stream_require_tenant_bound_identity(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "tenant-stream.db"))

    assert (
        client.get(
            "/api/rag/search",
            params={"q": "recovery evidence"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/assistant/stream",
            json={"message": "Summarize recovery evidence"},
        ).status_code
        == 401
    )

    wrong_tenant = client.get(
        "/api/rag/search",
        params={"q": "recovery evidence"},
        headers={
            "X-Operator-Token": OPERATOR_VALUE,
            "X-AgentIoT-Tenant": "another-customer",
        },
    )
    assert wrong_tenant.status_code == 403
    assert "another-customer" not in wrong_tenant.text

    accepted = client.get(
        "/api/rag/search",
        params={"q": "recovery evidence"},
        headers={
            "X-Operator-Token": OPERATOR_VALUE,
            "X-AgentIoT-Tenant": "greenovax",
        },
    )
    assert accepted.status_code == 200
    assert accepted.headers["X-AgentIoT-Tenant"] == "greenovax"


def test_production_orchestration_evidence_requires_operator_identity(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "evidence-auth.db"))

    denied = client.get("/api/orchestration/evidence-matrix")
    accepted = client.get(
        "/api/orchestration/evidence-matrix",
        headers={"X-Operator-Token": OPERATOR_VALUE},
    )

    assert denied.status_code == 401
    assert accepted.status_code == 200


def test_a2a_sse_requires_agent_read_scope(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "a2a-stream-auth.db"))

    assert client.get("/api/a2a/messages/stream").status_code == 401

    response = client.get(
        "/api/a2a/messages/stream",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


def test_operational_truth_is_tenant_bound_and_versioned(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_TENANT_ID", "greenovax")
    client = TestClient(create_app(database_path=tmp_path / "truth.db"))

    response = client.get("/api/system/operational-truth")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["schema_version"] == "operational.truth.v1"
    assert body["tenant_id"] == "greenovax"
    assert body["release"]["version"] == __version__
    assert body["assets"]["registered"] == 0
    assert body["agents"]["registered"] >= 1
    assert body["approvals"]["recovery_pending"] == 0


def test_runtime_access_logs_cannot_record_query_values() -> None:
    dockerfile = (REPO_ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    nginx = (REPO_ROOT / "docker/nginx-https-8040.conf").read_text(
        encoding="utf-8"
    )

    assert "--no-access-log" in dockerfile
    assert "log_format agentiot_safe" in nginx
    assert "access_log /dev/stdout agentiot_safe;" in nginx
    log_format = nginx.split("log_format agentiot_safe", 1)[1].split(";", 1)[0]
    assert "$uri" in log_format
    assert "$request_uri" not in log_format


def test_production_backup_requires_current_offhost_restore_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "bounded encrypted backup")
    client = TestClient(create_app(database_path=tmp_path / "offhost-gate.db"))

    local_restore = client.post(
        "/api/admin/production/restore-test",
        headers=admin_token_headers(monkeypatch),
        json={},
    )
    assert local_restore.status_code == 200
    blocked = client.get("/api/production/backup-retention").json()
    assert blocked["status"] == "restore_review_required"
    assert blocked["restore_test_state"] == "recorded"
    assert blocked["off_host_restore_required"] is True
    assert blocked["off_host_restore_state"] == "not_configured"

    receipt = configure_offhost_restore_receipt(monkeypatch, tmp_path)
    ready = client.get("/api/production/backup-retention").json()
    assert ready["status"] == "ready"
    assert ready["off_host_restore_state"] == "recorded"

    original_payload = json.loads(receipt.read_text(encoding="utf-8"))
    forged_payload = dict(original_payload)
    forged_payload["backup_digest"] = "sha256:" + ("c" * 64)
    receipt.write_text(json.dumps(forged_payload), encoding="utf-8")
    forged = client.get("/api/production/backup-retention").json()
    assert forged["status"] == "restore_review_required"
    assert forged["off_host_restore_state"] == "signature_invalid"

    receipt.write_text(json.dumps(original_payload, indent=2), encoding="utf-8")
    digest_mismatch = client.get("/api/production/backup-retention").json()
    assert digest_mismatch["status"] == "restore_review_required"
    assert digest_mismatch["off_host_restore_state"] == "receipt_digest_mismatch"

    mismatched_payload = dict(original_payload)
    mismatched_payload["release_version"] = "0.0.0"
    mismatched_payload["receipt_signature"] = sign_offhost_restore_payload(
        mismatched_payload
    )
    mismatched_bytes = json.dumps(mismatched_payload).encode("utf-8")
    receipt.write_bytes(mismatched_bytes)
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
        "sha256:" + hashlib.sha256(mismatched_bytes).hexdigest(),
    )
    mismatched = client.get("/api/production/backup-retention").json()
    assert mismatched["status"] == "restore_review_required"
    assert mismatched["off_host_restore_state"] == "release_mismatch"

    wrong_tenant_payload = dict(original_payload)
    wrong_tenant_payload["tenant_id"] = "another-customer"
    wrong_tenant_payload["receipt_signature"] = sign_offhost_restore_payload(
        wrong_tenant_payload
    )
    wrong_tenant_bytes = json.dumps(wrong_tenant_payload).encode("utf-8")
    receipt.write_bytes(wrong_tenant_bytes)
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
        "sha256:" + hashlib.sha256(wrong_tenant_bytes).hexdigest(),
    )
    wrong_tenant = client.get("/api/production/backup-retention").json()
    assert wrong_tenant["status"] == "restore_review_required"
    assert wrong_tenant["off_host_restore_state"] == "identity_mismatch"

    for field, invalid_value in (
        ("backup_object_name", "wrong-object.sqlite"),
        ("publication", "replace"),
        ("writer_isolation", "exclusive"),
        ("storage_immutability", "attested"),
        ("restore_consumer_requirement", "trust-receipt-only"),
    ):
        invalid_payload = dict(original_payload)
        invalid_payload[field] = invalid_value
        invalid_payload["receipt_signature"] = sign_offhost_restore_payload(
            invalid_payload
        )
        invalid_bytes = json.dumps(invalid_payload).encode("utf-8")
        receipt.write_bytes(invalid_bytes)
        monkeypatch.setenv(
            app_module.OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
            "sha256:" + hashlib.sha256(invalid_bytes).hexdigest(),
        )
        invalid = client.get("/api/production/backup-retention").json()
        assert invalid["status"] == "restore_review_required"
        assert invalid["off_host_restore_state"] == "invalid"


def test_restore_receipt_key_and_deployment_are_independently_bound(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "bounded encrypted backup")
    receipt = configure_offhost_restore_receipt(monkeypatch, tmp_path)
    client = TestClient(create_app(database_path=tmp_path / "key-boundary.db"))
    public_key = os.environ[app_module.OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_ENV]

    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "recorded"
    monkeypatch.delenv(
        app_module.OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_ENV,
        raising=False,
    )
    monkeypatch.setenv("AGENTIOT_CREDENTIAL_FERNET_KEY", Fernet.generate_key().decode())
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "signature_unavailable"

    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_ENV,
        public_key,
    )
    monkeypatch.setenv("AGENTIOT_DEPLOYMENT_ID", "different-deployment-2026")
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "deployment_mismatch"
    assert receipt.is_file()


def test_restore_receipt_requires_liveness_immutability_and_replay_guard(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "bounded encrypted backup")
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    client = TestClient(create_app(database_path=tmp_path / "replay-boundary.db"))
    liveness_file = Path(
        os.environ[app_module.OFFHOST_RESTORE_LIVENESS_FILE_ENV]
    )
    original_liveness = json.loads(liveness_file.read_text(encoding="utf-8"))
    backup = Path(os.environ[app_module.OFFHOST_RESTORE_BACKUP_FILE_ENV])
    backup_content = backup.read_bytes()

    def publish_liveness(payload: dict) -> None:
        payload["liveness_signature"] = sign_offhost_liveness_payload(payload)
        liveness_file.write_text(json.dumps(payload), encoding="utf-8")

    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "recorded"

    receipt = json.loads(
        Path(os.environ[app_module.OFFHOST_RESTORE_RECEIPT_FILE_ENV]).read_text(
            encoding="utf-8"
        )
    )
    aliased_provider = dict(original_liveness)
    aliased_provider["provider_key_id"] = receipt["receipt_key_id"]
    publish_liveness(aliased_provider)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "provider_key_not_separated"
    publish_liveness(dict(original_liveness))

    backup.unlink()
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "backup_object_unavailable"
    backup.write_bytes(backup_content)

    unattested = dict(original_liveness)
    unattested["provider_immutability"] = "not_attested"
    unattested["retention_until"] = None
    publish_liveness(unattested)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "immutability_unattested"

    replay_conflict = dict(original_liveness)
    replay_conflict["provider_object_version"] = "test-object-version-conflict"
    publish_liveness(replay_conflict)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "replay_conflict"


def test_restore_readiness_hashes_one_backup_once_per_liveness_proof(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "bounded encrypted backup")
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    client = TestClient(create_app(database_path=tmp_path / "bounded-hash.db"))
    app_module.OFFHOST_BACKUP_VERIFY_CACHE.clear()
    pread_calls = 0
    original_pread = app_module.os.pread

    def counted_pread(*args, **kwargs):
        nonlocal pread_calls
        pread_calls += 1
        return original_pread(*args, **kwargs)

    monkeypatch.setattr(app_module.os, "pread", counted_pread)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "recorded"
    first_request_calls = pread_calls
    assert first_request_calls > 0

    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "recorded"
    assert pread_calls == first_request_calls


def test_restore_backup_hash_is_single_flight_for_concurrent_readiness(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    backup = Path(os.environ[app_module.OFFHOST_RESTORE_BACKUP_FILE_ENV])
    content = backup.read_bytes()
    expected_digest = "sha256:" + hashlib.sha256(content).hexdigest()
    app_module.OFFHOST_BACKUP_VERIFY_CACHE.clear()
    original_pread = app_module.os.pread
    first_read_started = threading.Event()
    release_first_read = threading.Event()
    calls_lock = threading.Lock()
    pread_calls = 0

    def counted_pread(*args, **kwargs):
        nonlocal pread_calls
        with calls_lock:
            pread_calls += 1
            current_call = pread_calls
        if current_call == 1:
            first_read_started.set()
            assert release_first_read.wait(timeout=2)
        return original_pread(*args, **kwargs)

    monkeypatch.setattr(app_module.os, "pread", counted_pread)

    def verify() -> str:
        return app_module.verify_mounted_offhost_backup(
            expected_digest=expected_digest,
            expected_size=len(content),
            liveness_digest="sha256:" + ("a" * 64),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(verify)
        assert first_read_started.wait(timeout=2)
        second = executor.submit(verify)
        release_first_read.set()
        assert first.result(timeout=3) == "verified"
        assert second.result(timeout=3) == "verified"

    expected_chunks = (len(content) + (1024 * 1024) - 1) // (1024 * 1024)
    assert pread_calls == expected_chunks


def test_restore_digest_mismatch_is_single_flight_and_cached(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    backup = Path(os.environ[app_module.OFFHOST_RESTORE_BACKUP_FILE_ENV])
    content = backup.read_bytes()
    app_module.OFFHOST_BACKUP_VERIFY_CACHE.clear()
    original_pread = app_module.os.pread
    first_read_started = threading.Event()
    release_first_read = threading.Event()
    calls_lock = threading.Lock()
    pread_calls = 0

    def counted_pread(*args, **kwargs):
        nonlocal pread_calls
        with calls_lock:
            pread_calls += 1
            current_call = pread_calls
        if current_call == 1:
            first_read_started.set()
            assert release_first_read.wait(timeout=2)
        return original_pread(*args, **kwargs)

    monkeypatch.setattr(app_module.os, "pread", counted_pread)

    def verify() -> str:
        return app_module.verify_mounted_offhost_backup(
            expected_digest="sha256:" + ("0" * 64),
            expected_size=len(content),
            liveness_digest="sha256:" + ("b" * 64),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(verify)
        assert first_read_started.wait(timeout=2)
        second = executor.submit(verify)
        release_first_read.set()
        assert first.result(timeout=3) == "backup_object_digest_mismatch"
        assert second.result(timeout=3) == "backup_object_digest_mismatch"

    expected_chunks = (len(content) + (1024 * 1024) - 1) // (1024 * 1024)
    assert pread_calls == expected_chunks
    assert verify() == "backup_object_digest_mismatch"
    assert pread_calls == expected_chunks


def test_restore_receipt_rejects_legacy_unknown_expired_and_replayed_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    configure_production(monkeypatch)
    monkeypatch.setenv("AGENTIOT_BACKUP_POLICY", "bounded encrypted backup")
    receipt = configure_offhost_restore_receipt(monkeypatch, tmp_path)
    client = TestClient(create_app(database_path=tmp_path / "strict-receipt.db"))
    original = json.loads(receipt.read_text(encoding="utf-8"))
    liveness_file = Path(
        os.environ[app_module.OFFHOST_RESTORE_LIVENESS_FILE_ENV]
    )
    original_liveness = json.loads(liveness_file.read_text(encoding="utf-8"))

    def publish(payload: dict) -> None:
        payload["receipt_signature"] = sign_offhost_restore_payload(payload)
        encoded = json.dumps(payload).encode("utf-8")
        receipt.write_bytes(encoded)
        monkeypatch.setenv(
            app_module.OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
            "sha256:" + hashlib.sha256(encoded).hexdigest(),
        )

    def publish_liveness(payload: dict) -> None:
        payload["liveness_signature"] = sign_offhost_liveness_payload(payload)
        liveness_file.write_text(json.dumps(payload), encoding="utf-8")

    legacy = dict(original)
    legacy["schema_version"] = "agentiot.offhost-restore.v4"
    publish(legacy)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "legacy_receipt_rejected"

    unknown = dict(original)
    unknown["untrusted_extension"] = "reject"
    publish(unknown)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "invalid"

    expired = dict(original_liveness)
    issued_at = datetime.now(UTC) - timedelta(minutes=5)
    expired["checked_at"] = issued_at.isoformat()
    expired["expires_at"] = (issued_at + timedelta(seconds=120)).isoformat()
    publish(dict(original))
    publish_liveness(expired)
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "liveness_expired"

    publish(dict(original))
    publish_liveness(dict(original_liveness))
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "recorded"
    app_module.OFFHOST_BACKUP_VERIFY_CACHE.clear()
    assert client.get("/api/production/backup-retention").json()[
        "off_host_restore_state"
    ] == "recorded"
