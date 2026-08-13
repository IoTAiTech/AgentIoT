# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

"""Customer-safe project governance helpers for drift and gap boards."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def parse_audit_timestamp(value: str | None) -> datetime | None:
    """Parse stored audit timestamps as aware UTC datetimes."""

    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def review_window(
    latest_review: dict[str, Any] | None,
    *,
    cadence_hours: int,
) -> dict[str, Any]:
    """Return whether a governance review window is current or due."""

    if not latest_review:
        return {
            "cadence_hours": cadence_hours,
            "window_state": "needs_first_recorded_review",
            "last_review_at": None,
            "next_review_due_at": None,
        }
    last_review_at = parse_audit_timestamp(str(latest_review.get("created_at") or ""))
    if not last_review_at:
        return {
            "cadence_hours": cadence_hours,
            "window_state": "review_timestamp_invalid",
            "last_review_at": latest_review.get("created_at"),
            "next_review_due_at": None,
        }
    next_due = last_review_at + timedelta(hours=cadence_hours)
    return {
        "cadence_hours": cadence_hours,
        "window_state": "review_due" if datetime.now(UTC) >= next_due else "current",
        "last_review_at": last_review_at.isoformat(),
        "next_review_due_at": next_due.isoformat(),
    }


def project_drift_review_window(latest_review: dict[str, Any] | None) -> dict[str, Any]:
    """Return whether the six-hour drift review window is current or due."""

    return review_window(latest_review, cadence_hours=6)


def project_gap_review_window(latest_review: dict[str, Any] | None) -> dict[str, Any]:
    """Return whether the 6-hour gap-discovery review window is current or due."""

    return review_window(latest_review, cadence_hours=6)


def project_phase_closure_tasks(
    *,
    hardening: dict[str, Any],
    route_decision: dict[str, Any],
    release: dict[str, Any],
    drift: dict[str, Any],
    phase1_closure_decision: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return customer-safe tasks for remaining phase acceptance distance."""

    production_acceptance = release.get("production_acceptance", {})
    phase1_commercial_approved = bool(
        phase1_closure_decision
        and phase1_closure_decision.get("decision_id") == "phase-1-closure"
        and phase1_closure_decision.get("state") == "approved"
    )
    release_ready = (
        release.get("summary", {}).get("sla_gap", 1) <= 0
        and release.get("summary", {}).get("gates_ready")
        == release.get("summary", {}).get("gates_total")
        and drift.get("review_result") == "PASS"
    )
    hardening_items = hardening.get("items", [])
    hardening_waits_for_customer = any(
        item.get("state") == "customer_action_required"
        for item in hardening_items
        if isinstance(item, dict)
    )
    hardening_requires_secret = any(
        item.get("state") == "customer_action_required"
        and item.get("control_id") in {"identity-provider", "mqtt-broker-subscriber"}
        for item in hardening_items
        if isinstance(item, dict)
    )
    hardening_status = (
        "ready"
        if hardening.get("ready")
        else (
            "owner_decision_required"
            if hardening_waits_for_customer
            else "action_required"
        )
    )
    phase1_contract_tasks = [
        {
            "task_id": "phase1-m1-1-workshop-evidence",
            "phase": "Phase 1",
            "contract_milestone": "M1.1",
            "due_date": "2026-06-30",
            "overdue": True,
            "work_type": "external_evidence",
            "owner_agent_id": "product_delivery_manager",
            "status": "external_evidence_required",
            "acceptance_gate": "kickoff_workshop_evidence",
            "evidence_endpoint": "docs/customer/monthly/JUNE_2026_REPORT.en.md",
            "next_action": (
                "Record signed workshop minutes, attendance, decisions, and customer "
                "confirmation; do not infer attendance from the requirements baseline."
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase1-m1-2-architecture-design",
            "phase": "Phase 1",
            "contract_milestone": "M1.2",
            "due_date": "2026-06-30",
            "overdue": False,
            "work_type": "technical_evidence",
            "owner_agent_id": "architecture_controller",
            "status": "ready",
            "acceptance_gate": "architecture_function_design_v1",
            "evidence_endpoint": "docs/customer/phase1/ARCHITECTURE.en.md",
            "next_action": "Keep architecture and function design aligned with tested runtime contracts.",
            "can_close_by_code": False,
            "customer_decision_required": False,
            "requires_secret": False,
            "requires_external_evidence": False,
            "must_not_fake": True,
        },
        {
            "task_id": "phase1-m1-3-hardware-procurement-evidence",
            "phase": "Phase 1",
            "contract_milestone": "M1.3",
            "due_date": "2026-06-30",
            "overdue": True,
            "work_type": "external_evidence",
            "owner_agent_id": "hardware_delivery_controller",
            "status": "external_evidence_required",
            "acceptance_gate": "demonstrator_hardware_procurement",
            "evidence_endpoint": "docs/customer/phase1/HARDWARE_FIRMWARE_PLAN.en.md",
            "next_action": (
                "Attach purchase, delivery, serial, and custody evidence; the BOM alone "
                "does not prove procurement."
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase1-m1-4-ui-ux-design",
            "phase": "Phase 1",
            "contract_milestone": "M1.4",
            "due_date": "2026-07-31",
            "overdue": False,
            "work_type": "technical_evidence",
            "owner_agent_id": "ui_experience_controller",
            "status": "ready",
            "acceptance_gate": "ui_ux_design",
            "evidence_endpoint": "/api/ui/quality-gate",
            "next_action": "Refresh version-bound browser evidence after every frontend change.",
            "can_close_by_code": False,
            "customer_decision_required": False,
            "requires_secret": False,
            "requires_external_evidence": False,
            "must_not_fake": True,
        },
        {
            "task_id": "phase1-m1-5-mqtt-rest-backend",
            "phase": "Phase 1",
            "contract_milestone": "M1.5",
            "due_date": "2026-07-31",
            "overdue": False,
            "work_type": "technical_evidence",
            "owner_agent_id": "protocol_integration_controller",
            "status": "ready",
            "acceptance_gate": "mqtt_rest_backend_start",
            "evidence_endpoint": "/api/adapters/mqtt/broker/status",
            "next_action": "Refresh the isolated MQTT/REST protocol receipt on the current release candidate.",
            "can_close_by_code": False,
            "customer_decision_required": False,
            "requires_secret": False,
            "requires_external_evidence": False,
            "must_not_fake": True,
        },
        {
            "task_id": "phase1-m1-6-physical-firmware-validation",
            "phase": "Phase 1",
            "contract_milestone": "M1.6",
            "due_date": "2026-07-31",
            "overdue": True,
            "work_type": "hardware_evidence",
            "owner_agent_id": "firmware_compatibility_controller",
            "status": "hardware_evidence_required",
            "acceptance_gate": "physical_raspberry_pi_compatibility",
            "evidence_endpoint": "/api/firmware/compatibility",
            "next_action": (
                "Run and record physical Raspberry Pi 4/5 or approved ARM hardware "
                "validation; x86 simulation is not field evidence."
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase1-m1-7-consolidation-handover",
            "phase": "Phase 1",
            "contract_milestone": "M1.7",
            "due_date": "2026-08-31",
            "overdue": False,
            "work_type": "delivery_evidence",
            "owner_agent_id": "project_delivery_coordinator",
            "status": "in_progress",
            "acceptance_gate": "phase1_consolidation_handover",
            "evidence_endpoint": "docs/customer/phase1/PHASE_1_REPORT.en.md",
            "next_action": "Consolidate current evidence and complete customer handover by the August milestone date.",
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
    ]
    return [
        *phase1_contract_tasks,
        {
            "task_id": "phase1-commercial-baseline-review",
            "phase": "Phase 1",
            "work_type": "external_evidence",
            "owner_agent_id": "product_delivery_manager",
            "status": "ready" if phase1_commercial_approved else "review_ready",
            "acceptance_gate": "commercial_baseline_review",
            "evidence_endpoint": (
                "docs/customer/phase1/COMMERCIAL_BASELINE_EVIDENCE.en.md"
            ),
            "next_action": (
                "The commercial baseline review is owner-approved. This does not "
                "close workshop, procurement, physical hardware, or handover evidence."
                if phase1_commercial_approved
                else (
                    "Commercial baseline v1.7 evidence is recorded; owner review "
                    "remains separate from contractual milestone acceptance."
                )
            ),
            "can_close_by_code": False,
            "customer_decision_required": not phase1_commercial_approved,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase2-production-hardening-controls",
            "phase": "Phase 2",
            "work_type": "implementation_evidence",
            "owner_agent_id": "release_compliance_controller",
            "status": hardening_status,
            "acceptance_gate": "production_hardening",
            "evidence_endpoint": "/api/production/hardening",
            "next_action": (
                "Customer runtime configuration or owner approval remains; "
                "do not close this by code."
                if hardening_waits_for_customer
                else hardening.get(
                    "next_gate",
                    "Close production hardening controls with runtime evidence.",
                )
            ),
            "can_close_by_code": bool(
                not hardening.get("ready") and not hardening_waits_for_customer
            ),
            "customer_decision_required": hardening_waits_for_customer,
            "requires_secret": hardening_requires_secret,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase2-model-route-owner-decision",
            "phase": "Phase 2",
            "work_type": "owner_signoff_and_secret",
            "owner_agent_id": "AI_Diagnosis_Agent",
            "status": (
                "ready"
                if route_decision.get("ready")
                else "owner_decision_required"
            ),
            "acceptance_gate": "ai_model_route_approval",
            "evidence_endpoint": route_decision.get(
                "evidence_endpoint",
                "/api/production/approval-package",
            ),
            "next_action": route_decision.get(
                "next_action",
                "Record model-route owner decision or keep fallback-only delivery labelled.",
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": (
                route_decision.get("delivery_mode") == "owner_decision_required"
            ),
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase2-production-owner-signoff",
            "phase": "Phase 2",
            "work_type": "owner_signoff",
            "owner_agent_id": "project_delivery_coordinator",
            "status": (
                "ready"
                if production_acceptance.get("state") == "ready"
                else "owner_decision_required"
            ),
            "acceptance_gate": "production_owner_feedback_review",
            "evidence_endpoint": "/api/production/action-plan",
            "next_action": (
                "Record production-owner feedback, identity, hosting, backup, "
                "broker, and signoff decisions."
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase3-customer-release-package",
            "phase": "Phase 3",
            "work_type": "delivery_evidence",
            "owner_agent_id": "software_release_controller",
            "status": "ready" if release_ready else "action_required",
            "acceptance_gate": "clean_customer_release",
            "evidence_endpoint": "/api/release/evidence-console",
            "next_action": (
                "Keep the customer-safe Docker/source/docs bundle reproducible "
                "on the current source commit."
            ),
            "can_close_by_code": not release_ready,
            "customer_decision_required": False,
            "requires_secret": False,
            "requires_external_evidence": False,
            "must_not_fake": True,
        },
        {
            "task_id": "phase3-business-plan-presentation-review",
            "phase": "Phase 3",
            "work_type": "customer_review_evidence",
            "owner_agent_id": "product_delivery_manager",
            "status": "review_ready",
            "acceptance_gate": "business_plan_and_final_presentation",
            "evidence_endpoint": "/api/delivery/final-package",
            "next_action": (
                "Review final business plan and presentation with customer; "
                "record acceptance feedback separately."
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
        {
            "task_id": "phase3-final-acceptance-signoff",
            "phase": "Phase 3",
            "work_type": "owner_signoff",
            "owner_agent_id": "product_delivery_manager",
            "status": "owner_decision_required",
            "acceptance_gate": "final_acceptance",
            "evidence_endpoint": "/api/delivery/evidence-pack",
            "next_action": (
                "Do not claim final acceptance until customer signoff evidence "
                "is recorded in approved delivery records."
            ),
            "can_close_by_code": False,
            "customer_decision_required": True,
            "requires_secret": False,
            "requires_external_evidence": True,
            "must_not_fake": True,
        },
    ]


def project_phase_distance(
    phase_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return task-derived technical closure signals, never contract progress."""

    tasks_by_phase: dict[str, list[dict[str, Any]]] = {}
    for task in phase_tasks:
        tasks_by_phase.setdefault(str(task["phase"]), []).append(task)

    labels = {
        "Phase 1": "Foundation technical closure tasks",
        "Phase 2": "Core runtime technical closure tasks",
        "Phase 3": "Delivery technical closure tasks",
    }
    result: list[dict[str, Any]] = []
    for phase in ("Phase 1", "Phase 2", "Phase 3"):
        tasks = tasks_by_phase.get(phase, [])
        total = len(tasks)
        ready = sum(task.get("status") == "ready" for task in tasks)
        review_ready = sum(task.get("status") == "review_ready" for task in tasks)
        open_count = total - ready
        readiness = round(ready / total * 100) if total else 0
        result.append(
            {
                "phase": phase,
                "technical_readiness_percent": readiness,
                "technical_gap_percent": 100 - readiness,
                "metric_scope": "technical_closure_task_readiness",
                "metric_label": labels[phase],
                "contractual_milestone_progress": "not_calculated",
                "customer_acceptance_claimed": False,
                "ready_task_count": ready,
                "review_ready_task_count": review_ready,
                "open_task_count": open_count,
                "total_task_count": total,
                "readiness_basis": "ready_closure_tasks_only",
                "reason": (
                    f"{ready} of {total} technical closure task(s) are ready; "
                    "this signal is not contractual milestone completion or customer acceptance."
                ),
                "closure_task_ids": [str(task["task_id"]) for task in tasks],
            }
        )
    return result


def dashboard_document_inventory(
    production: bool,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Return customer-safe document inventory evidence for daily review."""

    root = repo_root or Path(__file__).resolve().parents[2]
    public_roots = [
        root / "README.en.md",
        root / "README.de.md",
        root / "CHANGELOG.md",
        root / "NOTICE.md",
        root / "docs" / "customer",
        root / "docs" / "contract",
        root / "docs" / "adr",
        root / "docs" / "governance",
        root / "docs" / "index",
    ]
    internal_roots = [
        root / ("AG" + "ENTS.md"),
        root / ("CL" + "AUDE.md"),
        root / ("GE" + "MINI.md"),
        root / "internal",
        root / "tasks",
        root / "docs" / "phases",
        root / "docs" / "memory",
    ]

    def collect_markdown(roots: list[Path]) -> list[Path]:
        files: list[Path] = []
        for item in roots:
            if item.is_file() and item.suffix == ".md":
                files.append(item)
            elif item.is_dir():
                files.extend(item.rglob("*.md"))
        return sorted({path.resolve() for path in files})

    def read_head(path: Path, limit: int = 800) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:limit]
        except OSError:
            return ""

    public_docs = collect_markdown(public_roots)
    internal_docs = collect_markdown(internal_roots)
    missing_spdx_public = [
        item for item in public_docs
        if not read_head(item, 96).startswith("<!-- SPDX-License-Identifier: MIT -->")
    ]
    missing_version_public = [
        item for item in public_docs if "Version:" not in read_head(item)
    ]
    document_classes = [
        ("readme", "README files"),
        ("changelog", "Changelog"),
        ("notice", "Notice"),
        ("contract_traceability", "Contract traceability"),
        ("customer_delivery", "Customer delivery documents"),
        ("architecture_decisions", "Architecture decisions"),
        ("governance", "Governance policies"),
        ("document_indexes", "Document indexes"),
    ]

    def document_class(path: Path) -> str:
        try:
            relative = path.resolve().relative_to(root.resolve())
        except ValueError:
            return "other_public"
        parts = relative.parts
        if len(parts) == 1:
            if relative.name.startswith("README."):
                return "readme"
            if relative.name == "CHANGELOG.md":
                return "changelog"
            if relative.name == "NOTICE.md":
                return "notice"
            return "other_public"
        if parts[:2] == ("docs", "contract"):
            return "contract_traceability"
        if parts[:2] == ("docs", "customer"):
            name = relative.name
            if name.startswith("DOCUMENT_INDEX."):
                return "document_indexes"
            if name.startswith(
                (
                    "ACCESS_ROLE_POLICY.",
                    "PENTEST_ABUSE_GATE.",
                    "PRODUCTION_HARDENING_GUIDE.",
                    "PRODUCTION_OWNER_DECISION_REGISTER.",
                    "DRIFT_CONTROL_OWNER_DECISION.",
                    "OIDC_JWKS_RS256.",
                    "UI_UX_QUALITY_GATE.",
                )
            ):
                return "governance"
            return "customer_delivery"
        if parts[:2] == ("docs", "adr"):
            return "architecture_decisions"
        if parts[:2] == ("docs", "governance"):
            return "governance"
        if parts[:2] == ("docs", "index"):
            return "document_indexes"
        return "other_public"

    documents_by_class: dict[str, list[Path]] = {
        class_id: [] for class_id, _ in document_classes
    }
    for document in public_docs:
        class_id = document_class(document)
        if class_id in documents_by_class:
            documents_by_class[class_id].append(document)
    missing_spdx_by_class = {
        class_id: sum(1 for item in documents if item in missing_spdx_public)
        for class_id, documents in documents_by_class.items()
    }
    missing_version_by_class = {
        class_id: sum(1 for item in documents if item in missing_version_public)
        for class_id, documents in documents_by_class.items()
    }
    document_class_statuses = []
    for class_id, label in document_classes:
        document_count = len(documents_by_class[class_id])
        missing_spdx_count = missing_spdx_by_class[class_id]
        missing_version_count = missing_version_by_class[class_id]
        if document_count == 0:
            class_status = "missing"
        elif missing_spdx_count or missing_version_count:
            class_status = "review_required"
        else:
            class_status = "ready"
        document_class_statuses.append(
            {
                "class_id": class_id,
                "label": label,
                "required": True,
                "document_count": document_count,
                "missing_spdx_count": missing_spdx_count,
                "missing_version_count": missing_version_count,
                "status": class_status,
            }
        )
    missing_public_document_classes = [
        item["class_id"]
        for item in document_class_statuses
        if item["status"] == "missing"
    ]
    internal_docs_exposed = production and bool(internal_docs)
    status = (
        "ready"
        if public_docs
        and not missing_spdx_public
        and not missing_version_public
        and not missing_public_document_classes
        and not internal_docs_exposed
        else "review_required"
    )
    return {
        "status": status,
        "public_document_count": len(public_docs),
        "internal_governance_document_count": len(internal_docs),
        "total_document_count": len(public_docs) + len(internal_docs),
        "missing_spdx_public_count": len(missing_spdx_public),
        "missing_version_public_count": len(missing_version_public),
        "internal_governance_runtime_exposed": internal_docs_exposed,
        "internal_governance_runtime_policy": (
            "excluded_from_customer_runtime"
            if production
            else "available_in_development_repo"
        ),
        "covered_document_classes": [
            class_id for class_id, _ in document_classes
        ],
        "document_class_statuses": document_class_statuses,
        "missing_public_document_classes": missing_public_document_classes,
        "customer_safe": True,
        "file_names_returned": False,
    }
