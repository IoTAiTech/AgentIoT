# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

import agentiot.app as agentiot_app
from agentiot.app import (
    ApprovalRequest,
    CoreStore,
    create_app,
    dashboard_initial_state,
    operation_workbench,
)
from conftest import make_test_jwt, seed_bearer_assignment


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_edge_data_retention_and_sqlite_quota_are_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_MAX_ROWS", 3)
    monkeypatch.setattr(agentiot_app, "EDGE_AUDIT_MAX_ROWS", 4)
    monkeypatch.setattr(agentiot_app, "EDGE_READ_WINDOW_ROWS", 2)
    database_path = tmp_path / "edge-retention.db"
    app = create_app(database_path=database_path)
    client = TestClient(app)
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "edge-line", "name": "Edge Line"},
    ).status_code == 201
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "edge-sensor",
            "name": "Edge Sensor",
            "adapter": "rest",
            "asset_id": "edge-line",
        },
    ).status_code == 201
    with app.state.store.connect() as connection:
        for value in range(6):
            connection.execute(
                """
                INSERT INTO telemetry (device_id, metric, value, unit, recorded_at)
                VALUES (?, 'temperature_c', ?, 'C', ?)
                """,
                ("edge-sensor", 20 + value, datetime.now(UTC).isoformat()),
            )
    for value in range(6):
        app.state.store.add_audit_event(
            event_type="edge.retention.fixture",
            subject_id=str(value),
            actor="retention-test",
        )

    result = app.state.store.cleanup_edge_data_retention(
        actor="system-retention-test"
    )

    assert result["telemetry_deleted"] == 3
    assert app.state.store.count_rows("telemetry") == 3
    assert app.state.store.count_rows("audit_events") <= 4
    assert len(app.state.store.list_rows("telemetry")) == 2
    assert len(app.state.store.list_latest_telemetry_by_device()) == 1
    with app.state.store.connect() as connection:
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        max_page_count = int(
            connection.execute("PRAGMA max_page_count").fetchone()[0]
        )
    assert page_size * max_page_count <= agentiot_app.EDGE_DATABASE_MAX_BYTES

    restarted = create_app(database_path=database_path)
    assert restarted.state.store.count_rows("telemetry") == 3
    assert restarted.state.store.count_rows("audit_events") <= 4


def test_telemetry_quota_is_per_device_and_global_capacity_is_fail_closed(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_MAX_ROWS", 4)
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_PER_DEVICE_MAX_ROWS", 2)
    app = create_app(database_path=tmp_path / "edge-device-quota.db")
    client = TestClient(app)
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "edge-fleet", "name": "Edge Fleet"},
    ).status_code == 201
    for device_id in ("noisy", "quiet", "new-device"):
        assert client.post(
            "/api/devices",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": device_id,
                "name": device_id,
                "adapter": "rest",
                "asset_id": "edge-fleet",
            },
        ).status_code == 201
    for value in (20, 21, 22):
        assert client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "noisy",
                "metric": "temperature_c",
                "value": value,
                "unit": "C",
            },
        ).status_code == 201
    for value in (30, 31):
        assert client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "quiet",
                "metric": "temperature_c",
                "value": value,
                "unit": "C",
            },
        ).status_code == 201

    rejected = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "new-device",
            "metric": "temperature_c",
            "value": 25,
            "unit": "C",
        },
    )

    assert rejected.status_code == 507
    assert rejected.headers["Retry-After"] == "60"
    with app.state.store.connect() as connection:
        counts = {
            row["device_id"]: row["count"]
            for row in connection.execute(
                "SELECT device_id, COUNT(*) AS count FROM telemetry GROUP BY device_id"
            ).fetchall()
        }
    assert counts == {"noisy": 2, "quiet": 2}


def test_global_telemetry_backpressure_is_atomic_across_app_instances(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_MAX_ROWS", 1)
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_PER_DEVICE_MAX_ROWS", 1)
    database_path = tmp_path / "shared-telemetry-budget.db"
    first_app = create_app(database_path=database_path)
    second_app = create_app(database_path=database_path)
    client = TestClient(first_app)
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "shared-edge", "name": "Shared Edge"},
    ).status_code == 201
    for device_id in ("sensor-a", "sensor-b"):
        assert client.post(
            "/api/devices",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": device_id,
                "name": device_id,
                "adapter": "rest",
                "asset_id": "shared-edge",
            },
        ).status_code == 201
    barrier = Barrier(2)

    def submit(app, device_id: str) -> int:
        barrier.wait(timeout=5)
        return TestClient(app).post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": device_id,
                "metric": "temperature_c",
                "value": 21.0,
                "unit": "C",
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(submit, first_app, "sensor-a"),
            executor.submit(submit, second_app, "sensor-b"),
        )
        statuses = sorted(future.result() for future in futures)

    assert statuses == [201, 507]
    assert first_app.state.store.count_rows("telemetry") == 1


def test_rest_and_mqtt_share_the_same_telemetry_budget(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_MAX_ROWS", 2)
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_PER_DEVICE_MAX_ROWS", 1)
    app = create_app(database_path=tmp_path / "shared-producer-budget.db")
    client = TestClient(app)
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "producer-edge", "name": "Producer Edge"},
    ).status_code == 201
    for device_id, adapter in (
        ("rest-noisy", "rest"),
        ("mqtt-quiet", "mqtt"),
        ("rest-new", "rest"),
    ):
        assert client.post(
            "/api/devices",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": device_id,
                "name": device_id,
                "adapter": adapter,
                "asset_id": "producer-edge",
            },
        ).status_code == 201
    for value in (20.0, 21.0):
        assert client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "rest-noisy",
                "metric": "temperature_c",
                "value": value,
                "unit": "C",
            },
        ).status_code == 201
    assert client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/mqtt-quiet/telemetry",
            "payload": '{"metric":"oxygen_pct","value":20.9,"unit":"%"}',
        },
    ).status_code == 201
    rejected = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "rest-new",
            "metric": "temperature_c",
            "value": 22.0,
            "unit": "C",
        },
    )

    assert rejected.status_code == 507
    with app.state.store.connect() as connection:
        counts = {
            row["device_id"]: row["count"]
            for row in connection.execute(
                "SELECT device_id, COUNT(*) AS count FROM telemetry GROUP BY device_id"
            ).fetchall()
        }
    assert counts == {"mqtt-quiet": 1, "rest-noisy": 1}


def test_telemetry_audit_flood_cannot_evict_protected_receipts(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_AUDIT_MAX_ROWS", 8)
    monkeypatch.setattr(agentiot_app, "EDGE_AUDIT_ROUTINE_MAX_ROWS", 4)
    store = CoreStore(tmp_path / "protected-audit.db")
    protected = (
        "identity.local.login.succeeded",
        "network.discovery.scan.completed",
        "network.discovery.candidate.approved",
    )
    for event_type in protected:
        store.add_audit_event(event_type, event_type, "security-test")
    for index in range(20):
        store.add_audit_event(
            "telemetry.ingested",
            f"telemetry-{index}",
            "telemetry-test",
        )

    store.cleanup_edge_data_retention(actor="system-retention-test")

    remaining = store.list_rows("audit_events")
    event_types = {row["event_type"] for row in remaining}
    assert set(protected).issubset(event_types)
    assert store.count_rows("audit_events") <= 8


def test_repeated_anomalies_keep_telemetry_alerts_and_recovery_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_MAX_ROWS", 2)
    monkeypatch.setattr(agentiot_app, "EDGE_TELEMETRY_PER_DEVICE_MAX_ROWS", 2)
    app = create_app(database_path=tmp_path / "bounded-anomaly.db")
    client = TestClient(app)
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "hot-sensor", "name": "Hot Sensor"},
    ).status_code == 201

    for value in range(20):
        response = client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "hot-sensor",
                "metric": "temperature_c",
                "value": 88.0 + value,
                "unit": "C",
            },
        )
        assert response.status_code == 201

    assert app.state.store.count_rows("telemetry") == 2
    assert len(app.state.store.list_rows("alerts")) == 1
    assert len(app.state.store.list_rows("recovery_proposals")) == 1


def test_telemetry_and_audit_receipt_rollback_together_for_rest_and_mqtt(
    tmp_path,
    monkeypatch,
) -> None:
    app = create_app(database_path=tmp_path / "atomic-telemetry-audit.db")
    client = TestClient(app, raise_server_exceptions=False)
    for device_id, adapter in (("rest-sensor", "rest"), ("mqtt-sensor", "mqtt")):
        assert client.post(
            "/api/devices",
            headers=OPERATOR_HEADERS,
            json={"device_id": device_id, "name": device_id, "adapter": adapter},
        ).status_code == 201

    def fail_audit(*_args, **_kwargs):
        raise sqlite3.OperationalError("injected audit failure")

    monkeypatch.setattr(app.state.store, "_insert_audit_event", fail_audit)
    rest = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "rest-sensor",
            "metric": "temperature_c",
            "value": 90.0,
            "unit": "C",
        },
    )
    mqtt = client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/mqtt-sensor/telemetry",
            "payload": '{"metric":"temperature_c","value":91,"unit":"C"}',
        },
    )

    assert rest.status_code == 500
    assert mqtt.status_code == 500
    assert app.state.store.count_rows("telemetry") == 0
    assert app.state.store.list_rows("alerts") == []
    assert app.state.store.list_rows("recovery_proposals") == []


def test_routine_audit_admission_is_continuously_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_AUDIT_MAX_ROWS", 8)
    monkeypatch.setattr(agentiot_app, "EDGE_AUDIT_ROUTINE_MAX_ROWS", 4)
    app = create_app(database_path=tmp_path / "continuous-audit-budget.db")
    client = TestClient(app)
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "audit-sensor", "name": "Audit Sensor"},
    ).status_code == 201
    protected = app.state.store.add_audit_event(
        "network.discovery.candidate.approved",
        "protected-candidate",
        "security-test",
    )

    for value in range(20):
        assert client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "audit-sensor",
                "metric": "temperature_c",
                "value": 20.0 + value / 10,
                "unit": "C",
            },
        ).status_code == 201

    events = app.state.store.list_rows("audit_events")
    assert app.state.store.count_rows("audit_events") <= 8
    assert any(
        event["audit_event_id"] == protected["audit_event_id"] for event in events
    )
    assert sum(event["event_class"] == "routine" for event in events) <= 4


def test_retention_batch_and_receipt_are_atomic_and_startup_bounded(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_RETENTION_BATCH_ROWS", 2)
    store = CoreStore(tmp_path / "atomic-retention.db")
    old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    with store.connect() as connection:
        for value in range(5):
            connection.execute(
                """
                INSERT INTO telemetry (device_id, metric, value, unit, recorded_at)
                VALUES ('retention-sensor', 'temperature_c', ?, 'C', ?)
                """,
                (value, old),
            )

    original_insert = store._insert_audit_event

    def fail_receipt(*_args, **_kwargs):
        raise sqlite3.OperationalError("injected receipt failure")

    monkeypatch.setattr(store, "_insert_audit_event", fail_receipt)
    with pytest.raises(sqlite3.OperationalError, match="injected receipt failure"):
        store.cleanup_edge_data_retention(actor="retention-test")
    assert store.count_rows("telemetry") == 5

    monkeypatch.setattr(store, "_insert_audit_event", original_insert)
    result = store.cleanup_edge_data_retention(actor="retention-test")
    assert result["telemetry_deleted"] == 2
    assert store.count_rows("telemetry") == 3
    events = store.list_rows("audit_events")
    assert events[-1]["event_type"] == "edge.data.retention.cleaned"


def test_existing_database_over_edge_ceiling_is_rejected_without_mutation(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "oversized-edge.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE payloads (payload BLOB NOT NULL)")
        connection.execute("INSERT INTO payloads VALUES (zeroblob(200000))")
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
    before = database_path.read_bytes()
    monkeypatch.setattr(
        agentiot_app,
        "EDGE_DATABASE_MAX_BYTES",
        page_size * (page_count - 1),
    )

    with pytest.raises(
        sqlite3.OperationalError,
        match="exceeds the configured edge storage ceiling",
    ):
        CoreStore(database_path)

    assert database_path.read_bytes() == before


def test_bounded_telemetry_keeps_exact_totals_and_latest_per_device_cmdb(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(agentiot_app, "EDGE_READ_WINDOW_ROWS", 2)
    app = create_app(database_path=tmp_path / "bounded-telemetry.db")
    client = TestClient(app)
    for asset_id, device_id in (
        ("quiet-zone", "quiet-sensor"),
        ("noisy-zone", "noisy-sensor"),
    ):
        assert client.post(
            "/api/assets",
            headers=OPERATOR_HEADERS,
            json={"asset_id": asset_id, "name": asset_id},
        ).status_code == 201
        assert client.post(
            "/api/devices",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": device_id,
                "name": device_id,
                "adapter": "rest",
                "asset_id": asset_id,
            },
        ).status_code == 201
    assert client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "quiet-sensor",
            "metric": "oxygen_pct",
            "value": 20.8,
            "unit": "%",
        },
    ).status_code == 201
    for value in (20.0, 21.0, 22.0):
        assert client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "noisy-sensor",
                "metric": "temperature_c",
                "value": value,
                "unit": "C",
            },
        ).status_code == 201

    summary = client.get("/api/operations/summary").json()
    workbench = operation_workbench(app.state.store, False)
    initial = dashboard_initial_state(
        app.state.store,
        False,
        {"status": "disabled", "enabled": False, "records": {}},
    )
    device_items = {
        item["ci_id"]: item
        for item in initial["cmdb"]["items"]
        if item["ci_type"] != "asset"
    }

    assert len(initial["telemetry"]["items"]) == 2
    assert summary["counters"]["telemetry"] == 4
    assert workbench["evidence_summary"]["telemetry"] == 4
    assert device_items["device:quiet-sensor"]["metric"] == "oxygen_pct"
    assert device_items["device:noisy-sensor"]["metric"] == "temperature_c"
    assert workbench["evidence_summary"]["cmdb_ci"] == 4
    assert workbench["evidence_summary"]["sensor_ci"] == 0


def test_device_asset_and_telemetry_flow_creates_alert_and_proposal(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "phase2.db"))

    asset_response = client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={
            "asset_id": "greenhouse-1",
            "name": "Greenhouse Zone 1",
            "location": "Greenhouse Zone A",
        },
    )
    assert asset_response.status_code == 201
    assert asset_response.json()["asset_id"] == "greenhouse-1"

    device_response = client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "name": "Temperature Sensor 1",
            "adapter": "rest",
            "asset_id": "greenhouse-1",
            "firmware_version": "1.0.0",
        },
    )
    assert device_response.status_code == 201
    assert device_response.json()["status"] == "registered"

    telemetry_response = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "metric": "temperature_c",
            "value": 88.0,
            "unit": "C",
        },
    )
    assert telemetry_response.status_code == 201
    assert telemetry_response.json()["accepted"] is True

    alerts_response = client.get("/api/alerts")
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()["items"]
    assert len(alerts) == 1
    assert alerts[0]["device_id"] == "sensor-1"
    assert alerts[0]["severity"] == "critical"
    assert alerts[0]["status"] == "open"

    proposals_response = client.get("/api/recovery/proposals")
    assert proposals_response.status_code == 200
    proposals = proposals_response.json()["items"]
    assert len(proposals) == 1
    assert proposals[0]["requires_approval"] is True
    assert proposals[0]["status"] == "pending_approval"


def test_asset_and_device_updates_are_audited_and_operator_gated(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "asset-device-update.db"))
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "greenhouse-ops", "name": "Greenhouse Ops"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-ops-1",
            "name": "Temperature Sensor",
            "adapter": "rest",
            "asset_id": "greenhouse-ops",
            "firmware_version": "1.0.0",
        },
    )

    anonymous = client.patch(
        "/api/devices/sensor-ops-1",
        json={"status": "maintenance"},
    )
    asset_update = client.patch(
        "/api/assets/greenhouse-ops",
        headers=OPERATOR_HEADERS,
        json={"name": "Greenhouse Operations", "location": "Zone B"},
    )
    device_update = client.patch(
        "/api/devices/sensor-ops-1",
        headers=OPERATOR_HEADERS,
        json={"status": "maintenance", "firmware_version": "1.0.1"},
    )
    device_detail = client.get("/api/devices/sensor-ops-1")
    asset_detail = client.get("/api/assets/greenhouse-ops")
    public_audit = client.get("/api/audit/events").json()["items"]
    operator_audit_text = client.get(
        "/api/audit/events",
        headers=OPERATOR_HEADERS,
    ).text

    assert anonymous.status_code == 401
    assert asset_update.status_code == 200
    assert asset_update.json()["name"] == "Greenhouse Operations"
    assert asset_update.json()["location"] == "Zone B"
    assert device_update.status_code == 200
    assert device_update.json()["status"] == "maintenance"
    assert device_update.json()["firmware_version"] == "1.0.1"
    assert device_detail.json()["status"] == "maintenance"
    assert asset_detail.json()["name"] == "Greenhouse Operations"
    assert any(item["event_type"] == "asset.updated" for item in public_audit)
    assert any(item["event_type"] == "device.updated" for item in public_audit)
    assert all(set(item) == {"event_type", "created_at"} for item in public_audit)
    assert "raw_secret_values_logged" in operator_audit_text
    assert "unit-" + "operator-" + "sentinel" not in operator_audit_text


def test_device_update_rejects_unknown_asset_and_invalid_state(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "device-update-invalid.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-ops-2", "name": "Temperature Sensor"},
    )

    unknown_asset = client.patch(
        "/api/devices/sensor-ops-2",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "missing-asset"},
    )
    invalid_state = client.patch(
        "/api/devices/sensor-ops-2",
        headers=OPERATOR_HEADERS,
        json={"status": "broken_state"},
    )
    empty_update = client.patch(
        "/api/assets/missing-asset",
        headers=OPERATOR_HEADERS,
        json={},
    )

    assert unknown_asset.status_code == 404
    assert invalid_state.status_code == 422
    assert empty_update.status_code == 404
    assert "/home/" not in unknown_asset.text
    assert "unit-" + "operator-" + "sentinel" not in unknown_asset.text


def test_rest_adapter_status_counts_rest_devices_and_telemetry_only(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rest-status.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "rest-1", "name": "REST Sensor", "adapter": "rest"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "mqtt-1", "name": "MQTT Sensor", "adapter": "mqtt"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "rest-1",
            "metric": "temperature_c",
            "value": 24.5,
            "unit": "C",
        },
    )
    client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/mqtt-1/telemetry",
            "payload": '{"metric":"temperature_c","value":25.5,"unit":"C"}',
        },
    )

    response = client.get("/api/adapters/rest/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["configured"] is True
    assert body["readiness_state"] == "active"
    assert body["rest_device_count"] == 1
    assert body["rest_telemetry_count"] == 1
    assert body["last_telemetry_at"]
    assert body["ingestion_endpoint"] == "/api/telemetry"
    assert body["safety"]["read_only"] is True
    assert body["safety"]["credentials_returned"] is False
    assert body["safety"]["raw_payloads_returned"] is False
    assert body["safety"]["mqtt_devices_excluded"] is True
    assert "mqtt-1" not in response.text
    assert "/api/operations/summary" in response.text


def test_rest_adapter_status_is_safe_when_idle(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rest-status-idle.db"))

    response = client.get("/api/adapters/rest/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["configured"] is False
    assert body["readiness_state"] == "idle_no_rest_devices"
    assert body["rest_device_count"] == 0
    assert body["rest_telemetry_count"] == 0
    assert body["last_telemetry_at"] is None
    assert body["safety"]["credentials_returned"] is False
    assert "/home/" not in response.text


def test_operations_summary_is_actionable_before_live_records(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-empty.db"))

    response = client.get("/api/operations/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["operational_state"] == "initial_setup_ready_no_live_records"
    assert body["phase_readiness_score"] >= 70
    assert body["counters"]["devices"] == 0
    assert body["counters"]["pending_recovery"] == 0
    assert body["current_risk"]["severity"] == "none"
    assert body["time_window"]["window_id"] == "15m"
    assert body["comparisons"]["assets"]["current_period"] == 0
    assert body["comparisons"]["telemetry"]["current_period"] == 0
    assert body["comparisons"]["readiness"]["delta"] >= 0
    assert "initial asset" in body["next_actions"][0]
    assert len(body["runbook"]) >= 5
    assert body["runbook"][0]["owner"] == "operator"


def test_operations_summary_reports_connected_telemetry_without_active_alert(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-monitoring.db"))
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "edge-1", "name": "Edge Node 1"},
    ).status_code == 201
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "thermal-1",
            "name": "Onboard Thermal Sensor",
            "adapter": "rest",
            "asset_id": "edge-1",
        },
    ).status_code == 201
    assert client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "thermal-1",
            "metric": "temperature_c",
            "value": 24.5,
            "unit": "C",
        },
    ).status_code == 201

    response = client.get("/api/operations/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["operational_state"] == "monitoring_active"
    assert body["latest_telemetry"]["device_id"] == "thermal-1"
    assert body["telemetry_health"]["status"] == "fresh"
    assert body["telemetry_health"]["counts"]["fresh"] == 1
    assert body["comparisons"]["telemetry"] == {
        "current_total": 1,
        "current_period": 1,
        "previous_period": 0,
        "delta": 1,
    }
    assert body["current_risk"] == {
        "label": "No active alert on thermal-1",
        "severity": "none",
        "device_id": "thermal-1",
        "message": "Latest temperature_c telemetry is connected and under active monitoring.",
    }


def test_operations_summary_marks_expired_device_telemetry_offline(tmp_path) -> None:
    database_path = tmp_path / "summary-offline.db"
    client = TestClient(create_app(database_path=database_path))
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "thermal-old", "name": "Thermal Sensor"},
    ).status_code == 201
    assert client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "thermal-old-profile",
            "name": "Thermal cadence",
            "device_id": "thermal-old",
            "telemetry_interval_s": 60,
        },
    ).status_code == 201
    assert client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "thermal-old",
            "metric": "temperature_c",
            "value": 24.5,
            "unit": "C",
        },
    ).status_code == 201
    expired_at = (datetime.now(UTC) - timedelta(minutes=11)).isoformat()
    with client.app.state.store.connect() as connection:
        connection.execute(
            "UPDATE telemetry SET recorded_at = ? WHERE device_id = ?",
            (expired_at, "thermal-old"),
        )

    body = client.get("/api/operations/summary").json()

    assert body["operational_state"] == "telemetry_connection_required"
    assert body["telemetry_health"]["status"] == "offline"
    device_health = body["telemetry_health"]["items"][0]
    assert device_health["state"] == "offline"
    assert device_health["expected_cadence_seconds"] == 60
    assert device_health["age_seconds"] >= 660
    assert body["current_risk"]["severity"] == "critical"
    assert body["current_risk"]["device_id"] == "thermal-old"


def test_operations_summary_compares_real_selected_time_windows(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-window.db"))
    for asset_id in ("asset-previous", "asset-current"):
        response = client.post(
            "/api/assets",
            headers=OPERATOR_HEADERS,
            json={"asset_id": asset_id, "name": asset_id.replace("-", " ").title()},
        )
        assert response.status_code == 201
    previous_at = (datetime.now(UTC) - timedelta(minutes=20)).replace(
        microsecond=0
    ).isoformat()
    with client.app.state.store.connect() as connection:
        connection.execute(
            "UPDATE assets SET created_at = ? WHERE asset_id = ?",
            (previous_at, "asset-previous"),
        )

    response = client.get("/api/operations/summary?window=15m")

    assert response.status_code == 200
    body = response.json()
    assert body["time_window"]["window_id"] == "15m"
    assert body["time_window"]["label"] == "Last 15 minutes"
    assert body["comparisons"]["assets"] == {
        "current_total": 2,
        "current_period": 1,
        "previous_period": 1,
        "delta": 0,
    }
    assert body["comparisons"]["readiness"]["current"] == body[
        "phase_readiness_score"
    ]


def test_operations_summary_rejects_unknown_time_window(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-window-invalid.db"))

    response = client.get("/api/operations/summary?window=quarter")

    assert response.status_code == 422


def test_operations_summary_counts_linked_alert_and_recovery_as_one_anomaly(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-linked.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-linked", "name": "Linked Sensor"},
    )

    telemetry = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-linked", "metric": "temperature_c", "value": 88.0},
    )

    assert telemetry.status_code == 201
    alert = client.get("/api/alerts").json()["items"][0]
    proposal = client.get("/api/recovery/proposals").json()["items"][0]
    assert proposal["alert_id"] == alert["alert_id"]

    summary = client.get("/api/operations/summary?window=15m").json()

    assert summary["counters"]["open_alerts"] == 1
    assert summary["counters"]["pending_recovery"] == 1
    assert summary["comparisons"]["anomalies"] == {
        "current_total": 1,
        "current_period": 1,
        "previous_period": 0,
        "delta": 1,
    }


def test_operations_summary_coalesces_repeated_open_anomaly(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-independent.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-independent", "name": "Independent Sensor"},
    )
    for value in (88.0, 89.0):
        telemetry = client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": "sensor-independent",
                "metric": "temperature_c",
                "value": value,
            },
        )
        assert telemetry.status_code == 201

    alerts = client.get("/api/alerts").json()["items"]
    proposals = client.get("/api/recovery/proposals").json()["items"]
    assert {proposal["alert_id"] for proposal in proposals} == {
        alert["alert_id"] for alert in alerts
    }

    summary = client.get("/api/operations/summary?window=15m").json()

    assert len(alerts) == 1
    assert len(proposals) == 1
    assert summary["counters"]["open_alerts"] == 1
    assert summary["counters"]["pending_recovery"] == 1
    assert summary["comparisons"]["anomalies"] == {
        "current_total": 1,
        "current_period": 1,
        "previous_period": 0,
        "delta": 1,
    }


def test_operations_workbench_returns_executable_runtime_runbook(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "operations-workbench.db"))

    empty = client.get("/api/operations/workbench")

    assert empty.status_code == 200
    body = empty.json()
    assert body["status"] == "ok"
    assert body["current_step_id"] == "asset-device-onboarding"
    assert body["completion_percent"] == 0
    assert body["token_required_for_write"] is True
    assert body["last_action"]["state"] == "idle"
    assert body["last_action"]["audit_event"] is None
    assert [step["step_id"] for step in body["steps"]] == [
        "asset-device-onboarding",
        "telemetry-alert-recovery",
        "cmdb-sensor-discovery",
        "simulator-lab-validation",
        "hitl-close-loop",
    ]
    assert body["steps"][0]["state"] == "ready"
    assert body["steps"][0]["action_endpoint"] == "/api/assets"
    assert body["steps"][1]["state"] == "blocked"
    assert body["steps"][1]["blocker"] == "asset and device required"

    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={
            "asset_id": "greenhouse-1",
            "name": "Greenhouse Zone 1",
            "location": "Greenhouse Zone A",
        },
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "name": "Temperature Sensor 1",
            "adapter": "mqtt",
            "asset_id": "greenhouse-1",
            "firmware_version": "1.0.0",
        },
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "metric": "temperature_c",
            "value": 88.0,
            "unit": "C",
        },
    )

    active = client.get("/api/operations/workbench").json()

    states = {step["step_id"]: step for step in active["steps"]}
    assert states["asset-device-onboarding"]["state"] == "complete"
    assert states["telemetry-alert-recovery"]["state"] == "complete"
    assert states["cmdb-sensor-discovery"]["state"] == "ready"
    assert states["hitl-close-loop"]["state"] == "ready"
    assert active["current_step_id"] == "cmdb-sensor-discovery"
    assert active["completion_percent"] == 40
    assert active["evidence_summary"]["assets"] == 1
    assert active["evidence_summary"]["devices"] == 1
    assert active["last_action"]["state"] == "recorded"
    assert active["last_action"]["audit_event"]["detail_redacted"] is True


def test_operations_workbench_uses_customer_safe_audit_labels(tmp_path) -> None:
    db_path = tmp_path / "operations-audit-labels.db"
    client = TestClient(create_app(database_path=db_path))
    store = CoreStore(db_path)
    store.add_audit_event(
        event_type="project.gap_discovery.reviewed",
        subject_id="gap-review-1",
        actor="delivery",
        detail="{}",
    )

    response = client.get("/api/operations/workbench")

    assert response.status_code == 200
    body = response.json()
    assert body["last_action"]["label"] == "readiness review recorded"
    assert "project" not in body["last_action"]["label"].lower()
    assert "_" not in body["last_action"]["label"]


def test_operational_commissioning_workflow_creates_live_closed_loop_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "operations-workflow.db"))

    response = client.post(
        "/api/operations/workflows/commissioning-run",
        headers=OPERATOR_HEADERS,
        json={},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["asset"]["asset_id"] == "greenhouse-1"
    assert body["device"]["device_id"] == "sensor-1"
    assert body["telemetry"]["accepted"] is True
    assert body["cmdb"]["summary"]["sensor_auto_discovered"] == 1
    assert body["summary"]["counters"]["open_alerts"] == 1
    assert body["summary"]["counters"]["pending_recovery"] == 1
    assert body["workbench"]["completion_percent"] >= 60
    assert body["workbench"]["evidence_summary"]["cmdb_ci"] >= 2
    assert "serial" not in response.text.lower()
    assert body["workbench"]["evidence_summary"]["telemetry"] == 1
    assert body["workbench"]["evidence_summary"]["open_alerts"] == 1
    assert body["workbench"]["evidence_summary"]["pending_recovery"] == 1
    assert body["workbench"]["next_action"]["button_id"] == "shell-proposal-select"

    proposal_id = client.get("/api/recovery/proposals").json()["items"][-1]["proposal_id"]
    approved = client.post(
        f"/api/recovery/proposals/{proposal_id}/approve",
        headers=OPERATOR_HEADERS,
        json={"approved_by": "operator"},
    )
    assert approved.status_code == 200
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "metric": "temperature_c",
            "value": 92.0,
            "unit": "C",
        },
    )

    reopened = client.get("/api/operations/workbench").json()

    reopened_steps = {step["step_id"]: step for step in reopened["steps"]}
    assert reopened_steps["hitl-close-loop"]["state"] == "ready"
    assert reopened["completion_percent"] < 100
    assert reopened["current_step_id"] == "hitl-close-loop"
    assert reopened["evidence_summary"]["pending_recovery"] == 1


def test_operations_workbench_reports_monitoring_when_all_runtime_steps_complete(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", "enabled")
    client = TestClient(create_app(database_path=tmp_path / "operations-complete.db"))

    run = client.post(
        "/api/plugins/hardware-simulator/runs",
        headers=OPERATOR_HEADERS,
        json={
            "device_count": 1,
            "samples_per_device": 1,
            "profiles": ["greenhouse_temperature"],
        },
    )
    assert run.status_code == 201

    proposals = client.get("/api/recovery/proposals").json()["items"]
    for proposal in proposals:
        approve = client.post(
            f"/api/recovery/proposals/{proposal['proposal_id']}/approve",
            headers=OPERATOR_HEADERS,
            json={"approved_by": "operator"},
        )
        assert approve.status_code == 200

    for alert in client.get("/api/alerts").json()["items"]:
        if alert["status"] == "open":
            resolve = client.post(
                f"/api/alerts/{alert['alert_id']}/resolve",
                headers=OPERATOR_HEADERS,
                json={
                    "resolved_by": "operator",
                    "resolution_note": "Closed after approved recovery verification.",
                },
            )
            assert resolve.status_code == 200

    workbench = client.get("/api/operations/workbench").json()

    assert workbench["completion_percent"] == 100
    assert workbench["operational_state"] == "monitoring_active"
    assert workbench["current_step_id"] == "monitoring-active"
    assert workbench["next_action"]["label"] == "Continue live monitoring"
    assert workbench["next_action"]["action_endpoint"] == "/api/operations/summary"
    assert workbench["next_action"]["blocker"] == ""
    assert all(
        step["blocker"] == ""
        for step in workbench["steps"]
        if step["state"] == "complete"
    )


def test_operational_preview_is_read_only_and_keeps_live_records_empty(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "preview.db"))

    response = client.get("/api/demo/operational-preview")

    assert response.status_code == 200
    assert response.json()["preview_mode"] == "read_only"
    assert response.json()["kpis"]["connected_devices"] == 3
    assert client.get("/api/devices").json()["items"] == []
    assert client.get("/api/alerts").json()["items"] == []
    assert client.get("/api/recovery/proposals").json()["items"] == []


def test_demo_bootstrap_is_disabled_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "bootstrap-off.db"))

    response = client.get("/api/demo/bootstrap/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"
    assert body["enabled"] is False
    assert body["seeded"] is False
    assert body["records"]["devices"] == 0
    assert client.get("/api/devices").json()["items"] == []


def test_demo_bootstrap_seeds_live_operational_records(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "bootstrap-on.db"))

    response = client.get("/api/demo/bootstrap/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "seeded"
    assert body["enabled"] is True
    assert body["seeded"] is True
    assert body["records"]["assets"] == 1
    assert body["records"]["devices"] == 1
    assert body["records"]["telemetry"] == 1
    assert body["records"]["alerts"] == 1
    assert body["records"]["recovery_proposals"] == 1
    summary = client.get("/api/operations/summary").json()
    assert summary["operational_state"] == "operator_action_required"
    assert summary["counters"]["pending_recovery"] == 1
    assert summary["latest_telemetry"]["value"] == 88.0


def test_config_profile_requires_operator_and_registered_references(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "config-profile.db"))

    missing_auth = client.post(
        "/api/config/profiles",
        json={"profile_id": "profile-1", "name": "Profile 1"},
    )
    assert missing_auth.status_code in {401, 503}

    missing_asset = client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "profile-1",
            "name": "Profile 1",
            "asset_id": "unknown-asset",
        },
    )
    assert missing_asset.status_code == 404
    assert missing_asset.json()["detail"] == "Asset not registered"

    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "greenhouse-1", "name": "Greenhouse Zone 1"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "name": "Temperature Sensor 1",
            "adapter": "mqtt",
            "asset_id": "greenhouse-1",
            "firmware_version": "1.0.0",
        },
    )

    created = client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "greenhouse-normal",
            "name": "Greenhouse Normal Monitoring",
            "asset_id": "greenhouse-1",
            "device_id": "sensor-1",
            "desired_firmware": "1.0.0",
            "telemetry_interval_s": 60,
            "enabled": True,
        },
    )

    assert created.status_code == 201
    body = created.json()
    assert body["profile_id"] == "greenhouse-normal"
    assert body["enabled"] is True
    profiles = client.get("/api/config/profiles").json()["items"]
    assert profiles[0]["desired_firmware"] == "1.0.0"
    assert profiles[0]["telemetry_interval_s"] == 60


def test_firmware_compatibility_is_read_only_and_actionable(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "firmware.db"))

    catalog = client.get("/api/firmware/compatibility")
    assert catalog.status_code == 200
    assert catalog.json()["items"][0]["minimum_firmware"] == "1.0.0"

    catalog_by_model = {
        item["hardware_model"]: item for item in catalog.json()["items"]
    }
    assert catalog_by_model["raspberry-pi-4"]["status"] == "validation_required"
    assert catalog_by_model["raspberry-pi-4"]["evidence_state"] == "verification_required"
    assert catalog_by_model["raspberry-pi-4"]["evidence_scope"] == "arm64_image_and_physical_device"
    assert catalog_by_model["raspberry-pi-5"]["status"] == "validation_required"
    assert catalog_by_model["radxa-rock-pi-4b-plus"]["status"] == "supported"
    assert catalog_by_model["radxa-rock-pi-4b-plus"]["evidence_state"] == "physical_device_validated"
    assert catalog_by_model["x86_64-edge"]["evidence_state"] == "runtime_smoke_validated"
    assert catalog_by_model["x86_64-edge"]["evidence_scope"] == "x86_64_runtime_smoke"
    compatible = client.post(
        "/api/firmware/compatibility",
        json={
            "hardware_model": "raspberry-pi-4",
            "firmware_version": "1.0.0",
            "target_runtime": "docker-edge",
        },
    )
    assert compatible.status_code == 200
    assert compatible.json()["compatible"] is False
    assert compatible.json()["risk_level"] == "review_required"

    human_label = client.post(
        "/api/firmware/compatibility",
        json={
            "hardware_model": "Raspberry Pi 4",
            "firmware_version": "1.0.0",
            "target_runtime": "docker-edge",
        },
    )
    assert human_label.status_code == 200
    assert human_label.json()["compatible"] is False
    assert human_label.json()["canonical_hardware_model"] == "raspberry-pi-4"

    radxa_label = client.post(
        "/api/firmware/compatibility",
        json={
            "hardware_model": "Radxa ROCK Pi 4B+",
            "firmware_version": "1.0.0",
            "target_runtime": "docker-edge",
        },
    )
    assert radxa_label.status_code == 200
    assert radxa_label.json()["canonical_hardware_model"] == "radxa-rock-pi-4b-plus"
    assert radxa_label.json()["compatible"] is True
    assert radxa_label.json()["evidence_state"] == "physical_device_validated"

    x86_64 = client.post(
        "/api/firmware/compatibility",
        json={
            "hardware_model": "x86_64-edge",
            "firmware_version": "1.0.0",
            "target_runtime": "docker-edge",
        },
    )
    assert x86_64.status_code == 200
    assert x86_64.json()["compatible"] is True
    assert x86_64.json()["risk_level"] == "low"
    assert x86_64.json()["evidence_state"] == "runtime_smoke_validated"
    assert x86_64.json()["evidence_scope"] == "x86_64_runtime_smoke"
    review = client.post(
        "/api/firmware/compatibility",
        json={
            "hardware_model": "raspberry-pi-4",
            "firmware_version": "0.9.4",
            "target_runtime": "docker-edge",
        },
    )
    assert review.status_code == 200
    assert review.json()["compatible"] is False
    assert review.json()["risk_level"] == "review_required"
    assert client.get("/api/config/profiles").json()["items"] == []


def test_firmware_drift_tracks_registered_device_against_enabled_profile(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "firmware-drift.db"))

    asset = client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={
            "asset_id": "line-1",
            "name": "Production Line 1",
            "location": "Plant A",
        },
    )
    assert asset.status_code == 201
    device = client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "controller-1",
            "name": "Controller 1",
            "adapter": "mqtt",
            "asset_id": "line-1",
            "firmware_version": "1.0.0",
        },
    )
    assert device.status_code == 201
    profile = client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "controller-1-policy",
            "name": "Controller 1 Policy",
            "asset_id": "line-1",
            "device_id": "controller-1",
            "desired_firmware": "1.0.0",
            "telemetry_interval_s": 60,
            "enabled": True,
        },
    )
    assert profile.status_code == 201

    aligned = client.get("/api/firmware/drift")
    assert aligned.status_code == 200
    assert aligned.json()["items"] == [
        {
            "device_id": "controller-1",
            "asset_id": "line-1",
            "profile_id": "controller-1-policy",
            "current_firmware": "1.0.0",
            "desired_firmware": "1.0.0",
            "status": "aligned",
            "action": "No firmware action required.",
        }
    ]

    upgraded_policy = client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "controller-1-policy",
            "name": "Controller 1 Policy",
            "asset_id": "line-1",
            "device_id": "controller-1",
            "desired_firmware": "1.1.0",
            "telemetry_interval_s": 60,
            "enabled": True,
        },
    )
    assert upgraded_policy.status_code == 201
    drift = client.get("/api/firmware/drift").json()["items"][0]
    assert drift["status"] == "upgrade_required"
    assert drift["current_firmware"] == "1.0.0"
    assert drift["desired_firmware"] == "1.1.0"

    updated_device = client.patch(
        "/api/devices/controller-1",
        headers=OPERATOR_HEADERS,
        json={"firmware_version": "1.1.0"},
    )
    assert updated_device.status_code == 200
    assert client.get("/api/firmware/drift").json()["items"][0]["status"] == "aligned"

    unmanaged = client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-unmanaged",
            "name": "Unmanaged Sensor",
            "adapter": "rest",
            "asset_id": "line-1",
            "firmware_version": "1.0.0",
        },
    )
    assert unmanaged.status_code == 201
    drift_by_device = {
        item["device_id"]: item
        for item in client.get("/api/firmware/drift").json()["items"]
    }
    assert drift_by_device["sensor-unmanaged"]["status"] == "unmanaged"

    invalid_profile = client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "sensor-unmanaged-policy",
            "name": "Sensor Policy",
            "asset_id": "line-1",
            "device_id": "sensor-unmanaged",
            "desired_firmware": "release-latest",
            "telemetry_interval_s": 60,
            "enabled": True,
        },
    )
    assert invalid_profile.status_code == 201
    drift_by_device = {
        item["device_id"]: item
        for item in client.get("/api/firmware/drift").json()["items"]
    }
    assert drift_by_device["sensor-unmanaged"]["status"] == "unknown"


def test_device_bound_firmware_check_rejects_conflicting_current_version(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "firmware-device-check.db"))
    created = client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "edge-1",
            "name": "Edge Runtime 1",
            "adapter": "mqtt",
            "firmware_version": "1.0.0",
        },
    )
    assert created.status_code == 201

    conflict = client.post(
        "/api/firmware/compatibility",
        json={
            "device_id": "edge-1",
            "hardware_model": "x86_64-edge",
            "firmware_version": "1.1.0",
            "target_runtime": "docker-edge",
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == (
        "Firmware request conflicts with the registered device version"
    )

    checked = client.post(
        "/api/firmware/compatibility",
        json={
            "device_id": "edge-1",
            "hardware_model": "x86_64-edge",
            "firmware_version": "1.0.0",
            "target_runtime": "docker-edge",
        },
    )
    assert checked.status_code == 200
    assert checked.json()["firmware_version"] == "1.0.0"
    assert checked.json()["compatible"] is True


def test_bounded_simulation_creates_stress_evidence_and_resets(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "simulation.db"))

    missing_auth = client.post(
        "/api/simulation/runs",
        json={"device_count": 2, "samples_per_device": 3},
    )
    assert missing_auth.status_code in {401, 503}

    response = client.post(
        "/api/simulation/runs",
        headers=OPERATOR_HEADERS,
        json={
            "device_count": 2,
            "samples_per_device": 3,
            "high_temperature_c": 88.0,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["bounded"] is True
    assert body["devices_created"] == 2
    assert body["config_profiles_created"] == 2
    assert body["telemetry_samples"] == 6
    assert body["alerts_created"] == 1
    assert body["recovery_proposals_created"] == 1
    assert body["stress_profile"]["max_telemetry_samples"] == 96
    runs = client.get("/api/simulation/runs").json()["items"]
    assert runs[0]["samples"] == 6
    summary = client.get("/api/operations/summary").json()
    assert summary["counters"]["simulation_runs"] == 1
    assert summary["counters"]["config_profiles"] == 2
    evidence = client.get("/api/operations/evidence", headers=OPERATOR_HEADERS).json()
    assert evidence["records"]["simulation_runs"][0]["alerts"] == 1

    reset = client.post(
        "/api/demo/reset",
        headers=OPERATOR_HEADERS,
        json={"confirmed_by": "operator"},
    )

    assert reset.status_code == 200
    assert client.get("/api/simulation/runs").json()["items"] == []


def test_hardware_simulator_plugin_is_disabled_by_default(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "sim-plugin-off.db"))

    status = client.get("/api/plugins/hardware-simulator/status")
    run = client.post(
        "/api/plugins/hardware-simulator/runs",
        headers=OPERATOR_HEADERS,
        json={"device_count": 1, "samples_per_device": 1},
    )

    assert status.status_code == 200
    assert status.json()["plugin"]["enabled"] is False
    assert status.json()["plugin"]["integration_mode"] == "sidecar_plugin"
    assert run.status_code == 409
    assert client.get("/api/devices").json()["items"] == []
    assert client.get("/api/telemetry").json()["items"] == []


def test_hardware_simulator_plugin_runs_through_hardware_interface(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", "enabled")
    client = TestClient(create_app(database_path=tmp_path / "sim-plugin-on.db"))

    catalog = client.get("/api/plugins/hardware-simulator/catalog")
    response = client.post(
        "/api/plugins/hardware-simulator/runs",
        headers=OPERATOR_HEADERS,
        json={
            "device_count": 2,
            "samples_per_device": 2,
            "profiles": ["greenhouse_temperature", "soil_moisture"],
        },
    )

    assert catalog.status_code == 200
    assert {item["profile_id"] for item in catalog.json()["items"]} >= {
        "greenhouse_temperature",
        "oxygen_concentration",
        "ambient_light",
        "motion_occupancy",
        "soil_moisture",
    }
    assert "raspberry-pi-5" in catalog.json()["interface"]["reference_boards"]
    assert "usb" in catalog.json()["interface"]["protocols"]
    assert response.status_code == 201
    body = response.json()
    assert body["plugin"]["enabled"] is True
    assert body["plugin"]["removable"] is True
    assert body["interface"]["write_path"] == "hardware_data_interface"
    assert body["devices_created"] == 2
    assert body["telemetry_samples"] == 4
    assert body["alerts_created"] == 1
    assert body["profile_coverage"] == ["greenhouse_temperature", "soil_moisture"]
    assert body["requested_profiles"] == ["greenhouse_temperature", "soil_moisture"]
    assert body["ignored_profiles"] == []
    assert body["fallback_profile_applied"] is False
    assert all(
        endpoint in body["interface"]["adapter_endpoints"]
        for endpoint in ["/api/devices", "/api/telemetry"]
    )
    assert client.get("/api/devices").json()["items"][0]["adapter"] == "simulator"
    runs = client.get("/api/plugins/hardware-simulator/runs").json()["items"]
    assert runs[0]["simulation_id"] == body["simulation_id"]


def test_hardware_simulator_reports_ignored_unknown_profiles(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", "enabled")
    client = TestClient(create_app(database_path=tmp_path / "sim-profile-gap.db"))

    response = client.post(
        "/api/plugins/hardware-simulator/runs",
        headers=OPERATOR_HEADERS,
        json={
            "device_count": 2,
            "samples_per_device": 1,
            "profiles": [
                "greenhouse_temperature",
                "oxygen_level",
                "oxygen_concentration",
            ],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["profile_coverage"] == [
        "greenhouse_temperature",
        "oxygen_concentration",
    ]
    assert body["requested_profiles"] == [
        "greenhouse_temperature",
        "oxygen_level",
        "oxygen_concentration",
    ]
    assert body["ignored_profiles"] == ["oxygen_level"]
    assert body["fallback_profile_applied"] is False
    runs = client.get("/api/plugins/hardware-simulator/runs").json()["items"]
    assert runs[0]["ignored_profiles"] == "oxygen_level"


def test_cmdb_auto_discovers_sensor_configuration_items(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", "enabled")
    client = TestClient(create_app(database_path=tmp_path / "cmdb-auto.db"))

    client.post(
        "/api/plugins/hardware-simulator/runs",
        headers=OPERATOR_HEADERS,
        json={
            "device_count": 3,
            "samples_per_device": 2,
            "profiles": [
                "greenhouse_temperature",
                "oxygen_concentration",
                "motion_occupancy",
            ],
        },
    )

    response = client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["auto_discovered"] >= 3
    assert body["summary"]["sensor_count"] >= 3
    assert body["summary"]["sensor_auto_discovered"] >= 3
    management = body["management_summary"]
    assert management["sensor_count"] >= 3
    assert management["auto_discovered_sensor_count"] >= 3
    assert management["validated_sensor_count"] == 0
    assert management["validation_coverage_percent"] == 0
    assert management["readiness_state"] == "partial_hardware_evidence"
    assert management["customer_safe"] is True
    assert {"usb", "i2c"}.issubset(set(management["supported_protocol_families"]))
    management_text = json.dumps(management, sort_keys=True)
    for restricted in ("vendor_id", "product_id", "driver", "hardware_signature"):
        assert restricted not in management_text
    assert body["discovery_policy"]["usb_supported"] is True
    items = {item["ci_id"]: item for item in body["items"]}
    sensor_items = [item for item in items.values() if item["ci_type"] == "sensor"]
    assert sensor_items
    assert {item["metric"] for item in sensor_items} >= {
        "temperature_c",
        "oxygen_pct",
        "occupancy_state",
    }
    assert all(item["asset_id"] == "hardware-simulator-lab" for item in sensor_items)
    assert all(item["discovery_source"] == "hardware_data_interface" for item in sensor_items)
    assert any("usb" in item["protocols"] for item in sensor_items)
    assert body["relations"][0]["relation_type"] == "contains"


def test_hardware_discovery_overview_summarizes_cmdb_and_plugins(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", "enabled")
    client = TestClient(create_app(database_path=tmp_path / "hardware-overview.db"))

    client.post(
        "/api/plugins/hardware-simulator/runs",
        headers=OPERATOR_HEADERS,
        json={
            "device_count": 2,
            "samples_per_device": 1,
            "profiles": ["greenhouse_temperature", "oxygen_concentration"],
        },
    )

    response = client.get("/api/hardware/discovery", headers=OPERATOR_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["summary"]["profile_count"] >= 6
    assert body["summary"]["sensor_count"] >= 2
    assert body["summary"]["auto_discovered_sensor_count"] >= 2
    assert body["summary"]["readiness_state"] == "partial_hardware_evidence"
    assert body["plugin"]["hardware_simulator"]["integration_mode"] == "sidecar_plugin"
    assert body["plugin"]["usb_discovery"]["core_embedded"] is False
    assert "usb" in body["supported"]["protocols"]
    assert "raspberry-pi-5" in body["supported"]["boards"]
    assert body["workflow"]["catalog_endpoint"] == "/api/hardware/discovery/profiles"
    assert body["workflow"]["cmdb_endpoint"] == "/api/cmdb/configuration-items"
    assert body["privacy"]["customer_safe"] is True
    assert body["privacy"]["serial_numbers_returned"] is False
    assert body["privacy"]["secret_values_returned"] is False
    assert "raw_serial" not in response.text.lower()
    assert "serial-redaction-fixture-value" not in response.text
    assert "vendor_id" not in response.text
    assert "product_id" not in response.text


def test_cmdb_rejects_metric_only_sensor_spoofing(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "cmdb-spoof.db"))

    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "lab-a", "name": "Lab A"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "generic-usb-1",
            "name": "Generic USB bridge",
            "adapter": "usb",
            "asset_id": "lab-a",
        },
    )
    client.post(
        "/api/config/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "profile_id": "generic-usb-1-profile",
            "name": "Generic USB profile",
            "asset_id": "lab-a",
            "device_id": "generic-usb-1",
        },
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "generic-usb-1",
            "metric": "temperature_c",
            "value": 24.0,
            "unit": "C",
        },
    )

    body = client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()
    device_ci = next(
        item for item in body["items"] if item["ci_id"] == "device:generic-usb-1"
    )

    assert device_ci["ci_type"] == "device"
    assert device_ci["auto_discovered"] is False
    assert device_ci["protocols"] == []
    assert device_ci["standards"] == []
    assert body["summary"]["sensor_auto_discovered"] == 0
    assert body["discovery_policy"]["usb_supported"] is False


def test_cmdb_management_summary_handles_empty_hardware_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "cmdb-management-empty.db"))

    response = client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    management = body["management_summary"]
    assert management["asset_count"] == 0
    assert management["device_count"] == 0
    assert management["sensor_count"] == 0
    assert management["validated_sensor_count"] == 0
    assert management["validation_coverage_percent"] == 0
    assert management["readiness_state"] == "no_sensor_evidence"
    assert "Register or approve sensor evidence" in management["next_action"]
    management_text = json.dumps(management, sort_keys=True)
    for restricted in ("vendor_id", "product_id", "driver", "interface_classes"):
        assert restricted not in management_text



def test_hardware_discovery_profile_catalog_lists_allowlisted_standards(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-profile-catalog.db"))

    response = client.get("/api/hardware/discovery/profiles", headers=OPERATOR_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["summary"]["profile_count"] >= 6
    assert body["policy"]["registration_endpoint"] == "/api/hardware/discovery/candidates"
    assert body["policy"]["cmdb_target"] == "/api/cmdb/configuration-items"
    assert body["policy"]["requires_operator_approval"] is True
    assert body["policy"]["direct_import_scopes"] == [
        "recovery:approve",
        "device:write",
    ]
    profile = next(item for item in body["items"] if item["profile_id"] == "greenhouse_temperature")
    assert "usb" in profile["protocols"]
    assert "Matter Temperature Sensor" in profile["standards"]
    assert "raspberry-pi-4" in profile["boards"]
    onboard_thermal = next(
        item
        for item in body["items"]
        if item["profile_id"] == "linux_onboard_thermal"
    )
    assert onboard_thermal["metric"] == "temperature_c"
    assert "linux-sysfs" in onboard_thermal["protocols"]
    assert "radxa-rock-pi-4b-plus" in onboard_thermal["boards"]
    assert "serial" not in response.text.lower()
    sensor_profiles = [item for item in body["items"] if item["device_kind"] == "sensor"]
    assert sensor_profiles
    assert all(
        {"raspberry-pi-4", "raspberry-pi-5", "x86_64-edge"}.issubset(item["boards"])
        for item in sensor_profiles
    )


def test_direct_hardware_inventory_import_requires_explicit_approval(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-import-gate.db"))

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "usb-gated-1",
            "profile_id": "greenhouse_temperature",
            "name": "USB Gated Probe",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Matter Temperature Sensor"],
            "hardware_model": "raspberry-pi-4",
            "metric": "temperature_c",
            "value": 24.2,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Explicit Asset Inventory import confirmation is required"
    )
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []
    assert client.get("/api/telemetry").json()["items"] == []


def test_onboard_linux_thermal_profile_creates_validated_cmdb_sensor(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "onboard-thermal.db"))
    registered_asset = client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={
            "asset_id": "greenovax-edge-201",
            "name": "GreeNovaX edge node",
            "location": "Hardware qualification bench",
        },
    )
    assert registered_asset.status_code == 201

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "rockpi-edge-201",
            "profile_id": "linux_onboard_thermal",
            "name": "Edge onboard thermal sensor",
            "asset_id": "greenovax-edge-201",
            "asset_name": "GreeNovaX edge node",
            "adapter": "rest",
            "protocols": ["rest"],
            "standards": ["Linux thermal sysfs"],
            "hardware_model": "Radxa ROCK Pi 4B+",
            "firmware_version": "1.0.0",
            "metric": "temperature_c",
            "value": 52.78,
            "unit": "C",
            "confirm_inventory_import": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["hardware_evidence"]["hardware_model"] == "radxa-rock-pi-4b-plus"
    assert body["hardware_evidence"]["profile_id"] == "linux_onboard_thermal"
    assert body["asset"]["location"] == "Hardware qualification bench"
    cmdb = body["cmdb"]
    assert cmdb["summary"]["sensor_auto_discovered"] == 1
    sensor = next(item for item in cmdb["items"] if item["ci_type"] == "sensor")
    assert sensor["protocols"] == ["rest"]
    assert sensor["hardware_profile"] == "radxa-rock-pi-4b-plus"


def test_direct_hardware_inventory_import_requires_device_write_scope(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "hardware-import-scope.db"))
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="hardware-approver",
        role="operator",
        scopes=["recovery:approve"],
    )
    token = make_test_jwt(
        subject="hardware-approver",
        role="operator",
        scope="recovery:approve",
    )

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "confirm_inventory_import": True,
            "device_id": "usb-scope-gated-1",
            "profile_id": "greenhouse_temperature",
            "name": "USB Scope Gated Probe",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Matter Temperature Sensor"],
            "hardware_model": "raspberry-pi-4",
            "metric": "temperature_c",
            "value": 24.2,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Scope required: device:write"
    assert client.get("/api/assets").json()["items"] == []


def test_hardware_discovery_profile_registers_usb_sensor_in_cmdb(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-discovery.db"))

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "confirm_inventory_import": True,
            "device_id": "usb-temp-1",
            "profile_id": "greenhouse_temperature",
            "name": "USB Temperature Probe 1",
            "asset_id": "greenhouse-usb-line",
            "asset_name": "Greenhouse USB Line",
            "adapter": "usb",
            "protocols": ["usb", "i2c"],
            "standards": ["Matter Temperature Sensor", "MQTT 5 telemetry"],
            "hardware_model": "raspberry-pi-4",
            "firmware_version": "lab-1.0.0",
            "metric": "temperature_c",
            "value": 24.2,
            "unit": "C",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "registered"
    assert body["asset"]["asset_id"] == "greenhouse-usb-line"
    assert body["device"]["adapter"] == "usb"
    assert body["telemetry"]["accepted"] is True
    assert body["cmdb"]["summary"]["sensor_auto_discovered"] == 1
    sensor_ci = next(
        item for item in body["cmdb"]["items"] if item["ci_id"] == "device:usb-temp-1"
    )
    assert sensor_ci["ci_type"] == "sensor"
    assert sensor_ci["asset_id"] == "greenhouse-usb-line"
    assert sensor_ci["discovery_source"] == "hardware_data_interface"
    assert "usb" in sensor_ci["protocols"]



def test_hardware_discovery_profile_accepts_x86_64_integration_board(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-discovery-x86.db"))

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "confirm_inventory_import": True,
            "device_id": "x86-temp-1",
            "profile_id": "greenhouse_temperature",
            "name": "x86 Integration Temperature Probe",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Matter Temperature Sensor"],
            "hardware_model": "x86_64-edge",
            "firmware_version": "lab-1.0.0",
            "metric": "temperature_c",
            "value": 24.2,
            "unit": "C",
        },
    )

    assert response.status_code == 201
def test_hardware_discovery_profile_validates_usb_descriptor_evidence(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-usb-evidence.db"))

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "confirm_inventory_import": True,
            "device_id": "usb-temp-descriptor-1",
            "profile_id": "greenhouse_temperature",
            "name": "USB Temperature Probe 1",
            "asset_id": "greenhouse-usb-descriptor-line",
            "asset_name": "Greenhouse USB Descriptor Line",
            "adapter": "usb",
            "protocols": ["usb", "i2c"],
            "standards": ["Matter Temperature Sensor", "MQTT 5 telemetry"],
            "hardware_model": "raspberry-pi-5",
            "firmware_version": "lab-1.0.0",
            "metric": "temperature_c",
            "value": 24.4,
            "unit": "C",
            "standard_descriptors": {
                "usb": {
                    "device_class": "0x03",
                    "driver": "usbhid",
                    "manufacturer": "Lab Vendor",
                    "product": "Greenhouse Temperature USB Probe",
                    "vendor_id": "2e8a",
                    "product_id": "000a",
                    "serial_number": "serial-redaction-fixture-value",
                }
            },
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert "serial-redaction-fixture-value" not in response.text
    assert body["profile"]["descriptor_validated"] is True
    usb = body["profile"]["validated_standard_descriptors"]["usb"]
    assert usb["device_class"] == "hid"
    assert usb["serial_redacted"] is True
    assert usb["vendor_id"] == "2e8a"
    sensor_ci = next(
        item
        for item in body["cmdb"]["items"]
        if item["ci_id"] == "device:usb-temp-descriptor-1"
    )
    assert sensor_ci["ci_type"] == "sensor"
    assert sensor_ci["standard_descriptor_validated"] is True
    assert sensor_ci["hardware_signature"]["usb"]["product_id"] == "000a"
    management = body["cmdb"]["management_summary"]
    assert management["validated_sensor_count"] == 1
    assert management["validation_coverage_percent"] == 100
    assert management["readiness_state"] == "hardware_evidence_ready"
    management_text = json.dumps(management, sort_keys=True)
    for restricted in ("vendor_id", "product_id", "driver", "hardware_signature"):
        assert restricted not in management_text
    assert body["cmdb"]["discovery_policy"]["standard_descriptor_supported"] is True


def test_hardware_discovery_candidate_requires_approval_before_cmdb_promotion(
    tmp_path, monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "hardware-candidate.db"))
    payload = {
        "device_id": "usb-temp-candidate-1",
        "profile_id": "greenhouse_temperature",
        "name": "USB Temperature Candidate 1",
        "asset_id": "candidate-greenhouse",
        "asset_name": "Candidate Greenhouse",
        "adapter": "usb",
        "protocols": ["usb", "i2c"],
        "standards": ["Matter Temperature Sensor", "MQTT 5 telemetry"],
        "hardware_model": "raspberry-pi-5",
        "firmware_version": "lab-1.0.0",
        "metric": "temperature_c",
        "value": 24.5,
        "unit": "C",
        "standard_descriptors": {
            "usb": {
                "device_class": "0x03",
                "driver": "usbhid",
                "manufacturer": "Lab Vendor",
                "product": "Greenhouse Temperature USB Probe",
                "vendor_id": "2e8a",
                "product_id": "000a",
                "serial_number": "serial-redaction-fixture-value",
            }
        },
    }

    queued = client.post(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        json={**payload, "confirm_inventory_import": True},
    )

    assert queued.status_code == 201
    assert "serial-redaction-fixture-value" not in queued.text
    candidate = queued.json()["candidate"]
    assert candidate["status"] == "queued"
    assert candidate["device_id"] == "usb-temp-candidate-1"
    assert candidate["asset_id"] == "candidate-greenhouse"
    assert candidate["descriptor_validated"] is True
    assert candidate["evidence_fingerprint"].startswith("sha256:")
    assert candidate["created_by"] == "redacted"
    assert candidate["approval_endpoint"].endswith("/approve")
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0

    queue = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
    ).json()
    assert queue["summary"]["queued_count"] == 1
    assert queue["policy"]["workflow"] == "validate_queue_approve_promote"
    assert queue["policy"]["approval_scopes"] == [
        "recovery:approve",
        "device:write",
    ]
    assert "serial-redaction-fixture-value" not in str(queue)

    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="candidate-reviewer",
        role="operator",
        scopes=["device:write"],
    )
    device_only_token = make_test_jwt(
        subject="candidate-reviewer",
        role="operator",
        scope="device:write",
    )
    weak_approval = client.post(
        candidate["approval_endpoint"],
        headers={"Authorization": f"Bearer {device_only_token}"},
        json={},
    )
    assert weak_approval.status_code == 403
    assert weak_approval.json()["detail"] == "Scope required: recovery:approve"
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0

    stale_approval = client.post(
        candidate["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": "sha256:" + ("0" * 64),
        },
    )
    assert stale_approval.status_code == 409
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0

    approved = client.post(
        candidate["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": candidate["evidence_fingerprint"],
        },
    )

    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved"
    assert body["candidate"]["status"] == "approved"
    assert body["candidate"]["approved_by"] == "redacted"
    assert body["registration"]["cmdb"]["summary"]["sensor_auto_discovered"] == 1
    assert body["registration"]["hardware_evidence"]["descriptor_validated"] is True
    assert "serial-redaction-fixture-value" not in approved.text
    telemetry_count = len(client.get("/api/telemetry").json()["items"])

    second_approval = client.post(
        candidate["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": candidate["evidence_fingerprint"],
        },
    )
    assert second_approval.status_code == 200
    assert second_approval.json()["status"] == "already_approved"
    assert len(client.get("/api/telemetry").json()["items"]) == telemetry_count

    requeue = client.post(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        json=payload,
    )
    assert requeue.status_code == 201
    assert requeue.json()["status"] == "already_approved"
    assert len(client.get("/api/telemetry").json()["items"]) == telemetry_count


def test_hardware_discovery_candidate_rejects_invalid_telemetry_before_write(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-candidate-invalid.db"))

    response = client.post(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "usb-temp-invalid",
            "profile_id": "greenhouse_temperature",
            "name": "Invalid Temperature Candidate",
            "asset_id": "invalid-greenhouse",
            "asset_name": "Invalid Greenhouse",
            "adapter": "usb",
            "protocols": ["usb", "i2c"],
            "standards": ["Matter Temperature Sensor", "MQTT 5 telemetry"],
            "hardware_model": "raspberry-pi-5",
            "metric": "temperature_c",
            "value": 250.0,
            "unit": "C",
            "standard_descriptors": {
                "usb": {
                    "device_class": "0x03",
                    "driver": "usbhid",
                    "product": "Greenhouse Temperature USB Probe",
                }
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Telemetry value outside supported range"
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []
    assert client.get("/api/telemetry").json()["items"] == []
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0


def test_hardware_discovery_candidate_blocks_unauthorized_writes(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-candidate-auth.db"))

    response = client.post(
        "/api/hardware/discovery/candidates",
        json={
            "device_id": "usb-temp-blocked",
            "profile_id": "greenhouse_temperature",
            "name": "Blocked USB Probe",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Matter Temperature Sensor"],
            "hardware_model": "raspberry-pi-4",
            "metric": "temperature_c",
            "value": 24.0,
        },
    )

    assert response.status_code == 401
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0


def test_usb_discovery_status_is_customer_safe_and_read_only(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AGENTIOT_USB_DISCOVERY_PLUGIN", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "usb-status.db"))

    response = client.get(
        "/api/hardware/discovery/usb/status",
        headers=OPERATOR_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["plugin"]["plugin_id"] == "usb-standard-discovery"
    assert body["plugin"]["enabled"] is False
    assert body["plugin"]["core_embedded"] is False
    assert body["source"]["raw_serial_storage"] is False
    assert body["source"]["registers_directly"] is False
    assert body["interface"]["status_endpoint"] == "/api/hardware/discovery/usb/status"
    assert body["interface"]["cmdb_target"] == "/api/cmdb/configuration-items"
    assert "serial-redaction-fixture-value" not in response.text
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0


def test_usb_sysfs_discovery_preview_is_disabled_by_default(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AGENTIOT_USB_DISCOVERY_PLUGIN", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "usb-sysfs-disabled.db"))

    response = client.get(
        "/api/hardware/discovery/usb/sysfs",
        headers=OPERATOR_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"
    assert body["registration_previews"] == []
    assert body["summary"]["raw_serial_storage"] is False


def test_usb_sysfs_discovery_preview_builds_cmdb_registration_payload(
    tmp_path,
    monkeypatch,
) -> None:
    sysfs_root = tmp_path / "sysfs-usb"
    device = sysfs_root / "1-1"
    interface = device / "1-1:1.0"
    interface.mkdir(parents=True)
    (device / "idVendor").write_text("2e8a\n", encoding="utf-8")
    (device / "idProduct").write_text("000a\n", encoding="utf-8")
    (device / "bDeviceClass").write_text("00\n", encoding="utf-8")
    (device / "manufacturer").write_text("Lab Vendor\n", encoding="utf-8")
    (device / "product").write_text(
        "Greenhouse Temperature USB Probe\n", encoding="utf-8"
    )
    (device / "serial").write_text("serial-redaction-fixture-value\n", encoding="utf-8")
    (interface / "bInterfaceClass").write_text("03\n", encoding="utf-8")
    driver_root = sysfs_root / "drivers" / "usbhid"
    driver_root.mkdir(parents=True)
    (interface / "driver").symlink_to(driver_root, target_is_directory=True)
    monkeypatch.setenv("AGENTIOT_USB_DISCOVERY_PLUGIN", "enabled")
    monkeypatch.setenv("AGENTIOT_USB_SYSFS_ROOT", str(sysfs_root))
    client = TestClient(create_app(database_path=tmp_path / "usb-sysfs.db"))

    response = client.get(
        "/api/hardware/discovery/usb/sysfs",
        headers=OPERATOR_HEADERS,
        params={"asset_id": "edge-usb-lab", "hardware_model": "raspberry-pi-5"},
    )

    assert response.status_code == 200
    assert "serial-redaction-fixture-value" not in response.text
    body = response.json()
    assert body["summary"]["usb_devices_seen"] == 1
    assert body["summary"]["matched_profiles"] == 1
    assert body["items"][0]["serial_redacted"] is True
    assert "bInterfaceClass" in body["source"]["evidence_fields"]
    assert "driver" in body["source"]["evidence_fields"]
    payload = body["registration_previews"][0]
    assert payload["profile_id"] == "greenhouse_temperature"
    assert payload["adapter"] == "usb"
    assert payload["standard_descriptors"]["usb"]["vendor_id"] == "2e8a"
    assert payload["standard_descriptors"]["usb"]["device_class"] == "03"
    assert payload["standard_descriptors"]["usb"]["driver"] == "usbhid"
    assert payload["standard_descriptors"]["usb"]["interfaces"] == ["usbhid"]
    assert payload["standard_descriptors"]["usb"]["interface_classes"] == ["03"]

    registered = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={**payload, "confirm_inventory_import": True},
    )

    assert registered.status_code == 201
    cmdb = registered.json()["cmdb"]
    assert cmdb["summary"]["sensor_auto_discovered"] == 1
    sensor_ci = next(
        item
        for item in cmdb["items"]
        if item["asset_id"] == "edge-usb-lab" and item["ci_type"] == "sensor"
    )
    assert sensor_ci["standard_descriptor_validated"] is True
    assert sensor_ci["hardware_signature"]["usb"]["device_class"] == "hid"



def test_usb_sysfs_discovery_unmatched_preview_does_not_mutate_cmdb(
    tmp_path, monkeypatch
) -> None:
    sysfs_root = tmp_path / "sysfs-usb-unmatched"
    device = sysfs_root / "1-2"
    interface = device / "1-2:1.0"
    interface.mkdir(parents=True)
    (device / "idVendor").write_text("046d\n", encoding="utf-8")
    (device / "idProduct").write_text("c31c\n", encoding="utf-8")
    (device / "bDeviceClass").write_text("00\n", encoding="utf-8")
    (device / "manufacturer").write_text("Lab Vendor\n", encoding="utf-8")
    (device / "product").write_text("Generic Keyboard\n", encoding="utf-8")
    (device / "serial").write_text("serial-redaction-fixture-value\n", encoding="utf-8")
    (interface / "bInterfaceClass").write_text("03\n", encoding="utf-8")
    monkeypatch.setenv("AGENTIOT_USB_DISCOVERY_PLUGIN", "enabled")
    monkeypatch.setenv("AGENTIOT_USB_SYSFS_ROOT", str(sysfs_root))
    client = TestClient(create_app(database_path=tmp_path / "usb-sysfs-unmatched.db"))

    response = client.get("/api/hardware/discovery/usb/sysfs", headers=OPERATOR_HEADERS)

    assert response.status_code == 200
    assert "serial-redaction-fixture-value" not in response.text
    body = response.json()
    assert body["summary"]["usb_devices_seen"] == 1
    assert body["summary"]["matched_profiles"] == 0
    assert body["registration_previews"] == []
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []
    assert client.get("/api/config/profiles").json()["items"] == []
    assert client.get("/api/telemetry").json()["items"] == []
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0


def test_hardware_discovery_profile_rejects_usb_descriptor_mismatch(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-usb-mismatch.db"))

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "confirm_inventory_import": True,
            "device_id": "usb-temp-mismatch-1",
            "profile_id": "greenhouse_temperature",
            "name": "USB Probe With Wrong Descriptor",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Matter Temperature Sensor"],
            "hardware_model": "raspberry-pi-4",
            "metric": "temperature_c",
            "value": 24.0,
            "standard_descriptors": {
                "usb": {
                    "device_class": "0x03",
                    "driver": "usbhid",
                    "product": "Motion Occupancy USB Probe",
                }
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "USB descriptor does not match hardware profile"
    assert client.get("/api/devices").json()["items"] == []


def test_hardware_discovery_profile_rejects_unmatched_standard_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-discovery-bad.db"))

    response = client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "confirm_inventory_import": True,
            "device_id": "usb-temp-2",
            "profile_id": "greenhouse_temperature",
            "name": "Untrusted USB Temperature Probe",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Unknown vendor profile"],
            "hardware_model": "raspberry-pi-4",
            "firmware_version": "lab-1.0.0",
            "metric": "temperature_c",
            "value": 24.0,
            "unit": "C",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Matching standard evidence required"
    assert client.get("/api/devices").json()["items"] == []
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()["summary"]["ci_count"] == 0


def test_hardware_simulator_plugin_run_is_blocked_in_production(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_HARDWARE_SIMULATOR_PLUGIN", "enabled")
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    strong_operator_token = "simulator-production-operator-" + ("a" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", strong_operator_token)
    app = create_app(database_path=tmp_path / "sim-plugin-prod.db")
    client = TestClient(app)

    response = client.post(
        "/api/plugins/hardware-simulator/runs",
        headers={"X-Operator-Token": strong_operator_token},
        json={"device_count": 1, "samples_per_device": 1},
    )

    assert response.status_code == 403
    assert app.state.store.list_rows("devices") == []


def test_operations_summary_tracks_alert_and_recovery_state(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "summary-active.db"))
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "greenhouse-1", "name": "Greenhouse Zone 1"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "name": "Sensor 1",
            "adapter": "mqtt",
            "asset_id": "greenhouse-1",
        },
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-1", "metric": "temperature_c", "value": 88.0},
    )
    client.post(
        "/api/adapters/mqtt/messages",
        headers=OPERATOR_HEADERS,
        json={
            "topic": "agentiot/sensor-1/telemetry",
            "payload": '{"metric":"temperature_c","value":82,"unit":"C"}',
        },
    )

    response = client.get("/api/operations/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["operational_state"] == "operator_action_required"
    assert body["phase_readiness_score"] >= 85
    assert body["counters"]["assets"] == 1
    assert body["counters"]["devices"] == 1
    assert body["counters"]["telemetry"] == 2
    assert body["counters"]["open_alerts"] == 1
    assert body["counters"]["pending_recovery"] == 1
    assert body["counters"]["audit_events"] == 4
    assert body["current_risk"]["severity"] == "critical"
    assert body["current_risk"]["device_id"] == "sensor-1"
    assert body["latest_telemetry"]["metric"] == "temperature_c"
    assert body["last_audit_event"]["event_type"] == "mqtt.telemetry.accepted"


def test_next_best_action_prioritizes_live_incident(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "next-action.db"))
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "greenhouse-1", "name": "Greenhouse Zone 1"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-1",
            "name": "Sensor 1",
            "adapter": "mqtt",
            "asset_id": "greenhouse-1",
        },
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-1", "metric": "temperature_c", "value": 88.0},
    )

    response = client.get("/api/operations/next-best-action")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "action_required"
    assert body["priority"] == "P0"
    assert body["owner_agent_id"] == "alert_recovery_agent"
    assert body["incident"]["device_id"] == "sensor-1"
    assert body["incident"]["severity"] == "critical"
    assert body["requires_human_approval"] is True
    assert body["primary_action"]["label"] == "Open recovery approval"
    assert body["primary_action"]["endpoint"].startswith("/api/recovery/proposals/")
    assert body["secondary_action"]["endpoint"] == "/api/operations/command-center"
    assert "/api/telemetry" in body["evidence_endpoints"]
    assert body["quality_gates"]["raw_payload_returned"] is False
    assert body["quality_gates"]["secret_values_returned"] is False


def test_next_best_action_opens_asset_setup_without_live_records(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "next-action-setup.db"))

    response = client.get("/api/operations/next-best-action")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Operations setup required"
    assert body["primary_action"]["label"] == "Open Asset Setup"
    assert body["primary_action"]["endpoint"] == "/operations"


def test_alert_resolution_closes_alert_and_writes_audit(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "resolve-alert.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-resolve", "name": "Resolve Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-resolve",
            "metric": "temperature_c",
            "value": 88.0,
        },
    )
    alert_id = client.get("/api/alerts").json()["items"][0]["alert_id"]

    response = client.post(
        f"/api/alerts/{alert_id}/resolve",
        headers=OPERATOR_HEADERS,
        json={
            "resolved_by": "spoofed-admin",
            "resolution_note": "Cooling and sensor placement checked.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["alert_id"] == alert_id
    assert body["status"] == "resolved"
    assert body["audit_id"].startswith("audit-event-")
    alerts = client.get("/api/alerts").json()["items"]
    assert alerts[0]["status"] == "resolved"
    audit = client.get("/api/audit/events", headers=OPERATOR_HEADERS).json()["items"]
    assert audit[-1]["event_type"] == "alert.resolved"
    assert audit[-1]["actor"] == "operator"
    assert "spoofed-admin" not in str(audit[-1])
    summary = client.get("/api/operations/summary").json()
    assert summary["counters"]["open_alerts"] == 0


def test_operations_evidence_exports_customer_safe_records(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "evidence.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-evidence", "name": "Evidence Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-evidence",
            "metric": "temperature_c",
            "value": 88.0,
        },
    )

    response = client.get("/api/operations/evidence", headers=OPERATOR_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["product"] == "AgentIoT Dashboard"
    assert body["license"] == "MIT"
    assert body["clean_room"] is True
    assert body["runtime"]["operator_write_gate"] is True
    assert body["summary"]["counters"]["devices"] == 1
    assert body["records"]["alerts"][0]["severity"] == "critical"
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_demo_reset_clears_bounded_runtime_records(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "reset.db"))
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "greenhouse-reset", "name": "Reset Greenhouse"},
    )
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-reset",
            "name": "Reset Sensor",
            "asset_id": "greenhouse-reset",
        },
    )

    response = client.post(
        "/api/demo/reset",
        headers=OPERATOR_HEADERS,
        json={"confirmed_by": "operator"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reset"
    assert body["deleted_records"] == 4
    assert body["audit_event_id"] == 3
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []
    audit = client.get("/api/audit/events").json()["items"]
    assert audit[0]["event_type"] == "demo.reset"


def test_recovery_actions_require_human_approval_and_are_audited(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "approval.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-2", "name": "Sensor 2"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-2", "metric": "temperature_c", "value": 91.0},
    )
    proposal_id = client.get("/api/recovery/proposals").json()["items"][0]["proposal_id"]

    approval_response = client.post(
        f"/api/recovery/proposals/{proposal_id}/approve",
        headers=OPERATOR_HEADERS,
        json={"approved_by": "spoofed-admin"},
    )

    assert approval_response.status_code == 200
    body = approval_response.json()
    assert body["proposal_id"] == proposal_id
    assert body["status"] == "approved"
    assert body["approved_by"] == "operator"
    assert body["audit_id"].startswith("audit-")
    audit = client.get("/api/audit/events", headers=OPERATOR_HEADERS).json()["items"]
    assert audit[-1]["actor"] == "operator"
    assert "spoofed-admin" not in str(audit[-1])

    proposals = client.get("/api/recovery/proposals").json()["items"]
    assert proposals[0]["status"] == "approved"
    alerts = client.get("/api/alerts").json()["items"]
    assert alerts[0]["status"] == "resolved"


def test_concurrent_recovery_approval_has_exactly_one_winner(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "approval-race.db")
    client = TestClient(app)
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-race", "name": "Race Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-race", "metric": "temperature_c", "value": 91.0},
    )
    proposal_id = client.get("/api/recovery/proposals").json()["items"][0][
        "proposal_id"
    ]
    store = app.state.store
    worker_count = 12
    barrier = Barrier(worker_count)

    def approve(index: int) -> dict:
        barrier.wait()
        return store.approve_proposal(
            proposal_id,
            ApprovalRequest(approved_by=f"operator-{index}"),
        )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(executor.map(approve, range(worker_count)))

    approved_by = {item["approved_by"] for item in results}
    audit_ids = {item["audit_id"] for item in results}
    with store.connect() as connection:
        audits = connection.execute(
            "SELECT actor, detail FROM audit_events "
            "WHERE event_type = 'recovery.approved' AND subject_id = ?",
            (proposal_id,),
        ).fetchall()
        alert_status = connection.execute(
            "SELECT status FROM alerts WHERE alert_id = "
            "(SELECT alert_id FROM recovery_proposals WHERE proposal_id = ?)",
            (proposal_id,),
        ).fetchone()["status"]
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]

    assert len(approved_by) == 1
    assert len(audit_ids) == 1
    assert len(audits) == 1
    assert audits[0]["actor"] == next(iter(approved_by))
    assert audits[0]["detail"] == next(iter(audit_ids))
    assert alert_status == "resolved"
    assert quick_check == "ok"


def test_recovery_approval_rolls_back_when_audit_insert_fails(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "approval-rollback.db")
    client = TestClient(app)
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-rollback", "name": "Rollback Sensor"},
    )
    client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "sensor-rollback",
            "metric": "temperature_c",
            "value": 91.0,
        },
    )
    proposal_id = client.get("/api/recovery/proposals").json()["items"][0][
        "proposal_id"
    ]
    store = app.state.store
    with store.connect() as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_recovery_audit
            BEFORE INSERT ON audit_events
            WHEN NEW.event_type = 'recovery.approved'
            BEGIN
              SELECT RAISE(ABORT, 'forced recovery audit failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        store.approve_proposal(
            proposal_id,
            ApprovalRequest(approved_by="operator-failure"),
        )

    with store.connect() as connection:
        proposal = connection.execute(
            "SELECT * FROM recovery_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        alert = connection.execute(
            "SELECT status FROM alerts WHERE alert_id = ?",
            (proposal["alert_id"],),
        ).fetchone()
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type = 'recovery.approved'"
        ).fetchone()[0]
        connection.execute("DROP TRIGGER fail_recovery_audit")

    assert proposal["status"] == "pending_approval"
    assert proposal["approved_by"] is None
    assert proposal["approved_at"] is None
    assert proposal["audit_id"] is None
    assert alert["status"] == "open"
    assert audit_count == 0

    approved = store.approve_proposal(
        proposal_id,
        ApprovalRequest(approved_by="operator-retry"),
    )
    replayed = store.approve_proposal(
        proposal_id,
        ApprovalRequest(approved_by="operator-loser"),
    )
    with store.connect() as connection:
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE event_type = 'recovery.approved'"
        ).fetchone()[0]
    assert approved["approved_by"] == "operator-retry"
    assert replayed["approved_by"] == "operator-retry"
    assert replayed["audit_id"] == approved["audit_id"]
    assert audit_count == 1


def test_unknown_device_telemetry_fails_safely(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "unknown.db"))

    response = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "missing", "metric": "temperature_c", "value": 20.0},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Device not registered"


def test_telemetry_rejects_unknown_metric_impossible_values_and_wrong_unit(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "telemetry-validation.db"))
    client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={"device_id": "sensor-validation", "name": "Validation Sensor"},
    )

    invalid_samples = [
        ({"metric": "unknown_metric", "value": 20.0}, "Unsupported telemetry metric"),
        ({"metric": "temperature_c", "value": -273.16}, "Telemetry value outside supported range"),
        ({"metric": "oxygen_pct", "value": 150.0}, "Telemetry value outside supported range"),
        ({"metric": "occupancy_state", "value": 2.0}, "Telemetry value outside supported range"),
        ({"metric": "temperature_c", "value": 22.0, "unit": "%"}, "Telemetry unit does not match metric"),
    ]

    for sample, detail in invalid_samples:
        response = client.post(
            "/api/telemetry",
            headers=OPERATOR_HEADERS,
            json={"device_id": "sensor-validation", **sample},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == detail

    assert client.get("/api/telemetry").json()["items"] == []


def test_telemetry_rejects_metric_that_does_not_match_hardware_profile(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "telemetry-profile.db"))
    client.post(
        "/api/hardware/discovery/profiles",
        headers=OPERATOR_HEADERS,
        json={
            "confirm_inventory_import": True,
            "device_id": "profile-temp-1",
            "profile_id": "greenhouse_temperature",
            "name": "Profile Temperature Sensor",
            "asset_id": "profile-greenhouse",
            "asset_name": "Profile Greenhouse",
            "adapter": "usb",
            "protocols": ["usb", "i2c"],
            "standards": ["Matter Temperature Sensor", "MQTT 5 telemetry"],
            "hardware_model": "raspberry-pi-5",
            "firmware_version": "lab-1.0.0",
            "metric": "temperature_c",
            "value": 24.0,
            "unit": "C",
        },
    )

    response = client.post(
        "/api/telemetry",
        headers=OPERATOR_HEADERS,
        json={"device_id": "profile-temp-1", "metric": "oxygen_pct", "value": 20.9, "unit": "%"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Telemetry metric does not match device profile"


def test_ai_chat_fallback_is_explicit_when_model_is_unavailable(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "chat.db"))

    response = client.post("/api/chat", json={"message": "Why is sensor-1 hot?"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "model_unavailable"
    assert "non-AI troubleshooting" in body["answer"]
