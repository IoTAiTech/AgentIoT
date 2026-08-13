# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.13 | Date: 2026-08-13

"""Customer-safe host architecture and hardware-technology identity."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path
from typing import Any

from .version import __version__

_SERIAL_LIKE = re.compile(
    r"(?i)\b(serial(?:_number)?|uuid|mac(?:addr)?|imei|sku)[:\s=]+\S+"
)
_CONTROL_CHARS = re.compile(r"[\x00-\x1f]+")
_X86_MACHINES = frozenset({"x86_64", "amd64", "i386", "i686", "x86", "x64"})
_ARM64_MACHINES = frozenset({"aarch64", "arm64", "armv8l", "armv8"})
_ARM32_MACHINES = frozenset({"armv7l", "armv6l", "armv7", "armv6", "arm"})


def _sanitize(value: str, *, limit: int = 160) -> str:
    cleaned = _CONTROL_CHARS.sub(" ", value or "")
    cleaned = _SERIAL_LIKE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]


def _read_text(path: Path, *, limit: int = 160) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if raw.startswith("\x00") or "\x00" in raw[:8]:
        raw = raw.replace("\x00", "")
    return _sanitize(raw, limit=limit)


def _cpuinfo_field(*names: str) -> str:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    wanted = {name.lower() for name in names}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() in wanted:
            cleaned = _sanitize(value)
            if cleaned:
                return cleaned
    return ""


def architecture_sign(machine: str | None = None) -> tuple[str, str]:
    """Return (architecture_sign, architecture_family)."""

    raw = (machine or platform.machine() or "").strip().lower()
    if raw in _X86_MACHINES:
        family = "x86_64" if raw in {"x86_64", "amd64", "x64"} else "x86"
        return "x86", family
    if raw in _ARM64_MACHINES:
        return "ARM", "arm64"
    if raw in _ARM32_MACHINES or raw.startswith("arm"):
        return "ARM", "arm"
    return "unknown", raw or "unknown"


def _board_model() -> str:
    configured = _sanitize(os.getenv("AGENTIOT_HARDWARE_MODEL", ""))
    if configured:
        return configured
    for candidate in (
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    ):
        value = _read_text(candidate)
        if value and value.lower() not in {"none", "to be filled by o.e.m.", "system product name"}:
            return value
    vendor = _read_text(Path("/sys/class/dmi/id/sys_vendor"))
    product_name = _read_text(Path("/sys/class/dmi/id/product_name"))
    board = _read_text(Path("/sys/class/dmi/id/board_name"))
    skip = {"none", "to be filled by o.e.m.", "system manufacturer", "system product name"}
    if vendor.lower() in skip:
        vendor = ""
    if product_name.lower() in skip:
        product_name = ""
    if vendor and product_name:
        return _sanitize(f"{vendor} {product_name}")
    if vendor and board:
        return _sanitize(f"{vendor} {board}")
    if product_name:
        return product_name
    return _cpuinfo_field("hardware", "model")


def hardware_technology(*, sign: str, family: str, board: str, cpu: str) -> str:
    """Human-readable technology label without serials or host names."""

    board_l = board.lower()
    if "raspberry" in board_l:
        series = "Raspberry Pi"
        if "pi 5" in board_l or "pi5" in board_l:
            series = "Raspberry Pi 5"
        elif "pi 4" in board_l or "pi4" in board_l:
            series = "Raspberry Pi 4"
        return f"ARM {series}"
    if "rock" in board_l and "pi" in board_l:
        return "ARM Rock Pi"
    if "radxa" in board_l:
        return "ARM Radxa"
    if sign == "ARM":
        if board:
            return f"ARM {board}"
        if cpu:
            return f"ARM64 {cpu}" if family == "arm64" else f"ARM {cpu}"
        return "ARM64 Linux edge" if family == "arm64" else "ARM Linux edge"
    if sign == "x86":
        if board and "linux" not in board_l:
            return f"x86 {board}"
        return "x86_64 Linux edge" if family == "x86_64" else "x86 Linux edge"
    if board:
        return board
    return "Hardware not reported"


def runtime_host_identity() -> dict[str, Any]:
    """Return cockpit-safe host identity for version and footer rendering."""

    machine = platform.machine() or "unknown"
    sign, family = architecture_sign(machine)
    board = _board_model()
    cpu = _cpuinfo_field("model name", "hardware")
    technology = hardware_technology(sign=sign, family=family, board=board, cpu=cpu)
    return {
        "version": __version__,
        "architecture": family,
        "architecture_sign": sign,
        "machine": _sanitize(machine, limit=32),
        "hardware_technology": technology,
        "board_model": board or "not_reported",
        "cpu_model": cpu or "not_reported",
        "os_name": _sanitize(platform.system() or "Linux", limit=32),
        "privacy": {
            "serial_returned": False,
            "hostname_returned": False,
            "address_returned": False,
        },
    }
