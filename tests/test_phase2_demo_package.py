# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-03

from fastapi.testclient import TestClient

from agentiot.app import create_app


def test_customer_website_demo_package_is_customer_safe(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "demo-package.db"))

    response = client.get("/api/operations/handoff-package")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "prepared"
    assert body["package_id"] == "greenovax-website-handoff"
    assert body["target_site"] == "www.greenovax.de"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["license"] == "MIT"
    assert "/" in body["entrypoints"]
    assert "/api/operations/scenario" in body["entrypoints"]
    assert "/api/operations/handoff-package" in body["entrypoints"]
    assert "/api/ai/routing" in body["entrypoints"]
    assert all("demo" not in item.lower() for item in body["entrypoints"])
    assert all(not item.startswith("/api/admin") for item in body["entrypoints"])
    assert "/api/demo/reset" not in body["entrypoints"]
    assert body["privacy"]["admin_entrypoints_returned"] is False
    assert body["runtime"]["container_port"] == 8080
    assert body["runtime"]["recommended_host_port"] == 8040
    assert len(body["operator_flow"]) >= 5
    assert body["limitations"][0]


def test_dashboard_shell_does_not_expose_demo_language(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "handoff-shell.db"))

    response = client.get("/")

    assert response.status_code == 200
    assert "demo" not in response.text.lower()
