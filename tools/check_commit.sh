#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 1.0.0 | Date: 2026-08-13
# Fail-closed commit gate: public-clean scan + tests. Does not push.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "${repo_root}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src

if [ -f AGENTS.md ]; then
  echo "private working tree: export then scan"
  ./tools/export_public_github_tree.sh
  python3 tools/scan_public_github_tree.py dist/public-github
  target="dist/public-github"
else
  echo "public tree: scan in place"
  python3 tools/scan_public_github_tree.py .
  target="."
fi

python3 -m pytest tests/test_public_github_publication.py -q

if [ -d "${target}/src" ]; then
  (
    cd "${target}"
    PYTHONPATH=src python3 -m pytest tests/test_public_github_publication.py -q
  )
fi

echo "commit gate pass"
echo "production_claim: false"
