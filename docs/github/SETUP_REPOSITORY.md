<!-- SPDX-License-Identifier: MIT -->
# Set up the public GitHub repository

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 1.0.0 | Date: 2026-08-13  
production_claim: false

Follow this after `CODER_GUIDE.md`. Do not initialize GitHub from the
private working tree.

## 1. Export and scan

```bash
./tools/export_public_github_tree.sh
./tools/scan_public_github_tree.py dist/public-github
```

Stop if the scanner exits non-zero.

## 2. Create an empty GitHub repository

Create an empty repository (no README, no license, no `.gitignore`).
Those files already exist in the export.

## 3. Publish from the export only

```bash
cd dist/public-github
git init
git add .
git status   # review: no docs/contract, docs/customer, AGENTS.md
git commit -m "chore: import public AgentIoT 0.157.20 source"
git branch -M main
git remote add origin git@github.com:OWNER/REPO.git
git push -u origin main
```

Replace `OWNER/REPO` with the real GitHub path.

## 4. Deploy key

1. Operator keeps the private key at
   `~/.local/share/agentiot-github/github_deploy_ed25519` (mode 600).
2. GitHub → Settings → Deploy keys → add
   `docs/github/github_deploy.pub`.
3. Grant write access only if this key will push. Prefer a
   read-only key plus a separate CI identity.
4. Never commit the private key.

## 5. First release

1. Tag `v0.157.20` on the **public** repository after the scan is green.
2. Attach architecture image archives built from `Dockerfile.public`.
3. Point `packaging/curl/install.sh` `GITHUB_REPO` at `OWNER/REPO`.

## 6. Later versions

Repeat export → scan → commit from the new export. Do not merge the
private working tree into the public remote.
