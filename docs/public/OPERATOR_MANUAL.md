<!-- SPDX-License-Identifier: MIT -->
# Operator manual

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 0.157.21 | Date: 2026-08-14  
production_claim: false

## What this product is

AgentIoT is an operations cockpit for IoT assets. It shows devices,
telemetry, alerts, and recovery proposals. A local assistant can summarize
evidence. It does not execute recovery by itself.

## Sign-in

The cockpit requires a signed-in operator when browser login is enabled.
Use the Sign In page. Change the initial administrator password on first use.

## Cockpit identity

The heading shows architecture (`x86` or `ARM`) and version (`v0.157.21`).
Both boxes in a pair must show the same version.

## Daily work

1. **Assets / devices** — register customer-owned hardware.
2. **Telemetry** — confirm the latest readings.
3. **Alarms** — open the newest critical alert first.
4. **Recovery** — read the proposal. Approve only after physical checks.
5. **Assistant** — ask operational questions. Expect five labels:
   Finding, Evidence, Agents, Next review, Approval.

## Assistant states

| Pill | Meaning |
|---|---|
| Live model | A configured local model answered this turn |
| Evidence-only | The model host did not answer; the review still uses records |
| Checking | Route is still being confirmed |

Use **Recheck model host** or **Open Models** if you need a live model.
Never treat evidence-only text as an executed action.

## Models

Settings → Models selects the local provider. Prefer a strong local chat
model. Tiny 0.5b tags and cloud aliases are not the default.

Configure the model host with environment variables on the box. Do not
commit host addresses to Git.

## Safety

- No secrets in chat, notes, or screenshots destined for GitHub.
- Recovery stays behind human approval.
- `production_claim` stays false until the owner signs a production gate.
