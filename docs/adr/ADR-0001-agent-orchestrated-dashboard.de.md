<!-- SPDX-License-Identifier: MIT -->
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.152.8
# Date: 2026-07-03
# Language: German
# License: MIT

# ADR-0001: Agenten-orchestriertes Dashboard

Prepared for GreeNovaX by IoT-AI.Tech.

## Status

Akzeptiert

## Kontext

Das vertragliche Dashboard muss als Agenten-Orchester betrieben werden. Jeder
operative Bereich benoetigt einen eindeutigen Owner-Agenten, sichtbare
Nachweislinks, rollenbegrenzte Aktionen und nachvollziehbare Uebergaben. Die
Implementierung muss clean-room und kundensicher bleiben; Build-Anweisungen
oder Build-Governance-Aufzeichnungen duerfen nicht Teil der
Kundenlieferung sein.

## Entscheidung

AgentIoT verwendet eine kundensichere Agent Card pro Dashboard-Bereich. Jede
Card beschreibt Owner Panel, Zweck, Ein- und Ausgabevertraege, Tool-Endpunkte,
Modellrichtlinie, Prompt-Referenz, Berechtigungen, SLA-Ziel, A2A-Schema und
ADR-Referenz. Agenten-Uebergaben verwenden den kanonischen A2A-JSON-Umschlag:
`id`, `from`, `to`, `type`, `schema_version`, `payload`, `trace_id` und `ts`.

Die Admin-Oberflaeche zeigt Registry, Prompt Contracts, Agent Cards, A2A-Kanten,
ADR-Register, Evidence Findings und Release Gates ueber Produkt-APIs statt ueber
nicht lieferbare Build-Governance-Dateien.

## Konsequenzen

- Jeder Dashboard-Bereich hat einen benannten Owner-Agenten und Nachweisendpunkt.
- Menschliche Freigabe bleibt fuer Recovery oder privilegierte Aenderungen
  erforderlich.
- Kundenpakete koennen diese ADR enthalten, ohne geschuetzte Prompts, Tokens,
  lokale Pfade oder Tool-Kommunikationsdaten offenzulegen.
- Neue Agenten muessen Agent Card, A2A-Route, Testnachweis und diese ADR-Menge
  aktualisieren, wenn sich die Architektur aendert.

## Verifikation

| Gate | Nachweis |
|---|---|
| Agent Cards | `/api/orchestration/protocol-contracts` |
| A2A-Umschlaege | `/api/orchestration/evidence-matrix` |
| Admin Registry | `/api/admin/agents` |
| Prompt Contracts | `/api/admin/agents/prompt-contracts` |
| Evidence Findings | `/api/evidence/findings` |
