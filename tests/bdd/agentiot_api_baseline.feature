# SPDX-License-Identifier: MIT
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.152.6
# Date: 2026-07-03
# Language: English
# License: MIT

Feature: AgentIoT API baseline

  Scenario: Health endpoint returns service status
    Given the AgentIoT backend is running
    When a client requests "/healthz"
    Then the response is successful
    And the response identifies GreeNovaX and IoT-AI.Tech

  Scenario: Root page is available for browser access
    Given the AgentIoT backend is running
    When a client requests "/"
    Then the response is a customer-safe operational console with operational workflow, forms, logo, copyright, and version

  Scenario: Cockpit route is available for browser access
    Given the AgentIoT backend is running
    When a client requests "/cockpit"
    Then the response is the dashboard cockpit shell and not a JSON error

  Scenario: First screen shows an actionable pilot scenario
    Given the AgentIoT backend is running before live devices are connected
    When a user opens the dashboard
    Then the first screen explains the pilot workflow, thresholds, and expected operator results

  Scenario: About page explains the product context
    Given the AgentIoT backend is running
    When a client requests "/about"
    Then the response explains funding context, product purpose, owner, developer, and license



  Scenario: Production action plan lists executable signoff tasks
    Given production hardening or owner signoff gates are still open
    When a client requests "/api/production/action-plan"
    Then the response lists customer-safe actions with evidence and owner agent without admin write endpoints
    And no restricted execution data, credentials, or contact data are returned

  Scenario: Admin production action plan lists write guidance
    Given an administrator has access-management scope
    When the administrator requests "/api/admin/production/action-plan"
    Then the response lists PATCH endpoints, request schemas, and approval boundaries for production controls and owner decisions
    And no credentials, local paths, contact data, or formal-acceptance claims are returned

  Scenario: Provider runtime requires fresh connectivity evidence
    Given an approved local or cloud model route has an older connectivity check
    When an operator asks the assistant to use provider runtime
    Then the provider chat gate reports "connectivity_check_stale"
    And no external or local model runtime is called before a fresh admin connectivity check


  Scenario: Release mission records prompt-free closed-loop session evidence
    Given an operator runs the release mission
    When the dashboard reviews assistant sessions and coworker quality
    Then the release response includes recorded closed-loop session metadata
    And coworker quality reports no gap to the 99.99 target
    And no raw instruction text, assistant instruction text, credential, or provider payload value is returned

  Scenario: Version endpoint returns delivery metadata
    Given the AgentIoT backend is running
    When a client requests "/api/version"
    Then the response declares version "0.152.8"

  Scenario: Production readiness rejects weak runtime token
    Given production mode is enabled without an identity provider
    When the operator token is short, placeholder, or test-style
    Then "/readyz" reports "not_ready"
    And "/api/security/status" reports only the token strength state without returning the token value

  Scenario: Production admin token rejects weak configuration
    Given production mode has a weak configured admin token
    When a client presents the matching token to a control-plane endpoint
    Then the endpoint reports "503" and "Admin authentication unavailable"
    And no admin control-plane action is executed

  Scenario: A2A handoff exposes Agent Card and prompt traceability
    Given an operator submits a supervised agent task
    When the dashboard records the A2A handoff trace
    Then each handoff includes the Agent Card id, prompt reference, prompt version, and redacted prompt hash

  Scenario: Six-hour project drift control
    Given active development or release preparation is running
    When a client requests "/api/project/drift-control"
    Then the response requires a 6-hour project_delivery_coordinator and release_compliance_controller document review
    And the response compares KPI and SLA status against the 99.99 target
    And the response includes source commit and review-window evidence
    And the response blocks customer release mirroring when drift is unresolved

  Scenario: Six-hour drift-control review recording
    Given active development or release preparation is running
    When an operator records "/api/project/drift-control/run"
    Then the response stores audit and closed-loop finding evidence without secrets or prompts

  Scenario: Daily project gap discovery
    Given active development or release preparation is running
    When a client requests "/api/project/gap-discovery"
    Then the response checks contract goals, phase distance, KPI, SLA, runtime evidence, and owner decisions every 6 hours
    And the response lists executable gaps with owner agents and customer-safe evidence links
    And the response does not claim customer acceptance or expose private operational material

  Scenario: Six-hour project gap-discovery review recording
    Given active development or release preparation is running
    When an operator records "/api/project/gap-discovery/run"
    Then the response stores audit and finding evidence for the current 6-hour gap review

  Scenario: Read-only operational preview
    Given no live runtime records exist
    When a client requests "/api/demo/operational-preview"
    Then the response shows overview, device detail, configuration, firmware, alarm management, recovery, diagnosis, and settings views
    And no live records are written by the preview

  Scenario: MQTT adapter ingestion
    Given a registered MQTT device exists
    When the backend receives an MQTT telemetry message
    Then telemetry, alert, recovery, and audit records are created
    And the response declares license "MIT"

  Scenario: MQTT adapter rejects invalid boundaries
    Given a device is not registered for MQTT or the MQTT payload is invalid
    When the backend receives the MQTT telemetry message
    Then the response is rejected before telemetry or audit records are written

  Scenario: MQTT broker subscriber status
    Given a customer MQTT broker can be configured through environment variables
    When a client requests broker subscriber status
    Then the response shows safe configuration flags, topic filter, counters, and no credential values

  Scenario: REST adapter status
    Given registered REST and MQTT devices may both have telemetry
    When a client requests REST adapter status
    Then the response reports only REST device and telemetry counts with evidence links and no raw payload values

  Scenario: Operations Console renders API data safely
    Given API records may contain customer-controlled identifiers
    When the browser renders device, alert, recovery, and audit data
    Then the UI renders values as DOM text and does not inject API values as HTML

  Scenario: RAG quality console exposes grounded evidence
    Given the AgentIoT backend is running
    When a client requests "/api/rag/quality-console"
    Then the response shows retrieval probes, grounding gaps, action owners, chart evidence, and customer-safe privacy status

  Scenario: Operator write gate protects state-changing actions
    Given a client has no valid operator token
    When the client sends a state-changing API request
    Then the request is rejected before product records are written

  Scenario: Production security posture is hardened
    Given the backend runs in production mode
    When a client requests browser pages and API documentation routes
    Then security headers are present and interactive API documentation is hidden

  Scenario: Pentest abuse gate blocks common attacks
    Given the backend runs in production mode
    When abuse probes target write routes, model endpoints, public rendering, and path identifiers
    Then auth bypass, SSRF, XSS, injection, and traversal attempts are rejected or redacted
    And no server error, secret, local path, or implementation traceback is returned

  Scenario: Delivery readiness and phase reports are visible
    Given the AgentIoT backend is running
    When a client requests settings, reports, or the root page
    Then deployment readiness and phase evidence are visible without exposing secrets

  Scenario: AI model resource governance stores safe usage and memory evidence
    Given cloud and local model services may be configured by an administrator
    When a client requests AI resource governance, token usage, or memory policy evidence
    Then the response includes required token windows, memory recommendations, and credential readiness
    And the response does not expose API keys, passwords, operator input text, answers, provider payloads, or local runtime URLs

  Scenario: Phase execution board is visible
    Given the AgentIoT backend is running
    When a client requests the project phase board or opens the root page
    Then Phase 1, Phase 2, Phase 3, operational value, evidence, and next actions are visible

  Scenario: Agent orchestration admin map is visible
    Given the AgentIoT backend is running
    When a client requests the agent admin registry or opens the root page
    Then section agents, A2A links, ADR evidence, visual agent map, and runtime evidence policies are visible

  Scenario: Dashboard sections have accountable agents
    Given the AgentIoT backend is running
    When a client requests "/api/orchestration/evidence-matrix"
    Then each primary dashboard section declares an owner agent, A2A links, ADR evidence, QA lane, eval profile, and customer-safe evidence endpoints
    And every visible dashboard and menu anchor is represented in the Dashboard Section Ownership Matrix

  Scenario: Agent section reports are visible
    Given the AgentIoT backend is running
    When a client requests the agent section reports or opens the root page
    Then each section agent reports readiness, runtime records, evidence links, next action, and A2A quality gate

  Scenario: UI/UX experience auditor protects dashboard navigation
    Given the AgentIoT backend is running
    When a client opens the root dashboard
    Then the primary menus open dashboard sections instead of raw JSON endpoints
    And the UI/UX Experience Auditor reports menu and chart quality evidence

  Scenario: UI/UX quality gate supports operational decisions
    Given the AgentIoT backend is running
    When a client requests "/api/ui/quality-gate"
    Then the response shows menu routing, chart readability, safe data presentation, responsive accessibility, and industrial visual quality gates
    And the dashboard UI/UX section shows score, ready gates, and raw JSON menu count

  Scenario: Browser visual cockpit fidelity is auditable
    Given the AgentIoT backend is running
    When a client opens "/" or "/cockpit"
    Then the cockpit exposes browser-visual QA hooks, time-range control, refresh status, and map-quality evidence
    And the UI/UX Experience Auditor can block a release if those hooks disappear

  Scenario: Advanced settings can run a bounded QA challenge
    Given the AgentIoT backend is running
    When an operator opens Advanced Settings and runs the QA challenge
    Then the dashboard shows the active profile, reasoning layer, answer layer, QA KPI, and latest challenge run
    And the backend stores bounded case evidence without exposing credential values

  Scenario: Continuous QA mission records release challenge evidence
    Given the AgentIoT backend is running
    When an operator records the continuous QA mission from Advanced Settings
    Then Smoke, API, A2A, ADR, Visual, Stress, RAG, Log, Security, License, and A/B lanes are stored as closed-loop evidence
    And the dashboard reports show 60-minute mission coverage against the 99.99 KPI without large datasets

  Scenario: Go-live readiness review runs all release gates
    Given the AgentIoT backend is running
    When an operator runs the readiness review from Automation Administration
    Then baseline AI eval, assistant Q/A, agent autopilot, continuous QA, report charts, findings, and privacy evidence are recorded without provider calls

  Scenario: First-screen settings can update AI route
    Given an admin runtime token is configured
    When the admin applies an AI route from the advanced settings gear
    Then the active analysis profile and provider policy are updated with audit evidence and no credential values

  Scenario: Dashboard charts and reports are visible
    Given the AgentIoT backend is running
    When a client requests the dashboard report package
    Then operations readiness, runtime records, agent coverage, visual chart metadata, and report evidence are returned

  Scenario: Operational Command Center links menus to action
    Given the AgentIoT backend is running
    When a client opens the Command menu or requests "/api/operations/command-center"
    Then the dashboard shows current state, readiness, active risk, next action, KPI status, owner agents, and evidence endpoints without opening raw JSON

  Scenario: Agent control requires admin scope
    Given an operator is not an admin
    When the operator tries to change an agent control
    Then the request is rejected and no control-plane change is accepted

  Scenario: Admin token controls dashboard agents
    Given an admin runtime token is configured
    When the admin updates a dashboard agent control from the console
    Then the agent mode, instruction template, and audit evidence are updated without exposing token material

  Scenario: Executable agent task creates A2A trace
    Given an operator submits a dashboard goal
    When the agent orchestra executes the task
    Then the response includes the primary agent, route, A2A trace, evidence links, audit event, and approval flag

  Scenario: AI provider policy is admin-managed
    Given an admin bearer identity is valid
    When the admin defines the assistant provider policy
    Then the routing endpoint shows provider, model, profile, runtime gate, tools, and no credentials

  Scenario: AI analysis profiles are admin-managed
    Given an admin bearer identity is valid
    When the admin activates an assistant analysis profile
    Then routing exposes separate reasoning and answer layers without storing prompts or credentials

  Scenario: RAG Knowledge Center supports grounded operations
    Given customer-safe knowledge records are active
    When a user searches for recovery approval evidence in the dashboard
    Then ranked knowledge matches, local evidence links, and assistant grounding are visible without opening raw JSON

  Scenario: Admin console can update provider and role policy
    Given an admin runtime token is configured
    When the admin updates provider policy or access role records from the dashboard
    Then the control-plane API stores the change with audit evidence and no credential values


  Scenario: Model service connectivity check stores sanitized evidence
    Given an admin has configured an approved model provider
    When the admin runs "/api/admin/ai/model-services/{provider}/connectivity-check"
    Then audit, finding, and token-count evidence are stored without prompts, answers, provider payloads, local URLs, or credential values

  Scenario: Cloud assistant runtime is operator-gated
    Given an admin enables an external assistant provider and runtime approval exists
    When a user asks for diagnosis without operator identity
    Then the system returns grounded records without calling the external provider



  Scenario: Advanced routing console supports Gemini candidate route
    Given an admin can open Advanced Settings
    When a client requests "/api/admin/ai/routing-console" or selects Gemini provider routing
    Then active profile, provider, model, runtime gate, candidate routes, owner-agent actions, and evidence links are visible without credentials or operator input text

  Scenario: AI model benchmark matrix separates routes
    Given the AgentIoT backend is running
    When a client requests "/api/ai/model-benchmarks"
    Then task fit, owner agents, model candidates, runtime gates, and evidence links are visible without credential or prompt values

  Scenario: AI evaluation run stores quality evidence
    Given an operator can access the dashboard
    When the operator runs the assistant evaluation suite
    Then provider policy, provider runtime gate, A2A trace, approval, grounding, and report evidence cases are stored

  Scenario: Closed-loop findings store lessons without prompts
    Given assistant chats, agent tasks, and eval runs produce operational learning
    When a client requests the findings table
    Then prompt-free outcomes, evidence summaries, and lessons learned are available for review


  Scenario: Assistant feedback loop records prompt-free quality signals
    Given an operator asks the assistant an operational question
    When the operator records assistant feedback for that interaction
    Then rating, outcome, category, evidence endpoint, audit event, and closed-loop finding are stored without operator input text or answer text

  Scenario: Assistant closed-loop learning suggests BDD candidates
    Given assistant interactions, feedback, and findings have been recorded
    When a client requests "/api/assistant/bdd-suggestions"
    Then the response returns Gherkin candidate scenarios derived from prompt-free evidence
    And the response marks candidates as human-approved patches before any BDD file write
    And raw operator messages, answer text, provider payloads, and credentials are not returned

  Scenario: Assistant interaction ledger stores prompt-free Q and A evidence
    Given an operator asks the assistant an operational question
    When a client requests "/api/assistant/interactions"
    Then prompt hashes, route status, evidence counts, latency, outcome, and approval boundaries are visible without operator input text or answer text

  Scenario: Assistant decision brief is prompt-free and decision-grade
    Given an operator asks for a current operational decision
    When a client requests "/api/assistant/decision-brief"
    Then decision readiness, risk register, A2A trace, ADR alignment, model routing, RAG grounding, and HITL evidence are returned
    And only a query hash is stored, with no operator input text or provider payload

  Scenario: Access role policy can be defined by admin
    Given an admin bearer identity is valid
    When the admin defines a role policy
    Then the access catalog includes the role, scopes, source, and audit evidence

  Scenario: Scoped bearer roles are enforced
    Given a bearer identity has only one operational write scope
    When the identity calls endpoints outside that scope
    Then the request is rejected with a scope-specific error before records are written

  Scenario: Access policy is visible without identity-provider secrets
    Given role groups and identity-provider integration are planned
    When a client requests the access policy
    Then viewer, operator, and admin scopes are visible without token material

  Scenario: Unsupported implementation details are absent
    Given the AgentIoT backend is running
    When a client inspects the public metadata
    Then no non-product instructions, addresses, or legacy branding are exposed

Feature: Phase 2 core product baseline

  Scenario: Device telemetry ingestion
    Given a registered device is assigned to an asset
    When the backend receives high temperature telemetry
    Then the telemetry is stored and a critical alert is visible through the API

  Scenario: Configuration profile management
    Given a registered asset and device exist
    When an operator saves a configuration profile
    Then the profile records desired firmware, telemetry interval, and enabled state

  Scenario: Firmware compatibility check
    Given a supported pilot hardware model is selected
    When the backend evaluates firmware compatibility
    Then the response reports compatibility, risk level, checks, and recommendations without writing runtime records

  Scenario: Bounded simulation run
    Given an operator needs smoke and stress evidence without large test data
    When the operator runs a bounded simulation
    Then the system creates capped devices, profiles, telemetry, alert, recovery, and audit evidence

  Scenario: Recovery approval
    Given an open alert has a recovery proposal
    When an operator approves the proposal
    Then the approval is recorded with an audit identifier

  Scenario: AI fallback
    Given no configured model is available
    When a user opens the diagnosis chatbot
    Then the system explains the unavailable model state and provides non-AI troubleshooting steps

  Scenario: AI routing status
    Given no local or cloud AI route is configured
    When a client requests the AI routing endpoint
    Then the system reports grounded fallback and does not expose credential material

  Scenario: Grounded diagnosis with runtime records
    Given telemetry has created an alert and recovery proposal
    When a user asks for diagnosis
    Then the response returns a structured assistant plan, evidence links, A2A trace, and next actions without executing recovery actions

  Scenario: First-screen assistant preview
    Given the dashboard has loaded current operational records
    When a user opens the operations console
    Then the page requests a read-only assistant preview without requiring an operator token

  Scenario: AI evaluation checks
    Given runtime records may or may not exist
    When a client requests AI evaluation status
    Then the system reports grounding, fallback, human approval, and provider-label checks

  Scenario: Customer website handoff package
    Given the customer website demo has not been publicly deployed
    When a client requests the handoff package metadata
    Then the system reports customer-safe target site, runtime, operator flow, and handoff files

  Scenario: Production hardening status
    Given production owner decisions may still be open
    When a client requests the production hardening endpoint
    Then the system reports readiness controls, score, and next gate without secrets

  Scenario: Admin-managed production readiness controls
    Given an admin needs to record production readiness evidence
    When the admin updates a production readiness control
    Then the system stores the control state with audit evidence and rejects contact data

  Scenario: Customer feedback loop
    Given a reviewer provides bounded product feedback through an operator
    When the feedback is accepted by the backend
    Then the system stores feedback evidence without contact details and writes an audit event

  Scenario: Production owner approval package
    Given production-owner decisions are needed before public operation
    When a client requests the approval package and feedback summary
    Then the system reports owner decisions, evidence links, feedback count, and next signoff gate

  Scenario: Production action blocker taxonomy
    Given production actions may include engineering work and customer decisions
    When a client requests the production action plan
    Then the system separates development-visible, customer-runtime, owner-signoff, and customer-decision blockers without exposing secrets

  Scenario: Final delivery package
    Given Phase 3 delivery review is being prepared
    When a client requests the final delivery package
    Then the system reports Docker, source, business plan, presentation, documentation, acceptance, and open signoff gates

  Scenario: Acceptance evidence pack
    Given customer delivery review needs one consolidated proof package
    When a client requests the acceptance evidence pack
    Then the system reports gate summary, charts, reports, agents, access policy, AI quality, final delivery, and open items

  Scenario: Operations snapshot before live data
    Given no runtime records have been created
    When an operator opens the dashboard
    Then the system shows pilot readiness, next action, current risk, and runbook guidance

  Scenario: Operations snapshot during alert handling
    Given telemetry creates a critical temperature alert
    When the operator checks the operations summary
    Then the system reports action required, pending recovery, latest telemetry, and the affected device

  Scenario: Alert closure
    Given a critical alert has been verified by an operator
    When the operator resolves the alert
    Then the alert is closed and an audit event records the closure

  Scenario: Evidence export
    Given runtime records exist for the operational workflow
    When the operator exports operations evidence
    Then the response includes version, clean-room metadata, counters, records, and audit evidence without secrets

  Scenario: Demo reset
    Given development demo records exist
    When the operator resets demo data
    Then bounded runtime records are cleared and a reset audit event remains

  Scenario: Optional demo bootstrap
    Given demo bootstrap is explicitly enabled for a review runtime
    When the application starts with an empty database
    Then a bounded initial asset, MQTT device, telemetry sample, alert, recovery proposal, and audit event are available

  Scenario: Bearer identity validation
    Given an identity provider issuer, audience, and validation material are configured
    When an operator presents a valid bearer identity
    Then the system returns safe actor, role, scope, and provider metadata

  Scenario: RS256 JWKS bearer validation
    Given an identity provider issuer, audience, and JWKS endpoint are configured
    When an operator presents a valid RS256 bearer identity
    Then the system validates the signing key and returns safe identity metadata without exposing key material

  Scenario: Unsafe JWKS endpoint rejection
    Given an identity provider issuer and audience are configured with a private, metadata, credentialed, or non-HTTPS JWKS endpoint
    When an operator presents an RS256 bearer identity
    Then the system rejects the identity provider configuration before any JWKS fetch and returns no endpoint detail

  Scenario: Secure remote access gate
    Given production mode is enabled without trusted hosts
    When the application starts
    Then startup fails before exposing the service

  Scenario: Shell navigation renders operational command surfaces
    Given the cockpit shell is the first screen
    When an operator chooses a grouped menu item or assistant shortcut
    Then the cockpit updates the matching Operate, Agents, Intelligence, Delivery, or Settings command surface without showing raw JSON

  Scenario: Cockpit assistant runs an audited agent review
    Given an operator token is present in the dashboard
    When the operator runs an agent review from the cockpit assistant
    Then an audited agent task, A2A route, evidence finding, and refreshed agent run table are available

  Scenario: Stored 60-round assistant Q/A challenge
    Given an operator token with agent read scope
    When the operator runs the assistant_qa_60 evaluation suite
    Then 60 hash-only cases are stored
    And provider calls are recorded as zero

  Scenario: Agent autopilot mission activates all section agents
    Given an operator token with agent read scope
    When the operator runs the agent autopilot mission
    Then each enabled section agent creates an audited run, A2A trace, evidence links, and a closed-loop finding

  Scenario: Admin manages customer-safe agent prompt contracts
    Given an admin identity with agent manage scope
    When the admin reviews and updates an agent prompt contract
    Then the dashboard exposes managed contract ids, editable playbook fields, A2A links, ADR evidence, and audit records without secrets or unsafe provider-routing payload text


  Scenario: Sidebar routes open operational command surfaces
    Given the customer-safe dashboard shell is available
    When an operator opens "/assets", "/reports", or "/settings" directly
    Then the page initializes the matching cockpit command surface and does not show raw JSON

  Scenario: Intelligence and reports lead with their primary operational workspace
    Given the customer-safe dashboard shell is available
    When an operator opens Intelligence or Reports directly
    Then Intelligence presents a grounded assistant request before governance detail
    And Reports presents operational metrics in the first viewport without AI administration data
    And Reports uses management labels instead of raw chart terminology

  Scenario: Empty runtime routes to real setup actions
    Given no asset, device, or telemetry record is connected
    When an operator opens Cockpit, Intelligence, Reports, or Administration
    Then the dashboard offers real setup actions for asset registration, device binding, telemetry ingestion, or provider connection
    And the actions do not create synthetic runtime records before the operator submits a form

  Scenario: Release evidence console summarizes mission readiness
    Given the AgentIoT API is running
    When the operator requests `/api/release/evidence-console`
    Then the response includes gate owners, SLA gap, charts, action plan, and customer-safe privacy posture

  Scenario: Release evidence console exposes execution controls
    Given the AgentIoT API is running
    When the operator requests `/api/release/evidence-console`
    Then the response includes token readiness, operator scope, required inputs, and a local release mission run endpoint

  Scenario: Release gap closure console maps blocked gates to executable actions
    Given the AgentIoT API is running without release auth configured
    When the operator requests `/api/release/gap-closure-console`
    Then the response shows open gates, blocked auth setup, safe run endpoints, A2A owners, charts, and customer-safe privacy controls


  Scenario: Production action plan renders in the dashboard
    Given production hardening or owner signoff gates are still open
    When a user opens the dashboard production section
    Then the page shows the production action summary and action rows as an operational table
    And no raw JSON response is used as navigation content

  Scenario: Cockpit action queue opens operational surfaces
    Given the dashboard action queue lists live operator work
    When an operator selects an action queue item
    Then the dashboard opens the matching cockpit surface with evidence guidance
    And no raw JSON response is used as navigation content

  Scenario: Final handoff console summarizes owner actions
    Given the AgentIoT API is running
    When the operator requests `/api/delivery/handoff-console`
    Then the response includes handoff score, owner-decision summary, next action, open handoff actions, and customer-safe evidence links

  Scenario: Assistant answer carries prompt-free self-evaluation
    Given the AgentIoT API has runtime evidence for a grounded assistant answer
    When the operator asks `/api/chat` for diagnosis support
    Then the response includes answer review score, gates, evidence counts, and privacy flags
    And no operator input text, raw answer storage, provider payload, secret, local path, or restricted artifact is returned

  Scenario: Assistant follow-up contract stays prompt-free and actionable
    Given the AgentIoT API has runtime evidence for a grounded assistant answer
    When the operator asks `/api/chat` for diagnosis support
    Then the response includes a follow-up contract with known evidence, missing-before-action items, next best action, safe follow-up question, owner agent, and evidence endpoints
    And no operator input text, raw answer storage, provider payload, credential, local path, or restricted artifact is returned

  Scenario: Provider runtime does not retain prompt or payload material
    Given the application has grounded runtime evidence and a successful active-provider connectivity check
    When an authenticated operator completes a provider-backed chat turn with a canary prompt
    Then the answer is returned to the caller
    And ledgers, audit events, findings, quality report, tool proposals, and A2A trace contain only customer-safe metadata

  Scenario: Assistant follow-up uses prompt-free session context
    Given the assistant has a prior chat turn in the same session
    When the operator sends a follow-up with the prior message as parent
    Then the response includes prior turn counts, parent match status, categories, and evidence counts without operator input text or answer text

  Scenario: Assistant session threads preserve coworker continuity without prompt leakage
    Given an authenticated operator records a two-turn assistant session with a parent message id
    When a client requests "/api/assistant/sessions/{session_id}"
    Then the response contains session turns, feedback metadata, parent linkage, and evidence links
    And the response does not contain operator input text, answer text, provider payloads, or credential values

  Scenario: Coworker quality closes with release and prompt-free session evidence
    Given release evidence, assistant QA, A2A orchestration, token-window governance, and prompt-free session feedback are ready
    When a client requests "/api/assistant/coworker-quality"
    Then the response reports ready status, zero gap to the SLA target, and ready orchestration and provider-transparency dimensions
    And the response keeps Gemini, Copilot, and provider parity claims explicitly withheld until approved runtime gates pass

  Scenario: Assistant recovery proposal approval remains human-gated
    Given a prepared assistant tool proposal targets a concrete recovery approval endpoint
    When an operator approves it through "/api/assistant/tool-proposals/{proposal_id}/approve"
    Then the recovery proposal approval is recorded with audit and A2A evidence
    And no physical device recovery action is executed by the assistant

  Scenario: Assistant memory policy prunes expired prompt-free metadata safely
    Given an admin configures assistant memory retention, session caps, memory caps, and auto-prune
    When an expired assistant interaction and a still-active session are evaluated
    Then expired or over-budget prompt-free interaction metadata is removed with audit evidence
    And active session tool proposals remain available without operator input text, answer text, provider payloads, credentials, or local paths

  Scenario: AI model route preflight exposes actionable readiness gates
    Given an admin selects a local or cloud AI provider route
    When a client requests "/api/ai/model-route-preflight"
    Then the response lists policy, credential, runtime, activation, token-window, memory, and owner-decision gates
    And the response does not expose credential values, operator input text, provider payloads, local runtime URLs, or customer-restricted process paths

  Scenario: Oversized write payloads are rejected before endpoint processing
    Given the AgentIoT API has a configured request body limit
    When a client submits a write request larger than that limit
    Then the API returns a clear 413 response before creating runtime records
    And the same gate applies when Content-Length is missing or understated

  Scenario: Backup-retention readiness exposes only safe metadata
    Given a customer-approved backup policy is configured for production
    When a client requests "/api/production/backup-retention"
    Then the response reports readiness, cadence, retention, restore-test state, and a short policy fingerprint
    And it does not expose policy text, backup paths, credentials, contact data, or local runtime paths

  Scenario: Production secret-free preflight
    Given production owner signoff still requires customer-owned TLS and backup evidence
    When a client requests "/api/production/preflight"
    Then the response lists secret-free runtime checks without credentials, local paths, backup paths, or admin write endpoints

  Scenario: Operations workspace separates operator jobs without synthetic writes
    Given the dashboard has no registered telemetry records
    When the operator opens Operations and selects Monitoring, Assets, Alarms, or Workflows
    Then only the selected operational workspace is visible with its live records or truthful empty state
    And opening a setup form focuses user-completed fields without posting synthetic assets, devices, or telemetry

  Scenario: Phase 1 technical readiness stays separate from milestone progress
    Given Phase 1 commercial baseline review is still pending
    When a manager reviews the phase-distance evidence
    Then technical readiness is derived only from ready closure tasks
    And contractual milestone progress is explicitly not calculated without an approved weighting policy
