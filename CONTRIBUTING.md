<!-- SPDX-License-Identifier: MIT -->
# Contributing

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 1.0.0 | Date: 2026-08-13  
production_claim: false

Thank you for helping AgentIoT. This public repository contains **only**
customer-safe source, tests, and manuals.

## Publication rule (binding)

Do not add private project documents. Internal architecture, contracts,
session information, fleet addresses, secrets, and operator notes are
out of scope for this repository.

Read [docs/github/CODER_GUIDE.md](docs/github/CODER_GUIDE.md) and
[docs/github/PUBLICATION_POLICY.md](docs/github/PUBLICATION_POLICY.md)
before every commit.

```bash
./tools/export_public_github_tree.sh
./tools/scan_public_github_tree.py dist/public-github
```

A failing scan must not be pushed.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python3 -m pytest
```

## Pull requests

- Keep diffs small and related to one change.
- Do not introduce LAN addresses or credentials.
- Update `CHANGELOG.md` and `VERSION` when behaviour changes.
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
