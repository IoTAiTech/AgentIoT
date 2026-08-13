# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.1 | Date: 2026-08-11

from pathlib import Path

from agentiot.network_discovery import (
    DISCOVERY_TOTAL_TIMEOUT_SECONDS,
    MAX_DISCOVERY_CONCURRENCY,
    MAX_DISCOVERY_HOSTS,
    PROTOCOL_PORT_HINTS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pi4_runtime_keeps_bounded_resources_and_no_raw_network_capability() -> None:
    compose = (REPO_ROOT / "docker" / "compose.yaml").read_text(encoding="utf-8")

    assert "mem_limit: 768m" in compose
    assert "pids_limit: 256" in compose
    assert "cap_drop:\n      - ALL" in compose
    assert "read_only: true" in compose
    assert "network_mode: host" not in compose
    assert "privileged: true" not in compose
    assert "NET_RAW" not in compose


def test_network_discovery_uses_a_fixed_edge_safe_budget() -> None:
    assert MAX_DISCOVERY_HOSTS == 32
    assert MAX_DISCOVERY_CONCURRENCY == 8
    assert DISCOVERY_TOTAL_TIMEOUT_SECONDS == 5.0
    assert PROTOCOL_PORT_HINTS == (
        (80, "http"),
        (443, "https"),
        (1883, "mqtt"),
        (8883, "mqtts"),
        (4840, "opcua"),
        (502, "modbus_tcp"),
    )


def test_discovery_does_not_add_heavy_or_privileged_scanners() -> None:
    dependency_text = "\n".join(
        [
            (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
            (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8"),
        ]
    ).lower()

    for forbidden in ("nmap", "scapy", "python-nmap", "netifaces", "zeroconf"):
        assert forbidden not in dependency_text
