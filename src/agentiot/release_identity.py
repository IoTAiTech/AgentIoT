# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

"""Customer-safe release identity helpers for drift and delivery gates."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .version import __version__


SECRET_LIKE_SOURCE_LABEL = re.compile(
    r"(?i)^(sk-|ghp_|glpat-|AIza|xox[baprs]-|.*(?:secret|token|password|api[_-]?key).*)"
)
WORKTREE_DRIFT_PATHS = (
    "VERSION",
    "README.en.md",
    "README.de.md",
    "src/agentiot",
    "tests",
    "docker",
    "tools",
    "docs/customer",
    "docs/contract",
    "docs/governance",
)


def safe_source_commit(value: str) -> str:
    """Return a customer-safe source commit label."""

    cleaned = value.strip()[:64]
    if not re.fullmatch(r"[A-Za-z0-9._-]{4,64}", cleaned):
        return "unknown"
    if SECRET_LIKE_SOURCE_LABEL.search(cleaned):
        return "unknown"
    return cleaned


def runtime_manifest_digest() -> str:
    """Return the immutable runtime manifest digest baked into the image."""

    configured = os.getenv("AGENTIOT_RUNTIME_DIGEST", "").strip().lower()
    if re.fullmatch(r"sha256:[a-f0-9]{64}", configured):
        return configured
    return "unknown"


def source_commit_id(*, repo_root: Path | None = None, cwd: Path | None = None) -> str:
    """Return the source commit from env or local Git metadata without processes."""

    configured = os.getenv("AGENTIOT_SOURCE_COMMIT", "")
    if configured.strip():
        return safe_source_commit(configured)
    root = repo_root or Path(__file__).resolve().parents[2]
    current = cwd or Path.cwd()
    for candidate in (root, current):
        git_dir = candidate / ".git"
        try:
            head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if head.startswith("ref:"):
            ref_path = git_dir / head.split(":", 1)[1].strip()
            try:
                head = ref_path.read_text(encoding="utf-8").strip()
            except OSError:
                return "unknown"
        safe_commit = safe_source_commit(head[:12])
        if safe_commit != "unknown":
            return safe_commit
    return "unknown"


def source_worktree_state(
    *,
    repo_root: Path | None = None,
    cwd: Path | None = None,
) -> dict[str, object]:
    """Return customer-safe tracked source tree drift evidence."""

    root = repo_root or Path(__file__).resolve().parents[2]
    _ = cwd
    if not (root / ".git").exists():
        return {
            "state": "not_available",
            "dirty": False,
            "git_available": False,
            "changed_tracked_file_count": 0,
            "checked_path_count": len(WORKTREE_DRIFT_PATHS),
            "scope": "tracked_delivery_sources",
        }
    command = [
        "git",
        "-C",
        str(root),
        "status",
        "--porcelain",
        "--untracked-files=no",
        "--",
        *WORKTREE_DRIFT_PATHS,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return {
            "state": "unavailable",
            "dirty": False,
            "git_available": False,
            "changed_tracked_file_count": 0,
            "checked_path_count": len(WORKTREE_DRIFT_PATHS),
            "scope": "tracked_delivery_sources",
        }
    if result.returncode != 0:
        return {
            "state": "unavailable",
            "dirty": False,
            "git_available": True,
            "changed_tracked_file_count": 0,
            "checked_path_count": len(WORKTREE_DRIFT_PATHS),
            "scope": "tracked_delivery_sources",
        }
    changed_count = sum(1 for line in result.stdout.splitlines() if line.strip())
    return {
        "state": "dirty" if changed_count else "clean",
        "dirty": bool(changed_count),
        "git_available": True,
        "changed_tracked_file_count": changed_count,
        "checked_path_count": len(WORKTREE_DRIFT_PATHS),
        "scope": "tracked_delivery_sources",
    }


def source_release_version(*, repo_root: Path | None = None, cwd: Path | None = None) -> str:
    """Return the source package version used for drift-control comparison."""

    configured = os.getenv("AGENTIOT_SOURCE_VERSION", "").strip()
    if configured:
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", configured):
            return configured
        return "unknown"
    root = repo_root or Path(__file__).resolve().parents[2]
    current = cwd or Path.cwd()
    for candidate in (root / "VERSION", current / "VERSION"):
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value):
            return value
    return __version__
