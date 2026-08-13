# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.1 | Date: 2026-08-11

"""Bounded private-network service hints for operator-approved asset import."""

from __future__ import annotations

import asyncio
import errno
import ipaddress
import time
from collections.abc import Awaitable, Callable
from typing import Any


MAX_DISCOVERY_HOSTS = 32
MAX_DISCOVERY_CONCURRENCY = 8
DISCOVERY_CONNECT_TIMEOUT_SECONDS = 0.25
DISCOVERY_TOTAL_TIMEOUT_SECONDS = 5.0
DISCOVERY_CANDIDATE_TTL_HOURS = 24
DISCOVERY_ACTOR_COOLDOWN_SECONDS = 300

PROTOCOL_PORT_HINTS: tuple[tuple[int, str], ...] = (
    (80, "http"),
    (443, "https"),
    (1883, "mqtt"),
    (8883, "mqtts"),
    (4840, "opcua"),
    (502, "modbus_tcp"),
)

RFC1918_NETWORKS: tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)

Probe = Callable[[str, int, float], Awaitable[bool]]

EXPECTED_CONNECT_ERRNOS = {
    getattr(errno, name)
    for name in (
        "ECONNABORTED",
        "ECONNREFUSED",
        "ECONNRESET",
        "EHOSTDOWN",
        "EHOSTUNREACH",
        "ENETDOWN",
        "ENETUNREACH",
        "ETIMEDOUT",
    )
    if hasattr(errno, name)
}


def private_scan_hosts(cidr: str) -> tuple[ipaddress.IPv4Network, list[str]]:
    """Return a bounded private IPv4 scope or reject it before any I/O."""

    try:
        network = ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError as error:
        raise ValueError("Discovery scope must be a valid IPv4 CIDR") from error
    if not isinstance(network, ipaddress.IPv4Network):
        raise ValueError("Discovery scope must use IPv4")
    if not any(network.subnet_of(allowed) for allowed in RFC1918_NETWORKS):
        raise ValueError("Discovery scope must be inside an RFC1918 IPv4 network")
    usable_host_count = network.num_addresses
    if network.prefixlen < 31:
        usable_host_count -= 2
    if usable_host_count > MAX_DISCOVERY_HOSTS:
        raise ValueError(
            f"Discovery scope exceeds the {MAX_DISCOVERY_HOSTS}-host safety limit"
        )
    hosts = [str(address) for address in network.hosts()]
    if not hosts and network.prefixlen == 32:
        hosts = [str(network.network_address)]
    if not hosts:
        raise ValueError("Discovery scope contains no usable hosts")
    return network, hosts


async def tcp_connect_hint(address: str, port: int, timeout: float) -> bool:
    """Check one TCP port without reading a banner or sending protocol data."""

    writer: asyncio.StreamWriter | None = None
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(address, port),
            timeout=timeout,
        )
        return True
    except TimeoutError:
        return False
    except OSError as error:
        if error.errno in EXPECTED_CONNECT_ERRNOS:
            return False
        raise
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


async def scan_private_network(
    cidr: str,
    *,
    probe: Probe = tcp_connect_hint,
) -> dict[str, Any]:
    """Return sanitized port hints for one bounded, explicitly selected scope."""

    network, hosts = private_scan_hosts(cidr)
    semaphore = asyncio.Semaphore(MAX_DISCOVERY_CONCURRENCY)
    observations: dict[str, list[tuple[int, str]]] = {host: [] for host in hosts}
    started = time.monotonic()

    async def check(address: str, port: int, protocol: str) -> None:
        async with semaphore:
            if await probe(address, port, DISCOVERY_CONNECT_TIMEOUT_SECONDS):
                observations[address].append((port, protocol))

    tasks = [
        asyncio.create_task(check(address, port, protocol))
        for address in hosts
        for port, protocol in PROTOCOL_PORT_HINTS
    ]
    timed_out = False
    try:
        await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=DISCOVERY_TOTAL_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        timed_out = True
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    items = []
    for address in hosts:
        hints = sorted(observations[address])
        if not hints:
            continue
        items.append(
            {
                "address": address,
                "protocol_hints": [protocol for _port, protocol in hints],
                "open_ports": [port for port, _protocol in hints],
                "confidence": "port_hint",
                "evidence_kind": "tcp_connect_only",
            }
        )
    return {
        "schema_version": "agentiot.network-discovery.v1",
        "scope": str(network),
        "status": "partial_timeout" if timed_out else "completed",
        "host_count": len(hosts),
        "observed_host_count": len(items),
        "duration_ms": max(0, round((time.monotonic() - started) * 1000)),
        "limits": {
            "max_hosts": MAX_DISCOVERY_HOSTS,
            "concurrency": MAX_DISCOVERY_CONCURRENCY,
            "connect_timeout_ms": round(DISCOVERY_CONNECT_TIMEOUT_SECONDS * 1000),
            "total_timeout_ms": round(DISCOVERY_TOTAL_TIMEOUT_SECONDS * 1000),
            "ports": [port for port, _protocol in PROTOCOL_PORT_HINTS],
        },
        "items": items,
        "asset_inventory_mutated": False,
        "payload_reads": False,
        "credentials_used": False,
    }
