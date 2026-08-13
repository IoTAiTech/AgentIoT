# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.11 | Date: 2026-08-13

"""Bounded MQTT topic and payload conventions for lab ingestion.

Supported conventions are parsed locally. This is not a full Sparkplug host
application, Homie controller, or Matter stack. Field TLS remains a separate
owner gate. production_claim: false.
"""

from __future__ import annotations

import json
from typing import Any


MQTT_PROTOCOL_LABEL = "mqtt-5.0"
MQTT_STANDARD_FAMILIES = (
    "OASIS MQTT 5.0 JSON envelope",
    "Eclipse Sparkplug B DDATA",
    "Homie 4.0 property",
)

AGENTIOT_CONVENTION = "agentiot_telemetry"
SPARKPLUG_CONVENTION = "sparkplug_b_ddata"
HOMIE_CONVENTION = "homie_4_property"


def topic_parts(topic: str) -> list[str]:
    """Split an MQTT topic into non-empty segments."""

    return [part for part in str(topic or "").split("/") if part]


def mqtt_subscription_filters(prefix: str = "agentiot") -> list[str]:
    """Return the subscriber filters for the supported conventions."""

    clean_prefix = str(prefix or "agentiot").strip("/") or "agentiot"
    return [
        f"{clean_prefix}/+/telemetry",
        "spBv1.0/+/DDATA/+/+",
        "homie/+/+/+",
    ]


def parse_standard_mqtt_topic(
    topic: str, prefix: str = "agentiot"
) -> dict[str, str] | None:
    """Identify a supported MQTT topic convention without network I/O."""

    parts = topic_parts(topic)
    prefix_parts = topic_parts(prefix or "agentiot")
    expected_len = len(prefix_parts) + 2
    if (
        len(parts) == expected_len
        and parts[: len(prefix_parts)] == prefix_parts
        and parts[-1] == "telemetry"
        and parts[-2]
    ):
        return {
            "device_id": parts[-2],
            "convention": AGENTIOT_CONVENTION,
            "metric_hint": "",
        }
    if (
        len(parts) == 5
        and parts[0] == "spBv1.0"
        and parts[2] == "DDATA"
        and parts[4]
        and not parts[4].startswith("+")
    ):
        return {
            "device_id": parts[4],
            "convention": SPARKPLUG_CONVENTION,
            "metric_hint": "",
        }
    if (
        len(parts) == 4
        and parts[0] == "homie"
        and parts[1]
        and parts[3]
        and not any(part.startswith("$") for part in parts[1:])
    ):
        return {
            "device_id": parts[1],
            "convention": HOMIE_CONVENTION,
            "metric_hint": parts[3],
        }
    return None


def mqtt_json_depth_exceeds(value: Any, maximum_depth: int = 32) -> bool:
    """Return whether decoded MQTT JSON exceeds the bounded nesting policy."""

    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        if depth > maximum_depth:
            return True
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return False


def _metric_from_mapping(payload: dict[str, Any], metric_hint: str) -> tuple[str, Any, str | None]:
    if "metric" in payload and "value" in payload:
        metric = payload["metric"]
        if not isinstance(metric, str):
            raise ValueError("metric must be a non-empty string")
        return metric, payload["value"], payload.get("unit")
    if "name" in payload and "value" in payload:
        name = payload["name"]
        if not isinstance(name, str):
            raise ValueError("metric must be a non-empty string")
        unit = payload.get("unit")
        if unit is None:
            unit = payload.get("units")
        return name, payload["value"], unit
    metrics = payload.get("metrics")
    if isinstance(metrics, list) and metrics:
        first = metrics[0]
        if isinstance(first, dict) and "value" in first:
            name = first.get("name") or first.get("metric") or metric_hint
            unit = first.get("unit")
            if unit is None:
                unit = first.get("units")
            return str(name or ""), first["value"], unit
    if metric_hint and "value" in payload:
        return metric_hint, payload["value"], payload.get("unit")
    raise ValueError("MQTT payload is missing a metric/value pair")


def parse_standard_mqtt_payload(
    device_id: str,
    raw_payload: str,
    *,
    metric_hint: str = "",
) -> dict[str, Any]:
    """Parse a supported MQTT payload into a telemetry envelope."""

    text = str(raw_payload)
    hint = str(metric_hint or "").strip()
    try:
        payload = json.loads(text)
        if mqtt_json_depth_exceeds(payload):
            raise ValueError("MQTT JSON nesting exceeds policy")
        if isinstance(payload, (int, float)) and hint:
            metric, value, unit = hint, payload, None
        elif isinstance(payload, dict):
            metric, value, unit = _metric_from_mapping(payload, hint)
        else:
            raise ValueError("MQTT payload must be a JSON object or numeric Homie value")
    except json.JSONDecodeError:
        if not hint:
            raise ValueError("Invalid MQTT payload") from None
        metric, value, unit = hint, text.strip(), None
    if not isinstance(metric, str) or not metric.strip():
        raise ValueError("metric must be a non-empty string")
    if unit is not None and not isinstance(unit, str):
        raise ValueError("unit must be a string when provided")
    return {
        "device_id": device_id,
        "metric": metric.strip(),
        "value": float(value),
        "unit": unit,
    }


def mqtt5_protocol_version() -> int:
    """Return the gmqtt MQTT 5.0 version constant, or 5 when the library is absent."""

    try:
        from gmqtt.mqtt.constants import MQTTv50

        return int(MQTTv50)
    except Exception:
        return 5
