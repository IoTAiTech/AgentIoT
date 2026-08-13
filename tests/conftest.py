# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.1 | Date: 2026-08-11

"""Shared pytest configuration for AgentIoT tests."""

import base64
import gc
import hashlib
import json
import os
import re
import secrets
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


TEST_IDP_KEY = "test-idp-validation-key"
TEST_ADMIN_TOKEN = "unit-admin-sentinel"
TEST_PRODUCTION_ADMIN_TOKEN = "test-production-admin-" + ("a" * 64)
TEST_OFFHOST_PRIVATE_KEY_FILE_ENV = "AGENTIOT_TEST_OFFHOST_PRIVATE_KEY_FILE"
TEST_OFFHOST_LIVENESS_PRIVATE_KEY_FILE_ENV = (
    "AGENTIOT_TEST_OFFHOST_LIVENESS_PRIVATE_KEY_FILE"
)


@pytest.fixture(autouse=True)
def configured_operator_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a non-production operator token for test writes."""

    os.environ.pop("AGENTIOT_ADMIN_TOKEN", None)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_DEPLOYMENT_ID", "test-deployment-2026")
    monkeypatch.setenv(
        "AGENTIOT_NETWORK_DISCOVERY_ALLOWED_CIDRS",
        "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
    )
    monkeypatch.setenv("AGENTIOT_SESSION_SECRET", "test-browser-session-" + ("s" * 64))
    monkeypatch.setenv(
        "AGENTIOT_AI_OPENAI_ALLOWED_HOSTS",
        "models.example.test",
    )
    yield
    os.environ.pop("AGENTIOT_ADMIN_TOKEN", None)
    gc.collect()


def make_test_jwt(
    *,
    issuer: str = "https://idp.example.test",
    audience: str | list[str] = "agentiot-dashboard",
    secret: str = TEST_IDP_KEY,
    subject: str | None = "operator@example.test",
    role: str = "operator",
    scope: str = "device:write telemetry:write recovery:approve",
    expires_in: int = 3600,
    tenant_id: str = "greenovax",
    include_exp: bool = True,
    preferred_username: str | None = None,
) -> str:
    """Create a compact HS256 JWT for identity-provider tests."""

    payload = {
        "iss": issuer,
        "aud": audience,
        "role": role,
        "scope": scope,
        "tenant_id": tenant_id,
    }
    if subject is not None:
        payload["sub"] = subject
    if include_exp:
        payload["exp"] = int(time.time()) + expires_in
    if preferred_username is not None:
        payload["preferred_username"] = preferred_username
    return jwt.encode(payload, secret, algorithm="HS256", headers={"typ": "JWT"})


def public_subject_ref(value: str) -> str:
    """Return the same contact-safe subject reference used by the app."""

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"subject-{digest}"


def assignable_subject_id(subject: str) -> str:
    """Return an assignment id that avoids raw contact data."""

    if (
        "@" not in subject
        and not re.search(r"(?:\d[\s().-]?){7,}", subject)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{1,79}", subject)
    ):
        return subject
    return public_subject_ref(subject)


def admin_token_headers(monkeypatch: pytest.MonkeyPatch | None = None) -> dict[str, str]:
    """Return bootstrap admin-token headers for test assignment setup."""

    token = (
        TEST_PRODUCTION_ADMIN_TOKEN
        if os.getenv("AGENTIOT_ENV", "development").lower() == "production"
        else TEST_ADMIN_TOKEN
    )
    if monkeypatch is not None:
        monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", token)
    else:
        os.environ["AGENTIOT_ADMIN_TOKEN"] = token
    return {"X-Admin-Token": token}


def sign_offhost_restore_payload(payload: dict) -> str:
    """Sign one test receipt with its ephemeral Ed25519 private key."""

    key_path = Path(os.environ[TEST_OFFHOST_PRIVATE_KEY_FILE_ENV])
    private_key = serialization.load_pem_private_key(
        key_path.read_bytes(),
        password=None,
    )
    assert isinstance(private_key, Ed25519PrivateKey)
    unsigned = {
        name: value
        for name, value in payload.items()
        if name != "receipt_signature"
    }
    message = b"agentiot-offhost-restore-v5\0" + json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "ed25519:" + base64.urlsafe_b64encode(
        private_key.sign(message)
    ).decode("ascii").rstrip("=")


def sign_offhost_liveness_payload(payload: dict) -> str:
    """Sign one test liveness proof with its independent ephemeral key."""

    key_path = Path(os.environ[TEST_OFFHOST_LIVENESS_PRIVATE_KEY_FILE_ENV])
    private_key = serialization.load_pem_private_key(
        key_path.read_bytes(),
        password=None,
    )
    assert isinstance(private_key, Ed25519PrivateKey)
    unsigned = {
        name: value
        for name, value in payload.items()
        if name != "liveness_signature"
    }
    message = b"agentiot-offhost-liveness-v1\0" + json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "ed25519:" + base64.urlsafe_b64encode(
        private_key.sign(message)
    ).decode("ascii").rstrip("=")


def configure_offhost_restore_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    """Configure a current path-redacted off-host restore receipt for tests."""

    from agentiot.app import (
        OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
        OFFHOST_RESTORE_BACKUP_FILE_ENV,
        OFFHOST_RESTORE_RECEIPT_FILE_ENV,
        OFFHOST_RESTORE_LEDGER_FILE_ENV,
        OFFHOST_RESTORE_RECEIPT_SCHEMA,
        RESTORE_VERIFICATION_TABLES,
    )
    from agentiot.version import __version__

    signing_key = Ed25519PrivateKey.generate()
    private_key_file = tmp_path / "offhost-receipt-private-key.pem"
    private_key_file.write_bytes(
        signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_key_file.chmod(0o600)
    public_key = signing_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    public_key_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    source_commit = "a" * 40
    runtime_digest = "sha256:" + ("b" * 64)
    monkeypatch.setenv(
        "AGENTIOT_OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY",
        public_key_pem,
    )
    monkeypatch.setenv(TEST_OFFHOST_PRIVATE_KEY_FILE_ENV, str(private_key_file))
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", source_commit)
    monkeypatch.setenv("AGENTIOT_RUNTIME_DIGEST", runtime_digest)
    monkeypatch.setenv("AGENTIOT_TENANT_ID", "greenovax")
    object_name = (
        f"agentiot-greenovax-{__version__}-20260809T120000Z-a1b2c3d4.sqlite"
    )
    backup = tmp_path / object_name
    backup.write_bytes(b"a" * 4096)
    backup_digest = "sha256:" + hashlib.sha256(backup.read_bytes()).hexdigest()
    issued_at = datetime.now(UTC)
    payload = {
        "schema_version": OFFHOST_RESTORE_RECEIPT_SCHEMA,
        "status": "verified",
        "verified_at": issued_at.isoformat(),
        "backup_digest": backup_digest,
        "quick_check": "ok",
        "storage_separation": "verified_remote_mount",
        "storage_profile_id": "greenovax-nas-primary",
        "storage_profile_fingerprint": "sha256:" + ("d" * 64),
        "filesystem_type": "cifs",
        "mount_id": "42",
        "mount_source_fingerprint": "sha256:" + ("c" * 64),
        "durability": "file_fsync_and_directory_fsync",
        "backup_size_bytes": 4096,
        "backup_object_name": object_name,
        "publication": "renameat2_noreplace",
        "writer_isolation": "owner_uid_match_no_world_write",
        "storage_immutability": "not_attested",
        "retention_until": None,
        "restore_consumer_requirement": (
            "reopen_nofollow_match_signed_sha256_each_readiness"
        ),
        "run_id": "restore-20260809t120000z-a1b2c3d4",
        "verified_tables": len(RESTORE_VERIFICATION_TABLES),
        "checked_records": 1,
        "release_version": __version__,
        "tenant_id": "greenovax",
        "deployment_id": "test-deployment-2026",
        "source_commit": source_commit,
        "runtime_digest": runtime_digest,
        "backup_id": "a" * 16,
        "receipt_key_id": hashlib.sha256(public_key_raw).hexdigest(),
        "customer_safe": True,
    }
    payload["receipt_signature"] = sign_offhost_restore_payload(payload)
    receipt = tmp_path / "offhost-restore-receipt.json"
    encoded_receipt = json.dumps(payload).encode("utf-8")
    receipt.write_bytes(encoded_receipt)
    liveness_key = Ed25519PrivateKey.generate()
    liveness_private_key_file = tmp_path / "offhost-liveness-private-key.pem"
    liveness_private_key_file.write_bytes(
        liveness_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    liveness_private_key_file.chmod(0o600)
    liveness_public_key = liveness_key.public_key()
    liveness_public_key_pem = liveness_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    liveness_public_key_raw = liveness_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    monkeypatch.setenv(
        "AGENTIOT_OFFHOST_RESTORE_LIVENESS_PUBLIC_KEY",
        liveness_public_key_pem,
    )
    monkeypatch.setenv(
        TEST_OFFHOST_LIVENESS_PRIVATE_KEY_FILE_ENV,
        str(liveness_private_key_file),
    )
    liveness_checked_at = datetime.now(UTC)
    liveness_payload = {
        "schema_version": "agentiot.offhost-liveness.v1",
        "status": "verified",
        "checked_at": liveness_checked_at.isoformat(),
        "expires_at": (liveness_checked_at + timedelta(seconds=120)).isoformat(),
        "nonce": secrets.token_hex(32),
        "receipt_digest": "sha256:" + hashlib.sha256(encoded_receipt).hexdigest(),
        "receipt_key_id": payload["receipt_key_id"],
        "liveness_key_id": hashlib.sha256(liveness_public_key_raw).hexdigest(),
        "tenant_id": payload["tenant_id"],
        "deployment_id": payload["deployment_id"],
        "backup_digest": payload["backup_digest"],
        "backup_object_name": payload["backup_object_name"],
        "storage_profile_fingerprint": payload["storage_profile_fingerprint"],
        "filesystem_type": payload["filesystem_type"],
        "mount_id": payload["mount_id"],
        "mount_source_fingerprint": payload["mount_source_fingerprint"],
        "namespace_check": "reopen_nofollow_mount_identity_match",
        "provider_immutability": "object_lock_attested",
        "provider_attestation_digest": "sha256:" + ("e" * 64),
        "provider_key_id": "f" * 64,
        "provider_object_version": "test-object-version-a1",
        "retention_until": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
    }
    liveness_payload["liveness_signature"] = sign_offhost_liveness_payload(
        liveness_payload
    )
    liveness_dir = tmp_path / "offhost-liveness"
    liveness_dir.mkdir()
    liveness_file = liveness_dir / "current.json"
    liveness_file.write_text(json.dumps(liveness_payload), encoding="utf-8")
    monkeypatch.setenv(OFFHOST_RESTORE_RECEIPT_FILE_ENV, str(receipt))
    monkeypatch.setenv(
        "AGENTIOT_OFFHOST_RESTORE_LIVENESS_FILE",
        str(liveness_file),
    )
    monkeypatch.setenv(OFFHOST_RESTORE_BACKUP_FILE_ENV, str(backup))
    monkeypatch.setenv(
        OFFHOST_RESTORE_LEDGER_FILE_ENV,
        str(tmp_path / "offhost-restore-ledger.json"),
    )
    monkeypatch.setenv(
        OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
        "sha256:" + hashlib.sha256(encoded_receipt).hexdigest(),
    )
    return receipt


def seed_bearer_assignment(
    client,
    monkeypatch: pytest.MonkeyPatch | None,
    *,
    subject: str = "operator@example.test",
    role: str = "operator",
    scopes: list[str] | None = None,
    status: str = "active",
) -> dict:
    """Create a contact-safe local assignment for a bearer subject."""

    response = client.patch(
        f"/api/admin/access/users/{assignable_subject_id(subject)}",
        headers=admin_token_headers(monkeypatch),
        json={
            "role": role,
            "scopes": scopes or ["device:write", "telemetry:write", "recovery:approve"],
            "status": status,
            "note": "Test assignment without contact data.",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def make_test_rs256_jwt(
    *,
    issuer: str = "https://idp.example.test",
    audience: str | list[str] = "agentiot-dashboard",
    subject: str = "operator-rs256@example.test",
    role: str = "operator",
    scope: str = "device:write telemetry:write recovery:approve",
    expires_in: int = 3600,
    tenant_id: str = "greenovax",
) -> tuple[str, object]:
    """Create a compact RS256 JWT and public key for JWKS validation tests."""

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    payload = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "role": role,
        "scope": scope,
        "exp": int(time.time()) + expires_in,
        "tenant_id": tenant_id,
    }
    token = jwt.encode(
        payload,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-rs256-key"},
    )
    return token, private_key.public_key()
