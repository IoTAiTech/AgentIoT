# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.153.0 | Date: 2026-07-16

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_PAGE = REPO_ROOT / "src" / "agentiot" / "root_page.html"


def test_administration_forms_are_contained_at_mobile_width() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    containment = body.split(
        ".advanced-settings,\n      .advanced-settings > *", 1
    )[1].split("}", 1)[0]
    assert "box-sizing: border-box" in containment
    assert "max-width: 100%" in containment
    assert "min-width: 0" in containment
    assert ".advanced-settings .shell-settings-command-grid > *" in body
    assert ".advanced-settings .inline-form > *" in body
    assert ".advanced-settings input," in body
    mobile = body.split("@media (max-width: 520px)", 1)[1]
    assert ".advanced-settings .shell-settings-command-grid," in mobile
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert "width: 100%" in mobile


def test_intelligence_transforms_internal_evidence_language() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "function customerSafeAssistantText(value)" in body
    assert "customerSafeAssistantText(streamed)" in body
    assert "customerSafeAssistantText((answer || {}).answer || text)" in body
    assert "customerSafeAssistantText(answer.answer)" in body
    assert ".innerHTML" not in body

    start = body.index("function operatorVisibleText(value)")
    end = body.index("function ownerDisplayLabel", start)
    functions = body[start:end]
    probe = """
const transformed = customerSafeAssistantText(
  'Use [rag_knowledge:ui-management] to validate the evidence in the linked APIs before acting. Keep the temperature threshold unchanged.'
);
if (transformed.includes('rag_knowledge') || transformed.includes('linked API')) process.exit(2);
if (!transformed.includes('available operational evidence')) process.exit(3);
if (!transformed.includes('Keep the temperature threshold unchanged.')) process.exit(4);
if (transformed.toLowerCase().includes('validate the evidence')) process.exit(5);
"""
    result = subprocess.run(
        ["node", "-e", functions + probe],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_intelligence_has_a_safe_authenticated_data_fallback() -> None:
    body = ROOT_PAGE.read_text(encoding="utf-8")

    assert "const safeBase = base || {};" in body
    assert "const metrics = safeBase.metrics || {};" in body
    assert "(safeBase.items || []).map" in body
    assert "'Connect telemetry'" in body
    assert "'Waiting for data'" in body
    assert "'Setup required'" not in body
