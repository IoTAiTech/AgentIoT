# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.2 | Date: 2026-08-09

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PAGE = REPO_ROOT / "src" / "agentiot" / "root_page.html"


def _mobile_css(body: str) -> str:
    return body.split("@media (max-width: 760px)", 1)[1].split("@media (max-width: 520px)", 1)[0]


def _tablet_css(body: str) -> str:
    return body.split(
        "@media (min-width: 761px) and (max-width: 1180px)", 1
    )[1].split("@media (max-width: 760px)", 1)[0]


def test_mobile_primary_navigation_wraps_complete_labels_without_horizontal_scroll() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    mobile = _mobile_css(body)

    assert ".shell-nav {" in mobile
    sidebar = mobile.split(".shell-sidebar {", 1)[1].split("}", 1)[0]
    nav = mobile.split(".shell-nav {", 1)[1].split("}", 1)[0]
    assert "overflow-x: hidden" in sidebar
    assert "grid-template-columns: minmax(0, 1fr)" in sidebar
    assert "overflow-x: visible" in nav
    assert ".shell-primary-nav {" in mobile
    assert "display: grid" in mobile
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in mobile
    assert "min-width: 0" in mobile
    assert ".shell-primary-nav a {" in mobile
    assert "min-height: 44px" in mobile
    assert ".shell-nav a:focus-visible" in body
    for destination in ("Cockpit", "Operations", "Intelligence", "Reports", "Administration", "About"):
        assert f">{destination}</a>" in body


def test_mobile_navigation_needs_no_overflow_control() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    mobile = _mobile_css(body)

    assert 'id="shell-nav-more"' not in body
    assert "installMobileNavigationAffordance" not in body
    assert "revealPrimaryNavigationLink" not in body
    assert "window.scrollTo({ top: 0, behavior: 'auto' });" in body
    assert "position: sticky" in mobile


def test_mobile_operations_tabs_wrap_complete_labels_without_horizontal_scroll() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    mobile = _mobile_css(body)

    assert 'class="shell-workspace-tabs-frame"' in body
    assert 'id="shell-workspace-tabs-more"' not in body
    assert "function installWorkspaceTabAffordance()" not in body
    assert "revealOperationsWorkspaceTab(selectedTab);" in body
    assert ".shell-workspace-tabs-frame {" in mobile
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert ".shell-workspace-tabs {" in mobile
    assert "flex-wrap: wrap" in mobile
    assert "overflow-x: visible" in mobile
    assert ".shell-workspace-tab {" in mobile
    assert "flex: 1 1 auto" in mobile
    assert "white-space: nowrap" in mobile


def test_recovery_queue_and_tablet_workflows_are_responsive() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    tablet = _tablet_css(body)
    compact = body.split("@media (max-width: 520px)", 1)[1]
    command_grid = body.split(".shell-workbench-command-grid {", 1)[1].split("}", 1)[0]

    assert 'id="shell-recovery-queue-pane"' in body
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in command_grid
    assert ".shell-workbench-command-grid {" in tablet
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in tablet
    assert '.shell-workbench-pane[data-workspace-panel="assets"],' in body
    assert '.shell-workbench-pane[data-workspace-panel="monitoring"] {' in body
    assert "grid-column: 1 / -1" in body
    assert '.shell-workbench-pane[data-workspace-panel="assets"] table,' in body
    assert '.shell-workbench-pane[data-workspace-panel="monitoring"] table {' in body
    assert "#shell-recovery-queue-pane {" in body
    assert "grid-column: 1 / -1" in body
    assert "#shell-recovery-queue-pane table {" in body
    assert "table-layout: fixed" in body
    assert "#shell-recovery-queue-pane thead," in compact
    assert "display: none" in compact
    assert "#shell-recovery-queue-pane td::before" in compact
    assert '.shell-workbench-pane[data-workspace-panel="assets"] thead' in compact
    assert '.shell-workbench-pane[data-workspace-panel="assets"] td::before' in compact
    assert '.shell-workbench-pane[data-workspace-panel="monitoring"] thead' in compact
    assert '.shell-workbench-pane[data-workspace-panel="monitoring"] td::before' in compact
    assert body.count('placeholder="e.g. 1.2.3"') == 2
    assert "Enter firmware version" not in body


def test_responsive_operational_tables_and_controls_are_not_detached() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "@media (max-width: 1500px)" in body
    assert ".shell-service-table td::before" in body
    assert "const labels = ['Service', 'Surface', 'Access', 'Transport'];" in body
    assert "const detailLabels = ['HTTP', 'Latency', 'Security', 'Last check'];" in body
    assert 'class="shell-settings-command-card provider-status-card"' in body
    assert 'class="form-row shell-checkbox-row"' in body
    assert ".form-row.shell-checkbox-row input[type=\"checkbox\"]" in body


def test_empty_runtime_assistant_uses_a_concise_operator_message() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    message = "Diagnosis is unavailable until live telemetry is connected."
    assert message in body
    assert "confidence === 'low_no_runtime_records'\n            ? text" in body
    assert "Unavailable until live operational evidence exists." in body
    assert "Telemetry is not connected." in body


def test_unavailable_model_provider_uses_warning_state() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "const providerNeedsReview = configured === 0" in body
    assert "providerRuntimeState?.classList.toggle('warn', providerNeedsReview);" in body


def test_mobile_footer_flows_after_administration_content() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    mobile = _mobile_css(body)

    assert "overflow: visible" in mobile
    assert ".shell-main { overflow: visible; padding-bottom: 20px; }" in mobile
    footer = mobile.rsplit(".shell-footer {", 1)[1].split("}", 1)[0]
    assert "position: static" in footer


def test_mobile_provider_connection_form_flows_to_footer() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    mobile = _mobile_css(body)

    selector = ".shell-context > .advanced-settings:not([hidden]) {"
    assert selector in mobile
    settings = mobile.split(selector, 1)[1].split("}", 1)[0]
    assert "max-height: none" in settings
    assert "overflow: visible" in settings


def test_operations_runtime_state_uses_concise_operator_labels() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")
    start = body.index("function selectedTimeRangeLabel()")
    end = body.index("function activeTimeRangeCutoff()", start)
    functions = body[start:end]
    probe = """
const nodes = {
  'shell-time-range-control': { selectedOptions: [{ textContent: 'Last 15 minutes' }] },
  'shell-workbench-state': { dataset: { statusLabel: 'Initial setup · No live records' }, textContent: '' }
};
global.document = { getElementById: (id) => nodes[id] || null };
function setShellText(id, value) { nodes[id].textContent = value; }
if (operationalStateLabel('initial_setup_ready_no_live_records') !== 'Initial setup · No live records') process.exit(2);
if (operationalStateLabel('monitoring_active') !== 'Monitoring active') process.exit(3);
updateWorkbenchRangeLabel();
if (nodes['shell-workbench-state'].textContent !== 'Initial setup · No live records · Last 15 minutes') process.exit(4);
"""
    result = subprocess.run(
        ["node", "-e", functions + probe],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
