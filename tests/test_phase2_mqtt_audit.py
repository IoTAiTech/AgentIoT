# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-22

import sys
from types import ModuleType

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from agentiot.app import MQTT_PAYLOAD_MAX_BYTES, MQTT_TOPIC_MAX_BYTES, create_app
from conftest import configure_offhost_restore_receipt


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def install_mock_gmqtt(monkeypatch, connect_error: Exception | None = None):
    """Install a lifecycle-recording gmqtt substitute without network access."""

    class MockMQTTClient:
        instances: list["MockMQTTClient"] = []

        def __init__(self, client_id: str) -> None:
            self.client_id = client_id
            self.auth_credentials: tuple[str | None, str | None] | None = None
            self.config: dict[str, int] | None = None
            self.connect_args: tuple[str, int, int, object, int] | None = None
            self.subscriptions: list[tuple[str, int]] = []
            self.disconnect_calls = 0
            self.on_connect = None
            self.on_disconnect = None
            self.on_message = None
            self.instances.append(self)

        def set_auth_credentials(self, username: str | None, password: str | None) -> None:
            self.auth_credentials = (username, password)

        def set_config(self, config: dict[str, int]) -> None:
            self.config = config

        def subscribe(self, topic: str, qos: int) -> None:
            self.subscriptions.append((topic, qos))

        async def connect(
            self, host: str, port: int, *, keepalive: int, ssl: object, version: int = 5
        ) -> None:
            self.connect_args = (host, port, keepalive, ssl, version)
            if connect_error:
                raise connect_error
            self.on_connect(self, None, None, None)

        async def disconnect(self) -> None:
            self.disconnect_calls += 1

    mock_module = ModuleType("gmqtt")
    mock_module.Client = MockMQTTClient
    monkeypatch.setattr("agentiot.app.gmqtt_available", lambda: True)
    monkeypatch.setitem(sys.modules, "gmqtt", mock_module)
    return MockMQTTClient


def event_types(client: TestClient) -> list[str]:
    return [
        item["event_type"] for item in client.get("/api/audit/events").json()["items"]
    ]


def test_mqtt_message_ingestion_creates_telemetry_alert_and_audit(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt.db"))
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "greenhouse-1", "name": "Zone 1"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-mqtt-1",
            "name": "MQTT Temperature Sensor",
            "adapter": "mqtt",
            "asset_id": "greenhouse-1",
        },
    )

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-mqtt-1/telemetry",
            "payload": '{"metric":"temperature_c","value":89.5,"unit":"C"}',
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["accepted"] is True
    assert body["device_id"] == "sensor-mqtt-1"
    assert body["telemetry_id"] == 1

    telemetry = client.get("/api/telemetry").json()["items"]
    assert telemetry[0]["device_id"] == "sensor-mqtt-1"
    assert telemetry[0]["metric"] == "temperature_c"

    alerts = client.get("/api/alerts").json()["items"]
    assert alerts[0]["severity"] == "critical"

    audit = client.get("/api/audit/events", headers=OPERATOR_HEADERS).json()["items"]
    mqtt_audits = [
        item for item in audit if item["event_type"] == "mqtt.telemetry.accepted"
    ]
    assert len(mqtt_audits) == 1
    assert mqtt_audits[0]["subject_id"] == "sensor-mqtt-1"



def test_mqtt_message_ingestion_honors_configured_topic_prefix(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_MQTT_TOPIC_PREFIX", "greenovax/lab")
    client = TestClient(create_app(database_path=tmp_path / "mqtt-prefix.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-mqtt-prefix",
            "name": "Prefixed MQTT Sensor",
            "adapter": "mqtt",
        },
    )

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "greenovax/lab/sensor-mqtt-prefix/telemetry",
            "payload": '{"metric":"temperature_c","value":22.5,"unit":"C"}',
        },
    )
    rejected = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-mqtt-prefix/telemetry",
            "payload": '{"metric":"temperature_c","value":22.5,"unit":"C"}',
        },
    )

    assert response.status_code == 201
    assert response.json()["device_id"] == "sensor-mqtt-prefix"
    assert rejected.status_code == 400
    assert rejected.json()["detail"] == "Unsupported MQTT topic"
    telemetry = client.get("/api/telemetry").json()["items"]
    assert telemetry[0]["device_id"] == "sensor-mqtt-prefix"


def test_mqtt_message_rejects_invalid_topic_without_telemetry(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-invalid.db"))

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "bad/topic",
            "payload": '{"metric":"temperature_c","value":89.5}',
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported MQTT topic"
    assert client.get("/api/telemetry").json()["items"] == []


def test_mqtt_message_rejects_invalid_payload_without_telemetry(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-payload.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-mqtt-2", "name": "Sensor", "adapter": "mqtt"},
    )

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-mqtt-2/telemetry",
            "payload": '{"metric":"temperature_c"}',
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid MQTT payload"
    assert client.get("/api/telemetry").json()["items"] == []


def test_mqtt_message_rejects_semantic_invalid_payload_without_audit(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-semantic.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-mqtt-3", "name": "Sensor", "adapter": "mqtt"},
    )

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-mqtt-3/telemetry",
            "payload": '{"metric":null,"value":20}',
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid MQTT payload"
    assert client.get("/api/telemetry").json()["items"] == []
    assert "mqtt.telemetry.accepted" not in event_types(client)


def test_mqtt_message_rejects_out_of_range_metric_without_audit(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-range.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-mqtt-range", "name": "Sensor", "adapter": "mqtt"},
    )

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-mqtt-range/telemetry",
            "payload": '{"metric":"oxygen_pct","value":150,"unit":"%"}',
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Telemetry value outside supported range"
    assert client.get("/api/telemetry").json()["items"] == []
    assert "mqtt.telemetry.accepted" not in event_types(client)


def test_mqtt_message_requires_mqtt_registered_device_without_audit(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mqtt-adapter.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-rest-1", "name": "REST Sensor", "adapter": "rest"},
    )

    response = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-rest-1/telemetry",
            "payload": '{"metric":"temperature_c","value":20}',
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Device is not registered for MQTT"
    assert client.get("/api/telemetry").json()["items"] == []
    assert "mqtt.telemetry.accepted" not in event_types(client)


def test_mqtt_broker_status_is_safe_when_not_configured(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AGENTIOT_MQTT_BROKER_HOST", raising=False)
    monkeypatch.delenv("AGENTIOT_MQTT_USERNAME", raising=False)
    monkeypatch.delenv("AGENTIOT_MQTT_PASSWORD", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "mqtt-broker-off.db"))

    response = client.get("/api/adapters/mqtt/broker/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_configured"
    assert body["configured"] is False
    assert body["connected"] is False
    assert body["topic_filter"] == "agentiot/+/telemetry"


def test_mqtt_broker_status_hides_host_and_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.invalid")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_PORT", "8883")
    monkeypatch.setenv("AGENTIOT_MQTT_TOPIC_PREFIX", "fixture")
    monkeypatch.setenv("AGENTIOT_MQTT_USERNAME", "username-fixture")
    monkeypatch.setenv("AGENTIOT_MQTT_PASSWORD", "password-fixture")
    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    client = TestClient(create_app(database_path=tmp_path / "mqtt-broker-on.db"))

    response = client.get("/api/adapters/mqtt/broker/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "configured_manual_start"
    assert body["configured"] is True
    assert body["port"] == 8883
    assert body["topic_filter"] == "fixture/+/telemetry"
    assert body["username_configured"] is True
    assert body["password_configured"] is True
    assert body["tls_enabled"] is True
    assert "password-fixture" not in response.text
    assert "broker.invalid" not in response.text
    assert "username-fixture" not in response.text


def test_mqtt_broker_status_uses_file_backed_secrets(tmp_path, monkeypatch) -> None:
    secret_dir = tmp_path / "mqtt-secrets"
    secret_dir.mkdir()
    password_file = secret_dir / "password"
    ca_cert_file = secret_dir / "ca.crt"
    client_cert_file = secret_dir / "client.crt"
    client_key_file = secret_dir / "client.key"
    password_file.write_text("password-file-fixture", encoding="utf-8")
    ca_cert_file.write_text("ca-file-fixture", encoding="utf-8")
    client_cert_file.write_text("cert-file-fixture", encoding="utf-8")
    client_key_file.write_text("key-file-fixture", encoding="utf-8")
    for env_name in (
        "AGENTIOT_MQTT_PASSWORD",
        "AGENTIOT_MQTT_CA_CERT",
        "AGENTIOT_MQTT_CLIENT_CERT",
        "AGENTIOT_MQTT_CLIENT_KEY",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.invalid")
    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    monkeypatch.setenv("AGENTIOT_MQTT_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv("AGENTIOT_MQTT_CA_CERT_FILE", str(ca_cert_file))
    monkeypatch.setenv("AGENTIOT_MQTT_CLIENT_CERT_FILE", str(client_cert_file))
    monkeypatch.setenv("AGENTIOT_MQTT_CLIENT_KEY_FILE", str(client_key_file))
    client = TestClient(create_app(database_path=tmp_path / "mqtt-broker-files.db"))

    response = client.get("/api/adapters/mqtt/broker/status")

    assert response.status_code == 200
    body = response.json()
    assert body["password_configured"] is True
    assert body["ca_cert_configured"] is True
    assert body["client_cert_configured"] is True
    assert body["client_key_configured"] is True
    assert body["tls_enabled"] is True
    for blocked in (
        "password-file-fixture",
        "ca-file-fixture",
        "cert-file-fixture",
        "key-file-fixture",
        str(secret_dir),
    ):
        assert blocked not in response.text


def test_production_mqtt_rejects_secret_files_outside_runtime_mount(
    tmp_path, monkeypatch
) -> None:
    unsafe_file = tmp_path / "mqtt-password"
    unsafe_file.write_text("unsafe-password", encoding="utf-8")
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.delenv("AGENTIOT_MQTT_PASSWORD", raising=False)
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.invalid")
    monkeypatch.setenv("AGENTIOT_MQTT_PASSWORD_FILE", str(unsafe_file))
    client = TestClient(create_app(database_path=tmp_path / "mqtt-prod-secret.db"))

    response = client.get("/api/adapters/mqtt/broker/status")

    assert response.status_code == 200
    assert response.json()["password_configured"] is False
    assert "unsafe-password" not in response.text
    assert str(unsafe_file) not in response.text


def test_mqtt_broker_status_sanitizes_raw_runtime_error(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.invalid")
    client = TestClient(create_app(database_path=tmp_path / "mqtt-broker-error.db"))
    client.app.state.mqtt_broker.last_error = (
        "connect failed for broker.invalid using /private/client.key"
    )

    response = client.get("/api/adapters/mqtt/broker/status")

    assert response.status_code == 200
    assert response.json()["last_error"] == "broker_runtime_error"
    assert "broker.invalid" not in response.text
    assert "/private/client.key" not in response.text


def test_mqtt_broker_handler_uses_existing_ingestion_boundary(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "mqtt-broker-handler.db")
    client = TestClient(app)
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-broker-1", "name": "Broker Sensor", "adapter": "mqtt"},
    )

    result = app.state.mqtt_broker.handle_message(
        "agentiot/sensor-broker-1/telemetry",
        b'{"metric":"temperature_c","value":86,"unit":"C"}',
    )

    assert result["accepted"] is True
    assert app.state.mqtt_broker.public_status()["messages_accepted"] == 1
    assert client.get("/api/telemetry").json()["items"][0]["device_id"] == "sensor-broker-1"
    assert client.get("/api/alerts").json()["items"][0]["severity"] == "critical"
    assert "mqtt.telemetry.accepted" in event_types(client)


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        ("a" * (MQTT_TOPIC_MAX_BYTES + 1), b'{"metric":"temperature_c","value":20}'),
        ("agentiot/sensor-broker-invalid/telemetry", b"x" * (MQTT_PAYLOAD_MAX_BYTES + 1)),
        ("agentiot/sensor-broker-invalid/telemetry", b"\xff"),
    ],
)
def test_mqtt_broker_rejects_unbounded_or_invalid_bytes_without_persistence(
    tmp_path, topic, payload
) -> None:
    app = create_app(database_path=tmp_path / "mqtt-broker-invalid-bytes.db")
    client = TestClient(app)
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-broker-invalid",
            "name": "Broker Sensor",
            "adapter": "mqtt",
        },
    )

    with pytest.raises(HTTPException) as error:
        app.state.mqtt_broker.handle_message(topic, payload)

    assert error.value.status_code == 400
    assert error.value.detail == "Invalid MQTT message"
    status = app.state.mqtt_broker.public_status()
    assert status["last_error"] is None
    assert status["last_ingestion_error"] == "message_rejected_by_ingestion_boundary"
    assert client.get("/api/telemetry").json()["items"] == []
    assert "mqtt.telemetry.accepted" not in event_types(client)


def test_rejected_message_does_not_poison_connected_production_readiness(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "mqtt-ingestion-readiness.db"
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_DB_PATH", str(database_path))
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "mqtt-ready-operator-" + ("a" * 64))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "mqtt-ready-admin-" + ("b" * 64))
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.fixture")
    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    configure_offhost_restore_receipt(monkeypatch, tmp_path)
    app = create_app(database_path=database_path)
    app.state.mqtt_broker.connected = True
    client = TestClient(app)

    with pytest.raises(HTTPException):
        app.state.mqtt_broker.handle_message(
            "a" * (MQTT_TOPIC_MAX_BYTES + 1),
            b'{"metric":"temperature_c","value":20}',
        )

    status = app.state.mqtt_broker.public_status()
    readiness = client.get("/readyz")
    assert status["connected"] is True
    assert status["last_error"] is None
    assert status["last_ingestion_error"] == "message_rejected_by_ingestion_boundary"
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"


@pytest.mark.parametrize(
    "payload",
    [
        '{"metric":"temperature_c","value":20,"extra":' + ("[" * 40) + "0" + ("]" * 40) + "}",
        "[" * 1400 + "0" + "]" * 1400,
    ],
)
def test_mqtt_rejects_excessive_json_depth_without_persistence(
    tmp_path, payload
) -> None:
    app = create_app(database_path=tmp_path / "mqtt-depth.db")
    client = TestClient(app)
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-depth", "name": "Depth Sensor", "adapter": "mqtt"},
    )

    rest = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={"topic": "agentiot/sensor-depth/telemetry", "payload": payload},
    )
    with pytest.raises(HTTPException) as broker_error:
        app.state.mqtt_broker.handle_message(
            "agentiot/sensor-depth/telemetry", payload.encode("utf-8")
        )

    assert rest.status_code == 400
    assert rest.json()["detail"] == "Invalid MQTT payload"
    assert broker_error.value.status_code == 400
    assert client.get("/api/telemetry").json()["items"] == []


def test_mqtt_rest_and_broker_enforce_utf8_byte_budget(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "mqtt-unicode-budget.db")
    client = TestClient(app)
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-unicode", "name": "Unicode Sensor", "adapter": "mqtt"},
    )
    payload = '{"metric":"temperature_c","value":20,"padding":"' + ("é" * 33000) + '"}'

    rest = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={"topic": "agentiot/sensor-unicode/telemetry", "payload": payload},
    )
    with pytest.raises(HTTPException) as broker_error:
        app.state.mqtt_broker.handle_message(
            "agentiot/sensor-unicode/telemetry", payload
        )

    assert rest.status_code == 400
    assert rest.json()["detail"] == "Invalid MQTT message"
    assert broker_error.value.status_code == 400
    assert broker_error.value.detail == "Invalid MQTT message"
    assert client.get("/api/telemetry").json()["items"] == []


def test_production_mqtt_autostart_requires_tls_without_connecting(tmp_path, monkeypatch) -> None:
    mock_client = install_mock_gmqtt(monkeypatch)
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "strong-runtime-token-" + ("a" * 64))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "strong-admin-token-" + ("b" * 64))
    monkeypatch.setenv("AGENTIOT_MQTT_AUTOSTART", "true")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.fixture")
    monkeypatch.delenv("AGENTIOT_MQTT_BROKER_PORT", raising=False)
    monkeypatch.delenv("AGENTIOT_MQTT_TLS", raising=False)
    app = create_app(database_path=tmp_path / "mqtt-production-tls.db")

    with TestClient(app) as client:
        status = client.get("/api/adapters/mqtt/broker/status").json()
        readiness = client.get("/readyz")
        preflight = client.get("/api/production/preflight").json()

    assert status["status"] == "tls_required"
    assert status["port"] == 8883
    assert status["tls_enabled"] is False
    assert status["tls_required"] is True
    assert status["last_error"] == "mqtt_tls_required"
    assert readiness.status_code == 503
    assert readiness.json()["status"] == "not_ready"
    mqtt_check = next(
        item for item in preflight["checks"]
        if item["check_id"] == "mqtt-broker-subscriber"
    )
    assert mqtt_check["state"] == "customer_action_required"
    assert mqtt_check["runtime_signals"]["broker_configured"] is True
    assert mqtt_check["runtime_signals"]["runtime_connected"] is False
    assert mqtt_check["runtime_signals"]["tls_requested"] is False
    assert mock_client.instances == []


def test_production_manual_mqtt_stays_not_ready_until_tls_connected(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_DB_PATH", str(tmp_path / "runtime.db"))
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "mqtt-manual-operator-" + ("a" * 64))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "mqtt-manual-admin-" + ("b" * 64))
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.fixture")
    monkeypatch.delenv("AGENTIOT_MQTT_AUTOSTART", raising=False)
    monkeypatch.delenv("AGENTIOT_MQTT_TLS", raising=False)
    app = create_app(database_path=tmp_path / "mqtt-manual-no-tls.db")
    client = TestClient(app)

    status = client.get("/api/adapters/mqtt/broker/status")
    readiness = client.get("/readyz")
    preflight = client.get("/api/production/preflight").json()

    assert status.json()["status"] == "tls_required"
    assert status.json()["tls_required"] is True
    assert readiness.status_code == 503
    assert readiness.json()["status"] == "not_ready"
    mqtt_check = next(
        item for item in preflight["checks"]
        if item["check_id"] == "mqtt-broker-subscriber"
    )
    assert mqtt_check["state"] == "customer_action_required"
    assert mqtt_check["runtime_signals"]["runtime_connected"] is False

    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    tls_app = create_app(database_path=tmp_path / "mqtt-manual-disconnected.db")
    tls_client = TestClient(tls_app)
    tls_status = tls_client.get("/api/adapters/mqtt/broker/status")
    tls_readiness = tls_client.get("/readyz")
    tls_preflight = tls_client.get("/api/production/preflight").json()

    assert tls_status.json()["status"] == "configured_manual_start"
    assert tls_readiness.status_code == 503
    assert tls_readiness.json()["status"] == "not_ready"
    tls_mqtt_check = next(
        item for item in tls_preflight["checks"]
        if item["check_id"] == "mqtt-broker-subscriber"
    )
    assert tls_mqtt_check["state"] == "customer_action_required"
    assert tls_mqtt_check["runtime_signals"]["tls_requested"] is True
    assert tls_mqtt_check["runtime_signals"]["runtime_connected"] is False


def test_configured_mqtt_autostart_connects_subscribes_and_stops(
    tmp_path, monkeypatch
) -> None:
    mock_client = install_mock_gmqtt(monkeypatch)
    monkeypatch.setenv("AGENTIOT_MQTT_AUTOSTART", "true")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.fixture")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_PORT", "1884")
    monkeypatch.setenv("AGENTIOT_MQTT_CLIENT_ID", "fixture-dashboard")
    monkeypatch.setenv("AGENTIOT_MQTT_USERNAME", "fixture-user")
    monkeypatch.setenv("AGENTIOT_MQTT_PASSWORD", "fixture-password")
    monkeypatch.setenv("AGENTIOT_MQTT_TOPIC_PREFIX", "greenovax/lab")
    monkeypatch.setenv("AGENTIOT_MQTT_QOS", "2")
    monkeypatch.setenv("AGENTIOT_MQTT_KEEPALIVE", "75")
    app = create_app(database_path=tmp_path / "mqtt-lifecycle.db")

    with TestClient(app) as client:
        response = client.get("/api/adapters/mqtt/broker/status")

        assert response.status_code == 200
        assert response.json()["status"] == "connected"
        assert response.json()["connected"] is True

    instance = mock_client.instances[0]
    assert instance.client_id == "fixture-dashboard"
    assert instance.auth_credentials == ("fixture-user", "fixture-password")
    assert instance.config == {"reconnect_retries": 10, "reconnect_delay": 30}
    assert instance.connect_args[:4] == ("broker.fixture", 1884, 75, False)
    assert instance.connect_args[4] == 5
    assert instance.subscriptions == [
        ("greenovax/lab/+/telemetry", 2),
        ("spBv1.0/+/DDATA/+/+", 2),
        ("homie/+/+/+", 2),
    ]
    assert instance.disconnect_calls == 1
    assert app.state.mqtt_broker.public_status()["status"] == "stopped"


def test_configured_mqtt_autostart_reports_safe_connection_failure(
    tmp_path, monkeypatch
) -> None:
    mock_client = install_mock_gmqtt(monkeypatch, OSError("broker unavailable"))
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "mqtt-production-operator-" + ("a" * 64))
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "mqtt-production-admin-" + ("b" * 64))
    monkeypatch.setenv("AGENTIOT_MQTT_AUTOSTART", "true")
    monkeypatch.setenv("AGENTIOT_MQTT_BROKER_HOST", "broker.fixture")
    monkeypatch.setenv("AGENTIOT_MQTT_TLS", "true")
    app = create_app(database_path=tmp_path / "mqtt-lifecycle-failure.db")

    with TestClient(app) as client:
        response = client.get("/api/adapters/mqtt/broker/status")
        readiness = client.get("/readyz")

        assert response.status_code == 200
        assert response.json()["status"] == "connection_error"
        assert response.json()["connected"] is False
        assert response.json()["last_error"] == "broker_connection_failed"
        assert "broker unavailable" not in response.text
        assert readiness.status_code == 503
        assert readiness.json()["status"] == "not_ready"
        preflight = client.get("/api/production/preflight").json()
        mqtt_check = next(
            item for item in preflight["checks"]
            if item["check_id"] == "mqtt-broker-subscriber"
        )
        assert mqtt_check["state"] == "customer_action_required"
        assert mqtt_check["runtime_signals"]["runtime_connected"] is False
        assert mqtt_check["runtime_signals"]["runtime_status"] == "connection_error"

    assert mock_client.instances[0].disconnect_calls == 1
    assert app.state.mqtt_broker.public_status()["status"] == "connection_error"


def test_recovery_approval_adds_audit_event(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "approval-audit.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-audit", "name": "Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-audit", "metric": "temperature_c", "value": 90.0},
    )
    proposal_id = client.get("/api/recovery/proposals").json()["items"][0]["proposal_id"]

    client.post(
        f"/api/recovery/proposals/{proposal_id}/approve",
        headers=OPERATOR_HEADERS,
        json={"approved_by": "operator"},
    )

    public_audit = client.get("/api/audit/events").json()["items"]
    assert public_audit[-1]["event_type"] == "recovery.approved"
    assert set(public_audit[-1]) == {"event_type", "created_at"}
    audit = client.get("/api/audit/events", headers=OPERATOR_HEADERS).json()["items"]
    assert audit[-1]["actor"] == "operator"
