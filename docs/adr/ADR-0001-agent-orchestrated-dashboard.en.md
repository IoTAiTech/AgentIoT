<!-- SPDX-License-Identifier: MIT -->
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.152.8
# Date: 2026-07-03
# Language: English
# License: MIT

# ADR-0001: Agent-Orchestrated Dashboard

Prepared for GreeNovaX by IoT-AI.Tech.

## Status

Accepted

## Context

The contracted dashboard must operate as an agent orchestra. Each operational
area needs an explicit owner agent, visible evidence links, role-bound actions,
and traceable handoffs. The implementation must remain clean-room and
customer-safe, with no private build instructions or build governance records in
the customer deliverable.

## Decision

AgentIoT uses one customer-safe Agent Card per dashboard section. Each card
declares the owner panel, purpose, input/output contracts, tool endpoints,
model policy, prompt reference, permissions, SLA target, A2A schema, and ADR
reference. Agent handoffs use the canonical A2A JSON envelope:
`id`, `from`, `to`, `type`, `schema_version`, `payload`, `trace_id`, and `ts`.

The admin surface exposes the registry, prompt contracts, Agent Cards, A2A
edges, ADR register, evidence findings, and release gates through product APIs
instead of non-deliverable build governance files.

## Consequences

- Every dashboard section has a named owner agent and evidence endpoint.
- Human approval remains required for recovery or privileged changes.
- Customer release packages can include the ADR without exposing protected
  prompts, tokens, local paths, or tool communication records.
- Future agent additions must add or update an Agent Card, A2A route, test
  evidence, and this ADR set when the architecture changes.

## Verification

| Gate | Evidence |
|---|---|
| Agent Cards | `/api/orchestration/protocol-contracts` |
| A2A envelopes | `/api/orchestration/evidence-matrix` |
| Admin registry | `/api/admin/agents` |
| Prompt contracts | `/api/admin/agents/prompt-contracts` |
| Evidence findings | `/api/evidence/findings` |
