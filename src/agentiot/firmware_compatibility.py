# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.15 | Date: 2026-08-13

"""Firmware and edge-runtime compatibility helpers."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel


SUPPORTED_HARDWARE_MODELS = {
    "raspberry-pi-4": {
        "minimum_firmware": "1.0.0",
        "status": "validation_required",
        "evidence_state": "verification_required",
        "evidence_scope": "arm64_image_and_physical_device",
        "notes": "ARM64 image and physical-device validation are required before pilot use.",
    },
    "raspberry-pi-5": {
        "minimum_firmware": "1.0.0",
        "status": "validation_required",
        "evidence_state": "verification_required",
        "evidence_scope": "arm64_image_and_physical_device",
        "notes": "ARM64 image and physical-device validation are required before pilot use.",
    },
    "x86_64-edge": {
        "minimum_firmware": "1.0.0",
        "status": "supported",
        "evidence_state": "runtime_smoke_validated",
        "evidence_scope": "x86_64_runtime_smoke",
        "notes": "Docker smoke validation completed for the x86_64 edge runtime.",
    },
    "generic-linux-arm64": {
        "minimum_firmware": "1.1.0",
        "status": "review_required",
        "evidence_state": "verification_required",
        "evidence_scope": "hardware_and_driver_review",
        "notes": "Compatible after customer hardware and driver evidence is reviewed.",
    },
    "radxa-rock-pi-4b-plus": {
        "minimum_firmware": "1.0.0",
        "status": "supported",
        "evidence_state": "physical_device_validated",
        "evidence_scope": "arm64_image_and_physical_device",
        "notes": "Physical Series-B host is a Radxa ROCK Pi 4B+ (RK3399). This is not a Raspberry Pi 4/5.",
    },
}
HARDWARE_MODEL_ALIASES = {
    "raspberry pi 4": "raspberry-pi-4",
    "raspberry pi 4 arm64": "raspberry-pi-4",
    "rpi 4": "raspberry-pi-4",
    "rpi4": "raspberry-pi-4",
    "raspberry pi 5": "raspberry-pi-5",
    "raspberry pi 5 arm64": "raspberry-pi-5",
    "rpi 5": "raspberry-pi-5",
    "rpi5": "raspberry-pi-5",
    "x86 64 edge": "x86_64-edge",
    "x86 edge": "x86_64-edge",
    "generic linux arm64": "generic-linux-arm64",
    "radxa rock pi 4b+": "radxa-rock-pi-4b-plus",
    "radxa rock pi 4b": "radxa-rock-pi-4b-plus",
    "radxa rock pi 4b plus": "radxa-rock-pi-4b-plus",
    "rock pi 4b+": "radxa-rock-pi-4b-plus",
    "rock pi 4b": "radxa-rock-pi-4b-plus",
}
SUPPORTED_EDGE_RUNTIMES = {"docker-edge", "systemd-edge"}
VALIDATED_EVIDENCE_STATES = {"runtime_smoke_validated", "physical_device_validated"}


class FirmwareCompatibilityRequest(BaseModel):
    """Read-only firmware compatibility check input."""

    hardware_model: str
    firmware_version: str
    target_runtime: str = "docker-edge"
    device_id: str | None = None


class FirmwareCompatibilityResponse(BaseModel):
    """Customer-safe firmware compatibility check output."""

    status: str
    compatible: bool
    risk_level: str
    hardware_model: str
    canonical_hardware_model: str
    firmware_version: str
    target_runtime: str
    evidence_state: str
    evidence_scope: str
    checks: list[dict[str, str]]
    recommendations: list[str]


def parse_semver(value: str) -> tuple[int, int, int] | None:
    """Parse a small semantic version string without external dependencies."""

    parts = value.strip().split(".")
    if len(parts) != 3:
        return None
    try:
        parsed = tuple(int(part) for part in parts)
    except ValueError:
        return None
    if any(part < 0 for part in parsed):
        return None
    return parsed  # type: ignore[return-value]


def firmware_drift_result(
    *,
    device_id: str,
    asset_id: str | None,
    profile_id: str | None,
    current_firmware: str | None,
    desired_firmware: str | None,
) -> dict[str, str]:
    """Compare registered and desired firmware without changing device state."""

    current = str(current_firmware or "").strip()
    desired = str(desired_firmware or "").strip()
    if not profile_id or not desired:
        status = "unmanaged"
        action = "Assign an enabled configuration profile."
    else:
        current_version = parse_semver(current)
        desired_version = parse_semver(desired)
        if current_version is None or desired_version is None:
            status = "unknown"
            action = "Record valid semantic versions for current and desired firmware."
        elif current_version == desired_version:
            status = "aligned"
            action = "No firmware action required."
        elif current_version < desired_version:
            status = "upgrade_required"
            action = "Plan an approved firmware update before field rollout."
        else:
            status = "ahead_of_profile"
            action = "Review the profile target before rollback or acceptance."
    return {
        "device_id": device_id,
        "asset_id": str(asset_id or ""),
        "profile_id": str(profile_id or ""),
        "current_firmware": current,
        "desired_firmware": desired,
        "status": status,
        "action": action,
    }


def normalize_hardware_model(value: str) -> str:
    """Map human-readable pilot hardware labels to canonical catalog ids."""

    normalized = re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()
    if value in SUPPORTED_HARDWARE_MODELS:
        return value
    return HARDWARE_MODEL_ALIASES.get(normalized, value.strip())


def firmware_compatibility_catalog() -> list[dict[str, Any]]:
    """Return the supported hardware and runtime catalog for operators."""

    return [
        {
            "hardware_model": model,
            "minimum_firmware": details["minimum_firmware"],
            "status": details["status"],
            "evidence_state": details["evidence_state"],
            "evidence_scope": details["evidence_scope"],
            "supported_runtimes": ", ".join(sorted(SUPPORTED_EDGE_RUNTIMES)),
            "notes": details["notes"],
        }
        for model, details in SUPPORTED_HARDWARE_MODELS.items()
    ]


def firmware_compatibility_result(
    *,
    hardware_model: str,
    firmware_version: str,
    target_runtime: str,
) -> dict[str, Any]:
    """Evaluate firmware compatibility without mutating runtime records."""

    checks: list[dict[str, str]] = []
    recommendations: list[str] = []
    canonical_hardware_model = normalize_hardware_model(hardware_model)
    hardware = SUPPORTED_HARDWARE_MODELS.get(canonical_hardware_model)
    firmware = parse_semver(firmware_version)

    evidence_state = str(hardware["evidence_state"]) if hardware else "unknown"
    evidence_scope = str(hardware["evidence_scope"]) if hardware else "unknown"
    hardware_evidence_validated = evidence_state in VALIDATED_EVIDENCE_STATES
    if hardware:
        checks.append(
            {
                "check": "hardware_model",
                "status": hardware["status"],
                "evidence": canonical_hardware_model,
            }
        )
        if hardware["status"] != "supported":
            recommendations.append(
                "Review hardware driver and deployment evidence before pilot use."
            )
    else:
        checks.append(
            {
                "check": "hardware_model",
                "status": "unsupported",
                "evidence": hardware_model,
            }
        )
        recommendations.append("Select a supported pilot hardware model.")

    if target_runtime in SUPPORTED_EDGE_RUNTIMES:
        checks.append(
            {
                "check": "target_runtime",
                "status": "supported",
                "evidence": target_runtime,
            }
        )
    else:
        checks.append(
            {
                "check": "target_runtime",
                "status": "unsupported",
                "evidence": target_runtime,
            }
        )
        recommendations.append("Use docker-edge or systemd-edge for Phase 2.")

    if not firmware:
        checks.append(
            {
                "check": "firmware_version",
                "status": "invalid",
                "evidence": firmware_version,
            }
        )
        recommendations.append("Use semantic version format X.Y.Z.")
    elif hardware:
        minimum = parse_semver(str(hardware["minimum_firmware"]))
        firmware_ok = bool(minimum and firmware >= minimum)
        checks.append(
            {
                "check": "firmware_minimum",
                "status": "passed" if firmware_ok else "review_required",
                "evidence": f"{firmware_version} >= {hardware['minimum_firmware']}",
            }
        )
        if not firmware_ok:
            recommendations.append(
                "Update firmware or record a customer-approved compatibility exception."
            )

    # Compatibility requires validated hardware evidence.
    if hardware and not hardware_evidence_validated:
        if canonical_hardware_model in {"raspberry-pi-4", "raspberry-pi-5"}:
            checks.append(
                {
                    "check": "arm64_runtime_evidence",
                    "status": "validation_required",
                    "evidence": "ARM64 image and physical-device validation are required.",
                }
            )
            recommendations.extend(
                [
                    "Build and verify an ARM64 image before pilot rollout.",
                    "Validate firmware and runtime on the physical target device.",
                ]
            )

    compatible = (
        bool(hardware)
        and hardware_evidence_validated
        and firmware is not None
        and target_runtime in SUPPORTED_EDGE_RUNTIMES
        and checks[-1]["status"] == "passed"
        and hardware["status"] == "supported"
    )
    risk_level = "low" if compatible else "review_required"
    if not hardware or target_runtime not in SUPPORTED_EDGE_RUNTIMES:
        risk_level = "high"
    if not recommendations:
        recommendations.append(
            "Proceed with bounded pilot onboarding and keep firmware evidence in the release record."
        )
    return {
        "status": "compatible" if compatible else "requires_review",
        "compatible": compatible,
        "risk_level": risk_level,
        "hardware_model": hardware_model,
        "canonical_hardware_model": canonical_hardware_model,
        "firmware_version": firmware_version,
        "target_runtime": target_runtime,
        "evidence_state": evidence_state,
        "evidence_scope": evidence_scope,
        "checks": checks,
        "recommendations": recommendations,
    }
