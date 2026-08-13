# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.11 | Date: 2026-08-13

from fastapi.testclient import TestClient

from agentiot.app import create_app
from agentiot.mqtt_standards import (
    mqtt_subscription_filters,
    parse_standard_mqtt_payload,
    parse_standard_mqtt_topic,
)


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_topic_conventions_identify_device_and_filter_list() -> None:
    assert parse_standard_mqtt_topic("agentiot/sensor-1/telemetry") == {
        "device_id": "sensor-1",
        "convention": "agentiot_telemetry",
        "metric_hint": "",
    }
    assert parse_standard_mqtt_topic("spBv1.0/lab/DDATA/edge-a/soil-1") == {
        "device_id": "soil-1",
        "convention": "sparkplug_b_ddata",
        "metric_hint": "",
    }
    assert parse_standard_mqtt_topic("homie/pump-1/motor/temperature") == {
        "device_id": "pump-1",
        "convention": "homie_4_property",
        "metric_hint": "temperature",
    }
    assert parse_standard_mqtt_topic("homie/pump-1/$state/ready") is None
    assert mqtt_subscription_filters() == [
        "agentiot/+/telemetry",
        "spBv1.0/+/DDATA/+/+",
        "homie/+/+/+",
    ]


def test_payload_conventions_accept_json_sparkplug_and_homie() -> None:
    assert parse_standard_mqtt_payload(
        "sensor-1", '{"metric":"temperature_c","value":21.5,"unit":"C"}'
    )["value"] == 21.5
    sparkplug = parse_standard_mqtt_payload(
        "soil-1",
        '{"timestamp":1,"metrics":[{"name":"moisture","value":18.2,"units":"%"}]}',
    )
    assert sparkplug["metric"] == "moisture"
    assert sparkplug["unit"] == "%"
    homie = parse_standard_mqtt_payload("pump-1", "22.25", metric_hint="temperature")
    assert homie["metric"] == "temperature"
    assert homie["value"] == 22.25


def _register_mqtt_device(client: TestClient, device_id: str) -> None:
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "lab-1", "name": "Lab Zone"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": device_id,
            "name": device_id,
            "adapter": "mqtt",
            "asset_id": "lab-1",
        },
    )


def test_sparkplug_and_homie_topics_ingest_when_device_is_mqtt(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-std.db"))
    _register_mqtt_device(client, "soil-1")
    _register_mqtt_device(client, "pump-1")

    sparkplug = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "spBv1.0/lab/DDATA/edge-a/soil-1",
            "payload": '{"metrics":[{"name":"temperature_c","value":12.5,"units":"C"}]}',
        },
    )
    homie = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={"topic": "homie/pump-1/motor/temperature_c", "payload": "19.5"},
    )

    assert sparkplug.status_code == 201
    assert sparkplug.json()["device_id"] == "soil-1"
    assert homie.status_code == 201
    assert homie.json()["device_id"] == "pump-1"
    metrics = {item["device_id"]: item["metric"] for item in client.get("/api/telemetry").json()["items"]}
    assert metrics["soil-1"] == "temperature_c"
    assert metrics["pump-1"] == "temperature_c"


def test_discovery_mqtt_hint_promotes_adapter_that_can_ingest(tmp_path, monkeypatch) -> None:
    app = create_app(database_path=tmp_path / "disc-mqtt.db")

    async def fake_scan(cidr: str):
        return {
            "schema_version": "agentiot.network-discovery.v1",
            "scope": cidr,
            "status": "completed",
            "host_count": 1,
            "observed_host_count": 1,
            "duration_ms": 1,
            "items": [
                {
                    "address": "127.0.0.1",
                    "protocol_hints": ["mqtt"],
                    "open_ports": [1883],
                    "confidence": "port_hint",
                    "evidence_kind": "tcp_connect_only",
                }
            ],
            "asset_inventory_mutated": False,
            "payload_reads": False,
            "credentials_used": False,
        }

    app.state.network_discovery_runner = fake_scan
    client = TestClient(app)
    scan = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "127.0.0.1/32", "confirm_active": True},
    )
    assert scan.status_code == 201
    candidate = scan.json()["candidates"][0]
    approved = client.post(
        f"/api/hardware/discovery/candidates/{candidate['candidate_id']}/approve",
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": candidate["evidence_fingerprint"],
            "expected_revision": candidate["observation_revision"],
            "device_id": "broker-edge-1",
            "asset_id": "lab-mqtt-asset",
        },
    )
    assert approved.status_code == 200
    device = client.get("/api/devices/broker-edge-1", headers=OPERATOR_HEADERS)
    if device.status_code == 404:
        device = client.get("/api/devices", headers=OPERATOR_HEADERS)
        items = device.json()["items"]
        match = next(item for item in items if item["device_id"] == "broker-edge-1")
    else:
        match = device.json()
    assert match["adapter"] == "network"

    ingest = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/broker-edge-1/telemetry",
            "payload": '{"metric":"temperature_c","value":20.1,"unit":"C"}',
        },
    )
    assert ingest.status_code == 201
