# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _token(codes: list[int]) -> str:
    return "".join(chr(code) for code in codes)


def _pattern(codes: list[int], *, flags: int = 0) -> re.Pattern[str]:
    return re.compile(re.escape(_token(codes)), flags)


SOURCE_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
    REPO_ROOT / "docker",
    REPO_ROOT / "tools",
    REPO_ROOT / "docs/customer",
    REPO_ROOT / "docs/contract",
    REPO_ROOT / "docs/adr",
    REPO_ROOT / "docs/agent-cards",
)

TEXT_SUFFIXES = {
    ".html",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

ROOT_TEXT_FILES = (
    REPO_ROOT / "README.en.md",
    REPO_ROOT / "README.de.md",
    REPO_ROOT / "NOTICE.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "LICENSE",
    REPO_ROOT / "VERSION",
)

FORBIDDEN_SOURCE_MARKERS = (
    _pattern([72, 73, 68]),
    _pattern([80, 114, 111, 100, 117, 99, 116, 88], flags=re.IGNORECASE),
    _pattern(
        [72, 111, 115, 116, 32, 73, 110, 116, 101, 108, 108, 105, 103, 101, 110, 99, 101],
        flags=re.IGNORECASE,
    ),
    _pattern([65, 71, 80, 76], flags=re.IGNORECASE),
    _pattern([87, 101, 114, 107, 118, 101, 114, 116, 114, 97, 103], flags=re.IGNORECASE),
    _pattern([90, 117, 115, 99, 104, 108, 97, 103], flags=re.IGNORECASE),
    _pattern(
        [76, 101, 105, 115, 116, 117, 110, 103, 115, 98, 101, 115, 99, 104, 114, 101, 105, 98, 117, 110, 103],
        flags=re.IGNORECASE,
    ),
    _pattern([65, 110, 103, 101, 98, 111, 116], flags=re.IGNORECASE),
    _pattern([77, 65, 83, 84, 69, 82, 32, 65, 73, 32, 83, 89, 83, 84, 69, 77, 32, 80, 82, 79, 77, 80, 84]),
    _pattern([99, 111, 100, 101, 120, 32, 114, 101, 115, 117, 109, 101], flags=re.IGNORECASE),
    _pattern([80, 114, 111, 106, 101, 99, 116, 95, 80, 104, 97, 115, 101, 95, 67, 111, 111, 114, 100, 105, 110, 97, 116, 111, 114]),
    _pattern([82, 101, 108, 101, 97, 115, 101, 95, 67, 111, 109, 112, 108, 105, 97, 110, 99, 101, 95, 65, 117, 100, 105, 116, 111, 114]),
    _pattern([80, 114, 111, 100, 117, 99, 116, 95, 80, 114, 111, 106, 101, 99, 116, 95, 77, 97, 110, 97, 103, 101, 114]),
    _pattern([83, 87, 95, 82, 101, 108, 101, 97, 115, 101, 95, 65, 117, 100, 105, 116, 111, 114]),
    _pattern([67, 111, 100, 101, 95, 84, 101, 115, 116, 95, 65, 117, 100, 105, 116, 95, 65, 103, 101, 110, 116]),
    _pattern([85, 73, 95, 85, 88, 95, 69, 120, 112, 101, 114, 105, 101, 110, 99, 101, 95, 65, 117, 100, 105, 116, 111, 114]),
)

SECRET_LITERAL_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}"),
    re.compile(r"BEGIN (RSA|OPENSSH|PRIVATE) KEY"),
)


def _source_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in TEXT_SUFFIXES
            and "__pycache__" not in path.parts
        )
    files.extend(path for path in ROOT_TEXT_FILES if path.exists())
    return sorted(files)


def test_source_code_stays_free_of_external_project_and_contract_markers() -> None:
    violations: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in FORBIDDEN_SOURCE_MARKERS):
                relative = path.relative_to(REPO_ROOT)
                violations.append(f"{relative}:{line_number}: restricted marker")

    assert violations == []


def test_source_code_has_no_secret_like_literals() -> None:
    violations: list[str] = []
    for path in _source_files():
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in SECRET_LITERAL_PATTERNS):
                relative = path.relative_to(REPO_ROOT)
                violations.append(f"{relative}:{line_number}: secret-like literal")

    assert violations == []


def test_customer_docs_do_not_publish_stale_pseudo_api_routes() -> None:
    stale_route = "/api/release/evidence-console.execution_controls"
    violations: list[str] = []
    for path in (REPO_ROOT / "docs/customer").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if stale_route in line:
                relative = path.relative_to(REPO_ROOT)
                violations.append(f"{relative}:{line_number}: {stale_route}")

    assert violations == []


def test_repo_root_has_no_local_runtime_secret_or_temp_artifacts() -> None:
    forbidden_roots = (
        REPO_ROOT / ".tmp",
        REPO_ROOT / "secrets",
    )
    forbidden_names = {
        ".env",
        "runtime-8040.env",
        "operator_token",
        "admin_token",
        "credential_fernet_key",
    }
    violations: list[str] = []

    for root in forbidden_roots:
        if root.exists():
            violations.append(str(root.relative_to(REPO_ROOT)))

    for path in REPO_ROOT.rglob("*"):
        if path.is_file() and path.name in forbidden_names:
            violations.append(str(path.relative_to(REPO_ROOT)))

    assert violations == []


def test_repo_tree_has_no_python_bytecode_artifacts() -> None:
    violations = [
        str(path.relative_to(REPO_ROOT))
        for path in REPO_ROOT.rglob("*")
        if "__pycache__" in path.parts or path.suffix == ".pyc"
    ]

    assert violations == []


def test_readme_secret_examples_use_external_runtime_directory() -> None:
    for path in (REPO_ROOT / "README.en.md", REPO_ROOT / "README.de.md"):
        text = path.read_text(encoding="utf-8")
        assert "mkdir -p secrets" not in text
        assert "> secrets/" not in text
        assert "AGENTIOT_RUNTIME_SECRET_DIR" in text


def test_release_builder_rejects_ignored_runtime_artifacts() -> None:
    text = (REPO_ROOT / "tools" / "build_customer_release.sh").read_text(
        encoding="utf-8"
    )

    assert "run_repo_runtime_artifact_gate" in text
    assert "clean_python_bytecode_artifacts" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "${repo_root}/.tmp" in text
    assert "${repo_root}/secrets" in text
    assert "runtime-*.env" in text


def test_root_page_uses_operator_labels_for_static_evidence_pills() -> None:
    text = (REPO_ROOT / "src" / "agentiot" / "root_page.html").read_text(
        encoding="utf-8"
    )
    visible_api_pill = re.compile(r"<span class=\"shell-pill\">/api/")

    assert visible_api_pill.search(text) is None
    assert "data-evidence-endpoint=\"/api/cmdb/configuration-items\"" in text
    assert "Sensor inventory records</span>" in text


def test_release_root_metadata_uses_current_version() -> None:
    version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    checks = {
        REPO_ROOT / "NOTICE.md": [
            f"# Version: {version}",
            f"Runtime Dependency Audit - Version {version}",
        ],
        REPO_ROOT / ".gitignore": [
            f"# Version: {version}",
            f"!output/playwright/agentiot-v{version}-*",
        ],
        REPO_ROOT / "requirements.lock": [
            f"# Version: {version}",
        ],
        REPO_ROOT / "docs/governance/ALWAYS_ON_CHECKLIST.en.md": [
            f"# Version: {version}",
        ],
        REPO_ROOT / "docs/governance/ALWAYS_ON_CHECKLIST.de.md": [
            f"# Version: {version}",
        ],
    }

    for path, fragments in checks.items():
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            assert fragment in text


def test_release_builder_checks_root_metadata_versions() -> None:
    text = (REPO_ROOT / "tools" / "build_customer_release.sh").read_text(
        encoding="utf-8"
    )

    assert "root_version_files" in text
    assert 'release_dir / ".gitignore"' in text
    assert 'release_dir / "NOTICE.md"' in text
    assert 'release_dir / "requirements.lock"' in text
    assert "runtime_audit_header" in text
    assert "visual_allow_ref" in text


def test_root_page_direct_routes_scroll_to_primary_workspace_cards() -> None:
    text = (REPO_ROOT / "src" / "agentiot" / "root_page.html").read_text(
        encoding="utf-8"
    )

    assert "'/tests': { view: 'agents', target: 'ui-quality-gate', scrollTarget: 'shell-test-workspace-card'" in text
    assert "'/evidence': { view: 'operate', target: 'api-evidence', scrollTarget: 'shell-evidence-workspace-card'" in text
    assert "openWorkspaceSection(route.view, route.target, route.message, route.scrollTarget);" in text
    assert "const scrollTarget = routeTarget || contextPanel || target;" in text
