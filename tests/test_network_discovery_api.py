# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.1 | Date: 2026-08-11

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from agentiot.app import NetworkDiscoveryScanRequest, OperatorContext, create_app
from conftest import make_test_jwt


OPERATOR_HEADERS = {"X-Operator-Token": "unit-operator-sentinel"}


def reset_scan_cooldown(app) -> None:
    with app.state.store.connect() as connection:
        connection.execute("DELETE FROM network_discovery_scan_guards")


def discovery_result(cidr: str) -> dict[str, object]:
    return {
        "schema_version": "agentiot.network-discovery.v1",
        "scope": cidr,
        "status": "completed",
        "host_count": 2,
        "observed_host_count": 1,
        "duration_ms": 4,
        "limits": {
            "max_hosts": 32,
            "concurrency": 8,
            "connect_timeout_ms": 250,
            "total_timeout_ms": 5000,
            "ports": [80, 443, 1883, 8883, 4840, 502],
        },
        "items": [
            {
                "address": "192.0.2.21",
                "protocol_hints": ["http", "mqtt", "opcua"],
                "open_ports": [80, 1883, 4840],
                "confidence": "port_hint",
                "evidence_kind": "tcp_connect_only",
            }
        ],
        "asset_inventory_mutated": False,
        "payload_reads": False,
        "credentials_used": False,
    }


def test_network_discovery_requires_authentication_and_explicit_confirmation(
    tmp_path,
) -> None:
    app = create_app(database_path=tmp_path / "discovery-auth.db")
    client = TestClient(app)

    unauthenticated = client.post(
        "/api/hardware/discovery/scans",
        json={"cidr": "192.0.2.20/31", "confirm_active": True},
    )
    unconfirmed = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.20/31", "confirm_active": False},
    )

    assert unauthenticated.status_code == 401
    assert unconfirmed.status_code == 400
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []


def test_scan_queues_only_and_approval_promotes_selected_candidate(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-approval.db")

    async def fake_runner(cidr: str) -> dict[str, object]:
        return discovery_result(cidr)

    app.state.network_discovery_runner = fake_runner
    client = TestClient(app)
    scan = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.20/31", "confirm_active": True},
    )

    assert scan.status_code == 201
    assert scan.json()["asset_inventory_mutated"] is False
    assert scan.json()["payload_reads"] is False
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []
    assert client.get("/api/telemetry").json()["items"] == []

    queue = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
    )
    assert queue.status_code == 200
    candidate = queue.json()["items"][0]
    assert candidate["source"] == "network_tcp_hint"
    assert candidate["status"] == "queued"
    assert candidate["confidence"] == "port_hint"

    before = client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()
    assert before["graph"]["candidate_nodes_included"] is False
    assert before["graph"]["nodes"] == []

    endpoint = candidate["approval_endpoint"]
    missing_confirmation = client.post(endpoint, headers=OPERATOR_HEADERS)
    stale_fingerprint = client.post(
        endpoint,
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": "sha256:" + ("0" * 64),
            "expected_revision": candidate["observation_revision"],
        },
    )
    assert missing_confirmation.status_code == 400
    assert stale_fingerprint.status_code == 409

    approval_payload = {
        "confirm": True,
        "expected_fingerprint": candidate["evidence_fingerprint"],
        "expected_revision": candidate["observation_revision"],
        "asset_id": "greenhouse-network-a",
        "asset_name": "Greenhouse Network A",
        "device_name": "Edge Gateway 21",
        "location": "Greenhouse Zone A",
    }
    approval = client.post(
        endpoint,
        headers=OPERATOR_HEADERS,
        json=approval_payload,
    )

    assert approval.status_code == 200
    result = approval.json()
    assert result["status"] == "approved"
    assert result["registration"]["telemetry_created"] is False
    assert result["registration"]["device"]["adapter"] == "network"
    assert {item["protocol"] for item in result["registration"]["protocols"]} == {
        "http",
        "mqtt",
        "opcua",
    }
    assert {
        item["endpoint_address"] for item in result["registration"]["protocols"]
    } == {"192.0.2.21"}
    assert client.get("/api/telemetry").json()["items"] == []

    graph = client.get(
        "/api/cmdb/configuration-items",
        headers=OPERATOR_HEADERS,
        params={"asset_id": "greenhouse-network-a", "protocol": "mqtt"},
    ).json()["graph"]
    assert graph["candidate_nodes_included"] is False
    assert graph["summary"] == {
        "node_count": 3,
        "edge_count": 2,
        "asset_count": 1,
        "device_count": 1,
        "protocol_count": 1,
    }
    assert {item["node_type"] for item in graph["nodes"]} == {
        "asset",
        "device",
        "protocol_hint",
    }
    hint_node = next(
        item for item in graph["nodes"] if item["node_type"] == "protocol_hint"
    )
    assert hint_node["status"] == "unverified_port_hint"
    assert next(
        item["endpoint_address"]
        for item in graph["nodes"]
        if item["node_type"] == "device"
    ) == "192.0.2.21"
    cmdb = client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).json()
    assert "opcua" not in cmdb["management_summary"]["supported_protocol_families"]
    assert set(cmdb["management_summary"]["observed_protocol_hints"]) == {
        "http",
        "mqtt",
        "opcua",
    }
    events = app.state.store.list_rows("audit_events")
    event_types = {event["event_type"] for event in events}
    assert {
        "network.discovery.scan.authorized",
        "network.discovery.candidates.queued",
        "network.discovery.scan.completed",
        "network.discovery.candidate.approved",
    }.issubset(event_types)
    approval_event = next(
        event
        for event in events
        if event["event_type"] == "network.discovery.candidate.approved"
    )
    approval_receipt = json.loads(approval_event["detail"])
    assert approval_receipt["endpoint_address"] == "192.0.2.21"
    assert approval_receipt["open_ports"] == [80, 1883, 4840]
    assert approval_receipt["evidence_fingerprint"] == candidate[
        "evidence_fingerprint"
    ]

    replay = client.post(
        endpoint,
        headers=OPERATOR_HEADERS,
        json=approval_payload,
    )
    changed_mapping = client.post(
        endpoint,
        headers=OPERATOR_HEADERS,
        json={**approval_payload, "asset_id": "different-asset"},
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "already_approved"
    assert changed_mapping.status_code == 409


def test_network_discovery_scan_has_actor_cooldown(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-cooldown.db")

    async def fake_runner(cidr: str) -> dict[str, object]:
        return discovery_result(cidr)

    app.state.network_discovery_runner = fake_runner
    client = TestClient(app)
    payload = {"cidr": "192.0.2.20/31", "confirm_active": True}

    assert client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json=payload,
    ).status_code == 201
    second = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json=payload,
    )

    assert second.status_code == 429
    assert "cooldown" in second.json()["detail"].lower()


def test_network_discovery_cooldown_is_shared_across_app_instances(tmp_path) -> None:
    database_path = tmp_path / "discovery-shared-cooldown.db"
    first_app = create_app(database_path=database_path)
    second_app = create_app(database_path=database_path)
    runner_calls: list[str] = []

    async def first_runner(cidr: str) -> dict[str, object]:
        runner_calls.append("first")
        return discovery_result(cidr)

    async def second_runner(cidr: str) -> dict[str, object]:
        runner_calls.append("second")
        return discovery_result(cidr)

    first_app.state.network_discovery_runner = first_runner
    second_app.state.network_discovery_runner = second_runner
    payload = {"cidr": "192.0.2.20/31", "confirm_active": True}

    first = TestClient(first_app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json=payload,
    )
    second = TestClient(second_app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json=payload,
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert runner_calls == ["first"]


def test_network_discovery_lease_is_global_across_app_instances(tmp_path) -> None:
    database_path = tmp_path / "discovery-global-lease.db"
    first = create_app(database_path=database_path)
    second = create_app(database_path=database_path)

    first_token, first_retry = first.state.store.claim_network_discovery_lease(
        actor="first-operator",
        lease_seconds=30,
    )
    second_token, second_retry = second.state.store.claim_network_discovery_lease(
        actor="second-operator",
        lease_seconds=30,
    )

    assert first_token
    assert first_retry == 0
    assert second_token is None
    assert second_retry > 0
    assert first.state.store.release_network_discovery_lease(first_token) is True

    replacement_token, replacement_retry = (
        second.state.store.claim_network_discovery_lease(
            actor="second-operator",
            lease_seconds=30,
        )
    )
    assert replacement_token
    assert replacement_retry == 0
    assert second.state.store.release_network_discovery_lease(
        replacement_token
    ) is True


def test_discovery_queue_pagination_restarts_after_observation_change(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-pagination-revision.db")
    current = discovery_result("192.0.2.20/31")
    current["items"] = [
        current["items"][0],
        {
            "address": "192.0.2.20",
            "protocol_hints": ["https"],
            "open_ports": [443],
            "confidence": "port_hint",
            "evidence_kind": "tcp_connect_only",
        },
    ]

    async def fake_runner(_cidr: str) -> dict[str, object]:
        return current

    app.state.network_discovery_runner = fake_runner
    client = TestClient(app)
    payload = {"cidr": "192.0.2.20/31", "confirm_active": True}
    assert client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json=payload,
    ).status_code == 201
    first_page = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        params={"limit": 1},
    )
    assert first_page.status_code == 200
    revision = first_page.json()["summary"]["queue_revision"]
    missing_revision = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        params={"limit": 1, "offset": 1},
    )
    assert missing_revision.status_code == 400

    current["items"][0] = {
        **current["items"][0],
        "protocol_hints": ["http", "mqtt", "opcua", "modbus_tcp"],
        "open_ports": [80, 1883, 4840, 502],
    }
    reset_scan_cooldown(app)
    assert client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json=payload,
    ).status_code == 201
    stale_page = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        params={
            "limit": 1,
            "offset": 1,
            "snapshot_revision": revision,
        },
    )

    assert stale_page.status_code == 409
    assert "restart pagination" in stale_page.json()["detail"]


def test_network_scan_requires_dedicated_scope_before_runner(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    app = create_app(database_path=tmp_path / "discovery-scope.db")

    async def forbidden_runner(_cidr: str) -> dict[str, object]:
        raise AssertionError("scanner must not run without network:scan")

    app.state.network_discovery_runner = forbidden_runner
    client = TestClient(app)
    assignment = client.patch(
        "/api/admin/access/users/operator-no-scan",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "role": "operator",
            "scopes": ["device:write"],
            "status": "active",
            "note": "Dedicated network scan scope regression.",
        },
    )
    assert assignment.status_code == 200
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    token = make_test_jwt(subject="operator-no-scan", scope="device:write")
    response = client.post(
        "/api/hardware/discovery/scans",
        headers={"Authorization": f"Bearer {token}"},
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Scope required: network:scan"


def test_network_scan_rejects_scope_outside_deployment_allowlist(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv(
        "AGENTIOT_NETWORK_DISCOVERY_ALLOWED_CIDRS",
        "192.0.2.0/24",
    )
    app = create_app(database_path=tmp_path / "discovery-allowlist.db")

    async def forbidden_runner(_cidr: str) -> dict[str, object]:
        raise AssertionError("scanner must not run outside deployment allowlist")

    app.state.network_discovery_runner = forbidden_runner
    response = TestClient(app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "10.0.0.1/32", "confirm_active": True},
    )

    assert response.status_code == 403
    assert "deployment allowlist" in response.json()["detail"]


def test_candidate_approval_rechecks_revoked_deployment_allowlist(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AGENTIOT_NETWORK_DISCOVERY_ALLOWED_CIDRS",
        "192.0.2.0/24",
    )
    app = create_app(database_path=tmp_path / "discovery-revoked-allowlist.db")

    async def fake_runner(cidr: str) -> dict[str, object]:
        return discovery_result(cidr)

    app.state.network_discovery_runner = fake_runner
    client = TestClient(app)
    scan = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )
    candidate = scan.json()["candidates"][0]
    monkeypatch.setenv(
        "AGENTIOT_NETWORK_DISCOVERY_ALLOWED_CIDRS",
        "10.0.0.0/24",
    )

    approval = client.post(
        candidate["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": candidate["evidence_fingerprint"],
            "expected_revision": candidate["observation_revision"],
        },
    )

    assert approval.status_code == 403
    assert "deployment allowlist" in approval.json()["detail"]
    assert client.get("/api/assets").json()["items"] == []
    assert client.get("/api/devices").json()["items"] == []


def test_changed_port_hints_requeue_same_identity_and_preserve_mapping(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-stable-identity.db")
    current = discovery_result("192.0.2.21/32")

    async def fake_runner(_cidr: str) -> dict[str, object]:
        return current

    app.state.network_discovery_runner = fake_runner
    client = TestClient(app)
    client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "existing-line", "name": "Existing Line"},
    )
    scan = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )
    first = scan.json()["candidates"][0]
    approval = client.post(
        first["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": first["evidence_fingerprint"],
            "expected_revision": first["observation_revision"],
            "asset_id": "existing-line",
            "device_id": "existing-edge-21",
        },
    )
    assert approval.status_code == 200

    current["items"] = [
        {
            "address": "192.0.2.21",
            "protocol_hints": ["https", "opcua"],
            "open_ports": [443, 4840],
            "confidence": "port_hint",
            "evidence_kind": "tcp_connect_only",
        }
    ]
    reset_scan_cooldown(app)
    changed_scan = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )
    changed = changed_scan.json()["candidates"][0]

    assert changed["candidate_id"] == first["candidate_id"]
    assert changed["evidence_fingerprint"] != first["evidence_fingerprint"]
    assert changed["status"] == "queued"
    stale = client.post(
        changed["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": first["evidence_fingerprint"],
            "expected_revision": first["observation_revision"],
        },
    )
    assert stale.status_code == 409

    reapproval = client.post(
        changed["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": changed["evidence_fingerprint"],
            "expected_revision": changed["observation_revision"],
        },
    )
    assert reapproval.status_code == 200
    assert reapproval.json()["candidate"]["asset_id"] == "existing-line"
    assert reapproval.json()["candidate"]["device_id"] == "existing-edge-21"
    protocols = reapproval.json()["registration"]["protocols"]
    assert {(item["protocol"], item["port"]) for item in protocols} == {
        ("https", 443),
        ("opcua", 4840),
    }

    current["items"] = discovery_result("192.0.2.21/32")["items"]
    reset_scan_cooldown(app)
    reverted_scan = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )
    reverted = reverted_scan.json()["candidates"][0]
    assert reverted["evidence_fingerprint"] == first["evidence_fingerprint"]
    assert reverted["observation_revision"] > changed["observation_revision"]

    stale_replay = client.post(
        reverted["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": first["evidence_fingerprint"],
            "expected_revision": first["observation_revision"],
        },
    )
    assert stale_replay.status_code == 409

    fresh_reapproval = client.post(
        reverted["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": reverted["evidence_fingerprint"],
            "expected_revision": reverted["observation_revision"],
        },
    )
    assert fresh_reapproval.status_code == 200
    assert fresh_reapproval.json()["candidate"]["device_id"] == "existing-edge-21"


def test_candidate_list_has_bounded_pagination_and_exact_record_lookup(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-pagination.db")
    observations = [
        {
            "address": f"192.0.2.{index}",
            "protocol_hints": ["http"],
            "open_ports": [80],
            "confidence": "port_hint",
            "evidence_kind": "tcp_connect_only",
        }
        for index in range(1, 16)
    ]
    app.state.store.queue_network_discovery_observations(
        observations,
        actor="pagination-test",
    )
    client = TestClient(app)

    first = client.get(
        "/api/hardware/discovery/candidates?limit=5&offset=0",
        headers=OPERATOR_HEADERS,
    )
    second = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        params={
            "limit": 5,
            "offset": 5,
            "snapshot_revision": first.json()["summary"]["queue_revision"],
        },
    )

    assert first.status_code == 200
    assert first.json()["summary"] == {
        **first.json()["summary"],
        "candidate_count": 15,
        "returned_count": 5,
        "offset": 0,
        "has_more": True,
        "next_offset": 5,
    }
    assert second.status_code == 200
    assert second.json()["summary"]["offset"] == 5
    assert second.json()["summary"]["next_offset"] == 10
    assert {
        item["candidate_id"] for item in first.json()["items"]
    }.isdisjoint({item["candidate_id"] for item in second.json()["items"]})

    candidate_id = second.json()["items"][0]["candidate_id"]
    exact = client.get(
        f"/api/hardware/discovery/candidates/{candidate_id}",
        headers=OPERATOR_HEADERS,
    )
    assert exact.status_code == 200
    assert exact.json()["candidate"]["candidate_id"] == candidate_id


def test_twenty_first_hardware_candidate_remains_reviewable_and_approvable(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "hardware-pagination.db"))
    oldest = None
    for index in range(21):
        queued = client.post(
            "/api/hardware/discovery/candidates",
            headers=OPERATOR_HEADERS,
            json={
                "device_id": f"usb-temperature-{index:02d}",
                "profile_id": "greenhouse_temperature",
                "name": f"USB Temperature Probe {index:02d}",
                "asset_id": f"greenhouse-zone-{index:02d}",
                "asset_name": f"Greenhouse Zone {index:02d}",
                "adapter": "usb",
                "protocols": ["usb"],
                "standards": ["Matter Temperature Sensor"],
                "hardware_model": "raspberry-pi-4",
                "metric": "temperature_c",
                "value": 20.0 + (index / 10),
            },
        )
        assert queued.status_code == 201
        oldest = oldest or queued.json()["candidate"]

    queue = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        params={"source": "hardware_profile", "limit": 100},
    ).json()
    assert queue["summary"]["candidate_count"] == 21
    assert len(queue["items"]) == 21
    exact = client.get(
        f"/api/hardware/discovery/candidates/{oldest['candidate_id']}",
        headers=OPERATOR_HEADERS,
    )
    assert exact.status_code == 200

    approved = client.post(
        oldest["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": oldest["evidence_fingerprint"],
        },
    )
    assert approved.status_code == 200
    assert approved.json()["candidate"]["status"] == "approved"


def test_candidate_approval_requires_device_write_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    app = create_app(database_path=tmp_path / "discovery-dual-scope.db")
    app.state.store.queue_network_discovery_observations(
        discovery_result("192.0.2.21/32")["items"],
        actor="scope-test",
    )
    client = TestClient(app)
    assignment = client.patch(
        "/api/admin/access/users/approval-only",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "role": "operator",
            "scopes": ["device:read", "recovery:approve"],
            "status": "active",
            "note": "Approval must not imply inventory mutation permission.",
        },
    )
    assert assignment.status_code == 200
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    token = make_test_jwt(
        subject="approval-only",
        scope="device:read recovery:approve",
    )
    candidate = client.get(
        "/api/hardware/discovery/candidates",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["items"][0]

    response = client.post(
        candidate["approval_endpoint"],
        headers={"Authorization": f"Bearer {token}"},
        json={
            "confirm": True,
            "expected_fingerprint": candidate["evidence_fingerprint"],
            "expected_revision": candidate["observation_revision"],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Scope required: device:write"
    assert client.get("/api/assets").json()["items"] == []


def test_network_approval_never_overwrites_an_existing_adapter(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-adapter-owner.db")
    client = TestClient(app)
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "existing-line", "name": "Existing Line"},
    ).status_code == 201
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "mqtt-edge-21",
            "name": "Authoritative MQTT Edge",
            "adapter": "mqtt",
            "asset_id": "existing-line",
        },
    ).status_code == 201
    queued = app.state.store.queue_network_discovery_observations(
        discovery_result("192.0.2.21/32")["items"],
        actor="adapter-owner-test",
    )[0]

    rejected = client.post(
        queued["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": queued["evidence_fingerprint"],
            "expected_revision": queued["observation_revision"],
            "asset_id": "existing-line",
            "device_id": "mqtt-edge-21",
            "device_name": "Replacement Name",
        },
    )

    assert rejected.status_code == 409
    assert rejected.json()["detail"] == "Existing device is owned by another adapter"
    device = next(
        item
        for item in client.get("/api/devices").json()["items"]
        if item["device_id"] == "mqtt-edge-21"
    )
    assert device["name"] == "Authoritative MQTT Edge"
    assert device["adapter"] == "mqtt"
    assert app.state.store.list_network_discovery_candidates()[0]["status"] == "queued"


def test_first_approval_cannot_merge_into_an_existing_network_device(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-explicit-link.db")
    client = TestClient(app)
    assert client.post(
        "/api/assets",
        headers=OPERATOR_HEADERS,
        json={"asset_id": "existing-line", "name": "Existing Line"},
    ).status_code == 201
    assert client.post(
        "/api/devices",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "network-edge-21",
            "name": "Existing Network Edge",
            "adapter": "network",
            "asset_id": "existing-line",
        },
    ).status_code == 201
    queued = app.state.store.queue_network_discovery_observations(
        discovery_result("192.0.2.21/32")["items"],
        actor="explicit-link-test",
    )[0]

    rejected = client.post(
        queued["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": queued["evidence_fingerprint"],
            "expected_revision": queued["observation_revision"],
            "asset_id": "existing-line",
            "device_id": "network-edge-21",
        },
    )

    assert rejected.status_code == 409
    assert "revision-checked link operation" in rejected.json()["detail"]
    device = next(
        item
        for item in client.get("/api/devices").json()["items"]
        if item["device_id"] == "network-edge-21"
    )
    assert device["name"] == "Existing Network Edge"
    assert device["adapter"] == "network"


def test_candidate_queue_summaries_and_facets_are_not_page_scoped(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-pagination.db")
    observations = [
        {
            "address": "192.0.2.21",
            "protocol_hints": ["http", "mqtt"],
            "open_ports": [80, 1883],
            "confidence": "port_hint",
            "evidence_kind": "tcp_connect_only",
        },
        {
            "address": "192.0.2.22",
            "protocol_hints": ["http", "opcua"],
            "open_ports": [80, 4840],
            "confidence": "port_hint",
            "evidence_kind": "tcp_connect_only",
        },
    ]
    app.state.store.queue_network_discovery_observations(
        observations,
        actor="pagination-test",
    )

    response = TestClient(app).get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        params={"status": "queued", "limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["summary"]["candidate_count"] == 2
    assert body["summary"]["queued_count"] == 2
    assert body["summary"]["has_more"] is True
    assert body["facets"] == {
        "statuses": ["queued"],
        "sources": ["network_tcp_hint"],
        "protocols": ["http", "mqtt", "opcua"],
    }


def test_expired_network_candidate_is_hidden_then_atomically_cleaned(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-retention.db")
    app.state.store.queue_network_discovery_observations(
        discovery_result("192.0.2.21/32")["items"],
        actor="retention-test",
    )
    with app.state.store.connect() as connection:
        connection.execute(
            "UPDATE network_discovery_candidates SET expires_at = ?",
            ("2000-01-01T00:00:00+00:00",),
        )
    client = TestClient(app)

    queue = client.get(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
    )

    assert queue.status_code == 200
    assert queue.json()["items"] == []
    with app.state.store.connect() as connection:
        stored_count = connection.execute(
            "SELECT COUNT(*) FROM network_discovery_candidates"
        ).fetchone()[0]
    assert stored_count == 1

    assert app.state.store.cleanup_network_discovery_candidates(
        actor="system-retention-test"
    ) == 1
    audit = client.get("/api/audit/events", headers=OPERATOR_HEADERS).json()["items"]
    receipt = next(
        item
        for item in audit
        if item["event_type"] == "network.discovery.candidates.retention.cleaned"
    )
    assert json.loads(receipt["detail"])["deleted_candidate_count"] == 1


def test_candidate_revision_survives_retention_delete(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-retention-revision.db")
    observation = discovery_result("192.0.2.21/32")["items"]
    first = app.state.store.queue_network_discovery_observations(
        observation,
        actor="revision-test",
    )[0]
    with app.state.store.connect() as connection:
        connection.execute(
            "UPDATE network_discovery_candidates SET expires_at = ?",
            ("2000-01-01T00:00:00+00:00",),
        )
    assert app.state.store.cleanup_network_discovery_candidates(
        actor="revision-retention-test"
    ) == 1

    current = app.state.store.queue_network_discovery_observations(
        observation,
        actor="revision-test",
    )[0]

    assert current["candidate_id"] == first["candidate_id"]
    assert current["observation_revision"] > first["observation_revision"]
    client = TestClient(app)
    stale = client.post(
        current["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": first["evidence_fingerprint"],
            "expected_revision": first["observation_revision"],
        },
    )
    approved = client.post(
        current["approval_endpoint"],
        headers=OPERATOR_HEADERS,
        json={
            "confirm": True,
            "expected_fingerprint": current["evidence_fingerprint"],
            "expected_revision": current["observation_revision"],
        },
    )
    assert stale.status_code == 409
    assert approved.status_code == 200


def test_direct_candidate_lookup_bypasses_500_row_list_cap(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "hardware-direct-lookup.db")
    client = TestClient(app)
    queued = client.post(
        "/api/hardware/discovery/candidates",
        headers=OPERATOR_HEADERS,
        json={
            "device_id": "usb-temperature-oldest",
            "profile_id": "greenhouse_temperature",
            "name": "USB Temperature Probe Oldest",
            "asset_id": "greenhouse-oldest",
            "asset_name": "Greenhouse Oldest",
            "adapter": "usb",
            "protocols": ["usb"],
            "standards": ["Matter Temperature Sensor"],
            "hardware_model": "raspberry-pi-4",
            "metric": "temperature_c",
            "value": 20.0,
        },
    )
    assert queued.status_code == 201
    oldest = queued.json()["candidate"]
    with app.state.store.connect() as connection:
        connection.execute(
            "UPDATE hardware_discovery_candidates SET created_at = ? "
            "WHERE candidate_id = ?",
            ("2000-01-01T00:00:00+00:00", oldest["candidate_id"]),
        )
        for index in range(500):
            connection.execute(
                """
                INSERT INTO hardware_discovery_candidates (
                    candidate_id, device_id, asset_id, profile_id, status,
                    payload_json, profile_json, evidence_fingerprint,
                    created_by, created_at, approved_by, approved_at,
                    registration_audit_event_id
                )
                SELECT ?, ?, ?, profile_id, status, payload_json, profile_json,
                    evidence_fingerprint, created_by, ?, approved_by, approved_at,
                    registration_audit_event_id
                FROM hardware_discovery_candidates
                WHERE candidate_id = ?
                """,
                (
                    f"hwdisc-seeded-{index:03d}",
                    f"seeded-device-{index:03d}",
                    f"seeded-asset-{index:03d}",
                    "2099-01-01T00:00:00+00:00",
                    oldest["candidate_id"],
                ),
            )

    listed = app.state.store.list_hardware_discovery_candidates()
    assert len(listed) == 500
    assert oldest["candidate_id"] not in {
        candidate["candidate_id"] for candidate in listed
    }
    direct = client.get(
        f"/api/hardware/discovery/candidates/{oldest['candidate_id']}",
        headers=OPERATOR_HEADERS,
    )
    assert direct.status_code == 200
    assert direct.json()["candidate"]["candidate_id"] == oldest["candidate_id"]
    assert client.get(
        "/api/hardware/discovery/candidates/unknown-candidate",
        headers=OPERATOR_HEADERS,
    ).status_code == 404

    expired = app.state.store.queue_network_discovery_observations(
        discovery_result("192.0.2.21/32")["items"],
        actor="direct-lookup-test",
    )[0]
    with app.state.store.connect() as connection:
        connection.execute(
            "UPDATE network_discovery_candidates SET expires_at = ? "
            "WHERE candidate_id = ?",
            ("2000-01-01T00:00:00+00:00", expired["candidate_id"]),
        )
    assert client.get(
        f"/api/hardware/discovery/candidates/{expired['candidate_id']}",
        headers=OPERATOR_HEADERS,
    ).status_code == 404


def test_network_scan_requires_allowlist_in_every_runtime_mode(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("AGENTIOT_NETWORK_DISCOVERY_ALLOWED_CIDRS", raising=False)
    app = create_app(database_path=tmp_path / "discovery-no-allowlist.db")

    async def forbidden_runner(_cidr: str) -> dict[str, object]:
        raise AssertionError("scanner must not run without an allowlist")

    app.state.network_discovery_runner = forbidden_runner
    response = TestClient(app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Network discovery allowlist is not configured"


def test_scanner_resource_failure_is_audited_and_queues_nothing(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-resource-failure.db")

    async def exhausted(_cidr: str) -> dict[str, object]:
        raise OSError(24, "descriptor limit")

    app.state.network_discovery_runner = exhausted
    client = TestClient(app)
    response = client.post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )

    assert response.status_code == 503
    assert app.state.store.list_network_discovery_candidates() == []
    events = app.state.store.list_rows("audit_events")
    event_types = [event["event_type"] for event in events]
    assert "network.discovery.scan.authorized" in event_types
    assert "network.discovery.scan.failed" in event_types
    assert "network.discovery.scan.completed" not in event_types


def test_unexpected_scanner_failure_has_one_sanitized_terminal_receipt(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "discovery-unexpected-failure.db")
    runner_calls: list[str] = []

    async def failed_runner(_cidr: str) -> dict[str, object]:
        runner_calls.append("failed")
        raise RuntimeError("private scanner diagnostic")

    app.state.network_discovery_runner = failed_runner
    response = TestClient(app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )

    assert response.status_code == 503
    assert "private scanner diagnostic" not in response.text
    throttled = TestClient(app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )
    assert throttled.status_code == 429
    assert runner_calls == ["failed"]
    events = app.state.store.list_rows("audit_events")
    terminal = [
        event
        for event in events
        if event["event_type"] in {
            "network.discovery.scan.completed",
            "network.discovery.scan.failed",
        }
    ]
    assert len(terminal) == 1
    detail = json.loads(terminal[0]["detail"])
    assert detail["reason"] == "scanner_unexpected_failure"
    assert "private scanner diagnostic" not in terminal[0]["detail"]


def test_cancelled_scan_has_one_terminal_receipt_and_reraises(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AGENTIOT_NETWORK_DISCOVERY_ALLOWED_CIDRS",
        "192.0.2.0/24",
    )
    app = create_app(database_path=tmp_path / "discovery-cancelled.db")

    async def cancelled_runner(_cidr: str) -> dict[str, object]:
        raise asyncio.CancelledError

    app.state.network_discovery_runner = cancelled_runner
    route = next(
        route
        for route in app.routes
        if getattr(route, "path", "") == "/api/hardware/discovery/scans"
        and "POST" in getattr(route, "methods", set())
    )
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            route.endpoint(
                NetworkDiscoveryScanRequest(
                    cidr="192.0.2.21/32",
                    confirm_active=True,
                ),
                OperatorContext(actor="cancel-test"),
            )
        )

    events = app.state.store.list_rows("audit_events")
    authorized = [
        event
        for event in events
        if event["event_type"] == "network.discovery.scan.authorized"
    ]
    terminal = [
        event
        for event in events
        if event["event_type"] in {
            "network.discovery.scan.completed",
            "network.discovery.scan.failed",
        }
    ]
    assert len(authorized) == 1
    assert len(terminal) == 1
    assert terminal[0]["event_type"] == "network.discovery.scan.failed"
    detail = json.loads(terminal[0]["detail"])
    assert detail == {
        "reason": "scanner_cancelled",
        "authorization_audit_event_id": authorized[0]["audit_event_id"],
        "asset_inventory_mutated": False,
    }
    assert app.state.store.list_network_discovery_candidates() == []
    assert app.state.store.list_rows("assets") == []
    assert app.state.store.list_rows("devices") == []
    assert app.state.store.claim_network_discovery_attempt(
        actor="cancel-test",
        cooldown_seconds=30,
    ) > 0


def test_response_projection_failure_cannot_create_two_terminal_receipts(
    tmp_path,
    monkeypatch,
) -> None:
    app = create_app(database_path=tmp_path / "discovery-projection.db")

    async def fake_runner(cidr: str) -> dict[str, object]:
        return discovery_result(cidr)

    app.state.network_discovery_runner = fake_runner
    monkeypatch.setattr(
        app.state.store,
        "list_network_discovery_candidates",
        lambda: (_ for _ in ()).throw(RuntimeError("post-commit projection")),
    )
    response = TestClient(app).post(
        "/api/hardware/discovery/scans",
        headers=OPERATOR_HEADERS,
        json={"cidr": "192.0.2.21/32", "confirm_active": True},
    )

    assert response.status_code == 201
    assert len(response.json()["candidates"]) == 1
    terminal = [
        event
        for event in app.state.store.list_rows("audit_events")
        if event["event_type"] in {
            "network.discovery.scan.completed",
            "network.discovery.scan.failed",
        }
    ]
    assert [event["event_type"] for event in terminal] == [
        "network.discovery.scan.completed"
    ]


def test_cmdb_and_discovery_overview_require_device_read_scope(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    app = create_app(database_path=tmp_path / "discovery-read-scope.db")
    client = TestClient(app)

    assert client.get("/api/cmdb/configuration-items").status_code == 401
    assert client.get("/api/hardware/discovery").status_code == 401

    assignment = client.patch(
        "/api/admin/access/users/report-only",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "role": "viewer",
            "scopes": ["report:read"],
            "status": "active",
            "note": "CMDB requires its dedicated read scope.",
        },
    )
    assert assignment.status_code == 200
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    token = make_test_jwt(subject="report-only", scope="report:read")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(
        "/api/cmdb/configuration-items", headers=headers
    ).status_code == 403
    assert client.get("/api/hardware/discovery", headers=headers).status_code == 403
    assert client.get(
        "/api/cmdb/configuration-items", headers=OPERATOR_HEADERS
    ).status_code == 200
