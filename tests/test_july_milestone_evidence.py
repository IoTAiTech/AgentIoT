# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.2 | Date: 2026-08-09

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from runpy import run_path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
EVIDENCE_PATH = (
    REPO_ROOT
    / f"docs/customer/phase1/evidence/JULY_PROTOCOL_LAB_{CURRENT_VERSION}.json"
)
VISUAL_REPORT_PATH = (
    REPO_ROOT / f"output/playwright/agentiot-v{CURRENT_VERSION}-visual-report.json"
)
DIGEST_TOOL_PATH = REPO_ROOT / "tools/compute_customer_runtime_digest.py"
PROTOCOL_RUNNER_PATH = REPO_ROOT / "tools/run_july_protocol_lab.py"


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _current_runtime_digest() -> str:
    namespace = run_path(str(DIGEST_TOOL_PATH))
    compute = namespace["compute_runtime_digest"]
    assert isinstance(compute, Callable)
    return compute(REPO_ROOT)


def test_runtime_digest_normalizes_non_executable_checkout_modes(
    tmp_path: Path,
) -> None:
    namespace = run_path(str(DIGEST_TOOL_PATH))
    normalize = namespace["normalized_runtime_mode"]
    candidate = tmp_path / "runtime-source.txt"
    candidate.write_text("same-content", encoding="utf-8")

    candidate.chmod(0o600)
    owner_only = normalize(candidate.stat())
    candidate.chmod(0o664)
    group_writable = normalize(candidate.stat())
    candidate.chmod(0o755)
    executable = normalize(candidate.stat())

    assert owner_only == b"0644"
    assert group_writable == b"0644"
    assert executable == b"0755"


def test_runtime_digest_excludes_release_ignored_generated_files() -> None:
    namespace = run_path(str(DIGEST_TOOL_PATH))
    ignored = namespace["ignored_runtime_candidate"]

    assert ignored(Path("src/agentiot/__pycache__/app.cpython-312.pyc"))
    assert ignored(Path("src/agentiot/.ruff_cache/state"))
    assert ignored(Path("src/agentiot/generated.orig"))
    assert not ignored(Path("src/agentiot/app.py"))


def test_protocol_runner_restricts_secret_to_the_image_user(tmp_path: Path) -> None:
    namespace = run_path(str(PROTOCOL_RUNNER_PATH))
    commands: list[tuple[str, ...]] = []

    def capture(*args: str, stream: bool = False) -> str:
        commands.append(args)
        return ""

    namespace["restrict_secret_to_image_user"].__globals__["run"] = capture
    secret = tmp_path / "operator-token"
    secret.write_text("not-forwarded-to-docker-arguments", encoding="ascii")
    secret.chmod(stat.S_IRUSR | stat.S_IWUSR)

    namespace["restrict_secret_to_image_user"]("candidate:test", secret)

    assert len(commands) == 1
    command = commands[0]
    assert command[:6] == ("docker", "run", "--rm", "--user", "0", "-v")
    assert command[7] == "candidate:test"
    assert "chown" in command[10]
    assert "chmod 600" in command[10]
    assert command[-1] == "operator-token"
    assert "not-forwarded-to-docker-arguments" not in " ".join(command)


def test_protocol_runner_uses_an_internal_lab_network() -> None:
    runner = PROTOCOL_RUNNER_PATH.read_text(encoding="utf-8")

    assert 'run("docker", "network", "create", "--internal", network)' in runner
    assert '"{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"' in runner
    assert '"127.0.0.1::8080"' not in runner


def test_july_protocol_evidence_is_version_bound_and_honest() -> None:
    evidence = _load_json(EVIDENCE_PATH)

    assert evidence["schema_version"] == "agentiot.phase1.july-evidence.v2"
    assert evidence["status"] == "PASS"
    assert evidence["version"] == CURRENT_VERSION
    assert len(evidence["runtime_source_commit"]) == 40
    assert evidence["runtime_source_digest"] == _current_runtime_digest()
    assert evidence["app_image_id"].startswith("sha256:")
    assert evidence["broker_image_id"].startswith("sha256:")

    scope = evidence["scope"]
    assert isinstance(scope, dict)
    assert scope["environment"] == "isolated x86_64 lab runtime"
    assert scope["production_acceptance"] is False
    assert scope["physical_arm_validated"] is False
    assert scope["customer_edge_deployed"] is False

    reproduction = evidence["reproduction"]
    assert reproduction["command"] == [
        "python3",
        "tools/run_july_protocol_lab.py",
    ]
    assert reproduction["runner_sha256"] == (
        "sha256:" + hashlib.sha256(PROTOCOL_RUNNER_PATH.read_bytes()).hexdigest()
    )
    assert reproduction["clean_source_required"] is True
    assert reproduction["temporary_secret_file_removed"] is True


def test_july_protocol_artifacts_are_relative_and_hash_bound() -> None:
    artifacts = _load_json(EVIDENCE_PATH)["artifacts"]
    assert isinstance(artifacts, list)
    assert len(artifacts) == 6

    for artifact in artifacts:
        assert isinstance(artifact, dict)
        relative = Path(artifact["path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        assert relative.parts[:4] == (
            "docs",
            "customer",
            "phase1",
            "evidence",
        )
        path = REPO_ROOT / relative
        content = path.read_bytes()
        assert artifact["bytes"] == len(content)
        assert artifact["sha256"] == (
            "sha256:" + hashlib.sha256(content).hexdigest()
        )


def test_july_mqtt_and_rest_lifecycles_have_real_lab_receipts() -> None:
    checks = _load_json(EVIDENCE_PATH)["checks"]
    assert isinstance(checks, dict)

    mqtt_broker = checks["mqtt_broker"]
    mqtt_lifecycle = checks["mqtt_lifecycle"]
    rest_lifecycle = checks["rest_lifecycle"]
    assert isinstance(mqtt_broker, dict)
    assert isinstance(mqtt_lifecycle, dict)
    assert isinstance(rest_lifecycle, dict)

    assert mqtt_broker["connected"] is True
    assert mqtt_broker["messages_accepted"] == 1
    assert mqtt_broker["messages_rejected"] == 0
    assert mqtt_lifecycle["records"] == 1
    assert mqtt_lifecycle["metric"] == "temperature_c"
    assert rest_lifecycle["records"] == 1
    assert rest_lifecycle["metric"] == "oxygen_pct"


def test_july_firmware_evidence_keeps_arm_validation_fail_closed() -> None:
    checks = _load_json(EVIDENCE_PATH)["checks"]
    assert isinstance(checks, dict)

    x86 = checks["x86_64_firmware"]
    pi4 = checks["raspberry_pi_4_boundary"]
    assert isinstance(x86, dict)
    assert isinstance(pi4, dict)

    assert x86["compatible"] is True
    assert x86["evidence_state"] == "runtime_smoke_validated"
    assert pi4["compatible"] is False
    assert pi4["evidence_state"] == "verification_required"
    assert pi4["risk_level"] == "review_required"


def test_m14_visual_evidence_matches_the_current_candidate() -> None:
    evidence = _load_json(EVIDENCE_PATH)
    visual = _load_json(VISUAL_REPORT_PATH)
    current_digest = _current_runtime_digest()

    assert visual["status"] == "PASS"
    assert visual["version"] == evidence["version"]
    assert visual["source_digest"] == current_digest
    assert visual["live_runtime_digest"] == current_digest
    assert visual["runtime_scope"] == "isolated-local-qa"
    assert "base_url" not in visual
    assert visual["total_count"] == 92
    assert visual["passed_count"] == 92
    assert visual["failed_count"] == 0
    assert visual["console_events"] == []
    assert len(visual["routes"]) == 22
    screenshot_paths = visual["screenshot_paths"]
    screenshot_artifacts = visual["screenshot_artifacts"]
    assert isinstance(screenshot_paths, list)
    assert isinstance(screenshot_artifacts, list)
    assert len(screenshot_paths) == 92
    assert len(set(screenshot_paths)) == 92
    assert len(screenshot_artifacts) == 92
    assert {item["path"] for item in screenshot_artifacts} == set(screenshot_paths)
    for artifact in screenshot_artifacts:
        path = REPO_ROOT / artifact["path"]
        content = path.read_bytes()
        assert artifact["bytes"] == len(content)
        assert artifact["sha256"] == (
            "sha256:" + hashlib.sha256(content).hexdigest()
        )


def test_derived_phase_evidence_is_outside_the_runtime_digest_scope() -> None:
    namespace = run_path(str(DIGEST_TOOL_PATH))
    runtime_files = namespace["_runtime_files"](REPO_ROOT)
    evidence_root = EVIDENCE_PATH.parent
    assert all(evidence_root not in path.parents for path in runtime_files)


def test_customer_reports_preserve_the_july_acceptance_boundary() -> None:
    paths = (
        REPO_ROOT / "docs/contract/CONTRACT_TRACEABILITY.en.md",
        REPO_ROOT / "docs/contract/CONTRACT_TRACEABILITY.de.md",
        REPO_ROOT / "docs/customer/monthly/JULY_2026_REPORT.en.md",
        REPO_ROOT / "docs/customer/monthly/JULY_2026_REPORT.de.md",
        REPO_ROOT / "docs/customer/phase1/PHASE_1_REPORT.en.md",
        REPO_ROOT / "docs/customer/phase1/PHASE_1_REPORT.de.md",
        REPO_ROOT / "docs/customer/phase1/UI_INTERACTION_SPEC.en.md",
        REPO_ROOT / "docs/customer/phase1/UI_INTERACTION_SPEC.de.md",
    )

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "0.152.16" not in text
        assert CURRENT_VERSION in text

    english = paths[2].read_text(encoding="utf-8")
    german = paths[3].read_text(encoding="utf-8")
    assert "87%" not in english
    assert "87%" not in german
    assert "M1.4 and M1.5 have passed their technical July evidence gates" in english
    assert "M1.4 und M1.5 haben ihre technischen Juli-Nachweisgates bestanden" in german
    assert "M1.6 remains" in english
    assert "M1.6 bleibt" in german
    assert "not customer acceptance" in english
    assert "keine Kundenabnahme" in german
