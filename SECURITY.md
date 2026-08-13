<!-- SPDX-License-Identifier: MIT -->
# Security

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 1.0.0 | Date: 2026-08-13  
production_claim: false

## Supported versions

| Version | Support |
|---|---|
| 0.157.x | Development preview only |

This cut is not a production claim.

## Reporting a vulnerability

Email the contractor security contact named in `NOTICE.md`. Do not open
a public issue that contains secrets, customer data, or exploit details.

## What this repository must never contain

- Private keys, `.env` files, tokens, passwords
- Contracts, invoices, and internal architecture
- Session transcripts and operator ledgers
- Fleet addresses and internal host names

See [docs/github/PUBLICATION_POLICY.md](docs/github/PUBLICATION_POLICY.md).

## Deploy-time secrets

Create secrets on the target host. Pass them through environment files
or Docker secrets. Never commit them.
