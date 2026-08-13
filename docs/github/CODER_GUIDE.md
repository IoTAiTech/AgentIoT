<!-- SPDX-License-Identifier: MIT -->
# Coder guide — public GitHub commits stay clean

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 1.0.0 | Date: 2026-08-13  
Audience: every coder (Claude · Codex · Gemini · Grok · human)  
Status: **binding**  
production_claim: false

## Founder order (2026-08-13)

Do **not** upload project-private documents to GitHub. Internal
architecture, contracts, session information, and every other sensitive
class stay off the public repository. **Every commit that can leave this
host must be completely clear of sensitive data.**

This file is the operating guide for that order. The allow/deny list is
[`PUBLICATION_POLICY.md`](PUBLICATION_POLICY.md). Project rule A1.1 in
`AGENTS.md` points here.

## What "clear" means

A GitHub commit, tag, release asset, or install package is **clear** only
when all of the following are true:

1. No deny-class **path** is present.
2. No deny-class **content** is present (fleet addresses, secrets,
   session identifiers, contract text, internal topology).
3. `tools/scan_public_github_tree.py` exits 0 on the tree that will be
   pushed.
4. The tree was built with `tools/export_public_github_tree.sh`, not by
   copying the working tree.

A green unit-test run on the private working tree does **not** make that
working tree GitHub-safe.

## Deny classes (never publish)

| Class | Keep on the private host only |
|---|---|
| Contracts | `docs/contract/`, invoices, commercial terms, traceability |
| Internal architecture | `docs/memory/`, `docs/phases/`, `internal/`, private topology |
| Session information | transcripts, mesh packets, work-unit ledgers, operator notes |
| Customer private packs | `docs/customer/`, evidence JSON, restore receipts |
| Secrets | `.env`, private keys, tokens, passwords, PEM files |
| Fleet facts | LAN addresses, internal hostnames, site maps, share paths |
| Internal coder ops | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, coder mesh state |

If you are unsure, it is **deny**. Ask before adding a new public path.

## Allow classes (public GitHub only)

- License and identity: `LICENSE`, `NOTICE.md`, `CHANGELOG.md`, `VERSION`
- Public manuals: `README.md`, `STATUS.md`, `docs/public/`, `docs/brand/`
- This GitHub folder: `docs/github/` (policy, this guide, public key only)
- Source and tests **after** the scanner passes
- Public Docker files: `docker/Dockerfile.public`, `docker/compose.public.yaml`
- Packaging: `packaging/`, `.github/`
- Build metadata: `pyproject.toml`, `requirements.txt`, `requirements.lock`

Example hosts in public files must be `127.0.0.1`, `ollama.example.internal`,
or RFC 5737 documentation addresses (`192.0.2.0/24`). Never a fleet address.

## Required workflow (every coder, every version)

```text
1. Finish the private-host change in the working tree.
2. Export:  ./tools/export_public_github_tree.sh
3. Scan:    ./tools/scan_public_github_tree.py dist/public-github
4. Inspect the scan receipt. Exit 0 is required.
5. Commit and push **only** from the exported tree (or a clone of it).
6. Never `git add -A` in the private working tree for a GitHub remote.
```

A failing scan is a failed publication. Do not push anyway. Do not
weaken the scanner to force a green result.

## Forbidden shortcuts

- Do not use `tools/build_github_source_and_install.sh` as the GitHub
  tree. That helper copies contract and customer documents.
- Do not copy `docker/compose.yaml` to GitHub. It is a private-host
  compose file. Use `docker/compose.public.yaml`.
- Do not copy `docker/Dockerfile` to GitHub. It embeds private document
  trees. Use `docker/Dockerfile.public`.
- Do not store a private SSH key in the repository. Only
  `docs/github/github_deploy.pub` may be public.
- Do not paste session IDs, mesh refs, or work-unit ledgers into README,
  issues, or release notes.

## Private key custody

Deploy keys live only under the operator home:

```text
~/.local/share/agentiot-github/github_deploy_ed25519      mode 600
~/.local/share/agentiot-github/github_deploy_ed25519.pub  public copy
```

GitHub Settings → Deploy keys receives the **public** key. The private
key never enters git, chat, or a report.

## How to add a new public file

1. Confirm it is not a deny class.
2. Add it to the allow list in `PUBLICATION_POLICY.md`.
3. Add it to the exporter allow list.
4. Re-run export + scan.
5. Record the path in `CHANGELOG.md` without private facts.

## Review duty

Before any GitHub push, every coder (including the author) must be able
to answer "yes" to:

- Did the exporter build this tree?
- Did the scanner exit 0?
- Would I be willing to show every file to a stranger on the internet?

If any answer is no, stop.

## Related files

| File | Role |
|---|---|
| [`PUBLICATION_POLICY.md`](PUBLICATION_POLICY.md) | Allow/deny list |
| [`SETUP_REPOSITORY.md`](SETUP_REPOSITORY.md) | Create the GitHub repository |
| `AGENTS.md` §A1.1 | Project-binding pointer (private host) |
| `CONTRIBUTING.md` | Public contributor summary |
