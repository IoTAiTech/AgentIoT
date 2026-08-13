# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

from fastapi.testclient import TestClient

from agentiot.app import create_app
from agentiot.version import __version__


FORBIDDEN_RESPONSE_TERMS = (
    "unit-" + "operator-" + "sentinel",
    "private " + "prompt",
    "system " + "prompt",
    "chain-of-" + "thought",
    "inter" + "nal",
    "".join(["/", "home", "/", "iot"]),
    ".".join(["192", "168", "50", "40"]),
    "l:" + "\\",
    "c:" + "\\",
)


def test_command_center_exposes_actionable_menu_content(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "command-center.db"))

    response = client.get("/api/operations/command-center")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["summary"]["operational_state"]
    assert body["summary"]["next_action"]
    kpi_ids = {item["kpi_id"] for item in body["kpis"]}
    assert {
        "operations-readiness",
        "agent-readiness",
        "ui-ux-quality",
        "rag-knowledge",
        "pending-recovery",
    }.issubset(kpi_ids)
    assert len(body["command_cards"]) >= 7
    for card in body["command_cards"]:
        assert card["area"]
        assert card["agent_id"]
        assert card["state"]
        assert card["kpi"]
        assert card["next_action"]
        assert card["primary_endpoint"].startswith("/")
        assert card["action_label"]
    assert body["agent_routes"]
    assert body["charts"][0]["chart_id"] == "command-center-readiness"
    lowered = response.text.lower()
    assert all(term not in lowered for term in FORBIDDEN_RESPONSE_TERMS)


def test_command_center_feeds_dashboard_reports(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_BOOTSTRAP_DEMO_DATA", "true")
    client = TestClient(create_app(database_path=tmp_path / "command-reports.db"))

    response = client.get("/api/reports/dashboard")

    assert response.status_code == 200
    body = response.json()
    chart_ids = {chart["chart_id"] for chart in body["charts"]}
    report_ids = {report["report_id"] for report in body["reports"]}
    assert "command-center-readiness" in chart_ids
    assert "operations-command-center" in report_ids
    lowered = response.text.lower()
    assert all(term not in lowered for term in FORBIDDEN_RESPONSE_TERMS)


def test_root_page_contains_command_center_section(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "command-root.db"))

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="#command-center"' in response.text
    assert '<div class="panel wide" id="command-center">' in response.text
    assert "Operational Command Center" in response.text
    assert 'id="command-center-kpis-body"' in response.text
    assert 'id="command-center-cards-body"' in response.text
    assert "function renderCommandCenter(center)" in response.text
    assert "cell.dataset.label" in response.text
    assert "#command-center td::before" in response.text
    assert "loadJsonSafe('/api/operations/command-center')" in response.text
    assert "loadJsonSafe('/api/operations/next-best-action')" in response.text
    assert "nextBestAction.primary_action" in response.text
    assert "Review human approval" in response.text


def test_topbar_and_time_range_controls_are_stateful() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'id="shell-notifications-control"' in body
    assert 'data-shell-target="command-center"' in body
    assert 'id="shell-help-control"' in body
    assert 'data-shell-target="overview"' in body
    assert 'id="shell-display-mode-control"' in body
    assert 'aria-pressed="false"' in body
    assert 'value="15m">Last 15 minutes' in body
    assert 'value="1h">Last hour' in body
    assert 'value="24h">Last 24 hours' in body
    assert 'value="today">Today' in body
    assert "window.sessionStorage" not in body
    assert "function initializeTimeRangeControl()" in body
    assert "function filterByActiveTimeRange(items, timeKey, timeWindow)" in body
    assert "start.setUTCHours(0, 0, 0, 0);" in body
    assert "start.setHours(0, 0, 0, 0);" not in body
    assert "Today (UTC)" in body
    assert "activeTimeRange = event.currentTarget.value" in body
    assert "await refreshData();" in body
    assert "function initializeDisplayModeControl()" in body
    assert "function applyDisplayMode(mode)" in body
    assert "shellMain.dataset.displayMode = nextMode" in body
    assert "activeDisplayMode = nextMode" in body
    assert "Range: ' + event.target.value" not in body


def test_root_page_replaces_seed_workflow_with_asset_setup_navigation() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Operations Control" in body
    assert 'data-open-asset-setup' in body
    assert "Open Asset Setup" in body
    assert 'id="shell-pilot-token"' not in body
    assert 'id="shell-run-pilot-flow"' not in body
    assert 'id="shell-send-critical-telemetry"' in body
    assert 'id="shell-discover-sensor-ci"' in body
    assert "async function runPilotFlow()" not in body
    assert "async function openAssetSetup()" in body
    assert "async function openWorkbenchForm(formId)" in body
    assert "async function openTelemetrySetup()" in body
    assert "async function openDeviceSetup()" in body
    assert "async function sendCriticalTelemetry()" not in body
    assert "async function discoverSensorCI()" not in body
    assert "device_id: 'sensor-1'" not in body
    assert "value: 92" not in body
    assert "/api/hardware/discovery/profiles" in body
    assert "loadControlJsonSafe(controlPath('production', 'readiness-controls')" in body


def test_root_page_exposes_live_operations_workbench() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Operations Control Center" in body
    assert 'aria-label="Operational controls"' in body
    assert 'id="shell-workbench-refresh-evidence"' in body
    assert 'id="shell-workbench-token"' not in body
    assert 'id="shell-workbench-access-state"' in body
    assert "Read-only mode: live evidence is visible. Sign in to run authorized actions." in body
    assert 'data-open-asset-setup' in body
    assert 'id="shell-workbench-telemetry"' in body
    assert 'id="shell-workbench-cmdb"' in body
    simulator_control_start = body.index('id="shell-workbench-simulator"')
    simulator_control = body[simulator_control_start : simulator_control_start + 240]
    assert "hidden" in simulator_control
    assert body.count('data-requires-access="operator-write"') >= 8
    assert body.count('aria-describedby="shell-workbench-access-state"') >= 8
    assert 'id="shell-workbench-telemetry-body"' in body
    assert "<th>Last sample</th><th>State</th><th>Alarm</th>" in body
    assert "summary.telemetry_health?.items" in body
    assert "telemetry_connection_required: 'Telemetry connection needed'" in body
    assert 'id="shell-workbench-cmdb-body"' in body
    assert 'id="shell-workbench-recovery-body"' in body
    assert 'id="shell-workbench-simulator-body"' in body
    assert 'id="shell-workbench-runbook"' in body
    assert 'id="shell-workbench-completion"' in body
    assert 'id="shell-workbench-current-step"' in body
    assert 'id="shell-workbench-next-action"' in body
    assert 'id="shell-workbench-last-action"' in body
    assert 'id="shell-workbench-last-evidence"' in body
    assert 'id="shell-workbench-last-state"' in body
    assert "No runtime action yet" in body
    assert "Operator Actions" in body
    assert "function renderWorkbenchOutcome(outcome)" in body
    assert "operationsWorkbench?.last_action" in body
    assert "function renderOperationalRunbook(workbench, simulatorEnabled = true)" in body
    assert "loadJsonSafe('/api/operations/workbench')" in body
    assert "data-workbench-action" in body
    assert "runbookActionMap" in body
    assert 'id="shell-workbench-sensors"' in body
    assert 'data-density-priority="sensor-cis"' in body
    assert 'id="shell-asset-form"' in body
    assert 'id="shell-device-form"' in body
    assert 'id="shell-asset-update-form"' in body
    assert 'id="shell-device-update-form"' in body
    assert 'id="shell-telemetry-form"' in body
    assert 'id="shell-recovery-form"' in body
    assert 'id="shell-alert-select"' in body
    assert 'id="shell-proposal-select"' in body
    assert 'name="operator_name"' not in body
    assert "payload.operator_name" not in body
    assert "Approval identity is recorded from the authenticated operator session." in body
    assert "overview-cmdb-sensors" in body
    assert body.index('id="shell-workbench-cmdb-body"') < body.index('id="shell-asset-form"')
    assert body.index('id="shell-workbench-telemetry-body"') < body.index('id="shell-asset-form"')
    assert body.index('id="shell-workbench-sensors"') < body.index('id="shell-asset-form"')
    assert "async function submitWorkbenchAsset" in body
    assert "async function submitWorkbenchDevice" in body
    assert "async function submitWorkbenchAssetUpdate" in body
    assert "async function submitWorkbenchDeviceUpdate" in body
    assert "async function loadOperatorJson" in body
    assert "loadDiscoveryCandidates()" in body
    assert "async function patchJson" in body
    assert "encodeURIComponent(update.id)" in body
    assert "async function submitWorkbenchTelemetry" in body
    assert "async function submitWorkbenchRecovery" in body
    assert "bindWorkbenchForm('shell-asset-form'" in body
    assert "bindWorkbenchForm('shell-asset-update-form'" in body
    assert "bindWorkbenchForm('shell-device-update-form'" in body
    assert "bindWorkbenchForm('shell-recovery-form'" in body
    assert "function renderLiveOperationsWorkbench(" in body
    first_fetch = body.index("loadJsonSafe('/api/operations/summary?window='")
    first_render = body.index("renderLiveOperationsWorkbench(\n          summary,\n          telemetryQuick")
    full_refresh = body.index("loadJson('/api/config/profiles')")
    assert first_fetch < first_render < full_refresh
    assert "loadJsonSafe('/api/cmdb/configuration-items')" in body
    assert "loadJsonSafe('/api/hardware/discovery')" in body
    assert "loadJsonSafe('/api/hardware/discovery/candidates', { items: [], summary: {} })" not in body
    assert "loadJsonSafe('/api/telemetry')" in body
    assert "function sensorFirstCIRows(" in body
    assert "sensorFirstCIRows(cmdb.items || [], 6)" in body
    assert "sensorFirstCIRows(cmdb.items || [], 8)" in body
    assert "hardwareSummary.validation_coverage_percent" in body
    assert "hardwareWorkflow.next_action" in body
    assert "id=\"shell-commissioning-validated\"" in body
    assert "id=\"shell-commissioning-coverage\"" in body
    assert "id=\"shell-commissioning-next-action\"" in body
    assert "managementSummary.validated_sensor_count" in body
    assert "managementSummary.validation_coverage_percent" in body
    assert "managementSummary.next_action" in body
    assert ".shell-workbench-grid .shell-workbench-pane:nth-child(2)" in body
    assert ".shell-command-card small" in body
    assert "renderWorkbenchOptions(" in body
    assert "runHardwareSimulatorWorkbench" in body
    assert "simulatorEnabled" in body
    assert "simulatorControl.hidden = !simulatorEnabled" in body
    assert "function updateWorkbenchActionAvailability()" in body
    assert "function bindSessionAvailability()" in body
    assert "function bindOperatorTokenAvailability()" not in body
    assert "function syncOperatorTokenInputs(source)" not in body
    assert "field.disabled = !enabled" in body
    assert "bindSessionAvailability();" in body
    assert "const lastSimulatorRun = runs[0] || {}" in body
    assert "lastSimulatorRun.ignored_profiles" in body
    simulator_start = body.index("async function runHardwareSimulatorWorkbench()")
    simulator_end = body.index("async function submitWorkbenchAsset", simulator_start)
    simulator_workbench = body[simulator_start:simulator_end]
    assert "profiles: ['greenhouse_temperature', 'oxygen_concentration']" in simulator_workbench
    assert "oxygen_level" not in simulator_workbench
    assert "Grounded fallback active" in body
    assert "Ask grounded operations evidence" in body
    assert "route.runtime_allowed === true" in body
    assert 'id="shell-system-state"' in body
    assert "Action required" in body
