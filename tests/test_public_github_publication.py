# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 1.0.0 | Date: 2026-08-13
"""Publication gate: public trees stay free of private documents."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]


def _load_scanner():
    path = REPO / "tools" / "scan_public_github_tree.py"
    spec = importlib.util.spec_from_file_location("scan_public_github_tree", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fleet(*parts: int) -> str:
    return ".".join(str(part) for part in parts)


def test_coder_guide_and_policy_exist() -> None:
    guide = (REPO / "docs/github/CODER_GUIDE.md").read_text(encoding="utf-8")
    policy = (REPO / "docs/github/PUBLICATION_POLICY.md").read_text(encoding="utf-8")
    assert "Do **not** upload" in guide
    assert "docs/contract" in policy
    agents = REPO / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        assert "A1.1 GitHub publication" in text
        assert "CODER_GUIDE.md" in text


def test_scanner_rejects_contract_path(tmp_path: Path) -> None:
    scanner = _load_scanner()
    dirty = tmp_path / "export"
    (dirty / "docs" / "contract").mkdir(parents=True)
    (dirty / "docs" / "contract" / "secret.md").write_text("private", encoding="utf-8")
    report = scanner.scan(dirty)
    assert report["ok"] is False
    assert any("deny-path" in item for item in report["path_violations"])


def test_scanner_rejects_fleet_literal(tmp_path: Path) -> None:
    scanner = _load_scanner()
    dirty = tmp_path / "export"
    dirty.mkdir()
    (dirty / "README.md").write_text(f"host {_fleet(192, 168, 50, 30)}\n", encoding="utf-8")
    report = scanner.scan(dirty)
    assert report["ok"] is False
    assert any(item.startswith("fleet-ip:") for item in report["content_violations"])


def test_sanitize_then_scan_passes(tmp_path: Path) -> None:
    scanner = _load_scanner()
    tree = tmp_path / "export"
    tree.mkdir()
    (tree / "README.md").write_text(
        f"example {_fleet(192, 168, 50, 30)} and { _fleet(192, 168, 50, 21)}\n",
        encoding="utf-8",
    )
    changed = scanner.sanitize_tree(tree)
    assert changed == 1
    report = scanner.scan(tree)
    assert report["ok"] is True
    text = (tree / "README.md").read_text(encoding="utf-8")
    assert _fleet(192, 168, 50) not in text


def test_exporter_and_public_compose_exist() -> None:
    assert (REPO / "tools/export_public_github_tree.sh").is_file()
    compose = (REPO / "docker/compose.public.yaml").read_text(encoding="utf-8")
    dockerfile = (REPO / "docker/Dockerfile.public").read_text(encoding="utf-8")
    assert "ollama.example.internal" in compose
    assert _fleet(192, 168, 50) not in compose
    assert "docs/customer" not in dockerfile
    assert "docs/contract" not in dockerfile
