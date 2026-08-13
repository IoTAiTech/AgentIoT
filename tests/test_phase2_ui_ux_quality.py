# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

import json
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from agentiot import __version__
from conftest import admin_token_headers
from agentiot.app import create_app
from agentiot.visual_quality import build_visual_qa_evidence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_node_json(source: str) -> dict[str, object]:
    result = subprocess.run(
        ["node", "-e", source],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    luminances = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (luminances[0] + 0.05) / (luminances[1] + 0.05)


def _css_rule(source: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", source, re.DOTALL)
    assert match, f"missing CSS selector: {selector}"
    return match.group("body")


def _css_hex_property(rule: str, property_name: str) -> str:
    match = re.search(
        rf"(?:^|\n)\s*{re.escape(property_name)}\s*:\s*(#[0-9a-fA-F]{{6}})\s*;",
        rule,
    )
    assert match, f"missing hexadecimal CSS property: {property_name}"
    return match.group(1)


def test_ui_ux_quality_gate_exposes_auditor_and_controls(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-ux-gate.db"))

    response = client.get("/api/ui/quality-gate")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["agent_id"] == "ui_ux_experience_auditor"
    assert body["auditor_role"] == "UI_UX_Quality_Auditor"
    assert body["score"] == round(sum(gate["state"] == "ready" for gate in body["gates"]) / len(body["gates"]) * 100)
    assert all(gate["state"] == "ready" for gate in body["gates"] if gate["gate_id"] != "browser-visual-qa-required")
    assert "WCAG 2.2 AA" in body["standards"]
    assert "ISO/IEC 25010" in body["standards"]
    assert body["metrics"]["raw_json_menu_links"] == 0
    assert body["metrics"]["section_anchor_links"] >= 10
    assert body["metrics"]["shell_context_targets"] >= 8
    assert body["metrics"]["shell_route_contexts"] >= 18
    assert body["metrics"]["shell_context_cards"] >= 12
    assert body["metrics"]["topbar_operational_controls"] >= 4
    assert body["metrics"]["right_rail_action_controls"] >= 3
    assert body["metrics"]["kpi_trend_signals"] >= 4
    assert body["metrics"]["legend_controls"] >= 2
    assert body["metrics"]["map_visual_hooks"] >= 3
    assert body["metrics"]["map_quality_hooks"] >= 6
    assert body["metrics"]["queue_visual_hooks"] >= 3
    assert body["metrics"]["live_action_queue_ready"] is True
    assert body["metrics"]["mobile_primary_cockpit_above_rail"] is True
    assert body["metrics"]["reference_fidelity_hooks"] >= 4
    assert body["metrics"]["visual_browser_audit_hooks"] >= 3
    assert body["metrics"]["report_workspace_hooks"] >= 5
    assert body["metrics"]["test_workspace_hooks"] >= 5
    assert body["metrics"]["evidence_workspace_hooks"] >= 5
    assert body["metrics"]["first_screen_cmdb_sensor_hooks"] >= 6
    assert body["metrics"]["workbench_data_before_write_controls"] is True
    assert body["metrics"]["workbench_session_clarity_hooks"] >= 8
    assert body["metrics"]["legacy_workspace_locked"] is True
    assert body["metrics"]["settings_panel_contained"] is True
    visual = body["visual_evidence"]
    assert visual["customer_safe"] is True
    assert visual["source_version"].startswith(f"{__version__}+")
    assert visual["live_version"] == __version__
    assert visual["status"] in {"PASS", "STALE", "PENDING"}
    if visual["status"] == "PASS":
        assert visual["freshness"]["status"] == "fresh"
        assert body["score"] == 100
    else:
        assert visual["freshness"]["status"] in {"missing", "stale", "invalid", "future", "fresh"}
        assert "browser-visual-qa-required" in body["blocked_items"]
        assert body["score"] < 100
    assert visual["freshness"]["max_age_hours"] == 6
    assert visual["passed_count"] == visual["check_count"] >= 18
    assert visual["route_count"] >= 5
    assert visual["viewport_count"] >= 3
    assert visual["screenshot_count"] >= 15
    assert visual["missing_routes"] == []
    assert visual["missing_viewports"] == []
    assert visual["missing_route_viewport_pairs"] == []
    assert visual["missing_screenshots"] == []
    assert isinstance(visual["console_error_count"], int)
    assert isinstance(visual["console_warning_count"], int)
    assert all(route.startswith("/") for route in visual["console_error_routes"])
    forbidden_console_prefix = "http"
    assert forbidden_console_prefix not in " ".join(visual["console_error_routes"])
    for route in (
        "/",
        "/operations",
        "/charts",
        "/analytics",
        "/status",
        "/reports",
        "/tests",
        "/evidence",
        "/settings",
    ):
        assert route in visual["covered_routes"]
    for viewport in ("mobile", "desktop", "desktop-wide"):
        assert viewport in visual["covered_viewports"]
    assert visual["report_attached"] is True
    assert visual["evidence_ref"] == "visual-qa-current"
    assert "report_path" not in visual
    assert "screenshot_path" not in visual
    assert "screenshot_paths" not in visual
    assert "output/playwright" not in response.text
    forbidden_home = "/" + "home" + "/" + "iot"
    forbidden_drive = "C" + ":"
    forbidden_host = ".".join(["192", "168", "50", "40"])
    assert forbidden_home not in response.text
    assert forbidden_drive not in response.text
    assert forbidden_host not in response.text
    gate_ids = {gate["gate_id"] for gate in body["gates"]}
    assert "primary-navigation" in gate_ids
    assert "raw-json-navigation-prevention" in gate_ids
    assert "menu-context-ownership" in gate_ids
    assert "deep-link-routing" in gate_ids
    assert "chart-readability" in gate_ids
    assert "industrial-aesthetic" in gate_ids
    assert "reference-cockpit-fidelity" in gate_ids
    assert "browser-visual-qa-required" in gate_ids
    assert "reports-workspace-visibility" in gate_ids
    assert "tests-workspace-visibility" in gate_ids
    assert "evidence-workspace-visibility" in gate_ids
    assert "industrial-cockpit-density" in gate_ids
    assert "mobile-primary-cockpit-before-rail" in gate_ids
    assert "first-screen-cmdb-sensor-visibility" in gate_ids
    assert "workbench-session-readonly-clarity" in gate_ids
    assert "responsive-accessibility" in gate_ids



def test_shell_context_cards_hide_raw_api_evidence_labels(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-ux-copy.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    context_start = body.index("function renderShellContext(contextId)")
    context_end = body.index("function closeDetailedWorkspace", context_start)
    context_renderer = body[context_start:context_end]
    assert "function evidenceDisplayLabel(card)" not in body
    assert "function stableEvidenceRef(value)" not in body
    assert "Evidence source: " not in context_renderer
    assert "stableEvidenceRef" not in context_renderer
    assert ".replace(/\\/api\\//g, 'service ')" in body
    assert "ownerDisplayLabel(route.route_id, 'AI route')" in body
    assert "function operatorStatusLabel(value" in body
    assert "operatorStatusLabel(runtime.runtime_claim, 'Unknown')" in body
    assert "operatorStatusLabel(confidence)" in body
    assert "liveRecordCount > 0" in body
    assert "runtimeRecordCount > 0" in body
    assert "'Not measured'" in body
    assert "meta: 'operations_coordinator" not in body
    assert "evidence.dataset.evidenceEndpoint = card.evidence" not in body
    assert "evidence.textContent = 'Evidence: ' + card.evidence" not in body


def test_customer_visible_shell_uses_operational_language(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-ux-language.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Automation Orchestration Surface" in body
    assert "Service Readiness" in body
    assert "workflow handoff" in body
    assert "Answer Quality" in body
    assert "Knowledge quality" in body
    assert "Operator-safe menu links" in body
    assert "Workflow handoffs" in body
    assert "Handoff steps" in body
    assert "Next handoff" in body
    assert "handoff policy" in body
    assert "title=\"/api" not in body
    assert "Raw service Menu Links" not in body
    assert "technical payload" not in body.lower()
    assert "<span>A2A Links</span>" not in body
    assert "<th>A2A Links</th>" not in body
    assert "<th>A2A Next Hop</th>" not in body
    assert "<th>A2A Step</th>" not in body
    assert "Release Evidence" not in body
    assert "Agent Orchestration Surface" not in body
    assert '<span class="label">QA KPI</span>' not in body
    assert "Charts and reports summarize operations, automation, QA" not in body
    assert "automation runs, QA, knowledge" not in body
    assert "RAG quality" not in body
    assert "A2A trace" not in body
    assert "Change AI route, model policy, and QA controls" not in body
    assert "CMDB records</span>" not in body
    assert "CMDB evidence" not in body
    assert "HITL proposals" not in body
    assert "Review HITL" not in body
    assert "RAG Knowledge Center" not in body
    assert "Assistant Q/A Challenge" not in body
    assert "Assistant Q/A challenge" not in body
    assert "Sensors become CIs" not in body
    assert "Operational Review Board" in body
    assert "shell-report-ops-board" in body
    assert "Asset coverage" in body
    assert "Operational source" in body
    assert "Operational reports appear after connected assets generate live evidence." not in body


def test_public_operational_api_labels_are_human_readable(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-api-language.db"))
    forbidden_labels = (
        "Promote sensor to " + "CMDB",
        "Discover sensor " + "CI",
        "Close " + "HITL" + " recovery loop",
        "A2A" + " steps",
        "RAG" + " Knowledge Coverage",
        "Send critical telemetry",
        "Discover sensor record",
    )

    for path in ("/api/operations/workbench", "/api/reports/dashboard"):
        response = client.get(path)

        assert response.status_code == 200
        body = response.text
        for label in forbidden_labels:
            assert label not in body
        assert "sensor inventory" in body or "Knowledge Coverage" in body
        assert "human approval" in body or "Handoff steps" in body or path == "/api/reports/dashboard"


def test_time_range_control_persists_operator_context(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-time-range.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "const TIME_RANGE_STORAGE_KEY = 'agentiot.shell.timeRange'" in body
    assert "window.localStorage.getItem(TIME_RANGE_STORAGE_KEY)" in body
    assert "window.localStorage.setItem(TIME_RANGE_STORAGE_KEY, activeTimeRange)" in body
    assert "start.setUTCHours(0, 0, 0, 0);" in body
    assert "Today (UTC)" in body
    assert "time range was not persisted after reload" in (
        PROJECT_ROOT / "tools" / "run_visual_qa.js"
    ).read_text()


def test_root_overview_and_contextual_rail_are_route_specific(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-route-layout.db"))

    for path in ("/", "/operations", "/settings", "/analytics", "/evidence", "/tests", "/reports", "/about"):
        assert client.get(path).status_code == 200

    body = client.get("/").text
    assert 'data-rail-panel="queue"' in body
    assert 'data-rail-panel="operations" hidden' in body
    assert 'data-rail-panel="assistant"' in body
    assert "const ROOT_RAIL_ROUTES = new Set(['/', '/dashboard', '/cockpit']);" in body
    assert "const OPERATIONS_RAIL_ROUTES = new Set(['/operations']);" in body
    assert "'/settings', '/analytics', '/evidence', '/tests', '/reports', '/about'" in body
    assert "function syncContextualRail(pathname)" in body
    assert 'data-rail-mode="none"' in body
    assert '.dashboard-shell[data-rail-mode="none"]' in body
    assert '.shell-workbench[hidden]' in body
    assert body.index('class="shell-kpis"') < body.index('class="shell-grid"')
    assert body.index('class="shell-grid"') < body.index('id="shell-context-panel"')


def test_quick_actions_open_user_completed_forms_without_synthetic_posts(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-real-form-actions.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    action_start = body.index("async function openWorkbenchForm")
    action_end = body.index("async function runHardwareSimulatorWorkbench", action_start)
    action_source = body[action_start:action_end]
    assert "async function sendCriticalTelemetry" not in body
    assert "async function discoverSensorCI" not in body
    assert "device_id: 'sensor-1'" not in action_source
    assert "value: 92" not in action_source
    assert "device_id: 'sensor-usb-rpi5-1'" not in action_source
    assert "openWorkbenchForm('shell-telemetry-form'" in body
    assert "openWorkbenchForm('shell-device-form'" in body
    assert "window.openInitialShellRoute?.();" in action_source
    assert "window.openInitialShellRoute = openInitialShellRoute;" in body
    assert "form?.querySelector('input, select, button')?.focus();" in action_source
    assert "window.setTimeout(() => {\n          form?.querySelector('input, select, button')?.focus();" not in action_source
    assert 'id="shell-workflow-token"' not in body
    assert "const workflowToken = document.getElementById('shell-workflow-token')" not in body
    assert 'id="shell-workflow-access-state"' in body
    assert "control.querySelectorAll('input, select, textarea')" in body
    assert "field.disabled = !enabled || blockedByRunbook;" in body
    visual_qa = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()
    assert "const writesBeforeSetup = writeRequests.length;" in visual_qa
    assert "const setupWriteRequests = writeRequests.slice(writesBeforeSetup);" in visual_qa
    assert "const setupMutationRequests = setupWriteRequests.filter" in visual_qa
    assert "'shell-workbench-open-asset-setup': openAssetSetup" in body
    assert "'shell-workbench-cmdb': openDeviceSetup" in body
    assert "Open Telemetry Form" in body
    assert "Open Device Setup" in body


def test_assistant_shortcuts_run_grounded_requests_instead_of_static_context(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-assistant-shortcuts.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert body.count("data-assistant-prompt=") == 3
    assert "document.querySelectorAll('[data-assistant-prompt]')" in body
    assert "form.requestSubmit();" in body
    assert "client_message_id: 'shell-right-rail-' + Date.now()" in body


def test_intelligence_and_reports_open_their_primary_operational_workspaces(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-primary-workspaces.db"))

    body = client.get("/insights").text

    assert 'id="assistant-workbench-input"' in body
    assert 'id="assistant-workbench-response"' in body
    assert "const isAssistantLanding = fallbackId === 'assistant';" in body
    assert "ledgerPanel.hidden = isAssistantLanding || !ASSISTANT_LEDGER_CONTEXTS.has(fallbackId);" in body
    assert "aiAssurancePanel.hidden = isAssistantLanding || !ASSISTANT_WORKBENCH_CONTEXTS.has(fallbackId);" in body
    assert "const ASSISTANT_WORKBENCH_CONTEXTS = new Set([\n        'assistant'\n      ]);" in body
    assert "const RAG_QUALITY_CONTEXTS = new Set([\n        'rag-knowledge'\n      ]);" in body
    assert "const MODEL_BENCHMARK_CONTEXTS = new Set([\n        'ai-control'\n      ]);" in body
    assert "const SINGLE_SURFACE_CONTEXTS = new Set([" in body
    assert "target.hidden = SINGLE_SURFACE_CONTEXTS.has(fallbackId)" in body
    assert "shellMain.scrollHeight > shellMain.clientHeight + 1" in body
    assert "shellMain.scrollTo({ top: destination, behavior: 'auto' });" in body
    assert "scrollTarget.getBoundingClientRect().top" in body
    assert "let initialWorkspaceDataRefresh = true;" in body
    assert "function scrollWorkspaceIntoView(scrollTarget)" in body
    assert "initialWorkspaceScrollTarget = scrollTarget.id;" in body
    assert "initialWorkspaceScrollTarget = shellTop.id;" in body
    assert "window.setTimeout(() => scrollWorkspaceIntoView(shellTop), 0);" in body
    assert "scrollWorkspaceIntoView(target);" in body
    assert "function reportWorkspaceMetaLabel(chart)" in body
    assert "Assistant Reviews" in body
    assert '.shell-main:not([data-active-context="cockpit"]) > .shell-heading' in body
    assert '.shell-main:not([data-active-context="cockpit"]) > .shell-kpis' in body
    assert '.shell-main:not([data-active-context="cockpit"]) > .shell-grid > .shell-panel' in body
    assert '.shell-main:not([data-active-context="operations"]) > #live-operations-workbench' in body


def test_empty_runtime_routes_to_real_setup_actions_without_synthetic_data(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-setup-actions.db"))

    body = client.get("/insights").text

    assert '<button id="shell-system-state"' in body
    assert 'id="shell-readiness-setup"' in body
    assert 'id="assistant-workbench-setup-actions" hidden' in body
    assert 'id="shell-report-setup-actions" hidden' in body
    assert 'id="shell-report-metrics"' in body
    assert 'id="advanced-admin-token"' not in body
    assert 'id="advanced-admin-password"' in body
    assert 'id="advanced-admin-login"' in body
    assert "document.querySelectorAll('[data-open-operational-form]')" in body
    assert "openWorkbenchForm(control.dataset.openOperationalForm" in body
    assert "async function loginAdminSession()" in body
    assert "browserSession = result;" in body
    assert "Run Operational Workflow" not in body
    assert (
        "Use the operational command cards above for controlled actions."
        in body
    )
    assert "reportSetupActions.hidden = hasRuntimeData;" in body
    assert "reportMetrics.hidden = !hasRuntimeData;" in body


def test_operations_uses_bounded_task_workspaces_and_canonical_navigation(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-bounded-workspaces.db"))

    response = client.get("/operations")

    assert response.status_code == 200
    body = response.text
    assert 'class="shell-workspace-tabs"' in body
    for panel in ("summary", "monitoring", "assets", "alarms", "workflows", "control"):
        assert f'data-workspace-tab="{panel}"' in body
    assert 'id="shell-telemetry-trend"' in body
    assert "function selectOperationsWorkspace(panelId)" in body
    assert "const LEGACY_SHELL_ROUTE_ALIASES" not in body
    assert "const OPERATIONS_ROUTE_PANELS" in body
    assert "const OPERATIONS_PANEL_ROUTES" in body
    assert "return pathname || '/';" in body
    assert "window.history.replaceState({ route: routePath" not in body
    assert "window.history.pushState({ route: '/workflows'" in body
    assert "window.selectOperationsWorkspace?.('workflows');" in body
    assert "const agentRoutes = new Set(['/orchestrator', '/registry', '/actions']);" in body
    assert "'/actions', '/releases'" not in body
    assert "renderTelemetryTrend(telemetryItems);" in body
    assert "['/', 'root']" in (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()
    assert "['/insights', 'intelligence']" in (
        PROJECT_ROOT / "tools" / "run_visual_qa.js"
    ).read_text()
    assert "['/charts', 'charts']" in (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()
    assert "['/evidence', 'evidence']" in (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()


def test_primary_navigation_and_operations_tabs_are_accessible(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-navigation-a11y.db"))
    body = client.get("/operations").text

    assert 'href="#dashboard-shell" aria-current="page"' in body
    for control_id in (
        "shell-service-solve",
        "shell-service-auto-heal",
        "shell-service-self-check",
        "shell-service-debug-dump",
    ):
        tag = re.search(rf'<button[^>]*id="{control_id}"[^>]*>', body)
        assert tag and 'aria-disabled="true"' in tag.group(0)
        assert re.search(r"\sdisabled(?:\s|>)", tag.group(0))
    assert 'class="shell-primary-nav"' in body
    assert "document.querySelectorAll('.shell-primary-nav a[href]')" in body
    assert "item.removeAttribute('aria-current');" in body
    assert "link.setAttribute('aria-current', 'page');" in body
    assert 'role="tablist" aria-label="Operations workspace" aria-orientation="horizontal"' in body
    assert 'id="shell-workspace-tabs-more"' not in body
    for panel in ("summary", "monitoring", "assets", "alarms", "workflows", "control"):
        assert f'id="operations-tab-{panel}"' in body
        assert 'aria-controls="operations-workspace-panel"' in body
    assert 'id="operations-workspace-panel" role="tabpanel"' in body
    assert "function handleOperationsTabKeydown(event)" in body
    for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
        assert f"'{key}'" in body
    assert "window.history.replaceState(" in body
    assert "scrollIntoView({ block: 'nearest', inline: 'nearest' })" in body


def test_customer_shell_normal_text_colors_meet_wcag_aa_contrast() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()

    for legacy_token in ("#11885d", "#0b8f5e", "#d97706"):
        assert legacy_token not in source.lower()

    foreground_background_pairs = (
        ("button.primary", "color", "background"),
        (".shell-refresh", "color", "background"),
        (".shell-assistant-input button", "color", "background"),
        (".shell-kpi-icon.warn", "color", "background"),
        (".queue-chip.medium", "color", "background"),
    )
    for selector, foreground_property, background_property in foreground_background_pairs:
        rule = _css_rule(source, selector)
        foreground = _css_hex_property(rule, foreground_property)
        background = _css_hex_property(rule, background_property)
        assert _contrast_ratio(foreground, background) >= 4.5, selector

    for selector in (".shell-kpi-trend", ".shell-kpi-trend.warn"):
        foreground = _css_hex_property(_css_rule(source, selector), "color")
        assert _contrast_ratio(foreground, "#ffffff") >= 4.5, selector


def test_api_failure_state_is_distinct_from_successful_empty_state(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-api-state.db"))
    body = client.get("/").text

    assert 'id="shell-data-load-state"' in body
    assert "Core operational data remains current." in body
    assert "Live data unavailable. Empty values may not reflect" not in body
    assert "const liveLoadFailures = new Set();" in body
    assert "function recordLiveLoad(path, failed)" in body
    assert "recordLiveLoad(path, true);" in body
    assert "recordLiveLoad(path, false);" in body
    assert "Operational data unavailable in " in body
    assert "dashboardFallback(path)" in body


def test_visual_qa_covers_tablet_navigation_scroll_and_about_geometry() -> None:
    source = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()

    assert "['tablet', { width: 1024, height: 768 }]" in source
    assert "activePrimaryCount" in source
    assert "ariaCurrentPrimaryCount" in source
    assert "sameAxisNestedScrollCount" in source
    assert "cockpitMainWidth" in source
    assert "cockpitKpiFirstRowCount" in source
    assert "cockpitContentClipCount" in source

    body = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()
    assert "@media (min-width: 761px) and (max-width: 1180px)" in body
    assert '"sidebar rail"' in body
    assert "focusableClipCount" in source
    assert "aboutGeometryReady" in source


def test_read_only_session_disables_write_form_fields(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-read-only-forms.db"))

    body = client.get("/operations").text

    assert "field.disabled = !enabled || blockedByRunbook;" in body
    assert "const adminForms = new Set();" in body
    assert "adminForms.forEach((form) => {" in body
    assert "field.disabled = !adminEnabled;" in body


def test_fleet_topology_uses_live_cmdb_relations_without_synthetic_geography(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-empty-map.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Fleet Topology" in body
    assert "Asset Locations" not in body
    assert 'id="shell-map-asset-layer" hidden' in body
    assert 'id="shell-map-empty-state"' in body
    assert "No registered asset relationships" in body
    assert "function renderShellMapState(cmdb)" in body
    assert "cmdb.relations" in body
    assert "renderShellMapState(cmdb);" in body
    assert "class=\"map-land\"" not in body
    assert "class=\"map-marker\"" not in body


def test_zero_runtime_data_uses_honest_neutral_visuals(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-honest-zero-state.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'id="shell-health-score">Not measured</strong>' in body
    assert 'id="shell-readiness-score">Waiting</strong>' in body
    assert '.donut[data-empty="true"]' in body
    assert 'id="shell-assets-donut" data-empty="true"' in body
    assert 'id="shell-type-donut" data-empty="true"' in body
    assert "const operationalDataReady = telemetryCount > 0;" in body
    assert "assetsDonut.dataset.empty = String(assetCount === 0);" in body
    assert "typeDonut.dataset.empty = String(typedDeviceCount === 0);" in body
    assert "'shell-readiness-storage'" in body
    assert "'Not connected'" in body
    assert 'id="shell-readiness-security">No evidence</strong>' in body
    assert "const auditEventCount = Number(counters.audit_events || 0);" in body
    assert "auditEventCount > 0" in body
    assert "'No evidence'" in body
    assert "setShellText('shell-readiness-security', 'Ready');" not in body


def test_empty_runtime_hides_only_decorative_asset_panels() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()
    assert len(re.findall(r'<[^>]*\bdata-empty-optional="true"[^>]*>', source)) == 3
    opt_in_panels = re.findall(
        r'<div\b[^>]*\bdata-empty-optional="true"[^>]*>\s*'
        r'<div[^>]*>\s*<h3>([^<]+)</h3>',
        source,
    )

    assert opt_in_panels == [
        "Top Assets by Status",
        "Fleet Topology",
        "Device Type Distribution",
    ]
    assert (
        '.shell-main[data-runtime-state="empty"] > .shell-grid > '
        '.shell-panel[data-empty-optional="true"]'
    ) in source


def test_cockpit_asset_metrics_do_not_mix_device_and_alert_record_counts(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-asset-metrics.db"))

    body = client.get("/").text
    assert "const assetCount = assetIds.size;" in body
    assert "Math.max(\n          Number(counters.assets || 0),\n          assets.items.length" not in body
    assert "const criticalAssetIds = new Set();" in body
    assert "const warningAssetIds = new Set();" in body
    assert "const offlineAssetIds = new Set();" in body
    assert "critical: criticalAssetIds.size" in body
    assert "warning: warningAssetIds.size" in body
    assert "offline: offlineAssetIds.size" in body
    assert "function setDonutSegments(target, values)" in body
    assert "setDonutSegments(assetsDonut" in body
    assert "setDonutSegments(typeDonut" in body
    assert "#24a96f 0 72%" not in body
    assert "Device Type Distribution" in body
    assert "Asset Type Distribution" not in body


def test_firmware_drift_is_visible_in_asset_workspace_and_detail_table(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-firmware-drift.db"))

    body = client.get("/assets").text

    assert 'id="shell-firmware-drift-body"' in body
    assert 'id="firmware-drift-body"' in body
    assert "loadJsonSafe('/api/firmware/drift')" in body
    assert "loadJson('/api/firmware/drift')" in body
    assert "renderFirmwareDrift(firmwareDriftQuick.items || []);" in body
    assert "renderFirmwareDrift(firmwareDrift.items || []);" in body
    assert "['device_id', 'versions', 'status']" in body
    assert "operatorStatusLabel(item.status, 'Unknown')" in body


def test_actions_route_renders_public_orchestration_without_legacy_scope_shape(
    tmp_path,
) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-actions-route.db"))

    body = client.get("/actions").text

    assert "const agentRoutes = new Set(['/orchestrator', '/registry', '/actions']);" in body
    assert "card.permissions.target_scopes ||" in body
    assert "...(card.permissions.data_scopes || [])" in body
    assert (
        ".replace(/\\bagent_to_agent_traceability\\b/g, "
        "'Workflow handoff traceability')"
    ) in body
    assert "decision.textContent = operatorVisibleText(item.decision);" in body
    assert "renderOrchestrationMatrix(matrix);" in body
    assert "renderArchitectureADR(adr);" in body


def test_operations_workbench_exposes_live_signal_path(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-live-signal-path.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'id="shell-workbench-live-path"' in body
    for signal in ("assets", "devices", "telemetry", "alarms", "cmdb", "recovery"):
        assert f'data-signal-kind="{signal}"' in body
    assert "function updateSignalNode" in body
    assert "function bindSignalPathNavigation" in body
    assert "signalPathHasTelemetryAndCmdb" in (
        PROJECT_ROOT / "tools" / "run_visual_qa.js"
    ).read_text()


def test_operations_workbench_exposes_sensor_commissioning_panel(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-sensor-commissioning.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'id="shell-sensor-commissioning-card"' in body
    assert "Live Sensor Commissioning" in body
    assert "Sensor Inventory Records" in body
    assert "Asset Discovery Queue" in body
    assert "Run asset discovery" in body
    assert "Approve sensor record" in body
    assert "Open Device Setup" in body
    assert "No discovered sensor records yet" in body
    assert "Discovery Queue" in body
    assert "Validated Sensors" in body
    assert "Validation Coverage" in body
    assert "Next Validation Action" in body
    assert "Persistence" in body
    assert "Restore Test" in body
    assert 'id="shell-commissioning-validated"' in body
    assert 'id="shell-commissioning-coverage"' in body
    assert 'id="shell-commissioning-next-action"' in body
    assert 'id="shell-commissioning-approve-profile"' in body
    assert 'id="shell-commissioning-run-restore"' in body
    assert 'id="shell-network-discovery-form"' in body
    assert 'id="shell-network-candidates-body"' in body
    assert 'id="shell-network-approval-form"' in body
    assert 'id="shell-topology-filter-form"' in body
    assert "I authorize this bounded TCP-connect scan" in body
    assert "Approve selected candidate" in body
    assert 'data-requires-access="admin-control"' in body
    assert "function renderSensorCommissioning" in body
    assert "managementSummary.validated_sensor_count" in body
    assert "managementSummary.validation_coverage_percent" in body
    assert "managementSummary.next_action" in body
    assert "function approveQueuedDiscovery" in body
    assert "function runBoundedNetworkDiscovery" in body
    assert "function renderDiscoveryCandidates" in body
    assert "protocol_hints: node.protocol_hints || []" in body
    assert "connection_protocols: node.connection_protocols || []" in body
    assert "value + ' (unverified hint)'" in body
    assert "selectedDiscoveryCandidateId" in body
    assert "loadJsonSafe('/readyz')" in body
    assert "loadJsonSafe('/api/production/backup-retention')" in body
    assert "loadDiscoveryCandidates()" in body
    assert "loadJson('/api/hardware/discovery/candidates')" not in body
    assert "postJson('/api/hardware/discovery/candidates'" not in body
    assert "queued discovery candidate" in body
    assert "Discover Sensor CI" not in body
    assert "CI / CMDB Records" not in body
    assert "postControlJson(controlPath('production', 'restore-test'), {})" in body
    assert "hasSensorCommissioning" in (
        PROJECT_ROOT / "tools" / "run_visual_qa.js"
    ).read_text()


def test_discovery_queue_filters_counts_and_selection_gate_are_explicit() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()

    for control_id in (
        "shell-network-candidate-filter-form",
        "shell-network-status-filter",
        "shell-network-source-filter",
        "shell-network-protocol-filter",
        "shell-network-candidates-count",
        "shell-network-candidates-load-more",
        "shell-network-candidates-retry",
    ):
        assert f'id="{control_id}"' in source
    assert "const DISCOVERY_CANDIDATE_LIMIT = 12;" in source
    assert "const filteredItems = items.filter((item) => (" in source
    assert "const shownItems = filteredItems.slice(0, visibleLimit);" in source
    assert "'Showing ' + shownCount + ' of ' + totalCount" in source
    assert "hardwareDiscoveryCandidatesCache.summary?.has_more" in source
    assert "loadDiscoveryCandidates({ append })" in source
    assert "discoveryCandidateFilterForm?.addEventListener('change'" not in source

    assert (
        'id="shell-commissioning-approve-profile" '
        'data-requires-access="operator-write" aria-describedby="shell-workbench-access-state" '
        'aria-disabled="true" disabled'
    ) in source
    assert (
        'id="shell-network-approval-submit" type="submit" '
        'aria-disabled="true" disabled'
    ) in source
    assert "function updateDiscoveryApprovalAvailability()" in source
    assert "visibleQueuedDiscoveryCandidateIds = new Set(queueView.queuedCandidateIds);" in source
    assert "visibleQueuedDiscoveryCandidateIds.has(" in source
    assert "const approvalEnabled = hasQueuedSelection && hasOperatorAccess();" in source
    assert "button.disabled = !approvalEnabled;" in source
    assert "button.setAttribute('aria-disabled', String(!approvalEnabled));" in source
    assert source.count("updateDiscoveryApprovalAvailability();") >= 5
    assert "selectedDiscoveryCandidateFingerprint" in source
    assert "selectedDiscoveryCandidateRevision" in source
    assert "const reviewedFingerprint = selectedDiscoveryCandidateFingerprint;" in source
    assert "Discovery evidence changed after review" in source
    assert "expected_fingerprint: reviewedFingerprint" in source
    assert "payload.expected_revision = reviewedRevision;" in source
    assert "clearDiscoveryMappingFields();" in source
    assert "updateDiscoveryFilterOptions(items, payload.facets || {});" in source
    assert "query.set('snapshot_revision', queueRevision);" in source
    assert "return loadDiscoveryCandidates();" in source
    assert "mergedItems.set(String(item.candidate_id || ''), item);" in source
    assert "hardwareDiscoveryCandidatesCache?.summary?.queued_count ??" in source
    assert "discoveryCandidates?.load_state || 'not_loaded'" in source
    assert "? 'Sign-in required'" in source
    assert "'shell-commissioning-approve-profile'" in source

    assert 'name="device_id" autocomplete="off"' in source
    assert "'device_id'," in source
    assert 'id="shell-network-mapping-mode"' in source
    assert "profileMappingLocked" in source
    assert "const mappingLocked = !selected || profileMappingLocked;" in source
    assert "control.disabled = mappingLocked;" in source
    assert "mapping fields are disabled" in source
    assert "load_state: 'sign_in_required'" in source
    assert "load_state: 'unavailable'" in source
    assert "candidate count unavailable" in source
    assert "const hasAuthoritativeGraph = Array.isArray(graph.nodes);" in source
    assert "const items = hasAuthoritativeGraph" in source
    assert "No topology records match the selected filters." in source
    discovery_renderer = source.split(
        "function renderDiscoveryCandidates(candidates)", 1
    )[1].split("function renderCMDB(cmdb)", 1)[0]
    assert "JSON.stringify" not in discovery_renderer


def test_discovery_queue_javascript_filters_caps_and_hides_omitted_selection() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()
    queue_contract = "function discoveryCandidateSource" + source.split(
        "function discoveryCandidateSource", 1
    )[1].split("function updateDiscoveryFilterOptions", 1)[0]
    result = _run_node_json(
        "const DISCOVERY_CANDIDATE_LIMIT = 12;\n"
        + queue_contract
        + """
const items = Array.from({length: 14}, (_, index) => ({
  candidate_id: 'queued-' + index,
  status: 'queued',
  source: 'network_tcp_hint',
  protocol_hints: ['mqtt']
}));
items.push({
  candidate_id: 'approved-usb',
  status: 'approved',
  source: 'usb_profile',
  protocols: ['opcua']
});
const capped = discoveryQueueView(items, {
  status: 'queued', source: 'network_tcp_hint', protocol: 'mqtt'
});
const filtered = discoveryQueueView(items, {
  status: 'approved', source: 'usb_profile', protocol: 'opcua'
});
console.log(JSON.stringify({
  cappedShown: capped.shownCount,
  cappedTotal: capped.totalCount,
  omittedSelectionVisible: capped.queuedCandidateIds.includes('queued-13'),
  filteredShown: filtered.shownCount,
  filteredId: filtered.shownItems[0].candidate_id
}));
"""
    )

    assert result == {
        "cappedShown": 12,
        "cappedTotal": 14,
        "omittedSelectionVisible": False,
        "filteredShown": 1,
        "filteredId": "approved-usb",
    }


def test_topology_scope_reports_only_rendered_nodes_and_links() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()
    renderer = source.split("function topologyRenderPlan(items, allRelations)", 1)[1].split(
        "function renderShellCockpit(", 1
    )[0]

    assert "totalNodeCount: totalNodeIds.length" in renderer
    assert "totalLinkCount: allRelations.length" in renderer
    assert "const renderableRelations = allRelations" in renderer
    assert "let renderedLinkCount = 0;" in renderer
    assert "renderedLinkCount += 1;" in renderer
    assert "const renderedNodeCount = nodeIds.length;" in renderer
    assert (
        "'Showing ' + renderedNodeCount + ' of ' + totalNodeCount + ' nodes · ' +"
        in renderer
    )
    assert "renderedLinkCount + ' of ' + totalLinkCount + ' links · '" in renderer
    assert "relations.length + (relations.length === 1" not in renderer
    assert "updateTopologyAccessibility(" in renderer
    assert "relationshipDescriptions" in renderer


def test_topology_has_accessible_relationships_and_stale_error_state() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()

    assert 'id="shell-map-description"' in source
    assert 'id="shell-topology-relationships"' in source
    assert 'aria-labelledby="shell-map-title shell-map-description"' in source
    assert 'aria-describedby="shell-topology-relationships"' in source
    assert 'id="shell-topology-filter-result" aria-live="polite"' in source
    assert "Topology filter failed. Retry to replace the stale graph." in source
    assert "scope?.setAttribute('data-stale', 'true');" in source
    assert "button.disabled = false;" in source


def test_topology_javascript_excludes_edges_for_nodes_outside_render_cap() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "root_page.html").read_text()
    topology_contract = "function topologyRenderPlan" + source.split(
        "function topologyRenderPlan", 1
    )[1].split("function renderShellMapState", 1)[0]
    result = _run_node_json(
        topology_contract
        + """
const items = Array.from({length: 14}, (_, index) => ({ci_id: 'node-' + index}));
const relations = Array.from({length: 13}, (_, index) => ({
  from_ci: 'node-' + index,
  to_ci: 'node-' + (index + 1)
}));
const plan = topologyRenderPlan(items, relations);
console.log(JSON.stringify({
  renderedNodes: plan.nodeIds.length,
  totalNodes: plan.totalNodeCount,
  renderedLinks: plan.renderableRelations.length,
  totalLinks: plan.totalLinkCount,
  omittedEdgeCount: plan.totalLinkCount - plan.renderableRelations.length
}));
"""
    )

    assert result == {
        "renderedNodes": 12,
        "totalNodes": 14,
        "renderedLinks": 11,
        "totalLinks": 13,
        "omittedEdgeCount": 2,
    }


def test_visual_qa_rejects_gateway_errors_and_wrong_branding() -> None:
    visual_qa_source = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()

    assert "badGatewayText" in visual_qa_source
    assert "502 Bad Gateway" in visual_qa_source
    assert "wrongLogoText" in visual_qa_source
    assert "internalUiLeak" in visual_qa_source
    assert "project_gap_discovery" in visual_qa_source
    assert "raw json" in visual_qa_source
    assert "visible internal identifiers" in visual_qa_source
    assert "unapproved branding" in visual_qa_source
    assert "customerBrandMissing" in visual_qa_source
    assert '[alt="GreeNovaX logo"]' in visual_qa_source
    assert "[...document.images].some" in visual_qa_source
    assert "customer dashboard identity failed" in visual_qa_source
    assert "shell-telemetry-trend" in visual_qa_source
    assert "monitoring workspace did not isolate telemetry trend and hide write forms" in visual_qa_source
    assert "notifications did not open the alarm workspace" in visual_qa_source
    assert "['/insights', 'intelligence']" in visual_qa_source
    assert "isVisibleElement(topology)" in visual_qa_source
    assert "!layer.hasAttribute('hidden')" in visual_qa_source
    assert "[data-relation-type]" in visual_qa_source


def test_dashboard_exposes_phase_distance_as_operational_panel(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-phase-distance.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'aria-label="Runtime readiness distance"' in body
    assert 'id="phase-distance-remaining"' in body
    assert 'id="phase-distance-body"' in body
    assert 'id="phase-distance-next-action"' in body
    assert "loadJson('/api/project/phase-distance')" in body
    assert "renderPhaseDistance(phaseDistance)" in body
    assert "Runtime Distance" in body
    assert "/api/project/phase-distance" in body


def test_dashboard_exposes_daily_gap_discovery_as_operational_panel(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-gap-discovery.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'id="project-gap-discovery"' in body
    assert 'aria-label="Runtime readiness review"' in body
    assert 'id="gap-discovery-open-count"' in body
    assert 'id="gap-discovery-code-count"' in body
    assert 'id="gap-discovery-body"' in body
    assert "loadJson('/api/project/gap-discovery')" in body
    assert "renderProjectGapDiscovery(gapDiscovery)" in body
    assert "Runtime Readiness Gaps" in body
    assert "/api/project/gap-discovery" in body


def test_dashboard_exposes_production_decision_console_in_shell(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-production-console.db"))

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'id="shell-production-action-card"' in body
    assert 'id="shell-production-readiness-score"' in body
    assert 'id="shell-production-decision-count"' in body
    assert 'id="shell-production-code-closeable"' in body
    assert 'id="shell-production-action-body"' in body
    assert "Production Decision Console" in body
    assert "PRODUCTION_ACTION_CONTEXTS.has(fallbackId)" in body
    assert "renderShellProductionActionPlan(productionActionPlan)" in body
    assert "/api/production/action-plan" in body


def test_dashboard_reports_include_ui_ux_quality_chart(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-ux-reports.db"))

    response = client.get("/api/reports/dashboard", headers=admin_token_headers())

    assert response.status_code == 200
    body = response.json()
    chart_ids = {chart["chart_id"] for chart in body["charts"]}
    report_ids = {report["report_id"] for report in body["reports"]}
    assert "ui-ux-quality-gate" in chart_ids
    assert "ui-ux-quality-gate" in report_ids
    assert body["ui_ux_quality"]["score"] == round(sum(gate["state"] == "ready" for gate in body["ui_ux_quality"]["gates"]) / len(body["ui_ux_quality"]["gates"]) * 100)
    assert body["ui_ux_quality"]["metrics"]["raw_json_menu_links"] == 0
    assert body["ui_ux_quality"]["metrics"]["shell_route_contexts"] >= 18
    assert body["ui_ux_quality"]["visual_evidence"]["customer_safe"] is True


def test_acceptance_pack_has_ui_ux_gate(tmp_path) -> None:
    client = TestClient(create_app(database_path=tmp_path / "ui-ux-acceptance.db"))

    response = client.get("/api/delivery/evidence-pack")

    assert response.status_code == 200
    body = response.json()
    by_id = {gate["gate_id"]: gate for gate in body["gates"]}
    assert by_id["ui-ux-quality"]["state"] == "ready"
    assert by_id["ui-ux-quality"]["evidence"].startswith("UI/UX quality score ")
    assert "0 raw service menu link(s)." in by_id["ui-ux-quality"]["evidence"]


def test_customer_ui_ux_quality_docs_are_paired_and_indexed() -> None:
    english = PROJECT_ROOT / "docs/customer/phase2/UI_UX_QUALITY_GATE.en.md"
    german = PROJECT_ROOT / "docs/customer/phase2/UI_UX_QUALITY_GATE.de.md"
    index_en = (PROJECT_ROOT / "docs/customer/DOCUMENT_INDEX.en.md").read_text()
    index_de = (PROJECT_ROOT / "docs/customer/DOCUMENT_INDEX.de.md").read_text()
    checklist_en = (PROJECT_ROOT / "docs/customer/ACCEPTANCE_CHECKLIST.en.md").read_text()
    checklist_de = (PROJECT_ROOT / "docs/customer/ACCEPTANCE_CHECKLIST.de.md").read_text()

    assert english.exists()
    assert german.exists()
    assert "operational and management value" in english.read_text()
    assert "Advanced AI route control" in english.read_text()
    assert "Management-Nutzen" in german.read_text()
    assert "Advanced-AI-Route-Steuerung" in german.read_text()
    assert "UI_UX_QUALITY_GATE.en.md" in index_en
    assert "UI_UX_QUALITY_GATE.de.md" in index_de
    assert "/api/ui/quality-gate" in checklist_en
    assert "/api/ui/quality-gate" in checklist_de


def test_visual_evidence_counts_playwright_console_type_errors(tmp_path) -> None:
    out_dir = tmp_path / "output" / "playwright"
    out_dir.mkdir(parents=True)
    version = "0.152.15"
    routes = ["/", "/reports", "/tests", "/evidence", "/settings"]
    viewports = ["mobile", "desktop", "desktop-wide"]
    checks = []
    for route in routes:
        route_name = "root" if route == "/" else route.strip("/")
        for viewport in viewports:
            screenshot = (
                f"output/playwright/agentiot-v{version}-{route_name}-{viewport}.png"
            )
            (tmp_path / screenshot).write_bytes(b"png")
            checks.append(
                {
                    "route": route,
                    "viewport": viewport,
                    "status": "PASS",
                    "screenshot_path": screenshot,
                }
            )
    report = {
        "version": version,
        "generated_at": "2026-06-30T10:00:00Z",
        "routes": routes,
        "viewports": viewports,
        "total_count": len(checks),
        "passed_count": len(checks),
        "console_events": [
            {"route": "/settings", "type": "error", "text": "TypeError: broken dashboard state"}
        ],
        "checks": checks,
    }
    (out_dir / f"agentiot-v{version}-visual-report.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    evidence = build_visual_qa_evidence(
        repo_root=tmp_path,
        version=version,
        source_commit="test",
        max_age_hours=24 * 365,
    )

    assert evidence["console_error_count"] == 1
    assert evidence["console_error_routes"] == ["/settings"]
    assert evidence["status"] != "PASS"
