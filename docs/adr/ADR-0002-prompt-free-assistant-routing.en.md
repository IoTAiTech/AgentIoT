<!-- SPDX-License-Identifier: MIT -->
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.152.8
# Date: 2026-07-03
# Language: English
# License: MIT

# ADR-0002: Prompt-Free Assistant Routing And Model Readiness

Prepared for GreeNovaX by IoT-AI.Tech.

## Status

Accepted

## Context

The assistant must support local and cloud model routes while avoiding
unsupported parity claims. Customer delivery must show exactly which route is
active, which credentials or policies are configured, what token usage is
recorded, and whether the route has passed activation and evaluation gates.

## Decision

AgentIoT separates routing from answer generation. The default route is a
grounded fallback that uses runtime records, RAG knowledge, A2A trace metadata,
and human approval boundaries. Provider-backed routes remain disabled until
policy, credential, runtime approval, identity, grounding, evaluation, token
usage, and connectivity evidence all pass.

Assistant interaction memory stores prompt hashes, metadata, feedback, findings,
and session continuity only. Raw prompts, answer text, provider payloads,
credential values, local paths, and internal operator instructions are excluded
from customer-facing output.

## Consequences

- The product can be delivered safely with a fallback-only route when the owner
  approves that boundary.
- Local or cloud routes can be activated later without changing the clean-room
  ownership model.
- The dashboard must not claim Gemini, ChatGPT, Claude, or Copilot-level parity
  until model credentials, activation, evaluation, and owner approval evidence
  prove the claim.

## Verification

| Gate | Evidence |
|---|---|
| Routing status | `/api/ai/routing` |
| Model benchmarks | `/api/ai/model-benchmarks` |
| Resource governance | `/api/ai/resource-governance` |
| Assistant quality | `/api/assistant/quality-report` |
| Interaction ledger | `/api/assistant/interactions` |
| Owner decision | `/api/production/approval-package` |

