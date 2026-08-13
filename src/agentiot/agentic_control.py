# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.13 | Date: 2026-08-13

"""Agent-owned operations control plane for GreeNovaX.

Adapts the 8088 operator-control pattern (radar, issues, auto-guard, cluster,
task resume, notifications) to this product. Agents execute bounded product
actions. Host Wi-Fi, systemd, Docker, and remote deploy are not copied.
production_claim: false.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from .version import __version__


CUSTOMER_NAME = "GreeNovaX"
CONTRACTOR_NAME = "IoT-AI.Tech"
CONTROL_SCHEMA = "agentiot.agentic-control.v1"
CLUSTER_PEERS_ENV = "AGENTIOT_CLUSTER_PEERS"
STATE_KEY = "default"
MAX_PEER_PROBE_SECONDS = 2.0

CONTROL_ACTIONS: tuple[dict[str, str], ...] = (
    {
        "action": "service.self_check",
        "label": "Service self-check",
        "owner_agent_id": "operations_coordinator",
        "hitl": "false",
        "effect": "Recheck fixed product HTTP services and store health.",
    },
    {
        "action": "service.solve",
        "label": "Solve service issues",
        "owner_agent_id": "operations_coordinator",
        "hitl": "true",
        "effect": "Recheck services and prepare HITL recovery proposals.",
    },
    {
        "action": "mqtt.refresh",
        "label": "Refresh MQTT adapter",
        "owner_agent_id": "device_fleet_agent",
        "hitl": "false",
        "effect": "Read live MQTT subscriber evidence.",
    },
    {
        "action": "cmdb.refresh",
        "label": "Refresh CMDB",
        "owner_agent_id": "device_fleet_agent",
        "hitl": "false",
        "effect": "Rebuild derived inventory from current registries.",
    },
    {
        "action": "discovery.status",
        "label": "Review discovery queue",
        "owner_agent_id": "device_fleet_agent",
        "hitl": "false",
        "effect": "List queued hardware/network discovery candidates.",
    },
    {
        "action": "recovery.review",
        "label": "Review recovery queue",
        "owner_agent_id": "operations_coordinator",
        "hitl": "true",
        "effect": "List pending recovery proposals for human approval.",
    },
    {
        "action": "node.probe",
        "label": "Probe cluster nodes",
        "owner_agent_id": "operations_coordinator",
        "hitl": "false",
        "effect": "Probe configured GreeNovaX peer health/version endpoints.",
    },
    {
        "action": "auto_guard.cycle",
        "label": "Auto-guard cycle",
        "owner_agent_id": "operations_coordinator",
        "hitl": "true",
        "effect": "Detect issues, run safe remediations, keep HITL for execution.",
    },
    {
        "action": "autopilot.mission",
        "label": "Agent autopilot",
        "owner_agent_id": "admin_governance_agent",
        "hitl": "true",
        "effect": "Activate section agents once with A2A evidence.",
    },
)

MqttStatusFn = Callable[[], Mapping[str, Any]]
HttpCheckFn = Callable[[str], Mapping[str, Any]]
CmdbFn = Callable[[], Mapping[str, Any]]
AutopilotFn = Callable[[str], Mapping[str, Any]]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def cluster_peer_urls() -> list[str]:
    raw = os.getenv(CLUSTER_PEERS_ENV, "").strip()
    urls: list[str] = []
    for item in raw.split(","):
        candidate = item.strip().rstrip("/")
        if not candidate:
            continue
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        if parsed.hostname in {None, "", "0.0.0.0"}:
            continue
        urls.append(candidate)
    return urls[:8]


def probe_peer_node(base_url: str) -> dict[str, Any]:
    """Probe one GreeNovaX peer using public health/version only."""

    parsed = urlparse(base_url)
    result: dict[str, Any] = {
        "node_id": parsed.netloc.replace(":", "-"),
        "base_url": base_url,
        "online": False,
        "version": None,
        "service": None,
        "latency_ms": None,
        "error": None,
    }
    context = ssl._create_unverified_context() if parsed.scheme == "https" else None
    started = datetime.now(UTC)
    try:
        request = urllib.request.Request(
            base_url + "/healthz",
            headers={"Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(
            request, timeout=MAX_PEER_PROBE_SECONDS, context=context
        ) as response:
            body = json.loads(response.read().decode("utf-8")[:2000])
        result["latency_ms"] = max(
            0, int((datetime.now(UTC) - started).total_seconds() * 1000)
        )
        if str(body.get("status") or "") in {"ok", "ready"}:
            result["online"] = True
            result["service"] = body.get("service")
            result["version"] = body.get("version")
        else:
            result["error"] = "unexpected_health_payload"
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError, ValueError) as error:
        result["error"] = type(error).__name__
        result["latency_ms"] = max(
            0, int((datetime.now(UTC) - started).total_seconds() * 1000)
        )
    return result


def default_task_state() -> dict[str, Any]:
    return {
        "objective": "Keep GreeNovaX agent-controlled operations live.",
        "last_instruction": "Review radar, close open issues, keep MQTT and inventory current.",
        "plan": [
            "Self-check product services",
            "Refresh MQTT and CMDB evidence",
            "Prepare HITL recovery for unresolved issues",
            "Probe configured peer nodes",
        ],
        "last_checkpoint": None,
        "resume_hint": "Run auto_guard.cycle if the last checkpoint is older than the guard interval.",
        "updated_at": None,
        "updated_by": "system",
    }


def load_control_state(store: Any) -> dict[str, Any]:
    getter = getattr(store, "get_agentic_control_state", None)
    if callable(getter):
        state = getter() or {}
        if isinstance(state, dict) and state:
            return state
    return {
        "auto_guard_enabled": True,
        "auto_guard_interval_seconds": 60,
        "controller_mode": True,
        "last_auto_guard": None,
        "task_state": default_task_state(),
        "updated_at": None,
    }


def save_control_state(store: Any, state: dict[str, Any], *, actor: str) -> dict[str, Any]:
    state = dict(state)
    state["updated_at"] = utc_now()
    state["updated_by"] = actor
    saver = getattr(store, "put_agentic_control_state", None)
    if callable(saver):
        saver(state, actor=actor)
    return state


def _count_alerts(store: Any) -> int:
    try:
        items = store.list_rows("alerts")
    except Exception:
        return 0
    return sum(1 for item in items if str(item.get("status") or "") in {"open", "active", "new"})


def _pending_recovery(store: Any) -> list[dict[str, Any]]:
    try:
        items = store.list_rows("recovery_proposals")
    except Exception:
        return []
    return [
        item
        for item in items
        if str(item.get("status") or "") in {"pending", "proposed", "awaiting_approval"}
    ]


def _discovery_queue(store: Any) -> list[dict[str, Any]]:
    lister = getattr(store, "list_network_discovery_candidates", None)
    if not callable(lister):
        return []
    return [item for item in lister() if str(item.get("status") or "") == "queued"]


def _agent_counts(store: Any) -> dict[str, int]:
    lister = getattr(store, "list_dashboard_agents", None)
    agents = lister() if callable(lister) else []
    return {
        "registered": len(agents),
        "enabled": sum(1 for agent in agents if agent.get("enabled")),
    }


def _service_inventory(store: Any) -> dict[str, Any]:
    from .service_operations import public_service_inventory

    lister = getattr(store, "list_http_service_health", None)
    rows = lister() if callable(lister) else []
    return public_service_inventory(rows)


def collect_issues(
    *,
    services: Mapping[str, Any],
    mqtt_status: Mapping[str, Any],
    pending_recovery: list[Mapping[str, Any]],
    discovery_queue: list[Mapping[str, Any]],
    open_alerts: int,
    nodes: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for item in services.get("items") or []:
        if item.get("status") in {"degraded", "down"}:
            issues.append(
                {
                    "id": f"svc-{item['service_id']}",
                    "severity": "high" if item.get("status") == "down" else "medium",
                    "source": "service",
                    "title": f"{item['name']} is {item['status']}",
                    "owner_agent_id": item.get("owner_agent_id"),
                    "action": "service.solve",
                    "detail": item.get("issue_code") or item.get("status"),
                }
            )
    if mqtt_status and not mqtt_status.get("connected"):
        issues.append(
            {
                "id": "mqtt-disconnected",
                "severity": "high" if mqtt_status.get("configured") else "medium",
                "source": "mqtt",
                "title": "MQTT subscriber is not connected",
                "owner_agent_id": "device_fleet_agent",
                "action": "mqtt.refresh",
                "detail": mqtt_status.get("status") or "not_configured",
            }
        )
    if open_alerts:
        issues.append(
            {
                "id": "open-alerts",
                "severity": "high" if open_alerts >= 3 else "medium",
                "source": "alarms",
                "title": f"{open_alerts} open operational alarm(s)",
                "owner_agent_id": "operations_coordinator",
                "action": "recovery.review",
                "detail": "Review alarms and recovery proposals.",
            }
        )
    if pending_recovery:
        issues.append(
            {
                "id": "pending-recovery",
                "severity": "medium",
                "source": "recovery",
                "title": f"{len(pending_recovery)} recovery proposal(s) wait for approval",
                "owner_agent_id": "operations_coordinator",
                "action": "recovery.review",
                "detail": "HITL required before execution.",
            }
        )
    if discovery_queue:
        issues.append(
            {
                "id": "discovery-queue",
                "severity": "low",
                "source": "discovery",
                "title": f"{len(discovery_queue)} discovery candidate(s) queued",
                "owner_agent_id": "device_fleet_agent",
                "action": "discovery.status",
                "detail": "Approve validated candidates into inventory.",
            }
        )
    for node in nodes:
        if node.get("role") == "peer" and not node.get("online"):
            issues.append(
                {
                    "id": f"node-{node.get('node_id')}",
                    "severity": "medium",
                    "source": "cluster",
                    "title": f"Peer node {node.get('node_id')} is offline",
                    "owner_agent_id": "operations_coordinator",
                    "action": "node.probe",
                    "detail": node.get("error") or "offline",
                }
            )
    return issues


def collect_notifications(issues: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    notices = []
    for item in issues[:12]:
        notices.append(
            {
                "severity": item.get("severity"),
                "source": item.get("source"),
                "title": item.get("title"),
                "detail": item.get("detail"),
                "ts": utc_now(),
            }
        )
    return notices


def local_node(version: str) -> dict[str, Any]:
    host = os.getenv("AGENTIOT_PUBLIC_ACCESS_URL", "local").strip() or "local"
    return {
        "node_id": "local",
        "role": "local",
        "base_url": host,
        "online": True,
        "version": version,
        "service": "agentiot-dashboard",
        "latency_ms": 0,
        "error": None,
    }


def build_cluster(version: str) -> dict[str, Any]:
    nodes = [local_node(version)]
    for url in cluster_peer_urls():
        nodes.append({**probe_peer_node(url), "role": "peer"})
    online = sum(1 for node in nodes if node.get("online"))
    return {
        "generated_at": utc_now(),
        "nodes": nodes,
        "summary": {
            "total_nodes": len(nodes),
            "online_nodes": online,
            "offline_nodes": len(nodes) - online,
            "peer_urls_configured": len(cluster_peer_urls()),
        },
    }


def build_control_dashboard(
    store: Any,
    *,
    mqtt_status: Mapping[str, Any] | None = None,
    cmdb: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = load_control_state(store)
    services = _service_inventory(store)
    mqtt = dict(mqtt_status or {})
    cmdb_summary = (cmdb or {}).get("summary") or {}
    pending = _pending_recovery(store)
    queued = _discovery_queue(store)
    open_alerts = _count_alerts(store)
    agents = _agent_counts(store)
    cluster = build_cluster(__version__)
    issues = collect_issues(
        services=services,
        mqtt_status=mqtt,
        pending_recovery=pending,
        discovery_queue=queued,
        open_alerts=open_alerts,
        nodes=cluster["nodes"],
    )
    radar = {
        "runtime": "ok",
        "mqtt": mqtt.get("status") or "unknown",
        "mqtt_connected": bool(mqtt.get("connected")),
        "services_healthy": services["summary"]["healthy"],
        "services_total": services["summary"]["total"],
        "open_alerts": open_alerts,
        "pending_recovery": len(pending),
        "discovery_queued": len(queued),
        "cmdb_records": int(cmdb_summary.get("ci_count") or 0),
        "agents_enabled": agents["enabled"],
        "cluster_online": cluster["summary"]["online_nodes"],
        "cluster_total": cluster["summary"]["total_nodes"],
        "open_issues": len(issues),
    }
    return {
        "schema_version": CONTROL_SCHEMA,
        "generated_at": utc_now(),
        "version": __version__,
        "prepared_for": CUSTOMER_NAME,
        "prepared_by": CONTRACTOR_NAME,
        "controller_mode": bool(state.get("controller_mode", True)),
        "production_claim": False,
        "summary": {
            **services["summary"],
            "open_issues": len(issues),
            "open_alerts": open_alerts,
            "pending_recovery": len(pending),
            "discovery_queued": len(queued),
            "mqtt_status": mqtt.get("status"),
            "auto_guard_enabled": bool(state.get("auto_guard_enabled", True)),
            "auto_guard_last_run": (state.get("last_auto_guard") or {}).get("generated_at"),
            "cluster_online_nodes": cluster["summary"]["online_nodes"],
            "cluster_total_nodes": cluster["summary"]["total_nodes"],
        },
        "radar": radar,
        "notifications": collect_notifications(issues),
        "issues": issues,
        "services": services,
        "cluster": cluster,
        "agents": agents,
        "mqtt": {
            "status": mqtt.get("status"),
            "connected": bool(mqtt.get("connected")),
            "configured": bool(mqtt.get("configured")),
            "messages_accepted": mqtt.get("messages_accepted") or 0,
            "messages_rejected": mqtt.get("messages_rejected") or 0,
            "field_ready": bool(mqtt.get("field_ready")),
        },
        "cmdb": cmdb_summary,
        "auto_guard": {
            "enabled": bool(state.get("auto_guard_enabled", True)),
            "interval_seconds": int(state.get("auto_guard_interval_seconds") or 60),
            "last_run": state.get("last_auto_guard"),
        },
        "task_state": state.get("task_state") or default_task_state(),
        "actions": list(CONTROL_ACTIONS),
        "policy": {
            "host_commands_allowed": False,
            "wifi_control_copied": False,
            "deploy_copied": False,
            "agent_owned": True,
            "hitl_for_execution": True,
        },
    }


def _safe_http_check(store: Any, actor: str, http_check: HttpCheckFn | None) -> dict[str, Any]:
    if callable(http_check):
        return dict(http_check(actor))
    return {"status": "skipped", "reason": "probe_unavailable"}


def run_control_action(
    store: Any,
    action: str,
    *,
    actor: str,
    mqtt_status: Mapping[str, Any] | None = None,
    http_check: HttpCheckFn | None = None,
    cmdb_builder: CmdbFn | None = None,
    autopilot: AutopilotFn | None = None,
) -> dict[str, Any]:
    """Execute one bounded agent control action."""

    known = {item["action"]: item for item in CONTROL_ACTIONS}
    spec = known.get(action)
    if spec is None:
        return {
            "status": "rejected",
            "action": action,
            "detail": "Unknown control action",
            "commands_executed": 0,
        }
    result: dict[str, Any] = {
        "status": "ok",
        "action": action,
        "owner_agent_id": spec["owner_agent_id"],
        "hitl": spec["hitl"] == "true",
        "commands_executed": 0,
        "generated_at": utc_now(),
    }
    if action == "service.self_check":
        checked = _safe_http_check(store, actor, http_check)
        result["detail"] = checked
        result["commands_executed"] = 1 if checked.get("status") != "skipped" else 0
    elif action == "service.solve":
        checked = _safe_http_check(store, actor, http_check)
        unresolved = [
            item
            for item in checked.get("items") or []
            if item.get("status") not in {"healthy", "not_checked"}
        ]
        result["detail"] = {
            "unresolved": len(unresolved),
            "proposals_prepared": 0,
            "next": "HITL recovery remains on /api/services/http/solve-issues",
        }
        result["commands_executed"] = 1
    elif action == "mqtt.refresh":
        result["detail"] = {
            "status": (mqtt_status or {}).get("status"),
            "connected": bool((mqtt_status or {}).get("connected")),
            "configured": bool((mqtt_status or {}).get("configured")),
        }
    elif action == "cmdb.refresh":
        snapshot = cmdb_builder() if callable(cmdb_builder) else {}
        result["detail"] = snapshot.get("summary") or {"ci_count": 0}
    elif action == "discovery.status":
        queued = _discovery_queue(store)
        result["detail"] = {"queued": len(queued)}
    elif action == "recovery.review":
        pending = _pending_recovery(store)
        result["detail"] = {"pending": len(pending)}
    elif action == "node.probe":
        result["detail"] = build_cluster(__version__)["summary"]
    elif action == "auto_guard.cycle":
        result = run_auto_guard(
            store,
            actor=actor,
            mqtt_status=mqtt_status,
            http_check=http_check,
            cmdb_builder=cmdb_builder,
        )
    elif action == "autopilot.mission":
        if not callable(autopilot):
            result["status"] = "skipped"
            result["detail"] = {"reason": "autopilot_unavailable"}
        else:
            result["detail"] = dict(autopilot(actor))
            result["commands_executed"] = 1
    audit = getattr(store, "add_audit_event", None)
    if callable(audit):
        audit(
            event_type=f"agentic.control.{action}",
            subject_id=action,
            actor=actor,
            detail=json.dumps(
                {
                    "status": result.get("status"),
                    "commands_executed": result.get("commands_executed"),
                    "hitl": result.get("hitl"),
                },
                separators=(",", ":"),
            ),
        )
    return result


def run_auto_guard(
    store: Any,
    *,
    actor: str,
    mqtt_status: Mapping[str, Any] | None = None,
    http_check: HttpCheckFn | None = None,
    cmdb_builder: CmdbFn | None = None,
) -> dict[str, Any]:
    """Run one agent-owned auto-guard cycle without host commands."""

    checked = _safe_http_check(store, actor, http_check)
    cmdb = cmdb_builder() if callable(cmdb_builder) else {}
    dashboard = build_control_dashboard(
        store, mqtt_status=mqtt_status, cmdb=cmdb
    )
    actions: list[dict[str, Any]] = []
    if checked.get("status") != "skipped":
        actions.append(
            {
                "type": "service.self_check",
                "ok": True,
                "output": f"checked {dashboard['services']['summary']['total']} services",
            }
        )
    unresolved = [
        item
        for item in (checked.get("items") or dashboard["services"]["items"])
        if item.get("status") in {"degraded", "down"}
    ]
    if unresolved:
        actions.append(
            {
                "type": "service.solve",
                "ok": True,
                "output": f"{len(unresolved)} service issue(s) remain for HITL solve",
            }
        )
    mqtt = dashboard["mqtt"]
    if mqtt.get("configured") and not mqtt.get("connected"):
        actions.append(
            {
                "type": "mqtt.refresh",
                "ok": False,
                "output": "subscriber configured but not connected",
            }
        )
    state = load_control_state(store)
    cycle = {
        "status": "completed",
        "action": "auto_guard.cycle",
        "owner_agent_id": "operations_coordinator",
        "hitl": True,
        "generated_at": utc_now(),
        "commands_executed": len(actions),
        "open_issues": len(dashboard["issues"]),
        "actions": actions,
        "detail": {
            "services": dashboard["services"]["summary"],
            "mqtt": mqtt.get("status"),
            "cluster": dashboard["cluster"]["summary"],
        },
    }
    state["last_auto_guard"] = cycle
    task = dict(state.get("task_state") or default_task_state())
    task["last_checkpoint"] = cycle["generated_at"]
    task["resume_hint"] = (
        "Open issues remain; rerun auto_guard.cycle after HITL approvals."
        if dashboard["issues"]
        else "No open control issues; keep the next guard interval."
    )
    task["updated_at"] = cycle["generated_at"]
    task["updated_by"] = actor
    state["task_state"] = task
    save_control_state(store, state, actor=actor)
    return cycle


def update_task_state(
    store: Any,
    patch: Mapping[str, Any],
    *,
    actor: str,
) -> dict[str, Any]:
    state = load_control_state(store)
    task = dict(state.get("task_state") or default_task_state())
    for key in ("objective", "last_instruction", "resume_hint"):
        if patch.get(key):
            task[key] = str(patch[key])[:400]
    if isinstance(patch.get("plan"), list):
        task["plan"] = [str(item)[:160] for item in patch["plan"][:8]]
    task["updated_at"] = utc_now()
    task["updated_by"] = actor
    state["task_state"] = task
    save_control_state(store, state, actor=actor)
    return task


def action_from_goal(goal: str) -> str | None:
    """Map a free-text agent goal onto a typed control action when obvious."""

    text = str(goal or "").strip().lower()
    # Existing section-agent autopilot missions must not re-enter control.
    if text.startswith("autopilot mission"):
        return None
    if text.startswith("control:"):
        candidate = text.split(":", 1)[1].strip().split()[0].replace(" ", ".")
        if any(item["action"] == candidate for item in CONTROL_ACTIONS):
            return candidate
    mapping = (
        ("auto-guard", "auto_guard.cycle"),
        ("auto guard", "auto_guard.cycle"),
        ("self-check", "service.self_check"),
        ("self check", "service.self_check"),
        ("solve issue", "service.solve"),
        ("mqtt", "mqtt.refresh"),
        ("cmdb", "cmdb.refresh"),
        ("discover", "discovery.status"),
        ("recovery", "recovery.review"),
        ("cluster", "node.probe"),
        ("peer", "node.probe"),
        ("run autopilot", "autopilot.mission"),
        ("agent autopilot", "autopilot.mission"),
    )
    for needle, action in mapping:
        if needle in text:
            return action
    return None
