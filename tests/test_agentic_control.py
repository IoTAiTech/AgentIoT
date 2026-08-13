# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.13 | Date: 2026-08-13

"""Contract tests for the GreeNovaX agentic control plane."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agentiot.agentic_control import (
    CONTROL_ACTIONS,
    action_from_goal,
    build_control_dashboard,
    collect_issues,
    run_control_action,
)
from agentiot.app import create_app


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


class FakeStore:
    def list_rows(self, table: str):
        if table == "alerts":
            return [{"status": "open"}]
        if table == "recovery_proposals":
            return [{"status": "pending"}]
        return []

    def list_network_discovery_candidates(self):
        return [{"status": "queued"}]

    def list_dashboard_agents(self):
        return [{"enabled": True}, {"enabled": False}]

    def list_http_service_health(self):
        return [
            {
                "service_id": "health-api",
                "name": "Health API",
                "status": "down",
                "owner_agent_id": "operations_coordinator",
                "issue_code": "http_5xx",
                "surface": "/healthz",
                "access": "public",
                "transport": "https",
                "http_status": 503,
                "latency_ms": 12,
                "security": {"state": "complete", "score": 100},
                "checked_at": "2026-08-13T00:00:00+00:00",
            }
        ]

    def add_audit_event(self, **_kwargs):
        return {"event_id": 1}


def test_action_from_goal_does_not_reenter_existing_autopilot_missions() -> None:
    assert action_from_goal("CONTROL:auto_guard.cycle Keep operations live") == (
        "auto_guard.cycle"
    )
    assert action_from_goal("Run auto-guard now") == "auto_guard.cycle"
    assert action_from_goal("Agent autopilot across sections") == "autopilot.mission"
    assert (
        action_from_goal(
            "Autopilot mission: Agentic control mission for Operations Coordinator."
        )
        is None
    )
    assert action_from_goal("Unrelated dashboard review") is None


def test_collect_issues_covers_service_mqtt_alerts_and_peers() -> None:
    issues = collect_issues(
        services={
            "items": [
                {
                    "service_id": "health-api",
                    "name": "Health API",
                    "status": "down",
                    "owner_agent_id": "operations_coordinator",
                    "issue_code": "http_5xx",
                }
            ]
        },
        mqtt_status={"configured": True, "connected": False, "status": "disconnected"},
        pending_recovery=[{"status": "pending"}],
        discovery_queue=[{"status": "queued"}],
        open_alerts=2,
        nodes=[{"node_id": "peer-arm", "role": "peer", "online": False, "error": "timeout"}],
    )
    issue_ids = {item["id"] for item in issues}
    assert {
        "svc-health-api",
        "mqtt-disconnected",
        "open-alerts",
        "pending-recovery",
        "discovery-queue",
        "node-peer-arm",
    } <= issue_ids


def test_control_dashboard_is_agent_owned_and_rejects_host_copy() -> None:
    dashboard = build_control_dashboard(
        FakeStore(),
        mqtt_status={"status": "disconnected", "connected": False, "configured": True},
        cmdb={"summary": {"ci_count": 3}},
    )
    assert dashboard["schema_version"] == "agentiot.agentic-control.v1"
    assert dashboard["production_claim"] is False
    assert dashboard["policy"]["host_commands_allowed"] is False
    assert dashboard["policy"]["wifi_control_copied"] is False
    assert dashboard["policy"]["agent_owned"] is True
    assert dashboard["radar"]["open_issues"] >= 1
    assert {item["action"] for item in dashboard["actions"]} == {
        item["action"] for item in CONTROL_ACTIONS
    }


def test_unknown_control_action_is_rejected() -> None:
    result = run_control_action(FakeStore(), "host.wifi.restart", actor="tester")
    assert result["status"] == "rejected"
    assert result["commands_executed"] == 0


def test_control_dashboard_and_agent_action_are_operator_gated(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "agentic-control.db")
    with TestClient(app) as client:
        public = client.get("/api/control/dashboard")
        denied = client.post("/api/control/agent-action", json={"action": "service.self_check"})
        accepted = client.post(
            "/api/control/agent-action",
            headers=OPERATOR_HEADERS,
            json={"action": "service.self_check"},
        )
        self_check = client.post(
            "/api/control/self-check",
            headers=OPERATOR_HEADERS,
            json={},
        )
        unknown = client.post(
            "/api/control/agent-action",
            headers=OPERATOR_HEADERS,
            json={"action": "docker.restart"},
        )
        task = client.post(
            "/api/agents/tasks",
            headers=OPERATOR_HEADERS,
            json={"goal": "CONTROL:mqtt.refresh Refresh MQTT evidence"},
        )
        autopilot_task = client.post(
            "/api/agents/tasks",
            headers=OPERATOR_HEADERS,
            json={
                "goal": "Autopilot mission: section review for Operations Coordinator."
            },
        )
        html = client.get("/control")

    assert public.status_code == 200
    body = public.json()
    assert body["schema_version"] == "agentiot.agentic-control.v1"
    assert body["production_claim"] is False
    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["action"] == "service.self_check"
    assert accepted.json()["control"]["action"] == "service.self_check"
    assert self_check.status_code == 200
    assert self_check.json()["action"] == "service.self_check"
    assert unknown.status_code == 200
    assert unknown.json()["control"]["status"] == "rejected"
    assert task.status_code == 201
    assert "Control action mqtt.refresh" in task.json()["answer"]
    assert autopilot_task.status_code == 201
    assert "Control action" not in autopilot_task.json()["answer"]
    assert html.status_code == 200
    assert 'data-workspace-tab="control"' in html.text
    assert "/api/control/dashboard" in html.text


def test_control_solve_runs_owned_agent_and_keeps_hitl(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "agentic-solve.db")
    with TestClient(app) as client:
        response = client.post(
            "/api/control/solve",
            headers=OPERATOR_HEADERS,
            json={},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "solved_or_queued"
    assert payload["production_claim"] is False
    assert payload["agent_run_id"]
    assert payload["auto_guard"]["action"] == "auto_guard.cycle"
    assert payload["auto_guard"]["hitl"] is True
