# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import CoreStore, create_app, evidence_action_board
from conftest import admin_token_headers


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_qa_challenge_run_scores_operational_agentic_readiness(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-challenge.db"))

    response = client.post(
        "/api/qa/challenge-runs",
        headers=OPERATOR_HEADERS,
        json={"case_count": 8, "profile_id": "grounded-operations"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["profile_id"] == "grounded-operations"
    assert body["case_count"] == 8
    assert body["score"] == 100
    assert body["kpi_target"] == 99.99
    assert body["kpi_actual"] == 100.0
    assert body["passed"] is True
    assert body["bounded"] is True
    assert body["benchmark_label"] == "bounded_operational_qa"
    assert {item["case_id"] for item in body["cases"]} >= {
        "ui-quality-gate",
        "a2a-handoff",
        "analysis-profile-routing",
        "closed-loop-finding",
    }

    runs = client.get("/api/qa/challenge-runs").json()["items"]
    assert runs[0]["run_id"] == body["run_id"]
    findings = client.get("/api/evidence/findings", headers=OPERATOR_HEADERS).json()["items"]
    qa_findings = [item for item in findings if item["source"] == "qa_challenge"]
    assert len(qa_findings) >= 8
    assert all(item["severity"] == "info" for item in qa_findings)
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_qa_challenge_requires_operator_scope(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-challenge-gate.db"))

    response = client.post(
        "/api/qa/challenge-runs",
        json={"case_count": 8, "profile_id": "grounded-operations"},
    )

    assert response.status_code == 401
    assert client.get("/api/qa/challenge-runs").json()["items"] == []


def test_dashboard_reports_include_qa_challenge_kpi(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-reports.db"))

    client.post(
        "/api/qa/challenge-runs",
        headers=OPERATOR_HEADERS,
        json={"case_count": 8, "profile_id": "grounded-operations"},
    )
    response = client.get("/api/reports/dashboard", headers=admin_token_headers())

    assert response.status_code == 200
    body = response.json()
    assert "qa_challenge_runs" in body
    chart_ids = {item["chart_id"] for item in body["charts"]}
    report_ids = {item["report_id"] for item in body["reports"]}
    assert "qa-challenge-kpi" in chart_ids
    assert "qa-challenge-harness" in report_ids
    assert body["qa_challenge_runs"][0]["score"] == 100


def test_continuous_qa_mission_exposes_contract_quality_plan(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-mission.db"))

    response = client.get("/api/qa/continuous-mission")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "planned"
    assert body["duration_minutes"] == 60
    assert body["question_rounds"] == 60
    assert body["kpi_target"] == 99.99
    assert body["coverage_score"] == 100
    assert body["bounded"] is True
    lane_ids = {item["lane_id"] for item in body["lanes"]}
    assert {
        "smoke",
        "api",
        "a2a",
        "adr",
        "visual",
        "stress",
        "rag",
        "log",
        "security",
        "license",
    }.issubset(lane_ids)
    assert all(item["agent_id"] for item in body["lanes"])
    assert body["sla"]["target_success_rate"] == 99.99
    assert body["stress_profile"]["max_devices"] <= 8
    assert "operator-" + "token" not in response.text


def test_operator_can_record_continuous_qa_mission_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-mission-run.db"))

    response = client.post(
        "/api/qa/continuous-mission",
        headers=OPERATOR_HEADERS,
        json={
            "duration_minutes": 60,
            "question_rounds": 60,
            "profile_id": "grounded-operations",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["mission_id"].startswith("continuous-qa-")
    assert body["coverage_score"] == 100
    assert body["closed_loop"]["findings_recorded"] == len(body["lanes"])
    findings = client.get("/api/evidence/findings", headers=OPERATOR_HEADERS).json()["items"]
    mission_findings = [
        item for item in findings if item["source"] == "continuous_qa_mission"
    ]
    assert len(mission_findings) == len(body["lanes"])
    assert all(item["severity"] == "info" for item in mission_findings)
    audit = client.get("/api/audit/events", headers=OPERATOR_HEADERS).json()["items"]
    assert audit[-1]["event_type"] == "qa.continuous_mission.completed"
    reports = client.get("/api/reports/dashboard", headers=admin_token_headers()).json()
    assert reports["continuous_qa_mission"]["mission_id"] == body["mission_id"]
    report_ids = {item["report_id"] for item in reports["reports"]}
    chart_ids = {item["chart_id"] for item in reports["charts"]}
    assert "continuous-qa-mission" in report_ids
    assert "continuous-qa-coverage" in chart_ids


def test_continuous_qa_mission_requires_operator_for_recording(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-mission-gate.db"))

    response = client.post(
        "/api/qa/continuous-mission",
        json={"duration_minutes": 60, "question_rounds": 60},
    )

    assert response.status_code == 401
    findings = client.get("/api/evidence/findings", headers=OPERATOR_HEADERS).json()["items"]
    assert [item for item in findings if item["source"] == "continuous_qa_mission"] == []


def test_qa_evidence_report_shows_gaps_before_runs(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-evidence-gaps.db"))

    response = client.get("/api/qa/evidence-report")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["version"] == __version__
    assert body["score"] == 50
    assert "Run a bounded QA challenge." in body["gaps"]
    assert "Record continuous QA mission evidence." in body["gaps"]
    assert "Run the 60-round assistant answer-quality review." in body["gaps"]
    assert body["latest_challenge"] is None
    assert len(body["standards"]) >= 10
    assert len(body["ab_tests"]) >= 2
    assert body["stress_profile"]["large_dataset_allowed"] is False


def test_qa_evidence_report_is_ready_after_challenge_and_mission(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "qa-evidence-ready.db"))

    challenge = client.post(
        "/api/qa/challenge-runs",
        headers=OPERATOR_HEADERS,
        json={"case_count": 8, "profile_id": "grounded-operations"},
    )
    assert challenge.status_code == 201
    mission = client.post(
        "/api/qa/continuous-mission",
        headers=OPERATOR_HEADERS,
        json={
            "duration_minutes": 60,
            "question_rounds": 60,
            "profile_id": "grounded-operations",
        },
    )
    assert mission.status_code == 201
    assistant_qa = client.post(
        "/api/ai/evaluations/runs?suite=assistant_qa_60&rounds=60",
        headers=OPERATOR_HEADERS,
    )
    assert assistant_qa.status_code == 201

    response = client.get("/api/qa/evidence-report")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["score"] == 100
    assert body["latest_challenge"]["score"] == 100
    assert body["continuous_mission"]["status"] == "completed"
    assert body["continuous_mission"]["findings_recorded"] == len(body["standards"])
    assert body["assistant_qa_challenge"]["case_count"] == 60
    assert body["assistant_qa_challenge"]["provider_calls"] == 0
    assert not body["gaps"]
    assert all(item["endpoint"].startswith("/") for item in body["evidence_links"])


def test_evidence_action_board_turns_findings_into_agent_actions(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "evidence-action-board.db"))

    chat = client.post(
        "/api/chat",
        headers=OPERATOR_HEADERS,
        json={"message": "Summarize current operational risk and next action."},
    )
    assert chat.status_code == 200
    task = client.post(
        "/api/agents/tasks",
        headers=OPERATOR_HEADERS,
        json={"goal": "Review visual evidence, QA gates, and action ownership."},
    )
    assert task.status_code == 201
    challenge = client.post(
        "/api/qa/challenge-runs",
        headers=OPERATOR_HEADERS,
        json={"case_count": 8, "profile_id": "grounded-operations"},
    )
    assert challenge.status_code == 201

    response = client.get("/api/evidence/action-board")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["total_actions"] >= 3
    assert body["summary"]["open_actions"] >= 1
    assert body["summary"]["no_raw_prompt_storage"] is True
    assert {"assistant_chat", "agent_task", "qa_challenge"}.issubset(
        set(body["summary"]["sources"])
    )
    assert all(item["owner_agent_id"] for item in body["actions"])
    assert all(item["evidence_endpoint"].startswith("/") for item in body["actions"])
    assert all(item["acceptance_gate"] for item in body["actions"])
    assert all(item["a2a_next_hop"] for item in body["actions"])
    assert "unit-" + "operator-" + "sentinel" not in response.text
    assert "Summarize current operational risk" not in response.text



def test_evidence_action_board_records_prompt_free_action_review(tmp_path) -> None:
    db_path = tmp_path / "evidence-action-review.db"
    store = CoreStore(db_path)
    store.add_evidence_finding(
        source="project_gap_discovery",
        subject_id="gap-review-1",
        outcome="review_required",
        severity="review_required",
        evidence="Project gap discovery needs owner action review evidence.",
        lesson="Record action reviews without prompts, contacts, or secrets.",
    )
    client = TestClient(create_app(database_path=db_path))

    before = client.get("/api/evidence/action-board").json()
    action = before["actions"][0]
    assert action["status"] == "open"
    assert action["review_state"] == "pending"

    assert action["action_key"].startswith("eab-")
    response = client.post(
        f"/api/evidence/action-board/{action['action_key']}/review",
        headers=OPERATOR_HEADERS,
        json={"outcome": "lesson_applied"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "recorded"
    assert body["action"]["status"] == "ready"
    assert body["action"]["review_state"] == "reviewed"
    assert body["board_summary"]["open_actions"] == 0
    assert body["board_summary"]["reviewed_actions"] == 1
    assert body["privacy"]["raw_prompt_stored"] is False
    assert "Project gap discovery needs" not in response.text
    findings = client.get("/api/evidence/findings", headers=OPERATOR_HEADERS).json()["items"]
    assert any(item["source"] == "evidence_action_review" for item in findings)


def test_evidence_action_board_groups_duplicate_finding_actions(tmp_path) -> None:
    store = CoreStore(tmp_path / "grouped-evidence-actions.db")
    for index in range(6):
        store.add_evidence_finding(
            source="project_gap_discovery",
            subject_id=f"gap-{index}",
            outcome="review_required",
            severity="review_required",
            evidence="Repeated evidence action needs one owner-owned review.",
            lesson="Group repeated evidence actions so operators see one actionable row.",
        )

    body = evidence_action_board(store, production=False)

    assert body["summary"]["raw_finding_actions"] == 6
    assert body["summary"]["grouped_action_count"] == 1
    assert body["summary"]["duplicate_actions_grouped"] == 5
    assert len(body["actions"]) == 1
    action = body["actions"][0]
    assert action["occurrence_count"] == 6
    assert action["action_key"].startswith("eab-")
    assert action["review_endpoint"].endswith(f"/{action['action_key']}/review")
    assert len(action["created_from_ids"]) == 6
    assert action["primary_cta"]["label"] == "Open Findings"
    assert action["primary_cta"]["target"] == "shell-evidence-finding-body"
    assert action["primary_cta"]["route"] == "/evidence"
    assert all(item.startswith("evidence-ref-") for item in action["created_from_ids"])
    assert "gap-0" not in str(body)
    assert "Repeated evidence action needs" not in str(body)
    assert "Repeated evidence action" not in str(action["created_from_ids"])
