# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Optional hardware simulator plugin for lab validation environments."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from .hardware_profiles import hardware_profile_catalog


PLUGIN_ID = "hardware-simulator"
PLUGIN_ENV = "AGENTIOT_HARDWARE_SIMULATOR_PLUGIN"


SIMULATOR_CATALOG: tuple[dict[str, Any], ...] = tuple(hardware_profile_catalog())


@dataclass(frozen=True)
class SimulatorPluginState:
    """Customer-safe plugin state derived from deployment configuration."""

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
            "integration_mode": "sidecar_plugin",
            "core_embedded": False,
            "configured_by": PLUGIN_ENV,
        }


def simulator_plugin_state() -> SimulatorPluginState:
    """Return optional simulator plugin state from environment."""

    value = os.getenv(PLUGIN_ENV, "disabled").strip().lower()
    if value in {"1", "true", "on", "enabled"}:
        return SimulatorPluginState("enabled")
    if value in {"0", "false", "off", "disabled", ""}:
        return SimulatorPluginState("disabled")
    if value in {"removed", "uninstalled"}:
        return SimulatorPluginState("removed")
    return SimulatorPluginState("disabled")


def simulator_interface_contract() -> dict[str, Any]:
    """Return the public hardware data interface used by the plugin."""

    return {
        "write_path": "hardware_data_interface",
        "adapter_endpoints": [
            "/api/assets",
            "/api/devices",
            "/api/config/profiles",
            "/api/telemetry",
            "/api/adapters/mqtt/messages",
        ],
        "protocols": [
            "rest",
            "mqtt",
            "usb",
            "gpio",
            "i2c",
            "spi",
            "uart",
            "modbus-rtu",
            "matter-metadata",
        ],
        "reference_boards": ["raspberry-pi-4", "raspberry-pi-5"],
        "control_path": "operator_approved_only",
            "large_dataset_policy": "bounded_lab_validation_only",
    }


def simulator_catalog() -> list[dict[str, Any]]:
    """Return supported lab-validation simulator device profiles."""

    return [dict(item) for item in SIMULATOR_CATALOG]


def simulator_status() -> dict[str, Any]:
    """Return customer-safe plugin status and integration contract."""

    state = simulator_plugin_state()
    return {
        "status": "ok",
        "plugin": state.as_dict(),
        "interface": simulator_interface_contract(),
        "catalog_count": len(SIMULATOR_CATALOG),
        "safety": {
            "lab_validation_only": True,
            "production_run_blocked_by_default": True,
            "secrets_required": False,
            "large_datasets_created": False,
        },
    }


def _profile_map() -> dict[str, dict[str, Any]]:
    return {item["profile_id"]: item for item in SIMULATOR_CATALOG}


def build_simulator_plan(
    *,
    device_count: int,
    samples_per_device: int,
    profiles: list[str],
    asset_id: str,
) -> dict[str, Any]:
    """Build a bounded simulator plan without writing to the core store."""

    profile_map = _profile_map()
    requested = [profile for profile in profiles if profile]
    selected = [profile for profile in requested if profile in profile_map]
    ignored = [profile for profile in requested if profile not in profile_map]
    fallback_profile_applied = False
    if not selected:
        selected = [SIMULATOR_CATALOG[0]["profile_id"]]
        fallback_profile_applied = True
    simulation_id = f"hardware-sim-{int(time.time())}"
    devices: list[dict[str, Any]] = []
    profiles_to_create: list[dict[str, Any]] = []
    telemetry: list[dict[str, Any]] = []

    for index in range(1, device_count + 1):
        profile_id = selected[(index - 1) % len(selected)]
        profile = profile_map[profile_id]
        device_id = f"lab-{profile_id.replace('_', '-')}-{index}"
        devices.append(
            {
                "device_id": device_id,
                "name": f"{profile['label']} {index}",
                "adapter": "simulator",
                "asset_id": asset_id,
                "firmware_version": "lab-1.0.0",
            }
        )
        profiles_to_create.append(
            {
                "profile_id": f"{device_id}-profile",
                "name": f"{profile['label']} profile",
                "asset_id": asset_id,
                "device_id": device_id,
                "desired_firmware": "lab-1.0.0",
                "telemetry_interval_s": 30,
                "enabled": True,
            }
        )
        for sample in range(1, samples_per_device + 1):
            value = profile["normal_value"]
            if index == 1 and sample == samples_per_device:
                value = profile["alarm_value"]
            telemetry.append(
                {
                    "device_id": device_id,
                    "metric": profile["metric"],
                    "value": value,
                    "unit": profile["unit"],
                }
            )

    return {
        "simulation_id": simulation_id,
        "asset": {
            "asset_id": asset_id,
            "name": "Hardware Simulator Lab Bench",
            "location": "Lab Validation Bench",
        },
        "devices": devices,
        "config_profiles": profiles_to_create,
        "telemetry": telemetry,
        "profile_coverage": selected,
        "requested_profiles": requested,
        "ignored_profiles": ignored,
        "fallback_profile_applied": fallback_profile_applied,
    }
