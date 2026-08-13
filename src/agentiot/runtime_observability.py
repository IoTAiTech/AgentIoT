# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.17 | Date: 2026-07-14

"""Read-only, customer-safe runtime platform telemetry."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TextReader = Callable[[str], str | None]
DiskUsage = Callable[[str | Path], Any]

_COMPONENT_FIELDS = frozenset(
    {
        "state",
        "configured",
        "connected",
        "persistent",
        "storage",
        "messages_accepted",
        "messages_rejected",
        "device_count",
        "telemetry_count",
        "last_observed_at",
    }
)


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _as_non_negative_int(value: str | None) -> int | None:
    try:
        parsed = int(value or "")
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _process_uptime(read_text: TextReader) -> dict[str, Any]:
    system_uptime = _read_first_float(read_text("/proc/uptime"))
    stat = read_text("/proc/self/stat")
    if system_uptime is None or not stat or ")" not in stat:
        return {"state": "unavailable"}
    fields = stat.rsplit(")", 1)[1].split()
    if len(fields) <= 19:
        return {"state": "unavailable"}
    start_ticks = _as_non_negative_int(fields[19])
    try:
        clock_ticks = int(os.sysconf("SC_CLK_TCK"))
    except (AttributeError, OSError, ValueError):
        clock_ticks = 0
    if start_ticks is None or clock_ticks <= 0:
        return {"state": "unavailable"}
    uptime_seconds = max(system_uptime - (start_ticks / clock_ticks), 0.0)
    return {"state": "available", "uptime_seconds": round(uptime_seconds, 2)}


def _read_first_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.split()[0])
    except (IndexError, ValueError):
        return None


def _load_average(
    getloadavg: Callable[[], tuple[float, float, float]],
    cpu_count: Callable[[], int | None],
) -> dict[str, Any]:
    try:
        count = cpu_count()
    except (OSError, ValueError):
        count = None
    try:
        one_minute, five_minutes, fifteen_minutes = getloadavg()
    except (OSError, ValueError):
        return {"state": "unavailable", "cpu_count": count}
    return {
        "state": "available",
        "one_minute": round(float(one_minute), 2),
        "five_minutes": round(float(five_minutes), 2),
        "fifteen_minutes": round(float(fifteen_minutes), 2),
        "cpu_count": count,
    }


def _memory(read_text: TextReader) -> dict[str, Any]:
    for current_path, limit_path in (
        ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.max"),
        (
            "/sys/fs/cgroup/memory/memory.usage_in_bytes",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        ),
    ):
        current = _as_non_negative_int(read_text(current_path))
        limit = _as_non_negative_int(read_text(limit_path))
        if current is not None and limit is not None and limit >= current:
            return {
                "state": "available",
                "source": "cgroup",
                "capacity_bytes": limit,
                "used_bytes": current,
                "available_bytes": limit - current,
            }

    values: dict[str, int] = {}
    for line in (read_text("/proc/meminfo") or "").splitlines():
        key, separator, raw_value = line.partition(":")
        if not separator:
            continue
        parsed = _as_non_negative_int(raw_value.strip().split(" ", 1)[0])
        if parsed is not None:
            values[key] = parsed * 1024
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if total is None or available is None or available > total:
        return {"state": "unavailable"}
    return {
        "state": "available",
        "source": "system_memory",
        "capacity_bytes": total,
        "used_bytes": total - available,
        "available_bytes": available,
    }


def _disk_usage(data_volume_path: str | Path, disk_usage: DiskUsage) -> dict[str, Any]:
    try:
        usage = disk_usage(data_volume_path)
        total = int(usage.total)
        used = int(usage.used)
        free = int(usage.free)
    except (OSError, TypeError, ValueError, AttributeError):
        return {"state": "unavailable"}
    if min(total, used, free) < 0:
        return {"state": "unavailable"}
    return {
        "state": "available",
        "capacity_bytes": total,
        "used_bytes": used,
        "available_bytes": free,
    }


def _network(read_text: TextReader) -> dict[str, Any]:
    received_bytes = sent_bytes = receive_errors = transmit_errors = 0
    observed = False
    for line in (read_text("/proc/net/dev") or "").splitlines():
        interface, separator, values = line.partition(":")
        if not separator or interface.strip() == "lo":
            continue
        counters = values.split()
        if len(counters) < 11:
            continue
        parsed = [_as_non_negative_int(counters[index]) for index in (0, 2, 8, 10)]
        if any(value is None for value in parsed):
            continue
        observed = True
        received_bytes += int(parsed[0])
        receive_errors += int(parsed[1])
        sent_bytes += int(parsed[2])
        transmit_errors += int(parsed[3])
    if not observed:
        return {"state": "unavailable"}
    return {
        "state": "available",
        "received_bytes": received_bytes,
        "sent_bytes": sent_bytes,
        "receive_errors": receive_errors,
        "transmit_errors": transmit_errors,
    }


def _safe_components(components: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: {key: value for key, value in component.items() if key in _COMPONENT_FIELDS}
        for name, component in components.items()
    }


def _issues(snapshot: Mapping[str, Any]) -> list[str]:
    issues = []
    for key, label in (
        ("process", "Process uptime"),
        ("load", "System load"),
        ("memory", "Memory telemetry"),
        ("disk", "Data-volume disk telemetry"),
        ("network", "Network telemetry"),
    ):
        if snapshot[key]["state"] == "unavailable":
            issues.append(f"{label} is unavailable.")
    components = snapshot["components"]
    if components.get("database", {}).get("state") == "unavailable":
        issues.append("Database availability needs review.")
    if components.get("mqtt", {}).get("state") == "not_configured":
        issues.append("MQTT is not configured.")
    if components.get("rest", {}).get("state") == "idle_no_rest_devices":
        issues.append("REST has no registered devices.")
    return issues


def collect_runtime_observability(
    *,
    data_volume_path: str | Path,
    components: Mapping[str, Mapping[str, Any]],
    observed_at: str | None = None,
    read_text: TextReader = _read_text,
    getloadavg: Callable[[], tuple[float, float, float]] = os.getloadavg,
    cpu_count: Callable[[], int | None] = os.cpu_count,
    disk_usage: DiskUsage = shutil.disk_usage,
) -> dict[str, Any]:
    """Collect a read-only telemetry snapshot without host-identifying details."""

    snapshot: dict[str, Any] = {
        "observed_at": observed_at
        or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "freshness": {"state": "fresh", "age_seconds": 0},
        "process": _process_uptime(read_text),
        "load": _load_average(getloadavg, cpu_count),
        "memory": _memory(read_text),
        "disk": _disk_usage(data_volume_path, disk_usage),
        "network": _network(read_text),
        "components": _safe_components(components),
    }
    snapshot["issues"] = _issues(snapshot)
    snapshot["next_action"] = (
        "Review unavailable or unconfigured telemetry before relying on platform status."
        if snapshot["issues"]
        else "Platform telemetry is current; continue normal monitoring."
    )
    return snapshot
