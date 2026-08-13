# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.4 | Date: 2026-08-11

"""Regression coverage for customer-safe public dashboard DTOs."""

from fastapi.testclient import TestClient

import agentiot.app as app_module
from agentiot.app import create_app


def test_unauthenticated_workbench_and_dashboard_are_compact_customer_dtos(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "public-dtos.db"))

    workbench = client.get("/api/assistant/workbench")
    dashboard = client.get("/api/reports/dashboard")

    assert workbench.status_code == 200
    assert dashboard.status_code == 200
    assert len(workbench.content) < 20_000
    assert len(dashboard.content) < 30_000

    workbench_body = workbench.json()
    dashboard_body = dashboard.json()
    workbench_text = workbench.text
    dashboard_text = dashboard.text

    assert set(workbench_body) == {
        "status",
        "version",
        "prepared_for",
        "prepared_by",
        "generated_at",
        "summary",
        "response_package",
        "continuity_brief",
        "action_panel",
        "quality_gates",
        "charts",
    }
    assert set(dashboard_body) == {
        "status",
        "version",
        "prepared_for",
        "prepared_by",
        "charts",
        "reports",
        "agent_runs",
        "ai_eval_runs",
        "autopilot_mission",
        "next_action",
    }
    assert workbench_body["summary"]["assistant_quality_score"] >= 0
    assert workbench_body["response_package"]["status"]
    assert "answer" in workbench_body["response_package"]
    assert isinstance(workbench_body["action_panel"], list)
    assert isinstance(workbench_body["charts"], list)

    assert dashboard_body["charts"]
    assert dashboard_body["reports"]
    assert {"operations-readiness", "runtime-records"} <= {
        item["chart_id"] for item in dashboard_body["charts"]
    }
    assert "operations-readiness" in {
        item["report_id"] for item in dashboard_body["reports"]
    }

    forbidden = (
        "managed_prompt_ids",
        "assistant.ops.diagnosis",
        "prompt_contract",
        "a2a_trace",
        "agent_orchestration",
        "agent_registry",
        "ai_analysis_profiles",
        "ai_provider_policy",
        "/api/admin/",
        "/home/",
    )
    for value in forbidden:
        assert value not in workbench_text
        assert value not in dashboard_text


def test_admin_agent_manage_scope_retains_the_existing_detailed_package(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "admin-dtos.db"))

    public = client.get("/api/assistant/workbench")
    operator = client.get(
        "/api/assistant/workbench",
        headers={"X-Operator-Token": "unit-operator-sentinel"},
    )
    detailed = client.get(
        "/api/assistant/workbench",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
    )
    public_dashboard = client.get("/api/reports/dashboard")
    detailed_dashboard = client.get(
        "/api/reports/dashboard",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
    )

    assert public.status_code == 200
    assert operator.status_code == 200
    assert detailed.status_code == 200
    assert public_dashboard.status_code == 200
    assert detailed_dashboard.status_code == 200
    assert "prompt_contract" not in public.json()
    assert "prompt_contract" not in operator.json()
    assert detailed.json()["prompt_contract"]["managed_prompt_ids"]
    assert "agent_registry" not in public_dashboard.json()
    assert detailed_dashboard.json()["agent_registry"]["agents"]


def test_public_dashboard_skips_the_admin_evidence_graph(
    tmp_path, monkeypatch
) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("public reports must not build the admin evidence graph")

    monkeypatch.setattr(app_module, "dashboard_report_package", fail_if_called)
    client = TestClient(create_app(database_path=tmp_path / "lean-public-reports.db"))

    response = client.get("/api/reports/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert {"operations-readiness", "runtime-records"} <= {
        chart["chart_id"] for chart in body["charts"]
    }
    assert "operations-command-center" in {
        report["report_id"] for report in body["reports"]
    }
