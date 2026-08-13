<!-- SPDX-License-Identifier: MIT -->
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.157.20
# Date: 2026-08-13
# Language: English
# License: MIT

# Changelog

All notable changes follow Keep a Changelog and semantic versioning.

## [Unreleased]

### Added
- Binding GitHub publication order for every coder: no contracts,
  internal architecture, session data, fleet addresses, or secrets in
  any commit that can leave the private host. Guide:
  `docs/github/CODER_GUIDE.md`. Exporter and fail-closed scanner are
  the only approved publication path.
- Public product page from the GreeNovaX LinkedIn announcements, plus
  official GreeNovaX and IoT-AI.Tech company logos in `docs/brand/`.
- `tools/check_commit.sh` so every public commit is scanned and tested.

## [0.157.20] - 2026-08-13

### Changed
- Assistant rail keeps the evidence diagnosis visible and explains a
  missing live model in operator language. Cockpit heading shows
  architecture and version together.

## [0.157.19] - 2026-08-13

### Changed
- Local assistant preference moves off Qwen to stronger private 11500
  chat models: `gpt-oss:20b`, then `gemma2:9b`. Tiny 0.5b and embed
  tags are no longer selected.

## [0.157.18] - 2026-08-13

### Added
- Operator assistant answers use a fixed Finding / Evidence / Agents /
  Next review / Approval format after internal agent + RAG preparation.

### Changed
- Default assistant instruction and AI-governance RAG describe that
  workflow so the chatbot stays read-only and evidence-first.

## [0.157.17] - 2026-08-13

### Added
- Assistant rail shows the live diagnosis and a per-agent activity list
  for the current turn.
- `GET /api/chat` includes `activity` so operators can see what each
  agent did, not only a status chip.

### Changed
- The cockpit Assistant no longer replaces a live model answer with a
  status-only summary.

## [0.157.16] - 2026-08-13

### Added
- Settings now load the live private 11500 model catalog and can
  activate the local assistant route in one operator action.

### Changed
- Default local model preference is `qwen3.5:latest` at a private
  operator-configured Ollama-compatible origin.
- Assistant runtime instruction requires cited grounding identifiers.

### Fixed
- Provider acceptance no longer rejects answers that only mention
  forbidden actions in prohibition form ("do not approve or execute").

## [0.157.15] - 2026-08-13

### Added
- Series-B firmware catalog now treats Radxa ROCK Pi 4B+ as a physically
  validated ARM64 board. Raspberry Pi 4/5 stay validation-required.

### Changed
- Greenhouse temperature profile accepts the Radxa Series-B board.

## [0.157.14] - 2026-08-13

### Fixed
- Cockpit "Sign-in required" now has a visible Sign In control and
  banner that open `/login`.
- After bootstrap login, password rotation opens
  `/login/change-password` instead of a hidden Settings panel.

## [0.157.13] - 2026-08-13

### Added
- Cockpit footer and heading show a live x86/ARM sign next to the
  product version plus a hardware-technology label from host identity.
- `/api/version` reports architecture, machine, board, and CPU model
  without serials, host names, or addresses.
- Settings readiness ledger and assistant blocked-state text with an
  admin connectivity recheck action.

### Changed
- Assistant no longer presents `grounded_fallback` as a working model
  answer. Control radar remains on the Control tab and is summarized on
  the cockpit summary strip.
- HTML version comment is bound to the same release as `VERSION`.

### Security
- Host identity is customer-safe. 8088 host-admin actions remain out of
  product scope.

## [0.157.12] - 2026-08-13

### Added
- Agent-owned operations control plane adapted from the 8088 operator
  pattern: radar, notifications, issues, auto-guard, cluster peer probe,
  and crash-resume task state.
- Typed control actions that agents execute through `/api/control/*` and
  `/api/agents/tasks` (`CONTROL:<action>` goals).
- Operations Control tab with live radar, issue-owned actions, and the
  full agent action catalog.

### Changed
- Agent tasks now run a mapped product control action instead of writing
  narrative-only answers for operations goals.

### Security
- Host Wi-Fi, systemd, Docker, and remote deploy commands from the 8088
  sample controller are not copied. Execution remains HITL.

## [0.157.11] - 2026-08-13

### Added
- MQTT 5 subscriber now advertises OASIS MQTT 5.0, Sparkplug B DDATA, and
  Homie 4.0 property conventions and accepts those topic/payload envelopes.
- Discovery-approved hosts that expose MQTT/MQTTS port hints can ingest
  telemetry without a second adapter rewrite.
- Sensor inventory now shows derived configuration-item relations.
- August 2026 Phase 1 monthly consolidation report (M1.7).

### Changed
- Broker status reports protocol version, topic filters, last message time,
  and an explicit lab `field_ready=false` unless TLS-verified field evidence
  exists.

## [0.157.10] - 2026-08-13

### Changed
- Aligned selected-period telemetry, active alarms, and recovery counts with
  the canonical operations summary while keeping active work visible outside
  the chart window.
- Moved live platform telemetry ahead of the collapsible HTTP(S) service
  inventory and made runtime issue guidance consume the backend evidence.
- Renamed projected audit and agent quality metrics so the interface no longer
  presents bounded or configuration-derived values as totals or maturity.

### Fixed
- Replaced a stale recovery-proposal variable that interrupted all live
  dashboard refreshes with the canonical pending-proposal collection.
- Made visual QA preserve failure evidence without treating a missing
  screenshot as a report-generation crash.
- Kept operator actions disabled after session expiry and exposed truthful
  footer states for partial, degraded, and authentication-required runtime data.
- Corrected uptime, disk, and network field mappings in platform observability.
- Extended authenticated visual QA with cross-surface count, footer-state,
  accessibility, and expired-session behavior checks.

### Security
- Server-redacted detailed audit fields for viewer identities while preserving
  operator and administrator investigation access.
- Isolated the protocol lab from external egress and narrowed Docker context
  exceptions to approved screenshots and the exact visual report.
- Required tablet coverage plus independent screenshot digest and byte-count
  verification before customer release packaging.

## [0.157.6] - 2026-08-12

### Added
- Added a truthful Linux onboard thermal profile for CMDB registration of
  measured edge-node temperature evidence, including Radxa ROCK Pi 4B+.

### Fixed
- Limited CMDB protocol and hardware claims to the evidence actually supplied
  by the approved discovery record.
- Preserved an existing asset's location while attaching approved hardware
  profile evidence.
- Bound the thermal collector to the checkout commit, runtime digest, and
  resolved immutable container image ID.

### Security
- Replaced the shared edge-ingestion credential with unique per-device secrets.
- Added timestamp bounds, idempotent sample identifiers, replay-conflict
  rejection, a shared authentication-rate bucket, and redirect-safe collection.

## [0.157.5] - 2026-08-11

### Added
- Added a resource-bounded edge thermal collector that forwards real Linux
  thermal-zone measurements through a device-bound, write-only telemetry API.
- Added a dedicated edge-ingestion credential so collectors never receive the
  broader dashboard operator token.

### Fixed
- Reported fresh connected telemetry as actively monitored when no alert is open,
  instead of incorrectly claiming that telemetry is unavailable.
- Classified device telemetry as fresh, stale, offline, or never seen from its
  configured cadence and exposed sample time and state in Operations.

## [0.157.4] - 2026-08-11

### Changed
- Replaced the public reports endpoint's admin evidence-graph build with a
  bounded operational projection for low-resource ARM deployments.
- Retained the complete report and evidence graph for authorized admin views.

## [0.157.3] - 2026-08-11

### Fixed
- Preserved the visible operational workbench while routing Assets, Alarms, and
  Workflows to their own context-specific command surfaces.

## [0.157.2] - 2026-08-11

### Fixed
- Kept asset discovery and CMDB approval controls inside the Assets workspace
  so Alarms, Workflows, Overview, and Operations show only their own controls.
- Replaced discovery loading placeholders with an actionable empty-queue state.

## [0.157.1] - 2026-08-11

### Added
- Added bounded private-network endpoint discovery, revision-bound human approval,
  protocol/type-filtered CMDB topology, and Pi-safe data retention and database ceilings.

### Changed
- Coalesced repeated open anomaly events and bounded active anomaly, history, and
  continuous-audit growth for constrained edge deployments.
- Made REST and MQTT telemetry, anomaly, recovery, and audit receipts atomic.
- Added a database-backed scan lease so concurrent workers cannot start overlapping
  network discovery runs.

### Security
- Revalidates the deployment allowlist at approval, shares scan cooldown through
  SQLite, and records one sanitized terminal receipt for every authorized attempt.
- Preserves terminal and protected audit evidence with class-based rotation and
  includes the MIT license in the customer runtime image.

## [0.157.0] - 2026-08-09

### Added
- Added a separately signed, short-lived off-host liveness proof that binds the
  tenant, deployment, receipt, NAS namespace, provider object version, and
  retention evidence.
- Added a host verifier that reopens the canonical remote object and validates
  an independently signed provider object-lock attestation before refreshing
  the runtime proof.

### Security
- Replaced shared-secret restore receipts with dedicated Ed25519 receipt and
  liveness trust domains, durable nonce replay protection, exact schema checks,
  and pinned no-follow file reads.
- Added owner-bound storage profiles, source SQLite identity/WAL checks, exact
  backup-object validation, and a monotonic restore-evidence image epoch.
- Disabled autonomous restart until a fresh liveness proof can be obtained for
  every process start; generic CIFS/NFS storage remains fail-closed without
  provider-verifiable retention evidence.

## [0.156.2] - 2026-08-09

### Changed
- Kept primary navigation visible on responsive deep routes and added a usable
  mobile overflow control with active-route positioning.
- Reflowed HTTP service inventory below wide desktop, expanded provider status
  to the full administration width, and aligned the safe-recheck checkbox.
- Replaced the long empty-runtime assistant response with a concise,
  action-oriented setup state.

### Quality
- Extended authenticated visual QA to reject hidden route navigation, clipped
  service/provider surfaces, detached checkboxes, hidden active tabs, and
  oversized empty-runtime assistant messages.

## [0.156.1] - 2026-08-09

### Changed
- Replaced hard-coded phase completion percentages with task-derived technical
  readiness, explicit open-task counts, and a fail-closed contract status.
- Kept the contractual phase at Phase 1 after commercial-baseline review;
  workshop, procurement, physical hardware, and handover evidence remain
  separate acceptance inputs.
- Raised primary green and amber interface tokens to WCAG AA contrast levels.
- Rebound the July MQTT/REST lab, authenticated 92-route/viewport visual gate,
  and isolated off-host restore drill to the current release identity.

### Security
- Removed percentage-based acceptance implications from management, QC, and
  owner-decision responses; customer acceptance is never inferred from runtime
  controls.
- Kept physical Raspberry Pi/ARM validation and customer-environment restore
  acceptance fail-closed despite successful isolated x86_64 QA evidence.

## [0.156.0] - 2026-07-29

### Added
- Added local dashboard accounts with role-based access, self-service password
  changes, administrator password reset, and session revocation.
- Added a dedicated browser sign-in page and separate Administration routes for
  access, services, model providers, routing, and quality controls.

### Changed
- Browser administration now uses a signed HttpOnly same-site session cookie;
  machine admin tokens remain available only for API automation.
- Removed the nested Settings scroll surface and present one focused settings
  section per route.

### Security
- Passwords use per-user salted scrypt hashes; temporary credentials are
  restricted to password rotation, and login limits are atomic across workers
  with bounded shared storage and expiry.
- Account mutations are audited atomically, and the final enabled administrator
  cannot be disabled or deleted.

## [0.155.1] - 2026-07-22

### Changed
- Authenticated local-model routes now require HTTPS and an approved private IP
  literal; credential-free local Ollama routes remain available over private
  HTTP for the configured lab endpoints.
- Protected HTTP service checks now use bounded operator authentication and no
  longer report an unauthenticated `401` or `403` response as healthy.
- Production readiness now requires a signed off-host restore receipt bound to
  the tenant, source commit, runtime digest, and running release version.
- Restored the authenticated prompt-registry list response and added direct
  regression coverage for its full-detail admin view.

### Security
- Isolated the mounted restore receipt from backup payloads, rejected
  world-writable or mixed-content receipt directories, and made receipt
  permission publication atomic.
- Prevented cleartext and DNS-rebinding credential egress from the local-model
  gateway while preserving exact-origin credential scoping.

## [0.155.0] - 2026-07-16

### Added
- Added one tenant-bound operational-truth API for release identity, assets,
  agents, approvals, recurring controls, and backup state.
- Added independently stored SQLite backup and restore receipts for production
  release evidence.
- Added a fixed-contract Full HTTP(S) Services Table with persisted health,
  latency, access, transport, security-header, and failure evidence.
- Added operator-gated Self Check, Solve Issues, and safe Auto Heal controls,
  plus an admin-only sanitized Debug Dump and service-operations settings.
- Added primary/secondary Ollama failover, dual-endpoint inference health,
  and one auditable health matrix for every registered dashboard agent.
- Added password-based admin unlock that issues a rate-limited, short-lived
  signed session instead of using the password as a bearer credential.

### Changed
- Bound cloud model credentials to exact provider host allowlists before
  outbound authentication is constructed.
- Scoped local-model credentials to their exact configured origin so a
  credentialed primary route cannot leak authentication to failover endpoints.
- Required authenticated production access for chat, RAG, assistant SSE, and
  A2A event streams.
- Aligned recurring gap and drift reviews to the six-hour control cadence.
- Added a recurring service-operations worker that performs loopback-only
  checks and prepares approval-required proposals for persistent failures.
- Made Settings reload authenticated service, model, routing, agent-health,
  and memory controls immediately after admin sign-in.
- Allowed a validated short-lived admin session to operate scope-protected
  dashboard controls without exposing the deployment operator token.

### Security
- Applied admin-password lockout before credential comparison and protected
  detailed service, observability, and operational-truth reads in production.
- Preserved live off-host receipt rotation, trusted forwarded client identity
  only in the launcher-isolated proxy topology, and preferred fresh admin
  sessions over stale operator credentials in browser requests.
- Rejected authentication material in URL query parameters without reflecting
  values.
- Disabled application access logs and configured the HTTPS proxy to log paths
  without query strings.
- Required fresh off-host restore evidence for production backup readiness.
- Restricted service checks to an immutable application-route allowlist,
  disabled redirects, rejected arbitrary targets, and prohibited host-command
  execution from Auto Heal.
- Limited diagnostics downloads to an explicit schema without credentials,
  environment data, raw logs, request bodies, provider payloads, or local paths.
- Kept admin passwords in mounted runtime secrets, kept session tokens in
  browser memory only, and stored no LLM health prompts or answer text.
- Required authentication for production simulation-run records and suppressed
  their pre-login browser requests with the other customer-data surfaces.

## [0.152.18] - 2026-07-16

- Added live firmware drift monitoring against enabled device profiles.
- Preserved canonical operational deep links and loaded Automation actions on `/actions`.
- Replaced synthetic geography with CMDB-backed fleet topology and corrected asset status counts.
- Bound visual evidence to the baked runtime manifest digest.
- Unified persistent data volumes and made deployment rollback restore app and proxy independently.

## [0.152.17] - 2026-07-14

- Tightened mobile navigation and footer density for clearer post-visual small-screen operation.

## [0.152.16] - 2026-07-14

- Reconciled Operational Assurance, truthful firmware evidence, mobile and assistant UI safety, and public API minimization for the active development release.

### 0.152.14 - Cockpit display cleanup

- Kept the Cockpit first viewport focused on KPIs, readiness, action queue, and assistant instead of exposing workspace clutter.
- Tightened Operations wording and routing so real controls stay in the Operations workbench.
- Refreshed browser visual QA evidence for version 0.152.14.


### Changed
- Keep Intelligence, Reports, and Administration routes to one primary workspace so operators do not see stacked internal panels.
- Label the Phase 1 `95%` indicator as foundation closure readiness rather than
  a weighted contractual-milestone total, and align the English/German customer
  control documents with that boundary.

### Fixed
- Wait for either live assets or visible zero-data setup actions before visual
  QA evaluates Intelligence routes.
- Keep exactly one visible sidebar item active after in-cockpit navigation.
- Replace About-page raw service and dead documentation links with dashboard
  surfaces, and disable mutating quality-review controls until an operator
  token is supplied.

## [0.152.8] - 2026-07-10
### Changed
- Replaced fixed cockpit trend labels with selected-window comparisons computed
  from persisted operational records.
- Made the 15-minute, 1-hour, 24-hour, and today controls reload their matching
  operational summary and telemetry period.
- Kept the focused cockpit on KPIs, readiness, and the action queue; moved
  write controls to operational routes and replaced the seed workflow shortcut
  with non-mutating asset-setup navigation.
- Reduced the Audit route to filtered operational audit events and collapsed
  credential-reference diagnostics behind customer-readable settings controls.
- Aligned the Today label and browser-side telemetry filter with the API's UTC
  day boundary.

### Fixed
- Hide optional lab-simulator controls when its plugin is disabled, use real
  notification counts, and reject visible internal identifiers in visual QA.

### Security
- Bind alert resolution and recovery approval audit actors to the authenticated
  operator identity and remove the editable operator identity field from the UI.

## [0.152.7] - 2026-07-10
### Added
- Added canonical browser history for all operational sidebar workspaces and
  focused route data loading instead of refreshing every dashboard service.

### Changed
- Disabled seed records by default and moved the live launcher to an isolated,
  configurable production data volume.
- Restored the official GreeNovaX logo on the product and About surfaces.

### Fixed
- Kept protected hardware-discovery records behind operator authentication
  while retaining a customer-safe commissioning summary.
- Kept exactly one sidebar item active across navigation and browser history.
- Kept right-rail actions inside their cards and improved mobile brand and
  workbench-title sizing.
- Allowed Phase 1/2 rechecks to record an honest empty-telemetry runtime.

### Security
- Fail backup readiness closed when restore evidence is stale or no longer
  covers the current database table profile.

## [0.152.6] - 2026-07-06
### Fixed
- Aligned the Phase 1/2 recheck source-commit detector with runtime drift
  evidence by preserving the `-dirty` suffix for tracked delivery-source
  changes.

## [0.152.5] - 2026-07-06
### Changed
- Updated the customer-facing dashboard logo and favicon.
- Removed contract/report/delivery wording from the customer-facing dashboard
  shell and routed `/reports` to operational metrics/charts instead of a report
  workspace.

## [0.152.4] - 2026-07-03
### Security
- Require admin-scope authentication for admin access role and user read routes,
  while keeping customer-safe RBAC transparency on `/api/access/policy`.

## [0.152.2] - 2026-07-03
### Changed
- Make the Help and Delivery Evidence surface show immediate management-ready
  production and drift-review guidance instead of loading or empty placeholders.
- Replace remaining sensor discovery UI abbreviations with customer-facing
  sensor inventory language.
- Strengthen visual QA so the Help interaction fails when the first viewport
  still shows loading or empty placeholder text.

### Fixed
- Block stale Phase 1/2 recheck evidence when the runtime source commit and
  recorded source commit do not match.
- Keep phase, report, UI/UX, and delivery panels rendering when protected
  hardware discovery evidence is unavailable before an operator token is entered.

## [0.152.1] - 2026-07-03
### Changed
- Replace remaining customer-visible machine-payload wording in the cockpit and
  evidence route with plain operator language that keeps users inside the
  dashboard workflow.

## [0.152.0] - 2026-07-03
### Added
- Add a customer-safe CMDB management summary with sensor discovery counts,
  validation coverage, supported protocol families, readiness state, and next
  action without raw hardware descriptor identifiers.

### Changed
- Replace protocol-heavy dashboard labels with operator-readable workflow
  handoff language in automation, release, and UI/UX quality panels.
- Clarify standing capability authorization in internal agent governance files.

## [0.151.0] - 2026-07-03
### Security
- Require admin scope for AI provider-policy and model-service read routes in every environment.
- Restrict AI provider allowed_tools to customer-safe read-only evidence endpoints and reject admin, recovery approval, and action endpoints.
- Redact operator actor metadata from public AI routing provider-policy output.


## [0.150.0] - 2026-07-03
### Added
- Add a customer-safe latest Phase 1/2 recheck API and Delivery Decision Brief summary so managers see plain phase status, owner action, and acceptance blockers without internal artifact paths.

### Security
- Redact per-event token usage details from public AI usage surfaces while keeping aggregate token windows visible.
- Safely coerce malformed provider token counters and ignore invalid persisted token timestamps in public token windows.

## [0.149.0] - 2026-07-03
### Added
- Add an operator-controlled hardware discovery candidate queue so validated sensor evidence is reviewed before promotion into CMDB, then approved through an audited endpoint.
- Surface the Asset Discovery Queue in the Operations cockpit with human-readable queued/promoted state, asset binding, and decision labels.

## [0.148.0] - 2026-07-03
### Added
- Add admin-gated restore verification that copies and reopens the active SQLite database, runs integrity checks, records sanitized audit evidence, and surfaces restore status in backup retention, preflight, and the Operations cockpit.

## [0.147.0] - 2026-07-03
### Added
- Add a Live Signal Path and Live Sensor Commissioning panel to the Operations cockpit, showing live asset, device, telemetry, alarm, CMDB, recovery, persistence, and restore-proof state from runtime evidence.

## [0.146.9] - 2026-07-03
### Changed
- Split the Charts route into a dedicated operational trend workspace with its own UI/UX gate and browser visual assertion.
- Persist the cockpit time-range selection across reloads and make visual QA fail if operator context resets.

### Fixed
- Removed legacy demo wording from the customer dashboard shell and customer handoff package entrypoints while keeping compatibility aliases protected in the API.

## [0.146.8] - 2026-07-03
### Fixed
- Stabilize browser visual QA for the live operations dashboard by using DOM-ready checks, retrying transient connection resets, and waiting for the time-range control to update before interaction assertions.

## [0.146.7] - 2026-07-03
### Changed
- Replace machine-style grouped action labels with customer-readable production setup and go-live decision wording in owner action and management briefs.

## [0.146.6] - 2026-07-03
### Fixed
- Clear stale blocker text from completed operations workbench steps so the cockpit shows an unambiguous monitoring-ready state.

## [0.146.5] - 2026-07-03
### Fixed
- Show a human-readable continue-monitoring next action when the operations workbench has completed all live runtime steps.
- Keep the Phase 1/2 operational workbench from showing a stale recovery blocker after all pending approvals and alerts are closed.

## [0.146.4] - 2026-07-03
### Changed
- Keep shell time-range and display-mode controls session-local without browser storage so the customer dashboard avoids persistent client-side UI state.

### Security
- Remove web-storage usage from the delivered operations shell so the frontend DOM security sink gate can pass without privacy or persistence exceptions.

## [0.146.3] - 2026-07-03
### Added
- Add visible Operations Control outcome cards so each workbench action shows last action, evidence created, result state, completion, current step, and next action.
- Add profile-backed telemetry validation for supported sensor metrics, units, and physical ranges across REST and MQTT ingestion.

### Fixed
- Reject unknown telemetry metrics, impossible temperature and oxygen values, invalid occupancy states, wrong units, and metrics that do not match a device hardware profile.

## [0.146.2] - 2026-07-03
### Changed
- Improve the operations dashboard access flow by syncing operator-token inputs across the workbench without storing secrets.
- Replace visible demo/reset wording with operational baseline and lab-validation language.
- Render a customer-safe first-paint operations snapshot so the cockpit opens with live counters instead of loading-only placeholders.
- Extend visual QA with stateful interaction checks for time range, display mode, notification context, and help context.

### Fixed
- Hide the development-only reset control from the customer-facing operations dashboard.
- Keep hardware simulator records labeled as lab-validation evidence instead of demo data.
- Replace the empty QA challenge placeholder with an actionable Tests surface message.
- Scrub first-paint snapshot data so admin endpoints, local paths, raw prompts, and credential values are not embedded in the page.

## [0.146.1] - 2026-07-03
### Changed
- Replace customer-facing dashboard jargon for service readiness, automation handoffs, decision records, and knowledge quality while keeping technical metadata available for tests and admin tooling.

### Fixed
- Add UI regression coverage so raw endpoint titles and old A2A/RAG/QA customer labels do not return to the main shell.

## [0.146.0] - 2026-07-02
### Added
- Add an operator-approved commissioning workflow endpoint that creates live asset, device, configuration, telemetry, alert, recovery, audit, and CMDB evidence from the dashboard.

### Changed
- Route the dashboard operations workflow and safe preview panels through `/api/operations/*` endpoints while keeping backward-compatible demo aliases internal.

## [0.145.9] - 2026-07-02
### Changed
- Replace customer-visible demo, preview, phase-report, and raw-API wording on the dashboard with operational baseline, delivery evidence, and customer handoff language.

## [0.145.8] - 2026-07-02
### Changed
- Surface Phase 2 owner-decision and production-action items in the first-screen Action Queue so open delivery gates are visible, clickable, and evidence-linked from the cockpit.

## [0.145.7] - 2026-07-02
### Changed
- Replace customer-visible internal governance wording with operational runtime-policy, readiness-review, quality-review, and improvement-log language while keeping API contracts stable.

### Security
- Extend customer release source-content and commercial-term gates to shipped architecture ADR and agent-card documentation.

## [0.145.6] - 2026-07-02
### Added
- Add live operations, settings, CMDB, hardware-simulator, and AI resource counters to Phase 2 and Phase 1+2 recheck evidence.

### Changed
- Auto-detect the local Git source commit in recheck evidence when `--source-commit` is not supplied.
- Replace customer-visible `Evidence JSON` wording with operational evidence-record language.

## [0.145.5] - 2026-07-02
### Added
- Add Phase 2 owner-decision presets for production hardening, hosting, TLS, backup retention, identity provider, and MQTT subscriber decisions.

### Security
- Restrict owner-decision admin read/write routes to `admin:delivery:approve` while keeping production readiness controls on `access:manage`.

## [0.145.4] - 2026-07-02
### Added
- Add a customer-safe management delivery brief for phase distance, owner questions, Phase 4 scope, and official-source competitive positioning.

### Fixed
- Keep the management brief evidence-grounded when fresh project data still shows Phase 1 customer confirmation open.

## [0.145.3] - 2026-07-02
### Added
- Add a customer-safe owner decision brief that converts Phase 2 production blockers into manager-readable questions, required evidence, answer options, and acceptance impact.

### Changed
- Synchronize Claude, Gemini, and agent entrypoint versions for parallel contributor handoff.

## [0.145.2] - 2026-07-02
### Fixed
- Show public AI model-service runtime, token-window, and memory-policy evidence in the Settings surface when admin credentials are not entered.

## [0.145.1] - 2026-07-02
### Security
- Keep generated application runtime secrets owner-readable only while syncing bind-mounted secret ownership to the container application user so operator and admin gates are readable at runtime.

## [0.145.0] - 2026-07-02
### Changed
- Replace customer-visible pilot, raw JSON, and endpoint-oriented cockpit labels with operational language for the Phase 1/2 dashboard review.

### Security
- Create application runtime secrets with owner-only file permissions in the HTTPS launch script while keeping the bind-mounted lab TLS key readable by the proxy container.

## [0.144.9] - 2026-07-01
### Added
- Add Phase 2 owner-decision presets in the dashboard so production owners can prepare fallback-only AI approval, feedback review, and Phase 2 closure decisions without auto-approving them.

## [0.144.8] - 2026-07-01
### Added
- Add repeatable Phase 1, Phase 2, and Phase 1+2 union recheck CLI tools with JSON and Markdown evidence output.

## [0.144.7] - 2026-07-01
### Added
- Add a customer-safe `/api/qc/fan-out` Phase 1/2 QC board that fans out model route, assistant quality, RAG, UI/UX, release, production action, and integrated Phase 1+2 union gates.

## [0.144.6] - 2026-07-01
### Added
- Add an audited Phase 1 closure owner decision so Phase 1 reaches 100% only after explicit owner approval.

### Security
- Reject secret-like values and private paths in owner decision notes before they can appear in customer-safe approval-package responses.

## [0.144.5] - 2026-07-01
### Changed
- Refresh Phase 1 closure evidence, source hygiene, and customer-safe documents for the full production signoff loop.
- Keep Phase 1 active until production owner inputs for local AI, IDP, MQTT, TLS, backup, feedback, and signoff are recorded.

## [0.144.4] - 2026-06-30
### Changed
- Put the Phase 1 Operations Console before KPI and chart panels so the first cockpit view is operational, not landing-page content.
- Replace inflated demo KPI fallbacks with live/pilot counters and loading defaults.

## [0.144.3] - 2026-06-30
### Security
- Move Docker Compose secret file defaults out of the repository tree to `/var/lib/agentiot-greenovax/secrets` so local compose runs do not create release-blocking repo secrets.

### Changed
- Add source-tree bytecode hygiene coverage so `__pycache__` and `.pyc` artifacts are caught before release packaging.

## [0.144.2] - 2026-06-30
### Added
- Add a shell-native Production Decision Console that surfaces owner-only production blockers, readiness, open decisions, code-closeable count, safe next action, and grouped customer-safe action packets from `/api/production/action-plan`.

## [0.144.1] - 2026-06-30
### Fixed
- Keep the live Operations Workbench HITL step open when a new pending recovery proposal exists after an earlier approval, preventing false 100% completion.
- Route `/operations` to the live Operations Workbench first so operators see actionable runtime controls before secondary monitoring context.
- Refresh current-version browser visual evidence and strengthen visual QA with tablet coverage, full-page screenshots, route-specific workspace assertions, and active-surface overlap checks.

## [0.144.0] - 2026-06-27
### Added
- Add a live Operations Workbench runbook API and cockpit cards that show executable asset/device onboarding, telemetry, CMDB discovery, simulator validation, and HITL recovery status with the next operational action.

## [0.143.9] - 2026-06-27
### Fixed
- Pass the optional hardware simulator plugin and production-allowance environment controls through the HTTPS launch script so the 8040 review host can run lab/demo simulator workflows while customer delivery defaults remain disabled.

## [0.143.8] - 2026-06-27
### Fixed
- Render the Live Operations Workbench from priority runtime evidence before the slower delivery/audit refresh finishes, so the first cockpit view shows real assets, telemetry, alarms, recovery, CMDB, and simulator state instead of temporary zero/loading values.
- Guard the advanced AI settings renderer against token-gated routing fallbacks so a missing admin route payload cannot leave the cockpit in a false `Needs review` refresh state.

## [0.143.7] - 2026-06-27
### Added
- Add a read-only USB discovery status endpoint so operators can verify the optional USB sidecar state without scanning sysfs or mutating CMDB records.

### Changed
- Prioritize the mobile Operations Cockpit and KPI context before the action rail, with visual QA now checking cockpit-first mobile ordering and horizontal overflow.

## [0.143.6] - 2026-06-27
### Added
- Add an operator-gated evidence action review endpoint using stable action keys so action-board rows can record prompt-free owner review evidence.

### Changed
- Evidence action board rows now expose review state, review endpoint, reviewed-action counts, and stable action keys while keeping prompts, contacts, and secrets out of customer evidence.

## [0.143.5] - 2026-06-27
### Added
- Add Live Operations Workbench read-only clarity so token-gated write controls are disabled and explained until an operator token is present.

## [0.143.4] - 2026-06-27
### Added
- Add customer-safe REST adapter status evidence for REST device counts, telemetry counts, readiness state, and evidence links.

## [0.143.3] - 2026-06-27
### Added
- Report requested, covered, ignored, and fallback simulator profiles so lab/demo sensor coverage gaps are visible instead of silent.

## [0.143.2] - 2026-06-27
### Fixed
- Align Python package metadata with the release version used by runtime, Docker, tests, and customer documents.
- Correct the Live Operations Workbench simulator action to request the supported oxygen concentration profile.

## [0.143.1] - 2026-06-27
### Added
- Add operator-gated assistant session detail actions in the dashboard so session continuity, feedback, proposals, BDD links, and next actions are reachable from each thread row.

## [0.143.0] - 2026-06-27
### Added
- Surface 24-hour project gap discovery in the dashboard with open-gap count, engineering-closeable count, next review, next action, and owner-assigned gap rows.

## [0.142.9] - 2026-06-27
### Added
- Surface phase acceptance distance in the dashboard Phase Execution Board with remaining distance, closure task counts, owner-task count, and next gate.

## [0.142.8] - 2026-06-27
### Added
- Add customer-safe `/api/project/phase-distance` evidence for phase completion distance, closure tasks, and owner-only gates.
- Add public read-only `/api/ai/model-services` evidence so Settings can show local/cloud model readiness without exposing secrets.

## [0.142.7] - 2026-06-27
### Added
- Add browser-safe `/operations`, `/charts`, `/analytics`, and `/status` dashboard routes so operator links render the UI shell instead of JSON 404 responses.
- Add customer-safe Agent Card discovery at `/api/agent-cards` and `/.well-known/agent-card.json`.

### Fixed
- Include the product test suite in the customer release directory and source archive so acceptance evidence is reproducible.

## [0.142.6] - 2026-06-27
### Security
- Remove literal admin API paths and literal PATCH method disclosure from the public dashboard HTML while preserving authenticated admin actions through runtime path construction.

## [0.142.5] - 2026-06-27
### Changed
- Add customer-safe grouped display actions for production and final handoff queues while preserving raw action rows for traceability.

### Security
- Keep grouped public production and handoff payloads free of admin write paths, methods, request schemas, secrets, local paths, and raw prompt text.

## [0.142.4] - 2026-06-27
### Changed
- Group duplicate evidence actions into one owner-assigned dashboard row with opaque source references, grouped counts, and a fixed Open Findings CTA.

### Security
- Keep raw evidence text and finding subject IDs out of the Evidence Action Board response while preserving the Evidence workspace link for review.

## [0.142.3] - 2026-06-27
### Changed
- Surface final handoff owner/customer actions inside the release gap-closure console, including customer-safe blocker categories, required input, acceptance impact, and final handoff evidence links without exposing operator runbooks.

## [0.142.2] - 2026-06-27
### Changed
- Render the final handoff roadmap in the dashboard UI with blocker category, required input, acceptance impact, and secret-safe closure status.

## [0.142.1] - 2026-06-27
### Changed
- Make the final handoff console operational by converting owner/customer blockers into prioritized action tasks with category, required input, acceptance impact, and secret-safe closure flags.

## [0.142.0] - 2026-06-27
### Added
- Add a Next Best Action operations endpoint and first-screen cockpit action card that turns live alert, telemetry, and recovery evidence into one HITL-safe operator action without executing recovery automatically.
- Add a customer-safe summary to the production owner approval package so open owner decisions, hardening score, feedback count, AI route, and next owner action are visible without reading raw decision rows.

## [0.141.36] - 2026-06-27
### Fixed
- Return the dashboard shell for unknown browser routes while keeping API 404 responses as JSON.

## [0.141.35] - 2026-06-27
### Fixed
- Block drift-control when tracked delivery source files are dirty.
- Route direct Tests and Evidence links to their primary workspace cards.
- Refresh NOTICE, ignore, and release metadata gates to the current version.

## [0.141.34] - 2026-06-27
### Changed
- Replaced visible raw API evidence labels in operator-facing cockpit surfaces with operational labels while retaining endpoints as metadata for audit and tooling.
- Updated README runtime secret examples to use an external runtime-secret directory outside the repository root.

### Security
- Added a customer-release preflight that rejects repo-root runtime secret and temp artifacts, including ignored files, before packaging.

## [0.141.33] - 2026-06-27
### Changed
- Demoted raw API endpoint strings from prominent shell card copy into technical evidence metadata, keeping operator cards focused on business actions.
- Aligned HTTPS runtime documentation and release evidence defaults with the live reverse-proxy/backend split on port 8040 and local backend port 18080.

### Fixed
- Added nginx plain-HTTP-on-HTTPS-port redirect handling so accidental HTTP access to the TLS proxy no longer renders a raw 400 page.

## [0.141.32] - 2026-06-27
### Fixed
- Split reverse-proxy TLS readiness from browser-trusted TLS readiness so self-signed lab certificates no longer satisfy customer public-access preflight.
- Moved the live Action Queue above the main cockpit content on mobile and added a UI/UX gate for that above-fold layout contract.

### Security
- Extended the customer release documentation safety gate to reject hyphenated cross-project and private source-document markers, and sanitized existing customer-facing wording.

## [0.141.31] - 2026-06-27
### Security
- Made release mission evidence version-aware so stale stored missions no longer
  satisfy current release readiness.
- Sanitized public release mission labels and release-mission evidence findings
  so operator/internal task labels are not exposed in customer-facing endpoints.
- Aligned the release mission execution route with the advertised `agent:run`
  scope.

## [0.141.30] - 2026-06-27
### Changed
- Moved phase-closure and phase-distance helpers out of the main FastAPI
  application module to reduce `app.py` size without changing runtime behavior.
- Added direct regression coverage for owner/secret phase-closure boundaries.

## [0.141.29] - 2026-06-27
### Security
- Removed executable pytest tests and fixture-token files from customer release bundles.
- Strengthened the customer release secret-pattern gate for quoted `AGENTIOT_*TOKEN`, `AGENTIOT_*SECRET`, `AGENTIOT_*KEY`, and `AGENTIOT_*PASSWORD` assignments.

### Changed
- Refreshed release metadata and visual evidence names for version 0.141.29.

## [0.141.28] - 2026-06-27
### Security
- Restricted admin agent registry and prompt-contract read endpoints to authenticated agent-read access while preserving admin-token full views.

### Fixed
- Hardened the dashboard agent-registry fallback so anonymous admin-read denial cannot break the rendered UI.

## [0.141.27] - 2026-06-27
### Changed
- Canonicalized AI token usage month-window identifiers to 3mo, 6mo, and 12mo for contract-aligned reporting.
- Moved AI token and memory helper functions into a focused module to reduce the main application file without changing runtime behavior.


## [0.141.26] - 2026-06-27
### Fixed
- Corrected Phase 2 hardening closure metadata so customer runtime configuration gaps are not reported as code-closeable engineering work.

## [0.141.25] - 2026-06-27
### Changed
- Recorded commercial baseline v1.7.0 evidence as customer-safe hash-only metadata.
- Marked the Phase 1 commercial baseline evidence task review-ready while keeping customer or owner confirmation open.

### Security
- Kept source commercial files outside Git and customer runtime bundles, with no copied legal text or local paths in deliverables.

## [0.141.24] - 2026-06-27
### Added
- Added customer-safe document class drilldown to the daily gap-discovery inventory.
- Added regression coverage for missing public document classes without returning file names.

## [0.141.23] - 2026-06-27
### Added
- Added optional Tailscale `*.ts.net` certificate support for the 8040 HTTPS launcher.
- Documented browser-trusted access requirements for customer TLS, Tailscale certificates, and self-signed lab trust.

### Security
- Restricted the TLS runtime directory while keeping the proxy key mount readable for the container.

## [0.141.22] - 2026-06-27
### Added
- Added a customer-safe project gap-discovery summary for management dashboards.
- Added required evidence and approval-boundary columns to the production action plan UI.

## [0.141.21] - 2026-06-27

### Fixed

- Allowed CORS preflight for the admin AI model-service credential `PUT` flow.
- Corrected customer release docs so `execution_controls` is documented as a field inside `/api/release/evidence-console`, not as a pseudo-route.

## [0.141.20] - 2026-06-27

### Fixed

- Added missing waiting-for-feedback and pending-owner-signoff states to the Owner Decision Board form so it covers every backend owner-decision state.

## [0.141.19] - 2026-06-27

### Fixed

- Added the MQTT broker subscriber decision to the Owner Decision Board form so every production-owner decision exposed by the approval package can be recorded from the dashboard.

## [0.141.18] - 2026-06-27

### Changed

- Added an explicit operator-token field and result message to the Customer Feedback form so the gated feedback workflow can be completed from the dashboard without relying on hidden global controls.

## [0.141.17] - 2026-06-27

### Changed

- Refined production gap discovery so owner-only and customer-runtime items are no longer counted as engineering-closeable action-plan gaps after real runtime controls are closed.
- Tightened mobile operational ledger wrapping so KPI timestamps and endpoint chips stay inside their cards.

## [0.141.16] - 2026-06-27

### Fixed

- Fixed the HTTPS runtime launcher so non-root application containers can read mounted operator and admin token files while the runtime secret directory remains outside Git and non-traversable.

## [0.141.15] - 2026-06-27

### Added

- Added a repeatable HTTPS runtime launcher for port 8040 with reverse-proxy TLS termination, local-only app binding, runtime-managed token files, and release gates that reject TLS material.

## [0.141.14] - 2026-06-27

### Changed

- Moved customer-safe source commit and source version identity helpers into a focused release module while preserving drift-control behavior.

## [0.141.13] - 2026-06-27

### Changed

- Moved project governance review windows and customer-safe document inventory into a focused helper module while preserving drift and gap-discovery behavior.

## [0.141.12] - 2026-06-27

### Changed

- Moved customer-safe A2A/MCP JSON-RPC envelope helpers into a focused protocol module while preserving protocol endpoint behavior.

## [0.141.9] - 2026-06-26

### Changed

- Moved browser visual evidence parsing into a focused visual quality module so the main FastAPI application stays smaller while preserving UI release gates.

## [0.141.8] - 2026-06-26
### Added
- Added executable phase-closure tasks to the goal and gap boards so remaining phase distance is tracked as implementation, evidence, or owner-signoff work without claiming final acceptance.

## [0.141.7] - 2026-06-26
### Changed
- Moved live CMDB and sensor evidence ahead of long write forms in the cockpit so operational data is visible earlier.

## [0.141.6] - 2026-06-26
### Fixed
- Removed internal agent-governance filename markers from customer-deliverable source inventory code while preserving runtime inventory checks.

## [0.141.5] - 2026-06-26
### Fixed
- Aligned manual MQTT ingestion with the configured `AGENTIOT_MQTT_TOPIC_PREFIX`, including nested prefixes used by lab or broker deployments.

## [0.141.4] - 2026-06-26
### Changed
- Classified gap-discovery items by code-closeable, owner-decision, secret, and external-evidence requirements.
- Moved healthy RAG continuous review from blocking gap output to maintenance evidence.

## [0.141.3] - 2026-06-26

### Added
- Added executable customer-safe document inventory evidence to the 24-hour gap-discovery board.
- Added runtime packaging of public README, NOTICE, changelog, contract, customer, ADR, governance, and index docs for compliance reconciliation.

### Fixed
- Updated customer-release tooling version metadata to match the current release line.

## [0.141.2] - 2026-06-26

### Added
- Added first-screen operational write forms for asset registration, device registration, telemetry ingestion, alert resolution, and HITL recovery approval.

### Changed
- Populated live alarm and recovery selectors from runtime records so the cockpit can execute closed-loop actions instead of only showing status tables.
- Tightened Live Operations Workbench table rendering to avoid broken labels in narrow panes.

### Security
- Added Docker Compose hardening for read-only root filesystem, tmpfs, dropped Linux capabilities, no-new-privileges, process limit, and memory limit.
- Prevented unauthenticated assistant-session loading from producing browser console 401 errors in the cockpit.

## [0.141.1] - 2026-06-26

### Added
- Added a first-screen Live Operations Workbench with live assets, devices, telemetry, alarms, recovery queue, CMDB evidence, and simulator plugin state.
- Added workbench actions for the pilot workflow, critical telemetry, sensor CI discovery, and lab simulator execution through existing operator-gated APIs.

### Fixed
- Made the cockpit assistant status honest by showing fallback mode when model runtime credentials, route approval, or evaluation gates are not ready.

## [0.141.0] - 2026-06-26

### Added
- Added visible Pilot Operations controls for creating live assets, devices, configuration profiles, critical telemetry, alarms, recovery proposals, and CMDB sensor CI evidence from the dashboard.

### Fixed
- Made admin-only dashboard data loads use safe fallbacks without blocking the operator cockpit when no admin token is present.

## [0.140.9] - 2026-06-26

### Added
- Added the read-only `agentiot.project_gap_discovery` MCP tool so agent/tool orchestration can inspect the 24-hour gap board through the MCP-compatible gateway.

### Changed
- Raised MCP protocol evidence to six read-only tools and removed the MCP coverage gap from the project gap-discovery board.

## [0.140.8] - 2026-06-26

### Added
- Added `/api/project/gap-discovery` and `/api/project/gap-discovery/run` for customer-safe 24-hour review of contract goals, phase distance, KPI/SLA, runtime evidence, RAG/MCP/AI gates, production actions, owner decisions, and executable gap ownership.

### Security
- Protected gap-discovery review recording with `agent:run` scope and regression tests that prevent credentials, local paths, internal operating material, and admin write endpoints from leaking through the customer-safe board.

## [0.140.7] - 2026-06-26

### Security
- Removed repository-local ignored runtime temp artifacts from the active worktree and added a regression gate that fails if `.tmp/`, `secrets/`, runtime env files, or token/key material reappear under the repository root.

## [0.140.6] - 2026-06-26

### Changed
- Kept public owner approval, handoff, and model-route preflight surfaces on customer-safe evidence links while retaining admin decision writes only behind admin-gated endpoints.

### Security
- Prevented public delivery and owner-review payloads from exposing `/api/admin/production/decisions` decision paths.

## [0.140.5] - 2026-06-26

### Added
- Added admin-only production action-plan guidance for PATCH endpoint and request-schema review without exposing write operations in the public action plan.
- Added mandatory specialist-team orchestration metadata to the admin agent registry and orchestration evidence matrix.
- Added operator-facing hardware discovery profile catalog for allowlisted protocols, standards, Raspberry Pi boards, and CMDB registration policy.

### Changed
- Added compact Agent Control Plane UI counters for mandatory specialist teams and parallel lanes.
- Registered internal specialist-team governance, ADR evidence, and always-on checklist updates outside the customer deliverable boundary.

### Security
- Kept internal rosters, prompts, routing logs, and subagent reports out of customer release scope.
- Verified USB sysfs preview for unmatched descriptors does not mutate assets, devices, telemetry, configuration profiles, or CMDB records.

## [0.140.4] - 2026-06-26

### Added
- Added `/api/production/preflight` for customer-safe, secret-free TLS, backup-retention, and restore-test readiness evidence before production owner signoff.

### Security
- Kept preflight output free of credentials, certificate material, backup paths, policy text, local paths, contact data, and admin write endpoints.

## [0.140.3] - 2026-06-26

### Security
- Added sanitized security-gate command provenance to the customer release report for pytest, focused pentest/RBAC/security tests, Bandit, dependency audit, and production smoke checks.
- Enforced MCP `tools/call` input-schema validation and rejected token-like test fixtures from customer source packages.

## [0.140.2] - 2026-06-26

### Changed
- Updated internal governance evidence after running the bounded QA challenge and closing `/api/qa/evidence-report` to ready.
- Clarified USB sysfs discovery evidence for VID/PID, device class, interface class, driver binding, and CMDB preview registration.

### Security
- Reconfirmed customer-deliverable hygiene with source/customer text scans and kept internal governance outside the customer bundle.

## [0.140.1] - 2026-06-26

### Fixed
- Replaced the USB redaction test fixture string so customer release tests do not contain secret-like serial wording.

### Security
- Kept USB serial redaction coverage while avoiding secret-like literals in customer-deliverable test files.

## [0.140.0] - 2026-06-26

### Added
- Added optional USB sysfs hardware discovery preview for Linux/Raspberry Pi edge gateways, producing sanitized CMDB registration payloads from USB descriptor evidence.

### Security
- Kept USB serial values out of API responses and registration payloads while preserving redaction evidence for auditability.

## [0.139.0] - 2026-06-26

### Added
- Added USB descriptor evidence validation for hardware discovery profiles, including USB class and descriptor-token checks before CMDB sensor promotion.

### Security
- Redacted USB serial identifiers, normalized VID/PID evidence, and prevented stale descriptor evidence from auto-discovering a CI without a matching hardware profile.

## [0.138.0] - 2026-06-26

### Added
- Added actionable cockpit Action Queue buttons that open the matching operational surface with customer-safe evidence guidance instead of leaving queue rows as static visual cards.

### Changed
- Strengthened the UI/UX quality gate so live action queue readiness requires route-aware controls, evidence endpoints, and visible action labels.

## [0.137.0] - 2026-06-26

### Added
- Added `/api/hardware/discovery/profiles` for operator-approved hardware profile ingestion that registers asset, device, configuration profile, telemetry, and CMDB sensor CI evidence from matching metric, protocol, standard, and board metadata.
- Split the hardware profile catalog out of the simulator plugin so USB/MQTT/REST discovery can use the same clean-room profile evidence without embedding demo code in the core path.

### Security
- Rejected hardware discovery submissions that report a known metric without matching standard evidence, preventing untrusted USB/metric spoofing from creating CMDB sensor CIs.

## [0.136.0] - 2026-06-26

### Added
- Added CI/CMDB auto-discovery for sensor configuration items from registered device evidence, hardware profile metadata, protocol coverage, standards, and USB-capable hardware profiles.

### Security
- Prevented metric-only telemetry spoofing from promoting a generic device into a sensor CI without matching configuration-profile evidence.

## [0.135.0] - 2026-06-26

### Added
- Added an optional hardware simulator plugin surface for lab/demo Raspberry Pi 4/5 sensor profiles, protocol coverage, and bounded telemetry validation through the hardware data interface.

## [0.134.51] - 2026-06-26

### Security
- Removed the direct admin production-readiness endpoint from the public project goal optimization board while preserving customer-safe hardening evidence.

## [0.134.50] - 2026-06-26

### Security
- Removed direct admin write endpoints and PATCH method hints from the public production action plan while keeping customer-safe evidence links and approval boundaries visible.

## [0.134.49] - 2026-06-26

### Security
- Required admin authorization for the AI routing control console so provider/model routing internals remain behind the `agent:manage` admin gate.

## [0.134.48] - 2026-06-26

### Security
- Required admin authorization for the admin AI token-usage read endpoint while keeping the public usage ledger available as the customer-safe summary surface.
- Prevented failed JWKS identity-provider fetches from writing `None` into the JWKS cache, so only successful bounded JSON key-set responses are cached.

## [0.134.47] - 2026-06-26

### Security
- Hardened customer release evidence fetching so drift-control and runtime-version evidence must come from approved local/private API paths with ambient proxy and redirect handling disabled.

## [0.134.46] - 2026-06-26

### Security
- Disabled ambient HTTP and HTTPS proxy inheritance for JWKS identity-provider fetches so identity metadata cannot be routed through unintended environment proxies.

## [0.134.45] - 2026-06-26

### Security
- Blocked unsafe cloud model endpoint storage when the configured host resolves to private, loopback, link-local, reserved, multicast, or unspecified ranges.

## [0.134.44] - 2026-06-26

### Security
- Blocked unsafe local model endpoint storage when the configured host resolves outside loopback, link-local, or private LAN ranges.

## [0.134.43] - 2026-06-26

### Security
- Required Docker-host local model endpoints to pass DNS resolution into loopback, link-local, or private LAN ranges before any provider request is opened.

## [0.134.42] - 2026-06-26

### Security
- Restricted local model runtime endpoints to loopback, link-local, private LAN, localhost, or Docker-host targets so local-provider credentials cannot be sent to public internet endpoints.

## [0.134.41] - 2026-06-26

### Security
- Disabled ambient HTTP and HTTPS proxy inheritance for model runtime calls so local or cloud model credentials cannot be routed through unintended environment proxies.

## [0.134.40] - 2026-06-26

### Security
- Disabled redirects for local model runtime calls so local API keys or Basic credentials cannot be forwarded to a redirected endpoint.

## [0.134.39] - 2026-06-26

### Security
- Disabled redirects for outbound cloud model provider calls so prevalidated HTTPS/DNS boundaries cannot be bypassed by a provider redirect before response parsing.

## [0.134.38] - 2026-06-26

### Security
- Added DNS-resolution validation for cloud model provider endpoints so HTTPS model calls are blocked when the host resolves to private, loopback, link-local, reserved, multicast, or unspecified addresses before any outbound request.

## [0.134.37] - 2026-06-26

### Security
- Restricted model-service credential environment references to provider-scoped secret names so internal runtime tokens cannot be reused as outbound model API credentials.

## [0.134.36] - 2026-06-26

### Security
- Required HTTPS for cloud model-service endpoints at credential storage and runtime provider-call boundaries so API keys are never sent to plain HTTP model routes.

### Fixed
- Made AI model-route preflight honor an approved fallback-only owner decision without showing provider-selection P0 actions or claiming provider runtime readiness.

## [0.134.35] - 2026-06-26

### Security
- Hardened the customer release builder with a direct runtime `/api/version` parity gate so customer bundles cannot be mirrored when runtime version, clean-room state, or customer identity differs from the committed release source.

## [0.134.34] - 2026-06-26

### Security
- Added bearer-token authentication failure throttling so malformed or replayed bearer credentials hit the same bounded abuse gate as operator-token failures without exposing token, IDP, or traceback details.

## [0.134.33] - 2026-06-26

### Security
- Required every bearer-token subject to have an active admin-defined access assignment before write or privileged read authorization, while preserving bootstrap `X-Admin-Token` and `X-Operator-Token` paths for configured operations.
- Allowed contact-safe public subject references for bearer assignments without accepting raw email, phone, or local contact identifiers.

## [0.134.32] - 2026-06-26

### Security
- Enforced admin-defined bearer user assignments so active assignments provide the effective role and scopes, disabled or review-required assignments fail closed, and assigned scopes are intersected with the current role policy before route authorization.

## [0.134.31] - 2026-06-26

### Added
- Recorded counts-only token usage for authenticated grounded-fallback assistant turns so the required token windows update even when no external provider call is made.

### Fixed
- Logged six-hour drift-control loop failures instead of suppressing them silently, keeping release governance auditable.

## [0.134.30] - 2026-06-26

### Security
- Added secret-delivery posture evidence to `/api/security/status` so runtime audits can prove whether operator, admin, identity, and credential secrets are delivered through mounted secret files, direct environment values, invalid files, or not configured, without returning secret values or local paths.

## [0.134.29] - 2026-06-26

### Security
- Added a runtime Content-Security-Policy header and security-status evidence so production responses constrain external resources, framing, object embedding, forms, and script evaluation.

## [0.134.28] - 2026-06-26

### Fixed
- Removed restricted internal-agent filename literals from the release regression fixture so the customer source bundle can pass the same text-safety gate it enforces.

## [0.134.27] - 2026-06-26

### Changed
- Removed stale historical Playwright visual QA artifacts from the tracked development source state so dev archives carry only current-version evidence and cannot reintroduce obsolete screenshots or oversized artifact history into release work.
- Added bundle-scope visual evidence and parent handoff gates so customer release PASS reports cannot coexist with stale customer artifacts or internal development archives beside the deliverable.

## [0.134.26] - 2026-06-26

### Security
- Made optional operator authentication fail closed when an invalid operator or bearer credential is supplied to admin read surfaces, while preserving anonymous customer-safe summaries when no credential is provided.
- Required `agent:run` scope for AI evaluation run creation so read-only agent scopes cannot create release/evaluation evidence.
- Required fresh timezone-aware visual QA evidence in the customer release gate and runtime UI/UX evidence status, rejecting missing or older-than-six-hour reports.

## [0.134.25] - 2026-06-26

### Fixed
- Added `/api/ai/model-resource-governance` as a compatibility alias for AI credential, token-window, and memory-policy governance so operators and agents do not hit a 404 on the model-resource wording.

## [0.134.24] - 2026-06-26

### Security
- Added a pytest source-content safety gate that fails if implementation, test, Docker, or tool code contains external-project markers, restricted contract document markers, restricted instruction markers, or secret-like literals.

## [0.134.23] - 2026-06-26

### Changed
- Added production acceptance boundary evidence to release evidence and drift-control responses so release KPI readiness cannot be mistaken for final customer production acceptance.

### Security
- Required authenticated operator scope for MCP `tools/call` in production while keeping MCP discovery public.
- Bounded AI provider JSON response reads and rejected oversized or non-object provider payloads before chat fallback, audit, or token-ledger handling.

## [0.134.22] - 2026-06-26

### Security
- Hardened provider answer acceptance to reject model output containing secret-like material, local/private paths, prompt-injection text, or tool-call payloads before chat or SSE exposure.
- Added regressions proving hostile and malformed provider responses stay out of chat responses, SSE events, audit events, findings, assistant ledgers, and token ledgers.

## [0.134.21] - 2026-06-26

### Added
- Added admin dashboard controls for AI memory allocation, retention, session cap, warning threshold, and auto-prune policy.
- Added 12-month token-usage retention pruning with audit evidence while preserving the required reporting windows.

### Security
- Hardened the customer release builder and source archive gate to reject backup and patch artifacts such as `.orig`, `.bak`, `.rej`, and `.patch`.

## [0.134.20] - 2026-06-26

### Added
- Automated generation of a customer-safe source archive and checksum in the customer release builder.

## [0.134.19] - 2026-06-26

### Security
- Hardened the customer release builder to reject `.env*` and `secrets/` runtime material if it enters the release tree.
- Added runtime delivery regression coverage proving `.env*` and `secrets/` are excluded from Git and Docker build contexts.

## [0.134.18] - 2026-06-25

### Fixed
- Added `/api/project/goal-board` as a customer-safe compatibility endpoint for the goal-optimization board so manager dashboards and external checks do not receive a 404.

## [0.134.17] - 2026-06-25

### Fixed
- Made drift-control recording create a fresh release audit when the version or source commit changes inside an otherwise current six-hour review window.

## [0.134.16] - 2026-06-25

### Security
- Added file-backed `AGENTIOT_CREDENTIAL_FERNET_KEY_FILE` support and Docker secret wiring for encrypted AI credential storage.
- Added file-backed OIDC shared-secret and MQTT password/TLS secret support so production Compose can use mounted runtime secrets instead of direct secret environment values.

## [0.134.15] - 2026-06-25

### Changed
- Added production database persistence readiness fields to `/readyz` so production deployments fail readiness when they use a temporary default database.
- Centralized operator-token scopes on the RBAC role catalogue and added runtime evidence-route token-file coverage.

### Fixed
- Kept drift-control finding evidence free of phone-like numeric chains while preserving structured KPI, SLA, version, and source evidence in audit detail.

## [0.134.14] - 2026-06-25

### Changed
- Added top-level `version` fields to final delivery and handoff console responses so customer delivery endpoints are traceable with the same version contract as the rest of the API.
- Exposed production hardening readiness as a boolean and aligned the goal-optimization board with the actual readiness-control state.

## [0.134.13] - 2026-06-25

### Changed
- Added customer-safe production action blocker taxonomy so `/api/production/action-plan` separates engineering-visible tasks, customer runtime configuration, owner signoff, and customer decisions.
- Updated the production owner approval package in English and German to document the taxonomy and formal approval boundary.

### Security
- Marked which production actions cannot be closed without customer secret material while keeping all credential values out of API responses and customer deliverables.

## [0.134.12] - 2026-06-25

### Fixed
- Updated customer-facing drift owner-decision and website-demo runtime evidence to the current release version.

### Security
- Extended the customer-release stale-version gate to block `0.131.x` runtime and owner-decision evidence from entering a new release bundle.

## [0.134.11] - 2026-06-25

### Security
- Aligned the development source-tree secret-literal regression with the customer-release gate so `secret` and `client_secret` hardcoded values are blocked before release packaging.

## [0.134.10] - 2026-06-25

### Security
- Added a customer-release production-mode smoke gate that proves production runtime hides interactive API documentation, enforces trusted hosts, and removes non-customer runtime hardening controls from the action plan.

## [0.134.9] - 2026-06-25

### Security
- Removed customer-facing sensitive artifact references from release documentation.
- Hardened the customer-release text safety gate with German sensitive-artifact markers.

## [0.134.8] - 2026-06-25

### Security
- Added explicit customer-release gates for generic secret-like literals in deliverable code and browser DOM security sinks in the shipped dashboard page.
- Made the release report record those gates directly so clean-room and security evidence is not only inferred from pytest.

## [0.134.7] - 2026-06-25

### Changed
- Made UI/UX visual QA evidence require the release route and viewport matrix for `/`, `/reports`, `/tests`, `/evidence`, and `/settings`.
- Added footer-safe cockpit spacing and regenerated browser screenshot evidence for desktop, desktop-wide, and mobile viewports.

### Security
- Hardened the customer release builder so visual proof must include customer-safe screenshot files, not only a JSON report.

## [0.134.6] - 2026-06-25

### Changed
- Added README protocol evidence sections for A2A, MCP, ADR, and orchestration contract endpoints in English and German.
- Added a documentation regression so protocol evidence endpoints stay indexed for customer and release review.

## [0.134.5] - 2026-06-25

### Security
- Added a generated `requirements.lock` with SHA-256 package hashes for runtime Python dependencies.
- Changed the Docker build to install from `requirements.lock` with `pip --require-hashes`.
- Included the dependency lockfile in the customer release manifest and source-content scan surface.

## [0.134.4] - 2026-06-25

### Security
- Pinned the Docker base image by digest and pinned direct Python runtime dependencies to exact versions to reduce release supply-chain drift.
- Updated the runtime dependency regression to require exact MQTT client pinning.

## [0.134.3] - 2026-06-25

### Security
- Made the customer release builder execute and record the full pytest suite, focused pentest/RBAC/security-hardening tests, Bandit medium/high scan, and Python dependency vulnerability audit before packaging.
- Kept clean-room release gates mandatory for customer text, deliverable source content, drift-control evidence, and manifest validation.

## [0.134.2] - 2026-06-25

### Security
- Added direct JWKS fetch hardening regressions for redirect blocking, JSON-only response enforcement, bounded body size, and endpoint-safe error reporting.
- Kept the customer deliverable clean-room gate focused on source code, tests, Docker, tooling, and package metadata with no project-cross-contamination or contract-source leakage allowed in code.

## [0.134.1] - 2026-06-25

### Security
- Expanded RS256/JWKS SSRF regression coverage for private IP, IPv6 loopback, link-local metadata, localhost, credentialed, and non-HTTPS JWKS endpoints.
- Proved unsafe JWKS endpoints are rejected before any JWKS client fetch and without returning endpoint details to clients.

## [0.134.0] - 2026-06-25

### Added
- Added a customer-safe `/api/production/backup-retention` readiness endpoint for backup policy metadata, cadence, retention, restore-test state, and fingerprint-only evidence.
- Connected backup-retention readiness into production hardening, owner approval evidence, API baseline documentation, and acceptance checks.

## [0.133.12] - 2026-06-25

### Security
- Hardened the release text-safety gate so restricted project, prompt, private path, and contract-source markers are generated only at scan time and are not stored as raw restricted text in release tooling.
- Expanded the source clean-room regression to cover release tooling and package metadata in addition to runtime source, tests, and Docker files.
- Documented the blocking source-content and pentest/security gates in paired governance and customer release documents.

## [0.133.11] - 2026-06-25

### Security
- Added production token-strength readiness checks so weak runtime tokens do not satisfy production readiness or release execution controls.
- Exposed customer-safe token strength states without returning token values.
- Added regression coverage for weak and strong production operator-token readiness.

## [0.133.10] - 2026-06-25

### Security
- Hardened the write request body limit to count actual streamed body bytes, including missing or understated Content-Length requests.
- Added ASGI-level abuse regressions for chunked-style payloads and misstated Content-Length payloads.

## [0.133.9] - 2026-06-25

### Security
- Added a bounded request-body gate for write endpoints to reject oversized JSON payloads before endpoint processing.
- Added regression coverage for oversized payload rejection, valid small writes, and invalid payload-limit startup configuration.

## [0.133.8] - 2026-06-25

### Security
- Restricted production secret-file reads to mounted runtime secret directories.
- Added regression coverage proving production ignores operator token files outside approved secret mounts without exposing token contents.

## [0.133.7] - 2026-06-25

### Security
- Added explicit CORS allowlist handling with production wildcard rejection.
- Added regression coverage proving browser cross-origin access stays closed unless an origin is configured.

## [0.133.6] - 2026-06-25

### Security
- Hardened RS256 JWKS configuration so non-HTTPS or private/local JWKS endpoints are rejected before key fetch.
- Added bounded authentication failure rate limiting for operator and admin write gates.
- Added regression coverage for private JWKS rejection and repeated failed-auth throttling.

## [0.133.5] - 2026-06-25

### Security
- Added a customer-release code-only contamination gate that blocks contract-source terms from deliverable source, tests, Docker files, and package metadata.

## [0.133.4] - 2026-06-25

### Fixed
- Accepted human-readable Raspberry Pi 4 hardware labels in firmware compatibility checks while preserving canonical catalog ids.

## [0.133.3] - 2026-06-25

### Changed
- Removed specific contract-source wording from runtime and test code surfaces and replaced it with customer-safe delivery-scope wording.

### Security
- Added a source-tree clean-room regression check to block other-project names, restricted source markers, private local path markers, and internal operation wording from runtime/test/docker code.

## [0.133.2] - 2026-06-25

### Added
- Added an automated Phase 2 pentest abuse gate covering auth bypass, SSRF-style model endpoint probes, XSS redaction, injection/traversal handling, and customer-safe control-plane text rejection.
- Added paired EN/DE customer documentation and BDD acceptance evidence for the pentest abuse gate.

## [0.133.1] - 2026-06-25

### Changed
- Reworded customer AI-provider evidence documentation so the release bundle stays free of restricted delivery-scan terms.
- Moved the dashboard shell into a static package template so security scanners audit runtime Python without treating HTML navigation text as SQL construction.

### Security
- Hardened SQLite dynamic identifier usage with validation and quoting for internal table and column names.
- Replaced local Git subprocess fallback with direct Git metadata reading to remove a process execution surface.
- Validated provider runtime URLs before outbound model calls and upgraded Docker dependency ranges to avoid audited `pip` and `starlette` vulnerabilities.
- Kept validated dynamic SQL placeholder construction behind inline audit suppressions so the medium/high Bandit gate runs without CLI-level skips.

## [0.133.0] - 2026-06-25

### Added
- Added a prompt-free assistant follow-up contract to `/api/chat` and the coworker package, exposing known evidence, missing-before-action items, next best action, safe follow-up question, owner agent, and evidence endpoints.
- Added regression and BDD coverage proving the follow-up contract remains actionable without returning operator input text, answer storage, provider payloads, credentials, local paths, or restricted artifacts.

### Changed
- Provider-policy documentation now consistently lists local, OpenAI, Gemini, and Hugging Face route gates while parity claims remain blocked until approved runtime evidence passes.

## [0.132.0] - 2026-06-25

### Added
- Added `/api/ai/model-route-preflight` to show provider, credential, runtime, activation-check, token-window, memory-policy, and owner-decision gates before any local/cloud assistant runtime is claimed ready.
- Added regression coverage proving the preflight exposes actionable next steps without returning credential values, raw prompts, provider payloads, or local runtime URLs.

### Changed
- AI model-route readiness now has a clearer admin/customer-safe preflight path while external model parity claims remain blocked until owner approval and activation evidence pass.

## [0.131.0] - 2026-06-25

### Added
- Release missions now record prompt-free assistant session evidence so closed-loop learning can reach coworker-quality target evidence without manual chat seeding.
- Added regression coverage proving release-session evidence remains hash-only and does not expose mission instruction text, assistant instruction text, or credential-like values.

### Changed
- Release mission responses now include customer-safe closed-loop session metadata while provider parity claims remain withheld until all external model gates are approved.

## [0.130.0] - 2026-06-25

### Added
- A2A handoff traces now expose customer-safe Agent Card id, prompt reference, prompt version, prompt hash, and prompt-contract history endpoint.
- Agent Card artifacts now mirror the full runtime card schema, including purpose, inputs, outputs, model policy, SLA, A2A, ADR, eval profile, and customer-delivery safety fields.

### Changed
- Agent Card model policy and SLA now include the required B3 schema aliases: `reasoning`, `qa`, `availability`, and `p95_latency_ms`.

## [0.129.0] - 2026-06-25

### Added
- Added regression coverage proving assistant memory retention removes expired prompt-free interaction metadata, enforces session and metadata memory caps, and preserves active session tool proposals.
- Added BDD coverage for admin-managed assistant memory pruning without raw prompt, answer, provider payload, or credential storage.

### Changed
- Assistant memory governance now enforces retention, session-count, and metadata memory-cap policy after policy updates and chat turns, records prompt-free prune audit evidence, and avoids deleting proposal state for sessions that still have active interactions.

## [0.128.0] - 2026-06-25

### Added
- Added regression coverage proving release, QA, session, feedback, orchestration, and provider transparency evidence drive `/api/assistant/coworker-quality` to ready while parity claims remain withheld.

### Changed
- Coworker quality scoring now uses live A2A/ADR control-plane evidence and AI resource-governance token-window evidence for agent orchestration and provider-route transparency.
- The production dashboard no longer requests protected assistant-session evidence before an operator token is present, preventing unauthenticated 401 console noise during visual QA while preserving customer-safe fallback session metadata.

## [0.127.0] - 2026-06-25

### Added
- Added Docker database persistence through `/app/data/agentiot-greenovax.db` and a dedicated `agentiot_data` volume so runtime evidence survives container replacement.

### Changed
- Docker image setup now creates the writable application data directory alongside the output directory for production delivery.

## [0.126.0] - 2026-06-25

### Added
- Added a rendered Production Action Plan table to the operational dashboard so production controls and owner decisions are visible as actionable UI rows.

### Changed
- Production signoff gaps now appear in the Production panel with action count, control count, owner decision count, owner agent, state, priority, and admin endpoint.

## [0.125.0] - 2026-06-25

### Added
- Added `/api/production/action-plan` to convert open production controls and owner decisions into customer-safe executable action tasks.
- Added tests and BDD coverage for the production signoff action plan without storing restricted execution data, contact data, or credentials.

### Changed
- Production owner approval evidence now links directly to the action plan so Phase 2 closure gaps are operational instead of only descriptive.

## [0.124.0] - 2026-06-25

### Added
- Added a six-hour freshness gate for local and cloud model-service connectivity evidence before provider-runtime chat can execute.
- Added BDD and unit coverage proving stale connectivity evidence blocks provider calls and returns grounded fallback.

### Security
- Provider-runtime chat now refuses stale activation evidence with `connectivity_check_stale`, exposes prompt-free freshness metadata, and does not call external or local model services until a fresh admin connectivity check exists.

## [0.123.0] - 2026-06-25

### Added
- Added a pre-return provider answer acceptance gate for local and cloud model routes. Raw provider text must reference selected runtime or RAG evidence terms before it can be shown as provider-backed output.

### Changed
- Provider chat responses now attach `answer_acceptance` metadata to accepted provider-runtime answers.

### Security
- Ungrounded provider answers are rejected, audited as `ai.provider_runtime.rejected`, kept out of the user answer and persisted evidence, and replaced with grounded fallback while preserving token accounting.

## [0.122.0] - 2026-06-25

### Changed
- Release missions now enforce the 60-round assistant Q/A minimum even when a smaller round count is requested, so Assistant Quality cannot pass on a reduced rehearsal.
- Release evidence console summaries now expose assistant round count, requested round count, minimum round policy, and policy status.

### Fixed
- Release evidence console preserves the operator-requested assistant round count from stored mission evidence instead of rebuilding it as the enforced minimum.

## [0.121.0] - 2026-06-25

### Changed
- Separated release KPI scoring from live operational assistant risk so completed release evidence gates can clear the 99.99 SLA while retaining the operational decision score as separate evidence.
- Updated runtime, Docker, tests, and customer-safe documentation headers to version 0.121.0.

## [0.120.0] - 2026-06-25

### Added
- Added a granular RBAC scope catalog to `/api/access/policy` for panel, agent-action, data, and admin scopes.
- Added per-agent run, panel-read, data-scope, and default-deny metadata to runtime Agent Cards.

### Security
- Changed bearer-token authorization to deny unknown roles by default before any write action is accepted.

## [0.119.0] - 2026-06-25

### Changed
- Hardened Docker Compose to use mounted operator/admin token secret files instead of direct token environment variables.
- Removed model-provider API key forwarding from Compose; provider credentials are managed through product credential controls.
- Updated runtime configuration tests and hardening documentation for file-based secret delivery.

## [0.118.0] - 2026-06-25

### Added
- Added A2A-compatible JSON-RPC discovery and task dispatch via `/api/a2a/jsonrpc`.
- Added bounded A2A SSE discovery events via `/api/a2a/messages/stream`.
- Added bilingual versioned Agent Card registry artifacts under `docs/agent-cards/`.

### Changed
- Release builder now requires exact-version visual evidence and includes Agent Card artifacts in the customer bundle.
- Updated runtime dependency audit values from the current Docker image.
- Corrected current source/test authorship headers and ADR endpoint evidence.

## [0.117.0] - 2026-06-25

### Added
- Added official bilingual ADR files under `docs/adr/` for the agent-orchestrated dashboard and prompt-free assistant routing/model readiness.
- Added the ADR directory to the customer release bundle so numbered product decisions are delivered with the customer-safe documentation package.

### Changed
- Updated customer document indexes and release manifests to list the official ADR package.
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.117.0.

## [0.116.0] - 2026-06-25

### Added
- Added activation-check evidence to AI model benchmark and route-decision readiness so local/cloud model routes become runtime-ready only after a successful provider connectivity check and token-count usage record.
- Added customer documentation for the model activation evidence gate and fixed the customer document index table shape.

### Changed
- Cloud provider calls now honor a validated stored model-service endpoint URL before falling back to deployment defaults.
- The model-services UI now shows each provider's latest activation check status.
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.116.0.

### Security
- Customer-visible model benchmark activation evidence is sanitized to avoid prompts, answers, secrets, local paths, provider payloads, or internal operator records.

## [0.115.0] - 2026-06-25

### Added
- Added a streamed cockpit assistant UI path that consumes `/api/assistant/stream` events and updates route, evidence, answer deltas, HITL proposal counts, and the final assistant panel without exposing protected operator input.

### Changed
- Extended the SSE `done` event with assistant plan and next-action metadata so web clients can reconstruct the full customer-safe assistant package from stream events.
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.115.0.

## [0.114.0] - 2026-06-25

### Added
- Added `/api/assistant/stream`, a customer-safe Server-Sent Events transport for assistant route, evidence, A2A trace, answer deltas, tool proposals, review, and done events.
- Added regression tests proving SSE event order, prompt-free privacy, authenticated ledger writes, and anonymous preview isolation.

### Changed
- Shared `/api/chat` response construction with the SSE transport so JSON and streaming assistant paths use the same session, HITL, privacy, and evidence logic.
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.114.0.

## [0.113.0] - 2026-06-25

### Added
- Added a deterministic evidence-cited coworker answer composer for the no-credential grounded fallback route.
- Added an answer-specificity quality gate so assistant review checks visible citation and route alignment before awarding top answer quality.

### Changed
- Coworker quality actions now surface score-gap work even when every dimension is technically ready.
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.113.0.

## [0.112.1] - 2026-06-25

### Fixed
- Fixed the dashboard refresh cycle by replacing the stale `setText` helper call with `setShellText` in the AI model services renderer.
- Replaced the initial right-rail pilot setup placeholder with a neutral live-loading state so stale setup guidance cannot remain visible after runtime records load.

### Changed
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.112.1.

## [0.112.0] - 2026-06-25

### Added
- Added a provider chat execution gate that requires a successful active-provider connectivity check with token-count evidence before `/api/chat` can call a local or cloud model route.
- Exposed `provider_chat_gate` in `/api/ai/routing` so operators can see missing connectivity, model mismatch, runtime, and usage-record gates without raw prompts or provider payloads.

### Changed
- Updated local, OpenAI, Gemini, and Hugging Face provider-runtime tests so provider-backed chat proves the active connectivity check first, then verifies prompt-free chat execution.
- Bumped runtime, Docker, tests, and customer-safe document headers to version 0.112.0.

### Security
- Provider chat remains blocked when connectivity evidence is missing, failed, model-mismatched, or lacks token usage recording; fallback answers continue without secret, prompt, answer, URL, or provider payload storage.

## [0.111.0] - 2026-06-25

### Added
- Added an audited AI model route decision gate that treats real provider runtime readiness and owner-approved fallback-only delivery as separate, explicit states.
- Added goal-optimization evidence fields for AI model route readiness, decision state, and delivery mode without inflating model capability scores.

### Changed
- Connected the existing production-owner `ai-model-route-approval` decision to AI assurance and optimized project goals so missing credentials stay visible while fallback-only acceptance can close the route-decision gate.

### Security
- The route decision gate returns no credential values, operator-entered content or provider response bodies.

## [0.110.0] - 2026-06-25

### Added
- Added prompt-free assistant session/thread endpoints for coworker continuity: `/api/assistant/sessions` and `/api/assistant/sessions/{session_id}`.
- Added Assistant Session Threads UI metrics and table for session turns, parent links, feedback, pending approvals, and next actions.
- Added closed-loop coworker scoring evidence that joins findings, BDD candidates, and assistant session threads without exposing prompts or answers.
- Added an assistant HITL approval bridge: `/api/assistant/tool-proposals/{proposal_id}/approve` records scoped operator approval for prepared recovery proposals.
- Added production gating and actor filtering for assistant session/thread metadata.

### Security
- Session/thread responses return metadata only: prompt text, answer text, provider payloads, credential values, and actor values remain excluded.
- The HITL bridge records `device_action_executed=false`, keeps physical recovery execution outside the assistant approval endpoint, and treats replay as idempotent without duplicate recovery audits.

## [0.109.0] - 2026-06-25

### Added
- Added an admin-only active model-service connectivity check endpoint for configured local/cloud providers.
- Added Settings controls to run the active provider probe after credential, policy, runtime, and environment gates are ready.
- Added token-ledger recording for provider connection probes without storing prompts, answers, secrets, local URLs, or provider payloads.

### Security
- Provider tests are blocked unless the provider is active in policy, runtime execution is enabled, required credentials exist, and the local/cloud runtime gate environment variable is approved.

## [0.108.1] - 2026-06-25

### Added
- Added a compact AI Model Services control directly inside Settings so admins can configure local, OpenAI, Gemini, or Hugging Face credentials without scrolling into the legacy workspace.

### Changed
- Connected the Settings model-service panel to the same write-only credential endpoint and runtime readiness evidence used by the full admin form.

## [0.108.0] - 2026-06-25
### Added
- Added an admin dashboard AI Model Services surface for local, OpenAI, Gemini, and Hugging Face credential readiness.
- Added write-only model-service credential controls for endpoint URL, API key, username/password, and deployment environment references.
- Added regression coverage proving the dashboard exposes model-service controls without returning or embedding secret values.

### Changed
- Updated AI provider and UI/UX customer documentation to describe the model-service control path as the practical prerequisite for approved runtime evaluations.

## [0.107.2] - 2026-06-24
### Added
- Added a production-owner AI model route approval decision so GreeNovaX can formally accept fallback-only delivery or provide approved local/cloud model credentials before external parity claims.
- Added customer-safe AI routing, model benchmark, and evaluation evidence links to the production approval package.

### Changed
- Updated the Owner Decision Board and customer approval documentation to include AI route acceptance as an explicit Phase 2 signoff gate.

## [0.107.1] - 2026-06-24
### Security
- Changed anonymous `/api/chat` into a non-persistent preview path: no assistant interaction ledger rows, no closed-loop findings, no persisted tool-proposal state, and no provider runtime calls are created without an authenticated operator.
- Added regression coverage for anonymous preview isolation while keeping authenticated operator chat prompt-free and durable for evidence.

## [0.107.0] - 2026-06-20
### Added
- Added a customer-safe MCP-compatible read-only tool registry at `/api/mcp/tools`.
- Added a JSON-RPC gateway at `/api/mcp/jsonrpc` for `initialize`, `tools/list`, and read-only `tools/call`.
- Added MCP protocol evidence to `/api/orchestration/protocol-contracts` so Agent Cards, A2A, and tool access are reviewed together.

### Security
- Restricted MCP tool calls to deterministic read-only dashboard evidence; recovery/admin/write tools remain outside the gateway and require HITL-controlled product endpoints.
- Added regression coverage proving MCP responses do not expose raw instructions, provider payloads, or credential-like values.

## [0.106.1] - 2026-06-20
### Fixed
- Replaced the stale exact-version Playwright allowlist with version-agnostic visual evidence patterns for customer-safe release packaging.
- Updated Docker packaging to copy the bounded Playwright evidence directory without failing during the first build of a new patch version.

### Changed
- Advanced the project release metadata to 0.106.1 after closing the independent QA evidence gap on the live runtime.

## [0.106.0] - 2026-06-20
### Added
- Added admin-managed prompt-contract version history, redacted hash/length diff evidence, and rollback controls for section agents.
- Added the `assistant.system.default` prompt artifact with version history, admin-only content, public hash references, and rollback for the final provider runtime instruction.
- Added `/api/admin/prompts`, `/api/admin/prompts/{prompt_id}`, `/api/admin/prompts/{prompt_id}/history`, and `/api/admin/prompts/{prompt_id}/rollback`.

### Changed
- Updated provider runtime calls to use the active prompt artifact version and return only prompt references in runtime metadata.
- Updated the Admin Prompt Contract Console to include runtime prompt artifact version, hash, storage, and rollback policy.

### Security
- Added regression coverage proving prompt artifact history is redacted publicly and provider runtime responses do not expose raw instructions.

## [0.105.1] - 2026-06-20
### Fixed
- Fixed customer-release package version coherence by aligning `pyproject.toml`, `requirements.txt`, runtime source headers, Docker metadata, and release documentation to 0.105.1.
- Extended the customer-release stale-version scan to block stale 0.104.x package metadata before handoff.
- Replaced internal governance role labels in customer-facing source and documentation with customer-safe delivery role names.

### Changed
- Rebuilt release evidence after resolving the demo alert/recovery queue through the operator API so release KPI/SLA and drift-control evidence report a zero SLA gap.

## [0.105.0] - 2026-06-20
### Added
- Added `/api/orchestration/protocol-contracts` with versioned Agent Cards, A2A envelope metadata, RBAC scopes, SLA targets, and bounded application tool contracts.
- Added Admin UI tables for Agent Card and tool-contract review plus compact Review actions on governance cards.

### Security
- Added production public redaction for model-service governance, assistant interaction ledger details, and release gap-closure runbook fields while keeping authenticated admin/operator detail available.

## [0.104.1] - 2026-06-20
### Fixed
- Fixed the customer-release stale-version scan so current runtime-version rows do not false-positive and stale 0.54.x, 0.98.x, and 0.103.x runtime/header references are blocked.
- Updated remaining NOTICE and requirements headers to the current release version and kept stale-version regression fixtures out of customer bundle scans.

## [0.104.0] - 2026-06-20
### Added
- Added customer-safe AI runtime configuration evidence for local and cloud model gates without returning secrets.
- Added Docker Compose environment wiring for AI credential encryption, local runtime approval, cloud runtime approval, and provider credential references.

### Changed
- Raised the default assistant memory policy to 768 MB so the normal server baseline satisfies the memory recommendation gate while preserving bounded retention and auto-prune controls.
- Tightened the goal-optimization resource-governance gate so token windows and memory recommendation must both be ready.

## [0.103.2] - 2026-06-20
### Fixed
- Removed prohibited delivery-scan literals from the goal-optimization regression test so the clean customer bundle can include the test suite without internal-instruction marker matches.

## [0.103.1] - 2026-06-20
### Added
- Added `/api/project/goal-optimization` to expose optimized contract-gap goals, phase distance, AI model-route blockers, token/memory governance status, UI/UX quality status, and production signoff actions without leaking prompts or credentials.

## [0.103.0] - 2026-06-20
### Added
- Added admin-managed cloud/local AI model service credentials with encrypted-at-rest secret support, fingerprint-only responses, and private-endpoint safeguards for cloud providers.
- Added token usage ledger windows for 1, 6, 12, and 24 hours; 2, 7, 14, and 30 days; and 3, 6, and 12 months.
- Added AI memory policy controls with recommended memory budget, retention window, warning threshold, and auto-prune guidance.

### Security
- Added regression coverage proving model credentials, operator input text, answers, provider payloads, and local runtime URLs are not returned by the governance surfaces.

## [0.102.0] - 2026-06-20
### Added
- Added `/api/assistant/bdd-suggestions` to derive human-reviewable Gherkin candidates from prompt-free assistant interactions, feedback, and closed-loop findings.
- Added regression and BDD coverage proving the suggestion endpoint does not expose operator input text, answer text, provider payloads, credentials, or runtime file writes.

## [0.101.0] - 2026-06-20
### Added
- Added prompt-free session-aware follow-up context for `/api/chat`, including prior turn count, parent match state, category counts, and evidence counts without returning raw prompt or answer text.
- Added actor-isolated regression coverage for same-session continuity, cross-session isolation, and parent-message miss behavior.

## [0.100.0] - 2026-06-20
### Added
- Added a gated Ollama-compatible local model adapter for private edge deployments, with admin policy, local runtime approval, operator identity, grounding, and eval gates.
- Added local-runtime regression tests proving no authorization header, secret value, provider response body, or local runtime URL is returned in customer responses.

### Changed
- Updated AI routing and model benchmark evidence so configured local models are distinguished from runtime-approved local models.

## [0.99.0] - 2026-06-20
### Added
- Added prompt-free per-answer self-evaluation to `/api/chat` and `/api/assistant/workbench`, with grounded-claims, citation, actionability, A2A, HITL, confidence, route, and privacy gates.
- Added assistant quality and coworker-quality evidence for answer self-evaluation without raw prompt, answer-text, provider-payload, secret, or local-path storage.

### Changed
- Updated the Workbench UI to show a compact Answer Review row instead of raw review data.

## [0.98.0] - 2026-06-20
### Fixed
- Fixed visual QA evidence parsing so current browser reports using `passed: true`, `passed_count`, and `live_version` are accepted instead of marked stale.
- Removed customer-release test dependency on non-delivery agent governance documents.

### Changed
- Updated the drift-control owner decision to reflect the closed release SLA gap and PASS drift review while keeping production owner signoff separate.

## [0.97.0] - 2026-06-20
### Added
- Added `/api/assistant/coworker-quality` as a prompt-free quality ladder for coworker-grade assistant readiness, with owner-agent actions, SLA gap evidence, and explicit no-parity claim until all gates pass.
- Added AI Assurance UI rendering for the coworker quality ladder without raw JSON or sensitive instruction exposure.

### Changed
- Extended AI assurance evidence with coworker quality score and gap metrics so PM, release, QA, and UI agents can coordinate the next actions.

## [0.96.0] - 2026-06-20

### Added
- Added a prompt-free assistant continuity brief to `/api/assistant/workbench`, including owner handoff, A2A next hop, approval state, top actions, and chart evidence.
- Added first-screen workbench rendering for the continuity brief so operators see the next controlled action without opening raw API views.

### Changed
- Reduced assistant action-card noise by rendering customer-safe evidence labels instead of raw endpoint strings in the workbench action list.

## [0.95.0] - 2026-06-20

### Added
- Added durable, prompt-free assistant session and tool-proposal state so prepared HITL actions survive workbench refreshes.
- Added compact right-rail assistant proposal cards with pilot-setup guidance and customer-safe evidence labels.

### Changed
- Updated assistant interaction evidence to expose prepared proposal counts without returning operator input text, provider payloads, or tool execution.

## [0.94.0] - 2026-06-20

### Added
- Added audited assistant tool-proposal preparation so coworker recommendations become HITL-bounded action records without executing operational writes.

### Changed
- Updated assistant workbench action cards and the right-rail action queue with Prepare controls tied to A2A, MCP boundary, audit, and closed-loop evidence.

## [0.93.0] - 2026-06-20

### Security
- Redacted public audit, access-assignment, agent playbook, operations-evidence, and dashboard-report surfaces while preserving authenticated admin/operator detail views.

### Added
- Added public-surface redaction regression coverage for control-plane markers, actor identities, server paths, and token-like data.

### Changed
- Kept operations summaries customer-safe by redacting last-audit actor and raw detail metadata.

## [0.92.0] - 2026-06-20

### Added
- Added prompt-free assistant session lifecycle metadata to `/api/chat` and `/api/assistant/workbench`.
- Added HITL-bounded application tool proposals with A2A schema and MCP boundary evidence.

### Changed
- Updated the cockpit right-rail assistant to render the grounded answer, confidence, evidence count, and next action in place.

## [0.91.0] - 2026-06-20

### Added

- Added canonical A2A message envelopes to agent traces with customer-safe payload, trace ID, schema version, and A2A message metadata.
- Added compact Visual QA evidence to the UI/UX quality gate so screenshot/report coverage is visible without exposing local paths.

### Changed

- Updated orchestration evidence to score canonical A2A envelope coverage alongside ADR, RBAC, HITL, trace, and eval gates.

## [0.90.2] - 2026-06-20

### Fixed

- Removed customer-unsafe local Windows fallback paths from the release-builder regression tests so copied customer bundles can pass the clean-room local-path scan.

## [0.90.1] - 2026-06-20

### Fixed

- Reassigned AI model benchmark alert and recovery task ownership from the stale `monitoring_alert_agent` ID to registered `alert_recovery_agent`, with regression coverage against `/api/admin/agents`.
- Enforced six-hour drift-control evidence in the customer release builder so unresolved KPI/SLA drift blocks customer release packaging unless an explicit owner/customer decision artifact exists.

## [0.90.0] - 2026-06-20

### Added

- Added a coworker-grade assistant response package to `/api/chat` and `/api/assistant/workbench`, including prompt-free intent, citations, task graph, tool plan, A2A handoff, memory policy, escalation boundary, platform readiness, and quality rubric.

### Changed

- Updated assistant evidence tests so the product proves operational coworker behavior without storing operator input text or enabling provider runtime by default.

## [0.89.4] - 2026-06-20

### Fixed

- Locked the hidden legacy detailed workspace closed so cockpit/sidebar navigation cannot reopen the old long-form workspace below the dashboard.
- Contained Advanced Settings inside the cockpit context with a bounded scroll area to prevent visual overlap with the action rail and footer.

### Changed

- Strengthened the UI/UX quality gate and regression tests to block future releases when legacy workspace auto-open behavior or uncontained settings panels return.

## [0.89.3] - 2026-06-20

### Added

- Added operator-gated `POST /api/project/drift-control/run` so the six-hour PM/release-auditor review records source commit, KPI/SLA state, checked sources, audit evidence, and closed-loop findings.
- Added dashboard drift-control action buttons and review-window/source-commit fields so the cadence is operational from the UI instead of only documented.
- Added Docker `AGENTIOT_SOURCE_COMMIT` build argument support so runtime drift evidence can identify the source commit inside container builds.

### Changed

- Extended drift-control customer documentation, BDD, and acceptance checks with recorded PASS/FAIL evidence requirements.

## [0.89.2] - 2026-06-19

### Changed

- Moved Advanced Settings into the active shell context so Settings no longer opens an overlapping fixed panel above the cockpit and legacy workspace.
- Limited reference cockpit data to true empty-state preview only, allowing live pilot data to drive KPI and action surfaces.
- Added UI/UX quality gates for single-surface navigation and live action-queue behavior.

### Fixed

- Fixed stale right-rail action cards by filtering resolved alerts and approved recovery proposals before rendering operator actions.

## [0.89.1] - 2026-06-19

### Changed

- Scoped Evidence-route governance card priority so `/evidence` starts with six-hour drift control while `/tests` starts with the operational QA/Test workspace.
- Refreshed runtime QA evidence by recording the bounded 24-case QA challenge after the 60-minute continuous mission and 60-round assistant Q/A evidence.

### Fixed

- Fixed the Tests menu visual ordering regression that placed drift/release cards ahead of QA evidence.

## [0.89.0] - 2026-06-19

### Added

- Added `AGENTIOT_OPERATOR_TOKEN_FILE` and `AGENTIOT_ADMIN_TOKEN_FILE` support so runtime credentials can be mounted from secret files instead of stored in Git or printed in command output.
- Added tests proving token-file readiness and operator write authorization without returning token values.

### Changed

- Updated release gap closure guidance to prefer runtime token files, token environment variables, or OIDC identities before running release evidence missions.
- Updated Claude/Gemini entrypoints and document/file indexes so the six-hour PM and release-auditor KPI/SLA drift-control rule is mandatory for all contributor agents.
- Clarified README, acceptance, project coordinator, and internal index wording so six-hour drift-control FAIL states explicitly block customer release mirroring.
- Aligned customer document headers and package metadata with release version 0.89.0.
- Corrected release mission agent-autopilot scoring to use coverage against the target agent count instead of a fixed multiplier that capped seven-agent missions at 98%.
- Corrected assistant decision-readiness scoring so resolved, grounded runtime evidence can reach the 99.99 SLA gate while open operational risk still lowers readiness.

### Security

- Kept token values out of API responses, docs, logs, tests, and customer-safe deliverables while enabling Docker-first release mission evidence.
- Added regression coverage that rejects prompt-contract text containing private paths or unsafe provider-routing payload wording.

## [0.88.0] - 2026-06-19

### Added

- Added `/api/release/gap-closure-console` to map open release KPI/SLA gates to owner agents, A2A next hops, required scope, auth readiness, safe run endpoints, and acceptance evidence.
- Added a Release Gap Closure card to the Delivery/Evidence shell so reviewers see executable release actions instead of only the blocked SLA number.
- Added score-input and blocking-gate breakdowns to release mission summaries so release KPI math is traceable without reading source code.

### Changed

- Updated release evidence links, README/API indexes, BDD coverage, and acceptance documentation with the new gap-closure console.

### Security

- Kept release execution operator-gated and returned only placeholder commands, auth readiness booleans, and customer-safe evidence links without credential values.

## [0.87.0] - 2026-06-19

### Added

- Added `/api/ai/assurance-console` to combine assistant quality, RAG coverage, A/B route comparison, model benchmark fit, release evidence, and owner-assigned AI remediation actions.
- Added an AI Assurance Console card to the Intelligence shell contexts so AI quality blockers are visible in the dashboard instead of requiring raw JSON review.
- Added `/api/project/drift-control` and a Delivery/Evidence shell card for the mandatory six-hour project delivery and release compliance KPI/SLA drift-control review.

### Changed

- Updated README, BDD, acceptance evidence, AI provider, RAG, and phase documentation with the new AI assurance gate.

### Security

- Kept the assurance response prompt-free and secret-free, with only customer-safe local evidence links and managed route identifiers.

## [0.85.0] - 2026-06-19

### Added

- Added release evidence execution controls so operators can run the release mission from the Evidence cockpit context with token-gated approval and assistant-round control.
- Added `/api/release/evidence-console.execution_controls` with run endpoint, required inputs, operator scope, readiness, and next action metadata.

### Changed

- Extended the Release Evidence Console UI from a passive evidence report into an operator action surface while keeping write execution behind `X-Operator-Token`.

## [0.84.0] - 2026-06-19

### Added

- Added `/api/release/evidence-console` with mission status, gate owners, SLA gap, charts, customer-safe evidence links, and privacy posture.
- Added a Release Evidence Console card to the cockpit delivery/evidence contexts so reviewers can act on release gaps without opening raw JSON.

### Changed

- Extended Phase 2 customer evidence and acceptance documentation with the release evidence console gate.

### Fixed

- Fixed cockpit initial data refresh by keeping the refresh-status helper in global script scope so shell evidence cards populate after page load.

## [0.83.0] - 2026-06-19

### Added

- Added stricter browser-visual cockpit fidelity hooks for the UI/UX auditor, including a time-range control, refresh status, and first-screen visual QA marker.
- Added richer operational map evidence with status rings, pulse markers, region labels, and route lines so the cockpit is less sparse and closer to the requested industrial reference view.

### Changed

- Tightened `/api/ui/quality-gate` with map-quality and browser-visual QA metrics so future frontend work cannot pass with only static DOM placeholders.

## [0.82.0] - 2026-06-19

### Added

- Added `/cockpit` as a browser-safe dashboard route so operators see the cockpit shell instead of a JSON or 404 API response when using the natural cockpit URL.
- Added `/api/rag/quality-console` with retrieval probes, grounding gaps, action owners, chart data, privacy posture, and customer-safe evidence links.
- Added the RAG Quality Console to the Insights/Assistant shell contexts so RAG quality can be reviewed without raw JSON navigation.

### Security

- Kept RAG quality output free of provider payloads, local paths, contact data, and internal instruction text.

## [0.81.0] - 2026-06-19

### Added

- Added `/api/admin/agents/prompt-contracts` and `/api/admin/agents/{agent_id}/prompt-contract` so admins can review and update customer-safe managed instruction contracts for each section agent.
- Added the Agent Prompt Contract Console to the admin UI with editable-field, storage-policy, A2A, ADR, evaluation, and evidence visibility without raw JSON navigation.

### Security

- Reject prompt-contract updates containing contact data, credential-like text, private paths, or provider-payload wording before audit storage.

## [0.80.0] - 2026-06-19

### Added

- Added `/api/assistant/workbench` as a prompt-free Copilot-style operator package combining assistant response, RAG grounding, model routing, A2A trace, HITL actions, quality gates, and chart evidence.
- Added the Assistant Copilot Workbench card to the Intelligence/Assistant shell so operators can inspect decision-grade AI evidence without opening raw JSON.

## [0.79.0] - 2026-06-19

### Added

- Added `/api/evidence/action-board` to convert closed-loop findings, QA gaps, and agent evidence into owner-assigned actions with priority, A2A next hop, acceptance gate, and chart data.
- Added the Evidence Action Board to the operational Evidence/Memory workspace so reviewers can act on findings without opening raw JSON.

## [0.78.0] - 2026-06-19

### Added

- Added an AI Routing Control Console inside Advanced Settings so admins can inspect active profile, provider, model, runtime gate, candidate routes, owner agents, and evidence actions without opening raw JSON.
- Added first-class Gemini provider routing through the existing credential, runtime approval, grounding, and operator gates using the Gemini generateContent REST boundary.


## [0.77.0] - 2026-06-19

### Added

- Added a token-gated Run Agent Autopilot action inside the Agent Control Plane Evidence shell so Admin can generate A2A task evidence without opening legacy panels.
- Extended the orchestration control plane with run/finding coverage, latest mission status, and a data-backed ready state after autopilot evidence covers every agent row.

## [0.76.0] - 2026-06-19

### Added

- Added an Agent Control Plane Evidence card to the Admin shell so operators can see orchestration maturity, release gate, A2A edge count, ADR gate count, and protocol evidence without opening raw JSON.
- Extended `/api/orchestration/evidence-matrix` with customer-safe control-plane metrics and protocol evidence for ADR, A2A, RBAC, HITL, Trace, and Eval gates.

## [0.75.0] - 2026-06-19

### Added

- Added a token-gated Run QA Challenge action inside the Operational Test Workspace so operators can execute bounded QA evidence without leaving the cockpit shell.
- The shell QA action refreshes workspace metrics after completion and records the run through the existing `/api/qa/challenge-runs` evidence path.
- Added a visible Operator token field in the Tests workspace so the QA action is usable without opening hidden access settings.


## [0.74.0] - 2026-06-19

### Added

- Added a visible Operational Test Workspace inside the Tests shell context with UI/UX score, ready gate count, QA runs, continuous QA coverage, gate evidence, and mission evidence.
- Added a visible Operational Evidence Workspace inside the Evidence and Memory shell contexts with endpoint evidence, report counts, audit counts, and closed-loop finding evidence.
- Extended the UI/UX Quality Auditor gate so missing Reports, Tests, or Evidence workspaces are detected before release.

## [0.73.0] - 2026-06-19

### Added

- Added a visible Operational Reports Workspace inside the Reports/Forecasts shell context with chart counts, report counts, agent runs, AI evals, chart summaries, and report evidence.
- Kept Reports menu content inside the operational cockpit instead of requiring users to inspect hidden legacy panels or raw API JSON.

## [0.72.0] - 2026-06-19

### Added

- Added an agent-owned SLA remediation plan to Release Mission Control with P0/P1 actions, A2A next hops, acceptance gates, and evidence endpoints.
- Added release remediation chart/report evidence so dashboard reports show the action plan behind the 99.99 SLA gap.
- Added the SLA Remediation Plan table to the dashboard release mission panel without exposing operator input text or provider payloads.

## [0.71.0] - 2026-06-19

### Changed

- Release Mission Control now reports explicit 99.99 SLA target, actual KPI score, gap, and pass/fail status.
- Release mission run status now remains `review_required` when quality gates pass but the 99.99 SLA target is not met.
- Shell navigation now keeps agent, report, test, and evidence menu actions inside the operational cockpit context instead of jumping to legacy detail sections.
- Tightened the cockpit visual polish for the GreeNovaX reference layout, including dotted map treatment and right-rail action queue spacing.

### Added

- Added a release mission SLA chart and dashboard metric so operators can see quality gaps without reading raw JSON.

## [0.70.0] - 2026-06-19

### Added

- Added Release Mission Control to run baseline AI evaluation, assistant Q/A challenge, agent autopilot, and continuous QA mission from one operator-gated command.
- Added `/api/release/mission` and `/api/release/mission/run` for release-gate status, charts, privacy controls, and evidence links.

### Changed

- Dashboard reports now include release mission gate evidence and a release-mission chart.

## [0.69.0] - 2026-06-19

### Added

- Added `/api/assistant/decision-brief`, a prompt-free operational decision package with readiness score, risk register, A2A trace, ADR alignment, model routing, RAG grounding, HITL boundary, chart metadata, and customer-safe evidence links.
- Added the Assistant Decision Brief panel to the dashboard and included its chart/report evidence in `/api/reports/dashboard`.

### Security

- Kept the decision brief read-only: no raw prompt storage, no raw answer storage, no provider payload storage, and no external model call.

## [0.68.0] - 2026-06-19

### Changed

- Tightened the live cockpit toward the supplied GreeNovaX reference screenshot with a semi-arc readiness gauge, right-rail queue geometry, active menu accent, and footer status strip.
- Kept the landing page operational and concise without adding long explanatory content or extra customer-facing prompt material.

## [0.67.0] - 2026-06-19

### Added

- Added route-aware cockpit deep-linking so `/assets`, `/reports`, `/settings`, and every primary sidebar URL opens the matching operational command surface instead of a generic cockpit state.
- Added a UI/UX quality gate metric and release gate for direct menu URL routing.

## [0.66.0] - 2026-06-19

### Added

- Added `/api/agents/autopilot/run`, an operator-gated mission that activates every enabled section agent once, stores A2A traces, evidence links, audit events, and a closed-loop `agent_autopilot` finding.
- Added Agent Autopilot Mission controls and KPI cards to the Agent Orchestration Admin dashboard.
- Added agent autopilot mission evidence to dashboard reports and chart datasets.

### Changed

- Agent run IDs now include a short random suffix to avoid collisions when multiple section agents run in the same millisecond.

## [0.65.0] - 2026-06-19

### Added

- Added `assistant_qa_60`, a stored 60-round assistant Q/A challenge that exercises the real assistant, RAG, A2A, and evidence route without provider calls or raw prompt/answer storage.
- Added assistant Q/A challenge status to assistant quality, QA evidence, dashboard reports, chart datasets, and the Admin AI evaluation controls.

### Changed

- QA evidence readiness now requires the bounded 60-round assistant Q/A challenge in addition to the QA challenge and continuous mission gates.

## [0.64.1] - 2026-06-19

### Fixed

- Activated the customer-safe reference cockpit preview when the live runtime has no asset, device, telemetry, alert, or recovery records, so the first screen shows the contracted Operations Cockpit value instead of a zero-value empty state.
- Kept real operational API counters unchanged while using the preview only for the first-screen visual cockpit.

## [0.64.0] - 2026-06-19

### Added

- Added `/api/ai/model-benchmarks`, a customer-safe matrix for task-level AI model routing, owner agents, runtime readiness, candidate routes, A2A/ADR/eval gates, and evidence links without external provider calls.
- Added the AI Model Benchmark Matrix to the Intelligence/Admin dashboard shell and detailed workspace so operators can review route fit without opening raw JSON.

### Changed

- Included model benchmark evidence in dashboard reports and AI section ownership metadata.

## [0.63.0] - 2026-06-19

### Changed

- Tightened the live cockpit toward the supplied GreeNovaX reference with a compact horizontal brand asset, distinct SVG sidebar navigation icons, and full-width active menu rows.
- Added regression coverage for the reference-logo asset and navigation-icon rendering so future UI work does not fall back to generic dot/square menu marks.

## [0.62.0] - 2026-06-19

### Added

- Added `/api/architecture/adr`, a customer-safe architecture decision register
  for ADR, A2A, HITL, RBAC, trace, eval, and prompt-free evidence governance.
- Added a visible ADR Governance Register to the Agent Orchestration shell so
  admins can inspect architecture decisions, owners, standards, evidence links,
  and acceptance gates without opening raw JSON.
- Added regression coverage for the typed ADR register endpoint and dashboard
  rendering hooks.

## [0.61.1] - 2026-06-19

### Fixed

- Replaced the visible shell Assistant Interaction Ledger table with compact
  responsive operational entries so the Memory context remains readable on
  desktop and mobile.
- Kept the prompt-free assistant evidence visible in the cockpit context while
  preserving the full hidden-detail table for regression and contract tests.

## [0.61.0] - 2026-06-19

### Added

- Added `/api/assistant/interactions`, a prompt-free assistant interaction ledger
  that records prompt hashes, categories, response status, route, evidence
  counts, HITL boundary, outcome, latency, and bounded actor labels without raw
  prompts or answer text.
- Added the Assistant Interaction Ledger panel to the admin dashboard and wired
  it into the assistant quality report gates.
- Added regression and BDD coverage for prompt-free assistant Q and A evidence.

## [0.60.0] - 2026-06-19

### Fixed

- Added customer-facing dashboard route aliases such as `/dashboard`,
  `/overview`, `/assets`, `/reports`, and `/settings` so operators who open
  UI paths see the cockpit HTML instead of FastAPI `{"detail":"Not Found"}`
  JSON.
- Kept `/api/...`, `/healthz`, and `/readyz` as JSON endpoints so API and
  Docker health checks remain unchanged.

## [0.59.0] - 2026-06-19

### Changed

- Polished the live cockpit first viewport against the supplied GreeNovaX reference: typography, spacing, KPI cards, readiness panels, map panel, action rail, assistant controls, and footer.
- Kept the legacy detailed workspace away from the customer-facing first screen so the root page stays operational instead of long-form/non-delivery.

### Fixed

- Fixed collapsed donut visuals and raw glyph-style sidebar icons that made the dashboard look unfinished in browser screenshots.

## [0.58.0] - 2026-06-19

### Added

- Added dashboard section ownership evidence to `/api/orchestration/evidence-matrix`, mapping each primary dashboard section to an accountable agent, A2A links, ADR id, QA lane, eval profile, and customer-safe evidence endpoints.
- Added a Dashboard Section Ownership table in the Agent Orchestration Admin area so operators can inspect section accountability without opening raw JSON.

### Changed

- Updated the customer Agent Orchestration Architecture documentation and document index to include dashboard section ownership evidence.

## [0.57.0] - 2026-06-19

### Fixed

- Fixed slow first-screen dashboard hydration by loading the cockpit-critical APIs in parallel before the secondary workspace/admin/report panels.

### Changed

- Changed the live cockpit refresh sequence so the GreeNovaX reference KPIs, readiness gauge, action queue, and assistant state render immediately after the core operational data is available.

## [0.56.0] - 2026-06-19

### Added

- Added `/api/qa/evidence-report` for a single operational QA report that joins challenge runs, continuous QA mission evidence, A/B comparisons, stress bounds, standards lanes, gaps, and release evidence links.
- Added a QA Evidence Report panel in Advanced Settings so operators can review test readiness without reading raw JSON.
- Added bootstrap-aware demo-estate cockpit metrics so the first viewport can match the supplied GreeNovaX operational reference when demo data is active.

### Changed

- Changed the first-screen cockpit renderer to format demo-scale KPI, readiness, queue, asset status, and asset type values while preserving runtime API truth in detailed workspace sections.

## [0.55.0] - 2026-06-19

### Added

- Added `/api/assistant/quality-report` for an operational assistant quality score, SLA target, route/layer split, RAG/runtime grounding, A2A trace, eval-run state, closed-loop blockers, recommendations, and evidence links.
- Added an Admin dashboard Assistant Quality Report panel that renders the quality gates and required actions without exposing operator input text, secrets, or restricted artifacts.

### Fixed

- Added no-store cache headers for customer-facing HTML pages so operators see the latest deployed cockpit instead of a stale browser-cached UI.

## [0.54.0] - 2026-06-19

### Added

- Added cockpit-grade visual polish for the first viewport: SVG KPI icons, chart grid labels, map SVG, status/type legends, and structured action queue items.

### Changed

- Kept command-surface cards away from the default cockpit view so the first viewport matches the supplied GreeNovaX operational cockpit reference more closely.
- Reworked first-screen chart and rail layout to reduce clutter and keep menu-specific operational content available only when a related menu is selected.

## [0.53.0] - 2026-06-19

### Added

- Added admin-managed agent analysis controls for each dashboard agent: analysis profile, model route, trace policy, and evaluation gate.
- Added A2A trace metadata and task responses that expose the selected agent profile, route, and trace policy without storing prompts or credentials.
- Added `/api/orchestration/evidence-matrix` and Agent Admin matrix UI to join agent controls, A2A trace, ADR, closed-loop findings, menu anchors, and evidence endpoints.
- Added Agent Admin UI controls and regression tests for profile routing, trace/eval governance, and unsupported profile rejection.

### Changed

- Connected the agent registry control plane to AI analysis profile, provider policy, task, and trace/eval standards endpoints.

## [0.52.0] - 2026-06-18

### Added

- Added reference-cockpit fidelity controls for the first viewport: notification badge, help/display/settings controls, user avatar, assistant input, compact action queue, and dotted map surface.
- Added KPI trend signals, comparison text, queue severity chips, timestamps, and assistant prompt handling to make the cockpit more operational and less sparse.
- Added UI/UX quality gate metrics for topbar controls, right-rail controls, KPI trend signals, reference cockpit fidelity, and industrial cockpit density.

### Changed

- Tightened the dashboard shell layout, spacing, right rail, KPI cards, readiness chart area, and map panel toward the supplied GreeNovaX cockpit reference.

## [0.51.0] - 2026-06-18

### Added

- Added a first-screen cockpit context surface so sidebar menu actions render concise operational cards instead of opening long workspace sections.
- Added UI/UX quality metrics for shell context targets and menu-owned command cards.
- Added a menu-context ownership quality gate to keep primary navigation actionable and free of raw JSON destinations.

### Changed

- Changed cockpit shell navigation to keep operators in the first-screen command center while preserving detailed workspace access for legacy in-page links.

## [0.50.0] - 2026-06-18

### Added

- Added `/api/qa/continuous-mission` for the 60-minute continuous QA mission plan and operator-recorded release challenge evidence.
- Added Advanced Settings controls and dashboard report/chart evidence for Smoke, API, A2A, ADR, Visual, Stress, RAG, Log, Security, License, and A/B QA lanes.
- Added closed-loop findings and audit events for continuous QA mission rehearsals without large datasets or credential exposure.

## [0.49.0] - 2026-06-18

### Added

- Added first-screen Advanced Settings quick controls for activating an AI analysis profile and provider runtime policy through audited admin endpoints.
- Added regression and BDD coverage for quick AI route updates without credential exposure.

### Fixed

- Connected the visible cockpit gear button to the Advanced Settings panel so the first-screen control can be opened without navigating to raw API output.

## [0.48.0] - 2026-06-18

### Added

- Added a cockpit assistant action that runs an audited agent review through `/api/agents/tasks`, refreshes agent evidence, and opens the Agent Admin review section.
- Added regression coverage for cockpit-launched agent tasks and closed-loop evidence findings.

## [0.47.1] - 2026-06-18

### Fixed

- Made cockpit shell routing update the active menu state correctly and scroll immediately to deep workspace sections.

## [0.47.0] - 2026-06-18

### Added

- Added operational shell navigation routing so cockpit menu items and assistant shortcuts open the matching detailed workspace section.
- Added customer-safe BDD and contract tests for grouped menu routing, assistant actions, and raw JSON prevention.

## [0.46.4] - 2026-06-18

### Fixed

- Removed inherited footer spacing from the cockpit footer and compacted the first-screen dashboard panels for a cleaner operational viewport.

## [0.46.3] - 2026-06-18

### Fixed

- Kept the cockpit footer inside the first desktop viewport by constraining the shell height and moving overflow into the sidebar, main panel, and action rail.

## [0.46.2] - 2026-06-18

### Fixed

- Made the industrial cockpit shell full-viewport on desktop so the live site matches the approved reference direction without outer page margins.
- Kept the copyright, version, year, and live status in the cockpit footer while avoiding repeated footer text below the detailed workspace.

## [0.46.1] - 2026-06-18

### Fixed

- Corrected the industrial cockpit shell grid so the sidebar, topbar, central operations cockpit, right action rail, and footer match the approved visual direction.
- Improved mobile shell navigation alignment so the active cockpit item does not stretch against grouped menu sections.

## [0.46.0] - 2026-06-18

### Changed

- Redesigned the dashboard first screen into a quieter industrial operations cockpit with grouped navigation, compact first-viewport KPIs, and progressive disclosure.
- Added dashboard view filtering so Operate, Agents, Intelligence, and Delivery menus show only relevant management sections instead of exposing the full page at once.
- Moved operator/admin token fields into a compact access disclosure to reduce visual noise on the primary surface.

### Added

- Added regression coverage for grouped dashboard navigation, cockpit panel structure, and workspace view filtering hooks.

## [0.45.2] - 2026-06-18

### Fixed

- Improved the mobile Command Center layout so KPI and command-card tables render as readable stacked action cards instead of clipped horizontal table columns.
- Added table cell labels for responsive dashboard rows to support visual audit and mobile readability checks.

## [0.45.1] - 2026-06-18

### Fixed

- Removed customer-facing non-delivery wording from A2A protocol metadata, UI/UX quality payloads, and release evidence strings.
- Added release-safety regression coverage for Command Center and dashboard report payloads.
- Added `/api/operations/command-center` to README, Core API baseline, and EN/DE acceptance checklists.

### Changed

- Added the mandatory frontend visual-audit rule to non-delivery UI/UX auditor governance.

## [0.45.0] - 2026-06-18

### Added

- Added `/api/operations/command-center` as the menu-owned operational command surface.
- Added the Operational Command Center dashboard section with state, readiness, active risk, next action, KPI table, and agent-owned action cards.
- Added Command Center chart/report evidence so management review focuses on operational decisions instead of long static text.
- Added regression coverage for Command Center API, reports, menu section, and safe rendering hooks.

### Changed

- Dashboard flow now places actionable operations before charts, so menu content leads to task ownership, evidence endpoints, and next operator action.
- Version metadata advanced to `0.45.0` for the operational command-center release slice.

## [0.44.0] - 2026-06-18

### Added

- Added `/api/rag/knowledge-base`, `/api/rag/search`, and `/api/admin/rag/knowledge/{doc_id}` for customer-safe RAG knowledge management.
- Added the RAG Knowledge Center dashboard section with search, compact evidence tables, admin update controls, and assistant knowledge grounding.
- Added RAG knowledge coverage chart/report evidence and AI evaluation gate coverage.
- Added EN/DE RAG Knowledge Center documentation and regression tests.

### Changed

- Assistant responses now include linked knowledge grounding alongside runtime evidence and A2A trace data.
- Dashboard AI content is grouped into operational menu sections instead of exposing raw API output.

## [0.43.0] - 2026-06-18

### Added

- Added `/api/qa/challenge-runs` for bounded operational QA challenge execution and stored run evidence.
- Added the Advanced Settings gear panel with active profile, reasoning layer, answer layer, QA KPI, challenge form, and latest run table.
- Added QA challenge KPI chart and report package evidence so management review can see actionable readiness, not long raw output.
- Added EN/DE QA Challenge Harness documentation and BDD coverage.

### Changed

- Dashboard management content is now grouped under section menus and Advanced Settings instead of pushing operators toward raw JSON views.

## [0.42.0] - 2026-06-18

### Added

- Added `/api/ui/quality-gate` with measurable menu, chart, responsive, accessibility, and data-presentation gates.
- Added the dashboard UI/UX Quality Gate panel so the primary menu stays inside the operational interface instead of opening raw JSON.
- Added the project-governance-only `UI_UX_Quality_Auditor` profile for visual QA, menu behavior, chart readability, and operational data presentation.
- Added UI/UX quality chart, report package evidence, and acceptance evidence gate.

### Changed

- Dashboard quality reporting is now action-oriented: score, ready gates, raw JSON menu count, owner agent, and blocking items.
- Acceptance evidence now treats UI/UX quality as a release gate rather than a descriptive note.

## [0.41.0] - 2026-06-18

### Added

- Added admin-managed AI Analysis Profiles for routing layer, answer layer, RAG mode, model strategy, active profile selection, and evaluation gate control.
- Added prompt-free Closed-Loop Evidence Findings for assistant chats, agent tasks, and AI evaluation runs.
- Added `/api/admin/ai/analysis-profiles`, `/api/admin/ai/analysis-profiles/{profile_id}`, and `/api/evidence/findings`.
- Added dashboard tables and controls for analysis profiles and closed-loop findings.
- Added dashboard charts and reports for analysis-profile readiness and evidence-finding volume.

### Changed

- AI routing now exposes the active analysis profile plus separate reasoning and answer layers.
- FastAPI lifecycle management now uses the current lifespan context manager pattern instead of deprecated `on_event` handlers.
- Source and test headers now use the required `Dr. Babak Sarkhpour, with AI assistance` authorship wording.

## [0.40.1] - 2026-06-18

### Fixed

- Made production, owner approval, delivery, and API evidence panels full-width so operational evidence tables remain readable in dashboard navigation.
- Added regression coverage that keeps key navigation anchors attached to the intended dashboard sections.

## [0.40.0] - 2026-06-18

### Added

- Added admin-managed Production Readiness Controls with audited state, owner label, evidence, and contact-data rejection.
- Added `/api/admin/production/readiness-controls` and `/api/admin/production/readiness-controls/{control_id}`.
- Added dashboard Update Production Readiness form and source/owner metadata in the Production Hardening panel.
- Added UI/UX Experience Auditor section agent for menu behavior, visual hierarchy, chart readability, and raw-JSON navigation prevention.
- Added API Evidence Reference as plain dashboard evidence text instead of primary navigation links.

### Changed

- Primary dashboard menus now navigate to HTML dashboard sections instead of opening raw JSON endpoints.
- Production hardening status now reflects admin-recorded readiness-control evidence while preserving customer signoff as a separate gate.

## [0.39.0] - 2026-06-18

### Added

- Added admin-managed Owner Decision Board for production-owner review decisions.
- Added `/api/admin/production/decisions` and `/api/admin/production/decisions/{decision_id}` with audit evidence and contact-data rejection.
- Added dashboard Owner Decision Board table and Update Owner Decision form.
- Added regression coverage for owner decision updates, audit events, contact-data rejection, and explicit owner-approved transition.

### Changed

- Production approval package now reflects recorded owner decisions while preserving formal customer acceptance as an explicit external gate.

## [0.38.0] - 2026-06-18

### Added

- Added admin-managed user access assignments with subject ID, role, scopes, status, bounded note, and audit evidence.
- Added `/api/admin/access/users` and `/api/admin/access/users/{subject_id}` for customer-safe access assignment review and updates.
- Added dashboard User Access Assignments table and Update User Access form.
- Added regression coverage for assignment creation, access-policy exposure, audit events, and contact-data rejection.

### Changed

- Public access policy now includes bounded user assignment records alongside role policies and identity-provider readiness.

## [0.37.0] - 2026-06-18

### Added

- Added admin-managed agent playbook fields for operating brief, A2A handoff policy, and quality-gate policy.
- Added dashboard form support that preloads the selected agent playbook before audited admin updates.
- Added regression coverage for customer-safe playbook exposure and audited admin playbook changes.

### Changed

- Agent Registry now shows each agent's function, operating brief, instruction template, handoff policy, quality-gate policy, and A2A links.
- Phase 2 documentation now treats agent playbooks as customer-facing product controls, separate from non-delivery build governance.

## [0.36.0] - 2026-06-18

### Added

- Added `/api/agents/section-reports` with per-agent readiness, runtime records, evidence links, connected agents, latest run references, next actions, and A2A quality gates.
- Added dashboard Agent Section Reports table for admin and delivery review.
- Added dashboard report package evidence for agent section reports.
- Added regression coverage for agent section report API, root-page hooks, and OpenAPI exposure.

### Changed

- Agent orchestration now exposes operational section evidence in addition to the visual A2A map and executable task runs.

## [0.35.0] - 2026-06-18

### Added

- Added read-only first-screen assistant preview that renders the structured diagnosis package on page load.
- Added a separate manual chat helper so diagnosis requests can work without the write-action token gate while still using an operator token when explicitly provided.
- Added regression coverage for automatic assistant preview hooks and the token-safe manual chat path.

### Changed

- The homepage now shows assistant route, plan, evidence, A2A trace, confidence, and next actions without requiring the first user click.

## [0.34.0] - 2026-06-18

### Added

- Added structured copilot-style assistant output with plan, evidence links, selected agent route, A2A trace, next actions, confidence label, and human-approval flag.
- Added homepage assistant panels for route, confidence, approval, plan, evidence, A2A trace, and next actions.
- Added regression coverage for structured assistant API fields and browser rendering hooks.

### Changed

- `/api/chat` now returns operational evidence metadata instead of only a single answer string.
- Customer AI documentation and acceptance gates now describe structured assistant output as a delivery requirement.

## [0.33.0] - 2026-06-18

### Added

- Added a native SVG Agent A2A orchestration map to the admin console.
- Added admin summary metrics for agent count, A2A link count, approval-required agents, and ADR/A2A standard state.
- Added regression coverage for the visual agent map hooks and admin graph rendering functions.

### Changed

- Agent architecture is now reviewable as both a table and a visual map in the customer-facing admin surface.

## [0.32.0] - 2026-06-18

### Added

- Added native SVG chart rendering for dashboard report datasets without adding frontend dependencies.
- Added dashboard report package summary metrics for chart count, report count, agent runs, and AI evaluation runs.
- Added regression coverage for visual chart metadata and rendered SVG chart hooks.

### Changed

- Charts and reports now provide a more useful first-screen review surface instead of only table rows.

## [0.31.0] - 2026-06-18

### Added

- Added `/api/delivery/evidence-pack` with acceptance score, gate summary, quality matrix, reports, operations, agent orchestration, access policy, AI routing/evaluations, final delivery, and open items.
- Added homepage Acceptance Evidence Pack and Assistant Quality Matrix panels.
- Added regression coverage for consolidated acceptance evidence and OpenAPI exposure.

### Changed

- Delivery review evidence now has one customer-safe API surface instead of requiring manual collection across individual report endpoints.

## [0.30.0] - 2026-06-18

### Added

- Added scope-specific enforcement for device, telemetry, recovery, agent-task, AI-evaluation, and admin control-plane writes.
- Added support for custom bearer roles that are limited to explicitly declared scopes.
- Added regression coverage for limited custom roles and per-area admin scope enforcement.

### Changed

- Built-in role defaults are applied only when a bearer token does not provide explicit scopes, allowing identity providers to issue narrower operational tokens.

## [0.29.0] - 2026-06-18

### Added

- Added dashboard Admin Token field and admin control forms for section-agent controls, access-role policy, and AI provider policy.
- Added optional `AGENTIOT_ADMIN_TOKEN` / `X-Admin-Token` control-plane gate for development and owner-review deployments without weakening OIDC bearer admin support.
- Added regression coverage for valid and invalid admin-token control changes and root-page admin console visibility.

### Changed

- Browser control-plane updates now create the same audited API records as direct admin API calls.

## [0.28.0] - 2026-06-18

### Added

- Added secure external AI provider runtime execution for OpenAI Responses API and Hugging Face OpenAI-compatible chat completion routes.
- Added default-off runtime gate requiring admin policy, provider credential, `AGENTIOT_AI_ALLOW_CLOUD_CALLS=true`, runtime grounding records, and authenticated operator identity before any provider call.
- Added provider runtime status in `/api/ai/routing`, `/api/chat`, homepage AI policy/routing panels, and AI evaluation evidence.
- Added regression coverage proving provider calls are skipped without operator identity and that mocked OpenAI/Hugging Face payloads do not expose credentials.

### Changed

- AI provider policy now separates configured cloud route visibility from actual model execution readiness.
- `/api/chat` can use approved external runtime routes while preserving grounded fallback and human-approval boundaries.

## [0.27.0] - 2026-06-18

### Added

- Added customer-safe AI provider policy endpoints under `/api/admin/ai/provider-policy`.
- Added local AI/agent evaluation runs under `/api/ai/evaluations/runs`.
- Added homepage AI Provider Policy and AI Evaluation Runs panels.
- Added assistant-quality chart and provider-policy evidence in dashboard reports.

### Changed

- AI routing now reflects admin-managed provider policy while keeping credentials out of responses and persistence.
- AI evaluation status now includes provider-policy and local-eval-suite gates.

## [0.26.0] - 2026-06-18

### Added

- Added audited executable agent tasks through `/api/agents/tasks` with route, A2A trace, evidence links, and human-approval flag.
- Added agent task run history in the homepage and dashboard report charts.
- Added configurable access-role policy endpoints under `/api/admin/access/roles`.
- Added EN/DE customer documentation for agent task execution and access role policy.

### Changed

- Dashboard reports now include agent task execution evidence and task-run chart data.
- Public access policy now includes default and admin-defined role policies.

## [0.25.0] - 2026-06-18

### Added

- Added dashboard section-agent registry with A2A-compatible product-local links, ADR evidence, customer-safe prompt/instruction templates, and admin control metadata.
- Added `/api/admin/agents`, admin-only `/api/admin/agents/{agent_id}`, and `/api/reports/dashboard`.
- Added homepage Charts & Reports and Agent Orchestration Admin panels with chart-ready runtime data.
- Added EN/DE agent orchestration architecture and ADR-0001 documentation.

### Changed

- Extended RBAC with `agent:read` and `agent:manage` scopes.
- Updated release scanning so customer-safe prompt/instruction templates are allowed while non-product execution material remains blocked.

## [0.24.0] - 2026-06-18

### Added

- Added optional MQTT broker subscriber status and lifecycle using the existing validated MQTT adapter boundary.
- Added `/api/adapters/mqtt/broker/status` with secret-safe broker configuration flags, TLS/auth readiness, topic filter, counters, and client-library availability.
- Added `/api/project/phases` and the homepage Phase Execution Board so Phase 1, Phase 2, Phase 3, evidence, runtime value, and next actions are visible in the operational page.
- Added EN/DE MQTT broker integration documentation and acceptance traceability.
- Added regression coverage for default-off broker status, credential secrecy, and broker-handler telemetry ingestion.

## [0.23.0] - 2026-06-18

### Added

- Added optional `AGENTIOT_BOOTSTRAP_DEMO_DATA` startup seeding for a bounded live pilot dataset.
- Added `/api/demo/bootstrap/status` so the browser and API can show whether demo records were seeded, skipped, or disabled.
- Added root-page Demo Seed status and regression coverage for default-off and enabled bootstrap behavior.

## [0.22.0] - 2026-06-18

### Added

- Added PyJWT-backed RS256/JWKS bearer validation with issuer, audience, expiry, role, and scope checks.
- Added `AGENTIOT_IDP_JWKS_URL` runtime configuration for production identity providers.
- Added EN/DE OIDC JWKS and RS256 validation documentation.
- Added regression coverage for RS256 token validation, RS256 write authorization, HS256 fallback compatibility, and JWKS URL secrecy.
- Added first-screen preview fallback counters so the operations console shows useful device, alert, and recovery context before live write actions run.

## [0.21.0] - 2026-06-18

### Added

- Added `/api/simulation/runs` for operator-approved bounded simulation runs.
- Added Bounded Simulation and Simulation Evidence UI controls.
- Added simulation evidence to operations summary and operations evidence export.
- Added EN/DE simulation and stress evidence documentation.
- Added regression coverage for simulation write gate, bounded telemetry, alert, recovery, audit, evidence, and cleanup behavior.

## [0.20.0] - 2026-06-18

### Added

- Added `/api/config/profiles` for operator-managed configuration profiles with desired firmware and telemetry interval.
- Added `/api/firmware/compatibility` for read-only hardware, firmware, and runtime compatibility checks.
- Added Configuration Profile, Firmware Compatibility, Configuration Profiles, and Firmware Catalog UI controls.
- Added EN/DE configuration and firmware compatibility documentation and acceptance traceability.
- Added regression coverage for profile authorization, reference validation, read-only firmware checks, and root-page visibility.

## [0.19.0] - 2026-06-18

### Added

- Added `/api/demo/operational-preview` for read-only operational dashboard value before live devices are connected.
- Added Read-Only Operational Preview and Operational Workbench tabs to the first page.
- Added EN/DE operational preview documentation and acceptance checklist traceability.
- Added regression coverage to prove the preview is customer-safe and does not write live records.

## [0.18.0] - 2026-06-18

### Added

- Added `/api/delivery/final-package` for final delivery package contents and open customer signoff gates.
- Added Final Delivery panel to the Operations Console.
- Added EN/DE Phase 3 final delivery package, final business plan, and final presentation outline documents.
- Added regression coverage for final delivery package metadata, open gates, OpenAPI exposure, and root-page visibility.

## [0.17.0] - 2026-06-18

### Added

- Added `/api/production/approval-package` for production-owner decision items, evidence links, and Phase 2 signoff gate.
- Added `/api/customer/feedback/summary` for bounded customer feedback count, rating average, area counts, and next review gate.
- Added Owner Approval and Feedback Summary panels to the Operations Console.
- Added EN/DE production-owner approval package documentation.
- Added regression coverage for owner decisions, feedback aggregation, OpenAPI exposure, and root-page visibility.

## [0.16.0] - 2026-06-18

### Added

- Added `/api/production/hardening` for customer-safe production-readiness controls, score, and next gate.
- Added `/api/customer/feedback` for operator-approved customer feedback with data minimisation and audit evidence.
- Added Production Hardening and Customer Feedback panels to the Operations Console.
- Added EN/DE production hardening and customer feedback documentation.
- Added regression coverage for production configuration reflection, feedback write gate, data minimisation, and UI visibility.

### Security

- Strengthened customer feedback minimisation by rejecting phone-like contact text before audit storage.
- Rejected wildcard trusted hosts when production mode is enabled.

## [0.15.0] - 2026-06-18

### Added

- Added `/api/demo/package` for customer-safe website demo metadata, operator flow, runtime, and handoff files.
- Added a Customer Website Demo panel to the Operations Console.
- Added EN/DE customer website demo package documentation.
- Added EN/DE Phase 2 business plan draft documentation.
- Added regression coverage for demo package metadata and root-page visibility.

## [0.14.1] - 2026-06-18

### Fixed

- Updated the operations summary and diagnosis panel text to reflect grounded diagnosis behavior after the P2.12 AI routing baseline.

## [0.14.0] - 2026-06-18

### Added

- Added `/api/ai/routing` for customer-safe local, cloud, and grounded fallback route status.
- Added `/api/ai/evaluations` for grounding, fallback, human approval, and provider-label checks.
- Added grounded diagnosis output in `/api/chat` based on current alert, telemetry, and recovery proposal records.
- Added Operations Console panels for AI routing and AI evaluation status.
- Added regression coverage for AI route labeling, credential non-disclosure, grounded diagnosis, and evaluation readiness.

## [0.13.0] - 2026-06-18

### Added

- Added OIDC-compatible bearer-token validation at `/api/access/token/validate`.
- Added bearer identity support for state-changing API write gates.
- Added identity-provider readiness metadata to access policy, security status, settings, and evidence outputs without exposing validation material.
- Added EN/DE secure remote access guide for production host allowlist, reverse-proxy TLS, readiness, and identity-provider gates.
- Added regression tests for valid bearer identity, expired bearer rejection, and IDP-only readiness.

## [0.12.0] - 2026-06-18

### Added

- Added `/api/alerts/{alert_id}/resolve` with operator protection and audit evidence.
- Added `/api/operations/evidence` for customer-safe runtime evidence export.
- Added `/api/demo/reset` for development-only bounded demo data reset.
- Added browser controls for alert resolution, evidence export, and demo reset.
- Added regression coverage for operations closure and production-disabled reset.

## [0.11.0] - 2026-06-18

### Added

- Added `/api/operations/summary` for a first-screen operational state, readiness score, current risk, next actions, and runbook.
- Added Operations Snapshot cards to the browser console.
- Added asset, telemetry, and Operator Runbook panels to the live operational data view.
- Added regression tests for actionable empty-state operations and active alert summary behavior.

## [0.10.1] - 2026-06-18

### Fixed

- Removed the demo operator token value from the root browser page.
- Added a write-action warning when no operator token is entered.
- Added regression coverage to prevent token material from being embedded in root HTML.

## [0.10.0] - 2026-06-18

### Added

- Added `/api/access/policy` with viewer, operator, and admin role scopes.
- Added identity-provider readiness state without exposing credential material.
- Added Operations Console access policy panel and first-screen access role summary.
- Added regression tests for access policy visibility and OpenAPI route coverage.

## [0.9.1] - 2026-06-18

### Fixed

- Added first-viewport summary counters for Deployment Readiness and Phase Reports.
- Regenerated release evidence from the current source commit after audit feedback.

## [0.9.0] - 2026-06-18

### Added

- Added customer-safe deployment readiness content at `/api/settings`.
- Added customer-safe phase delivery report summaries at `/api/reports`.
- Added Operations Console panels for Deployment Readiness and Phase Reports.
- Added regression tests for non-empty readiness and report evidence without exposing secrets.

### Changed

- The settings and reports endpoints now provide operational delivery value instead of empty placeholder collections.

## [0.8.0] - 2026-06-18

### Added

- Added `/api/demo/scenario` with the first operational pilot workflow.
- Added a first-screen Pilot Scenario panel with workflow steps, thresholds, and expected operator results.
- Added regression coverage that prevents the dashboard from opening as an empty zero-value page.

### Changed

- The Operations Console now explains the pilot workflow before live runtime records exist.

## [0.7.0] - 2026-06-18

### Added

- Added security headers for browser and API responses.
- Added production mode that disables `/docs`, `/redoc`, and `/openapi.json`.
- Added `/api/security/status` for customer-safe security posture visibility.
- Added Operations Console security baseline panel.
- Added regression tests for security headers, production documentation mode, and public security status.

### Changed

- Added TrustedHostMiddleware with environment-driven host allowlist support.

## [0.6.0] - 2026-06-18

### Added

- Added operator-token write gate using `X-Operator-Token`.
- Added RBAC baseline tests for unauthorized writes, configured tokens, and recovery approval protection.
- Added Operations Console support for sending the operator token on state-changing actions.

### Changed

- Protected asset, device, telemetry, MQTT ingestion, and recovery approval write endpoints with a shared FastAPI security dependency.

## [0.5.0] - 2026-06-18

### Added

- Added MQTT adapter baseline at `/api/adapters/mqtt/messages`.
- Added audit event storage and `/api/audit/events`.
- Added operational console controls for MQTT message ingestion and audit review.
- Added regression tests for MQTT telemetry ingestion, invalid MQTT topics, invalid MQTT payloads, and recovery approval audit events.
- Added runtime dependency and license audit evidence for the 0.5.0 Docker image.

### Fixed

- Rejected semantically invalid MQTT telemetry payloads before telemetry or audit records are written.
- Enforced MQTT adapter registration before accepting MQTT telemetry for a device.
- Replaced dynamic customer-data HTML rendering with DOM `textContent` rendering in the Operations Console.

## [0.4.0] - 2026-06-18

### Added

- Replaced the static root dashboard with an operational console.
- Added browser controls for registering assets, registering devices, ingesting telemetry, reviewing alerts, approving recovery proposals, and checking AI fallback.
- Added an end-to-end `Run Demo Flow` button for the Asset -> Device -> Telemetry -> Alert -> Recovery workflow.
- Added regression coverage for the operational console UI surface.

### Fixed

- Tightened the customer release scanner so product workflow documentation is allowed while non-product operating wording remains blocked.

## [0.3.1] - 2026-06-18

### Fixed

- Added Docker healthcheck for `/healthz`.
- Aligned Docker Compose deployment with the operational host port `8040`.
- Set the Compose image tag to `agentiot-greenovax:0.3.1`.
- Updated README usage examples to show Docker host port `8040` separately from direct development port `8080`.

## [0.3.0] - 2026-06-18

### Added

- Added SQLite-backed Phase 2 core API behavior for assets, devices, telemetry, alerts, and recovery proposals.
- Added human-in-the-loop recovery approval with audit identifiers.
- Added explicit AI chatbot fallback wording for unavailable model state.
- Added Phase 2 API regression tests and BDD scenarios.
- Added customer-safe Phase 2 core API baseline documentation in English and German.

## [0.2.0] - 2026-06-18

### Added

- Added customer-safe Phase 1 requirements alignment, architecture, UI interaction, hardware/firmware, and report documents in English and German.
- Added a customer-safe Phase 1 dashboard for browser access at `/`.
- Added GreeNovaX logo branding and footer copyright/version metadata to the dashboard.
- Added a customer-safe About page with funding context, product purpose, owner, developer, and MIT license.

### Fixed

- Added the missing MIT SPDX header to the BDD baseline feature file.
- Removed a spelled-out legacy marker from shipped test source and tightened the customer release scan.

## [0.1.0] - 2026-06-17

### Added

- Independent clean-room repository scaffold.
- MIT license, NOTICE, bilingual README files, customer release docs, and indexes.
- Customer release manifest and acceptance checklist.
- FastAPI baseline with contracted public API paths.
- BDD feature file and pytest smoke/contract tests.

### Security

- Public metadata excludes non-product operating material and legacy branding.
