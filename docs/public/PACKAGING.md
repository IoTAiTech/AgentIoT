<!-- SPDX-License-Identifier: MIT -->
# Packaging

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 0.157.20 | Date: 2026-08-13  
production_claim: false

## Artifacts

| Artifact | Use |
|---|---|
| Source tree (public export) | GitHub repository root |
| `agentiot-greenovax:VERSION` | x86_64 Docker image |
| `agentiot-greenovax:VERSION-arm64` | ARM64 Docker image |
| `packaging/curl/install.sh` | One-line box install |
| `packaging/npm/` | npm wrapper for the same install |

Every coder must follow [docs/github/CODER_GUIDE.md](../github/CODER_GUIDE.md)
before a GitHub commit. Private contracts, internal architecture, and
session data are never part of this package.

## Build public source

```bash
./tools/export_public_github_tree.sh
./tools/scan_public_github_tree.py "$PWD/dist/public-github"
```

## Build images

```bash
docker build -t agentiot-greenovax:0.157.20 -f docker/Dockerfile .
docker build --platform linux/arm64 -t agentiot-greenovax:0.157.20-arm64 -f docker/Dockerfile .
docker save agentiot-greenovax:0.157.20 | gzip > dist/agentiot-greenovax-0.157.20-amd64.tar.gz
docker save agentiot-greenovax:0.157.20-arm64 | gzip > dist/agentiot-greenovax-0.157.20-arm64.tar.gz
```

Attach those files to a GitHub Release after the repository exists.

## npm

The package `agentiot-greenovax-install` only fetches the installer. It
does not embed private documents.
