# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

import os

from fastapi.testclient import TestClient

from agentiot import __version__
from agentiot.app import create_app


def admin_headers() -> dict[str, str]:
    os.environ["AGENTIOT_ADMIN_TOKEN"] = "unit-admin-sentinel"
    return {"X-Admin-Token": "unit-admin-sentinel"}


def configure_idp(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_IDP_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("AGENTIOT_IDP_AUDIENCE", "agentiot-dashboard")
    monkeypatch.setenv("AGENTIOT_IDP_SHARED_SECRET", "test-idp-validation-key")


def test_rag_knowledge_base_exposes_customer_safe_sources(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rag-base.db"))

    response = client.get("/api/rag/knowledge-base")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["version"] == __version__
    assert body["metrics"]["document_count"] >= 5
    doc_ids = {item["doc_id"] for item in body["items"]}
    assert {
        "delivery-scope",
        "device-operations",
        "ai-governance",
        "delivery-acceptance",
    }.issubset(doc_ids)
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_rag_search_ranks_delivery_and_runtime_evidence(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rag-search.db"))

    response = client.get(
        "/api/rag/search",
        params={"q": "firmware recovery approval dashboard", "top_k": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["query"] == "firmware recovery approval dashboard"
    assert body["top_k"] == 3
    assert body["active_profile"]["profile_id"] == "grounded-operations"
    assert body["rag_mode"] == "runtime_and_delivery_evidence"
    assert 1 <= len(body["matches"]) <= 3
    assert body["matches"][0]["score"] > 0
    assert all(item["endpoint"].startswith("/") for item in body["evidence_links"])
    assert "secret" not in response.text.lower()


def test_rag_quality_console_scores_grounding_and_action_gaps(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rag-quality.db"))

    response = client.get("/api/rag/quality-console")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "review_required"}
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["document_count"] >= 5
    assert body["summary"]["coverage_score"] >= 80
    assert body["summary"]["retrieval_probe_count"] >= 4
    assert body["summary"]["storage_policy"] == "customer_safe_knowledge_only"
    assert body["profile_alignment"]["routing_layer"]
    assert body["profile_alignment"]["answer_layer"]
    assert body["profile_alignment"]["rag_mode"] == "runtime_and_delivery_evidence"
    assert body["retrieval_probes"]
    assert all(probe["top_match"]["endpoint"].startswith("/") for probe in body["retrieval_probes"])
    assert body["summary"]["grounding_gap_count"] == 0
    assert body["summary"]["maintenance_item_count"] >= 1
    assert body["grounding_gaps"] == []
    assert body["maintenance_items"]
    assert all(item["owner_agent_id"] for item in body["maintenance_items"])
    assert all(item["blocking"] is False for item in body["maintenance_items"])
    assert body["action_plan"]
    assert all(action["evidence_endpoint"].startswith("/") for action in body["action_plan"])
    assert any(chart["chart_id"] == "rag-quality-coverage" for chart in body["charts"])
    assert any(link["endpoint"] == "/api/rag/search" for link in body["evidence_links"])
    serialized = response.text.lower()
    assert "private " + "prompt" not in serialized
    assert "system " + "prompt" not in serialized
    assert "secret" not in serialized
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_admin_can_update_rag_knowledge_without_contact_data(tmp_path, monkeypatch) -> None:
    configure_idp(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "rag-admin.db"))

    response = client.patch(
        "/api/admin/rag/knowledge/ai-governance",
        headers=admin_headers(),
        json={
            "title": "AI governance and RAG routing",
            "category": "ai",
            "summary": "RAG routing separates evidence retrieval, reasoning, and final answer generation.",
            "content": "Use runtime records, delivery evidence, A2A trace, and human approval gates before model execution.",
            "endpoint": "/api/rag/search",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["document"]["doc_id"] == "ai-governance"
    assert body["audit_event_id"]
    search = client.get("/api/rag/search", params={"q": "final answer generation"})
    assert search.status_code == 200
    assert search.json()["matches"][0]["doc_id"] == "ai-governance"
    rejected = client.patch(
        "/api/admin/rag/knowledge/ai-governance",
        headers=admin_headers(),
        json={
            "title": "Invalid contact",
            "category": "ai",
            "summary": "Call 123 456 7890",
            "content": "Contact data must be rejected.",
            "endpoint": "/api/rag/search",
        },
    )
    assert rejected.status_code == 400


def test_chat_response_includes_rag_knowledge_grounding(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "rag-chat.db"))

    response = client.post(
        "/api/chat",
        json={"message": "Which evidence controls recovery approval?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["knowledge_grounding"]
    assert body["knowledge_grounding"][0]["type"] == "rag_knowledge"
    assert body["knowledge_grounding"][0]["endpoint"] == "/api/rag/search"
    assert "recovery" in body["knowledge_grounding"][0]["summary"].lower()
