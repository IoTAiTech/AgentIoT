# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

import base64
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import agentiot.app as app_module


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (PROJECT_ROOT / "VERSION").read_text().strip()


def test_dockerfile_declares_healthcheck() -> None:
    dockerfile = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()

    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8080/readyz" in dockerfile
    assert "USER agentiot" in dockerfile
    assert "FROM python:3.12-alpine@sha256:" in dockerfile
    assert "adduser -S -D -H -G agentiot agentiot" in dockerfile
    assert "mkdir -p /app/output /app/data" in dockerfile
    assert "COPY requirements.txt requirements.lock ./" in dockerfile
    assert "COPY --chown=agentiot:agentiot README.en.md README.de.md CHANGELOG.md LICENSE NOTICE.md ./" in dockerfile
    assert "COPY --chown=agentiot:agentiot docs/customer ./docs/customer" in dockerfile
    assert "COPY --chown=agentiot:agentiot docs/contract ./docs/contract" in dockerfile
    assert "COPY --chown=agentiot:agentiot docs/adr ./docs/adr" in dockerfile
    assert "COPY --chown=agentiot:agentiot docs/governance ./docs/governance" not in dockerfile
    assert "COPY --chown=agentiot:agentiot docs/index ./docs/index" not in dockerfile
    assert "COPY --chown=agentiot:agentiot " + "AGENTS.md" not in dockerfile
    assert "COPY --chown=agentiot:agentiot internal" not in dockerfile
    assert "COPY --chown=agentiot:agentiot tasks" not in dockerfile
    assert "chmod -R a+rX /app/src /app/docs /app/output" in dockerfile
    assert (
        "chmod a+r /app/README.en.md /app/README.de.md /app/CHANGELOG.md"
        in dockerfile
    )
    assert "/app/LICENSE /app/NOTICE.md" in dockerfile
    assert "pip==26.1.2" in dockerfile
    assert "--require-hashes -r requirements.lock" in dockerfile
    assert 'org.greenovax.agentiot.restore-evidence-epoch="5"' in dockerfile


def test_compose_uses_operational_host_port_8040() -> None:
    compose = (PROJECT_ROOT / "docker" / "compose.yaml").read_text()

    assert "container_name: agentiot-greenovax-8040" in compose
    assert f"image: agentiot-greenovax:{CURRENT_VERSION}" in compose
    assert '"127.0.0.1:8040:8080"' in compose
    assert '"8040:8080"' not in compose
    assert 'AGENTIOT_ENV: "${AGENTIOT_ENV:-production}"' in compose
    assert 'AGENTIOT_DB_PATH: "/app/data/agentiot-greenovax.db"' in compose
    assert 'AGENTIOT_TLS_TERMINATION: "${AGENTIOT_TLS_TERMINATION:-}"' in compose
    assert "AGENTIOT_ALLOWED_HOSTS:?Set AGENTIOT_ALLOWED_HOSTS" in compose
    assert "AGENTIOT_ALLOWED_HOSTS:-*" not in compose
    assert 'AGENTIOT_OPERATOR_TOKEN_FILE: "/run/secrets/operator_token"' in compose
    assert 'AGENTIOT_ADMIN_TOKEN_FILE: "/run/secrets/admin_token"' in compose
    assert 'AGENTIOT_OPERATOR_TOKEN: ' not in compose
    assert "secrets:" in compose
    assert "operator_token:" in compose
    assert "admin_token:" in compose
    repo_local_secret_prefix = ".." + "/secrets/"
    assert repo_local_secret_prefix not in compose
    assert "/var/lib/agentiot-greenovax/secrets/operator_token" in compose
    assert "/var/lib/agentiot-greenovax/secrets/admin_token" in compose
    assert "AGENTIOT_IDP_ISSUER" in compose
    assert "AGENTIOT_IDP_AUDIENCE" in compose
    assert 'AGENTIOT_IDP_SHARED_SECRET_FILE: "/run/secrets/idp_shared_secret"' in compose
    assert "idp_shared_secret:" in compose
    assert "AGENTIOT_IDP_SHARED_SECRET: " not in compose
    assert "AGENTIOT_IDP_JWKS_URL" in compose
    assert 'AGENTIOT_CREDENTIAL_FERNET_KEY_FILE: "/run/secrets/credential_fernet_key"' in compose
    assert "credential_fernet_key:" in compose
    assert "AGENTIOT_CREDENTIAL_FERNET_KEY: " not in compose
    assert "AGENTIOT_AI_ALLOW_LOCAL_CALLS" in compose
    assert "AGENTIOT_AI_ALLOW_CLOUD_CALLS" in compose
    assert "AGENTIOT_AI_LOCAL_MODEL" in compose
    assert "AGENTIOT_AI_CLOUD_PROVIDER" in compose
    assert "OPENAI_API_KEY" not in compose
    assert "GEMINI_API_KEY" not in compose
    assert "HF_TOKEN" not in compose
    assert "AGENTIOT_BOOTSTRAP_DEMO_DATA" in compose
    assert "AGENTIOT_BACKUP_POLICY" in compose
    assert "AGENTIOT_BACKUP_RETENTION_DAYS" in compose
    assert "AGENTIOT_BACKUP_CADENCE_HOURS" in compose
    assert "AGENTIOT_BACKUP_LAST_RESTORE_TEST_AT" in compose
    assert "AGENTIOT_OFFHOST_RESTORE_RECEIPT_DIGEST:?Set the SHA-256 digest" in compose
    assert (
        'AGENTIOT_OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_FILE: '
        '"/run/secrets/offhost_restore_receipt_public_key"'
    ) in compose
    assert (
        'AGENTIOT_OFFHOST_RESTORE_LIVENESS_PUBLIC_KEY_FILE: '
        '"/run/secrets/offhost_restore_liveness_public_key"'
    ) in compose
    assert 'AGENTIOT_OFFHOST_RESTORE_LIVENESS_FILE: "/run/agentiot-liveness/current.json"' in compose
    assert 'AGENTIOT_OFFHOST_RESTORE_BACKUP_FILE: "/run/agentiot-restore/backup.sqlite"' in compose
    assert 'AGENTIOT_OFFHOST_RESTORE_LEDGER_FILE: "/app/data/offhost-restore-ledger.json"' in compose
    assert 'restart: "no"' in compose
    assert "restart: unless-stopped" not in compose
    assert 'target: /run/agentiot-restore/receipt.json' in compose
    assert 'target: /run/agentiot-restore/backup.sqlite' in compose
    assert 'target: /run/agentiot-liveness' in compose
    assert "create_host_path: false" in compose
    assert ":/run/agentiot-restore/receipt.json:ro" not in compose
    assert "AGENTIOT_MQTT_BROKER_HOST" in compose
    assert 'AGENTIOT_MQTT_PASSWORD_FILE: "/run/secrets/mqtt_password"' in compose
    assert 'AGENTIOT_MQTT_CA_CERT_FILE: "/run/secrets/mqtt_ca_cert"' in compose
    assert 'AGENTIOT_MQTT_CLIENT_CERT_FILE: "/run/secrets/mqtt_client_cert"' in compose
    assert 'AGENTIOT_MQTT_CLIENT_KEY_FILE: "/run/secrets/mqtt_client_key"' in compose
    assert "mqtt_password:" in compose
    assert "mqtt_ca_cert:" in compose
    assert "mqtt_client_cert:" in compose
    assert "mqtt_client_key:" in compose
    assert "AGENTIOT_MQTT_PASSWORD: " not in compose
    assert "AGENTIOT_MQTT_CA_CERT: " not in compose
    assert "AGENTIOT_MQTT_CLIENT_CERT: " not in compose
    assert "AGENTIOT_MQTT_CLIENT_KEY: " not in compose
    assert "AGENTIOT_MQTT_AUTOSTART" in compose
    assert "AGENTIOT_HARDWARE_SIMULATOR_PLUGIN" in compose
    assert "AGENTIOT_HARDWARE_SIMULATOR_ALLOW_PRODUCTION" in compose
    assert "agentiot_product_data:/app/data" in compose
    assert "agentiot_product_data:" in compose
    assert "read_only: true" in compose
    assert "tmpfs:" in compose
    assert "/tmp:rw,noexec,nosuid,size=64m" in compose
    assert "cap_drop:" in compose
    assert "- ALL" in compose
    assert "security_opt:" in compose
    assert "no-new-privileges:true" in compose
    assert "pids_limit: 256" in compose
    assert "mem_limit: 768m" in compose


def test_docker_context_includes_current_visual_evidence() -> None:
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text()

    assert "!output/playwright/" in dockerignore
    assert f"!output/playwright/agentiot-v{CURRENT_VERSION}-*.png" in dockerignore
    assert f"!output/playwright/agentiot-v{CURRENT_VERSION}-visual-report.json" in dockerignore
    assert f"!output/playwright/agentiot-v{CURRENT_VERSION}-*\n" not in dockerignore


def test_https_reverse_proxy_launcher_is_versioned_and_secret_free() -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()
    proxy_config = (PROJECT_ROOT / "docker" / "nginx-https-8040.conf").read_text()

    assert f"Version: {CURRENT_VERSION}" in launcher
    assert "#!/usr/bin/env bash" in launcher
    assert "set -euo pipefail" in launcher
    assert "AGENTIOT_ALLOWED_HOSTS is required" in launcher
    assert "agentiot-greenovax-app-8040" in launcher
    assert "agentiot-greenovax-https-8040" in launcher
    assert 'app_port="${AGENTIOT_APP_PORT:-18080}"' in launcher
    assert 'https_port="${AGENTIOT_HTTPS_PORT:-8040}"' in launcher
    assert '127.0.0.1:${app_port}:8080' in launcher
    assert 'AGENTIOT_TLS_TERMINATION="reverse-proxy"' in launcher
    assert "agentiot_greenovax_runtime" in launcher
    assert "docker network create" in launcher
    assert "--network-alias agentiot-app" in launcher
    assert 'AGENTIOT_OPERATOR_TOKEN_FILE="/run/secrets/operator_token"' in launcher
    assert 'AGENTIOT_ADMIN_TOKEN_FILE="/run/secrets/admin_token"' in launcher
    assert "sync_app_secret_ownership" in launcher
    assert 'id -u agentiot' in launcher
    assert 'id -g agentiot' in launcher
    assert 'AGENTIOT_HARDWARE_SIMULATOR_PLUGIN="${AGENTIOT_HARDWARE_SIMULATOR_PLUGIN:-disabled}"' in launcher
    assert 'AGENTIOT_HARDWARE_SIMULATOR_ALLOW_PRODUCTION="${AGENTIOT_HARDWARE_SIMULATOR_ALLOW_PRODUCTION:-}"' in launcher
    assert 'AGENTIOT_BOOTSTRAP_DEMO_DATA="${AGENTIOT_BOOTSTRAP_DEMO_DATA:-0}"' in launcher
    assert 'AGENTIOT_BOOTSTRAP_DEMO_DATA="${AGENTIOT_BOOTSTRAP_DEMO_DATA:-1}"' not in launcher
    assert 'chmod 600 "${target_file}"' in launcher
    assert 'chmod 700 "${tls_dir}"' in launcher
    assert 'tls_cert_file="${tls_dir}/tls.crt"' in launcher
    assert 'tls_key_file="${tls_dir}/tls.key"' in launcher
    assert '"${AGENTIOT_TLS_CERT_FILE:-}" "${persistent_tls_dir}/tls.crt"' in launcher
    assert '"${AGENTIOT_TLS_KEY_FILE:-}" "${persistent_tls_dir}/tls.key"' in launcher
    assert 'credential_fernet_key_file="${secret_dir}/credential_fernet_key"' in launcher
    assert 'stage_fernet_key_file "${credential_fernet_key_file}"' in launcher
    assert "A deployment-owned credential Fernet key is required in production." in launcher
    assert 'offhost_restore_receipt_digest=""' in launcher
    assert 'offhost_restore_runtime_file="/run/agentiot-restore/receipt.json"' in launcher
    assert 'offhost_restore_backup_runtime_file="/run/agentiot-restore/backup.sqlite"' in launcher
    assert "/offhost/restore-receipt/latest-restore-receipt.json" in launcher
    assert 'offhost_restore_required="1"' in launcher
    assert 'AGENTIOT_ENV="production"' in launcher
    assert "requires AGENTIOT_ENV=production" in launcher
    assert "requires off-host restore evidence" in launcher
    assert "receipt must not be group- or world-writable" in launcher
    assert "receipt must not be a symbolic link" in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_RECEIPT_DIGEST=${offhost_restore_receipt_digest}' in launcher
    assert '--mount "type=bind,source=${offhost_restore_receipt_source},target=${offhost_restore_runtime_file},readonly"' in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_RECEIPT_FILE=${offhost_restore_runtime_file}' in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_FILE=/run/secrets/offhost_restore_receipt_public_key' in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_BACKUP_FILE=${offhost_restore_backup_runtime_file}' in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_LIVENESS_FILE=${offhost_restore_liveness_runtime_file}' in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_LIVENESS_PUBLIC_KEY_FILE=/run/secrets/offhost_restore_liveness_public_key' in launcher
    assert 'AGENTIOT_OFFHOST_RESTORE_LEDGER_FILE=/app/data/offhost-restore-ledger.json' in launcher
    assert "--restart unless-stopped" not in launcher
    assert "verify_offhost_receipt_mount" in launcher
    assert "App container did not receive the exact read-only restore receipt." in launcher
    assert "App container did not receive the exact read-only backup object." in launcher
    assert "App container did not receive the live read-only proof directory." in launcher
    assert "verify_image_restore_epoch" in launcher
    assert "verify_existing_runtime_restore_epoch" in launcher
    assert "restore-evidence-epoch" in launcher
    assert '${offhost_restore_receipt_directory}:/run/agentiot-restore:ro' not in launcher
    assert '--proxy-headers "--forwarded-allow-ips=*"' in launcher
    assert 'AGENTIOT_CREDENTIAL_FERNET_KEY_FILE="/run/secrets/credential_fernet_key"' in launcher
    assert ':/run/secrets/credential_fernet_key:ro"' in launcher
    assert "mqtt_docker_args=(" in launcher
    assert "mqtt_secret_args=()" in launcher
    assert "stage_mqtt_secret" in launcher
    for mqtt_name in (
        "AGENTIOT_MQTT_BROKER_HOST",
        "AGENTIOT_MQTT_BROKER_PORT",
        "AGENTIOT_MQTT_CLIENT_ID",
        "AGENTIOT_MQTT_USERNAME",
        "AGENTIOT_MQTT_TOPIC_PREFIX",
        "AGENTIOT_MQTT_QOS",
        "AGENTIOT_MQTT_KEEPALIVE",
        "AGENTIOT_MQTT_TLS",
        "AGENTIOT_MQTT_AUTOSTART",
    ):
        assert f'-e "{mqtt_name}=${{{mqtt_name}:-}}"' in launcher
    assert '"${mqtt_docker_args[@]}"' in launcher
    assert '"${mqtt_secret_args[@]}"' in launcher
    assert '"/run/secrets/mqtt_password" "AGENTIOT_MQTT_PASSWORD_FILE"' in launcher
    assert '"/run/secrets/mqtt_ca_cert" "AGENTIOT_MQTT_CA_CERT_FILE"' in launcher
    assert '"/run/secrets/mqtt_client_cert" "AGENTIOT_MQTT_CLIENT_CERT_FILE"' in launcher
    assert '"/run/secrets/mqtt_client_key" "AGENTIOT_MQTT_CLIENT_KEY_FILE"' in launcher
    assert 'tls_domain="${AGENTIOT_TLS_DOMAIN:-}"' in launcher
    assert 'use_tailscale_cert="${AGENTIOT_USE_TAILSCALE_CERT:-0}"' in launcher
    assert 'tls_cert_source="${AGENTIOT_TLS_CERT_SOURCE:-self-signed-lab}"' in launcher
    assert 'tls_browser_trusted="${AGENTIOT_TLS_BROWSER_TRUSTED:-0}"' in launcher
    assert 'runtime_lock_file="${AGENTIOT_RUNTIME_LOCK_FILE:-${runtime_dir}/launcher.lock}"' in launcher
    assert 'runtime_lock_timeout="${AGENTIOT_RUNTIME_LOCK_TIMEOUT:-120}"' in launcher
    assert 'flock -w "${runtime_lock_timeout}" "${runtime_lock_fd}"' in launcher
    assert "/tmp/agentiot-greenovax-8040.runtime.lock" not in launcher
    assert 'readiness_attempts="${AGENTIOT_READINESS_ATTEMPTS:-60}"' in launcher
    assert "acquire_runtime_lock" in launcher
    assert "release_runtime_lock" in launcher
    assert "preserve_existing_runtime" in launcher
    assert "restore_existing_runtime" in launcher
    assert "commit_new_runtime" in launcher
    assert "deployment_exit" in launcher
    assert "trap deployment_exit EXIT" in launcher
    assert "trap 'exit 130' INT TERM" in launcher
    assert launcher.count('docker rm -f "${proxy_container}" "${app_container}"') == 1
    assert "wait_for_app_ready" in launcher
    assert "wait_for_proxy_ready" in launcher
    assert '"http://127.0.0.1:${app_port}/readyz"' in launcher
    assert 'public_access_url="${AGENTIOT_PUBLIC_ACCESS_URL:-}"' in launcher
    assert 'tls_cert_source="${AGENTIOT_TLS_CERT_SOURCE:-tailscale}"' in launcher
    assert 'tls_browser_trusted="${AGENTIOT_TLS_BROWSER_TRUSTED:-1}"' in launcher
    assert 'AGENTIOT_TLS_CERT_SOURCE="${tls_cert_source}"' in launcher
    assert 'AGENTIOT_TLS_BROWSER_TRUSTED="${tls_browser_trusted}"' in launcher
    assert 'AGENTIOT_PUBLIC_ACCESS_URL="${public_access_url}"' in launcher
    assert "tailscale cert" in launcher
    assert "--cert-file" in launcher
    assert "--key-file" in launcher
    assert "*.ts.net" in launcher
    assert "TLS certificate source: Tailscale MagicDNS certificate" in launcher
    assert "private self-signed lab certificate" in launcher
    assert "browser-trusted access requires customer TLS or local trust import" in launcher
    assert 'openssl req -x509' in launcher
    assert 'chmod 600 "${tls_key_file}"' in launcher
    assert 'chmod 644 "${tls_cert_file}"' in launcher
    assert 'AGENTIOT_OPERATOR_TOKEN="' not in launcher
    assert 'AGENTIOT_ADMIN_TOKEN="' not in launcher
    assert "--read-only" in launcher
    assert "--cap-drop ALL" in launcher
    assert "--cap-add CHOWN" in launcher
    assert "--cap-add SETGID" in launcher
    assert "--cap-add SETUID" in launcher
    assert "--cap-add DAC_READ_SEARCH" in launcher
    assert "no-new-privileges:true" in launcher
    assert 'data_volume="${AGENTIOT_DATA_VOLUME:-}"' in launcher
    assert "resolve_data_volume_name" in launcher
    assert '-v "${data_volume}:/app/data"' in launcher
    local_home = "/" + "home" + "/" + "iot"
    assert local_home not in launcher
    assert "192.168." not in launcher
    assert "100.109." not in launcher
    assert "BEGIN " not in launcher
    pinned_nginx_image = "nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10"
    assert launcher.count(pinned_nginx_image) == 2
    assert "nginx:1.27-alpine nginx" not in launcher
    assert "listen 8443 ssl" in proxy_config
    assert "error_page 497 =400 @https_required" in proxy_config
    assert "location @https_required" in proxy_config
    assert "return 400" in proxy_config
    assert "proxy_set_header Host $http_host;" in proxy_config
    assert "proxy_pass http://agentiot-app:8080" in proxy_config
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in proxy_config
    assert "$proxy_add_x_forwarded_for" not in proxy_config
    assert "BEGIN " not in proxy_config


def test_offhost_restore_receipt_is_container_readable(tmp_path: Path) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_restore_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = tmp_path / "latest-restore-receipt.json"

    module.atomic_json_write(receipt, {"status": "verified"})

    assert stat.S_IMODE(receipt.stat().st_mode) == 0o644
    assert list(receipt.parent.iterdir()) == [receipt]


def test_offhost_restore_receipt_tool_binds_identity_and_signature() -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_restore_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = {
        "schema_version": module.OFFHOST_RESTORE_RECEIPT_SCHEMA,
        "tenant_id": "greenovax",
        "release_version": "0.156.0",
        "source_commit": "a" * 40,
        "runtime_digest": "sha256:" + ("b" * 64),
    }

    signing_key = Ed25519PrivateKey.generate()
    signature = module.receipt_signature(payload, signing_key)
    changed = module.receipt_signature(
        {**payload, "tenant_id": "another-customer"},
        signing_key,
    )
    source = tool_path.read_text(encoding="utf-8")

    assert signature.startswith("ed25519:")
    assert signature != changed
    assert "create_local_sqlite_backup(source_db, staging_path)" in source
    assert "--internal-copy-worker" in source
    assert 'parser.add_argument("--timeout-seconds", type=float, default=120.0)' in source
    assert "os.O_WRONLY" in source
    assert "os.O_CREAT" in source
    assert "os.O_EXCL" in source
    assert "dir_fd=directory_fd" in source
    assert 'parser.add_argument("--tenant-id", required=True)' in source
    assert 'parser.add_argument("--source-commit", required=True)' in source
    assert 'parser.add_argument("--runtime-digest", required=True)' in source
    assert 'parser.add_argument("--signing-key-file", type=Path, required=True)' in source
    assert 'parser.add_argument("--storage-profile-id", required=True)' in source
    assert 'parser.add_argument("--deployment-id", required=True)' in source
    assert (
        'parser.add_argument("--storage-profile-file", type=Path, required=True)'
        in source
    )
    assert 'worker_parser.add_argument("--expected-mount-source", required=True)' in source
    assert 'worker_parser.add_argument("--expected-filesystem-type", required=True)' in source
    assert 'worker_parser.add_argument("--staging-digest", required=True)' in source
    assert "agentiot.offhost-restore.v5" in source
    assert "source_db.as_uri()" in source
    assert "SQLite did not open the pinned source database" in source
    assert "Storage profile file is not deployment owned" in source
    assert "RENAME_NOREPLACE" in source
    assert "renameat2_noreplace" in source
    assert "backup_object_name" in source
    assert "verify_published_backup_for_receipt" in source
    assert "reopen_nofollow_match_signed_sha256" in source
    assert "file_fsync_and_directory_fsync" in source
    assert 'offhost_dir / "latest-restore-receipt.json"' not in source


def test_generated_v5_receipt_matches_runtime_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_v5_contract", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    signing_key = Ed25519PrivateKey.generate()
    signing_key_file = tmp_path / "receipt-key.pem"
    signing_key_file.write_bytes(
        signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    signing_key_file.chmod(0o600)
    public_key_pem = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    source_db = tmp_path / "source.sqlite"
    source_db.write_bytes(b"source")
    offhost_dir = tmp_path / "offhost"
    offhost_dir.mkdir()
    receipt_path = tmp_path / "receipt.json"
    mount_source = "//nas/greenovax"
    mount_fingerprint = "sha256:" + hashlib.sha256(
        mount_source.encode("utf-8")
    ).hexdigest()
    profile_fingerprint = "sha256:" + ("d" * 64)

    monkeypatch.setattr(
        module,
        "load_trusted_storage_profile",
        lambda *_args, **_kwargs: {
            "mount_source": mount_source,
            "filesystem_type": "cifs",
            "immutability_mode": "not_attested",
            "minimum_retention_days": 0,
            "profile_fingerprint": profile_fingerprint,
        },
    )

    def fake_snapshot(_source: Path, staging: Path) -> int:
        staging.write_bytes(b"bounded-test-backup")
        return int(staging.stat().st_dev)

    def fake_worker(command: list[str], _timeout: float) -> None:
        staging = Path(command[command.index("--staging-path") + 1])
        result = Path(command[command.index("--result-path") + 1])
        final_name = command[command.index("--final-name") + 1]
        result.write_text(
            json.dumps(
                {
                    "status": "verified",
                    "backup_digest": module.sha256_file(staging),
                    "quick_check": "ok",
                    "checked_records": 1,
                    "backup_size_bytes": staging.stat().st_size,
                    "filesystem_type": "cifs",
                    "mount_id": "42",
                    "mount_source_fingerprint": mount_fingerprint,
                    "durability": "file_fsync_and_directory_fsync",
                    "backup_object_name": final_name,
                    "publication": "renameat2_noreplace",
                    "writer_isolation": "owner_uid_match_no_world_write",
                    "storage_immutability": "not_attested",
                    "restore_consumer_requirement": (
                        "reopen_nofollow_match_signed_sha256_each_readiness"
                    ),
                    "storage_profile_id": "greenovax-nas-primary",
                }
            ),
            encoding="utf-8",
        )

    parent_evidence: dict[str, object] = {}

    def fake_parent_verification(**_kwargs) -> dict[str, object]:
        return dict(parent_evidence)

    monkeypatch.setattr(module, "create_local_sqlite_backup", fake_snapshot)
    monkeypatch.setattr(module, "run_supervised_worker", fake_worker)
    monkeypatch.setattr(
        module,
        "verify_published_backup_for_receipt",
        fake_parent_verification,
    )
    parent_evidence.update(
        {
            "quick_check": "ok",
            "checked_records": 1,
            "backup_size_bytes": len(b"bounded-test-backup"),
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source_fingerprint": mount_fingerprint,
            "writer_isolation": "owner_uid_match_no_world_write",
        }
    )
    source_commit = "a" * 40
    runtime_digest = "sha256:" + ("b" * 64)
    deployment_id = "test-deployment-2026"

    receipt = module.run_drill(
        source_db=source_db,
        offhost_dir=offhost_dir,
        receipt_path=receipt_path,
        release_version=CURRENT_VERSION,
        tenant_id="greenovax",
        deployment_id=deployment_id,
        source_commit=source_commit,
        runtime_digest=runtime_digest,
        signing_key_file=signing_key_file,
        storage_profile_id="greenovax-nas-primary",
        storage_profile_file=tmp_path / "unused-profile.json",
        trusted_profile_owner_uid=os.geteuid(),
    )

    assert set(receipt) == app_module.OFFHOST_RESTORE_RECEIPT_FIELDS
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_ENV,
        public_key_pem,
    )
    monkeypatch.delenv(
        app_module.OFFHOST_RESTORE_RECEIPT_PUBLIC_KEY_FILE_ENV,
        raising=False,
    )
    monkeypatch.setenv(app_module.OFFHOST_RESTORE_RECEIPT_FILE_ENV, str(receipt_path))
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_RECEIPT_DIGEST_ENV,
        module.sha256_file(receipt_path),
    )
    monkeypatch.setenv("AGENTIOT_TENANT_ID", "greenovax")
    monkeypatch.setenv("AGENTIOT_DEPLOYMENT_ID", deployment_id)
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", source_commit)
    monkeypatch.setenv("AGENTIOT_RUNTIME_DIGEST", runtime_digest)
    backup = tmp_path / str(receipt["backup_object_name"])
    backup.write_bytes(b"bounded-test-backup")
    monkeypatch.setenv(app_module.OFFHOST_RESTORE_BACKUP_FILE_ENV, str(backup))
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_LEDGER_FILE_ENV,
        str(tmp_path / "liveness-ledger.json"),
    )
    receipt_public_key_file = tmp_path / "receipt-public-key.pem"
    receipt_public_key_file.write_text(public_key_pem, encoding="utf-8")
    receipt_public_key_file.chmod(0o644)
    provider_key = Ed25519PrivateKey.generate()
    provider_public_key = provider_key.public_key()
    provider_public_key_file = tmp_path / "provider-public-key.pem"
    provider_public_key_file.write_bytes(
        provider_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    provider_public_key_file.chmod(0o644)
    provider_key_id = hashlib.sha256(
        provider_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).hexdigest()
    provider_issued_at = datetime.now(UTC)
    provider_attestation = {
        "schema_version": "agentiot.provider-object-lock.v1",
        "status": "object_lock_attested",
        "issued_at": provider_issued_at.isoformat(),
        "storage_profile_fingerprint": receipt["storage_profile_fingerprint"],
        "backup_object_name": receipt["backup_object_name"],
        "backup_digest": receipt["backup_digest"],
        "provider_object_version": "provider-version-test-a1",
        "retention_until": (provider_issued_at + timedelta(days=30)).isoformat(),
        "provider_key_id": provider_key_id,
    }
    provider_message = b"agentiot-provider-object-lock-v1\0" + json.dumps(
        provider_attestation,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    provider_attestation["provider_signature"] = (
        "ed25519:"
        + base64.urlsafe_b64encode(provider_key.sign(provider_message))
        .decode("ascii")
        .rstrip("=")
    )
    provider_attestation_file = tmp_path / "provider-attestation.json"
    provider_attestation_file.write_text(
        json.dumps(provider_attestation),
        encoding="utf-8",
    )
    provider_attestation_file.chmod(0o644)
    liveness_key = Ed25519PrivateKey.generate()
    liveness_private_key_file = tmp_path / "liveness-private-key.pem"
    liveness_private_key_file.write_bytes(
        liveness_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    liveness_private_key_file.chmod(0o600)
    liveness_public_key = liveness_key.public_key()
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_LIVENESS_PUBLIC_KEY_ENV,
        liveness_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii"),
    )
    liveness_tool_path = PROJECT_ROOT / "tools" / "issue_offhost_liveness_proof.py"
    monkeypatch.syspath_prepend(str(liveness_tool_path.parent))
    liveness_spec = importlib.util.spec_from_file_location(
        "offhost_liveness_contract",
        liveness_tool_path,
    )
    assert liveness_spec is not None and liveness_spec.loader is not None
    liveness_module = importlib.util.module_from_spec(liveness_spec)
    liveness_spec.loader.exec_module(liveness_module)
    monkeypatch.setattr(
        liveness_module.backup_drill,
        "load_trusted_storage_profile",
        lambda *_args, **_kwargs: {
            "mount_source": mount_source,
            "filesystem_type": "cifs",
            "immutability_mode": "not_attested",
            "minimum_retention_days": 0,
            "profile_fingerprint": profile_fingerprint,
        },
    )
    monkeypatch.setattr(
        liveness_module.backup_drill,
        "verify_published_backup_for_receipt",
        fake_parent_verification,
    )
    liveness_dir = tmp_path / "liveness"
    liveness_dir.mkdir()
    liveness_file = liveness_dir / "current.json"
    liveness = liveness_module.issue_liveness_proof(
        receipt_file=receipt_path,
        receipt_public_key_file=receipt_public_key_file,
        provider_attestation_file=provider_attestation_file,
        provider_public_key_file=provider_public_key_file,
        liveness_private_key_file=liveness_private_key_file,
        storage_profile_file=tmp_path / "unused-profile.json",
        storage_profile_id="greenovax-nas-primary",
        offhost_dir=offhost_dir,
        output_file=liveness_file,
        trusted_profile_owner_uid=os.geteuid(),
    )
    assert set(liveness) == app_module.OFFHOST_RESTORE_LIVENESS_FIELDS
    with pytest.raises(ValueError, match="must be independent"):
        liveness_module.issue_liveness_proof(
            receipt_file=receipt_path,
            receipt_public_key_file=receipt_public_key_file,
            provider_attestation_file=provider_attestation_file,
            provider_public_key_file=provider_public_key_file,
            liveness_private_key_file=signing_key_file,
            storage_profile_file=tmp_path / "unused-profile.json",
            storage_profile_id="greenovax-nas-primary",
            offhost_dir=offhost_dir,
            output_file=liveness_file,
            trusted_profile_owner_uid=os.geteuid(),
        )
    aliased_provider = dict(provider_attestation)
    aliased_provider.pop("provider_signature")
    aliased_provider["provider_key_id"] = receipt["receipt_key_id"]
    aliased_message = b"agentiot-provider-object-lock-v1\0" + json.dumps(
        aliased_provider,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    aliased_provider["provider_signature"] = (
        "ed25519:"
        + base64.urlsafe_b64encode(signing_key.sign(aliased_message))
        .decode("ascii")
        .rstrip("=")
    )
    provider_public_key_file.write_text(public_key_pem, encoding="utf-8")
    provider_attestation_file.write_text(
        json.dumps(aliased_provider),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Provider attestation key must be independent"):
        liveness_module.issue_liveness_proof(
            receipt_file=receipt_path,
            receipt_public_key_file=receipt_public_key_file,
            provider_attestation_file=provider_attestation_file,
            provider_public_key_file=provider_public_key_file,
            liveness_private_key_file=liveness_private_key_file,
            storage_profile_file=tmp_path / "unused-profile.json",
            storage_profile_id="greenovax-nas-primary",
            offhost_dir=offhost_dir,
            output_file=liveness_file,
            trusted_profile_owner_uid=os.geteuid(),
        )
    provider_public_key_file.write_bytes(
        provider_public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    provider_attestation_file.write_text(
        json.dumps(provider_attestation),
        encoding="utf-8",
    )
    monkeypatch.setenv(
        app_module.OFFHOST_RESTORE_LIVENESS_FILE_ENV,
        str(liveness_file),
    )

    status = app_module.offhost_restore_receipt_status(24)

    assert status["signature_verified"] is True
    assert status["state"] == "recorded"


def test_offhost_restore_table_profile_matches_runtime_validator() -> None:
    from agentiot import app as app_module

    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_profile_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.RESTORE_VERIFICATION_TABLES == (
        app_module.RESTORE_VERIFICATION_TABLES
    )


def test_offhost_worker_timeout_is_bounded() -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_timeout_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    started = time.monotonic()

    with pytest.raises(TimeoutError, match="worker timed out"):
        module.run_supervised_worker(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            0.05,
        )

    assert time.monotonic() - started < 5


def test_offhost_receipt_replace_failure_preserves_previous_receipt(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_atomic_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = tmp_path / "latest-restore-receipt.json"
    previous = b'{"status":"previous"}\n'
    receipt.write_bytes(previous)

    monkeypatch.setattr(
        module.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("forced replace failure")),
    )
    with pytest.raises(OSError, match="forced replace failure"):
        module.atomic_json_write(receipt, {"status": "verified"})

    assert receipt.read_bytes() == previous
    assert list(tmp_path.iterdir()) == [receipt]


def test_offhost_worker_rejects_same_device_before_publication(tmp_path: Path) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_device_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"not-read-on-same-device")
    result = tmp_path / "result.json"

    module.validate_remote_mount_profile = lambda *_args, **_kwargs: {
        "mount_id": "42",
        "filesystem_type": "cifs",
        "mount_source": "//nas/greenovax",
    }
    with pytest.raises(ValueError, match="independent storage"):
        module.copy_verify_offhost_worker(
            staging_path=staging,
            offhost_dir=tmp_path,
            final_name="agentiot-greenovax-test.sqlite",
            source_device=tmp_path.stat().st_dev,
            result_path=result,
            storage_profile_id="greenovax-nas-primary",
            expected_mount_source="//nas/greenovax",
            expected_filesystem_type="cifs",
            staging_digest=module.sha256_file(staging),
        )

    assert not result.exists()
    assert not (tmp_path / "agentiot-greenovax-test.sqlite").exists()


def test_offhost_mount_profile_uses_longest_match_and_exact_identity(
    tmp_path: Path,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_mount_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mount_root = tmp_path / "nas"
    target = mount_root / "greenovax" / "receipts"
    target.mkdir(parents=True)
    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        "31 20 0:30 / / rw,relatime - ext4 /dev/root rw\n"
        f"42 31 0:51 / {mount_root} rw,relatime - cifs //nas/general rw\n"
        f"41 42 0:52 / {mount_root / 'greenovax'} rw - autofs systemd-1 rw\n"
        f"43 41 0:53 / {mount_root / 'greenovax'} rw,relatime - cifs //nas/greenovax rw\n",
        encoding="utf-8",
    )

    profile = module.validate_remote_mount_profile(
        target,
        expected_mount_source="//nas/greenovax",
        expected_filesystem_type="cifs",
        mountinfo_path=mountinfo,
    )

    assert profile["mount_id"] == "43"
    assert profile["mount_source"] == "//nas/greenovax"
    with pytest.raises(ValueError, match="mount source"):
        module.validate_remote_mount_profile(
            target,
            expected_mount_source="//nas/wrong",
            expected_filesystem_type="cifs",
            mountinfo_path=mountinfo,
        )


def test_storage_profile_is_owner_bound_and_destination_allowlisted(
    tmp_path: Path,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_policy_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    destination = tmp_path / "approved"
    destination.mkdir()
    profile_file = tmp_path / "storage-profiles.json"
    profile_file.write_text(
        json.dumps(
            {
                "schema_version": module.OFFHOST_STORAGE_PROFILE_SCHEMA,
                "profiles": [
                    {
                        "storage_profile_id": "greenovax-nas-primary",
                        "destination_path": str(destination),
                        "filesystem_type": "cifs",
                        "mount_source": "//nas/greenovax",
                        "immutability_mode": "not_attested",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    profile_file.chmod(0o644)

    profile = module.load_trusted_storage_profile(
        profile_file,
        storage_profile_id="greenovax-nas-primary",
        offhost_dir=destination,
        trusted_owner_uid=os.geteuid(),
    )

    assert profile["filesystem_type"] == "cifs"
    assert profile["immutability_mode"] == "not_attested"
    assert str(profile["profile_fingerprint"]).startswith("sha256:")
    with pytest.raises(ValueError, match="deployment owned"):
        module.load_trusted_storage_profile(
            profile_file,
            storage_profile_id="greenovax-nas-primary",
            offhost_dir=destination,
            trusted_owner_uid=os.geteuid() + 1,
        )
    unapproved = tmp_path / "unapproved"
    unapproved.mkdir()
    with pytest.raises(ValueError, match="not allowlisted"):
        module.load_trusted_storage_profile(
            profile_file,
            storage_profile_id="greenovax-nas-primary",
            offhost_dir=unapproved,
            trusted_owner_uid=os.geteuid(),
        )
    profile_payload = json.loads(profile_file.read_text(encoding="utf-8"))
    profile_payload["profiles"][0]["immutability_mode"] = "object_lock_attested"
    profile_payload["profiles"][0]["minimum_retention_days"] = 30
    profile_file.write_text(json.dumps(profile_payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Provider-verifiable object-lock proof"):
        module.load_trusted_storage_profile(
            profile_file,
            storage_profile_id="greenovax-nas-primary",
            offhost_dir=destination,
            trusted_owner_uid=os.geteuid(),
        )


def test_source_snapshot_rejects_swap_even_when_path_is_restored(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_source_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source.sqlite"
    replacement = tmp_path / "replacement.sqlite"
    pinned_name = tmp_path / "source-pinned.sqlite"
    for path, marker in ((source, "trusted"), (replacement, "replacement")):
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES (?)", (marker,))
        connection.commit()
        connection.close()
    original_connect = module.sqlite3.connect
    swapped = False

    def swap_then_restore(database, *args, **kwargs):
        nonlocal swapped
        if not swapped and str(database).startswith("file:"):
            swapped = True
            source.rename(pinned_name)
            replacement.rename(source)
            connection = original_connect(database, *args, **kwargs)
            source.rename(replacement)
            pinned_name.rename(source)
            return connection
        return original_connect(database, *args, **kwargs)

    monkeypatch.setattr(module.sqlite3, "connect", swap_then_restore)
    with pytest.raises(ValueError, match="pinned source database"):
        module.create_local_sqlite_backup(source, tmp_path / "backup.sqlite")

    assert source.exists()
    assert replacement.exists()


def test_source_snapshot_rejects_symbolic_link(tmp_path: Path) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_source_link", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "source.sqlite"
    source.write_bytes(b"database")
    link = tmp_path / "source-link.sqlite"
    link.symlink_to(source)

    with pytest.raises(ValueError, match="symlinks are not allowed"):
        module.create_local_sqlite_backup(link, tmp_path / "backup.sqlite")


def test_source_snapshot_preserves_uncheckpointed_wal_commit(tmp_path: Path) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_wal_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path / "wal-source.sqlite"
    backup = tmp_path / "wal-backup.sqlite"
    connection = sqlite3.connect(source)
    try:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('committed-in-wal')")
        connection.commit()
        assert source.with_name(source.name + "-wal").stat().st_size > 0

        module.create_local_sqlite_backup(source, backup)
    finally:
        connection.close()

    restored = sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)
    try:
        assert restored.execute("SELECT value FROM marker").fetchone()[0] == (
            "committed-in-wal"
        )
    finally:
        restored.close()


def test_offhost_directory_fsync_failure_is_not_suppressed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_fsync_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module.os,
        "fsync",
        lambda *_args: (_ for _ in ()).throw(OSError("forced durability failure")),
    )

    with pytest.raises(OSError, match="forced durability failure"):
        module.fsync_directory(tmp_path)


def test_offhost_worker_detects_directory_entry_substitution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_inode_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"original-pinned-backup")
    result = tmp_path / "result.json"
    final_name = "agentiot-greenovax-substitution.sqlite"
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )

    def substitute_entry(_descriptor: int) -> tuple[str, int]:
        pending = next(tmp_path.glob(f".{final_name}.*.pending"))
        pending.unlink()
        pending.write_bytes(b"attacker-substitution")
        return "ok", 0

    monkeypatch.setattr(module, "verify_sqlite_backup_fd", substitute_entry)
    with pytest.raises(ValueError, match="changed during verification"):
        module.copy_verify_offhost_worker(
            staging_path=staging,
            offhost_dir=tmp_path,
            final_name=final_name,
            source_device=tmp_path.stat().st_dev + 1,
            result_path=result,
            storage_profile_id="greenovax-nas-primary",
            expected_mount_source="//nas/greenovax",
            expected_filesystem_type="cifs",
            staging_digest=module.sha256_file(staging),
        )

    assert not result.exists()
    assert not (tmp_path / final_name).exists()
    pending = list(tmp_path.glob(f".{final_name}.*.pending"))
    assert len(pending) == 1
    assert pending[0].read_bytes() == b"attacker-substitution"


def test_offhost_worker_publishes_with_noreplace_without_hard_link(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_cifs_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"pinned-cifs-backup")
    result = tmp_path / "result.json"
    final_name = "agentiot-greenovax-cifs.sqlite"
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )
    monkeypatch.setattr(
        module,
        "verify_sqlite_backup_fd",
        lambda _fd: ("ok", 1),
    )
    monkeypatch.setattr(
        module.os,
        "link",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("backup publication must not use hard links")
        ),
    )

    module.copy_verify_offhost_worker(
        staging_path=staging,
        offhost_dir=tmp_path,
        final_name=final_name,
        source_device=tmp_path.stat().st_dev + 1,
        result_path=result,
        storage_profile_id="greenovax-nas-primary",
        expected_mount_source="//nas/greenovax",
        expected_filesystem_type="cifs",
        staging_digest=module.sha256_file(staging),
    )

    assert result.exists()
    assert (tmp_path / final_name).read_bytes() == staging.read_bytes()
    result_payload = json.loads(result.read_text(encoding="utf-8"))
    assert result_payload["backup_object_name"] == final_name
    assert result_payload["publication"] == "renameat2_noreplace"
    assert result_payload["writer_isolation"] == "owner_uid_match_no_world_write"
    assert result_payload["storage_immutability"] == "not_attested"


def test_parent_reopens_published_name_before_receipt_signing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_parent_verify", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    final_name = "agentiot-greenovax-parent-verify.sqlite"
    final_path = tmp_path / final_name
    final_path.write_bytes(b"verified-parent-object")
    expected_digest = module.sha256_file(final_path)
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )
    monkeypatch.setattr(
        module,
        "verify_sqlite_backup_fd",
        lambda _descriptor: ("ok", 2),
    )

    verified = module.verify_published_backup_for_receipt(
        offhost_dir=tmp_path,
        backup_object_name=final_name,
        expected_backup_digest=expected_digest,
        expected_mount_source="//nas/greenovax",
        expected_filesystem_type="cifs",
    )

    assert verified == {
        "quick_check": "ok",
        "checked_records": 2,
        "backup_size_bytes": len(b"verified-parent-object"),
        "mount_id": "42",
        "filesystem_type": "cifs",
        "mount_source_fingerprint": (
            "sha256:"
            + hashlib.sha256(b"//nas/greenovax").hexdigest()
        ),
        "writer_isolation": "owner_uid_match_no_world_write",
    }
    final_path.write_bytes(b"substituted-parent-object")
    with pytest.raises(ValueError, match="does not match worker evidence"):
        module.verify_published_backup_for_receipt(
            offhost_dir=tmp_path,
            backup_object_name=final_name,
            expected_backup_digest=expected_digest,
            expected_mount_source="//nas/greenovax",
            expected_filesystem_type="cifs",
        )


def test_offhost_worker_tolerates_content_stable_cifs_metadata_settle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_cifs_metadata", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"content-stable-cifs-backup")
    result = tmp_path / "result.json"
    final_name = "agentiot-greenovax-cifs-metadata.sqlite"
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )
    monkeypatch.setattr(
        module,
        "verify_sqlite_backup_fd",
        lambda _descriptor: ("ok", 1),
    )
    original_sha256_fd = module.sha256_fd
    hash_calls = 0

    def settle_metadata_after_hash(descriptor: int) -> str:
        nonlocal hash_calls
        digest = original_sha256_fd(descriptor)
        hash_calls += 1
        if hash_calls == 4:
            pending = next(tmp_path.glob(f".{final_name}.*.pending"))
            current = pending.stat()
            os.utime(
                pending,
                ns=(current.st_atime_ns, current.st_mtime_ns + 1_000_000_000),
            )
        return digest

    monkeypatch.setattr(module, "sha256_fd", settle_metadata_after_hash)
    module.copy_verify_offhost_worker(
        staging_path=staging,
        offhost_dir=tmp_path,
        final_name=final_name,
        source_device=tmp_path.stat().st_dev + 1,
        result_path=result,
        storage_profile_id="greenovax-nas-primary",
        expected_mount_source="//nas/greenovax",
        expected_filesystem_type="cifs",
        staging_digest=module.sha256_file(staging),
    )

    assert result.exists()
    assert (tmp_path / final_name).read_bytes() == staging.read_bytes()


def test_offhost_worker_preserves_preexisting_final_object(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_noreplace", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"new-backup")
    result = tmp_path / "result.json"
    final_name = "agentiot-greenovax-existing.sqlite"
    final_path = tmp_path / final_name
    final_path.write_bytes(b"existing-backup")
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )
    monkeypatch.setattr(
        module,
        "verify_sqlite_backup_fd",
        lambda _descriptor: ("ok", 1),
    )

    with pytest.raises(FileExistsError):
        module.copy_verify_offhost_worker(
            staging_path=staging,
            offhost_dir=tmp_path,
            final_name=final_name,
            source_device=tmp_path.stat().st_dev + 1,
            result_path=result,
            storage_profile_id="greenovax-nas-primary",
            expected_mount_source="//nas/greenovax",
            expected_filesystem_type="cifs",
            staging_digest=module.sha256_file(staging),
        )

    assert final_path.read_bytes() == b"existing-backup"
    assert not result.exists()
    assert len(list(tmp_path.glob(f".{final_name}.*.pending"))) == 1


def test_offhost_worker_crash_leaves_only_hidden_pending(
    tmp_path: Path,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"x" * (2 * 1024 * 1024))
    result = tmp_path / "result.json"
    signal_file = tmp_path / "first-write"
    final_name = "agentiot-greenovax-crash.sqlite"
    child = tmp_path / "crash_worker.py"
    child.write_text(
        f"""
import importlib.util
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("offhost_crash", {str(tool_path)!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.validate_remote_mount_profile = lambda *_args, **_kwargs: {{
    "mount_id": "42",
    "filesystem_type": "cifs",
    "mount_source": "//nas/greenovax",
}}
original_write = module.os.write
first_write = True

def slow_after_first_write(descriptor, content):
    global first_write
    written = original_write(descriptor, content)
    if first_write:
        first_write = False
        Path({str(signal_file)!r}).write_text("written", encoding="ascii")
        time.sleep(60)
    return written

module.os.write = slow_after_first_write
staging = Path({str(staging)!r})
module.copy_verify_offhost_worker(
    staging_path=staging,
    offhost_dir=Path({str(tmp_path)!r}),
    final_name={final_name!r},
    source_device=Path({str(tmp_path)!r}).stat().st_dev + 1,
    result_path=Path({str(result)!r}),
    storage_profile_id="greenovax-nas-primary",
    expected_mount_source="//nas/greenovax",
    expected_filesystem_type="cifs",
    staging_digest=module.sha256_file(staging),
)
""",
        encoding="utf-8",
    )
    process = subprocess.Popen(
        [sys.executable, str(child)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 10
    pending: list[Path] = []
    while time.monotonic() < deadline:
        pending = list(tmp_path.glob(f".{final_name}.*.pending"))
        if signal_file.exists() and pending:
            break
        time.sleep(0.02)
    else:
        process.kill()
        process.wait(timeout=5)
        pytest.fail("worker did not reach the first pending write")

    process.kill()
    process.wait(timeout=5)

    assert not result.exists()
    assert not (tmp_path / final_name).exists()
    assert len(pending) == 1
    assert 0 < pending[0].stat().st_size < staging.stat().st_size


def test_offhost_worker_rejects_world_writable_destination(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_writer_scope", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"writer-scope")
    result = tmp_path / "result.json"
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )
    tmp_path.chmod(0o707)
    try:
        with pytest.raises(ValueError, match="owner scoped"):
            module.copy_verify_offhost_worker(
                staging_path=staging,
                offhost_dir=tmp_path,
                final_name="agentiot-greenovax-writer-scope.sqlite",
                source_device=tmp_path.stat().st_dev + 1,
                result_path=result,
                storage_profile_id="greenovax-nas-primary",
                expected_mount_source="//nas/greenovax",
                expected_filesystem_type="cifs",
                staging_digest=module.sha256_file(staging),
            )
    finally:
        tmp_path.chmod(0o700)

    assert not result.exists()
    assert not list(tmp_path.glob(".*.pending"))


def test_offhost_worker_detects_same_inode_content_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_content_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"original-pinned-backup")
    result = tmp_path / "result.json"
    final_name = "agentiot-greenovax-content-mutation.sqlite"
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )

    def mutate_content(descriptor: int) -> tuple[str, int]:
        first = os.pread(descriptor, 1, 0)
        os.pwrite(descriptor, bytes([first[0] ^ 1]), 0)
        os.fsync(descriptor)
        return "ok", 0

    monkeypatch.setattr(module, "verify_sqlite_backup_fd", mutate_content)
    with pytest.raises(ValueError, match="content changed"):
        module.copy_verify_offhost_worker(
            staging_path=staging,
            offhost_dir=tmp_path,
            final_name=final_name,
            source_device=tmp_path.stat().st_dev + 1,
            result_path=result,
            storage_profile_id="greenovax-nas-primary",
            expected_mount_source="//nas/greenovax",
            expected_filesystem_type="cifs",
            staging_digest=module.sha256_file(staging),
        )

    assert not result.exists()
    assert not (tmp_path / final_name).exists()


def test_offhost_worker_rejects_staging_digest_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_staging_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    staging = tmp_path / "staging.sqlite"
    staging.write_bytes(b"pinned-staging-backup")
    result = tmp_path / "result.json"
    monkeypatch.setattr(
        module,
        "validate_remote_mount_profile",
        lambda *_args, **_kwargs: {
            "mount_id": "42",
            "filesystem_type": "cifs",
            "mount_source": "//nas/greenovax",
        },
    )

    with pytest.raises(ValueError, match="Staging backup digest"):
        module.copy_verify_offhost_worker(
            staging_path=staging,
            offhost_dir=tmp_path,
            final_name="agentiot-greenovax-staging-mismatch.sqlite",
            source_device=tmp_path.stat().st_dev + 1,
            result_path=result,
            storage_profile_id="greenovax-nas-primary",
            expected_mount_source="//nas/greenovax",
            expected_filesystem_type="cifs",
            staging_digest="sha256:" + ("0" * 64),
        )

    assert not result.exists()
    assert not (tmp_path / "agentiot-greenovax-staging-mismatch.sqlite").exists()


def test_offhost_receipt_mode_survives_restrictive_umask(tmp_path: Path) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_umask_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = tmp_path / "receipt.json"
    previous_umask = os.umask(0o077)
    try:
        module.exclusive_json_write(receipt, {"status": "verified"})
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(receipt.stat().st_mode) == 0o644


def test_offhost_receipt_rejects_parent_path_replacement(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_parent_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parent = tmp_path / "receipts"
    parent.mkdir()
    detached = tmp_path / "detached-receipts"
    receipt = parent / "receipt.json"
    original_link = module.os.link

    def replace_parent(*args, **kwargs):
        result = original_link(*args, **kwargs)
        parent.rename(detached)
        parent.mkdir()
        return result

    monkeypatch.setattr(module.os, "link", replace_parent)
    with pytest.raises(ValueError, match="directory changed"):
        module.exclusive_json_write(receipt, {"status": "verified"})

    assert list(parent.iterdir()) == []
    assert list(detached.iterdir()) == []


def test_offhost_receipt_cleans_both_links_when_temp_unlink_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_unlink_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = tmp_path / "receipt.json"
    original_unlink = module.os.unlink
    failed_once = False

    def fail_first_temporary_unlink(name, *args, **kwargs):
        nonlocal failed_once
        if str(name).startswith(".receipt.json.") and not failed_once:
            failed_once = True
            raise OSError("forced temporary unlink failure")
        return original_unlink(name, *args, **kwargs)

    monkeypatch.setattr(module.os, "unlink", fail_first_temporary_unlink)
    with pytest.raises(OSError, match="forced temporary unlink failure"):
        module.exclusive_json_write(receipt, {"status": "verified"})

    assert list(tmp_path.iterdir()) == []


def test_offhost_receipt_publication_never_replaces_existing_file(
    tmp_path: Path,
) -> None:
    tool_path = PROJECT_ROOT / "tools" / "run_offhost_backup_restore_drill.py"
    spec = importlib.util.spec_from_file_location("offhost_receipt_drill", tool_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = tmp_path / "receipt.json"
    receipt.write_bytes(b"previous-receipt")

    with pytest.raises(FileExistsError):
        module.exclusive_json_write(receipt, {"status": "verified"})

    assert receipt.read_bytes() == b"previous-receipt"
    assert list(tmp_path.iterdir()) == [receipt]


def test_https_launcher_requires_existing_fernet_key_in_production(tmp_path) -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()
    start = launcher.index("stage_fernet_key_file() {")
    end = launcher.index("\n}\n", start) + 3
    target = tmp_path / "credential_fernet_key"
    environment = os.environ.copy()
    environment.update({"AGENTIOT_ENV": "production", "TARGET": str(target)})

    result = subprocess.run(
        [
            "bash",
            "-c",
            launcher[start:end]
            + '\nstage_fernet_key_file "$TARGET" "" ""',
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "credential Fernet key is required" in result.stdout
    assert not target.exists()


def test_https_launcher_application_run_uses_compose_containment_contract() -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()
    app_name_index = launcher.index('--name "${app_container}"')
    app_run_start = launcher.rfind("docker run -d", 0, app_name_index)
    assert app_run_start != -1
    app_run_end = launcher.index("\n\nverify_offhost_receipt_mount", app_name_index)
    app_run_block = launcher[app_run_start:app_run_end]

    assert "--read-only" in app_run_block
    assert "--tmpfs /tmp:rw,noexec,nosuid,size=64m" in app_run_block
    assert "--cap-drop ALL" in app_run_block
    assert "--security-opt no-new-privileges:true" in app_run_block
    assert "--pids-limit 256" in app_run_block
    assert "--memory 768m" in app_run_block
    assert "--user" not in app_run_block
    assert '"${mqtt_docker_args[@]}"' in app_run_block
    assert '"${mqtt_secret_args[@]}"' in app_run_block
    assert '"${edge_ingest_args[@]}"' in app_run_block
    assert '-e "AGENTIOT_MQTT_PASSWORD=' not in app_run_block

    app_volume_lines = [
        line.strip().rstrip(" \\")
        for line in app_run_block.splitlines()
        if line.lstrip().startswith("-v ")
    ]
    assert app_volume_lines == [
        '-v "${data_volume}:/app/data"',
        '-v "${operator_token_file}:/run/secrets/operator_token:ro"',
        '-v "${admin_token_file}:/run/secrets/admin_token:ro"',
        '-v "${session_secret_file}:/run/secrets/session_secret:ro"',
        '-v "${credential_fernet_key_file}:/run/secrets/credential_fernet_key:ro"',
        '-v "${offhost_restore_receipt_public_key_file}:/run/secrets/offhost_restore_receipt_public_key:ro"',
        '-v "${offhost_restore_liveness_public_key_file}:/run/secrets/offhost_restore_liveness_public_key:ro"',
        '-v "${visual_evidence_dir}:/app/output/playwright:ro"',
    ]


def test_https_launcher_rejects_not_ready_payload_before_proxy_start() -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()
    function_start = launcher.index("readiness_payload_is_ready() {")
    function_end = launcher.index("\n}\n", function_start) + 3
    readiness_function = launcher[function_start:function_end]

    rejected = subprocess.run(
        [
            "bash",
            "-c",
            readiness_function
            + "\nreadiness_payload_is_ready '{\"status\":\"not_ready\"}'",
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    accepted = subprocess.run(
        [
            "bash",
            "-c",
            readiness_function + "\nreadiness_payload_is_ready '{\"status\":\"ready\"}'",
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )

    assert rejected.returncode != 0
    assert accepted.returncode == 0
    assert 'readiness_payload_is_ready "${ready_payload}"' in launcher
    readiness_gate = launcher.index("\nwait_for_app_ready\n")
    proxy_validation = launcher.index("\ndocker run --rm \\", readiness_gate)
    assert readiness_gate < proxy_validation
    proxy_start = launcher.index('\n  --name "${proxy_container}"', proxy_validation)
    proxy_ready = launcher.index("\nwait_for_proxy_ready\n", proxy_start)
    commit = launcher.index("\ncommit_new_runtime\n", proxy_ready)
    assert proxy_start < proxy_ready < commit


def test_https_launcher_lock_handles_stale_content_and_times_out(tmp_path) -> None:
    flock = shutil.which("flock")
    bash = shutil.which("bash")
    if flock is None or bash is None:
        pytest.skip("bash and flock are required for launcher lock tests")

    launcher = (PROJECT_ROOT / "docker/launch_https_proxy_8040.sh").read_text()
    acquire_start = launcher.index("acquire_runtime_lock() {")
    acquire_end = launcher.index("\n}\n", acquire_start) + 3
    release_start = launcher.index("release_runtime_lock() {")
    release_end = launcher.index("\n}\n", release_start) + 3
    functions = launcher[acquire_start:acquire_end] + launcher[release_start:release_end]
    runtime_dir = tmp_path / "runtime"
    lock_file = runtime_dir / "launcher.lock"
    script = (
        'set -euo pipefail\n'
        'runtime_dir="$TEST_RUNTIME_DIR"\n'
        'runtime_lock_file="$TEST_LOCK_FILE"\n'
        'runtime_lock_timeout="$TEST_LOCK_TIMEOUT"\n'
        'runtime_lock_fd=""\n'
        + functions
        + "\nacquire_runtime_lock\nrelease_runtime_lock\n"
    )
    env = {
        **os.environ,
        "TEST_RUNTIME_DIR": str(runtime_dir),
        "TEST_LOCK_FILE": str(lock_file),
        "TEST_LOCK_TIMEOUT": "1",
    }

    for stale_content in (None, "", "not-a-pid\n"):
        runtime_dir.mkdir(parents=True, exist_ok=True)
        if stale_content is None:
            lock_file.unlink(missing_ok=True)
        else:
            lock_file.write_text(stale_content, encoding="utf-8")
        result = subprocess.run(
            [bash, "-c", script],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
        assert result.returncode == 0, result.stderr

    marker = tmp_path / "holder-ready"
    holder = subprocess.Popen(
        [flock, "-x", str(lock_file), "-c", f"touch '{marker}'; sleep 5"],
        text=True,
    )
    try:
        deadline = time.monotonic() + 2
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.exists()
        blocked = subprocess.run(
            [bash, "-c", script],
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
        assert blocked.returncode != 0
        assert "Timed out waiting for AgentIoT runtime lock" in (
            blocked.stdout + blocked.stderr
        )
    finally:
        holder.terminate()
        holder.wait(timeout=3)


def test_https_launcher_preserves_previous_runtime_until_candidate_is_ready() -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()

    preserve = launcher.index("\npreserve_existing_runtime\n")
    app_start = launcher.index('\n  --name "${app_container}"', preserve)
    app_ready = launcher.index("\nwait_for_app_ready\n", app_start)
    proxy_start = launcher.index('\n  --name "${proxy_container}"', app_ready)
    commit = launcher.index("\ncommit_new_runtime\n", proxy_start)
    assert preserve < app_start < app_ready < proxy_start < commit
    assert 'docker rename "${rollback_name}" "${current_name}"' in launcher
    assert 'docker start "${current_name}"' in launcher
    assert "restore_errors=0" in launcher
    assert "restore_runtime_container" in launcher
    assert "wait_for_proxy_ready" in launcher


def test_https_launcher_restores_app_and_proxy_independently_on_failure(
    tmp_path,
) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is required for launcher rollback tests")
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()
    functions = []
    for name in ("restore_runtime_container", "restore_existing_runtime"):
        start = launcher.index(f"{name}() {{")
        end = launcher.index("\n}\n", start) + 3
        functions.append(launcher[start:end])
    log_path = tmp_path / "docker.log"
    script = (
        'set -u\n'
        'app_container="app"\n'
        'proxy_container="proxy"\n'
        'rollback_app_container="app-old"\n'
        'rollback_proxy_container="proxy-old"\n'
        'rollback_app_stopped=0\n'
        'rollback_proxy_stopped=0\n'
        'new_runtime_started=1\n'
        'had_existing_runtime=1\n'
        'restore_errors=0\n'
        'docker() {\n'
        '  printf "%s\\n" "$*" >> "$TEST_DOCKER_LOG"\n'
        '  if [ "$*" = "start app" ]; then return 1; fi\n'
        '  return 0\n'
        '}\n'
        'wait_for_proxy_ready() { return 0; }\n'
        + "\n".join(functions)
        + '\nif restore_existing_runtime; then exit 91; fi\n'
        'grep -Fx "rename app-old app" "$TEST_DOCKER_LOG"\n'
        'grep -Fx "start app" "$TEST_DOCKER_LOG"\n'
        'grep -Fx "rename proxy-old proxy" "$TEST_DOCKER_LOG"\n'
        'grep -Fx "start proxy" "$TEST_DOCKER_LOG"\n'
    )
    result = subprocess.run(
        [bash, "-c", script],
        env={**os.environ, "TEST_DOCKER_LOG": str(log_path)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_runtime_uses_one_canonical_data_volume_and_inherits_active_mount() -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()
    compose = (PROJECT_ROOT / "docker" / "compose.yaml").read_text()

    assert 'data_volume="${AGENTIOT_DATA_VOLUME:-}"' in launcher
    assert "resolve_data_volume_name()" in launcher
    assert '"/app/data"' in launcher
    assert 'agentiot_greenovax_product_data' in launcher
    assert "agentiot_product_data:/app/data" in compose
    assert 'name: "${AGENTIOT_DATA_VOLUME:-agentiot_greenovax_product_data}"' in compose
    assert "agentiot_data:/app/data" not in compose


def test_customer_release_builder_reads_local_backend_evidence_by_default() -> None:
    builder = (PROJECT_ROOT / "tools" / "build_customer_release.sh").read_text()

    assert "http://127.0.0.1:18080/api/project/drift-control" in builder
    assert 'evidence_url="http://127.0.0.1:18080/api/version"' in builder
    assert "http://127.0.0.1:8040/api/project/drift-control" not in builder


def test_tracked_visual_evidence_is_current_version_only() -> None:
    version = (PROJECT_ROOT / "VERSION").read_text().strip()
    tracked = subprocess.check_output(
        ["git", "ls-files", "output/playwright"],
        cwd=PROJECT_ROOT,
        text=True,
    ).splitlines()

    assert tracked
    assert len(tracked) >= 19
    assert all(f"agentiot-v{version}-" in path for path in tracked)
    assert any(path.endswith("-visual-report.json") for path in tracked)


def test_visual_qa_can_use_system_chrome_when_browser_bundle_is_missing() -> None:
    visual = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()

    assert "function chromiumLaunchOptions()" in visual
    assert "PLAYWRIGHT_CHROMIUM_EXECUTABLE" in visual
    assert "/usr/bin/google-chrome" in visual
    assert "chromium.launch(chromiumLaunchOptions())" in visual
    assert "controlClipCount" in visual
    assert "visible controls exceed their cards" in visual
    assert "protectedCollectionPaths" in visual
    assert "anonymous collection access did not fail closed" in visual
    assert "anonymous audit activity is not bounded and identity-free" in visual
    assert "AGENTIOT_RUNTIME_LOCK_DIR" in visual
    assert "acquireRuntimeLock('visual-qa')" in visual
    assert "releaseRuntimeLock" in visual
    assert "runtime lock timeout" in visual
    assert "runNoJavaScriptCredentialFormCheck" in visual
    assert "javaScriptEnabled: false" in visual
    assert "credential sentinel entered URL" in visual


def test_visual_qa_stale_runtime_lock_cleanup_is_bounded_and_nonrecursive() -> None:
    visual = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()

    assert "const runtimeLockRoot = fs.realpathSync.native('/tmp');" in visual
    assert "function validateRuntimeLockDir(lockDir)" in visual
    assert "path.dirname(resolvedLockDir) !== runtimeLockRoot" in visual
    assert "const expectedRuntimeLockMetadata = new Set(['pid', 'owner']);" in visual
    assert "unexpected runtime lock content" in visual
    assert "entryStat.nlink !== 1" in visual
    assert "fs.unlinkSync(path.join(runtimeLockDir, entry));" in visual
    assert "fs.rmdirSync(runtimeLockDir);" in visual
    assert "fs.rmSync(runtimeLockDir, { recursive: true, force: true })" not in visual


def test_visual_qa_retries_only_the_known_interaction_screenshot_transport_failure() -> None:
    visual = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()

    assert "const interactionScreenshotMaxAttempts = 2;" in visual
    assert "const interactionScreenshotRetryDelayMs = 250;" in visual
    assert "function isTransientInteractionScreenshotError(error)" in visual
    assert "async function captureInteractionScreenshotWithRetry(page, screenshotPath)" in visual
    assert "return String(error).includes(interactionScreenshotRetrySignature);" in visual
    assert "await page.waitForTimeout(interactionScreenshotRetryDelayMs);" in visual
    assert "const screenshotResult = await captureInteractionScreenshotWithRetry(page, screenshots[1]);" in visual
    assert "failures.push(`post-interaction screenshot failed: ${String(error).slice(0, 500)}`);" in visual
    assert visual.index("const screenshotResult = await captureInteractionScreenshotWithRetry(") > visual.index(
        "const failures = [];"
    )


def test_visual_qa_waits_for_zero_data_intelligence_setup_actions() -> None:
    visual = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()

    assert "const intelligenceReady = await page.waitForFunction" in visual
    assert "const assetCount = Number(" in visual
    assert "#assistant-workbench-setup-actions" in visual
    assert "return assetCount > 0 || setupVisible;" in visual
    assert "intelligence workspace did not show live data or real setup actions" in visual
    assert "page.on('pageerror'" in visual
    assert "Page error:" in visual
    assert "sensor-temp-01" not in visual
    assert "/No records yet/i.test(rows[0].innerText || '')" in visual
    assert "/No operational changes recorded/i.test(text)" in visual


def test_runtime_secret_files_are_excluded_from_git_and_docker_context() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text()

    for ignore_file in (gitignore, dockerignore):
        assert ".env\n" in ignore_file
        assert ".env.*" in ignore_file
        assert "secrets/" in ignore_file
        assert "*.pem" in ignore_file
        assert "*.key" in ignore_file
        assert "*.crt" in ignore_file
        assert "caddy-data/" in ignore_file


def test_runtime_dependencies_include_mqtt_client() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
    requirements = (PROJECT_ROOT / "requirements.txt").read_text()
    lockfile = (PROJECT_ROOT / "requirements.lock").read_text()

    for manifest in (pyproject, requirements, lockfile):
        assert "cryptography==50.0.0" in manifest

    assert "gmqtt==0.7.0" in requirements
    assert "gmqtt==0.7.0" in lockfile
    assert "--hash=sha256:" in lockfile


def test_release_dependency_gate_normalizes_requirement_extras() -> None:
    release_builder = (PROJECT_ROOT / "tools" / "build_customer_release.sh").read_text()

    assert 'package = package.split("[", maxsplit=1)[0]' in release_builder


def test_release_security_tests_isolate_runtime_evidence_urls() -> None:
    release_builder = (PROJECT_ROOT / "tools" / "build_customer_release.sh").read_text()

    assert release_builder.count("-u AGENTIOT_DRIFT_CONTROL_URL") == 2
    assert release_builder.count("-u AGENTIOT_RUNTIME_VERSION_URL") == 2


def test_release_builder_accepts_only_current_short_or_full_commit() -> None:
    release_builder = (PROJECT_ROOT / "tools" / "build_customer_release.sh").read_text()

    assert 'commit_full="$(git -C "${repo_root}" rev-parse HEAD' in release_builder
    assert '"${drift_source_commit}" != "${commit_full}"' in release_builder


def test_readme_indexes_protocol_evidence_endpoints() -> None:
    readme_en = (PROJECT_ROOT / "README.en.md").read_text()
    readme_de = (PROJECT_ROOT / "README.de.md").read_text()

    for readme in (readme_en, readme_de):
        assert "/api/orchestration/protocol-contracts" in readme
        assert "/api/a2a/jsonrpc" in readme
        assert "/api/a2a/messages/stream" in readme
        assert "/api/mcp/tools" in readme
        assert "/api/mcp/jsonrpc" in readme
        assert "/api/architecture/adr" in readme


def test_remote_access_docs_cover_tailscale_cert_without_private_hosts() -> None:
    readme_en = (PROJECT_ROOT / "README.en.md").read_text()
    readme_de = (PROJECT_ROOT / "README.de.md").read_text()
    guide_en = (
        PROJECT_ROOT / "docs" / "customer" / "phase2" / "SECURE_REMOTE_ACCESS_GUIDE.en.md"
    ).read_text()
    guide_de = (
        PROJECT_ROOT / "docs" / "customer" / "phase2" / "SECURE_REMOTE_ACCESS_GUIDE.de.md"
    ).read_text()
    owner_en = (
        PROJECT_ROOT
        / "docs"
        / "customer"
        / "phase3"
        / "PRODUCTION_OWNER_DECISION_REGISTER.en.md"
    ).read_text()
    owner_de = (
        PROJECT_ROOT
        / "docs"
        / "customer"
        / "phase3"
        / "PRODUCTION_OWNER_DECISION_REGISTER.de.md"
    ).read_text()

    for document in (readme_en, readme_de, guide_en, guide_de, owner_en, owner_de):
        assert "AGENTIOT_USE_TAILSCALE_CERT=1" in document or "Tailscale" in document
        assert "*.ts.net" in document or "node.tailnet.ts.net" in document
        assert "100.109." not in document
        assert "tail1ed27e" not in document
        assert "iot-dashboard-serv" not in document


def test_visual_release_evidence_is_bound_to_runtime_source_digest() -> None:
    runner = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()
    builder = (PROJECT_ROOT / "tools" / "build_customer_release.sh").read_text()
    digest_tool = PROJECT_ROOT / "tools" / "compute_customer_runtime_digest.py"

    assert digest_tool.is_file()
    assert "source_digest: sourceDigest" in runner
    assert "runtimeIdentityCheck" in runner
    assert "/api/version" in runner
    assert "runtime manifest digest mismatch" in runner
    assert "AGENTIOT_VISUAL_SOURCE_COMMIT" not in runner
    assert "visual report source digest does not match" in builder
    assert "compute_customer_runtime_digest.py" in builder
    assert 'required_viewports = ("mobile", "tablet", "desktop", "desktop-wide")' in builder
    assert 'expected_sha256 = "sha256:" + hashlib.sha256(content).hexdigest()' in builder
    assert "visual screenshot digest mismatch" in builder
    assert "visual screenshot byte count mismatch" in builder


def test_runtime_manifest_digest_covers_all_image_copy_inputs_without_evidence_loop() -> None:
    digest_tool = (
        PROJECT_ROOT / "tools" / "compute_customer_runtime_digest.py"
    ).read_text()
    dockerfile = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()

    for required in (
        'Path("README.en.md")',
        'Path("README.de.md")',
        'Path("CHANGELOG.md")',
        'Path("NOTICE.md")',
        'Path("docs/customer")',
        'Path("docs/contract")',
        'Path("docs/adr")',
        'Path("docker")',
    ):
        assert required in digest_tool
    assert 'Path("output/playwright")' not in digest_tool
    assert "COPY --chown=agentiot:agentiot output/playwright/" not in dockerfile
    assert "ARG AGENTIOT_RUNTIME_DIGEST=unknown" in dockerfile
    assert "ENV AGENTIOT_RUNTIME_DIGEST=${AGENTIOT_RUNTIME_DIGEST}" in dockerfile


def test_runtime_manifest_digest_changes_for_runtime_inputs_not_visual_evidence(
    tmp_path,
) -> None:
    root_files = (
        "VERSION",
        "pyproject.toml",
        "requirements.txt",
        "requirements.lock",
        "README.en.md",
        "README.de.md",
        "CHANGELOG.md",
        "NOTICE.md",
    )
    for relative_path in root_files:
        (tmp_path / relative_path).write_text(relative_path + "\n", encoding="utf-8")
    for relative_path in (
        "docker",
        "src",
        "docs/customer",
        "docs/contract",
        "docs/adr",
    ):
        directory = tmp_path / relative_path
        directory.mkdir(parents=True)
        (directory / "fixture.txt").write_text(relative_path + "\n", encoding="utf-8")
    digest_tool = PROJECT_ROOT / "tools" / "compute_customer_runtime_digest.py"

    first = subprocess.check_output(
        ["python3", digest_tool, tmp_path],
        text=True,
    ).strip()
    (tmp_path / "README.en.md").write_text("changed runtime input\n", encoding="utf-8")
    second = subprocess.check_output(
        ["python3", digest_tool, tmp_path],
        text=True,
    ).strip()
    evidence_dir = tmp_path / "output" / "playwright"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "report.json").write_text("{}\n", encoding="utf-8")
    third = subprocess.check_output(
        ["python3", digest_tool, tmp_path],
        text=True,
    ).strip()

    assert first != second
    assert second == third


def test_https_launcher_stages_each_deployment_in_isolated_secret_paths() -> None:
    launcher = (PROJECT_ROOT / "docker/launch_https_proxy_8040.sh").read_text()

    assert 'candidate_runtime_dir="${runtime_dir}/deployments/${deployment_id}"' in launcher
    assert 'secret_dir="${candidate_runtime_dir}/secrets"' in launcher
    assert 'tls_dir="${candidate_runtime_dir}/tls"' in launcher
    assert "resolve_runtime_mount_source()" in launcher
    assert 'remove_candidate_runtime' in launcher
    assert 'operator_token_source="$(resolve_runtime_mount_source' in launcher
    assert 'edge_ingest_credentials_source="$(resolve_runtime_mount_source' in launcher
    assert (
        "AGENTIOT_EDGE_INGEST_CREDENTIALS_FILE="
        "/run/secrets/edge_ingest_credentials.json"
    ) in launcher
    assert (
        '${edge_ingest_credentials_file}:'
        '/run/secrets/edge_ingest_credentials.json:ro'
    ) in launcher
    assert "Deprecated shared edge-ingestion settings are not accepted" in launcher
    assert "if len(tokens) != len(set(tokens))" in launcher
    assert 'for name in ("operator_token", "admin_token")' in launcher
    assert 'mqtt_password_source="$(resolve_runtime_mount_source' in launcher
    assert 'tls_cert_source_file="$(resolve_runtime_mount_source' in launcher
