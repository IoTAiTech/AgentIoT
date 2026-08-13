# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

"""Tests for repeatable Phase 1/2 recheck tools."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "tools" / "run_phase12_recheck.py"
PHASE2_SCRIPT_PATH = PROJECT_ROOT / "tools" / "run_phase2_recheck.py"


def load_recheck_module():
    """Load the recheck script as a module for focused tests."""

    spec = importlib.util.spec_from_file_location("run_phase12_recheck", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_phase2_module():
    """Load the Phase 2 wrapper as a module for focused tests."""

    tools_path = str(PROJECT_ROOT / "tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    spec = importlib.util.spec_from_file_location("run_phase2_recheck", PHASE2_SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_payloads(version: str = "0.152.8") -> dict:
    """Return customer-safe sample runtime payloads."""

    return {
        "health": {"status": "ok", "version": version},
        "version": {"version": version},
        "phase_distance": {
            "status": "review_required",
            "summary": {"open_phase_closure_task_count": 6},
        },
        "production_action_plan": {
            "summary": {
                "open_control_count": 3,
                "open_decision_count": 9,
                "customer_decision_required": True,
            }
        },
        "operations_summary": {
            "status": "ok",
            "operational_state": "operator_action_required",
            "phase_readiness_score": 90,
            "counters": {
                "assets": 3,
                "devices": 6,
                "config_profiles": 6,
                "telemetry": 10,
                "open_alerts": 2,
                "pending_recovery": 1,
                "audit_events": 579,
                "simulation_runs": 1,
            },
            "latest_telemetry": {
                "metric": "oxygen_pct",
                "value": 20.9,
                "unit": "%",
            },
        },
        "settings": {
            "status": "ok",
            "items": [
                {"control": "Persistence", "state": "sqlite"},
                {"control": "Identity provider", "state": "not_configured"},
                {"control": "AI model services", "state": "waiting_for_credentials"},
            ],
        },
        "cmdb_items": {
            "status": "ok",
            "summary": {
                "ci_count": 9,
                "asset_count": 3,
                "device_count": 6,
                "sensor_auto_discovered": 5,
            },
            "discovery_policy": {
                "usb_supported": True,
                "standard_descriptor_supported": True,
            },
        },
        "simulator_status": {
            "status": "ok",
            "plugin": {
                "installed": True,
                "enabled": False,
                "core_embedded": False,
            },
            "catalog_count": 7,
        },
        "simulator_runs": {
            "status": "ok",
            "items": [{"simulation_id": "hardware-sim-1"}],
        },
        "ai_resource_governance": {
            "status": "ok",
            "credentials": [
                {"provider": "openai", "credential_configured": False},
                {"provider": "local", "credential_configured": False},
            ],
            "token_usage": {"summary": {"window_count": 11}},
            "memory_policy": {
                "max_memory_mb": 768,
                "retention_hours": 720,
            },
            "privacy": {"secret_values_returned": False},
        },
        "security_status": {
            "production_mode": False,
            "admin_token_strength": "not_configured",
        },
        "qc_fanout": {
            "version": version,
            "source_commit": "unit-test",
            "summary": {
                "lane_count": 9,
                "ready_lane_count": 6,
                "engineering_closeable_lane_count": 0,
                "customer_decision_lane_count": 4,
                "secret_required_lane_count": 3,
                "phase_1_technical_readiness_percent": 100,
                "phase_2_technical_readiness_percent": 0,
                "phase12_union_ready": False,
                "must_not_fake": True,
            },
            "lanes": [
                {
                    "lane_id": "qc.phase1.foundation",
                    "status": "ready",
                    "score": 100,
                    "owner_agent_id": "project_delivery_coordinator",
                    "customer_decision_required": False,
                    "requires_secret": False,
                    "evidence_endpoint": "/api/project/phase-distance",
                    "next_action": "Phase 1 is closed.",
                },
                {
                    "lane_id": "qc.phase2.model_route",
                    "status": "owner_decision_required",
                    "score": 87,
                    "owner_agent_id": "AI_Quality_Auditor",
                    "customer_decision_required": True,
                    "requires_secret": True,
                    "evidence_endpoint": "/api/ai/model-benchmarks",
                    "next_action": "Approve fallback-only delivery or configure a model route.",
                },
                {
                    "lane_id": "qc.phase12.union",
                    "status": "action_required",
                    "score": 0,
                    "owner_agent_id": "project_delivery_coordinator",
                    "customer_decision_required": True,
                    "requires_secret": True,
                    "evidence_endpoint": "/api/qc/fan-out",
                    "next_action": "Keep Phase 2 owner decisions visible.",
                },
            ],
        },
    }


def test_phase12_recheck_reports_owner_gated_phase2_without_fake_pass() -> None:
    module = load_recheck_module()

    report = module.evaluate_recheck(
        payloads=sample_payloads(),
        expected_version="0.152.8",
        source_commit="unit-test",
    )

    assert report["status"] == "ACTION_REQUIRED"
    assert report["phase_summary"]["phase_1_technical_readiness_percent"] == 100
    assert report["phase_summary"]["phase_2_technical_readiness_percent"] == 0
    assert report["phase_summary"]["phase12_union_ready"] is False
    assert report["phase_summary"]["open_phase_closure_task_count"] == 6
    assert report["phase_summary"]["contractual_milestone_progress"] == (
        "not_calculated"
    )
    assert report["result_scope"] == "technical_readiness_only"
    assert report["customer_acceptance_claimed"] is False
    assert "remaining_phase_distance" not in report["phase_summary"]
    assert "completion_percent" not in report["phase_summary"]
    assert "phase2_not_100" in report["failure_reasons"]
    assert "phase12_union_not_ready" in report["failure_reasons"]
    assert report["closeability"] == {
        "engineering_closeable_lane_count": 0,
        "customer_decision_lane_count": 2,
        "secret_required_lane_count": 2,
        "must_not_fake": True,
    }
    assert report["operational_evidence"]["operations"]["counters"]["devices"] == 6
    assert report["operational_evidence"]["cmdb"]["summary"]["ci_count"] == 9
    assert report["operational_evidence"]["hardware_simulator"]["run_count"] == 1
    assert report["operational_evidence"]["ai_resources"]["token_window_count"] == 11
    assert report["operational_evidence"]["ai_resources"]["memory_status"] == "configured"
    assert report["operational_evidence"]["ai_resources"]["memory_cap_mb"] == 768
    assert report["runtime"]["source_commit"] == "unit-test"
    assert report["runtime"]["source_commit_ready"] is True
    assert report["privacy"]["credential_values_returned"] is False


def test_phase12_recheck_accepts_empty_live_telemetry() -> None:
    module = load_recheck_module()
    payloads = sample_payloads()
    payloads["operations_summary"]["latest_telemetry"] = None

    report = module.evaluate_recheck(
        payloads=payloads,
        expected_version="0.152.8",
        source_commit="unit-test",
    )

    operations = report["operational_evidence"]["operations"]
    assert operations["latest_metric"] is None
    assert operations["latest_value"] is None
    assert operations["latest_unit"] is None


def test_phase12_recheck_writes_json_and_markdown_evidence(tmp_path) -> None:
    module = load_recheck_module()
    report = module.evaluate_recheck(
        payloads=sample_payloads(),
        expected_version="0.152.8",
        source_commit="unit-test",
    )

    json_path, md_path = module.write_evidence(report, tmp_path)

    assert json_path.exists()
    assert md_path.exists()
    assert "phase2_not_100" in json_path.read_text(encoding="utf-8")
    assert "qc.phase2.model_route" in md_path.read_text(encoding="utf-8")
    assert "Live devices: 6" in md_path.read_text(encoding="utf-8")


def test_phase12_recheck_blocks_stale_runtime_commit_evidence() -> None:
    module = load_recheck_module()
    payloads = sample_payloads()
    payloads["qc_fanout"]["source_commit"] = "runtime123"

    report = module.evaluate_recheck(
        payloads=payloads,
        expected_version="0.152.8",
        source_commit="source456",
    )

    assert report["status"] == "ACTION_REQUIRED"
    assert report["runtime"]["source_commit"] == "runtime123"
    assert report["runtime"]["source_commit_ready"] is False
    assert "runtime_source_commit_mismatch" in report["failure_reasons"]


def test_phase12_recheck_blocks_weak_production_admin_token() -> None:
    recheck = load_recheck_module()
    phase2 = load_phase2_module()
    payloads = sample_payloads()
    payloads["security_status"] = {
        "production_mode": True,
        "admin_token_strength": "weak",
    }

    report = recheck.evaluate_recheck(
        payloads=payloads,
        expected_version="0.152.8",
        source_commit="unit-test",
    )
    focused = phase2.focus_phase2_report(report)

    assert report["status"] == "ACTION_REQUIRED"
    assert "production_admin_token_weak" in report["failure_reasons"]
    assert report["runtime"]["security"] == {
        "production_mode": True,
        "admin_token_strength": "weak",
    }
    assert "production_admin_token_weak" in focused["failure_reasons"]


def test_phase12_recheck_auto_detects_customer_safe_git_commit(tmp_path) -> None:
    module = load_recheck_module()
    git_dir = tmp_path / ".git"
    ref_dir = git_dir / "refs" / "heads"
    ref_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (ref_dir / "main").write_text("1234567890abcdef\n", encoding="utf-8")

    assert module.resolve_source_commit("unknown", tmp_path) == "1234567890ab"
    assert module.resolve_source_commit("manual_1234", tmp_path) == "manual_1234"
    assert module.resolve_source_commit("bad/path", tmp_path) == "1234567890ab"


def test_phase12_recheck_marks_dirty_delivery_sources(monkeypatch, tmp_path) -> None:
    module = load_recheck_module()
    git_dir = tmp_path / ".git"
    ref_dir = git_dir / "refs" / "heads"
    ref_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (ref_dir / "main").write_text("abcdef1234567890\n", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = " M src/agentiot/app.py\n"

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: Result())

    assert module.resolve_source_commit("unknown", tmp_path) == "abcdef123456-dirty"


def test_phase2_recheck_filters_union_failure_from_phase2_scope() -> None:
    recheck = load_recheck_module()
    phase2 = load_phase2_module()
    report = recheck.evaluate_recheck(
        payloads=sample_payloads(),
        expected_version="0.152.8",
        source_commit="unit-test",
    )

    focused = phase2.focus_phase2_report(report)

    assert focused["status"] == "ACTION_REQUIRED"
    assert focused["phase_scope"] == {
        "phase": "phase_2",
        "technical_readiness_percent": 0,
        "union_gate_evaluated": False,
        "union_gate_status": False,
    }
    assert focused["failure_reasons"] == ["phase2_not_100"]
    assert [lane["lane_id"] for lane in focused["open_lanes"]] == [
        "qc.phase2.model_route"
    ]
