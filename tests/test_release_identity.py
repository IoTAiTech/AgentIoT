# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Tests for customer-safe release identity helpers."""

from types import SimpleNamespace

from agentiot.release_identity import (
    runtime_manifest_digest,
    safe_source_commit,
    source_commit_id,
    source_release_version,
    source_worktree_state,
)


def marker(*codes: int) -> str:
    return "".join(chr(code) for code in codes)


def test_safe_source_commit_accepts_only_customer_safe_labels() -> None:
    assert safe_source_commit("abc1234") == "abc1234"
    assert safe_source_commit("release_2026.06-rc1") == "release_2026.06-rc1"
    assert safe_source_commit("abc") == "unknown"
    assert safe_source_commit("../../secret") == "unknown"
    assert (
        safe_source_commit("abc1234 " + marker(47, 104, 111, 109, 101, 47, 105, 111, 116))
        == "unknown"
    )
    assert safe_source_commit(marker(115, 107, 45) + ("A" * 24)) == "unknown"
    assert safe_source_commit(marker(103, 104, 112, 95) + ("A" * 24)) == "unknown"


def test_source_commit_id_prefers_safe_env_and_reads_git_metadata(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "envcommit_123")
    assert source_commit_id(repo_root=tmp_path, cwd=tmp_path) == "envcommit_123"

    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "bad/path")
    assert source_commit_id(repo_root=tmp_path, cwd=tmp_path) == "unknown"

    monkeypatch.delenv("AGENTIOT_SOURCE_COMMIT", raising=False)
    git_dir = tmp_path / ".git"
    ref_dir = git_dir / "refs" / "heads"
    ref_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (ref_dir / "main").write_text("abcdef1234567890abcdef\n")
    assert source_commit_id(repo_root=tmp_path, cwd=tmp_path) == "abcdef123456"


def test_source_release_version_prefers_safe_env_then_version_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AGENTIOT_SOURCE_VERSION", "0.152.8")
    assert source_release_version(repo_root=tmp_path, cwd=tmp_path) == "0.152.8"

    monkeypatch.setenv("AGENTIOT_SOURCE_VERSION", "0.141.bad")
    assert source_release_version(repo_root=tmp_path, cwd=tmp_path) == "unknown"

    monkeypatch.delenv("AGENTIOT_SOURCE_VERSION", raising=False)
    (tmp_path / "VERSION").write_text("0.152.8\n")
    assert source_release_version(repo_root=tmp_path, cwd=tmp_path) == "0.152.8"


def test_runtime_manifest_digest_accepts_only_sha256(monkeypatch) -> None:
    valid = "sha256:" + ("b" * 64)
    monkeypatch.setenv("AGENTIOT_RUNTIME_DIGEST", valid)
    assert runtime_manifest_digest() == valid

    monkeypatch.setenv("AGENTIOT_RUNTIME_DIGEST", "bad/digest")
    assert runtime_manifest_digest() == "unknown"

    monkeypatch.delenv("AGENTIOT_RUNTIME_DIGEST", raising=False)
    assert runtime_manifest_digest() == "unknown"


def test_source_worktree_state_reports_dirty_without_paths(monkeypatch, tmp_path) -> None:
    (tmp_path / ".git").mkdir()

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=" M src/agentiot/app.py\n", stderr="")

    monkeypatch.setattr("agentiot.release_identity.subprocess.run", fake_run)

    state = source_worktree_state(repo_root=tmp_path)

    assert state["state"] == "dirty"
    assert state["dirty"] is True
    assert state["changed_tracked_file_count"] == 1
    assert "app.py" not in str(state)


def test_source_worktree_state_does_not_block_release_without_git(tmp_path) -> None:
    state = source_worktree_state(repo_root=tmp_path)

    assert state["state"] == "not_available"
    assert state["dirty"] is False
    assert state["git_available"] is False
