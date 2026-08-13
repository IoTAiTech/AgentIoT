# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Customer-safe browser visual quality evidence helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


def visual_evidence_freshness(
    generated_at: Any,
    *,
    max_age_hours: int = 6,
    future_tolerance_seconds: int = 300,
    now_fn: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Return freshness status for browser visual evidence."""

    base = {
        "status": "missing",
        "max_age_hours": max_age_hours,
        "age_seconds": None,
    }
    if not isinstance(generated_at, str) or not generated_at.strip():
        return base
    try:
        generated_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return {**base, "status": "invalid"}
    if generated_dt.tzinfo is None:
        return {**base, "status": "invalid"}
    now = now_fn() if now_fn else datetime.now(UTC)
    generated_utc = generated_dt.astimezone(UTC)
    age = now - generated_utc
    if age.total_seconds() < -future_tolerance_seconds:
        return {**base, "status": "future"}
    age_seconds = max(0, int(age.total_seconds()))
    if age > timedelta(hours=max_age_hours):
        return {**base, "status": "stale", "age_seconds": age_seconds}
    return {**base, "status": "fresh", "age_seconds": age_seconds}


def build_visual_qa_evidence(
    *,
    repo_root: Path,
    version: str,
    source_commit: str,
    max_age_hours: int = 6,
    future_tolerance_seconds: int = 300,
) -> dict[str, Any]:
    """Return customer-safe browser visual QA evidence without local paths."""

    required_routes = (
        "/",
        "/operations",
        "/charts",
        "/analytics",
        "/status",
        "/reports",
        "/tests",
        "/evidence",
        "/settings",
    )
    required_viewports = ("mobile", "desktop", "desktop-wide")
    expected_report = repo_root / "output" / "playwright" / f"agentiot-v{version}-visual-report.json"
    report_path = expected_report
    if not report_path.exists():
        candidates = sorted((repo_root / "output" / "playwright").glob("agentiot-v*-visual-report.json"))
        report_path = candidates[-1] if candidates else expected_report
    evidence = {
        "status": "PENDING",
        "source_version": f"{version}+{source_commit}",
        "live_version": version,
        "report_version": "unknown",
        "report_attached": False,
        "evidence_ref": "visual-qa-current",
        "required_routes": list(required_routes),
        "required_viewports": list(required_viewports),
        "covered_routes": [],
        "covered_viewports": [],
        "missing_routes": list(required_routes),
        "missing_viewports": list(required_viewports),
        "missing_route_viewport_pairs": [
            f"{route}@{viewport}"
            for route in required_routes
            for viewport in required_viewports
        ],
        "missing_screenshots": [],
        "route_count": 0,
        "screenshot_count": 0,
        "viewport_count": 0,
        "check_count": 0,
        "passed_count": 0,
        "console_error_count": 0,
        "console_warning_count": 0,
        "console_error_routes": [],
        "generated_at": None,
        "freshness": visual_evidence_freshness(
            None,
            max_age_hours=max_age_hours,
            future_tolerance_seconds=future_tolerance_seconds,
        ),
        "customer_safe": True,
    }
    if not report_path.exists():
        return evidence
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        evidence["status"] = "UNREADABLE"
        return evidence

    checks_raw = payload.get("checks") or payload.get("results") or []
    checks = [item for item in checks_raw if isinstance(item, dict)] if isinstance(checks_raw, list) else []
    payload_total = payload.get("total_count") or payload.get("total")
    payload_passed = payload.get("passed_count") or payload.get("passed")
    if isinstance(payload_passed, bool):
        payload_passed = None
    total_count = int(payload_total) if isinstance(payload_total, int) else len(checks)
    passed_count = (
        int(payload_passed)
        if isinstance(payload_passed, int)
        else sum(
            1
            for item in checks
            if item.get("status") == "PASS"
            or item.get("passed") is True
            or item.get("pass") is True
        )
    )
    viewports = payload.get("viewports") or []
    routes = payload.get("routes") or []
    normalized_routes = {
        str(route)
        for route in routes
        if isinstance(route, str) and route.startswith("/")
    }
    normalized_viewports = {
        str(item.get("name") if isinstance(item, dict) else item)
        for item in viewports
        if str(item.get("name") if isinstance(item, dict) else item)
    }
    passed_pairs: set[tuple[str, str]] = set()
    screenshot_paths: set[str] = set()
    missing_screenshots: list[str] = []
    for item in checks:
        route = item.get("route")
        viewport = item.get("viewport")
        if isinstance(route, str) and route.startswith("/"):
            normalized_routes.add(route)
        if isinstance(viewport, str) and viewport:
            normalized_viewports.add(viewport)
        passed = (
            item.get("status") == "PASS"
            or item.get("passed") is True
            or item.get("pass") is True
        )
        if isinstance(route, str) and isinstance(viewport, str) and passed:
            passed_pairs.add((route, viewport))
        screenshot = item.get("screenshot") or item.get("screenshot_path")
        if isinstance(screenshot, str) and screenshot.startswith("output/playwright/"):
            screenshot_paths.add(screenshot)
            if not (repo_root / screenshot).exists():
                missing_screenshots.append(screenshot)
    payload_screenshot = payload.get("screenshot_path")
    if isinstance(payload_screenshot, str) and payload_screenshot.startswith("output/playwright/"):
        screenshot_paths.add(payload_screenshot)
        if not (repo_root / payload_screenshot).exists():
            missing_screenshots.append(payload_screenshot)

    console_events_raw = payload.get("console_events") or []
    console_events = (
        [item for item in console_events_raw if isinstance(item, dict)]
        if isinstance(console_events_raw, list)
        else []
    )
    console_events = [
        item
        for item in console_events
        if "net::ERR_NETWORK_CHANGED" not in str(item.get("text", ""))
    ]

    def console_level(item: dict[str, Any]) -> str:
        level = item.get("level", item.get("type", ""))
        return str(level).lower()

    console_error_count = sum(
        1 for item in console_events if console_level(item) == "error"
    )
    console_warning_count = sum(
        1 for item in console_events if console_level(item) in {"warning", "warn"}
    )
    console_error_routes = sorted(
        {
            urlparse(route).path or "/"
            for item in console_events
            if console_level(item) == "error"
            for route in [item.get("route")]
            if isinstance(route, str)
        }
    )

    missing_routes = sorted(set(required_routes) - normalized_routes)
    missing_viewports = sorted(set(required_viewports) - normalized_viewports)
    missing_pairs = [
        f"{route}@{viewport}"
        for route in required_routes
        for viewport in required_viewports
        if (route, viewport) not in passed_pairs
    ]
    viewport_count = (
        len(viewports)
        if isinstance(viewports, list) and viewports
        else len({str(item.get("viewport")) for item in checks if item.get("viewport")})
    )
    report_version = str(payload.get("version") or payload.get("live_version") or "unknown")
    freshness = visual_evidence_freshness(
        payload.get("generated_at"),
        max_age_hours=max_age_hours,
        future_tolerance_seconds=future_tolerance_seconds,
    )
    evidence.update(
        {
            "status": (
                "PASS"
                if total_count > 0
                and passed_count == total_count
                and report_version == version
                and not missing_routes
                and not missing_viewports
                and not missing_pairs
                and not missing_screenshots
                and console_error_count == 0
                and freshness["status"] == "fresh"
                else "STALE"
            ),
            "report_version": report_version,
            "route_count": len(normalized_routes),
            "viewport_count": max(viewport_count, len(normalized_viewports)),
            "screenshot_count": len(screenshot_paths),
            "covered_routes": sorted(normalized_routes),
            "covered_viewports": sorted(normalized_viewports),
            "report_attached": True,
            "evidence_ref": "visual-qa-current",
            "missing_routes": missing_routes,
            "missing_viewports": missing_viewports,
            "missing_route_viewport_pairs": missing_pairs,
            "missing_screenshots": sorted(set(missing_screenshots)),
            "check_count": total_count,
            "passed_count": passed_count,
            "console_error_count": console_error_count,
            "console_warning_count": console_warning_count,
            "console_error_routes": console_error_routes,
            "generated_at": payload.get("generated_at"),
            "freshness": freshness,
        }
    )
    return evidence
