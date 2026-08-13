# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

import sqlite3
from pathlib import Path

import pytest
import yaml
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import CoreStore, create_app
from conftest import admin_token_headers, make_test_jwt, seed_bearer_assignment


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


def test_evidence_findings_accept_commit_hashes_but_reject_contact_numbers(
    tmp_path,
) -> None:
    store = CoreStore(tmp_path / "finding-hash-contact.db")

    accepted = store.add_evidence_finding(
        source="release_mission",
        subject_id="release-mission-hash-regression",
        outcome="completed",
        severity="info",
        evidence="source_commit=64f9c8358453, release_version=0.152.8",
        lesson="Commit hashes are release evidence, not contact data.",
    )

    assert accepted["source"] == "release_mission"
    with pytest.raises(HTTPException) as error:
        store.add_evidence_finding(
            source="release_mission",
            subject_id="release-mission-contact-regression",
            outcome="blocked",
            severity="high",
            evidence="operator phone 491234567890",
            lesson="Contact data must stay out of findings.",
        )
    assert error.value.status_code == 400


def assert_canonical_a2a_envelope(
    message: dict, *, step: int, sender: str, recipient: str
) -> None:
    """Assert project and A2A-compatible handoff message shape."""

    required = {"id", "from", "to", "type", "schema_version", "payload", "trace_id", "ts"}
    assert required.issubset(message)
    assert message["id"].startswith(message["trace_id"])
    assert message["from"] == sender
    assert message["to"] == recipient
    assert message["type"] == "agent.handoff"
    assert message["schema_version"] == "a2a.envelope.v1"
    assert message["kind"] == "message"
    assert message["messageId"] == message["id"]
    assert message["role"] == "agent"
    assert message["parts"] and message["parts"][0]["kind"] == "text"
    assert message["payload"]["messageId"] == message["id"]
    assert message["payload"]["role"] == "agent"
    assert message["payload"]["parts"] == message["parts"]
    metadata = message["payload"]["metadata"]
    assert metadata == message["metadata"]
    assert metadata["step"] == step
    assert metadata["from"] == sender
    assert metadata["to"] == recipient
    assert metadata["protocol"].startswith("A2A")
    assert metadata["trace_policy"]
    assert metadata["approval_required"] in {True, False}
    assert metadata["agent_card_id"].startswith(f"agent-card.{sender}.")
    assert metadata["prompt_ref"] == f"agent.{sender}.contract"
    assert metadata["prompt_version"] >= 1
    assert len(metadata["prompt_content_hash"]) == 16
    assert message["agent_card_id"] == metadata["agent_card_id"]
    assert message["prompt_ref"] == metadata["prompt_ref"]
    assert message["prompt_version"] == metadata["prompt_version"]


def configured_idp(monkeypatch) -> None:
    """Configure the local test identity provider."""

    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")


def test_agent_registry_exposes_a2a_and_customer_safe_instructions(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agents.db"))
    headers = admin_token_headers(monkeypatch)

    public_response = client.get("/api/admin/agents")
    assert public_response.status_code == 401
    assert public_response.json()["detail"] == "Operator token required"

    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="agent-reader",
        scopes=["agent:read"],
    )
    read_token = make_test_jwt(subject="agent-reader", scope="agent:read")
    read_response = client.get(
        "/api/admin/agents", headers={"Authorization": f"Bearer {read_token}"}
    )

    assert read_response.status_code == 200
    read_body = read_response.json()
    assert read_body["detail_level"] == "customer_safe_summary"
    assert all(agent["playbook_redacted"] for agent in read_body["agents"])
    assert all(
        agent["instruction_template"] == "redacted_public_view"
        for agent in read_body["agents"]
    )

    response = client.get(
        "/api/admin/agents",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["detail_level"] == "full"
    assert body["standards"]["adr"] == "ADR-0001 Agent-Orchestrated Dashboard"
    assert body["standards"]["adr_register"] == "/api/architecture/adr"
    assert "A2A-compatible" in body["standards"]["a2a"]
    agent_ids = {agent["agent_id"] for agent in body["agents"]}
    assert "operations_coordinator" in agent_ids
    assert "ai_diagnosis_agent" in agent_ids
    assert "ui_ux_experience_auditor" in agent_ids
    ux_agent = next(
        agent for agent in body["agents"] if agent["agent_id"] == "ui_ux_experience_auditor"
    )
    assert "raw service" in ux_agent["quality_gate_policy"]
    assert "reporting_compliance_agent" in ux_agent["connected_agents"]
    ai_agent = next(
        agent for agent in body["agents"] if agent["agent_id"] == "ai_diagnosis_agent"
    )
    assert ai_agent["operating_brief"]
    assert ai_agent["handoff_policy"]
    assert ai_agent["quality_gate_policy"]
    assert ai_agent["analysis_profile_id"] == "copilot-grade-operations"
    assert ai_agent["model_route"] == "best_available_per_task"
    assert ai_agent["trace_policy"] == "trace_model_tool_handoff_guardrail"
    assert "grounding" in ai_agent["eval_profile"]
    assert len(body["edges"]) >= 6
    assert body["control_plane"]["profile_endpoint"] == "/api/admin/ai/analysis-profiles"
    assert body["control_plane"]["trace_standard"] == "Agents SDK trace semantics"
    assert "secret" not in response.text.lower()



def test_agent_registry_exposes_multi_team_orchestration_policy(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-team-policy.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.get("/api/admin/agents", headers=headers)

    assert response.status_code == 200
    body = response.json()
    policy = body["orchestration_policy"]
    assert policy["activation_rule"] == "mandatory_for_non_trivial_work"
    assert policy["minimum_parallel_lanes"] >= 4
    assert policy["customer_delivery"] == "customer_safe_role_metadata_only"
    graph = body["team_graph"]
    team_ids = {node["team_id"] for node in graph["nodes"]}
    required = {
        "sw_project_coordinator",
        "research_validation_team",
        "requirements_analysis_team",
        "solution_design_team",
        "frontend_implementation_team",
        "backend_implementation_team",
        "security_review_team",
        "qa_io_test_team",
        "contract_license_auditor",
        "product_approval_team",
    }
    assert required.issubset(team_ids)
    assert graph["summary"]["mandatory_team_count"] >= len(required)
    assert graph["summary"]["edge_count"] >= len(required) - 1
    assert graph["quality_gates"]["release_requires_product_approval"] is True
    assert graph["quality_gates"]["hardware_discovery_requires_allowlisted_evidence"] is True
    assert all(node["customer_safe"] for node in graph["nodes"])
    assert all(edge["protocol"] == "A2A" for edge in graph["edges"])
    assert "private " + "prompt" not in response.text.lower()
    assert "/home/" not in response.text
    assert "C:" not in response.text


def test_agent_prompt_contracts_are_admin_manageable_and_customer_safe(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-prompts.db"))
    headers = admin_token_headers(monkeypatch)

    public_response = client.get("/api/admin/agents/prompt-contracts")
    assert public_response.status_code == 401
    assert public_response.json()["detail"] == "Operator token required"

    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="prompt-reader",
        scopes=["agent:read"],
    )
    read_token = make_test_jwt(subject="prompt-reader", scope="agent:read")
    read_response = client.get(
        "/api/admin/agents/prompt-contracts",
        headers={"Authorization": f"Bearer {read_token}"},
    )
    assert read_response.status_code == 200
    assert "redacted_public_view" in read_response.text
    assert "admin@example.test" not in read_response.text
    read_body = read_response.json()
    assert "update_endpoint" not in read_body["admin_surface"]
    assert "rollback_endpoint" not in read_body["admin_surface"]
    read_contract = {
        item["agent_id"]: item for item in read_body["items"]
    }["ai_diagnosis_agent"]
    assert "rollback_endpoint" not in read_contract
    assert not any(
        link["endpoint"].endswith("/prompt-contract")
        for link in read_contract["evidence_links"]
    )

    response = client.get(
        "/api/admin/agents/prompt-contracts",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["summary"]["contract_count"] >= 7
    assert body["summary"]["storage_policy"] == "customer_safe_templates_only"
    assert body["admin_surface"]["update_endpoint"] == (
        "/api/admin/agents/{agent_id}/prompt-contract"
    )
    contracts = {item["agent_id"]: item for item in body["items"]}
    ai_contract = contracts["ai_diagnosis_agent"]
    assert ai_contract["managed_prompt_id"] == "agent.ai_diagnosis_agent.contract"
    assert ai_contract["editable_fields"] == [
        "instruction_template",
        "operating_brief",
        "handoff_policy",
        "quality_gate_policy",
        "eval_profile",
    ]
    assert ai_contract["prompt_storage"] == "versioned_templates_only"
    assert ai_contract["customer_delivery"] == "runtime_policy_record_only"
    assert ai_contract["latest_version"] >= 1
    assert ai_contract["history_count"] >= 1
    assert ai_contract["diff_policy"] == "hash_length_field_diff"
    assert ai_contract["rollback_policy"] == "admin_scope_required_new_version_created"
    assert ai_contract["history_endpoint"].endswith(
        "/ai_diagnosis_agent/prompt-contract/history"
    )
    assert ai_contract["rollback_endpoint"].endswith(
        "/ai_diagnosis_agent/prompt-contract/rollback"
    )
    assert ai_contract["a2a_links"]
    assert ai_contract["adr_id"] == "ADR-0001"
    assert body["summary"]["versioned_count"] == body["summary"]["contract_count"]
    assert body["summary"]["diff_policy"] == "hash_length_field_diff"
    assert body["summary"]["rollback_policy"] == (
        "admin_scope_required_new_version_created"
    )
    assert body["admin_surface"]["history_endpoint"] == (
        "/api/admin/agents/{agent_id}/prompt-contract/history"
    )
    assert body["admin_surface"]["rollback_endpoint"] == (
        "/api/admin/agents/{agent_id}/prompt-contract/rollback"
    )
    assert all(link["endpoint"].startswith("/") for link in ai_contract["evidence_links"])
    serialized = response.text.lower()
    assert "system " + "prompt" not in serialized
    assert "private " + "prompt" not in serialized
    assert "sk-" not in serialized

    update = client.patch(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract",
        headers=headers,
        json={
            "instruction_template": (
                "Use runtime telemetry, RAG evidence, A2A trace, and HITL boundaries "
                "before recommending operational action."
            ),
            "operating_brief": "Deliver bounded diagnosis with visible evidence.",
            "handoff_policy": "Escalate recovery proposals to the recovery agent.",
            "quality_gate_policy": "Pass grounding, A2A, approval, and secret-safety checks.",
            "eval_profile": "grounding,a2a,human_approval,credential_safety",
        },
    )

    assert update.status_code == 200
    updated = update.json()
    assert updated["status"] == "updated"
    assert updated["contract"]["agent_id"] == "ai_diagnosis_agent"
    assert updated["contract"]["managed_prompt_id"] == "agent.ai_diagnosis_agent.contract"
    assert updated["contract"]["quality_gate_policy"].startswith("Pass grounding")
    assert updated["prompt_version"] == ai_contract["latest_version"] + 1
    assert {item["field"] for item in updated["diff"]} == {
        "instruction_template",
        "operating_brief",
        "handoff_policy",
        "quality_gate_policy",
        "eval_profile",
    }
    assert updated["rollback_endpoint"].endswith(
        "/ai_diagnosis_agent/prompt-contract/rollback"
    )
    assert updated["audit_event_id"] > 0
    assert "private " + "prompt" not in update.text.lower()
    assert "sk-" not in update.text.lower()


def test_agent_prompt_contract_history_diff_and_rollback_are_admin_gated(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-prompt-history.db"))
    headers = admin_token_headers(monkeypatch)

    baseline = client.get(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract/history",
        headers=headers,
    )

    assert baseline.status_code == 200
    baseline_body = baseline.json()
    assert baseline_body["detail_level"] == "full"
    assert baseline_body["summary"]["latest_version"] == 1
    baseline_item = baseline_body["items"][0]
    baseline_instruction = baseline_item["snapshot"]["instruction_template"]
    assert baseline_item["change_type"] == "baseline"
    assert baseline_item["snapshot_available"] is True

    anonymous_baseline = client.get(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract/history"
    )
    assert anonymous_baseline.status_code == 401

    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="prompt-history-reader",
        scopes=["agent:read"],
    )
    reader_token = make_test_jwt(subject="prompt-history-reader", scope="agent:read")
    reader_headers = {"Authorization": f"Bearer {reader_token}"}
    public_baseline = client.get(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract/history",
        headers=reader_headers,
    ).json()
    assert public_baseline["detail_level"] == "customer_safe_summary"
    assert public_baseline["summary"]["snapshot_returned"] is False
    assert "rollback_endpoint" not in public_baseline["summary"]
    assert "snapshot" not in public_baseline["items"][0]
    assert public_baseline["items"][0]["actor"] == "redacted"

    update = client.patch(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract",
        headers=headers,
        json={
            "instruction_template": (
                "Use runtime telemetry, RAG evidence, A2A trace, HITL boundaries, "
                "and explicit uncertainty labels before recommending action."
            ),
            "operating_brief": "Deliver bounded diagnosis with cited runtime evidence.",
            "handoff_policy": "Escalate recovery proposals through approved A2A handoff.",
            "quality_gate_policy": "Pass grounding, A2A, approval, rollback, and secret-safety checks.",
            "eval_profile": "grounding,a2a,human_approval,credential_safety",
        },
    )

    assert update.status_code == 200
    update_body = update.json()
    assert update_body["prompt_version"] == 2
    assert all(item["before"] == "redacted_public_view" for item in update_body["diff"])
    assert all(item["after"] == "redacted_public_view" for item in update_body["diff"])
    assert {item["field"] for item in update_body["diff"]} >= {
        "instruction_template",
        "operating_brief",
        "handoff_policy",
        "quality_gate_policy",
    }

    public_history = client.get(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract/history",
        headers=reader_headers,
    ).json()
    assert public_history["summary"]["latest_version"] == 2
    assert public_history["items"][0]["diff"][0]["before"] == "redacted_public_view"
    assert public_history["items"][0]["diff"][0]["after"] == "redacted_public_view"
    assert "explicit uncertainty labels" not in str(public_history)

    rollback = client.post(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract/rollback",
        headers=headers,
        json={"target_version": 1, "reason": "Restore baseline after admin review."},
    )

    assert rollback.status_code == 200
    rollback_body = rollback.json()
    assert rollback_body["prompt_version"] == 3
    assert rollback_body["contract"]["instruction_template"] == baseline_instruction
    assert rollback_body["diff"]

    final_history = client.get(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract/history",
        headers=headers,
    ).json()
    assert final_history["summary"]["latest_version"] == 3
    assert final_history["items"][0]["change_type"] == "rollback"
    assert final_history["items"][0]["target_version"] == 1
    audit = client.get("/api/audit/events", headers=headers).json()["items"]
    assert audit[-1]["event_type"] == "agent.control.updated"


def test_agent_protocol_contracts_public_view_hides_admin_and_write_surfaces(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-protocol.db"))

    response = client.get("/api/orchestration/protocol-contracts")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["summary"]["agent_card_count"] >= 7
    assert body["summary"]["tool_contract_count"] >= 10
    assert body["summary"]["mcp_tool_count"] >= 6
    assert body["summary"]["conformance_score"] == 100
    assert body["schema_contracts"]["agent_card"] == "agent.card.v1"
    assert body["schema_contracts"]["tool_contract"] == "tool.contract.v1"
    assert body["schema_contracts"]["mcp_tool"] == "mcp.tool.v1"
    assert body["schema_contracts"]["mcp_protocol_version"] == "2025-06-18"
    assert "tools/list" in body["schema_contracts"]["mcp_jsonrpc_methods"]
    assert body["admin_surface"]["mcp_tools_endpoint"] == "/api/mcp/tools"
    assert body["admin_surface"]["mcp_jsonrpc_endpoint"] == "/api/mcp/jsonrpc"
    assert "agent_registry_endpoint" not in body["admin_surface"]
    assert "prompt_contract_endpoint" not in body["admin_surface"]
    assert "task_endpoint" not in body["admin_surface"]
    assert body["mcp_gateway"]["security"]["gateway_mode"] == "read_only"
    assert body["schema_contracts"]["a2a_envelope"] == "a2a.envelope.v1"
    cards = {card["id"]: card for card in body["agent_cards"]}
    ai_card = cards["ai_diagnosis_agent"]
    required = {
        "id",
        "owner_panel",
        "purpose",
        "inputs",
        "outputs",
        "tools",
        "model_policy",
        "prompt_ref",
        "permissions",
        "sla",
    }
    assert required.issubset(ai_card)
    assert ai_card["prompt_ref"] == "managed_agent_contract"
    assert ai_card["permissions"]["read_scope"] == "agent:read"
    assert "manage_scope" not in ai_card["permissions"]
    assert ai_card["permissions"]["panel_read_scope"] == "panel:intelligence:read"
    assert "agent_run_scope" not in ai_card["permissions"]
    assert "data:reports:read" in ai_card["permissions"]["data_scopes"]
    assert ai_card["permissions"]["default_decision"] == "deny"
    assert ai_card["permissions"]["rbac_policy"] == "default_deny_least_privilege"
    assert ai_card["model_policy"]["reasoning"] == ai_card["model_policy"]["model_route"]
    assert ai_card["model_policy"]["qa"] == ai_card["eval_profile"]
    assert ai_card["sla"]["quality_target"] == 99.99
    assert ai_card["sla"]["availability"] == 99.99
    assert ai_card["sla"]["p95_latency_ms"] == 2000
    assert ai_card["a2a"]["schema_version"] == "a2a.envelope.v1"
    assert all(tool["schema_version"] == "tool.contract.v1" for tool in ai_card["tools"])
    assert all(tool["mcp_boundary"] == "application_api_tool" for tool in body["tool_contracts"])
    assert all(tool["endpoint"].startswith("/") for tool in body["tool_contracts"])
    assert all(gate["status"] == "ready" for gate in body["conformance_gates"])
    serialized = response.text.lower()
    assert "/api/admin" not in serialized
    assert "/api/agents/tasks" not in serialized
    assert "rollback" not in serialized
    assert "update_endpoint" not in serialized
    assert "instruction_template" not in serialized
    assert "operating_brief" not in serialized
    assert "private " + "prompt" not in serialized
    assert "sk-" not in serialized


def test_agent_protocol_contracts_admin_view_keeps_control_surfaces(
    tmp_path, monkeypatch
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-protocol-admin.db"))

    response = client.get(
        "/api/orchestration/protocol-contracts",
        headers=admin_token_headers(monkeypatch),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["admin_surface"]["agent_registry_endpoint"] == "/api/admin/agents"
    assert body["admin_surface"]["prompt_contract_endpoint"] == (
        "/api/admin/agents/prompt-contracts"
    )
    assert body["admin_surface"]["task_endpoint"] == "/api/agents/tasks"
    cards = {card["id"]: card for card in body["agent_cards"]}
    ai_card = cards["ai_diagnosis_agent"]
    assert ai_card["permissions"]["manage_scope"] == "agent:manage"
    assert ai_card["permissions"]["agent_run_scope"] == "agent:ai_diagnosis_agent:run"
    assert "/api/agents/tasks" in response.text


def test_agent_card_registry_has_public_read_only_discovery_endpoint(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-card-discovery.db"))

    for path in ("/api/agent-cards", "/.well-known/agent-card.json"):
        response = client.get(path)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"] == __version__
        assert body["schema_version"] == "agent.card.registry.v1"
        assert body["prepared_for"] == "GreeNovaX"
        assert body["prepared_by"] == "IoT-AI.Tech"
        assert body["summary"]["agent_card_count"] >= 7
        assert body["customer_delivery_safe"] is True
        assert len(body["agent_cards"]) == body["summary"]["agent_card_count"]
        serialized = response.text.lower()
        assert "/api/admin" not in serialized
        assert "/api/agents/tasks" not in serialized
        assert "rollback" not in serialized
        assert "update_endpoint" not in serialized
        assert "instruction_template" not in serialized
        assert "operating_brief" not in serialized
        assert "private " + "prompt" not in serialized
        assert "sk-" not in serialized


def test_versioned_agent_card_artifact_matches_runtime_contracts(
    tmp_path, monkeypatch
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-card-artifact.db"))

    response = client.get(
        "/api/orchestration/protocol-contracts",
        headers=admin_token_headers(monkeypatch),
    )
    artifact_path = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "agent-cards"
        / "AGENT_CARDS.en.yaml"
    )

    assert response.status_code == 200
    runtime_cards = {card["id"]: card for card in response.json()["agent_cards"]}
    artifact = yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == "agent.card.registry.v1"
    assert artifact["a2a_schema_version"] == "a2a.envelope.v1"
    assert artifact["jsonrpc_endpoint"] == "/api/a2a/jsonrpc"
    artifact_cards = {card["id"]: card for card in artifact["cards"]}
    assert set(artifact_cards) == set(runtime_cards)
    required_card_fields = {
        "id",
        "card_id",
        "schema_version",
        "owner_panel",
        "purpose",
        "inputs",
        "outputs",
        "tools",
        "model_policy",
        "prompt_ref",
        "permissions",
        "sla",
        "a2a",
        "adr_ref",
        "eval_profile",
        "customer_delivery_safe",
    }
    for agent_id, artifact_card in artifact_cards.items():
        runtime_card = runtime_cards[agent_id]
        assert required_card_fields.issubset(artifact_card)
        for field in required_card_fields:
            assert artifact_card[field] == runtime_card[field]


def test_a2a_jsonrpc_lists_agents_dispatches_tasks_and_exposes_stream(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "a2a-jsonrpc.db"))

    list_response = client.post(
        "/api/a2a/jsonrpc",
        json={"jsonrpc": "2.0", "id": "list-1", "method": "agents/list"},
    )
    assert list_response.status_code == 200
    list_body = list_response.json()["result"]
    assert list_body["protocolVersion"] == "a2a.envelope.v1"
    assert list_body["transport"]["jsonrpc_endpoint"] == "/api/a2a/jsonrpc"
    assert "tasks/send" in list_body["transport"]["methods"]
    assert len(list_body["agents"]) >= 7
    assert all(card["schema_version"] == "agent.card.v1" for card in list_body["agents"])

    unauthenticated_task = client.post(
        "/api/a2a/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": "task-denied",
            "method": "tasks/send",
            "params": {"goal": "review current alerts"},
        },
    )
    assert unauthenticated_task.status_code == 200
    assert unauthenticated_task.json()["error"]["code"] == -32001

    task_response = client.post(
        "/api/a2a/jsonrpc",
        headers=OPERATOR_HEADERS,
        json={
            "jsonrpc": "2.0",
            "id": "task-1",
            "method": "tasks/send",
            "params": {
                "goal": "review current alerts and recommend supervised action",
                "preferred_agent_id": "alert_recovery_agent",
            },
        },
    )
    task_body = task_response.json()["result"]
    assert task_response.status_code == 200
    assert task_body["protocolVersion"] == "a2a.envelope.v1"
    assert task_body["task"]["primary_agent_id"] == "alert_recovery_agent"
    assert task_body["task"]["a2a_trace"]
    assert task_body["task"]["requires_human_approval"] is True

    stream_negotiation = client.post(
        "/api/a2a/jsonrpc",
        json={"jsonrpc": "2.0", "id": "stream-1", "method": "messages/stream"},
    )
    stream_body = stream_negotiation.json()["result"]
    assert stream_body["endpoint"] == "/api/a2a/messages/stream"
    assert stream_body["event_types"] == ["a2a.ready", "a2a.agent", "a2a.complete"]

    stream_response = client.get(
        "/api/a2a/messages/stream",
        headers=OPERATOR_HEADERS,
    )
    assert stream_response.status_code == 200
    assert "text/event-stream" in stream_response.headers["content-type"]
    assert "event: a2a.ready" in stream_response.text
    assert "event: a2a.complete" in stream_response.text


def test_a2a_tasks_send_requires_agent_run_scope(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    client = TestClient(create_app(database_path=tmp_path / "a2a-run-scope.db"))
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="a2a-read",
        scopes=["agent:read"],
    )
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="a2a-run",
        scopes=["agent:run"],
    )
    payload = {
        "jsonrpc": "2.0",
        "id": "task-scope",
        "method": "tasks/send",
        "params": {"goal": "review current alerts"},
    }

    denied = client.post(
        "/api/a2a/jsonrpc",
        headers={
            "Authorization": "Bearer "
            + make_test_jwt(subject="a2a-read", scope="agent:read")
        },
        json=payload,
    )
    allowed = client.post(
        "/api/a2a/jsonrpc",
        headers={
            "Authorization": "Bearer "
            + make_test_jwt(subject="a2a-run", scope="agent:run")
        },
        json=payload,
    )

    assert denied.status_code == 200
    assert denied.json()["error"]["code"] == -32003
    assert "agent:run" in denied.json()["error"]["message"]
    assert allowed.status_code == 200
    assert allowed.json()["result"]["task"]["run_id"]
    assert len(client.get("/api/agents/tasks", headers=OPERATOR_HEADERS).json()["items"]) == 1


def test_mcp_gateway_lists_read_only_tools(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mcp-tools.db"))

    response = client.get("/api/mcp/tools")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["protocol_version"] == "2025-06-18"
    assert body["capabilities"]["tools"]["listChanged"] is True
    assert body["security"]["gateway_mode"] == "read_only"
    assert body["security"]["tools_call_auth"] == "operator_required_in_production"
    names = [tool["name"] for tool in body["tools"]]
    assert names == sorted(names)
    assert "agentiot.operations_summary" in names
    assert "agentiot.assistant_decision_brief" in names
    assert "agentiot.project_gap_discovery" in names
    for tool in body["tools"]:
        assert tool["inputSchema"]["type"] == "object"
        assert tool["outputSchema"]["type"] == "object"
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["destructiveHint"] is False
        assert tool["_meta"]["approval_required"] is False
        assert tool["_meta"]["endpoint"].startswith("/")
    serialized = response.text.lower()
    assert "instruction_template" not in serialized
    assert "operating_brief" not in serialized
    assert "sk-" not in serialized


def test_mcp_jsonrpc_tools_list_and_call_read_tool(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mcp-jsonrpc.db"))

    init = client.post(
        "/api/mcp/jsonrpc",
        json={"jsonrpc": "2.0", "id": "init-1", "method": "initialize", "params": {}},
    )
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "agentiot-greenovax"

    listed = client.post(
        "/api/mcp/jsonrpc",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert listed.status_code == 200
    listed_body = listed.json()
    assert listed_body["jsonrpc"] == "2.0"
    assert listed_body["result"]["resultType"] == "complete"
    assert listed_body["result"]["cacheScope"] == "public"
    assert any(
        tool["name"] == "agentiot.operations_summary"
        for tool in listed_body["result"]["tools"]
    )

    called = client.post(
        "/api/mcp/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "agentiot.operations_summary",
                "arguments": {},
            },
        },
    )
    assert called.status_code == 200
    body = called.json()
    result = body["result"]
    assert result["resultType"] == "complete"
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert result["structuredContent"]["status"] == "ok"
    assert result["structuredContent"]["operational_state"]
    assert "counters" in result["structuredContent"]

    gap_called = client.post(
        "/api/mcp/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": "gap-tool",
            "method": "tools/call",
            "params": {
                "name": "agentiot.project_gap_discovery",
                "arguments": {},
            },
        },
    )
    assert gap_called.status_code == 200
    gap_body = gap_called.json()["result"]["structuredContent"]
    assert gap_body["cadence_hours"] == 6
    assert gap_body["customer_acceptance_claimed"] is False
    assert gap_body["privacy"]["customer_safe"] is True
    assert gap_body["kpi_sla"]["mcp_tool_count"] >= 6
    assert "/api/admin/" not in gap_called.text


def test_mcp_jsonrpc_tools_call_requires_operator_in_production(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ENV", "production")
    monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")
    strong_operator_token = "mcp-production-operator-" + ("a" * 64)
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", strong_operator_token)
    client = TestClient(create_app(database_path=tmp_path / "mcp-production.db"))
    seed_bearer_assignment(
        client,
        monkeypatch,
        scopes=["device:write", "telemetry:write"],
    )
    payload = {
        "jsonrpc": "2.0",
        "id": "prod-call",
        "method": "tools/call",
        "params": {
            "name": "agentiot.operations_summary",
            "arguments": {},
        },
    }

    listed = client.post(
        "/api/mcp/jsonrpc",
        json={"jsonrpc": "2.0", "id": "list", "method": "tools/list", "params": {}},
    )
    assert listed.status_code == 200
    assert listed.json()["result"]["cacheScope"] == "public"

    blocked = client.post("/api/mcp/jsonrpc", json=payload)
    assert blocked.status_code == 200
    assert blocked.json()["error"]["code"] == -32001
    assert "authenticated operator" in blocked.json()["error"]["message"]

    low_scope_token = make_test_jwt(scope="device:write telemetry:write")
    denied = client.post(
        "/api/mcp/jsonrpc",
        headers={"Authorization": f"Bearer {low_scope_token}"},
        json=payload,
    )
    assert denied.status_code == 200
    assert denied.json()["error"]["code"] == -32003
    assert "panel:operate:read" in denied.json()["error"]["message"]

    allowed = client.post(
        "/api/mcp/jsonrpc",
        headers={"X-Operator-Token": strong_operator_token},
        json=payload,
    )
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["result"]["structuredContent"]["status"] == "ok"
    assert "unit-" + "operator-" + "sentinel" not in allowed.text


def test_mcp_jsonrpc_rejects_unregistered_or_write_tools(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mcp-reject.db"))

    response = client.post(
        "/api/mcp/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "/api/recovery/proposals",
                "arguments": {"proposal_id": 1},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"]["code"] == -32602
    assert "read-only MCP gateway" in body["error"]["message"]


def test_mcp_jsonrpc_validates_declared_input_schema(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "mcp-schema.db"))

    missing_required = client.post(
        "/api/mcp/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": "missing-query",
            "method": "tools/call",
            "params": {
                "name": "agentiot.rag_search",
                "arguments": {},
            },
        },
    )
    unexpected_and_out_of_range = client.post(
        "/api/mcp/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": "bad-top-k",
            "method": "tools/call",
            "params": {
                "name": "agentiot.rag_search",
                "arguments": {
                    "query": "temperature anomaly",
                    "top_k": 999,
                    "unexpected": True,
                },
            },
        },
    )
    empty_tool_with_extra = client.post(
        "/api/mcp/jsonrpc",
        json={
            "jsonrpc": "2.0",
            "id": "extra-empty",
            "method": "tools/call",
            "params": {
                "name": "agentiot.operations_summary",
                "arguments": {"unexpected": True},
            },
        },
    )

    for response in (
        missing_required,
        unexpected_and_out_of_range,
        empty_tool_with_extra,
    ):
        assert response.status_code == 200
        body = response.json()
        assert body["error"]["code"] == -32602
        assert body["error"]["message"] == "Tool arguments do not match input schema."
        assert "unexpected" not in response.text


def test_agent_prompt_contract_rejects_sensitive_admin_text(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-prompt-risk.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.patch(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract",
        headers=headers,
        json={
            "instruction_template": (
                "Use this private "
                "prompt with support@example.test and s"
                "k-test-value."
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Instruction contract text is not customer-safe"


def test_agent_prompt_contract_rejects_private_paths_and_provider_payload(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-prompt-path-risk.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.patch(
        "/api/admin/agents/ai_diagnosis_agent/prompt-contract",
        headers=headers,
        json={
            "instruction_template": (
                "Use "
                + "raw provider "
                + "payload from "
                + chr(67)
                + chr(58)
                + "\\Users"
                + "\\operator"
                + "\\payload.json"
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Instruction contract text is not customer-safe"


def test_dashboard_reports_include_charts_and_agent_map(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-reports.db"))

    response = client.get("/api/reports/dashboard", headers=admin_token_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["charts"]) >= 3
    chart_ids = {chart["chart_id"] for chart in body["charts"]}
    assert "operations-readiness" in chart_ids
    assert "agent-coverage" in chart_ids
    report_ids = {report["report_id"] for report in body["reports"]}
    assert "agent-orchestration-map" in report_ids
    assert body["agent_registry"]["admin_controls"]["required_scope"] == "agent:manage"
    chart_ids = {chart["chart_id"] for chart in body["charts"]}
    assert "agent-task-runs" in chart_ids
    assert "agent-autopilot-mission" in chart_ids
    assert "assistant-quality" in chart_ids
    assert "assistant-decision-brief" in chart_ids
    assert "closed-loop-findings" in chart_ids
    assert "analysis-profiles" in chart_ids
    assert "assistant-provider-policy" in report_ids
    assert "ai-analysis-profiles" in report_ids
    assert "closed-loop-findings" in report_ids
    assert "agent-section-reports" in report_ids
    assert "agent-autopilot-mission" in report_ids
    assert "assistant-decision-brief" in report_ids
    assert body["assistant_decision_brief"]["privacy"]["provider_call"] == "not_performed_by_decision_brief"
    assert body["autopilot_mission"]["summary"]["runs_created"] == 0
    assert len(body["agent_section_reports"]["items"]) >= 7
    assert "evidence_findings" in body
    assert body["ai_analysis_profiles"]["active_profile"]["profile_id"]


def test_release_mission_runs_all_quality_agents_and_records_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "release-mission.db"))

    response = client.post(
        "/api/release/mission/run",
        headers=OPERATOR_HEADERS,
        json={"mission_label": "Phase 2 release rehearsal", "assistant_rounds": 10},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["gates_total"] == 4
    assert body["summary"]["assistant_rounds"] == 60
    assert body["summary"]["requested_assistant_rounds"] == 10
    assert body["summary"]["assistant_minimum_rounds"] == 60
    assert body["summary"]["assistant_round_policy"] == "release_minimum_enforced"
    assert body["summary"]["provider_calls"] == 0
    assert body["summary"]["agent_runs"] >= 7
    assert body["summary"]["sla_target"] == 99.99
    assert body["summary"]["sla_state"] == "ready"
    assert body["summary"]["sla_gap"] == 0
    decision_input = next(
        item
        for item in body["summary"]["score_inputs"]
        if item["component_id"] == "assistant-decision-readiness"
    )
    assert decision_input["score"] == 100
    assert decision_input["operational_decision_score"] <= 100
    assert decision_input["score_basis"] == "release_quality_gates_ready"
    assert body["sla"]["target_success_rate"] == 99.99
    assert body["sla"]["passed"] is True
    assert body["sla"]["gap"] == body["summary"]["sla_gap"]
    assert body["sla"]["status"] == "ready"
    gate_ids = {item["gate_id"] for item in body["gates"]}
    assert {
        "baseline-ai-eval",
        "assistant-qa-challenge",
        "agent-autopilot",
        "continuous-qa-mission",
    }.issubset(gate_ids)
    autopilot_gate = next(
        item for item in body["gates"] if item["gate_id"] == "agent-autopilot"
    )
    assert autopilot_gate["score"] == 100
    assert "target" in autopilot_gate["evidence"]
    assert all(link["endpoint"].startswith("/") for link in body["evidence_links"])
    assert any(chart["chart_id"] == "release-mission-gates" for chart in body["charts"])
    assert body["privacy"]["prompt_storage"] == "hash_only_or_not_stored"
    assert body["privacy"]["provider_call"] == "not_performed_by_release_mission"
    assert any(chart["chart_id"] == "release-mission-sla" for chart in body["charts"])

    findings = client.get(
        "/api/evidence/findings", headers=OPERATOR_HEADERS
    ).json()["items"]
    sources = {item["source"] for item in findings}
    assert {
        "release_mission",
        "assistant_qa_challenge",
        "ai_eval",
        "agent_autopilot",
        "continuous_qa_mission",
    }.issubset(sources)

    status = client.get("/api/release/mission").json()
    assert status["status"] == body["status"]
    reports = client.get("/api/reports/dashboard", headers=admin_token_headers()).json()
    chart_ids = {item["chart_id"] for item in reports["charts"]}
    report_ids = {item["report_id"] for item in reports["reports"]}
    assert "release-mission-gates" in chart_ids
    assert "release-mission-control" in report_ids
    assert reports["release_mission"]["mission_id"] == body["mission_id"]


def test_release_mission_exposes_agent_owned_sla_remediation_plan(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "release-remediation.db"))

    response = client.post(
        "/api/release/mission/run",
        headers=OPERATOR_HEADERS,
        json={"mission_label": "Phase 2 remediation rehearsal", "assistant_rounds": 10},
    )

    assert response.status_code == 201
    body = response.json()
    plan = body["remediation_plan"]
    assert plan["status"] == "ready"
    assert plan["target_success_rate"] == 99.99
    assert plan["current_success_rate"] == body["summary"]["kpi_score"]
    assert plan["sla_gap"] == 0
    assert body["summary"]["assistant_rounds"] == 60
    assert body["summary"]["requested_assistant_rounds"] == 10
    assert plan["action_count"] >= 4
    owner_ids = {item["owner_agent_id"] for item in plan["actions"]}
    assert {
        "ai_diagnosis_agent",
        "ui_ux_experience_auditor",
        "admin_governance_agent",
        "reporting_compliance_agent",
    }.issubset(owner_ids)
    assert all(item["a2a_next_hop"] for item in plan["actions"])
    assert all(item["evidence_endpoint"].startswith("/") for item in plan["actions"])
    assert all(item["acceptance_gate"] for item in plan["actions"])
    assert any(item["priority"] == "P0" for item in plan["actions"])

    reports = client.get("/api/reports/dashboard", headers=admin_token_headers()).json()
    chart_ids = {item["chart_id"] for item in reports["charts"]}
    report_ids = {item["report_id"] for item in reports["reports"]}
    assert "release-remediation-actions" in chart_ids
    assert "release-remediation-plan" in report_ids
    assert reports["release_mission"]["remediation_plan"]["action_count"] == plan["action_count"]


def test_release_evidence_console_summarizes_mission_readiness(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "release-evidence.db"))

    waiting = client.get("/api/release/evidence-console")

    assert waiting.status_code == 200
    waiting_body = waiting.json()
    assert waiting_body["status"] == "review_required"
    assert waiting_body["version"] == __version__
    assert waiting_body["summary"]["mission_status"] == "waiting_for_run"
    assert waiting_body["summary"]["gates_ready"] == 0
    assert waiting_body["summary"]["gates_total"] == 4
    assert waiting_body["privacy"]["customer_safe"] == "true"

    run = client.post(
        "/api/release/mission/run",
        headers=OPERATOR_HEADERS,
        json={"mission_label": "Phase 2 release evidence console", "assistant_rounds": 10},
    )
    assert run.status_code == 201

    response = client.get("/api/release/evidence-console")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["mission_status"] == "completed"
    assert body["summary"]["mission_label"] == f"Release mission {__version__}"
    assert body["summary"]["kpi_score"] > 0
    assert body["summary"]["sla_target"] == 99.99
    assert body["summary"]["sla_gap"] == 0
    assert body["summary"]["assistant_rounds"] == 60
    assert body["summary"]["requested_assistant_rounds"] == 10
    assert body["summary"]["assistant_round_policy"] == "release_minimum_enforced"
    assert body["summary"]["evidence_freshness"] == "current_version"
    assert body["summary"]["evidence_current"] is True
    assert body["summary"]["evidence_version"] == __version__
    assert body["summary"]["gates_total"] == 4
    assert body["summary"]["production_acceptance_state"] == "action_required"
    assert body["summary"]["customer_acceptance_claimed"] is False
    assert body["production_acceptance"]["customer_acceptance_claimed"] is False
    assert body["production_acceptance"]["open_action_count"] >= 1
    assert body["production_acceptance"]["evidence_endpoint"] == (
        "/api/production/action-plan"
    )
    assert "not final production acceptance" in body["production_acceptance"]["boundary"]
    assert len(body["gate_evidence"]) == 4
    assert all(item["evidence_endpoint"].startswith("/") for item in body["gate_evidence"])
    assert all(item["owner_agent_id"] for item in body["gate_evidence"])
    assert body["action_plan"]
    assert all(item["evidence_endpoint"].startswith("/") for item in body["action_plan"])
    chart_ids = {chart["chart_id"] for chart in body["charts"]}
    assert "release-evidence-readiness" in chart_ids
    assert "release-evidence-sla" in chart_ids
    endpoints = {link["endpoint"] for link in body["evidence_links"]}
    assert "/api/release/mission" in endpoints
    assert "/api/qa/evidence-report" in endpoints
    assert "/api/evidence/action-board" in endpoints
    assert body["privacy"]["provider_payload_storage"] == "not_stored"
    assert body["privacy"]["local_path_storage"] == "not_stored"


def test_release_evidence_console_rejects_stale_release_mission_version(
    tmp_path,
) -> None:
    database_path = tmp_path / "release-evidence-stale.db"
    client = TestClient(create_app(database_path=database_path))

    run = client.post(
        "/api/release/mission/run",
        headers=OPERATOR_HEADERS,
        json={"mission_label": "Phase 2 current release", "assistant_rounds": 10},
    )
    assert run.status_code == 201

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO evidence_findings (
                finding_id, source, subject_id, outcome, severity,
                evidence, lesson, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "finding-stale-release",
                "release_mission",
                "release-mission-stale",
                "completed",
                "info",
                (
                    "0.141.14 persistent HTTPS evidence closure: 4/4 gates ready, "
                    "requested 60 assistant rounds, ran 60 assistant rounds, "
                    "7 agent runs, SLA gap 0.0%."
                ),
                "Legacy release evidence must not satisfy the current release.",
                "2999-01-01T00:00:00+00:00",
            ),
        )

    response = client.get("/api/release/evidence-console")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "review_required"
    assert body["summary"]["mission_status"] == "stale_evidence"
    assert body["summary"]["mission_label"] == "Stale release mission evidence"
    assert "0.141.14" not in body["summary"]["mission_label"]
    assert body["summary"]["evidence_freshness"] == "stale_stored"
    assert body["summary"]["evidence_current"] is False
    assert body["summary"]["evidence_version"] == "unknown"


def test_release_evidence_console_exposes_operator_execution_controls(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "release-execution.db"))

    waiting = client.get("/api/release/evidence-console").json()

    controls = waiting["execution_controls"]
    assert controls["run_endpoint"] == "/api/release/mission/run"
    assert controls["operator_scope"] == "agent:run"
    assert controls["token_configured"] is False
    assert controls["token_strength"] == "not_configured"
    assert controls["ready_to_run"] is False
    assert controls["run_button_label"] == "Run Readiness Review"
    assert controls["next_action"].startswith("Configure a strong operator token")
    assert {item["name"] for item in controls["required_inputs"]} == {
        "operator_token",
        "mission_label",
        "assistant_rounds",
        "include_disabled_agents",
    }

    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    ready = client.get("/api/release/evidence-console").json()["execution_controls"]

    assert ready["token_configured"] is True
    assert ready["token_strength"] == "weak"
    assert ready["ready_to_run"] is True
    assert ready["next_action"].startswith("Run the readiness review")


def test_release_mission_requires_operator_scope(tmp_path, monkeypatch) -> None:
    client = TestClient(create_app(database_path=tmp_path / "release-mission-gate.db"))

    response = client.post(
        "/api/release/mission/run",
        json={"mission_label": "No token", "assistant_rounds": 10},
    )

    assert response.status_code == 401
    assert client.get("/api/release/mission").json()["status"] == "waiting_for_run"

    configured_idp(monkeypatch)
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="release-reader",
        scopes=["agent:read"],
    )
    read_token = make_test_jwt(subject="release-reader", scope="agent:read")
    read_response = client.post(
        "/api/release/mission/run",
        headers={"Authorization": f"Bearer {read_token}"},
        json={"mission_label": "Read-only token", "assistant_rounds": 10},
    )

    assert read_response.status_code == 403
    assert read_response.json()["detail"] == "Scope required: agent:run"


def test_release_gap_closure_console_maps_open_gates_to_operator_actions(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AGENTIOT_OPERATOR_TOKEN", raising=False)
    client = TestClient(create_app(database_path=tmp_path / "release-gap-closure.db"))

    response = client.get("/api/release/gap-closure-console")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "operator_setup_required"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["open_gate_count"] >= 3
    assert body["summary"]["sla_target"] == 99.99
    assert body["summary"]["runnable_now"] is False
    assert body["auth_gate"]["required_scope"] == "agent:run"
    assert body["auth_gate"]["runnable_now"] is False
    assert body["auth_gate"]["credential_values_returned"] is False
    assert {item["gate_id"] for item in body["gate_closure_plan"]} == {
        "baseline-ai-eval",
        "assistant-qa-challenge",
        "agent-autopilot",
        "continuous-qa-mission",
    }
    assert all(item["run_endpoint"].startswith("/") for item in body["gate_closure_plan"])
    assert all(item["owner_agent_id"] for item in body["gate_closure_plan"])
    assert all(item["a2a_next_hop"] == "release_compliance_controller" for item in body["gate_closure_plan"])
    assert any(
        "strong_operator_token_or_identity_not_configured" in item["blocked_by"]
        for item in body["gate_closure_plan"]
        if item["status"] != "ready"
    )
    assert "unit-" + "operator-" + "sentinel" not in response.text
    chart_ids = {chart["chart_id"] for chart in body["charts"]}
    assert "release-gap-closure-readiness" in chart_ids
    endpoints = {link["endpoint"] for link in body["evidence_links"]}
    assert "/api/release/gap-closure-console" in endpoints
    assert "/api/project/drift-control" in endpoints
    assert body["privacy"]["credential_values_returned"] == "false"

    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    ready = client.get("/api/release/gap-closure-console").json()

    assert ready["status"] == "ready_to_run"
    assert ready["auth_gate"]["runnable_now"] is True
    assert ready["auth_gate"]["operator_token_strength"] == "weak"
    assert ready["summary"]["runnable_now"] is True
    assert all(
        item["runnable_now"] is True
        for item in ready["gate_closure_plan"]
        if item["status"] != "ready"
    )


def test_release_mission_summary_exposes_score_inputs_and_blocking_gates(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "release-score-inputs.db"))

    response = client.get("/api/release/mission")

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert {item["component_id"] for item in summary["score_inputs"]} == {
        "baseline-ai-eval",
        "assistant-qa-challenge",
        "continuous-qa-mission",
        "assistant-decision-readiness",
    }
    scores = [item["score"] for item in summary["score_inputs"]]
    assert scores[0:3] == [0, 0, 100]
    assert 0 <= scores[3] <= 100
    assert summary["kpi_score"] == round(sum(scores) / len(scores), 1)
    assert {item["gate_id"] for item in summary["blocking_gates"]} == {
        "baseline-ai-eval",
        "assistant-qa-challenge",
        "agent-autopilot",
        "continuous-qa-mission",
    }
    assert all(item["source_endpoint"].startswith("/") for item in summary["blocking_gates"])


def test_agent_section_reports_expose_each_agent_runtime_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-section-reports.db"))

    response = client.get("/api/agents/section-reports")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["prepared_for"] == "GreeNovaX"
    items = body["items"]
    assert len(items) >= 7
    by_id = {item["agent_id"]: item for item in items}
    assert by_id["operations_coordinator"]["readiness"]
    assert by_id["device_fleet_agent"]["runtime_records"]["devices"] == 0
    assert by_id["ai_diagnosis_agent"]["runtime_records"]["eval_runs"] == 0
    assert by_id["ui_ux_experience_auditor"]["runtime_records"]["raw_json_menu_links"] == 0
    assert by_id["ui_ux_experience_auditor"]["readiness"] == "ready"
    assert by_id["admin_governance_agent"]["quality_gate"] == "human_approval_required"
    assert all(item["evidence_links"] for item in items)
    assert "secret" not in response.text.lower()


def test_agent_control_requires_admin_scope(tmp_path, monkeypatch) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-admin.db"))
    seed_bearer_assignment(client, monkeypatch)
    operator_token = make_test_jwt()

    response = client.patch(
        "/api/admin/agents/ai_diagnosis_agent",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"mode": "observe_only"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin scope required"


def test_admin_can_update_agent_control_and_audit_it(tmp_path, monkeypatch) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-admin-ok.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.patch(
        "/api/admin/agents/ai_diagnosis_agent",
        headers=headers,
        json={
            "enabled": False,
            "mode": "disabled",
            "analysis_profile_id": "ui-reporting-analyst",
            "model_route": "bounded_visual_quality_review",
            "trace_policy": "trace_ui_visual_gate",
            "eval_profile": "menu_integrity,chart_readability,no_raw_json_navigation",
            "instruction_template": "Use only approved evidence and report unavailable model routes clearly.",
            "operating_brief": "Provide grounded diagnosis for operator review.",
            "handoff_policy": "Escalate active incidents to recovery and reports to compliance.",
            "quality_gate_policy": "Verify grounding, provider labels, and A2A trace evidence.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["agent"]["enabled"] is False
    assert body["agent"]["mode"] == "disabled"
    assert body["agent"]["analysis_profile_id"] == "ui-reporting-analyst"
    assert body["agent"]["model_route"] == "bounded_visual_quality_review"
    assert body["agent"]["trace_policy"] == "trace_ui_visual_gate"
    assert body["agent"]["eval_profile"].startswith("menu_integrity")
    assert body["agent"]["operating_brief"] == "Provide grounded diagnosis for operator review."
    assert body["agent"]["handoff_policy"].startswith("Escalate active incidents")
    assert body["agent"]["quality_gate_policy"].startswith("Verify grounding")
    assert body["agent"]["updated_by"] == "admin-token"
    public_audit = client.get("/api/audit/events").json()["items"]
    assert public_audit[-1]["event_type"] == "agent.control.updated"
    assert set(public_audit[-1]) == {"event_type", "created_at"}
    audit = client.get(
        "/api/audit/events",
        headers=headers,
    ).json()["items"]
    assert "quality_gate_policy" in audit[-1]["detail"]
    assert "analysis_profile_id" in audit[-1]["detail"]


def test_agent_control_rejects_unregistered_analysis_profile(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "agent-profile-bad.db"))

    response = client.patch(
        "/api/admin/agents/ai_diagnosis_agent",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={"analysis_profile_id": "unknown-profile"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported analysis profile"


def test_admin_token_can_update_agent_control_and_audit_it(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "agent-admin-token.db"))

    response = client.patch(
        "/api/admin/agents/operations_coordinator",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "enabled": True,
            "mode": "observe_only",
            "instruction_template": "Observe runtime evidence and route actions to specialist agents.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["agent"]["mode"] == "observe_only"
    assert body["agent"]["operating_brief"].startswith("Coordinate the dashboard")
    assert body["agent"]["updated_by"] == "admin-token"
    assert "unit-admin-sentinel" not in response.text
    audit = client.get("/api/audit/events").json()["items"]
    assert audit[-1]["event_type"] == "agent.control.updated"


def test_wrong_admin_token_is_rejected_before_control_change(
    tmp_path, monkeypatch
) -> None:
    admin_value = "unit-admin-sentinel-" + "a" * 64
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", admin_value)
    client = TestClient(create_app(database_path=tmp_path / "agent-admin-token-bad.db"))

    response = client.patch(
        "/api/admin/agents/operations_coordinator",
        headers={"X-Admin-Token": "wrong-admin-token"},
        json={"mode": "observe_only"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Admin token required"
    agent = next(
        item
        for item in client.get(
            "/api/admin/agents",
            headers={"X-Admin-Token": admin_value},
        ).json()["agents"]
        if item["agent_id"] == "operations_coordinator"
    )
    assert agent["mode"] == "supervised"


def test_admin_quick_route_can_activate_profile_and_provider_policy(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "ai-quick-route.db"))
    headers = {"X-Admin-Token": "unit-admin-sentinel"}
    anonymous_profiles = client.get("/api/admin/ai/analysis-profiles")
    profiles = client.get("/api/admin/ai/analysis-profiles", headers=headers).json()["items"]
    assert anonymous_profiles.status_code == 401
    profile = next(
        item for item in profiles if item["profile_id"] == "copilot-grade-operations"
    )

    profile_response = client.patch(
        "/api/admin/ai/analysis-profiles/copilot-grade-operations",
        headers=headers,
        json={
            "label": profile["label"],
            "routing_layer": profile["routing_layer"],
            "answer_layer": profile["answer_layer"],
            "rag_mode": profile["rag_mode"],
            "model_strategy": profile["model_strategy"],
            "evaluation_gate": profile["evaluation_gate"],
            "active": True,
        },
    )
    policy_response = client.patch(
        "/api/admin/ai/provider-policy",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={
            "provider": "grounded_fallback",
            "model": "not_configured",
            "quality_profile": "copilot-grade-operations",
            "max_context_chars": 6000,
            "grounding_required": True,
                "runtime_enabled": False,
                "allowed_tools": [
                    "/api/operations/summary",
                    "/api/ai/routing",
                    "/api/reports/dashboard",
                    "/api/ai/evaluations",
                    "/api/rag/search",
                ],
        },
    )

    assert profile_response.status_code == 200
    assert policy_response.status_code == 200
    routing = client.get("/api/ai/routing").json()
    assert routing["active_analysis_profile"]["profile_id"] == "copilot-grade-operations"
    assert routing["provider_policy"]["quality_profile"] == "copilot-grade-operations"
    assert routing["provider_policy"]["provider"] == "grounded_fallback"
    audit = client.get("/api/audit/events").json()["items"]
    assert {audit[-2]["event_type"], audit[-1]["event_type"]} == {
        "ai.analysis_profile.updated",
        "ai.provider_policy.updated",
    }


def test_operator_can_run_audited_agent_task(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-task.db"))

    response = client.post(
        "/api/agents/tasks",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
        json={"goal": "Review current alert risk and recovery status."},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["primary_agent_id"] == "alert_recovery_agent"
    assert body["analysis_profile_id"] == "grounded-operations"
    assert body["model_route"] == "fallback_first"
    assert body["trace_policy"] == "trace_a2a_handoff_guardrails"
    assert "operations_coordinator" in body["route"]
    assert len(body["a2a_trace"]) >= 2
    assert_canonical_a2a_envelope(
        body["a2a_trace"][0],
        step=1,
        sender="operations_coordinator",
        recipient=body["route"][1],
    )
    assert body["a2a_trace"][0]["metadata"]["trace_policy"] == "trace_a2a_handoff_guardrails"
    assert body["requires_human_approval"] is True
    runs = client.get("/api/agents/tasks", headers=OPERATOR_HEADERS).json()["items"]
    assert runs[0]["run_id"] == body["run_id"]
    audit = client.get("/api/audit/events").json()["items"]
    assert audit[-1]["event_type"] == "agent.task.completed"
    findings = client.get(
        "/api/evidence/findings", headers=OPERATOR_HEADERS
    ).json()["items"]
    assert findings[0]["source"] == "agent_task"
    assert findings[0]["subject_id"] == body["run_id"]
    assert "Route length" in findings[0]["evidence"]


def test_orchestration_evidence_matrix_exposes_control_plane_release_gate(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-control-plane.db"))

    response = client.get("/api/orchestration/evidence-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    control = body["control_plane"]
    assert control["release_gate"] == "review_required"
    assert control["maturity_score"] >= 90
    assert control["agent_card_count"] == body["summary"]["agents"]
    assert control["dashboard_section_count"] == body["summary"]["dashboard_sections"]
    assert control["customer_safe_section_count"] == body["summary"]["customer_safe_sections"]
    assert control["a2a_edge_count"] >= 6
    assert control["a2a_trace_step_count"] == control["a2a_envelope_count"]
    assert control["a2a_envelope_count"] >= body["summary"]["agents"]
    assert control["adr_gate_count"] >= 3
    assert control["prompt_policy"] == "customer_safe_instruction_templates_only"
    assert control["admin_action"] == "Run agent autopilot mission before phase sign-off."
    protocols = {item["standard"] for item in body["protocol_evidence"]}
    assert {"ADR", "A2A", "A2A Envelope", "RBAC", "HITL", "Trace", "Eval"}.issubset(protocols)
    assert all(item["evidence_endpoint"].startswith("/") for item in body["protocol_evidence"])
    assert all(item["state"] in {"ready", "review_required"} for item in body["protocol_evidence"])
    assert "private " + "prompt" not in response.text.lower()
    forbidden_path = "/" + "home" + "/" + "iot"
    assert forbidden_path not in response.text



def test_orchestration_evidence_matrix_reports_multi_team_graph(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-team-matrix.db"))

    response = client.get("/api/orchestration/evidence-matrix")

    assert response.status_code == 200
    body = response.json()
    control = body["control_plane"]
    assert control["orchestration_team_count"] >= 10
    assert control["mandatory_parallel_lanes"] >= 4
    assert control["team_graph_ready"] is True
    graph = body["team_graph"]
    assert graph["policy_id"] == "multi-team-orchestration-required"
    assert graph["summary"]["mandatory_team_count"] == control["orchestration_team_count"]
    protocol_ids = {item["standard"] for item in body["protocol_evidence"]}
    assert "Multi-Team Orchestration" in protocol_ids
    product_gate = next(
        item for item in graph["nodes"] if item["team_id"] == "product_approval_team"
    )
    assert "release_signoff" in product_gate["required_gates"]
    hardware_team = next(
        item for item in graph["nodes"] if item["team_id"] == "backend_implementation_team"
    )
    assert "/api/hardware/discovery/profiles" in hardware_team["evidence_endpoints"]
    assert "/api/cmdb/configuration-items" in hardware_team["evidence_endpoints"]


def test_agent_autopilot_updates_orchestration_release_gate(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-gate-autopilot.db"))

    before = client.get("/api/orchestration/evidence-matrix").json()
    assert before["control_plane"]["release_gate"] == "review_required"

    response = client.post(
        "/api/agents/autopilot/run",
        headers=OPERATOR_HEADERS,
        json={"mission_label": "Control plane sign-off", "include_disabled": False},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["summary"]["runs_created"] >= 7
    assert body["summary"]["a2a_trace_steps"] >= 7
    after = client.get("/api/orchestration/evidence-matrix").json()
    control = after["control_plane"]
    assert control["release_gate"] == "ready"
    assert control["rows_with_run"] == after["summary"]["agents"]
    assert control["rows_with_finding"] == after["summary"]["agents"]
    assert control["latest_mission_status"] == "completed"
    assert control["admin_action"] == "Agent control plane evidence is ready for phase review."


def test_orchestration_evidence_matrix_joins_trace_adr_and_findings(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-matrix.db"))
    run_response = client.post(
        "/api/agents/tasks",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
        json={"goal": "Review current alert risk and recovery status."},
    )

    assert run_response.status_code == 201
    run = run_response.json()
    response = client.get("/api/orchestration/evidence-matrix")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["adr_id"] == "ADR-0001"
    assert body["standards"]["trace"] == "Agents SDK trace semantics"
    row = next(
        item for item in body["rows"] if item["agent_id"] == "alert_recovery_agent"
    )
    assert row["analysis_profile_id"] == "grounded-operations"
    assert row["model_route"] == "fallback_first"
    assert row["trace_policy"] == "trace_a2a_handoff_guardrails"
    assert row["adr_id"] == "ADR-0001"
    assert row["run_id"] == run["run_id"]
    assert row["finding_id"] is not None
    assert row["menu_anchor"] == "#command-center"
    assert_canonical_a2a_envelope(
        row["a2a_trace"][0],
        step=1,
        sender="operations_coordinator",
        recipient=run["route"][1],
    )
    assert row["a2a_trace"][0]["metadata"]["trace_policy"] == "trace_a2a_handoff_guardrails"
    assert "/api/evidence/findings" in row["evidence_endpoints"]
    assert "/api/admin/ai/analysis-profiles" in row["evidence_endpoints"]
    assert body["summary"]["dashboard_sections"] >= 18
    assert body["summary"]["assigned_sections"] == body["summary"]["dashboard_sections"]
    assert body["summary"]["customer_safe_sections"] == body["summary"]["dashboard_sections"]
    sections = body["dashboard_sections"]
    section_ids = {section["section_id"] for section in sections}
    actual_anchors = {section["menu_anchor"] for section in sections}
    assert {
        "cockpit",
        "overview",
        "asset_workflows",
        "monitoring",
        "alarms",
        "agent_orchestration",
        "access_admin",
        "closed_loop_memory",
        "ai_intelligence",
        "assistant",
        "rag_insights",
        "reports",
        "delivery_evidence",
        "api_evidence",
        "production_readiness",
        "feedback",
        "ui_quality",
        "advanced_settings",
    }.issubset(section_ids)
    assert {
        "#dashboard-shell",
        "#overview",
        "#workflows",
        "#operations",
        "#command-center",
        "#agent-admin",
        "#access-admin",
        "#evidence-findings",
        "#ai-admin",
        "#assistant",
        "#rag-knowledge",
        "#reports-dashboard",
        "#delivery-evidence",
        "#api-evidence",
        "#production-readiness",
        "#feedback",
        "#ui-quality-gate",
        "#advanced-settings-panel",
    }.issubset(actual_anchors)
    for section in sections:
        assert section["owner_agent_id"]
        assert section["owner_agent"]
        assert section["a2a_links"]
        assert section["adr_id"] == "ADR-0001"
        assert section["qa_lane"]
        assert section["eval_profile"]
        assert section["evidence_endpoints"]
        assert all(
            endpoint.startswith("/") for endpoint in section["evidence_endpoints"]
        )
    alarms = next(section for section in sections if section["section_id"] == "alarms")
    assert alarms["owner_agent_id"] == "alert_recovery_agent"
    assert alarms["a2a_protocol"].startswith("A2A")
    assert alarms["adr_id"] == "ADR-0001"
    assert "hitl" in alarms["qa_lane"]
    assert "/api/recovery/proposals" in alarms["evidence_endpoints"]
    assert alarms["playbook_fields_present"] is True
    assert alarms["customer_safe"] is True


def test_agent_task_requires_operator_gate(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "agent-task-gate.db"))

    response = client.post(
        "/api/agents/tasks",
        json={"goal": "Review current alert risk."},
    )

    assert response.status_code == 401
    assert client.get(
        "/api/agents/tasks", headers=OPERATOR_HEADERS
    ).json()["items"] == []


def test_agent_autopilot_mission_runs_all_enabled_agents(
    tmp_path, monkeypatch
) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "agent-autopilot.db"))
    seed_bearer_assignment(
        client,
        monkeypatch,
        subject="operator@example.test",
        scopes=["agent:run", "report:read"],
    )
    operator_token = make_test_jwt(
        subject="operator@example.test",
        role="operator",
        scope="agent:run report:read",
    )

    blocked = client.post("/api/agents/autopilot/run")

    assert blocked.status_code == 401

    response = client.post(
        "/api/agents/autopilot/run",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={"mission_label": "Phase 2 autopilot QA", "include_disabled": False},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["mission_id"].startswith("agent-autopilot-")
    assert body["mission_label"] == "Phase 2 autopilot QA"
    assert body["summary"]["enabled_agents"] >= 7
    assert body["summary"]["runs_created"] == body["summary"]["enabled_agents"]
    assert body["summary"]["a2a_trace_steps"] >= body["summary"]["runs_created"]
    assert body["summary"]["approval_required_runs"] >= 1
    assert body["agent_ids"] == [item["primary_agent_id"] for item in body["runs"]]
    assert "ai_diagnosis_agent" in body["agent_ids"]
    assert all(item["route"] for item in body["runs"])
    assert all(item["a2a_trace"] for item in body["runs"])
    assert all(item["evidence"] for item in body["runs"])
    assert "operator@example.test" not in response.text
    agent_runs = client.get(
        "/api/agents/tasks", headers=OPERATOR_HEADERS
    ).json()["items"]
    assert len(agent_runs) == body["summary"]["runs_created"]
    findings = client.get(
        "/api/evidence/findings", headers=OPERATOR_HEADERS
    ).json()["items"]
    assert any(item["source"] == "agent_autopilot" for item in findings)
    reports = client.get("/api/reports/dashboard", headers=admin_token_headers()).json()
    assert reports["autopilot_mission"]["summary"]["runs_created"] >= 7


def test_admin_can_define_access_role_policy(tmp_path, monkeypatch) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "access-role-policy.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.patch(
        "/api/admin/access/roles/field-reviewer",
        headers=headers,
        json={
            "description": "Field reviewer for dashboard reports and agent evidence.",
            "scopes": ["agent:read", "report:read", "device:read"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["role"]["role"] == "field-reviewer"
    assert body["role"]["source"] == "admin"
    assert "agent:read" in body["role"]["scopes"]
    roles = client.get("/api/admin/access/roles", headers=headers).json()["items"]
    assert "field-reviewer" in {role["role"] for role in roles}
    policy_roles = client.get("/api/access/policy").json()["roles"]
    assert "field-reviewer" in {role["role"] for role in policy_roles}


def test_admin_can_define_user_access_assignment(tmp_path, monkeypatch) -> None:
    configured_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "access-user.db"))
    headers = admin_token_headers(monkeypatch)

    response = client.patch(
        "/api/admin/access/users/operator-reviewer",
        headers=headers,
        json={
            "role": "operator",
            "scopes": ["device:write", "telemetry:write", "report:read"],
            "status": "active",
            "note": "Pilot access assignment without contact data.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["assignment"]["subject_id"] == "operator-reviewer"
    assert body["assignment"]["role"] == "operator"
    assert "telemetry:write" in body["assignment"]["scopes"]
    public_users = client.get("/api/admin/access/users")
    assert public_users.status_code == 401
    users = client.get(
        "/api/admin/access/users",
        headers=headers,
    ).json()["items"]
    assert users[0]["subject_id"] == "operator-reviewer"
    policy = client.get("/api/access/policy").json()
    assert policy["user_assignments"] == []
    audit = client.get(
        "/api/audit/events",
        headers=headers,
    ).json()["items"]
    assert audit[-1]["event_type"] == "access.user.updated"


def test_user_access_assignment_rejects_contact_data(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", "unit-admin-sentinel")
    client = TestClient(create_app(database_path=tmp_path / "access-user-bad.db"))

    response = client.patch(
        "/api/admin/access/users/operator@example.test",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
        json={"role": "operator", "scopes": ["report:read"], "status": "active"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported subject id"
    assert client.get(
        "/api/admin/access/users",
        headers={"X-Admin-Token": "unit-admin-sentinel"},
    ).json()["items"] == []


def test_architecture_decision_register_exposes_adr_a2a_governance(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "adr-register.db"))

    response = client.get("/api/architecture/adr")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["summary"]["total"] >= 2
    assert body["summary"]["accepted"] == body["summary"]["total"]
    assert body["summary"]["acceptance_gates"] >= 6
    assert "A2A-compatible" in body["standards"]["a2a"]
    adr_ids = {item["adr_id"] for item in body["items"]}
    assert {"ADR-0001", "ADR-0002"}.issubset(adr_ids)
    for item in body["items"]:
        assert item["owner_agent_id"]
        assert item["customer_safe"] is True
        assert item["acceptance_gates"]
        assert all(endpoint.startswith("/") for endpoint in item["evidence_endpoints"])
    assert "why is current" not in response.text.lower()
    assert "unit-admin-sentinel" not in response.text
