# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.13 | Date: 2026-08-13

"""Runtime architecture and hardware-identity tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agentiot.app import create_app
from agentiot.runtime_platform import architecture_sign, hardware_technology, runtime_host_identity
from agentiot.version import __version__


def test_architecture_sign_maps_x86_and_arm() -> None:
    assert architecture_sign("x86_64") == ("x86", "x86_64")
    assert architecture_sign("amd64") == ("x86", "x86_64")
    assert architecture_sign("aarch64") == ("ARM", "arm64")
    assert architecture_sign("armv7l") == ("ARM", "arm")


def test_hardware_technology_labels_boards() -> None:
    assert "Raspberry Pi 5" in hardware_technology(
        sign="ARM", family="arm64", board="Raspberry Pi 5 Model B", cpu=""
    )
    assert hardware_technology(
        sign="x86", family="x86_64", board="", cpu="Intel"
    ) == "x86_64 Linux edge"


def test_runtime_host_identity_is_customer_safe() -> None:
    identity = runtime_host_identity()
    assert identity["architecture_sign"] in {"x86", "ARM", "unknown"}
    assert identity["hardware_technology"]
    assert identity["privacy"]["serial_returned"] is False
    assert identity["privacy"]["hostname_returned"] is False
    blob = " ".join(str(value) for value in identity.values())
    assert "serial" not in blob.lower() or "serial_returned" in blob


def test_version_endpoint_exposes_architecture_and_hardware() -> None:
    client = TestClient(create_app())
    body = client.get("/api/version").json()
    assert body["version"] == __version__
    assert body["architecture_sign"] in {"x86", "ARM", "unknown"}
    assert body["hardware_technology"]
    assert "serial" not in body["hardware_technology"].lower()


def test_login_page_shows_arch_near_version() -> None:
    client = TestClient(create_app())
    page = client.get("/login").text
    assert f"Version {__version__}" in page
    assert 'id="login-arch-badge"' in page
    assert page.count("{{ARCH_SIGN}}") == 0


def test_cockpit_renders_arch_badge_and_honest_assistant() -> None:
    client = TestClient(create_app())
    page = client.get("/dashboard").text
    assert 'id="shell-arch-badge"' in page
    assert 'id="shell-hardware-tech"' in page
    assert "Version 0.157.10" not in page
    assert f"Version {__version__}" in page
    assert 'id="settings-readiness-ledger"' in page
    assert 'id="shell-assistant-recheck"' in page
    assert 'id="shell-version-badge"' in page
    assert "Recheck model host" in page
    assert "Evidence-only" in page or "evidence-only review" in page
    assert page.count("{{ARCH_SIGN}}") == 0
    assert page.count("{{HARDWARE_TECH}}") == 0
