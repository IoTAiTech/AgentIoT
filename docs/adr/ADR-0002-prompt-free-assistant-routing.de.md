<!-- SPDX-License-Identifier: MIT -->
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.152.8
# Date: 2026-07-03
# Language: German
# License: MIT

# ADR-0002: Prompt-freies Assistenten-Routing und Modellbereitschaft

Prepared for GreeNovaX by IoT-AI.Tech.

## Status

Akzeptiert

## Kontext

Der Assistent muss lokale und Cloud-Modellrouten unterstuetzen, ohne nicht
belegte Paritaetsversprechen abzugeben. Die Kundenlieferung muss klar zeigen,
welche Route aktiv ist, welche Zugangsdaten oder Policies konfiguriert sind,
welche Token-Nutzung erfasst wird und ob Aktivierungs- und Evaluierungsgates
bestanden wurden.

## Entscheidung

AgentIoT trennt Routing von Antwortgenerierung. Die Standardroute ist ein
grounded fallback, der Runtime-Daten, RAG-Wissen, A2A-Trace-Metadaten und
Freigabegrenzen nutzt. Provider-basierte Routen bleiben deaktiviert, bis Policy,
Credential, Runtime-Freigabe, Identitaet, Grounding, Evaluierung, Token-Nutzung
und Connectivity-Nachweis bestanden sind.

Das Assistenten-Gedaechtnis speichert nur Prompt-Hashes, Metadaten, Feedback,
Findings und Session-Kontinuitaet. Rohprompts, Antworttexte, Provider-Payloads,
Credential-Werte, lokale Pfade und interne Betreiberanweisungen werden aus
kundenbezogenen Ausgaben ausgeschlossen.

## Konsequenzen

- Das Produkt kann sicher mit fallback-only Route geliefert werden, wenn der
  Owner diese Grenze freigibt.
- Lokale oder Cloud-Routen koennen spaeter aktiviert werden, ohne das
  clean-room Ownership-Modell zu aendern.
- Das Dashboard darf keine Gemini-, ChatGPT-, Claude- oder Copilot-Paritaet
  behaupten, bis Credential-, Aktivierungs-, Evaluierungs- und Owner-Nachweise
  diese Behauptung belegen.

## Verifikation

| Gate | Nachweis |
|---|---|
| Routing-Status | `/api/ai/routing` |
| Modell-Benchmarks | `/api/ai/model-benchmarks` |
| Ressourcen-Governance | `/api/ai/resource-governance` |
| Assistentenqualitaet | `/api/assistant/quality-report` |
| Interaction Ledger | `/api/assistant/interactions` |
| Owner-Entscheidung | `/api/production/approval-package` |

