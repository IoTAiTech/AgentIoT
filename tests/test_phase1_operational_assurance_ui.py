# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

from pathlib import Path


ROOT_PAGE = (
    Path(__file__).resolve().parents[1] / "src" / "agentiot" / "root_page.html"
)


def test_operational_assurance_is_a_safe_fault_isolated_read_only_surface() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert 'id="shell-operational-assurance"' in body
    assert "Operational Assurance" in body
    assert "Last checked" in body
    assert "Run self-check" in body
    assert "const OPERATIONAL_ASSURANCE_ENDPOINTS = [" in body
    for endpoint in (
        "/readyz",
        "/api/security/status",
        "/api/operations/summary",
        "/api/adapters/mqtt/broker/status",
        "/api/adapters/rest/status",
        "/api/production/backup-retention",
    ):
        assert endpoint in body
    assert "Promise.allSettled" in body
    assert "path === '/readyz' && response.status === 503" in body
    assert "function renderOperationalAssurance" in body
    assert "function refreshOperationalAssurance" in body
    assert "textContent" in body
    assert ".innerHTML" not in body
    for forbidden_reference in (
        "mqttStatus.host",
        "mqttStatus.topic_filter",
        "mqttStatus.port",
        "mqttStatus.last_error",
        "securityStatus.secret_delivery",
        "backupRetention.policy_fingerprint",
        "backupRetention.restore_evidence_fingerprint",
    ):
        assert forbidden_reference not in body


def test_operational_assurance_exposes_productive_service_controls_and_table() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    for label in (
        "Full HTTP(S) Services Table",
        "Solve Issues",
        "Auto Heal",
        "Self Check",
        "Debug Dump",
        "Service Operations Settings",
    ):
        assert label in body
    for element_id in (
        "shell-service-solve",
        "shell-service-auto-heal",
        "shell-service-self-check",
        "shell-service-debug-dump",
        "shell-http-services-body",
        "service-operations-settings-form",
    ):
        assert f'id="{element_id}"' in body
    assert '<details class="shell-service-table" id="shell-http-services-details">' in body
    assert '<summary class="shell-service-table-head" aria-describedby="shell-http-services-summary">' in body
    assert 'id="shell-http-services-summary" role="status" aria-live="polite"' in body
    for endpoint in (
        "/api/services/http",
        "/api/services/http/self-check",
        "/api/services/http/solve-issues",
        "/api/services/http/auto-heal",
        "/api/system/debug-dump",
    ):
        assert endpoint in body
    assert "controlPath('service-operations', 'settings')" in body
    assert 'id="shell-service-solve"' in body and 'data-requires-access="operator-write"' in body
    assert 'id="shell-service-debug-dump"' in body and 'data-requires-access="admin-control"' in body
    assert "function renderHttpServices" in body
    assert "function downloadDebugDump" in body
    assert ".innerHTML" not in body


def test_service_settings_and_operator_tokens_cannot_replay_stale_ui_values() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "if (input && input !== source && !input.value)" not in body
    assert "function syncOperatorTokenInputs" not in body
    assert 'id="shell-workbench-token"' not in body
    assert 'id="shell-workflow-token"' not in body
    assert "serviceOperationsSettingsLoaded" in body
    assert "await loadServiceOperationsSettings()" in body
    assert "if (!serviceOperationsSettingsLoaded)" in body
    assert "['admin_token_required', 'admin_sign_in_required'].includes(payload?.status)" in body


def test_visual_qa_exercises_authenticated_service_controls() -> None:
    runner = (
        ROOT_PAGE.parents[2] / "tools" / "run_visual_qa.js"
    ).read_text(encoding="utf-8")

    for expected in (
        "AGENTIOT_VISUAL_ADMIN_PASSWORD_FILE",
        "AGENTIOT_VISUAL_REQUIRE_AUTH",
        "authenticateVisualContext",
        "shell-service-self-check",
        "shell-service-solve",
        "shell-service-auto-heal",
        "shell-service-debug-dump",
        "authenticated_actions_exercised",
        "post_self_check",
        "service self-check totals are inconsistent or unchecked/down",
        "agentiot.debug-dump.v1",
        "selected-period telemetry counts disagree",
        "active alarm counts disagree",
        "footer reports operational while live data is unavailable",
        "footer did not settle after route load",
        "expired session re-enabled an operator action",
        "session_expiry_guard",
    ):
        assert expected in runner
    assert "password: adminPassword" not in runner


def test_expired_sessions_and_failed_live_data_cannot_keep_green_status() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "let browserSessionExpired = false;" in body
    assert "response.status === 401 && browserSession.authenticated" in body
    assert "expireBrowserSession();" in body
    assert "Session expired: sign in again" in body
    assert "'authentication-required': { chip: 'Sign-in required', live: 'Session expired' }" in body
    assert "primaryFailures.length" in body
    assert "? 'degraded'" in body
    assert 'button.primary[aria-disabled="true"]' in body
    pilot_start = body.index("async function runPilotAction")
    pilot_end = body.index("async function openWorkbenchForm", pilot_start)
    pilot_action = body[pilot_start:pilot_end]
    assert "updateWorkbenchActionAvailability();" in pilot_action
    assert "control.disabled = false;" not in pilot_action


def test_active_alarms_and_recovery_stay_visible_outside_the_chart_window() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "const openAlerts = (alerts.items || []).filter" in body
    assert "const pendingProposals = (proposals.items || []).filter" in body
    assert "['open', 'active', 'new'].includes" in body
    assert "['pending_approval', 'pending', 'waiting_approval', 'draft'].includes" in body
    assert "filterByActiveTimeRange(alerts.items" not in body
    assert "filterByActiveTimeRange(proposals.items" not in body
    assert "proposalItems" not in body
    assert "'shell-proposal-select',\n          pendingProposals," in body
    assert "summary.time_window" in body
    assert "parsed >= start && parsed < end" in body
    assert "summary.comparisons?.telemetry?.current_period" in body
    assert "No open alarm.'" in body


def test_audit_workspace_loads_a_bounded_operational_history() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "Recent Operational Events" in body
    assert "Total Events" not in body
    assert "loadJsonSafe('/api/audit/events?limit=200')" in body
    for prefix in ("'ai.'", "'assistant.'", "'agent.'", "'simulation.'"):
        assert prefix in body
    excluded_terms = body[body.index("const excludedAuditTerms"):]
    excluded_terms = excluded_terms[: excluded_terms.index(";")]
    assert "|agent|" not in excluded_terms
