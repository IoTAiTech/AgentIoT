# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

from pathlib import Path


ROOT_PAGE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "agentiot"
    / "root_page.html"
)


def test_live_platform_telemetry_is_a_compact_read_only_assurance_panel() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert 'id="shell-platform-telemetry"' in body
    assert "Live platform telemetry" in body
    for metric_id in (
        "shell-observability-uptime",
        "shell-observability-load",
        "shell-observability-memory",
        "shell-observability-storage",
        "shell-observability-network",
    ):
        assert f'id="{metric_id}"' in body
    for summary_id in (
        "shell-observability-component-status",
        "shell-observability-issue",
        "shell-observability-next-action",
    ):
        assert f'id="{summary_id}"' in body
    assert "Run self-check" in body
    assert "'/api/system/observability'" in body
    assert "function renderPlatformTelemetry" in body
    assert "function formatObservability" in body
    assert "Promise.allSettled" in body
    assert "textContent" in body
    assert ".innerHTML" not in body


def test_live_platform_telemetry_stays_customer_safe_and_mobile_stable() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert ".shell-platform-telemetry-grid" in body
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in body
    assert "@media (max-width: 520px)" in body
    assert "grid-template-columns: 1fr;" in body
    telemetry_start = body.index('id="shell-platform-telemetry"')
    telemetry_end = body.index('id="shell-workbench-live-path"', telemetry_start)
    telemetry = body[telemetry_start:telemetry_end]
    for forbidden_text in (
        "JSON",
        "/api/",
        "/home/",
        "localhost",
        "127.0.0.1",
        "build",
        "internal",
    ):
        assert forbidden_text not in telemetry


def test_live_platform_telemetry_reads_the_runtime_observability_contract() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    for backend_path in (
        "process.uptime_seconds",
        "load.one_minute",
        "memory.used_bytes",
        "disk.used_bytes",
        "network.received_bytes",
        "network.sent_bytes",
    ):
        assert f"'{backend_path}'" in body
    assert "observability && observability.issues" in body
    assert "observability?.next_action" in body
    assert "issues.length > 0" in body
