# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.1 | Date: 2026-08-11

"""Deterministic tests for bounded private-network discovery."""

from __future__ import annotations

import asyncio
import errno

import pytest

from agentiot import network_discovery


@pytest.mark.parametrize(
    "scope",
    (
        "invalid",
        "8.8.8.8/32",
        "127.0.0.1/32",
        "169.254.1.1/32",
        "224.0.0.1/32",
        "192.0.0.8/32",
        "198.18.0.1/32",
        "203.0.113.1/32",
        "::1/128",
        "192.0.2.0/24",
    ),
)
def test_private_scan_scope_rejects_unsafe_or_oversized_targets(scope: str) -> None:
    with pytest.raises(ValueError):
        network_discovery.private_scan_hosts(scope)


def test_private_scan_scope_accepts_at_most_thirty_two_hosts() -> None:
    network, hosts = network_discovery.private_scan_hosts("192.0.2.0/27")

    assert str(network) == "192.0.2.0/27"
    assert len(hosts) == 30
    assert hosts[0] == "192.0.2.1"
    assert hosts[-1] == "ollama.example.internal"


def test_oversized_scope_is_rejected_before_host_enumeration(monkeypatch) -> None:
    def fail_if_enumerated(_network):
        raise AssertionError("oversized scope was enumerated")

    monkeypatch.setattr(network_discovery.ipaddress.IPv4Network, "hosts", fail_if_enumerated)

    with pytest.raises(ValueError, match="32-host safety limit"):
        network_discovery.private_scan_hosts("10.0.0.0/8")


def test_network_scan_returns_only_fixed_port_hints() -> None:
    calls: list[tuple[str, int, float]] = []

    async def probe(address: str, port: int, timeout: float) -> bool:
        calls.append((address, port, timeout))
        return address == "192.0.2.1" and port in {443, 1883}

    result = asyncio.run(
        network_discovery.scan_private_network("192.0.2.1/32", probe=probe)
    )

    assert result["status"] == "completed"
    assert result["asset_inventory_mutated"] is False
    assert result["payload_reads"] is False
    assert result["credentials_used"] is False
    assert [call[1] for call in calls] == [
        port for port, _protocol in network_discovery.PROTOCOL_PORT_HINTS
    ]
    assert result["items"] == [
        {
            "address": "192.0.2.1",
            "protocol_hints": ["https", "mqtt"],
            "open_ports": [443, 1883],
            "confidence": "port_hint",
            "evidence_kind": "tcp_connect_only",
        }
    ]


def test_network_scan_enforces_concurrency_limit() -> None:
    active = 0
    peak = 0

    async def probe(_address: str, _port: int, _timeout: float) -> bool:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return False

    result = asyncio.run(
        network_discovery.scan_private_network("10.0.0.0/29", probe=probe)
    )

    assert result["status"] == "completed"
    assert peak <= network_discovery.MAX_DISCOVERY_CONCURRENCY
    assert result["items"] == []


def test_network_scan_fails_bounded_on_total_timeout(monkeypatch) -> None:
    monkeypatch.setattr(network_discovery, "DISCOVERY_TOTAL_TIMEOUT_SECONDS", 0.01)

    async def probe(_address: str, _port: int, _timeout: float) -> bool:
        await asyncio.sleep(0.1)
        return True

    result = asyncio.run(
        network_discovery.scan_private_network("172.16.1.1/32", probe=probe)
    )

    assert result["status"] == "partial_timeout"
    assert result["items"] == []


def test_tcp_probe_treats_refusal_as_closed_but_propagates_resource_failure(
    monkeypatch,
) -> None:
    async def refused(*_args, **_kwargs):
        raise ConnectionRefusedError(errno.ECONNREFUSED, "refused")

    monkeypatch.setattr(network_discovery.asyncio, "open_connection", refused)
    assert asyncio.run(
        network_discovery.tcp_connect_hint("192.0.2.1", 80, 0.1)
    ) is False

    async def exhausted(*_args, **_kwargs):
        raise OSError(errno.EMFILE, "descriptor limit")

    monkeypatch.setattr(network_discovery.asyncio, "open_connection", exhausted)
    with pytest.raises(OSError) as error:
        asyncio.run(
            network_discovery.tcp_connect_hint("192.0.2.1", 80, 0.1)
        )
    assert error.value.errno == errno.EMFILE


def test_network_scan_cancels_remaining_probes_on_resource_failure() -> None:
    async def exhausted(_address: str, _port: int, _timeout: float) -> bool:
        raise OSError(errno.ENOMEM, "memory pressure")

    with pytest.raises(OSError) as error:
        asyncio.run(
            network_discovery.scan_private_network(
                "192.0.2.1/32",
                probe=exhausted,
            )
        )
    assert error.value.errno == errno.ENOMEM
