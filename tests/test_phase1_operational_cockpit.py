# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.152.8 | Date: 2026-07-10

from fastapi.testclient import TestClient

from agentiot.app import create_app


def test_phase1_routes_operational_controls_to_operations_workbench(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "phase1-cockpit.db"))

    root_response = client.get("/")
    operations_response = client.get("/operations")

    assert root_response.status_code == 200
    assert operations_response.status_code == 200
    body = root_response.text
    assert "Operations Control Center" in body
    assert 'aria-label="Operational controls"' in body
    assert 'id="live-operations-workbench" aria-label="Operational controls" hidden' in body
    assert 'id="shell-workbench-refresh-evidence"' in body
    assert "Use the tabs below for current status, live monitoring, asset inventory, alarm handling, workflow execution, and agent control." in body
    assert "bindPhase1OperationalControls();" in body
    assert (
        "const OPERATIONS_WORKBENCH_ROUTES = new Set(Object.keys(OPERATIONS_ROUTE_PANELS));"
        in body
    )
    assert "syncOperationalWorkbenchVisibility(routePath);" in body
    assert "'/operations': { view: 'operate', target: 'operations', operationsPanel: 'summary'" in body
    assert 'class="shell-workspace-tabs"' in body
    assert 'id="shell-telemetry-trend"' in body
    assert "initialSetupPreviewActive" in body
    assert "assetCount: 1248" not in body
    assert "healthScore: 98.6" not in body
    for forbidden_label in (
        "Run Pilot Flow",
        "Customer Website Demo",
        "Raw API evidence",
        "Service evidence endpoints",
        "Pilot Area",
        "Pilot setup needed",
        "Pilot flow",
        "Pilot operation failed",
        "operational Phase 2 console",
        "run the demo flow",
    ):
        assert forbidden_label not in body
    assert 'id="shell-assets-count">1,248' not in body
    assert body.index('class="shell-kpis"') < body.index('id="shell-context-panel"')
    assert body.index('data-open-asset-setup') < body.index('id="shell-assets-count"')
