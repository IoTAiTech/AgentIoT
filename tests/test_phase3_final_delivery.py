# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

import json
import hashlib
import os
from datetime import UTC, datetime, timedelta
import shutil
import subprocess
import sys
import tarfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import create_app


def _marker(codes: list[int]) -> str:
    return "".join(chr(code) for code in codes)


def _posix_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _find_bash() -> str | None:
    for candidate in (shutil.which("bash"),):
        if candidate and Path(candidate).exists():
            return _posix_path(Path(candidate))
    return None


def _write_minimal_release_repo(repo_root: Path) -> None:
    source_root = Path(__file__).resolve().parents[1]
    root_files = {
        ".dockerignore": "*.pyc\n",
        ".gitignore": "dist/\n",
        "CHANGELOG.md": "# Changelog\n",
        "LICENSE": "MIT License\n",
        "NOTICE.md": "AgentIoT fixture notice\n",
        "README.de.md": "# AgentIoT\n",
        "README.en.md": "# AgentIoT\n",
        "VERSION": "0.152.8\n",
        "pyproject.toml": "[project]\nname = \"agentiot-greenovax\"\n",
        "requirements.txt": "fastapi\n",
        "requirements.lock": (
            "# fixture lock\n"
            "fastapi==0.138.1 \\\n"
            "    --hash=sha256:"
            "0000000000000000000000000000000000000000000000000000000000000000\n"
        ),
    }
    for relative_path, content in root_files.items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    for directory in (
        "docker",
        "src/agentiot",
        "tests",
        "docs/adr",
        "docs/agent-cards",
        "docs/contract",
        "docs/customer",
        "output/playwright",
    ):
        (repo_root / directory).mkdir(parents=True, exist_ok=True)

    (repo_root / "docker/Dockerfile").write_text(
        "FROM scratch\n"
        "COPY requirements.txt requirements.lock ./\n"
        "RUN pip install --no-cache-dir --require-hashes -r requirements.lock\n",
        encoding="utf-8",
    )
    (repo_root / "src/agentiot/__init__.py").write_text(
        "__version__ = '0.152.8'\n", encoding="utf-8"
    )
    (repo_root / "src/agentiot/root_page.html").write_text(
        "<!doctype html><html lang=\"en\"><body><main>AgentIoT fixture</main></body></html>\n",
        encoding="utf-8",
    )
    (repo_root / "tests/README.md").write_text("release fixture\n", encoding="utf-8")
    (repo_root / "docs/contract/CONTRACT_TRACEABILITY.en.md").write_text(
        "# Contract Traceability\n", encoding="utf-8"
    )
    (repo_root / "docs/adr/ADR-0001-agent-orchestrated-dashboard.en.md").write_text(
        "# ADR-0001: Agent-Orchestrated Dashboard\n", encoding="utf-8"
    )
    (repo_root / "docs/agent-cards/AGENT_CARDS.en.yaml").write_text(
        "schema_version: agent.card.registry.v1\ncards: []\n", encoding="utf-8"
    )
    (repo_root / "docs/customer/ACCEPTANCE_CHECKLIST.en.md").write_text(
        "# Acceptance Checklist\n", encoding="utf-8"
    )
    (repo_root / "docs/customer/phase1/COMMERCIAL_BASELINE_EVIDENCE.en.md").parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    (repo_root / "docs/customer/phase1/COMMERCIAL_BASELINE_EVIDENCE.en.md").write_text(
        "# Commercial Baseline Evidence\n"
        "| Item | Value |\n"
        "|---|---|\n"
        "| Baseline version | v1.7.0 |\n"
        "| Editable source SHA-256 | `E058EF21B15DD89D76EFC254C3CA8E3106C8B8BC7CADFB69D41F32DC6FC4A806` |\n"
        "| Repository storage | Not stored in Git |\n",
        encoding="utf-8",
    )
    visual_version = "0.152.8"
    visual_routes = [
        "/",
        "/operations",
        "/charts",
        "/analytics",
        "/status",
        "/reports",
        "/tests",
        "/evidence",
        "/settings",
        "/assistant",
    ]
    visual_viewports = ["mobile", "tablet", "desktop", "desktop-wide"]
    visual_checks = []
    visual_artifacts = []
    for route in visual_routes:
        route_slug = "root" if route == "/" else route.strip("/").replace("/", "-")
        for viewport in visual_viewports:
            screenshot = (
                f"output/playwright/agentiot-v{visual_version}-"
                f"{route_slug}-{viewport}.png"
            )
            screenshot_content = b"fixture visual evidence"
            (repo_root / screenshot).write_bytes(screenshot_content)
            visual_artifacts.append(
                {
                    "path": screenshot,
                    "sha256": "sha256:" + hashlib.sha256(screenshot_content).hexdigest(),
                    "bytes": len(screenshot_content),
                }
            )
            visual_checks.append(
                {
                    "route": route,
                    "viewport": viewport,
                    "screenshot": screenshot,
                    "passed": True,
                    "failures": [],
                }
            )
    (repo_root / f"output/playwright/agentiot-v{visual_version}-visual-report.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "version": visual_version,
                "routes": visual_routes,
                "viewports": visual_viewports,
                "passed_count": len(visual_checks),
                "total_count": len(visual_checks),
                "checks": visual_checks,
                "screenshot_artifacts": visual_artifacts,
                "generated_at": datetime.now(UTC).isoformat(),
                "screenshot_path": (
                    f"output/playwright/agentiot-v{visual_version}-root-desktop.png"
                ),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    source_builder = source_root / "tools" / "build_customer_release.sh"
    digest_tool = source_root / "tools" / "compute_customer_runtime_digest.py"
    if not source_builder.exists():
        pytest.skip("release-builder tests run only in the development repository")
    tools_dir = repo_root / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_builder, tools_dir / "build_customer_release.sh")
    shutil.copy2(digest_tool, tools_dir / "compute_customer_runtime_digest.py")


def _refresh_visual_runtime_digest(repo_root: Path) -> Path:
    version = (repo_root / "VERSION").read_text(encoding="utf-8").strip()
    visual_report = (
        repo_root / f"output/playwright/agentiot-v{version}-visual-report.json"
    )
    digest_tool = repo_root / "tools/compute_customer_runtime_digest.py"
    payload = json.loads(visual_report.read_text(encoding="utf-8"))
    payload["source_digest"] = subprocess.check_output(
        [sys.executable, digest_tool, repo_root],
        text=True,
    ).strip()
    visual_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    return visual_report


def _init_clean_git_repo(
    repo_root: Path,
    *,
    refresh_visual_digest: bool = True,
) -> None:
    if refresh_visual_digest:
        _refresh_visual_runtime_digest(repo_root)
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "release-test@example.test"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Release Test"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test fixture"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


def _repo_short_commit(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()


def _start_drift_control_server(payload: dict[str, object]) -> ThreadingHTTPServer:
    class DriftControlHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/api/version":
                payload = self.server.version_payload  # type: ignore[attr-defined]
                data = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            if self.path != "/api/project/drift-control":
                self.send_response(404)
                self.end_headers()
                return

            payload = self.server.payload  # type: ignore[attr-defined]
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), DriftControlHandler)
    server.payload = payload  # type: ignore[attr-defined]
    server.version_payload = {  # type: ignore[attr-defined]
        "version": payload.get("version"),
        "clean_room": True,
        "prepared_for": "GreeNovaX",
        "prepared_by": "IoT-AI.Tech",
    }
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _start_release_proxy_server(
    drift_payload: dict[str, object],
    version_payload: dict[str, object],
) -> ThreadingHTTPServer:
    class ReleaseProxyHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.endswith("/api/project/drift-control"):
                payload = self.server.drift_payload  # type: ignore[attr-defined]
            elif self.path.endswith("/api/version"):
                payload = self.server.version_payload  # type: ignore[attr-defined]
            else:
                self.send_response(404)
                self.end_headers()
                return

            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ReleaseProxyHandler)
    server.drift_payload = drift_payload  # type: ignore[attr-defined]
    server.version_payload = version_payload  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_customer_release_rejects_proxied_public_evidence_urls(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    _init_clean_git_repo(repo_root)
    drift_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    proxy = _start_release_proxy_server(
        drift_payload,
        {
            "version": "0.152.8",
            "clean_room": True,
            "prepared_for": "GreeNovaX",
            "prepared_by": "IoT-AI.Tech",
        },
    )
    proxy_url = f"http://127.0.0.1:{proxy.server_port}"
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            "http://drift.example.test/api/project/drift-control"
        ),
        "AGENTIOT_RUNTIME_VERSION_URL": "http://runtime.example.test/api/version",
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "HTTP_PROXY": proxy_url,
        "HTTPS_PROXY": proxy_url,
        "ALL_PROXY": proxy_url,
        "NO_PROXY": "",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "proxied"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        assert "Release evidence URL rejected" in result.stderr
        report = (release_dir / "proxied/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Drift review result: PASS" not in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        proxy.shutdown()
        proxy.server_close()


def test_customer_release_records_drift_evidence_and_blocks_unresolved_state(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [
            {"reference": "docs/contract/CONTRACT_TRACEABILITY.en.md"},
            {"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"},
        ],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [
            {"agent_id": "project_delivery_coordinator"},
            {"agent_id": "release_compliance_controller"},
        ],
        "release_block_state": "clear",
    }
    blocked_payload = {
        **clear_payload,
        "review_result": "FAIL",
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.25},
        "deviations": [{"id": "sla-gap"}],
        "release_block_state": "blocked_until_drift_review_passes",
    }
    server = _start_drift_control_server(clear_payload)
    drift_url = f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": drift_url,
        "AGENTIOT_RUNTIME_VERSION_URL": (
            f"http://127.0.0.1:{server.server_port}/api/version"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        pass_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "pass"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert pass_result.returncode == 0, pass_result.stderr
        pass_report = (release_dir / "pass/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Drift review result: PASS" in pass_report
        assert "Drift cadence hours: 6" in pass_report
        assert f"Drift source commit: {_repo_short_commit(repo_root)}" in pass_report
        assert "Drift checked source count: 2" in pass_report
        assert "Drift SLA target: 99.99" in pass_report
        assert "Drift SLA gap: 0.0" in pass_report
        assert "Drift deviation count: 0" in pass_report
        assert (
            "Drift owner agents: project_delivery_coordinator, release_compliance_controller"
            in pass_report
        )
        assert "Drift release block state: clear" in pass_report
        drift_block_index = pass_report.index("Drift release block state: clear")
        manifest_pass_index = pass_report.index("Customer release manifest check: PASS")
        assert drift_block_index < manifest_pass_index
        assert (
            release_dir / "pass/docs/adr/ADR-0001-agent-orchestrated-dashboard.en.md"
        ).exists()
        assert (release_dir / "pass/docs/agent-cards/AGENT_CARDS.en.yaml").exists()
        assert (
            release_dir / "pass/output/playwright/agentiot-v0.152.8-visual-report.json"
        ).exists()
        assert (
            release_dir / "pass/output/playwright/agentiot-v0.152.8-reports-mobile.png"
        ).exists()
        assert "Visual multi-route evidence gate: PASS" in pass_report
        assert "Bundle visual artifact scope gate: PASS" in pass_report
        assert (
            "Security gate provenance: Full pytest suite | "
            "mode=pytest_fixture | command_id=pytest-full-suite | "
            f"source_commit={_repo_short_commit(repo_root)}"
        ) in pass_report
        assert "command_id=bandit-medium-high" in pass_report
        assert "command_id=pip-audit-lockfile" in pass_report
        assert str(repo_root) not in pass_report
        assert "Production-mode runtime hardening smoke: PASS" in pass_report
        assert "Deliverable secret-pattern gate: PASS" in pass_report
        assert "Frontend DOM security sink gate: PASS" in pass_report
        assert "Source archive gate: PASS" in pass_report
        assert "Release parent handoff gate: PASS" in pass_report
        assert "Commercial terms gate: PASS" in pass_report
        customer_changelog = (release_dir / "pass/CHANGELOG.md").read_text(
            encoding="utf-8"
        )
        assert "Content-Security-Policy" in customer_changelog
        assert "internal-agent" not in customer_changelog
        assert "development source state" not in customer_changelog
        assert "Claude" not in customer_changelog
        assert (release_dir / "pass/tests/test_customer_smoke.py").exists()
        assert (
            release_dir / "pass/tests/bdd/agentiot_api_baseline.feature"
        ).exists()
        contract_trace = (
            release_dir / "pass/docs/contract/CONTRACT_TRACEABILITY.en.md"
        ).read_text(encoding="utf-8")
        assert "EUR" not in contract_trace
        assert ("fix" + "ed " + "pr" + "ice") not in contract_trace.lower()
        assert "delivery period" not in contract_trace.lower()
        baseline_evidence = (
            release_dir
            / "pass/docs/customer/phase1/COMMERCIAL_BASELINE_EVIDENCE.en.md"
        ).read_text(encoding="utf-8")
        assert "v1.7.0" in baseline_evidence
        assert "SHA-256" in baseline_evidence
        assert "Not stored in Git" in baseline_evidence
        assert "EUR" not in baseline_evidence
        assert ("contract" + " PDF") not in baseline_evidence
        assert "L:" not in baseline_evidence
        assert "C:" not in baseline_evidence
        source_archive = release_dir / "pass-source.tar.gz"
        source_checksum = release_dir / "pass-source.tar.gz.sha256"
        assert source_archive.exists()
        assert source_checksum.exists()
        expected_hash = source_checksum.read_text(encoding="utf-8").split()[0]
        actual_hash = hashlib.sha256(source_archive.read_bytes()).hexdigest()
        assert actual_hash == expected_hash
        with tarfile.open(source_archive, "r:gz") as archive:
            archived_names = set(archive.getnames())
        assert "pass/src/agentiot/__init__.py" in archived_names
        assert "pass/RELEASE_CHECK_REPORT.txt" in archived_names
        assert "pass/tests/test_customer_smoke.py" in archived_names
        assert "pass/tests/bdd/agentiot_api_baseline.feature" in archived_names
        assert "pass/tests/conftest.py" not in archived_names
        disallowed_root_names = (
            "A" + "GENTS.md",
            "C" + "LAUDE.md",
            "G" + "EMINI.md",
            "inter" + "nal",
            "sec" + "rets",
            "." + "env",
        )
        disallowed_archive_names = {
            f"pass/{root_name}" for root_name in disallowed_root_names
        }
        assert archived_names.isdisjoint(disallowed_archive_names)
        assert not any(name.endswith(".pdf") or name.endswith(".pyc") for name in archived_names)

        server.payload = blocked_payload  # type: ignore[attr-defined]
        block_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert block_result.returncode != 0
        blocked_report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Drift review result: FAIL" in blocked_report
        assert "Drift release block state: blocked_until_drift_review_passes" in (
            blocked_report
        )
        assert "Drift owner/customer decision artifact: absent" in blocked_report
        assert "Customer release manifest check: PASS" not in blocked_report

        server.payload = {
            **clear_payload,
            "version": "0.134.24",
            "source_version": "0.134.24",
        }  # type: ignore[attr-defined]
        stale_runtime_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "stale-runtime"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert stale_runtime_result.returncode != 0
        stale_runtime_report = (
            release_dir / "stale-runtime/RELEASE_CHECK_REPORT.txt"
        ).read_text(encoding="utf-8")
        assert "FAIL: drift runtime version mismatch" in stale_runtime_report
        assert "Customer release manifest check: PASS" not in stale_runtime_report
        shutil.rmtree(release_dir / "stale-runtime")

        server.payload = {  # type: ignore[attr-defined]
            **clear_payload,
            "source_commit": _repo_short_commit(repo_root),
        }
        server.version_payload = {  # type: ignore[attr-defined]
            "version": "0.134.24",
            "clean_room": True,
            "prepared_for": "GreeNovaX",
            "prepared_by": "IoT-AI.Tech",
        }
        stale_api_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "api-version-parent/blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert stale_api_result.returncode != 0
        stale_api_report = (
            release_dir / "api-version-parent/blocked/RELEASE_CHECK_REPORT.txt"
        ).read_text(encoding="utf-8")
        assert "FAIL: runtime /api/version mismatch" in stale_api_report
        assert "Customer release manifest check: PASS" not in stale_api_report

        server.payload = clear_payload  # type: ignore[attr-defined]
        server.version_payload = {  # type: ignore[attr-defined]
            "version": "0.152.8",
            "clean_room": True,
            "prepared_for": "GreeNovaX",
            "prepared_by": "IoT-AI.Tech",
        }
        stale_version = "0." + "104.1"
        (repo_root / "pyproject.toml").write_text(
            f'[project]\nname = "agentiot-greenovax"\nversion = "{stale_version}"\n',
            encoding="utf-8",
        )
        visual_report = _refresh_visual_runtime_digest(repo_root)
        subprocess.run(
            ["git", "add", "pyproject.toml", visual_report],
            cwd=repo_root,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "add stale package version fixture"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
        server.payload = {  # type: ignore[attr-defined]
            **clear_payload,
            "source_commit": _repo_short_commit(repo_root),
        }
        stale_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "stale-package-version"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert stale_result.returncode != 0
        stale_report = (
            release_dir / "stale-package-version/RELEASE_CHECK_REPORT.txt"
        ).read_text(encoding="utf-8")
        assert stale_version in stale_report
        assert "FAIL: stale customer-release version text found" in stale_report
        assert "Customer release manifest check: PASS" not in stale_report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_requires_current_approved_drift_decision(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    decision_path = (
        repo_root / "docs/customer/phase3/DRIFT_CONTROL_OWNER_DECISION.md"
    )
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(
        "# Drift Control Owner Decision\n"
        "Decision status: PENDING\n"
        "Decision version: 0.152.8\n"
        "Decision ID: DCO-2026-08-09-0.152.8\n"
        "Approved by: pending\n"
        "Approval date: 2026-08-09\n"
        "| Runtime version | 0.152.8 |\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    blocked_payload: dict[str, object] = {
        "review_result": "FAIL",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [
            {"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}
        ],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.25},
        "deviations": [{"id": "sla-gap"}],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "blocked_until_drift_review_passes",
    }
    server = _start_drift_control_server(blocked_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RUNTIME_VERSION_URL": (
            f"http://127.0.0.1:{server.server_port}/api/version"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        invalid_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "invalid"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert invalid_result.returncode != 0
        invalid_report = (
            release_dir / "invalid/RELEASE_CHECK_REPORT.txt"
        ).read_text(encoding="utf-8")
        assert "Drift owner/customer decision artifact: invalid" in invalid_report
        assert "FAIL: unresolved drift-control block" in invalid_report
        assert "Customer release manifest check: PASS" not in invalid_report
        shutil.rmtree(release_dir / "invalid")

        decision_path.write_text(
            "# Drift Control Owner Decision\n"
            "Decision status: APPROVED\n"
            "Decision version: 0.152.8\n"
            "Decision ID: DCO-2026-08-09-0.152.8\n"
            "Approved by: Release Owner\n"
            "Approval date: 2026-08-09\n"
            "| Runtime version | 0.152.8 |\n",
            encoding="utf-8",
        )
        visual_report = _refresh_visual_runtime_digest(repo_root)
        subprocess.run(
            ["git", "add", decision_path, visual_report],
            cwd=repo_root,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "approve release evidence decision"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
        server.payload = {  # type: ignore[attr-defined]
            **blocked_payload,
            "source_commit": _repo_short_commit(repo_root),
        }

        valid_result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "valid"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert valid_result.returncode == 0, valid_result.stderr
        valid_report = (
            release_dir / "valid/RELEASE_CHECK_REPORT.txt"
        ).read_text(encoding="utf-8")
        assert "Drift owner/customer decision artifact: valid" in valid_report
        assert "Customer evidence coherence gate: PASS" in valid_report
        assert "Customer release manifest check: PASS" in valid_report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_commercial_terms_in_customer_docs(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    commercial_fixture = (
        "# Traceability\nTotal "
        + "fix"
        + "ed "
        + "pr"
        + "ice: "
        + "EUR "
        + "49000\n"
    )
    (repo_root / "docs/contract/CONTRACT_TRACEABILITY.en.md").write_text(
        commercial_fixture,
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Commercial terms gate: FAIL" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_internal_archive_in_handoff_parent(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_parent = tmp_path / "handoff"
    release_dir = release_parent / "agentiot-dashboard-v0.152.8"
    dev_payload_dir = tmp_path / "dev-payload"
    repo_root.mkdir()
    release_parent.mkdir()
    dev_payload_dir.mkdir()
    _write_minimal_release_repo(repo_root)
    _init_clean_git_repo(repo_root)
    blocked_name = "A" + "GENTS.md"
    (dev_payload_dir / blocked_name).write_text(
        "# Agent instructions\n", encoding="utf-8"
    )
    internal_archive_name = (
        "agentiot-greenovax-" + "dev-v0.152.8-fixture.tar.gz"
    )
    with tarfile.open(release_parent / internal_archive_name, "w:gz") as archive:
        archive.add(dev_payload_dir / blocked_name, arcname=f"dev/{blocked_name}")

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Release parent handoff gate: FAIL" in report
        assert internal_archive_name in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_non_current_sibling_release_directory(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_parent = tmp_path / "handoff"
    release_dir = release_parent / "agentiot-dashboard-v0.152.8"
    repo_root.mkdir()
    release_parent.mkdir()
    _write_minimal_release_repo(repo_root)
    _init_clean_git_repo(repo_root)
    stale_sibling = release_parent / "agentiot-dashboard-v0.134.50"
    stale_sibling.mkdir()
    (stale_sibling / "VERSION").write_text("0.134.50\n", encoding="utf-8")

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Release parent handoff gate: FAIL" in report
        assert "unexpected sibling directory in customer handoff parent" in report
        assert "agentiot-dashboard-v0.134.50" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_stale_runtime_version_text(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    stale_version = "0." + "112.1"
    phase3 = repo_root / "docs/customer/phase3"
    phase3.mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/customer/ACCEPTANCE_CHECKLIST.en.md").write_text(
        f"# Acceptance Checklist\nRuntime image agentiot-greenovax:{stale_version}\n",
        encoding="utf-8",
    )
    decision_version = "0." + "110.0"
    scanner_version = "0." + "114.0"
    (phase3 / "DRIFT_CONTROL_OWNER_DECISION.md").write_text(
        "# Drift Control Owner Decision\n"
        f"Decision ID: DCO-2026-06-20-{decision_version}\n"
        f"| Runtime version | {decision_version} |\n"
        f"| Source reference | v{decision_version} source package |\n",
        encoding="utf-8",
    )
    (phase3 / "STALE_RUNTIME_FIXTURE.en.md").write_text(
        "# Stale Runtime Fixture\n"
        f"| Runtime version | {scanner_version} |\n"
        f"Runtime image agentiot-greenovax:{scanner_version}\n",
        encoding="utf-8",
    )
    (repo_root / "docs/customer/phase2").mkdir(parents=True, exist_ok=True)
    stale_demo_version = "0." + "131.0"
    (repo_root / "docs/customer/phase2/CUSTOMER_WEBSITE_DEMO_PACKAGE.en.md").write_text(
        "# Customer Website Demo Package\n"
        f"| Runtime | Docker image `agentiot-greenovax:{stale_demo_version}` |\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": f"http://127.0.0.1:{server.server_port}/api/project/drift-control",
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "RELEASE_CHECK_REPORT.txt").read_text(encoding="utf-8")
        assert "FAIL: stale customer-release version text found" in report
        assert stale_version in report
        assert scanner_version in report
        assert stale_demo_version in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_local_path_text_in_copied_sources(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    (repo_root / "src/agentiot/path_marker_fixture.py").write_text(
        "MARKER = " + repr("C" + ":/customer-unsafe") + "\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        assert "prohibited customer-release text found" in (
            result.stdout + result.stderr
        )
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_stale_visual_evidence(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    visual_report = repo_root / "output/playwright/agentiot-v0.152.8-visual-report.json"
    payload = json.loads(visual_report.read_text(encoding="utf-8"))
    payload["generated_at"] = (datetime.now(UTC) - timedelta(hours=7)).isoformat()
    visual_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [bash, "tools/build_customer_release.sh", _posix_path(release_dir / "blocked")],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Visual multi-route evidence gate: FAIL" in report
        assert "older than 6 hours" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_missing_visual_evidence_timestamp(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    visual_report = repo_root / "output/playwright/agentiot-v0.152.8-visual-report.json"
    payload = json.loads(visual_report.read_text(encoding="utf-8"))
    payload.pop("generated_at", None)
    visual_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [bash, "tools/build_customer_release.sh", _posix_path(release_dir / "blocked")],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Visual multi-route evidence gate: FAIL" in report
        assert "generated_at is missing" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_visual_evidence_for_different_runtime_source(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    visual_report = repo_root / "output/playwright/agentiot-v0.152.8-visual-report.json"
    payload = json.loads(visual_report.read_text(encoding="utf-8"))
    payload["source_digest"] = "sha256:" + ("0" * 64)
    visual_report.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    _init_clean_git_repo(repo_root, refresh_visual_digest=False)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [bash, "tools/build_customer_release.sh", _posix_path(release_dir / "blocked")],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Visual multi-route evidence gate: FAIL" in report
        assert "source digest does not match" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_contract_source_markers_in_customer_docs(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    pdf_marker = "contract" + " PDF"
    contract_marker = "contract" + "-source"
    project_marker = "other" + "-project"
    private_note = repo_root / "docs/customer/phase1/PRIVATE_SOURCE_NOTE.en.md"
    private_note.parent.mkdir(parents=True, exist_ok=True)
    private_note.write_text(
        "# Private Source Note\n"
        f"This {pdf_marker} content must not ship.\n"
        f"This {contract_marker} marker must not ship.\n"
        f"This {project_marker} marker must not ship.\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Customer bundle source-content gate: FAIL" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_source_markers_in_shipped_architecture_docs(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    pdf_marker = "contract" + " PDF"
    private_note = repo_root / "docs/adr/ADR-9999-private-source-note.en.md"
    private_note.write_text(
        "# Private Architecture Source Note\n"
        f"This {pdf_marker} content must not ship through architecture docs.\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Customer bundle source-content gate: FAIL" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_backup_patch_artifacts(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    secret_key = "client_" + "secret"
    (repo_root / "src/agentiot/app.py.orig").write_text(
        f'{secret_key}: "fixture-value"\n',
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        assert "disallowed backup/patch artifact present" in (
            result.stdout + result.stderr
        )
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_secret_like_literals_in_deliverable_code(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    secret_key = "client_" + "secret"
    secret_value = "fixture-" + "secret-" + "value"
    (repo_root / "docker/release_secret_fixture.yml").write_text(
        f'{secret_key}: "{secret_value}"\n',
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Deliverable secret-pattern gate: FAIL" in report
        assert "secret-like literal" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_secret_like_literals_in_customer_docs(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    secret_key = "client_" + "secret"
    secret_value = "fixture-" + "secret-" + "value"
    (repo_root / "docs/customer/ACCEPTANCE_CHECKLIST.en.md").write_text(
        f"# Acceptance Checklist\n\n{secret_key}: \"{secret_value}\"\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Deliverable secret-pattern gate: FAIL" in report
        assert "secret-like literal" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_excludes_pytest_fixtures_and_unit_tests(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    (repo_root / "tests/conftest.py").write_text(
        'TEST_ADMIN_TOKEN = "test-admin-token"\n'
        'PROVIDER = "dummy-provider-token-secret"\n',
        encoding="utf-8",
    )
    (repo_root / "tests/test_customer_internal_fixture.py").write_text(
        'AGENTIOT_INTERNAL_TOKEN = "unit-internal-token"\n',
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "pass"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert not (release_dir / "pass/tests/conftest.py").exists()
        assert not (release_dir / "pass/tests/test_customer_internal_fixture.py").exists()
        shipped_tests = {
            path.relative_to(release_dir / "pass").as_posix()
            for path in (release_dir / "pass").rglob("test_*.py")
        }
        assert shipped_tests == {"tests/test_customer_smoke.py"}
        report = (release_dir / "pass/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Deliverable secret-pattern gate: PASS" in report
        with tarfile.open(release_dir / "pass-source.tar.gz", "r:gz") as archive:
            archived_names = set(archive.getnames())
        assert "pass/tests/conftest.py" not in archived_names
        assert "pass/tests/test_customer_internal_fixture.py" not in archived_names
        assert "pass/tests/test_customer_smoke.py" in archived_names
        assert "pass/tests/bdd/agentiot_api_baseline.feature" in archived_names
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_quoted_agentiot_secret_assignments(
    tmp_path,
) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    (repo_root / "src/agentiot/customer_secret_fixture.py").write_text(
        'AGENTIOT_CUSTOMER_TOKEN = "release-token-fixture"\n',
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Deliverable secret-pattern gate: FAIL" in report
        assert "secret-like literal" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_env_files_in_copied_sources(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    (repo_root / "docker/.env").write_text(
        "AGENTIOT_ENV=production\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "disallowed environment or secret runtime file" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_customer_release_rejects_frontend_dom_security_sinks(tmp_path) -> None:
    bash = _find_bash()
    if bash is None:
        pytest.skip("bash is required for the customer release builder")

    repo_root = tmp_path / "repo"
    release_dir = tmp_path / "release"
    repo_root.mkdir()
    _write_minimal_release_repo(repo_root)
    (repo_root / "src/agentiot/root_page.html").write_text(
        "<!doctype html><script>target.innerHTML = payload;</script>\n",
        encoding="utf-8",
    )
    _init_clean_git_repo(repo_root)

    clear_payload: dict[str, object] = {
        "review_result": "PASS",
        "cadence_hours": 6,
        "version": "0.152.8",
        "source_version": "0.152.8",
        "source_commit": _repo_short_commit(repo_root),
        "checked_sources": [{"reference": "docs/customer/ACCEPTANCE_CHECKLIST.en.md"}],
        "kpi_sla": {"sla_target": 99.99, "sla_gap": 0.0},
        "deviations": [],
        "required_agents": [{"agent_id": "release_compliance_controller"}],
        "release_block_state": "clear",
    }
    server = _start_drift_control_server(clear_payload)
    env = {
        **os.environ,
        "AGENTIOT_DRIFT_CONTROL_URL": (
            f"http://127.0.0.1:{server.server_port}/api/project/drift-control"
        ),
        "AGENTIOT_RELEASE_SECURITY_GATES": "prevalidated-test-fixture",
        "PYTHON": _posix_path(Path(sys.executable)),
    }

    try:
        result = subprocess.run(
            [
                bash,
                "tools/build_customer_release.sh",
                _posix_path(release_dir / "blocked"),
            ],
            cwd=repo_root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode != 0
        report = (release_dir / "blocked/RELEASE_CHECK_REPORT.txt").read_text(
            encoding="utf-8"
        )
        assert "Frontend DOM security sink gate: FAIL" in report
        assert "innerHTML assignment" in report
        assert "Customer release manifest check: PASS" not in report
    finally:
        server.shutdown()
        server.server_close()


def test_final_delivery_package_is_customer_safe() -> None:
    client = TestClient(create_app())

    response = client.get("/api/delivery/final-package")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "phase_3_prepared"
    assert body["version"] == __version__
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["license"] == "MIT"
    deliverable_ids = {item["deliverable_id"] for item in body["deliverables"]}
    assert "docker-release" in deliverable_ids
    assert "source-archive" in deliverable_ids
    assert "final-business-plan" in deliverable_ids
    assert "final-presentation" in deliverable_ids
    assert "acceptance-checklist" in deliverable_ids
    assert body["next_gate"] == "customer_acceptance_signoff"
    assert "test-" + "operator-" + "token" not in response.text


def test_final_delivery_package_reports_open_signoff_items() -> None:
    client = TestClient(create_app())

    response = client.get("/api/delivery/final-package")

    assert response.status_code == 200
    gates = {item["gate_id"]: item for item in response.json()["open_gates"]}
    assert gates["production-owner-signoff"]["state"] == "pending_customer_action"
    assert gates["public-hosting-approval"]["state"] == "pending_customer_action"
    assert gates["final-acceptance"]["state"] == "pending_customer_action"


def test_acceptance_evidence_pack_combines_delivery_quality_and_gates(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "evidence-pack.db"))

    response = client.get("/api/delivery/evidence-pack")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_owner_review"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["license"] == "MIT"
    assert body["acceptance_score"] >= 60
    assert body["gate_summary"]["total"] >= 8
    gate_ids = {item["gate_id"] for item in body["gates"]}
    assert {
        "runtime-health",
        "operations-data",
        "agent-orchestra",
        "access-control",
        "assistant-quality",
        "reports-and-charts",
        "clean-room-release",
        "final-delivery",
    }.issubset(gate_ids)
    quality_dimensions = {item["dimension"] for item in body["quality_matrix"]}
    assert "Grounded assistant" in quality_dimensions
    assert "Agent A2A traceability" in quality_dimensions
    assert "Scoped access" in quality_dimensions
    assert body["reports"]["status"] == "ok"
    assert body["operations"]["counters"]["devices"] == 1
    assert len(body["agent_orchestration"]["agents"]) >= 6
    assert "roles" in body["access_policy"]
    assert body["ai"]["routing"]["status"] == "ok"
    assert body["final_delivery"]["package"]["status"] == "phase_3_prepared"
    assert any(item["state"].startswith("pending") for item in body["open_items"])
    assert "test-" + "operator-" + "token" not in response.text


def test_final_handoff_console_summarizes_owner_actions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "handoff-console.db"))

    response = client.get("/api/delivery/handoff-console")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_owner_review"
    assert body["version"] == __version__
    assert body["version"] == __version__
    assert body["handoff_score"] >= 60
    assert body["owner_decision_summary"]["total"] >= 5
    assert body["owner_decision_summary"]["approved"] == 0
    assert body["gate_summary"]["total"] >= 8
    assert body["next_action"].startswith("Resolve")
    assert body["display_action_queue"]
    assert len(body["display_action_queue"]) <= len(body["action_queue"])
    assert body["display_action_summary"]["display_action_count"] == len(
        body["display_action_queue"]
    )
    assert body["display_action_summary"]["raw_action_count"] == len(
        body["action_queue"]
    )
    assert any(
        item["occurrence_count"] > 1 for item in body["display_action_queue"]
    )
    for item in body["display_action_queue"]:
        assert item["customer_safe"] is True
        assert item["source_action_ids"]
        assert item["occurrence_count"] == len(item["source_action_ids"])
        assert item["blocking_category"] in {
            "admin_evidence",
            "customer_decision",
            "customer_runtime_config",
            "development_visible",
            "owner_signoff",
        }
        assert "/api/admin" not in json.dumps(item)
        assert '"method"' not in json.dumps(item)
    assert any(
        action["evidence_endpoint"] == "/api/production/approval-package"
        for action in body["action_queue"]
    )
    first_action = body["action_queue"][0]
    assert first_action["action_id"].startswith(("decision-", "control-"))
    assert first_action["blocking_category"] in {
        "admin_evidence",
        "customer_decision",
        "customer_runtime_config",
        "development_visible",
        "owner_signoff",
    }
    assert isinstance(first_action["can_close_without_customer_secret"], bool)
    assert first_action["safe_next_step"]
    assert first_action["required_input"]
    assert first_action["acceptance_impact"] in {
        "blocks_final_acceptance",
        "improves_runtime_readiness",
        "requires_owner_review",
    }
    assert body["action_summary"]["action_count"] == len(body["action_queue"])
    assert body["action_summary"]["customer_decision_required"] is True
    assert body["privacy"]["customer_delivery"] == "customer_safe"
    assert "test-" + "operator-" + "token" not in response.text


def test_management_delivery_brief_answers_owner_questions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "management-brief.db"))

    response = client.get("/api/delivery/management-brief")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["contract_phase_count"] == 3
    assert body["summary"]["remaining_contract_phase_count"] == 3
    assert body["summary"]["phase_1_technical_readiness_percent"] == 38
    assert body["summary"]["phase_2_technical_readiness_percent"] == 0
    assert body["summary"]["phase_3_technical_readiness_percent"] == 0
    assert body["summary"]["contractual_milestone_progress"] == "not_calculated"
    assert body["summary"]["customer_acceptance_claimed"] is False
    assert body["summary"]["phase4_policy"] == "post_contract_optional"
    assert body["summary"]["owner_question_count"] == len(body["questions_to_answer"])
    assert body["summary"]["p0_owner_question_count"] >= 1
    assert all(item["answer_options"] for item in body["questions_to_answer"])
    assert {
        item["acceptance_impact"] for item in body["questions_to_answer"]
    } <= {"blocks_final_acceptance", "requires_owner_review"}
    assert "technical readiness never implies customer acceptance" in body[
        "management_answer"
    ]
    assert "physical hardware validation" in body["management_answer"]
    assert len(body["needs_to_resolve"]) == 3
    assert all(item["can_be_solved_by_code"] is False for item in body["needs_to_resolve"])
    assert {item["need_id"] for item in body["needs_to_resolve"]} == {
        "customer-runtime-configuration",
        "model-route-approval",
        "production-owner-signoff",
    }
    assert len(body["phase_4_backlog"]) == 3
    market = body["competitive_position"]
    assert market["status"] == "contract_pilot_not_enterprise_parity"
    assert "not yet at Siemens" in market["summary"]
    assert "enterprise platform maturity" in market["summary"]
    assert len(market["benchmark_sources"]) == 4
    vendors = {item["vendor"] for item in market["benchmark_sources"]}
    assert "Siemens Insights Hub" in vendors
    assert "GE Vernova APM" in vendors
    assert "Bosch IoT Suite" in vendors
    assert "Microsoft Azure IoT Operations" in vendors
    assert market["source_basis"].startswith("Official vendor pages")
    assert body["privacy"]["customer_safe"] is True
    assert body["privacy"]["admin_write_endpoints_returned"] is False
    assert "/api/admin" not in response.text
    assert "test-" + "operator-" + "token" not in response.text
    assert "/home/" not in response.text
    assert "C:" not in response.text
    assert _marker([65, 71, 80, 76]) not in response.text
    assert _marker([72, 73, 68]) not in response.text


def test_public_delivery_and_goal_payloads_do_not_expose_admin_routes(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "public-leakage.db"))

    for endpoint in (
        "/api/delivery/management-brief",
        "/api/delivery/handoff-console",
        "/api/project/goal-optimization",
        "/api/recheck/latest",
    ):
        response = client.get(endpoint)

        assert response.status_code == 200
        assert "/api/admin" not in response.text
        assert "PATCH" not in response.text
        assert "/home/" not in response.text
        assert "C:" not in response.text
        assert "test-" + "operator-" + "token" not in response.text


def test_release_gap_console_surfaces_final_handoff_actions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "release-handoff-actions.db"))

    response = client.get("/api/release/gap-closure-console")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["summary"]["handoff_action_count"] >= 1
    assert body["summary"]["customer_decision_required"] is True
    assert body["summary"]["engineering_closeable_action_count"] >= 0
    assert body["handoff_acceptance_plan"]
    assert body["action_queue"]
    handoff_actions = [
        action for action in body["action_queue"] if action["source"] == "final_handoff"
    ]
    assert handoff_actions
    first_action = handoff_actions[0]
    assert first_action["blocking_category"] in {
        "admin_evidence",
        "customer_decision",
        "customer_runtime_config",
        "development_visible",
        "owner_signoff",
    }
    assert first_action["required_input"]
    assert first_action["safe_next_step"]
    assert first_action["acceptance_impact"] in {
        "blocks_final_acceptance",
        "improves_runtime_readiness",
        "requires_owner_review",
    }
    assert any(
        action["acceptance_impact"] == "blocks_final_acceptance"
        for action in handoff_actions
    )
    assert first_action["evidence_endpoint"].startswith("/")
    endpoints = {link["endpoint"] for link in body["evidence_links"]}
    assert "/api/delivery/handoff-console" in endpoints
    assert "test-" + "operator-" + "token" not in response.text
