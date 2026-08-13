# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-11

"""Phase 1/2 QC fan-out contract tests."""

import json

from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import create_app


def test_phase12_qc_fanout_surfaces_all_quality_lanes_without_sensitive_data(
    tmp_path,
    monkeypatch,
) -> None:
    """Expose one customer-safe operational QC contract for Phase 1/2 closure."""

    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "qc-fanout.db"))

    response = client.get("/api/qc/fan-out")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["status"] == "action_required"
    assert body["summary"]["lane_count"] >= 8
    assert body["summary"]["phase_1_technical_readiness_percent"] == 38
    assert body["summary"]["phase_2_technical_readiness_percent"] == 0
    assert body["summary"]["phase12_union_ready"] is False
    assert body["summary"]["engineering_closeable_lane_count"] >= 0
    assert body["summary"]["customer_decision_lane_count"] >= 1
    assert body["summary"]["secret_required_lane_count"] >= 1
    assert body["summary"]["must_not_fake"] is True
    assert body["summary"]["next_action"]

    lane_ids = {lane["lane_id"] for lane in body["lanes"]}
    assert {
        "qc.phase1.foundation",
        "qc.phase2.core_runtime",
        "qc.phase2.model_route",
        "qc.phase2.rag_grounding",
        "qc.phase2.ui_ux",
        "qc.phase2.security_release",
        "qc.phase2.production_actions",
        "qc.phase12.union",
    }.issubset(lane_ids)

    phase1_lane = next(
        lane for lane in body["lanes"] if lane["lane_id"] == "qc.phase1.foundation"
    )
    assert phase1_lane["label"] == "Phase 1 technical closure controls"

    for lane in body["lanes"]:
        assert lane["owner_agent_id"]
        assert lane["status"] in {
            "ready",
            "review_required",
            "action_required",
            "owner_decision_required",
        }
        assert lane["evidence_endpoint"]
        assert lane["next_action"]
        assert isinstance(lane["can_close_by_code"], bool)
        assert isinstance(lane["customer_decision_required"], bool)
        assert isinstance(lane["requires_secret"], bool)
        assert lane["must_not_fake"] is True

    route_lane = next(
        lane for lane in body["lanes"] if lane["lane_id"] == "qc.phase2.model_route"
    )
    assert route_lane["status"] in {"review_required", "owner_decision_required"}
    assert route_lane["customer_decision_required"] is True
    assert route_lane["requires_secret"] is True
    assert route_lane["evidence_endpoint"] == "/api/ai/model-benchmarks"

    union_lane = next(
        lane for lane in body["lanes"] if lane["lane_id"] == "qc.phase12.union"
    )
    assert union_lane["status"] == "action_required"
    assert union_lane["customer_decision_required"] is True
    assert "Phase 2" in union_lane["next_action"]

    serialized = json.dumps(body).lower()
    assert "/api/admin/" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized
    assert "system prompt" not in serialized
    assert "c:\\\\" not in serialized
    assert body["privacy"] == {
        "customer_safe": True,
        "raw_prompts_returned": False,
        "credential_values_returned": False,
        "provider_payloads_returned": False,
        "local_paths_returned": False,
        "admin_write_endpoints_returned": False,
    }


def test_latest_recheck_status_is_manager_safe_without_artifact_paths(
    tmp_path,
    monkeypatch,
) -> None:
    """Expose current Phase 1/2 status without internal paths or prompts."""

    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "latest-recheck.db"))

    response = client.get("/api/recheck/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["status"] == "action_required"
    assert body["summary"]["phase_1_technical_readiness_percent"] == 38
    assert body["summary"]["phase_2_technical_readiness_percent"] == 0
    assert body["summary"]["phase12_union_ready"] is False
    assert body["summary"]["engineering_closeable_lane_count"] >= 0
    assert body["phase_status_brief"]["headline"].startswith("Phase 1:")
    assert "Phase 2" in body["phase_status_brief"]["message"]
    assert body["phase_status_brief"]["next_owner_action"]
    assert body["open_lanes"]
    assert body["privacy"]["artifact_file_path_returned"] is False
    assert body["privacy"]["admin_write_endpoints_returned"] is False
    serialized = json.dumps(body)
    forbidden_host = "".join(
        chr(code) for code in (49, 57, 50, 46, 49, 54, 56, 46, 53, 48, 46, 52, 48)
    )
    forbidden_private_prompt = "".join(
        chr(code) for code in (112, 114, 105, 118, 97, 116, 101, 32, 112, 114, 111, 109, 112, 116)
    )
    forbidden_raw_payload = "".join(
        chr(code) for code in (114, 97, 119, 32, 112, 114, 111, 118, 105, 100, 101, 114, 32, 112, 97, 121, 108, 111, 97, 100)
    )
    assert "output/recheck" not in serialized
    assert "/home/" not in serialized
    assert "\\\\" + forbidden_host not in serialized
    assert "/api/admin" not in serialized
    assert forbidden_private_prompt not in serialized.lower()
    assert forbidden_raw_payload not in serialized.lower()
