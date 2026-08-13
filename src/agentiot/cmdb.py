# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

"""CMDB auto-discovery from the hardware data interface."""

from __future__ import annotations

import json
from typing import Any

from .hardware_profiles import hardware_profile_catalog


def _profiles_by_metric() -> dict[str, list[dict[str, Any]]]:
    profiles: dict[str, list[dict[str, Any]]] = {}
    for item in hardware_profile_catalog():
        profiles.setdefault(str(item["metric"]), []).append(item)
    return profiles


def _profiles_by_id() -> dict[str, dict[str, Any]]:
    return {item["profile_id"]: item for item in hardware_profile_catalog()}


def _latest_metric_by_device(telemetry: list[dict[str, Any]]) -> dict[str, str]:
    latest: dict[str, str] = {}
    for item in telemetry:
        latest[str(item.get("device_id", ""))] = str(item.get("metric", ""))
    return latest


def _normalised(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _profile_from_hardware_evidence(
    metric: str,
    config_profile: dict[str, Any],
    evidence_profile: dict[str, Any],
    profiles_by_metric: dict[str, list[dict[str, Any]]],
    profiles_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if evidence_profile:
        profile_id = str(evidence_profile.get("profile_id", ""))
        profile = profiles_by_id.get(profile_id, {})
        if profile and profile.get("metric") == metric:
            return profile
    candidates = profiles_by_metric.get(metric, [])
    if not candidates:
        return {}
    if not config_profile:
        return {}
    evidence = _normalised(
        " ".join(
            [
                str(config_profile.get("profile_id", "")),
                str(config_profile.get("name", "")),
                str(config_profile.get("desired_firmware", "")),
            ]
        )
    )
    for profile in candidates:
        accepted_needles = {
            _normalised(profile.get("profile_id")),
            _normalised(profile.get("label")),
        }
        if any(needle and needle in evidence for needle in accepted_needles):
            return profile
    return {}


def _safe_json(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value or ""))
    except json.JSONDecodeError:
        return fallback


def build_cmdb(
    *,
    assets: list[dict[str, Any]],
    devices: list[dict[str, Any]],
    telemetry: list[dict[str, Any]],
    config_profiles: list[dict[str, Any]],
    hardware_evidence: list[dict[str, Any]] | None = None,
    device_protocols: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build customer-safe CI/CMDB records from registered runtime evidence."""

    profiles_by_metric = _profiles_by_metric()
    profiles_by_id = _profiles_by_id()
    latest_metric = _latest_metric_by_device(telemetry)
    profile_by_device = {
        str(item.get("device_id", "")): item for item in config_profiles
    }
    evidence_by_device = {
        str(item.get("device_id", "")): item for item in hardware_evidence or []
    }
    approved_protocols_by_device: dict[str, list[dict[str, Any]]] = {}
    for item in device_protocols or []:
        if str(item.get("status") or "").lower() == "queued":
            continue
        device_id = str(item.get("device_id") or "")
        protocol = str(item.get("protocol") or "")
        if not device_id or not protocol:
            continue
        approved_protocols_by_device.setdefault(device_id, []).append(item)
    items: list[dict[str, Any]] = []
    relations: list[dict[str, str]] = []

    for asset in assets:
        asset_id = str(asset.get("asset_id", ""))
        items.append(
            {
                "ci_id": f"asset:{asset_id}",
                "ci_type": "asset",
                "name": asset.get("name") or asset_id,
                "asset_id": asset_id,
                "status": "active",
                "metric": "",
                "protocols": [],
                "standards": [],
                "hardware_profile": "customer_asset",
                "discovery_source": "asset_registry",
                "auto_discovered": False,
            }
        )

    for device in devices:
        device_id = str(device.get("device_id", ""))
        asset_id = str(device.get("asset_id") or "")
        metric = latest_metric.get(device_id, "")
        config_profile = profile_by_device.get(device_id, {})
        evidence_profile = evidence_by_device.get(device_id, {})
        profile = _profile_from_hardware_evidence(
            metric,
            config_profile,
            evidence_profile,
            profiles_by_metric,
            profiles_by_id,
        )
        network_protocol_rows = approved_protocols_by_device.get(device_id, [])
        protocol_hint_rows = [
            item
            for item in network_protocol_rows
            if str(item.get("evidence_kind") or "") == "tcp_connect_only"
        ]
        validated_protocol_rows = [
            item
            for item in network_protocol_rows
            if str(item.get("evidence_kind") or "") != "tcp_connect_only"
        ]
        ci_type = str(profile.get("device_kind") or "device")
        evidence_protocols = _safe_json(
            evidence_profile.get("protocols_json"), []
        )
        evidence_standards = _safe_json(
            evidence_profile.get("standards_json"), []
        )
        profile_protocols = (
            evidence_protocols
            if evidence_profile
            else list(profile.get("protocols") or [])
        )
        standards = (
            evidence_standards
            if evidence_profile
            else list(profile.get("standards") or [])
        )
        protocols = sorted(
            {
                *profile_protocols,
                *[
                    str(item.get("protocol") or "")
                    for item in validated_protocol_rows
                    if item.get("protocol")
                ],
            }
        )
        protocol_hints = sorted(
            {
                str(item.get("protocol") or "")
                for item in protocol_hint_rows
                if item.get("protocol")
            }
        )
        connection_protocols = sorted({*protocols, *protocol_hints})
        descriptor_validated = bool(
            profile and evidence_profile.get("descriptor_validated")
        )
        hardware_signature = (
            _safe_json(evidence_profile.get("standard_descriptors_json"), {})
            if profile
            else {}
        )
        hardware_profile = (
            str(evidence_profile.get("hardware_model") or "")
            if evidence_profile
            else ",".join(profile.get("boards") or [])
        )
        if not hardware_profile:
            hardware_profile = "registered_device"
        items.append(
            {
                "ci_id": f"device:{device_id}",
                "ci_type": ci_type,
                "name": device.get("name") or device_id,
                "asset_id": asset_id,
                "status": device.get("status") or "registered",
                "metric": metric,
                "firmware_version": str(device.get("firmware_version") or ""),
                "desired_firmware": str(
                    config_profile.get("desired_firmware") or ""
                ),
                "protocols": protocols,
                "protocol_hints": protocol_hints,
                "connection_protocols": connection_protocols,
                "standards": standards,
                "hardware_profile": hardware_profile,
                "hardware_signature": hardware_signature,
                "protocol_ports": {
                    str(item["protocol"]): int(item["port"])
                    for item in validated_protocol_rows
                    if item.get("protocol") and item.get("port") is not None
                },
                "protocol_hint_ports": {
                    str(item["protocol"]): int(item["port"])
                    for item in protocol_hint_rows
                    if item.get("protocol") and item.get("port") is not None
                },
                "endpoint_address": str(
                    next(
                        (
                            item.get("endpoint_address")
                            for item in network_protocol_rows
                            if item.get("endpoint_address")
                        ),
                        "",
                    )
                ),
                "standard_descriptor_validated": descriptor_validated,
                "discovery_source": (
                    "hardware_data_interface"
                    if metric and profile
                    else "network_discovery"
                    if network_protocol_rows
                    else "device_registry"
                ),
                "auto_discovered": bool(profile or network_protocol_rows),
            }
        )
        if asset_id:
            relations.append(
                {
                    "from_ci": f"asset:{asset_id}",
                    "to_ci": f"device:{device_id}",
                    "relation_type": "contains",
                }
            )
        if metric and profile:
            relations.append(
                {
                    "from_ci": f"device:{device_id}",
                    "to_ci": f"metric:{metric}",
                    "relation_type": "produces",
                }
            )
        for protocol in protocols:
            relations.append(
                {
                    "from_ci": f"device:{device_id}",
                    "to_ci": f"protocol:{protocol}",
                    "relation_type": "uses",
                }
            )
        for protocol in protocol_hints:
            relations.append(
                {
                    "from_ci": f"device:{device_id}",
                    "to_ci": f"protocol_hint:{protocol}",
                    "relation_type": "port_hint",
                }
            )

    sensor_count = sum(1 for item in items if item["ci_type"] == "sensor")
    sensor_auto_discovered = sum(
        1
        for item in items
        if item["ci_type"] == "sensor" and item["auto_discovered"]
    )
    validated_sensor_count = sum(
        1
        for item in items
        if item["ci_type"] == "sensor"
        and item.get("standard_descriptor_validated") is True
    )
    protocol_families = sorted(
        {
            str(protocol)
            for item in items
            for protocol in item.get("protocols", [])
            if protocol
        }
    )
    standard_families = sorted(
        {
            str(standard)
            for item in items
            for standard in item.get("standards", [])
            if standard
        }
    )
    observed_protocol_hints = sorted(
        {
            str(protocol)
            for item in items
            for protocol in item.get("protocol_hints", [])
            if protocol
        }
    )
    validation_coverage = (
        round((validated_sensor_count / sensor_count) * 100, 1)
        if sensor_count
        else 0.0
    )
    if sensor_count == 0:
        readiness_state = "no_sensor_evidence"
        readiness_label = "No sensor evidence is registered yet."
        next_action = "Register or approve sensor evidence before CMDB acceptance."
    elif validated_sensor_count == sensor_count:
        readiness_state = "hardware_evidence_ready"
        readiness_label = "All discovered sensors have validated hardware evidence."
        next_action = "Use the CMDB records for asset acceptance and protocol checks."
    elif sensor_auto_discovered:
        readiness_state = "partial_hardware_evidence"
        readiness_label = "Some discovered sensors still need validation evidence."
        next_action = "Complete validation for the remaining sensor records."
    else:
        readiness_state = "registry_only"
        readiness_label = "Assets and devices are registered, but sensor evidence is not validated."
        next_action = "Run sensor discovery or approve validated laboratory evidence."
    return {
        "status": "ok",
        "summary": {
            "ci_count": len(items),
            "asset_count": sum(1 for item in items if item["ci_type"] == "asset"),
            "device_count": sum(1 for item in items if item["ci_type"] != "asset"),
            "sensor_count": sensor_count,
            "sensor_auto_discovered": sensor_auto_discovered,
            "auto_discovered": sum(1 for item in items if item["auto_discovered"]),
        },
        "management_summary": {
            "asset_count": sum(1 for item in items if item["ci_type"] == "asset"),
            "device_count": sum(1 for item in items if item["ci_type"] != "asset"),
            "sensor_count": sensor_count,
            "auto_discovered_sensor_count": sensor_auto_discovered,
            "validated_sensor_count": validated_sensor_count,
            "validation_coverage_percent": validation_coverage,
            "supported_protocol_families": protocol_families,
            "observed_protocol_hints": observed_protocol_hints,
            "supported_standard_families": standard_families,
            "readiness_state": readiness_state,
            "readiness_label": readiness_label,
            "next_action": next_action,
            "evidence_sources": [
                "asset registry",
                "device registry",
                "hardware data interface",
                "telemetry ingest",
            ],
            "evidence_endpoints": [
                "/api/cmdb/configuration-items",
                "/api/hardware/discovery/candidates",
                "/api/hardware/discovery/scans",
                "/api/telemetry",
            ],
            "customer_safe": True,
        },
        "items": items,
        "relations": relations,
        "discovery_policy": {
            "basis": "hardware_profile_metric_protocol_standard",
            "source": "hardware_data_interface",
            "usb_supported": any("usb" in item["protocols"] for item in items),
            "standard_descriptor_supported": any(
                item.get("standard_descriptor_validated") for item in items
            ),
        },
    }


def build_cmdb_graph(
    cmdb: dict[str, Any],
    *,
    asset_id: str = "",
    protocol: str = "",
    ci_type: str = "",
) -> dict[str, Any]:
    """Return a filterable graph projection over approved inventory only."""

    requested_asset = asset_id.strip()
    requested_protocol = protocol.strip().lower()
    requested_type = ci_type.strip().lower()
    all_items = list(cmdb.get("items") or [])
    selected_devices = [
        item
        for item in all_items
        if item.get("ci_type") != "asset"
        and (not requested_asset or item.get("asset_id") == requested_asset)
        and (
            not requested_protocol
            or requested_protocol
            in {
                str(value).lower()
                for value in item.get("connection_protocols") or []
            }
        )
        and (
            not requested_type
            or str(item.get("ci_type") or "").lower() == requested_type
        )
    ]
    selected_asset_ids = {
        str(item.get("asset_id") or "")
        for item in selected_devices
        if item.get("asset_id")
    }
    selected_assets = [
        item
        for item in all_items
        if item.get("ci_type") == "asset"
        and (
            (requested_asset and item.get("asset_id") == requested_asset)
            or (not requested_asset and item.get("asset_id") in selected_asset_ids)
        )
    ]
    if not requested_asset and not requested_protocol and not requested_type:
        selected_assets = [item for item in all_items if item.get("ci_type") == "asset"]
    selected_items = selected_assets + selected_devices
    selected_ids = {str(item.get("ci_id") or "") for item in selected_items}
    nodes = [
        {
            "node_id": str(item.get("ci_id") or ""),
            "node_type": str(item.get("ci_type") or "device"),
            "label": str(item.get("name") or item.get("ci_id") or "Unnamed"),
            "status": str(item.get("status") or "unknown"),
            "asset_id": str(item.get("asset_id") or ""),
            "protocols": list(item.get("protocols") or []),
            "protocol_hints": list(item.get("protocol_hints") or []),
            "connection_protocols": list(item.get("connection_protocols") or []),
            "endpoint_address": str(item.get("endpoint_address") or ""),
        }
        for item in selected_items
    ]
    protocol_names = sorted(
        {
            str(value)
            for item in selected_devices
            for value in item.get("protocols") or []
            if value and (not requested_protocol or str(value).lower() == requested_protocol)
        }
    )
    protocol_hint_names = sorted(
        {
            str(value)
            for item in selected_devices
            for value in item.get("protocol_hints") or []
            if value and (not requested_protocol or str(value).lower() == requested_protocol)
        }
    )
    nodes.extend(
        {
            "node_id": f"protocol:{name}",
            "node_type": "protocol",
            "label": (
                name.upper()
                if name in {"http", "https", "mqtt", "mqtts"}
                else name
            ),
            "status": "supported",
            "asset_id": "",
            "protocols": [name],
        }
        for name in protocol_names
    )
    nodes.extend(
        {
            "node_id": f"protocol_hint:{name}",
            "node_type": "protocol_hint",
            "label": f"{name.upper()} hint",
            "status": "unverified_port_hint",
            "asset_id": "",
            "protocols": [],
            "protocol_hints": [name],
            "connection_protocols": [name],
        }
        for name in protocol_hint_names
    )
    graph_ids = (
        selected_ids
        | {f"protocol:{name}" for name in protocol_names}
        | {f"protocol_hint:{name}" for name in protocol_hint_names}
    )
    edges = [
        dict(edge)
        for edge in cmdb.get("relations") or []
        if edge.get("from_ci") in graph_ids and edge.get("to_ci") in graph_ids
    ]
    return {
        "schema_version": "agentiot.cmdb-graph.v1",
        "filters": {
            "asset_id": requested_asset or None,
            "protocol": requested_protocol or None,
            "ci_type": requested_type or None,
        },
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "asset_count": len(selected_assets),
            "device_count": len(selected_devices),
            "protocol_count": len(protocol_names) + len(protocol_hint_names),
        },
        "nodes": nodes,
        "edges": edges,
        "candidate_nodes_included": False,
    }
