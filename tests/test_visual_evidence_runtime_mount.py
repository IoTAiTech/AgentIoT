# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.17 | Date: 2026-07-14

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_https_launcher_mounts_live_visual_evidence_read_only() -> None:
    launcher = (PROJECT_ROOT / "docker" / "launch_https_proxy_8040.sh").read_text()

    assert 'visual_evidence_dir="${repo_root}/output/playwright"' in launcher
    assert 'mkdir -p "${visual_evidence_dir}"' in launcher
    assert '-v "${visual_evidence_dir}:/app/output/playwright:ro"' in launcher
