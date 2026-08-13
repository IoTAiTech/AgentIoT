# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

"""Protocol evidence boundaries in CMDB and topology projections."""

from agentiot.cmdb import build_cmdb, build_cmdb_graph


def test_tcp_port_observations_are_hints_not_supported_protocols() -> None:
    cmdb = build_cmdb(
        assets=[{"asset_id": "line-a", "name": "Line A"}],
        devices=[
            {
                "device_id": "sensor-a",
                "asset_id": "line-a",
                "name": "Sensor A",
                "status": "registered",
            }
        ],
        telemetry=[{"device_id": "sensor-a", "metric": "temperature_c"}],
        config_profiles=[
            {
                "device_id": "sensor-a",
                "profile_id": "sensor-a-greenhouse_temperature-profile",
                "name": "Greenhouse temperature profile",
            }
        ],
        hardware_evidence=[
            {
                "device_id": "sensor-a",
                "profile_id": "greenhouse_temperature",
                "descriptor_validated": 1,
                "protocols_json": '["mqtt"]',
                "standards_json": '["MQTT 5 telemetry"]',
                "standard_descriptors_json": "{}",
            }
        ],
        device_protocols=[
            {
                "device_id": "sensor-a",
                "protocol": "opcua",
                "port": 4840,
                "evidence_kind": "tcp_connect_only",
                "endpoint_address": "192.0.2.21",
            },
            {
                "device_id": "sensor-a",
                "protocol": "modbus_tcp",
                "port": 502,
                "evidence_kind": "tcp_connect_only",
                "status": "queued",
            },
        ],
    )

    supported = cmdb["management_summary"]["supported_protocol_families"]
    assert "mqtt" in supported
    assert "opcua" not in supported
    assert "modbus_tcp" not in supported
    assert cmdb["management_summary"]["observed_protocol_hints"] == ["opcua"]
    device = next(item for item in cmdb["items"] if item["ci_id"] == "device:sensor-a")
    assert device["protocol_hints"] == ["opcua"]
    assert "opcua" in device["connection_protocols"]

    graph = build_cmdb_graph(cmdb, protocol="opcua")
    assert all(node["node_id"] != "protocol:opcua" for node in graph["nodes"])
    hint = next(node for node in graph["nodes"] if node["node_id"] == "protocol_hint:opcua")
    assert hint["node_type"] == "protocol_hint"
    assert hint["status"] == "unverified_port_hint"
    assert any(
        edge["relation_type"] == "port_hint"
        and edge["to_ci"] == "protocol_hint:opcua"
        for edge in graph["edges"]
    )
