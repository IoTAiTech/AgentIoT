# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.15 | Date: 2026-08-13

"""Supported hardware profile evidence for discovery and lab simulation."""

from __future__ import annotations

from typing import Any

USB_CLASS_ALIASES = {
    "0x02": "cdc-acm",
    "02": "cdc-acm",
    "cdc": "cdc-acm",
    "cdcacm": "cdc-acm",
    "0x03": "hid",
    "03": "hid",
    "usbhid": "hid",
    "0x0a": "cdc-data",
    "0a": "cdc-data",
    "0xff": "vendor-specific",
    "ff": "vendor-specific",
    "vendorspecific": "vendor-specific",
}

USB_DESCRIPTOR_TEXT_KEYS = (
    "device_class",
    "driver",
    "manufacturer",
    "product",
    "standard",
)
USB_DESCRIPTOR_LIST_KEYS = ("interfaces", "interface_classes")
USB_DESCRIPTOR_ID_KEYS = ("vendor_id", "product_id")
USB_DESCRIPTOR_SECRET_KEYS = ("serial", "serial_number", "serialNumber")
MAX_DESCRIPTOR_TEXT = 80
MAX_DESCRIPTOR_LIST_ITEMS = 8


SUPPORTED_HARDWARE_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "linux_onboard_thermal",
        "label": "Linux onboard thermal sensor",
        "device_kind": "sensor",
        "protocols": ["rest", "linux-sysfs"],
        "standards": ["Linux thermal sysfs"],
        "boards": [
            "radxa-rock-pi-4b-plus",
            "raspberry-pi-4",
            "raspberry-pi-5",
            "generic-linux-arm64",
            "x86_64-edge",
        ],
        "metric": "temperature_c",
        "unit": "C",
        "normal_value": 50.0,
        "alarm_value": 85.0,
        "control_supported": False,
        "standard_descriptor_rules": {},
    },
    {
        "profile_id": "greenhouse_temperature",
        "label": "Greenhouse temperature sensor",
        "device_kind": "sensor",
        "protocols": ["rest", "mqtt", "usb", "i2c", "gpio"],
        "standards": ["Matter Temperature Sensor", "MQTT 5 telemetry"],
        "boards": [
            "radxa-rock-pi-4b-plus",
            "raspberry-pi-4",
            "raspberry-pi-5",
            "x86_64-edge",
        ],
        "metric": "temperature_c",
        "unit": "C",
        "normal_value": 24.0,
        "alarm_value": 88.0,
        "control_supported": False,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["hid", "cdc-acm", "vendor-specific"],
                "tokens": ["temperature", "thermometer", "temp", "i2c", "sensor"],
            }
        },
    },
    {
        "profile_id": "oxygen_concentration",
        "label": "Oxygen concentration sensor",
        "device_kind": "sensor",
        "protocols": ["rest", "mqtt", "usb", "uart", "i2c", "modbus-rtu"],
        "standards": ["industrial lab profile", "MQTT 5 telemetry"],
        "boards": ["raspberry-pi-4", "raspberry-pi-5", "x86_64-edge"],
        "metric": "oxygen_pct",
        "unit": "%",
        "normal_value": 20.9,
        "alarm_value": 18.0,
        "control_supported": False,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["cdc-acm", "cdc-data", "vendor-specific"],
                "tokens": ["oxygen", "o2", "gas", "uart", "sensor"],
            }
        },
    },
    {
        "profile_id": "ambient_light",
        "label": "Ambient light sensor",
        "device_kind": "sensor",
        "protocols": ["rest", "mqtt", "usb", "i2c"],
        "standards": ["Matter Light Sensor", "MQTT 5 telemetry"],
        "boards": ["raspberry-pi-4", "raspberry-pi-5", "x86_64-edge"],
        "metric": "illuminance_lux",
        "unit": "lux",
        "normal_value": 420.0,
        "alarm_value": 40.0,
        "control_supported": False,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["hid", "cdc-acm", "vendor-specific"],
                "tokens": ["light", "lux", "illuminance", "sensor"],
            }
        },
    },
    {
        "profile_id": "motion_occupancy",
        "label": "Motion and occupancy sensor",
        "device_kind": "sensor",
        "protocols": ["rest", "mqtt", "usb", "gpio"],
        "standards": ["Matter Occupancy Sensor", "MQTT 5 telemetry"],
        "boards": ["raspberry-pi-4", "raspberry-pi-5", "x86_64-edge"],
        "metric": "occupancy_state",
        "unit": "state",
        "normal_value": 0.0,
        "alarm_value": 1.0,
        "control_supported": False,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["hid", "vendor-specific"],
                "tokens": ["motion", "occupancy", "pir", "sensor"],
            }
        },
    },
    {
        "profile_id": "soil_moisture",
        "label": "Soil moisture probe",
        "device_kind": "sensor",
        "protocols": ["rest", "mqtt", "usb", "i2c", "gpio"],
        "standards": ["Matter Soil Sensor", "MQTT 5 telemetry"],
        "boards": ["raspberry-pi-4", "raspberry-pi-5", "x86_64-edge"],
        "metric": "soil_moisture_pct",
        "unit": "%",
        "normal_value": 42.0,
        "alarm_value": 18.0,
        "control_supported": False,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["hid", "cdc-acm", "vendor-specific"],
                "tokens": ["soil", "moisture", "humidity", "sensor"],
            }
        },
    },
    {
        "profile_id": "energy_meter",
        "label": "Energy meter",
        "device_kind": "meter",
        "protocols": ["rest", "mqtt", "usb", "modbus-rtu"],
        "standards": ["MQTT 5 telemetry"],
        "boards": ["raspberry-pi-4", "raspberry-pi-5"],
        "metric": "power_kw",
        "unit": "kW",
        "normal_value": 3.2,
        "alarm_value": 7.8,
        "control_supported": False,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["cdc-acm", "cdc-data", "vendor-specific"],
                "tokens": ["energy", "meter", "power", "modbus"],
            }
        },
    },
    {
        "profile_id": "hvac_controller",
        "label": "HVAC controller",
        "device_kind": "controller",
        "protocols": ["rest", "mqtt", "usb", "gpio"],
        "standards": ["Matter HVAC", "MQTT 5 telemetry"],
        "boards": ["raspberry-pi-4", "raspberry-pi-5"],
        "metric": "fan_speed_pct",
        "unit": "%",
        "normal_value": 35.0,
        "alarm_value": 95.0,
        "control_supported": True,
        "standard_descriptor_rules": {
            "usb": {
                "classes": ["hid", "cdc-acm", "vendor-specific"],
                "tokens": ["hvac", "fan", "controller", "relay"],
            }
        },
    },
)


def hardware_profile_catalog() -> list[dict[str, Any]]:
    """Return customer-safe hardware discovery profiles."""

    return [dict(item) for item in SUPPORTED_HARDWARE_PROFILES]


def hardware_profile_by_id(profile_id: str) -> dict[str, Any]:
    """Return one supported profile by id, or an empty mapping."""

    return next(
        (
            dict(item)
            for item in SUPPORTED_HARDWARE_PROFILES
            if item["profile_id"] == profile_id
        ),
        {},
    )


def normalise_evidence_token(value: Any) -> str:
    """Normalize protocol and standard labels for evidence matching."""

    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _limited_text(value: Any) -> str:
    return str(value or "").strip()[:MAX_DESCRIPTOR_TEXT]


def _normalise_usb_class(value: Any) -> str:
    token = str(value or "").strip().lower().replace("_", "-")
    compact = normalise_evidence_token(token)
    return USB_CLASS_ALIASES.get(token) or USB_CLASS_ALIASES.get(compact) or token


def _safe_usb_identifier(value: Any) -> str:
    cleaned = str(value or "").strip().lower()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if 1 <= len(cleaned) <= 4 and all(ch in "0123456789abcdef" for ch in cleaned):
        return cleaned.zfill(4)
    return ""


def _safe_usb_descriptor(raw: dict[str, Any]) -> dict[str, Any]:
    descriptor: dict[str, Any] = {}
    for key in USB_DESCRIPTOR_TEXT_KEYS:
        value = _limited_text(raw.get(key))
        if value:
            descriptor[key] = value
    for key in USB_DESCRIPTOR_ID_KEYS:
        value = _safe_usb_identifier(raw.get(key))
        if value:
            descriptor[key] = value
    for key in USB_DESCRIPTOR_LIST_KEYS:
        values = raw.get(key)
        if isinstance(values, list):
            descriptor[key] = [
                _limited_text(item) for item in values[:MAX_DESCRIPTOR_LIST_ITEMS]
            ]
    if any(raw.get(key) for key in USB_DESCRIPTOR_SECRET_KEYS):
        descriptor["serial_redacted"] = True
    descriptor["device_class"] = _normalise_usb_class(
        descriptor.get("device_class") or raw.get("interface_class")
    )
    return descriptor


def _descriptor_text(descriptor: dict[str, Any]) -> str:
    values: list[str] = []
    for key in USB_DESCRIPTOR_TEXT_KEYS + USB_DESCRIPTOR_ID_KEYS:
        values.append(str(descriptor.get(key, "")))
    for key in USB_DESCRIPTOR_LIST_KEYS:
        values.extend(str(item) for item in descriptor.get(key, []))
    return normalise_evidence_token(" ".join(values))


def validate_standard_descriptor_evidence(
    profile: dict[str, Any],
    protocols: set[str],
    standard_descriptors: dict[str, Any],
) -> dict[str, Any]:
    """Validate optional standard descriptors such as USB class evidence."""

    if not standard_descriptors:
        return {}
    validated: dict[str, Any] = {}
    if "usb" in standard_descriptors:
        if "usb" not in protocols:
            raise ValueError("USB descriptor requires USB protocol evidence")
        raw_usb = standard_descriptors.get("usb")
        if not isinstance(raw_usb, dict):
            raise ValueError("USB descriptor must be an object")
        usb = _safe_usb_descriptor(raw_usb)
        rules = (profile.get("standard_descriptor_rules") or {}).get("usb") or {}
        accepted_classes = set(rules.get("classes") or [])
        accepted_tokens = {
            normalise_evidence_token(item) for item in rules.get("tokens") or []
        }
        descriptor_class = _normalise_usb_class(usb.get("device_class"))
        class_ok = descriptor_class in accepted_classes
        descriptor_text = _descriptor_text(usb)
        token_ok = any(token and token in descriptor_text for token in accepted_tokens)
        if not class_ok or not token_ok:
            raise ValueError("USB descriptor does not match hardware profile")
        usb["device_class"] = descriptor_class
        usb["validation_rule"] = "class_and_descriptor_token"
        validated["usb"] = usb
    unknown = set(standard_descriptors) - {"usb"}
    if unknown:
        raise ValueError("Unsupported standard descriptor evidence")
    return validated


def validate_hardware_profile_evidence(
    *,
    profile_id: str,
    metric: str,
    protocols: list[str],
    standards: list[str],
    hardware_model: str,
    standard_descriptors: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate discovered hardware evidence against the supported profile catalog."""

    profile = hardware_profile_by_id(profile_id)
    if not profile:
        raise ValueError("Unsupported hardware profile")
    if metric != profile["metric"]:
        raise ValueError("Metric does not match hardware profile")
    requested_protocols = {
        str(item).strip().lower() for item in protocols if str(item).strip()
    }
    supported_protocols = set(profile["protocols"])
    if not requested_protocols or not requested_protocols.intersection(supported_protocols):
        raise ValueError("Matching protocol evidence required")
    requested_standards = {
        normalise_evidence_token(item) for item in standards if str(item).strip()
    }
    supported_standards = {
        normalise_evidence_token(item) for item in profile["standards"]
    }
    if not requested_standards or not requested_standards.intersection(supported_standards):
        raise ValueError("Matching standard evidence required")
    if hardware_model and hardware_model not in set(profile["boards"]):
        raise ValueError("Hardware model not supported by profile")
    descriptor_evidence = validate_standard_descriptor_evidence(
        profile, requested_protocols, standard_descriptors or {}
    )
    profile["validated_protocols"] = sorted(requested_protocols.intersection(supported_protocols))
    profile["validated_standards"] = sorted(
        item
        for item in profile["standards"]
        if normalise_evidence_token(item) in requested_standards
    )
    profile["validated_standard_descriptors"] = descriptor_evidence
    profile["descriptor_validated"] = bool(descriptor_evidence)
    return profile
