# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

import re

from fastapi.testclient import TestClient

from agentiot import __version__
import agentiot.app as agentiot_app
from agentiot.app import create_app


OPERATOR_HEADERS = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}


CONTRACTED_PATHS = {
    "/healthz",
    "/readyz",
    "/api/version",
    "/api/system/operational-truth",
    "/api/devices",
    "/api/cmdb/configuration-items",
    "/api/hardware/discovery",
    "/api/hardware/discovery/profiles",
    "/api/hardware/discovery/usb/status",
    "/api/hardware/discovery/usb/sysfs",
    "/api/config/profiles",
    "/api/firmware/compatibility",
    "/api/firmware/drift",
    "/api/adapters/mqtt/broker/status",
    "/api/adapters/rest/status",
    "/api/simulation/runs",
    "/api/plugins/hardware-simulator/status",
    "/api/plugins/hardware-simulator/catalog",
    "/api/plugins/hardware-simulator/runs",
    "/api/telemetry",
    "/api/assets",
    "/api/alerts",
    "/api/alerts/{alert_id}/resolve",
    "/api/recovery/proposals",
    "/api/recovery/proposals/{proposal_id}/approve",
    "/api/adapters/mqtt/messages",
    "/api/audit/events",
    "/api/security/status",
    "/api/access/policy",
    "/api/access/token/validate",
    "/api/production/hardening",
    "/api/production/preflight",
    "/api/production/backup-retention",
    "/api/production/approval-package",
    "/api/production/action-plan",
    "/api/production/owner-decision-brief",
    "/api/release/mission",
    "/api/release/mission/run",
    "/api/release/evidence-console",
    "/api/customer/feedback",
    "/api/customer/feedback/summary",
    "/api/delivery/final-package",
    "/api/delivery/evidence-pack",
    "/api/delivery/handoff-console",
    "/api/delivery/management-brief",
    "/api/admin/production/action-plan",
    "/api/admin/production/readiness-controls",
    "/api/admin/production/readiness-controls/{control_id}",
    "/api/admin/production/decisions",
    "/api/admin/production/decisions/{decision_id}",
    "/api/operations/summary",
    "/api/operations/workbench",
    "/api/operations/next-best-action",
    "/api/operations/command-center",
    "/api/operations/evidence",
    "/api/project/phases",
    "/api/project/phase-distance",
    "/api/project/goal-board",
    "/api/project/drift-control",
    "/api/project/drift-control/run",
    "/api/project/gap-discovery",
    "/api/project/gap-discovery/run",
    "/api/recheck/latest",
    "/api/admin/agents",
    "/api/admin/agents/prompt-contracts",
    "/api/admin/agents/{agent_id}",
    "/api/admin/agents/{agent_id}/prompt-contract",
    "/api/agents/section-reports",
    "/api/admin/access/roles",
    "/api/admin/access/roles/{role}",
    "/api/admin/access/users",
    "/api/admin/access/users/{subject_id}",
    "/api/admin/ai/provider-policy",
    "/api/ai/resource-governance",
    "/api/ai/model-services",
    "/api/ai/model-resource-governance",
    "/api/admin/ai/model-services",
    "/api/admin/ai/model-services/{provider}/credentials",
    "/api/admin/ai/model-services/{provider}/connectivity-check",
    "/api/ai/usage-ledger",
    "/api/admin/ai/token-usage",
    "/api/admin/ai/memory-policy",
    "/api/admin/ai/routing-console",
    "/api/ai/assurance-console",
    "/api/admin/ai/analysis-profiles",
    "/api/admin/ai/analysis-profiles/{profile_id}",
    "/api/admin/rag/knowledge/{doc_id}",
    "/api/assistant/quality-report",
    "/api/assistant/coworker-quality",
    "/api/assistant/decision-brief",
    "/api/assistant/workbench",
    "/api/assistant/interactions",
    "/api/assistant/sessions",
    "/api/assistant/sessions/{session_id}",
    "/api/assistant/bdd-suggestions",
    "/api/assistant/tool-proposals/prepare",
    "/api/assistant/tool-proposals/{proposal_id}/approve",
    "/api/rag/knowledge-base",
    "/api/rag/quality-console",
    "/api/rag/search",
    "/api/evidence/findings",
    "/api/evidence/action-board",
    "/api/ui/quality-gate",
    "/api/qc/fan-out",
    "/api/recheck/latest",
    "/api/qa/challenge-runs",
    "/api/qa/continuous-mission",
    "/api/qa/evidence-report",
    "/api/agents/tasks",
    "/api/control/dashboard",
    "/api/control/notifications",
    "/api/control/issues",
    "/api/control/nodes",
    "/api/control/auto-guard",
    "/api/control/self-check",
    "/api/control/solve",
    "/api/control/agent-action",
    "/api/control/task-state",
    "/api/control/task/update",
    "/api/a2a/jsonrpc",
    "/api/a2a/messages/stream",
    "/api/architecture/adr",
    "/api/reports/dashboard",
    "/api/demo/scenario",
    "/api/demo/operational-preview",
    "/api/demo/bootstrap/status",
    "/api/demo/reset",
    "/api/demo/package",
    "/api/ai/routing",
    "/api/ai/model-route-preflight",
    "/api/ai/model-benchmarks",
    "/api/ai/evaluations",
    "/api/ai/evaluations/runs",
    "/api/chat",
    "/api/assistant/stream",
    "/api/settings",
    "/api/reports",
}


def test_healthz_reports_clean_service_identity() -> None:
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "agentiot-dashboard"
    assert body["customer"] == "GreeNovaX"
    assert body["contractor"] == "IoT-AI.Tech"


def test_root_path_returns_customer_safe_status_page() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store, max-age=0, must-revalidate"
    assert response.headers["pragma"] == "no-cache"
    assert "AgentIoT Dashboard" in response.text
    assert "Prepared for GreeNovaX by IoT-AI.Tech" in response.text
    assert "/static/greenovax-logo.png" in response.text
    assert "/static/greenovax-logo-horizontal.png" in response.text
    assert 'alt="GreeNovaX logo"' in response.text
    assert set(re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', response.text)) == {
        "/static/greenovax-logo.png",
        "/static/greenovax-logo-horizontal.png",
    }
    assert "legacy-logo" not in response.text
    assert "width: min(170px, 100%);" in response.text
    assert ".queue-side .queue-action" in response.text
    assert "flex: 1 1 100%;" in response.text
    assert ".shell-workbench-head .shell-pill" in response.text
    assert "data-nav-icon=\"cockpit\"" in response.text
    assert ".shell-nav-icon svg" in response.text
    assert "font-size: 0;" not in response.text
    assert "Operations Console" in response.text
    assert "Open Asset Setup" in response.text
    assert 'class="dashboard-shell"' in response.text
    assert 'class="shell-sidebar"' in response.text
    assert 'class="shell-topbar"' in response.text
    assert 'class="shell-rail"' in response.text
    assert "Operations Cockpit" in response.text
    assert "cockpit-drift-control" in response.text
    assert "cockpit-release-evidence" in response.text
    assert "Operational Drift Review" in response.text
    assert "Acceptance Drift Review" not in response.text
    assert 'id="shell-run-drift-control"' in response.text
    assert 'id="drift-control-run-button"' in response.text
    assert "Record Drift Review" in response.text
    assert "Record Acceptance Review" not in response.text
    assert "Six-Hour Drift Control" not in response.text
    assert "ADR Governance Register" not in response.text
    assert "Instruction Contract Console" not in response.text
    assert "Runtime Instruction Artifacts" not in response.text
    assert "Daily Gap Discovery" not in response.text
    assert "Service Readiness" in response.text
    assert "Action Queue" in response.text
    assert "buildPhase2ClosureActions(ownerDecisionBrief, productionActionPlan)" not in response.text
    assert "delivery decision needed" not in response.text
    assert "buildPhase2ClosureActions" not in response.text
    assert "loadJsonSafe('/api/production/owner-decision-brief')" not in response.text
    assert "loadJsonSafe('/api/production/action-plan')" not in response.text
    assert "Open Asset Setup" in response.text
    assert "async function openAssetSetup()" in response.text
    assert "AI Assistant" in response.text
    assert "shell-top-icon" in response.text
    assert "shell-avatar" in response.text
    assert "shell-notification-badge" in response.text
    assert 'id="shell-notification-count"' in response.text
    assert "shell-kpi-trend" in response.text
    assert "summary.comparisons" in response.text
    assert "comparisonPeriodText" in response.text
    assert "2.4%" not in response.text
    assert "0.8%" not in response.text
    assert "vs 15m ago" not in response.text
    assert "queue-chip" in response.text
    assert "shell-assistant-input" in response.text
    assert "map-world-svg" in response.text
    assert "shell-legend" in response.text
    assert "queue-icon" in response.text
    assert "queue-chevron" in response.text
    assert "--arc: 0%;" in response.text
    assert "shell-footer-chip" in response.text
    assert "shell-signal-bars" in response.text
    assert "box-shadow: inset 4px 0 0 #12a76f" in response.text
    assert "reference-cockpit-fidelity" in response.text
    assert "industrial-cockpit-density" in response.text
    assert "mobile-cockpit-stack" in response.text
    assert "visual reference cockpit" in response.text
    assert "browser-visual-required" in response.text
    assert 'id="shell-time-range-control"' in response.text
    assert 'aria-label="Select cockpit time range"' in response.text
    assert 'id="shell-refresh-status"' in response.text
    assert "map-status-ring" in response.text
    assert "map-region-label" in response.text
    assert "map-pulse" in response.text
    assert "function updateCockpitRefreshStatus" in response.text
    assert response.text.index("function updateCockpitRefreshStatus") < response.text.index("function installWorkspaceNavigation")
    assert 'id="shell-readiness-gauge"' in response.text
    assert "function renderShellCockpit" in response.text
    assert "function shellCockpitMetrics" in response.text
    assert "referencePreviewActive" in response.text
    assert "liveRecordCount === 0" in response.text
    assert "function formatShellNumber" in response.text
    assert "initialSetupPreviewActive" in response.text
    assert (
        '.shell-main[data-active-context="api-evidence"] #shell-drift-control-card'
        in response.text
    )
    assert (
        '.shell-main[data-active-context="ui-quality-gate"] #shell-test-workspace-card'
        in response.text
    )
    assert "#shell-drift-control-card {{\n        order: -4;" not in response.text
    assert "assetCount: 1248" not in response.text
    assert "healthScore: 98.6" not in response.text
    assert 'id="shell-assets-count">0' in response.text
    assert 'id="shell-alarm-count">0' in response.text
    assert 'id="shell-anomaly-count">0' in response.text
    assert 'id="shell-health-score">Not measured' in response.text
    assert 'id="shell-readiness-score">Waiting' in response.text
    assert 'id="shell-action-count">0' in response.text
    assert "Initial setup needed: register device and ingest telemetry" in response.text
    assert "Live actions ready" in response.text
    assert "Operations summary" in response.text
    assert "setText(" not in response.text
    assert "No open operator actions" in response.text
    assert "const openAlerts = alerts.items.filter" in response.text
    assert "const pendingProposals = proposals.items.filter" in response.text
    assert "Recovery proposal awaiting approval" in response.text
    assert "renderShellCockpit(" in response.text
    assert "bootstrapStatus" in response.text
    assert "Promise.all([" in response.text
    assert response.text.index("renderShellCockpit(") < response.text.index("loadJson('/api/config/profiles')")
    assert 'data-shell-target="agent-control"' in response.text
    assert 'data-shell-target="ai-control"' in response.text
    assert 'data-shell-target="command-center"' in response.text
    assert 'data-shell-target="advanced-settings-panel"' in response.text
    assert ">Reports</a>" in response.text
    assert "Monthly Report" not in response.text
    assert "Contract Traceability" not in response.text
    assert 'id="shell-advanced-settings-control"' in response.text
    assert "Change assistant routing, model policy, and answer-quality controls" in response.text
    assert "function openWorkspaceSection" in response.text
    assert "moveAdvancedSettingsIntoShell" in response.text
    assert "panel.dataset.shellManaged = 'true'" in response.text
    assert 'id="shell-context-panel"' in response.text
    assert 'id="shell-context-title"' in response.text
    assert 'id="shell-context-cards"' in response.text
    assert "const SHELL_CONTEXT_VIEWS" in response.text
    assert "function renderShellContext" in response.text
    assert "renderShellContext(targetId || view || 'cockpit')" in response.text
    assert "OPERATIONS_SHELL_CONTEXTS.has(fallbackId)" in response.text
    assert "? 'operations'" in response.text
    assert "detailedWorkspace.open = true" not in response.text
    assert "function openDetailedWorkspace" not in response.text
    assert "setAttribute('open'" not in response.text
    assert 'id="detailed-workspace" hidden aria-hidden="true"' in response.text
    assert ".legacy-workspace[hidden]," in response.text
    assert "Operate Command Surface" in response.text
    assert "Automation Orchestration Surface" in response.text
    assert "Intelligence Surface" in response.text
    assert "Operational Evidence Surface" in response.text
    assert "Operational Audit Trail" in response.text
    assert "No raw technical navigation" in response.text
    assert "advancedSettingsPanel.hidden = fallbackId !== 'advanced-settings-panel'" in response.text
    assert "'agent-control', 'api-evidence', 'advanced-settings-panel'" not in response.text
    assert "'ai-control', 'assistant', 'agent-control', 'advanced-settings-panel'" not in response.text
    assert "scrollTarget.scrollIntoView" in response.text
    assert "targetId !== 'advanced-settings-panel'" not in response.text
    assert "targetId !== 'agent-control'" not in response.text
    assert "targetId === 'reports-dashboard'" not in response.text
    assert "openDetailedWorkspace(targetId);" not in response.text
    assert "closeDetailedWorkspace" in response.text
    assert ".advanced-settings:not([hidden])" in response.text
    assert ".legacy-workspace[open]" in response.text
    assert "display: none !important" in response.text
    assert "max-width: calc(100vw - 32px)" not in response.text
    assert ".advanced-settings table" in response.text
    assert ".legacy-workspace .forms > .panel:not(#command-center):not(#rag-knowledge) table" in response.text
    assert ".legacy-workspace .forms > .panel:not(#command-center):not(#rag-knowledge) th" in response.text
    assert "position: fixed" not in response.text
    assert "position: static" in response.text
    assert ".shell-context > .advanced-settings:not([hidden])" in response.text
    assert "max-height: min(70vh, 720px)" not in response.text
    assert "max-width: 100vw" in response.text
    assert "overflow-x: hidden" in response.text
    assert "Show critical alarms" in response.text
    assert "Explain recent anomaly" in response.text
    assert "Recommend actions" in response.text
    assert "function openShellQueueAction" in response.text
    assert "data-shell-queue-target" in response.text
    assert "data-shell-evidence-endpoint" in response.text
    assert "Open action" in response.text
    assert 'id="shell-agent-task"' in response.text
    assert "function runShellAgentTask" in response.text
    assert "postJson('/api/agents/tasks', payload)" in response.text
    assert "Cockpit automation task completed with route:" in response.text
    assert "Automation run stored. Review the workflow handoff" in response.text
    assert 'id="agent-prompt-contracts-body"' in response.text
    assert 'id="shell-agent-prompt-contract-card"' in response.text
    assert 'id="shell-agent-prompt-contract-body"' in response.text
    assert 'id="shell-agent-prompt-contract-count"' in response.text
    assert 'id="prompt-artifacts-body"' in response.text
    assert "function renderAgentPromptContracts" in response.text
    assert "function renderPromptArtifacts" in response.text
    assert "const standards = registry.standards || {};" in response.text
    assert "standards.adr || 'Decision record unavailable'" in response.text
    assert "standards.a2a || 'Workflow handoff unavailable'" in response.text
    assert (
        "standards: { adr: 'Decision record unavailable', "
        "a2a: 'Workflow handoff unavailable' }"
        in response.text
    )
    assert "loadControlJsonSafe(controlPath('agents', 'prompt-contracts')" in response.text
    assert "loadControlJsonSafe(controlPath('prompts')" in response.text
    assert 'id="shell-report-workspace-card"' in response.text
    assert 'id="shell-report-chart-body"' in response.text
    assert 'id="shell-report-evidence-body"' in response.text
    assert "const REPORT_WORKSPACE_CONTEXTS" in response.text
    assert "'reports-dashboard'" in response.text
    assert "function renderShellReportWorkspace" in response.text
    assert "renderShellReportWorkspace(dashboardReports);" in response.text
    assert ".shell-chart-bars" in response.text
    assert "className = 'shell-chart-bar'" in response.text
    assert 'id="shell-test-workspace-card"' in response.text
    assert 'id="shell-operator-token"' not in response.text
    assert 'for="shell-operator-token"' not in response.text
    assert 'id="shell-run-qa-challenge"' in response.text
    assert 'id="shell-qa-challenge-result"' in response.text
    assert 'id="shell-test-gate-body"' in response.text
    assert 'id="shell-test-mission-body"' in response.text
    assert "const TEST_WORKSPACE_CONTEXTS" in response.text
    assert "function renderShellTestWorkspace" in response.text
    assert "function getOperatorToken" not in response.text
    assert "document.getElementById('shell-operator-token')" not in response.text
    assert "function runShellQAChallenge" in response.text
    assert "postJson('/api/qa/challenge-runs', payload)" in response.text
    assert "Shell quality review completed:" in response.text
    assert "renderShellTestWorkspace(uiUxQuality, qaChallengeRuns, continuousQAMission);" in response.text
    assert 'id="shell-evidence-workspace-card"' in response.text
    assert 'id="shell-evidence-endpoint-body"' in response.text
    assert "const EVIDENCE_WORKSPACE_CONTEXTS" in response.text
    assert "function renderShellEvidenceWorkspace" in response.text
    assert "No operational changes recorded" in response.text
    assert "const operationalPrefixes" in response.text
    assert "const excludedAuditTerms" in response.text
    assert 'id="advanced-ai-routing-form"' in response.text
    assert '<option value="gemini">Gemini</option>' in response.text
    assert 'id="advanced-routing-console"' in response.text
    assert "AI Routing Control Console" in response.text
    assert 'id="advanced-routing-console-body"' in response.text
    assert 'id="advanced-routing-action-body"' in response.text
    assert "function renderRoutingControlConsole(consoleState)" in response.text
    assert "function loadControlJsonSafe(path, fallback)" in response.text
    assert "adminRoutingConsoleFallback()" in response.text
    assert "loadControlJsonSafe(" in response.text
    assert "controlPath('ai', 'routing-console')" in response.text
    assert "renderRoutingControlConsole(aiRoutingConsole);" in response.text
    assert "Apply AI Route" in response.text
    assert "const safeRoute = route || {};" in response.text
    assert "const providerPolicy = safeRoute.provider_policy || {};" in response.text
    assert "const localModel = safeRoute.local_model || {};" in response.text
    assert "safeRoute.active_route || 'grounded_fallback'" in response.text
    assert "const safePolicy = policy || {};" in response.text
    assert "renderAIProviderPolicy(displayAIProviderPolicy);" in response.text
    assert "aiRouting.provider_policy || aiProviderPolicy" in response.text
    assert "function profilePayload" in response.text
    assert "controlPatchJson(controlPath('ai', 'provider-policy'), providerPayload)" in response.text
    assert "advanced-ai-routing-result" in response.text
    assert "AI route update failed:" in response.text
    assert '<span class="nav-heading">Operate</span>' in response.text
    assert '<span class="nav-heading">Agents</span>' in response.text
    assert '<span class="nav-heading">Intelligence</span>' in response.text
    assert '<span class="nav-heading">Runtime</span>' in response.text
    assert 'data-view="operate"' in response.text
    assert 'class="operator-access"' not in response.text
    assert 'class="panel cockpit-panel"' in response.text
    assert "installWorkspaceNavigation()" in response.text
    assert "workspace-ready[data-view=\"operate\"]" in response.text
    assert "Register Asset" in response.text
    assert "Operational Command Center" in response.text
    assert 'href="#command-center"' in response.text
    assert '<div class="panel wide" id="command-center">' in response.text
    assert "id=\"command-center-kpis-body\"" in response.text
    assert "id=\"command-center-cards-body\"" in response.text
    assert "function renderCommandCenter(center)" in response.text
    assert "loadJsonSafe('/api/operations/command-center')" in response.text
    assert "loadJsonSafe('/api/operations/next-best-action')" in response.text
    assert "Review human approval" in response.text
    assert "Register Device" in response.text
    assert "Configuration Profile" in response.text
    assert "Firmware Compatibility" in response.text
    assert "Hardware Simulator Plugin" in response.text
    assert "Sensor Inventory Auto Discovery" in response.text
    assert "id=\"cmdb-items-body\"" in response.text
    assert "id=\"cmdb-relations-body\"" in response.text
    assert "id=\"shell-cmdb-workspace-card\"" in response.text
    assert "id=\"shell-cmdb-item-list\"" in response.text
    assert "CMDB_WORKSPACE_CONTEXTS" in response.text
    assert "loadJson('/api/cmdb/configuration-items')" in response.text
    assert "function renderCMDB(cmdb)" in response.text
    assert "Configuration Profiles" in response.text
    assert "Firmware Catalog" in response.text
    assert "Simulation Evidence" in response.text
    assert "name=\"adapter\"" in response.text
    assert "value=\"mqtt\"" in response.text
    assert "Ingest Telemetry" in response.text
    assert "Pending Recovery" in response.text
    assert "Initial Records" in response.text
    assert "Security Baseline" in response.text
    assert "Production Hardening" in response.text
    assert "Owner Approval" in response.text
    assert "Access Policy" in response.text
    assert "JWKS configured" in response.text
    assert "Validation method" in response.text
    assert "Customer Feedback" in response.text
    assert "Feedback Summary" in response.text
    assert "Runtime Package" in response.text
    assert "Operations Evidence Pack" in response.text
    assert "Assistant Quality Matrix" in response.text
    assert "Assistant Quality Records" in response.text
    assert 'id="assistant-quality-report"' in response.text
    assert 'id="assistant-quality-body"' in response.text
    assert "Assistant Decision Brief" in response.text
    assert 'id="assistant-decision-brief" data-dashboard-group="delivery intelligence"' in response.text
    assert 'id="assistant-decision-risk-body"' in response.text
    assert 'id="assistant-decision-model-body"' in response.text
    assert "Identity Provider" in response.text
    assert "Deployment Readiness" in response.text
    assert "Operational Evidence" in response.text
    assert "Ask Diagnosis" in response.text
    assert "AI Routing" in response.text
    assert "AI Evaluations" in response.text
    assert "id=\"assistant-copilot-summary\"" in response.text
    assert "id=\"assistant-plan-body\"" in response.text
    assert "id=\"assistant-evidence-body\"" in response.text
    assert "id=\"assistant-a2a-body\"" in response.text
    assert "id=\"assistant-next-actions\"" in response.text
    assert "id=\"asset-form\"" in response.text
    assert "id=\"device-form\"" in response.text
    assert "id=\"config-profile-form\"" in response.text
    assert "id=\"firmware-form\"" in response.text
    assert "id=\"simulation-form\"" in response.text
    assert "id=\"hardware-simulator-status-body\"" in response.text
    assert "id=\"hardware-simulator-catalog-body\"" in response.text
    assert "id=\"telemetry-form\"" in response.text
    assert "id=\"operator-form\"" not in response.text
    assert "id=\"operator-token\"" not in response.text
    assert "id=\"admin-token\"" not in response.text
    assert "type=\"password\"" in response.text
    assert "placeholder=\"Operator token\"" not in response.text
    assert "placeholder=\"Admin token\"" not in response.text
    assert "X-Operator-Token" not in response.text
    assert "X-Admin-Token" not in response.text
    assert "unit-" + "operator-" + "sentinel" not in response.text
    assert 'href="#overview"' in response.text
    assert 'href="#operations"' in response.text
    assert 'href="#reports-dashboard" data-view="intelligence">Charts</a>' in response.text
    assert 'href="#production-readiness"' in response.text
    assert 'href="#delivery-evidence"' in response.text
    assert 'href="/api/' not in response.text
    assert '<div class="panel wide" id="reports-dashboard">\n          <h2>Operational Metrics</h2>' in response.text
    assert '<div class="panel wide" id="agent-control">\n          <h2>Automation Administration</h2>' in response.text
    assert '<div class="panel wide" id="access-control">\n          <h2>Configurable Access Roles</h2>' in response.text
    assert '<div class="panel wide" id="ai-control">\n          <h2>AI Provider Policy</h2>' in response.text
    assert 'id="live-operations-workbench" aria-label="Operational controls" hidden' in response.text
    assert "function syncOperationalWorkbenchVisibility" in response.text
    assert '<div class="panel wide" id="production-readiness">\n          <h2>Production Hardening</h2>' in response.text
    assert 'data-open-asset-setup' in response.text
    assert "id=\"run-demo\"" not in response.text
    assert "id=\"reset-demo\"" not in response.text
    assert "postJson('/api/assets'" in response.text
    assert "postJson('/api/config/profiles'" in response.text
    assert "postJson('/api/plugins/hardware-simulator/runs'" in response.text
    assert "postJson('/api/telemetry'" in response.text
    assert "fetch('/api/firmware/compatibility'" in response.text
    assert "Runtime Package" in response.text
    assert "Operations Snapshot" in response.text
    assert "Operational State" in response.text
    assert "Operational Readiness" in response.text
    assert "Current Risk" in response.text
    assert "Next Operator Action" in response.text
    assert "Latest Telemetry" in response.text
    assert "Last Audit Event" in response.text
    assert "id=\"latest-telemetry\"" in response.text
    assert "id=\"last-audit-event\"" in response.text
    assert "Commissioning Workflow" in response.text
    assert "Safe Operational Baseline" in response.text
    assert "Operational Workbench" in response.text
    assert "Baseline Devices" in response.text
    assert "Load Read-only Baseline" in response.text
    assert "/api/operations/preview" in response.text
    assert "/api/operations/bootstrap/status" in response.text
    assert "postJson('/api/operations/workflows/commissioning-run'" not in response.text
    assert "id=\"preview-tabs\"" in response.text
    assert "id=\"preview-panel\"" in response.text
    assert "id=\"bootstrap-state\"" in response.text
    assert "function renderOperationalPreview(preview)" in response.text
    assert "function renderPreviewTab()" in response.text
    assert "function renderFirstScreenCounters(summary, preview)" in response.text
    assert "liveOrPreviewCount(summary.counters.devices" in response.text
    assert "Safe operational baseline is active" in response.text
    assert "activePreviewTab = 'overview'" in response.text
    assert "Runtime Action Package" in response.text
    for forbidden_label in (
        "Demo Seed",
        "Customer Website Demo",
        "Load Read-Only Preview",
        "Reset Pilot Records",
        "Raw API evidence",
        "Service evidence endpoints",
        "Pilot Area",
        "Pilot setup needed",
        "Pilot flow",
        "Pilot operation failed",
        "operational Phase 2 console",
        "run the demo flow",
    ):
        assert forbidden_label not in response.text
    assert "id=\"readiness-count\"" in response.text
    assert "id=\"report-count\"" in response.text
    assert "/api/operations/scenario" in response.text
    assert "/api/operations/handoff-package" in response.text
    assert "/api/operations/summary" in response.text
    assert "Temperature thresholds" in response.text
    assert "Live Operational Data" in response.text
    assert "Assets" in response.text
    assert "Telemetry" in response.text
    assert "Operator Runbook" in response.text
    assert "Operational records" in response.text
    assert "Evidence JSON" not in response.text
    assert "id=\"assets-body\"" in response.text
    assert "id=\"telemetry-body\"" in response.text
    assert "id=\"config-profiles-body\"" in response.text
    assert "id=\"firmware-catalog-body\"" in response.text
    assert "id=\"firmware-drift-body\"" in response.text
    assert "id=\"simulation-runs-body\"" in response.text
    assert "id=\"runbook-body\"" in response.text
    assert "id=\"handoff-package-body\"" in response.text
    assert "id=\"production-hardening-body\"" in response.text
    assert "id=\"production-action-plan-body\"" in response.text
    assert "id=\"production-action-summary\"" in response.text
    assert "id=\"shell-production-action-card\"" in response.text
    assert "id=\"shell-production-readiness-score\"" in response.text
    assert "id=\"shell-production-action-body\"" in response.text
    assert "Production Decision Console" in response.text
    assert "function renderShellProductionActionPlan(plan)" in response.text
    assert "renderShellProductionActionPlan(productionActionPlan)" in response.text
    assert "const PRODUCTION_ACTION_CONTEXTS" in response.text
    assert "Required Record" in response.text
    assert "Approval Boundary" in response.text
    assert "Secret-Free" in response.text
    assert "display_actions" in response.text
    assert "display_action_queue" in response.text
    assert "occurrence_count" in response.text
    assert "grouped" in response.text
    assert "blocking_category" in response.text
    assert "required_evidence" in response.text
    assert "approval_boundary" in response.text
    assert "can_close_without_customer_secret" in response.text
    assert "Update Production Readiness" in response.text
    assert "id=\"production-readiness-form\"" in response.text
    assert "controlPath('production', 'readiness-controls')" in response.text
    assert "id=\"owner-approval-body\"" in response.text
    assert "id=\"feedback-summary-body\"" in response.text
    assert "id=\"final-delivery-body\"" in response.text
    assert "id=\"acceptance-gates-body\"" in response.text
    assert "id=\"quality-matrix-body\"" in response.text
    assert "id=\"acceptance-score\"" in response.text
    assert "id=\"customer-feedback-body\"" in response.text
    assert "id=\"feedback-form\"" in response.text
    assert "id=\"feedback-operator-token\"" not in response.text
    assert "id=\"feedback-result\"" in response.text
    assert "Required for feedback write" not in response.text
    assert "function feedbackOperatorHeaders" in response.text
    assert "postFeedbackJson('/api/customer/feedback', payload)" in response.text
    assert "feedbackToken" not in response.text
    assert '<option value="mqtt-broker-subscriber">MQTT broker subscriber</option>' in response.text
    assert "/healthz" in response.text
    assert "/readyz" in response.text
    assert "/about" in response.text
    assert "/api/devices" in response.text
    assert "/api/config/profiles" in response.text
    assert "/api/firmware/compatibility" in response.text
    assert "/api/firmware/drift" in response.text
    assert "/api/simulation/runs" in response.text
    assert "/api/recovery/proposals" in response.text
    assert "/api/security/status" in response.text
    assert "/api/access/policy" in response.text
    assert "/api/production/hardening" in response.text
    assert "/api/production/approval-package" in response.text
    assert "/api/production/action-plan" in response.text
    assert "/api/customer/feedback" in response.text
    assert "/api/customer/feedback/summary" in response.text
    assert "/api/delivery/final-package" in response.text
    assert "/api/delivery/evidence-pack" in response.text
    assert "/api/delivery/handoff-console" in response.text
    assert "/api/delivery/management-brief" in response.text
    assert "id=\"final-handoff-console\"" in response.text
    assert "id=\"handoff-score\"" in response.text
    assert "id=\"handoff-action-body\"" in response.text
    assert "id=\"management-delivery-brief\"" in response.text
    assert "id=\"management-questions-body\"" in response.text
    assert "id=\"management-needs-body\"" in response.text
    assert "id=\"management-market-body\"" in response.text
    assert "Required Input" in response.text
    assert "Operational Impact" in response.text
    assert "id=\"shell-final-handoff-console-card\"" in response.text
    assert "id=\"shell-handoff-score\"" in response.text
    assert "id=\"shell-handoff-secret-free\"" in response.text
    assert "id=\"shell-handoff-action-body\"" in response.text
    assert "required_input" in response.text
    assert "acceptance_impact" in response.text
    assert "can_close_without_customer_secret" in response.text
    assert "renderFinalHandoffConsole(" in response.text
    assert "renderManagementDeliveryBrief(" in response.text
    assert "renderShellFinalHandoffConsole(" in response.text
    assert "loadJson('/api/delivery/handoff-console')" in response.text
    assert "loadJson('/api/delivery/management-brief')" in response.text
    assert "/api/operations/summary" in response.text
    assert "/api/operations/evidence" in response.text
    assert "/api/project/phases" in response.text
    assert "/api/project/drift-control" in response.text
    assert "/api/release/gap-closure-console" in response.text
    assert 'id="shell-release-gap-closure-card"' in response.text
    assert 'id="shell-gap-auth"' in response.text
    assert 'id="shell-release-gap-closure-body"' in response.text
    assert "function renderReleaseGapClosureConsole" in response.text
    assert "loadJson('/api/release/gap-closure-console')" in response.text
    assert "renderReleaseGapClosureConsole(releaseGapClosureConsole);" in response.text
    assert 'id="project-drift-control"' in response.text
    assert 'id="drift-control-status"' in response.text
    assert 'id="shell-drift-control-card"' in response.text
    assert 'id="shell-drift-status"' in response.text
    assert 'id="shell-drift-control-body"' in response.text
    assert "DRIFT_CONTROL_CONTEXTS" in response.text
    assert "function renderProjectDriftControl" in response.text
    assert "loadJson('/api/project/drift-control')" in response.text
    assert "renderProjectDriftControl(driftControl);" in response.text
    assert "controlPath('agents')" in response.text
    assert "/api/agents/section-reports" in response.text
    assert "controlPath('access', 'roles')" in response.text
    assert "/api/agents/tasks" in response.text
    assert "/api/reports/dashboard" in response.text
    assert "/api/ai/routing" in response.text
    assert "/api/ai/model-benchmarks" in response.text
    assert "/api/ai/assurance-console" in response.text
    assert "/api/ai/evaluations" in response.text
    assert "controlPath('ai', 'provider-policy')" in response.text
    assert "controlPath('ai', 'analysis-profiles')" in response.text
    assert "/api/evidence/findings" in response.text
    assert "/api/ui/quality-gate" in response.text
    assert "/api/ai/evaluations/runs" in response.text
    assert "/api/settings" in response.text
    assert "/api/reports" in response.text
    assert "Copyright 2026 GreeNovaX" in response.text
    assert "MQTT Adapter" in response.text
    assert "MQTT Broker" in response.text
    assert "MQTT Broker Status" in response.text
    assert "/api/adapters/mqtt/messages" in response.text
    assert "/api/adapters/mqtt/broker/status" in response.text
    assert "id=\"mqtt-broker-state\"" in response.text
    assert "id=\"mqtt-broker-body\"" in response.text
    assert "Audit Events" in response.text
    assert "function renderRows(targetId, items, columns)" in response.text
    assert "function renderSummary(summary)" in response.text
    assert "function renderHandoffPackage(packageInfo)" in response.text
    assert "Payload JSON" not in response.text
    assert "Customer routes" in response.text
    assert "function renderProductionHardening(items)" in response.text
    assert "production-readiness-result" in response.text
    assert "function renderOwnerApproval(items)" in response.text
    assert "function renderFeedbackSummary(summary)" in response.text
    assert "function renderFinalDelivery(items)" in response.text
    assert "function renderCustomerFeedback(items)" in response.text
    assert "function renderAIRouting(route)" in response.text
    assert "function renderAIModelBenchmarks(matrix)" in response.text
    assert "loadJson('/api/ai/model-benchmarks')" in response.text
    assert 'id="shell-ai-assurance-card"' in response.text
    assert 'id="shell-ai-assurance-score"' in response.text
    assert 'id="shell-ai-assurance-actions"' in response.text
    assert "function renderAIAssuranceConsole" in response.text
    assert "loadJson('/api/ai/assurance-console')" in response.text
    assert 'id="shell-ai-coworker-ladder-body"' in response.text
    assert "loadJson('/api/assistant/coworker-quality')" in response.text
    assert "function loadAssistantSessionsSafe" in response.text
    assert "loadAssistantSessionsSafe()" in response.text
    assert "fetch('/api/assistant/sessions', {" in response.text
    assert "headers: operatorHeaders()" in response.text
    assert "loadJson('/api/assistant/sessions')" not in response.text
    assert "function renderAssistantSessions" in response.text
    assert "function loadAssistantSessionDetail(sessionId)" in response.text
    assert "fetch(detailPath, { headers: operatorHeaders() })" in response.text
    assert "detailButton.dataset.sessionDetailPath = '/api/assistant/sessions/{session_id}'" in response.text
    assert "detailButton.addEventListener('click', () => loadAssistantSessionDetail(item.session_id))" in response.text
    assert 'id="assistant-session-threads"' in response.text
    assert 'id="shell-assistant-session-body"' in response.text
    assert 'id="assistant-session-detail"' in response.text
    assert "'/assistant': { view: 'intelligence', target: 'assistant'" in response.text
    assert "renderAIAssuranceConsole({...aiAssuranceConsole, coworker_quality_ladder: assistantCoworkerQuality});" in response.text
    assert 'id="shell-orchestration-control-card"' in response.text
    assert 'id="shell-orchestration-maturity"' in response.text
    assert 'id="shell-orchestration-release-gate"' in response.text
    assert 'id="shell-orchestration-teams"' in response.text
    assert 'id="shell-orchestration-lanes"' in response.text
    assert 'id="shell-orchestration-protocol-body"' in response.text
    assert 'id="shell-autopilot-token"' not in response.text
    assert 'id="shell-run-agent-autopilot"' in response.text
    assert 'id="shell-agent-autopilot-result"' in response.text
    assert '#shell-orchestration-control-card { order: 0; }' in response.text
    assert 'id="shell-model-benchmark-card"' in response.text
    assert 'id="ai-model-benchmarks-body"' in response.text
    assert "MODEL_BENCHMARK_CONTEXTS" in response.text
    assert "function renderAIEvaluations(items)" in response.text
    assert "function renderAssistantResponse(answer)" in response.text
    assert 'id="shell-assistant-workbench-card"' in response.text
    assert 'id="assistant-workbench-body"' in response.text
    assert 'id="assistant-workbench-action-body"' in response.text
    assert "function renderAssistantWorkbench" in response.text
    assert "continuity_brief" in response.text
    assert "Runtime connection" in response.text
    assert "const continuityActions" in response.text
    assert "evidence_label || 'Operational evidence'" in response.text
    assert "function renderShellAssistantProposalQueue(workbench)" in response.text
    assert "postJson('/api/assistant/tool-proposals/prepare'" in response.text
    assert "function approveAssistantProposal" in response.text
    assert "'/api/assistant/tool-proposals/' + encodeURIComponent(proposal.proposal_id) + '/approve'" in response.text
    assert "loadJson('/api/assistant/workbench')" in response.text
    assert "renderAssistantWorkbench(assistantWorkbench);" in response.text
    assert "/api/assistant/workbench" in response.text
    assert "function loadAssistantPreview()" in response.text
    assert "function postChatJson(payload)" in response.text
    assert "function postChatStream(payload, onProgress)" in response.text
    assert "function renderAssistantStreamProgress(state)" in response.text
    assert "await loadAssistantPreview();" in response.text
    assert "const answer = await postChatStream" in response.text
    assert "fetch('/api/assistant/stream'" in response.text
    assert "Summarize current operational risk and next operator action." in response.text
    assert "postJson('/api/chat'" not in response.text
    assert "function renderAcceptanceEvidencePack(pack)" in response.text
    assert "function renderMQTTBroker(status)" in response.text
    assert "Runtime Readiness Board" in response.text
    assert "id=\"phase-board-body\"" in response.text
    assert "function renderPhaseBoard(board)" in response.text
    assert "Operational Metrics" in response.text
    assert "id=\"report-package-summary\"" in response.text
    assert "id=\"dashboard-chart-count\"" in response.text
    assert "id=\"dashboard-report-count\"" in response.text
    assert "id=\"dashboard-agent-runs\"" in response.text
    assert "id=\"dashboard-ai-eval-runs\"" in response.text
    assert "id=\"chart-board\"" in response.text
    assert "chart-svg" in response.text
    assert "function chartColor(index)" in response.text
    assert "function createSvgBarChart(chart, maxValue)" in response.text
    assert "function formatChartValue(item, unit)" in response.text
    assert "Automation Administration" in response.text
    assert "UI/UX Experience Auditor" in response.text
    assert 'href="#ui-quality-gate"' in response.text
    assert '<div class="panel wide" id="ui-quality-gate">\n          <h2>UI/UX Quality Gate</h2>' in response.text
    assert "id=\"ui-ux-score\"" in response.text
    assert "id=\"ui-ux-gates-body\"" in response.text
    assert "function renderUIUXQualityGate(gate)" in response.text
    assert "id=\"advanced-settings-toggle\"" in response.text
    assert "aria-label=\"Advanced Settings\"" in response.text
    assert "id=\"advanced-settings-panel\"" in response.text
    assert "id=\"qa-challenge-form\"" in response.text
    assert "id=\"qa-challenge-runs-body\"" in response.text
    assert "function toggleAdvancedSettings()" in response.text
    assert "function renderQAChallengeRuns(items)" in response.text
    assert "postJson('/api/qa/challenge-runs'" in response.text
    assert "loadJson('/api/qa/challenge-runs')" in response.text
    assert "/api/qa/challenge-runs" in response.text
    assert "Continuous Quality Review" in response.text
    assert "id=\"continuous-qa-mission-form\"" in response.text
    assert "id=\"continuous-qa-mission-body\"" in response.text
    assert "function renderContinuousQAMission(mission)" in response.text
    assert "postJson('/api/qa/continuous-mission', payload)" in response.text
    assert "loadJson('/api/qa/continuous-mission')" in response.text
    assert "/api/qa/continuous-mission" in response.text
    assert "Quality Evidence Records" in response.text
    assert "id=\"qa-evidence-score\"" in response.text
    assert "id=\"qa-evidence-ab-body\"" in response.text
    assert "id=\"qa-evidence-gaps-body\"" in response.text
    assert "function renderQAEvidenceReport(report)" in response.text
    assert "loadJson('/api/qa/evidence-report')" in response.text
    assert "/api/qa/evidence-report" in response.text
    assert "id=\"agent-map-summary\"" in response.text
    assert "id=\"agent-map-count\"" in response.text
    assert "id=\"agent-map-links\"" in response.text
    assert "id=\"agent-map-approval-count\"" in response.text
    assert "id=\"agent-map-standard\"" in response.text
    assert "id=\"agent-map\"" in response.text
    assert "agent-map-svg" in response.text
    assert "function createAgentMapSvg(registry)" in response.text
    assert "function renderAgentMap(registry)" in response.text
    assert "function agentNodeClass(agent)" in response.text
    assert "id=\"agent-registry-body\"" in response.text
    assert "Team Section Records" in response.text
    assert "id=\"agent-section-reports-body\"" in response.text
    assert "Orchestration Evidence Matrix" in response.text
    assert "id=\"orchestration-matrix-body\"" in response.text
    assert "Dashboard Section Ownership Matrix" in response.text
    assert "id=\"section-ownership-matrix\"" in response.text
    assert "id=\"section-ownership-body\"" in response.text
    assert "function renderOrchestrationMatrix(matrix)" in response.text
    assert "matrix.dashboard_sections" in response.text
    assert "shell-orchestration-control-card" in response.text
    assert "shell-orchestration-teams" in response.text
    assert "shell-orchestration-lanes" in response.text
    assert "control.orchestration_team_count" in response.text
    assert "control.mandatory_parallel_lanes" in response.text
    assert "matrix.control_plane" in response.text
    assert "matrix.protocol_evidence" in response.text
    assert "function runShellAgentAutopilot" in response.text
    assert "postJson('/api/agents/autopilot/run', payload)" in response.text
    assert "Shell agent automation review completed:" in response.text
    assert "activateShellRouteNav('#operations', 'Operations')" in response.text
    assert "loadJson('/api/orchestration/evidence-matrix')" in response.text
    assert "Update Automation Control" in response.text
    assert "id=\"agent-control-form\"" in response.text
    assert "Analysis Profile" in response.text
    assert "name=\"analysis_profile_id\"" in response.text
    assert "name=\"model_route\"" in response.text
    assert "name=\"trace_policy\"" in response.text
    assert "name=\"eval_profile\"" in response.text
    assert "Operating Brief" in response.text
    assert "Handoff Policy" in response.text
    assert "Quality Gate Policy" in response.text
    assert "function populateAgentControlForm()" in response.text
    assert "Run Automation Task" in response.text
    assert "id=\"agent-runs-body\"" in response.text
    assert "Configurable Access Roles" in response.text
    assert "id=\"access-roles-body\"" in response.text
    assert "Update Access Role" in response.text
    assert "id=\"access-role-form\"" in response.text
    assert "User Access Assignments" in response.text
    assert "id=\"access-users-body\"" in response.text
    assert "Update User Access" in response.text
    assert "id=\"access-user-form\"" in response.text
    assert "function renderAccessUsers(items)" in response.text
    assert "AI Provider Policy" in response.text
    assert "id=\"ai-provider-policy-body\"" in response.text
    assert "Knowledge Center" in response.text
    assert 'href="#rag-knowledge"' in response.text
    assert '<div class="panel wide" id="rag-knowledge">' in response.text
    assert 'id="shell-rag-quality-card"' in response.text
    assert 'id="shell-rag-quality-body"' in response.text
    assert 'id="shell-rag-quality-score"' in response.text
    assert "function renderRAGQualityConsole" in response.text
    assert "id=\"rag-knowledge-body\"" in response.text
    assert "id=\"rag-search-form\"" in response.text
    assert "id=\"rag-search-body\"" in response.text
    assert "id=\"rag-knowledge-form\"" in response.text
    assert "function renderRAGKnowledge(base)" in response.text
    assert "loadJson('/api/rag/quality-console')" in response.text
    assert "function renderRAGSearch(result)" in response.text
    assert "loadJson('/api/rag/knowledge-base')" in response.text
    assert "loadJson('/api/assistant/quality-report')" in response.text
    assert "loadJson('/api/assistant/decision-brief')" in response.text
    assert "/api/assistant/decision-brief" in response.text
    assert "loadJson('/api/assistant/interactions')" in response.text
    assert "function renderAssistantQualityReport(report)" in response.text
    assert "function renderAssistantDecisionBrief(brief)" in response.text
    assert "function renderAssistantInteractions(ledger)" in response.text
    assert "function renderShellAssistantLedger(rows)" in response.text
    assert "shell-ledger-entry" in response.text
    assert "id=\"shell-assistant-ledger-card\"" in response.text
    assert "id=\"shell-assistant-ledger-body\"" in response.text
    assert "ASSISTANT_LEDGER_CONTEXTS" in response.text
    assert "setShellText('shell-ledger-total'" in response.text
    assert "fetch('/api/rag/search?" in response.text
    assert "controlPatchJson(controlPath('rag', 'knowledge', docId)" in response.text
    assert "Update AI Provider Policy" in response.text
    assert "id=\"ai-provider-policy-form\"" in response.text
    assert "id=\"ai-provider-model-select\"" in response.text
    assert "id=\"advanced-activate-11500\"" in response.text
    assert "Activate 11500 local route" in response.text
    assert "http://ollama.example.internal:11434" in response.text
    assert "id=\"shell-assistant-route-label\"" in response.text
    assert "id=\"shell-assistant-activity\"" in response.text
    assert "AI Analysis Profiles" in response.text
    assert "id=\"ai-analysis-profiles-body\"" in response.text
    assert "Update Analysis Profile" in response.text
    assert "id=\"ai-analysis-profile-form\"" in response.text
    assert "Operational Improvement Log" in response.text
    assert "id=\"evidence-findings-body\"" in response.text
    assert "Owner Decision Board" in response.text
    assert "id=\"owner-decisions-body\"" in response.text
    assert "Update Owner Decision" in response.text
    assert "id=\"owner-decision-form\"" in response.text
    assert "data-owner-preset=\"fallback-only\"" in response.text
    assert "data-owner-preset=\"production-hardening\"" in response.text
    assert "data-owner-preset=\"hosting-owner\"" in response.text
    assert "data-owner-preset=\"tls-ready\"" in response.text
    assert "data-owner-preset=\"backup-retention\"" in response.text
    assert "data-owner-preset=\"identity-provider\"" in response.text
    assert "data-owner-preset=\"mqtt-subscriber\"" in response.text
    assert "data-owner-preset=\"feedback-ready\"" in response.text
    assert "data-owner-preset=\"phase2-closure\"" in response.text
    assert "decision_id: 'production-hardening'" in response.text
    assert "decision_id: 'hosting-owner'" in response.text
    assert "decision_id: 'reverse-proxy-tls'" in response.text
    assert "decision_id: 'backup-retention'" in response.text
    assert "decision_id: 'identity-provider'" in response.text
    assert "decision_id: 'mqtt-broker-subscriber'" in response.text
    assert "const OWNER_DECISION_PRESETS" in response.text
    assert "function applyOwnerDecisionPreset" in response.text
    assert "without external provider parity claims" in response.text
    assert "without broker passwords or certificate material" in response.text
    assert "function renderOwnerDecisions(items)" in response.text
    assert "Runtime status" in response.text
    assert "Runtime allowed" in response.text
    assert "Run Assistant Evaluation" in response.text
    assert "id=\"ai-eval-runs-body\"" in response.text
    assert "function renderCharts(packageInfo)" in response.text
    assert "function renderAgentRegistry(registry)" in response.text
    assert "loadJson('/api/architecture/adr')" in response.text
    assert "function renderArchitectureADR(register)" in response.text
    assert 'id="shell-adr-card"' in response.text
    assert 'id="shell-adr-list"' in response.text
    assert "ADR_GOVERNANCE_CONTEXTS" in response.text
    assert "function renderAgentSectionReports(reports)" in response.text
    assert "function renderAgentRuns(items)" in response.text
    assert "agent-autopilot-form" in response.text
    assert "agent-autopilot-run-button" in response.text
    assert "agent-autopilot-status" in response.text
    assert "agent-autopilot-runs" in response.text
    assert "/api/agents/autopilot/run" in response.text
    assert "Go-Live Readiness Review" in response.text
    assert 'id="release-mission-control"' in response.text
    assert 'id="release-mission-form"' in response.text
    assert "loadJson('/api/release/mission')" in response.text
    assert "postJson('/api/release/mission/run'" in response.text
    assert "function renderReleaseMission" in response.text
    assert "SLA Target" in response.text
    assert "release-mission-sla" in response.text
    assert "mission.sla" in response.text
    assert "SLA Action Plan" in response.text
    assert 'id="release-mission-remediation-body"' in response.text
    assert 'id="shell-release-remediation-card"' in response.text
    assert 'id="shell-release-remediation-body"' in response.text
    assert 'id="shell-release-evidence-console-card"' in response.text
    assert 'id="shell-release-evidence-body"' in response.text
    assert 'id="shell-release-evidence-score"' in response.text
    assert 'id="shell-release-mission-token"' not in response.text
    assert 'id="shell-release-assistant-rounds"' in response.text
    assert 'id="shell-run-release-mission"' in response.text
    assert 'id="shell-release-mission-result"' in response.text
    assert "Runtime Decision Brief" in response.text
    assert "Plain runtime status, owner action" in response.text
    assert "function renderPhaseDecisionBrief" in response.text
    assert "function renderReleaseEvidenceConsole(consoleState, managementBrief, latestRecheck)" in response.text
    assert "function runShellReleaseMission" in response.text
    assert "postJson('/api/release/mission/run', payload)" in response.text
    assert "document.getElementById('shell-run-release-mission')" in response.text
    assert "loadJson('/api/release/evidence-console')" in response.text
    assert "loadJson('/api/recheck/latest')" in response.text
    assert "renderReleaseEvidenceConsole(releaseEvidenceConsole, managementBrief, latestRecheck);" in response.text
    assert "RELEASE_REMEDIATION_CONTEXTS" in response.text
    assert "function renderReleaseRemediationPlan(plan)" in response.text
    assert "renderReleaseRemediationPlan(mission.remediation_plan" in response.text
    assert "function renderAccessRoles(items)" in response.text
    assert "function renderAIProviderPolicy(policy)" in response.text
    assert "function renderAIAnalysisProfiles(profiles)" in response.text
    assert "function renderEvidenceFindings(items)" in response.text
    assert "function renderAIEvalRuns(items)" in response.text
    assert "function controlHeaders()" in response.text
    assert "function controlPatchJson(path, payload)" in response.text
    assert "identity-provider-body" in response.text
    assert "ai-routing-body" in response.text
    assert "ai-evaluations-body" in response.text
    assert "assistant-qa-form" in response.text
    assert "assistant-qa-rounds" in response.text
    assert "assistant-qa-run-button" in response.text
    assert "assistant-qa-result" in response.text
    assert "assistant-qa-stored-cases" in response.text
    assert "assistant-qa-provider-calls" in response.text
    assert "assistant-qa-status" in response.text
    assert "ui-visual-evidence-strip" in response.text
    assert "ui-visual-status" in response.text
    assert "function renderAlerts(items)" in response.text
    assert "replaceChildren()" in response.text
    assert "textContent = String(item[column] ?? '')" in response.text
    assert ".innerHTML =" not in response.text
    assert "/api/admin/access/local-users" in response.text
    assert "['/api', 'admin']" not in response.text
    assert "method: 'PATCH'" in response.text
    assert "controlMethod('patch')" not in response.text
    assert "function patchAdminJson" not in response.text
    assert "function adminPath" not in response.text
    assert "function controlPath" in response.text
    assert "function controlPatchJson" in response.text
    assert f"Version {__version__}" in response.text


def test_governance_cards_offer_interactive_review_actions() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert 'class="shell-pill shell-pill-action"' in body
    assert 'aria-label="Review AI assurance control surface"' in body
    assert 'aria-label="Review assistant workbench control surface"' in body
    assert 'aria-label="Review automation control surface"' in body
    assert 'aria-label="Review runtime policy control surface"' in body
    assert 'data-shell-target="ai-control"' in body
    assert 'data-shell-target="assistant"' in body
    assert 'data-shell-target="agent-control"' in body
    assert 'id="agent-protocol-contracts-body"' in body
    assert 'id="agent-tool-contracts-body"' in body
    assert 'id="shell-agent-card-count"' in body
    assert 'id="shell-agent-tool-contract-count"' in body
    assert "function renderAgentProtocolContracts" in body
    assert "loadJson('/api/orchestration/protocol-contracts')" in body
    assert "renderAgentProtocolContracts(agentProtocolContracts);" in body


def test_right_rail_assistant_renders_answer_without_raw_json_menu() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "function renderShellAssistantAnswer" in body
    assert "renderShellAssistantAnswer(answer);" in body
    assert "human approval proposals" in body
    assert "function assistantEvidenceLabel" in body
    assert "Loading current operational evidence..." in body
    assert "Initial setup needed: register device and ingest telemetry" in body
    assert "cards.slice(0, 2)" in body
    assert "setText(" not in body
    assert "assistantStateLabel" in body
    assert "session_id: 'shell-right-rail'" in body
    assert "Routing grounded assistant request through AI Diagnosis Agent: ' + text" not in body


def test_dashboard_ui_paths_return_html_shell_not_json() -> None:
    client = TestClient(create_app())

    for path in (
        "/dashboard",
        "/overview",
        "/operations",
        "/assets",
        "/reports",
        "/charts",
        "/analytics",
        "/status",
        "/settings",
    ):
        response = client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert not response.text.strip().startswith("{")
        assert "Operations Cockpit" in response.text
        assert "Prepared for GreeNovaX by IoT-AI.Tech" in response.text
        assert "const SHELL_ROUTE_CONTEXTS" in response.text
        assert "function openInitialShellRoute()" in response.text
        assert "const routePath = canonicalShellRoute(requestedRoute);" in response.text
        assert "const LEGACY_SHELL_ROUTE_ALIASES" not in response.text
        assert "return pathname || '/';" in response.text
        assert "window.history.replaceState({ route: routePath" not in response.text
        assert "openInitialShellRoute();" in response.text

    api_response = client.get("/api/version")
    assert api_response.status_code == 200
    assert api_response.headers["content-type"].startswith("application/json")


def test_sidebar_direct_urls_are_mapped_to_operational_surfaces() -> None:
    client = TestClient(create_app())

    response = client.get("/settings")

    assert response.status_code == 200
    route_expectations = {
        "/dashboard": "target: 'dashboard-shell'",
        "/operations": "target: 'operations'",
        "/assets": "target: 'assets'",
        "/monitoring": "target: 'operations'",
        "/alarms": "target: 'command-center'",
        "/workflows": "target: 'workflows'",
        "/orchestrator": "target: 'agent-control'",
        "/actions": "target: 'agent-control'",
        "/memory": "target: 'api-evidence'",
        "/anomaly-detection": "target: 'ai-control'",
        "/charts": "target: 'forecast-charts'",
        "/analytics": "target: 'rag-knowledge'",
        "/insights": "target: 'assistant'",
        "/reports": "target: 'reports-dashboard'",
        "/status": "target: 'ui-quality-gate'",
        "/settings": "target: 'advanced-settings-panel'",
    }
    for route, target in route_expectations.items():
        assert f"'{route}':" in response.text
        assert target in response.text
    assert "const CMDB_WORKSPACE_CONTEXTS = new Set(['assets']);" in response.text
    assert "const OPERATIONS_SHELL_CONTEXTS = new Set([" in response.text
    assert "OPERATIONS_SHELL_CONTEXTS.has(fallbackId)" in response.text
    assert "activateShellRouteNav(primaryHrefForContext(route));" in response.text
    assert "activeText: 'Operations'" in response.text
    assert "activeText: 'Reports'" in response.text
    assert "activeText: 'Analytics'" in response.text
    assert "activeText: 'Forecasts'" in response.text
    assert "activeText: 'Status'" in response.text
    assert "activeText: 'Administration'" in response.text


def test_sidebar_navigation_uses_canonical_routes_and_browser_history() -> None:
    client = TestClient(create_app())

    response = client.get("/dashboard")

    assert response.status_code == 200
    body = response.text
    assert "const SHELL_NAV_ROUTES" in body
    canonical_routes = {
        "Cockpit": "/dashboard",
        "Operations": "/operations",
        "Intelligence": "/insights",
        "Reports": "/reports",
        "Administration": "/settings/access",
        "Overview": "/overview",
        "Assets": "/assets",
        "Monitoring": "/monitoring",
        "Alarms": "/alarms",
        "Workflows": "/workflows",
        "Automation": "/orchestrator",
        "Anomaly Detection": "/anomaly-detection",
        "Forecasts": "/forecasts",
        "Insights": "/insights",
        "Runtime": "/releases",
        "Audit": "/evidence",
        "Settings": "/settings/access",
    }
    for label, route in canonical_routes.items():
        assert f"'{label}': '{route}'" in body
    assert "'Improvement Log': '/memory'" not in body
    assert "'Quality': '/tests'" not in body
    assert "'Registry': '/registry'" not in body
    assert "'Actions': '/actions'" not in body
    assert "window.history.pushState" in body
    assert "window.addEventListener('popstate', openInitialShellRoute)" in body
    assert "document.querySelectorAll('.shell-primary-nav a[href]')" in body
    assert "item.classList.remove('active');" in body
    assert "item.removeAttribute('aria-current');" in body
    assert "async function refreshFocusedWorkspace" in body
    assert "await refreshFocusedWorkspace(window.location.pathname" in body
    assert "qualityRoutes.has(route)" in body
    evidence_start = body.index("if (evidenceRoutes.has(route))")
    evidence_end = body.index("if (agentRoutes.has(route))", evidence_start)
    evidence_loader = body[evidence_start:evidence_end]
    assert "loadJsonSafe('/api/audit/events?limit=200')" in evidence_loader
    assert "loadJsonSafe('/api/security/status')" not in evidence_loader
    assert "loadJsonSafe('/api/access/policy')" not in evidence_loader
    assert "/api/delivery/evidence-pack" not in evidence_loader
    assert "/api/evidence/findings" not in evidence_loader
    assert "/api/evidence/action-board" not in evidence_loader
    advanced_start = body.index('id="advanced-model-services"')
    advanced_end = body.index('id="advanced-memory-policy-form"', advanced_start)
    advanced_services = body[advanced_start:advanced_end]
    assert ">Key Env" not in advanced_services
    assert ">Password Env" not in advanced_services
    assert 'id="shell-footer-runtime-state" data-state="partial">Checking</span>' in body
    assert 'id="shell-footer-live-label">Loading data</span>' in body
    assert "function setFooterRuntimeState(state)" in body
    assert "function expireBrowserSession()" in body
    assert "response.status === 401 && browserSession.authenticated" in body
    assert "reportRoutes.has(route)" in body
    assert "const CMDB_WORKSPACE_CONTEXTS = new Set(['assets']);" in body
    assert "project_gap_discovery" not in body
    assert "const excludedAuditTerms" in body


def test_operations_scenario_endpoint_makes_first_screen_actionable() -> None:
    client = TestClient(create_app())

    response = client.get("/api/operations/scenario")

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_id"] == "greenhouse-temperature-risk"
    assert body["title"] == "Greenhouse Temperature Risk"
    assert body["risk_threshold_c"] == 80.0
    assert body["critical_threshold_c"] == 85.0
    assert len(body["steps"]) == 4
    assert body["steps"][0]["endpoint"] == "/api/assets"
    assert body["steps"][2]["endpoint"] == "/api/telemetry"
    assert "audit identifier" in body["steps"][3]["expected_result"]


def test_operational_preview_endpoint_makes_empty_page_useful() -> None:
    client = TestClient(create_app())

    response = client.get("/api/operations/preview")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["preview_mode"] == "read_only"
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["scope_basis"] == "Approved customer delivery scope"
    assert body["kpis"]["connected_devices"] == 3
    assert body["kpis"]["open_alerts"] == 1
    assert body["alerts"][0]["severity"] == "critical"
    assert body["recovery_proposals"][0]["requires_approval"] is True
    assert "device_details" in body["tabs"]
    assert "configuration" in body["tabs"]
    assert "firmware" in body["tabs"]
    assert "alarm_management" in body["tabs"]
    assert "diagnosis" in body["tabs"]
    assert "settings" in body["tabs"]
    assert body["config_profiles"][0]["desired_firmware"] == "1.0.0"
    assert body["firmware_compatibility"][0]["compatible"] is True
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_project_drift_control_sets_six_hour_pm_release_auditor_gate() -> None:
    client = TestClient(create_app())

    response = client.get("/api/project/drift-control")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["prepared_for"] == "GreeNovaX"
    assert body["prepared_by"] == "IoT-AI.Tech"
    assert body["cadence_hours"] == 6
    assert body["review_result"] in {"PASS", "FAIL"}
    assert body["source_commit"]
    assert body["review_window"]["cadence_hours"] == 6
    assert body["review_window"]["window_state"] in {
        "needs_first_recorded_review",
        "current",
        "review_due",
        "review_timestamp_invalid",
    }
    assert body["kpi_sla"]["sla_target"] == 99.99
    assert "sla_gap" in body["kpi_sla"]
    assert {agent["agent_id"] for agent in body["required_agents"]} == {
        "project_delivery_coordinator",
        "release_compliance_controller",
    }
    assert any(source["reference"].endswith("CONTRACT_TRACEABILITY.en.md") for source in body["checked_sources"])
    assert any(link["endpoint"] == "/api/project/drift-control/run" for link in body["evidence_links"])
    assert body["release_block_state"] in {
        "clear",
        "blocked_until_drift_review_passes",
    }
    assert body["production_acceptance_state"] == "action_required"
    assert body["customer_acceptance_claimed"] is False
    assert body["production_acceptance"]["customer_acceptance_claimed"] is False
    assert body["production_acceptance"]["evidence_endpoint"] == (
        "/api/production/action-plan"
    )
    serialized = response.text.lower()
    assert "private " + "prompt" not in serialized
    assert "system " + "prompt" not in serialized
    assert "secret" not in serialized
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_project_drift_control_blocks_dirty_tracked_source_tree(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        agentiot_app,
        "source_worktree_state",
        lambda: {
            "state": "dirty",
            "dirty": True,
            "git_available": True,
            "changed_tracked_file_count": 2,
            "checked_path_count": 10,
            "scope": "tracked_delivery_sources",
        },
    )
    client = TestClient(create_app(database_path=tmp_path / "drift-dirty.db"))

    response = client.get("/api/project/drift-control")

    assert response.status_code == 200
    body = response.json()
    assert body["review_result"] == "FAIL"
    assert body["release_block_state"] == "blocked_until_drift_review_passes"
    assert body["source_tree"]["dirty"] is True
    assert body["source_tree"]["changed_tracked_file_count"] == 2
    deviations = {item["deviation_id"]: item for item in body["deviations"]}
    assert "tracked-source-tree-dirty" in deviations
    assert deviations["tracked-source-tree-dirty"]["severity"] == "P0"
    assert "app.py" not in response.text




def test_project_drift_control_blocks_dirty_runtime_source_commit(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "19721d54-dirty")
    monkeypatch.setattr(
        agentiot_app,
        "source_worktree_state",
        lambda: {
            "state": "clean",
            "dirty": False,
            "git_available": True,
            "changed_tracked_file_count": 0,
            "checked_path_count": 10,
            "scope": "tracked_delivery_sources",
        },
    )
    client = TestClient(create_app(database_path=tmp_path / "drift-runtime-dirty.db"))

    response = client.get("/api/project/drift-control")

    assert response.status_code == 200
    body = response.json()
    assert body["review_result"] == "FAIL"
    assert body["release_block_state"] == "blocked_until_drift_review_passes"
    assert body["source_commit"] == "19721d54-dirty"
    deviations = {item["deviation_id"]: item for item in body["deviations"]}
    assert "runtime-source-commit-dirty" in deviations
    assert deviations["runtime-source-commit-dirty"]["severity"] == "P0"

def test_project_drift_control_blocks_source_runtime_version_mismatch(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_SOURCE_VERSION", "0.134.25")
    client = TestClient(create_app(database_path=tmp_path / "drift-version.db"))

    response = client.get("/api/project/drift-control")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["runtime_version"] == __version__
    assert body["source_version"] == "0.134.25"
    assert body["review_result"] == "FAIL"
    assert body["release_block_state"] == "blocked_until_drift_review_passes"
    deviations = {item["deviation_id"]: item for item in body["deviations"]}
    assert "source-runtime-version-drift" in deviations
    assert deviations["source-runtime-version-drift"]["severity"] == "P0"


def test_project_drift_control_run_records_audit_and_finding(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "abc1234")
    client = TestClient(create_app(database_path=tmp_path / "drift-control.db"))

    response = client.post(
        "/api/project/drift-control/run",
        headers={"X-Operator-Token": "unit-" + "operator-" + "sentinel"},
        json={"force": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == __version__
    assert body["source_commit"] == "abc1234"
    assert body["recording"]["status"] == "recorded"
    assert body["recording"]["audit_event_id"] > 0
    assert body["recording"]["finding_id"].startswith("finding-")
    assert body["last_recorded_review"]["review_result"] == body["review_result"]
    assert body["review_window"]["window_state"] == "current"
    assert body["privacy"]["raw_prompts_returned"] == "false"

    audit_events = client.get("/api/audit/events").json()["items"]
    assert any(item["event_type"] == "project.drift_control.reviewed" for item in audit_events)
    findings = client.get(
        "/api/evidence/findings", headers=OPERATOR_HEADERS
    ).json()["items"]
    assert any(item["source"] == "project_drift_control" for item in findings)
    serialized = response.text.lower()
    assert "private " + "prompt" not in serialized
    assert "system " + "prompt" not in serialized
    assert "unit-" + "operator-" + "sentinel" not in response.text


def test_project_drift_control_run_records_release_change_inside_current_window(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "abc1234")
    client = TestClient(create_app(database_path=tmp_path / "drift-release.db"))
    headers = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}

    first = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": True},
    )
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "def5678")
    second = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": False},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    body = second.json()
    assert body["review_window"]["window_state"] == "current"
    assert body["source_commit"] == "def5678"
    assert body["recording"]["status"] == "recorded"
    assert body["recording"]["reason"] == "release_identity_changed"
    assert body["last_recorded_review"]["source_commit"] == "def5678"
    audit_events = client.get("/api/audit/events").json()["items"]
    drift_events = [
        item for item in audit_events
        if item["event_type"] == "project.drift_control.reviewed"
    ]
    assert len(drift_events) == 2


def test_project_drift_control_run_records_version_change_inside_current_window(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "abc1234")
    client = TestClient(create_app(database_path=tmp_path / "drift-version.db"))
    headers = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}

    first = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": True},
    )
    changed_version = "0.152.15-test"
    monkeypatch.setattr(agentiot_app, "__version__", changed_version)
    second = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": False},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    body = second.json()
    assert body["version"] == changed_version
    assert body["recording"]["status"] == "recorded"
    assert body["recording"]["reason"] == "release_identity_changed"
    assert body["last_recorded_review"]["version"] == changed_version
    audit_events = client.get("/api/audit/events").json()["items"]
    drift_events = [
        item for item in audit_events
        if item["event_type"] == "project.drift_control.reviewed"
    ]
    assert len(drift_events) == 2


def test_project_drift_control_run_skips_same_release_inside_current_window(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AGENTIOT_OPERATOR_TOKEN", "unit-" + "operator-" + "sentinel")
    monkeypatch.setenv("AGENTIOT_SOURCE_COMMIT", "abc1234")
    client = TestClient(create_app(database_path=tmp_path / "drift-skip.db"))
    headers = {"X-Operator-Token": "unit-" + "operator-" + "sentinel"}

    first = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": True},
    )
    second = client.post(
        "/api/project/drift-control/run",
        headers=headers,
        json={"force": False},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["recording"]["status"] == "skipped_current_window"
    audit_events = client.get("/api/audit/events").json()["items"]
    drift_events = [
        item for item in audit_events
        if item["event_type"] == "project.drift_control.reviewed"
    ]
    assert len(drift_events) == 1


def test_cockpit_route_renders_dashboard_shell_not_json() -> None:
    client = TestClient(create_app())

    response = client.get("/cockpit")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="dashboard-shell"' in response.text
    assert "Operations Cockpit" in response.text
    assert "Prepared for GreeNovaX by IoT-AI.Tech" in response.text


def test_about_path_explains_project_context() -> None:
    client = TestClient(create_app())

    response = client.get("/about")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "About AgentIoT" in response.text
    assert "Product Purpose" in response.text
    assert "contract" not in response.text.lower()
    assert "Why This Product" in response.text
    assert "Product Owner" in response.text
    assert "GreeNovaX" in response.text
    assert "Developer" in response.text
    assert "IoT-AI.Tech" in response.text
    assert "MIT License" in response.text
    assert f"Version {__version__}" in response.text
    assert "Copyright 2026 GreeNovaX" in response.text
    assert 'href="/healthz"' not in response.text
    assert 'href="/api/version"' not in response.text
    assert 'href="/docs"' not in response.text
    for path in ("/", "/operations", "/settings"):
        assert f'href="{path}"' in response.text


def test_dashboard_navigation_and_quality_actions_require_clear_access_state() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "activateShellRouteNav(primaryHrefForContext(routeContext));" in body
    assert 'id="shell-run-qa-challenge" data-requires-access="operator-write"' in body
    assert 'id="qa-challenge-form" class="inline-form" data-requires-access="operator-write"' in body
    assert 'id="assistant-qa-form" class="inline-form" data-requires-access="operator-write"' in body
    assert 'id="continuous-qa-mission-form" class="inline-form" data-requires-access="operator-write"' in body
    assert 'aria-label="Current access state"' in body
    assert 'id="shell-session-name">Read-only session</strong>' in body
    assert 'id="shell-session-state">Sign in required</small>' in body
    assert "const sessionName = browserSession.authenticated" in body
    assert ": 'Read-only session';" in body
    assert ": 'Sign in required';" in body
    assert "'Operator API access'" not in body
    assert "'Server validation pending'" not in body
    assert "field.disabled = !enabled || blockedByRunbook;" in body
    assert "const adminForms = new Set();" in body
    assert "field.disabled = !adminEnabled;" in body
    assert '<strong>Admin</strong><small>Operations</small>' not in body


def test_dashboard_uses_qualified_phase_readiness_labels() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "phase: item.metric_label || item.phase" in response.text


def test_unknown_browser_route_returns_dashboard_shell_not_raw_json() -> None:
    client = TestClient(create_app())

    response = client.get("/does-not-exist", headers={"accept": "text/html"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "AgentIoT Dashboard" in response.text
    assert "Operations Cockpit" in response.text
    assert '{"detail":"Not Found"}' not in response.text


def test_unknown_api_route_keeps_json_not_found_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/api/does-not-exist", headers={"accept": "text/html"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Not Found"}


def test_logo_asset_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/static/greenovax-logo.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_horizontal_logo_asset_is_served() -> None:
    client = TestClient(create_app())

    response = client.get("/static/greenovax-logo-horizontal.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_version_endpoint_declares_mit_clean_room_basis() -> None:
    client = TestClient(create_app())

    response = client.get("/api/version")

    assert response.status_code == 200
    body = response.json()
    assert body["product"] == "AgentIoT Dashboard"
    assert body["version"] == __version__
    assert body["license"] == "MIT"
    assert body["clean_room"] is True
    assert body["architecture_sign"] in {"x86", "ARM", "unknown"}
    assert body["hardware_technology"]


def test_version_endpoint_exposes_baked_runtime_manifest_digest(monkeypatch) -> None:
    digest = "sha256:" + ("a" * 64)
    monkeypatch.setenv("AGENTIOT_RUNTIME_DIGEST", digest)
    client = TestClient(create_app())

    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.json()["runtime_digest"] == digest



def test_api_route_table_has_no_duplicate_method_paths(tmp_path) -> None:
    app = create_app(database_path=tmp_path / "route-table.db")
    seen: set[tuple[str, str]] = set()
    duplicates: list[str] = []
    methods_by_path: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if not (path.startswith("/api/") or path in {"/healthz", "/readyz"}):
            continue
        clean_methods = set(methods) - {"HEAD", "OPTIONS"}
        if clean_methods:
            methods_by_path.setdefault(path, set()).update(clean_methods)
        for method in clean_methods:
            key = (method, path)
            if key in seen:
                duplicates.append(f"{method} {path}")
            seen.add(key)

    assert duplicates == []
    assert methods_by_path["/api/hardware/discovery/profiles"] == {"GET", "POST"}
    assert methods_by_path["/api/hardware/discovery/usb/status"] == {"GET"}
    assert methods_by_path["/api/hardware/discovery/usb/sysfs"] == {"GET"}


def test_openapi_schema_exposes_contracted_api_baseline() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert CONTRACTED_PATHS.issubset(paths)
