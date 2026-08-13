# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Optional USB hardware descriptor discovery for lab and edge gateways."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hardware_profiles import (
    hardware_profile_catalog,
    validate_standard_descriptor_evidence,
)


PLUGIN_ID = "usb-standard-discovery"
PLUGIN_ENV = "AGENTIOT_USB_DISCOVERY_PLUGIN"
SYSFS_ROOT_ENV = "AGENTIOT_USB_SYSFS_ROOT"
DEFAULT_SYSFS_ROOT = "/sys/bus/usb/devices"
MAX_USB_DEVICES = 64
MAX_USB_TEXT = 80


@dataclass(frozen=True)
class USBDiscoveryPluginState:
    """Customer-safe USB discovery state derived from deployment configuration."""

    install_state: str

    @property
    def installed(self) -> bool:
        return self.install_state != "removed"

    @property
    def enabled(self) -> bool:
        return self.install_state == "enabled"

    def as_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": PLUGIN_ID,
            "installed": self.installed,
            "enabled": self.enabled,
            "install_state": self.install_state,
            "removable": True,
            "disableable": True,
            "integration_mode": "sidecar_lab_adapter",
            "core_embedded": False,
            "configured_by": PLUGIN_ENV,
        }


def usb_discovery_plugin_state() -> USBDiscoveryPluginState:
    """Return optional USB discovery plugin state from environment."""

    value = os.getenv(PLUGIN_ENV, "disabled").strip().lower()
    if value in {"1", "true", "on", "enabled"}:
        return USBDiscoveryPluginState("enabled")
    if value in {"removed", "uninstalled"}:
        return USBDiscoveryPluginState("removed")
    return USBDiscoveryPluginState("disabled")


def usb_discovery_status() -> dict[str, Any]:
    """Return customer-safe USB discovery status."""

    state = usb_discovery_plugin_state()
    return {
        "status": "ok",
        "plugin": state.as_dict(),
        "source": {
            "standard": "USB descriptor via Linux sysfs",
            "root": os.getenv(SYSFS_ROOT_ENV, DEFAULT_SYSFS_ROOT),
            "evidence_fields": [
                "idVendor",
                "idProduct",
                "bDeviceClass",
                "bInterfaceClass",
                "driver",
                "manufacturer",
                "product",
            ],
            "raw_serial_storage": False,
            "registers_directly": False,
        },
        "interface": {
            "status_endpoint": "/api/hardware/discovery/usb/status",
            "preview_endpoint": "/api/hardware/discovery/usb/sysfs",
            "registration_endpoint": "/api/hardware/discovery/profiles",
            "cmdb_target": "/api/cmdb/configuration-items",
        },
    }


def _safe_text(value: str) -> str:
    return value.strip()[:MAX_USB_TEXT]


def _read_text(path: Path) -> str:
    try:
        return _safe_text(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return ""


def _driver_name(path: Path) -> str:
    try:
        target = path.resolve()
    except OSError:
        return ""
    return _safe_text(target.name)


def _usb_interface_rows(device_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for child in sorted(device_path.iterdir()):
        if not child.is_dir():
            continue
        interface_class = _read_text(child / "bInterfaceClass")
        if not interface_class:
            continue
        driver = _driver_name(child / "driver") if (child / "driver").exists() else ""
        rows.append(
            {
                "interface_class": interface_class,
                "driver": driver,
            }
        )
    return rows[:8]


def _usb_descriptor_from_sysfs(device_path: Path) -> dict[str, Any]:
    vendor_id = _read_text(device_path / "idVendor").lower()
    product_id = _read_text(device_path / "idProduct").lower()
    device_class = _read_text(device_path / "bDeviceClass")
    interfaces = _usb_interface_rows(device_path)
    if device_class in {"", "00"} and interfaces:
        device_class = interfaces[0]["interface_class"]
    drivers = sorted({row["driver"] for row in interfaces if row["driver"]})
    descriptor: dict[str, Any] = {
        "device_class": device_class,
        "manufacturer": _read_text(device_path / "manufacturer"),
        "product": _read_text(device_path / "product"),
        "vendor_id": vendor_id,
        "product_id": product_id,
        "standard": "USB sysfs descriptor",
        "interfaces": drivers,
        "interface_classes": [
            row["interface_class"] for row in interfaces if row["interface_class"]
        ],
    }
    if drivers:
        descriptor["driver"] = drivers[0]
    return {key: value for key, value in descriptor.items() if value}


def _profile_matches_usb_descriptor(usb_descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for profile in hardware_profile_catalog():
        if "usb" not in profile.get("protocols", []):
            continue
        try:
            validated = validate_standard_descriptor_evidence(
                profile,
                {"usb"},
                {"usb": usb_descriptor},
            )
        except ValueError:
            continue
        matches.append(
            {
                "profile_id": profile["profile_id"],
                "label": profile["label"],
                "metric": profile["metric"],
                "unit": profile["unit"],
                "normal_value": profile["normal_value"],
                "protocols": profile["protocols"],
                "standards": profile["standards"],
                "validated_standard_descriptors": validated,
            }
        )
    return matches


def read_usb_sysfs_descriptors(
    *, root: str | Path | None = None, limit: int = MAX_USB_DEVICES
) -> list[dict[str, Any]]:
    """Read sanitized USB descriptors from Linux sysfs."""

    sysfs_root = Path(root or os.getenv(SYSFS_ROOT_ENV, DEFAULT_SYSFS_ROOT))
    if not sysfs_root.exists() or not sysfs_root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for device_path in sorted(sysfs_root.iterdir()):
        if len(items) >= max(1, min(limit, MAX_USB_DEVICES)):
            break
        if not device_path.is_dir() or not (device_path / "idVendor").exists():
            continue
        usb_descriptor = _usb_descriptor_from_sysfs(device_path)
        if not usb_descriptor.get("vendor_id") or not usb_descriptor.get("product_id"):
            continue
        serial_present = bool(_read_text(device_path / "serial"))
        matches = _profile_matches_usb_descriptor(usb_descriptor)
        items.append(
            {
                "source": "linux_sysfs_usb",
                "device_key": device_path.name[:40],
                "standard_descriptors": {"usb": usb_descriptor},
                "serial_present": serial_present,
                "serial_redacted": serial_present,
                "matches": matches,
            }
        )
    return items


def build_usb_discovery_preview(
    *,
    asset_id: str,
    hardware_model: str,
    root: str | Path | None = None,
    limit: int = MAX_USB_DEVICES,
) -> dict[str, Any]:
    """Build safe registration previews for USB descriptors without writing state."""

    items = read_usb_sysfs_descriptors(root=root, limit=limit)
    previews: list[dict[str, Any]] = []
    for item in items:
        if not item["matches"]:
            continue
        profile = item["matches"][0]
        usb = item["standard_descriptors"]["usb"]
        signature = hashlib.sha256(
            "|".join(
                [
                    usb.get("vendor_id", ""),
                    usb.get("product_id", ""),
                    usb.get("product", ""),
                    item.get("device_key", ""),
                ]
            ).encode("utf-8")
        ).hexdigest()[:10]
        previews.append(
            {
                "device_id": f"usb-{usb.get('vendor_id')}-{usb.get('product_id')}-{signature}",
                "profile_id": profile["profile_id"],
                "name": usb.get("product") or profile["label"],
                "asset_id": asset_id,
                "asset_name": asset_id,
                "adapter": "usb",
                "protocols": ["usb"],
                "standards": profile["standards"],
                "hardware_model": hardware_model,
                "metric": profile["metric"],
                "value": profile["normal_value"],
                "unit": profile["unit"],
                "standard_descriptors": item["standard_descriptors"],
            }
        )
    return {
        "status": "ok",
        "plugin": usb_discovery_status()["plugin"],
        "source": usb_discovery_status()["source"],
        "items": items,
        "registration_previews": previews,
        "summary": {
            "usb_devices_seen": len(items),
            "matched_profiles": sum(1 for item in items if item["matches"]),
            "registration_previews": len(previews),
            "raw_serial_storage": False,
        },
    }
