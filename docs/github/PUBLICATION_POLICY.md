<!-- SPDX-License-Identifier: MIT -->
# GitHub publication policy

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 1.1.0 | Date: 2026-08-13  
Audience: every coder (Claude · Codex · Gemini · Grok · human)  
Status: binding  
production_claim: false

## Order

GitHub is a **public-clean** surface. Commits that leave this host for
GitHub must be free of private project documents and sensitive data.

Founder order 2026-08-13: do not upload internal architecture, contracts,
session information, or any other private class. Every commit must be
completely clear.

This file is the single allow/deny list. The operating guide for every
coder is [`CODER_GUIDE.md`](CODER_GUIDE.md). The exporter
`tools/export_public_github_tree.sh` is the only approved way to build
the tree that may be pushed.

## Deny — never publish

| Class | Examples |
|---|---|
| Contracts | `docs/contract/`, invoices, commercial terms, traceability |
| Internal architecture | `docs/memory/`, `docs/phases/`, `internal/`, private topology |
| Session information | transcripts, mesh packets, work-unit ledgers, operator notes |
| Customer private docs | `docs/customer/`, evidence JSON, restore receipts |
| Secrets | `.env`, `*.key` (except `*.pub`), `*.pem`, tokens, passwords |
| Fleet facts | LAN addresses, internal hostnames, site maps, home paths |
| Internal coder ops | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` |

Path-name deny (any matching relative path is a scan failure):

- `docs/contract`, `docs/customer`, `docs/memory`, `docs/phases`
- `docs/governance`, `docs/index`, `internal/`
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
- `.env`, `*.pem`, files named `id_ed25519` or `id_rsa` without `.pub`
- `output/`, `dist/customer-release/`, `tasks/`

Content deny (scan failure even inside an otherwise allowed file):

- Fleet IPv4 literals such as `192.0.2.*` and `ollama.example.internal`
- Internal host labels and share roots
- Private-key PEM headers and common cloud token prefixes

Allowed documentation ranges: `127.0.0.1`, `192.168.0.0/16`,
`10.0.0.0/8`, `172.16.0.0/12`, `192.0.2.0/24`, `ollama.example.internal`.

## Allow — public GitHub tree only

- `LICENSE`, `NOTICE.md`, `CHANGELOG.md`, `VERSION`
- Public `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`,
  `CODE_OF_CONDUCT.md`, `STATUS.md`
- `src/`, `tests/` after the scanner passes (exporter sanitizes fleet
  literals before the scan)
- `docker/Dockerfile.public`, `docker/Dockerfile.arm-overlay`,
  `docker/compose.public.yaml`, `docker/nginx-https-8040.conf`
- `docs/public/`, `docs/brand/`, this GitHub folder
- `docs/adr/` only when the scanner finds no private facts
- `packaging/`, `.github/`
- `pyproject.toml`, `requirements.txt`, `requirements.lock`
- `tools/export_public_github_tree.sh`, `tools/scan_public_github_tree.py`

## Coder rules

1. Do not `git add` a deny-class path into a branch that will be pushed.
2. Do not paste LAN addresses, session IDs, or credentials into README,
   issues, or release notes.
3. If a public file needs an example host, use `ollama.example.internal`
   or `127.0.0.1`, never a fleet address.
4. Private keys created for GitHub stay under
   `~/.local/share/agentiot-github/` (mode 600). Only the **public**
   key may be stored in the public tree.
5. Run the exporter + scanner before every GitHub push.
6. Do not use `tools/build_github_source_and_install.sh` as the GitHub
   tree. It copies private document classes.

## Commands

```bash
./tools/export_public_github_tree.sh
./tools/scan_public_github_tree.py dist/public-github
```

A failing scan is a failed publication. Do not push anyway.
