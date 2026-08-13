#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 1.0.0 | Date: 2026-08-13
# Build the only tree that may be pushed to GitHub.
# Allowlist copy + sanitize + fail-closed scan. Does not push.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
dest="${1:-${repo_root}/dist/public-github}"
scanner="${repo_root}/tools/scan_public_github_tree.py"

rm -rf "${dest}"
mkdir -p "${dest}"

copy_file() {
  local rel="$1"
  local src="${repo_root}/${rel}"
  if [ ! -e "${src}" ]; then
    return 0
  fi
  mkdir -p "${dest}/$(dirname "${rel}")"
  cp -a "${src}" "${dest}/${rel}"
}

copy_tree() {
  local rel="$1"
  local src="${repo_root}/${rel}"
  if [ ! -d "${src}" ]; then
    return 0
  fi
  mkdir -p "${dest}/${rel}"
  # Copy files but drop bytecode and editor junk.
  tar -C "${src}" --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' \
    -cf - . | tar -C "${dest}/${rel}" -xf -
}

# Allowlist only. Deny-class trees are never copied.
copy_file LICENSE
copy_file NOTICE.md
copy_file CHANGELOG.md
copy_file VERSION
copy_file README.md
copy_file STATUS.md
copy_file CONTRIBUTING.md
copy_file SECURITY.md
copy_file SUPPORT.md
copy_file CODE_OF_CONDUCT.md
copy_file pyproject.toml
copy_file requirements.txt
copy_file requirements.lock

copy_tree src
copy_tree tests
copy_tree docs/public
copy_tree docs/brand
copy_tree docs/adr
copy_tree docs/github
copy_tree packaging
copy_tree .github

mkdir -p "${dest}/docker" "${dest}/tools"
copy_file docker/Dockerfile.public
copy_file docker/Dockerfile.arm-overlay
copy_file docker/compose.public.yaml
copy_file docker/nginx-https-8040.conf
copy_file tools/export_public_github_tree.sh
copy_file tools/scan_public_github_tree.py
copy_file tools/check_commit.sh

# Public compose is the only compose file in the export.
if [ -f "${dest}/docker/compose.public.yaml" ]; then
  cp -a "${dest}/docker/compose.public.yaml" "${dest}/docker/compose.yaml"
fi

# Public Dockerfile is the image default in the export.
if [ -f "${dest}/docker/Dockerfile.public" ]; then
  cp -a "${dest}/docker/Dockerfile.public" "${dest}/docker/Dockerfile"
fi

cat > "${dest}/.gitignore" <<'EOF'
.venv/
__pycache__/
*.pyc
.pytest_cache/
.env
*.pem
id_rsa
id_ed25519
github_deploy_ed25519
dist/
output/
*.sqlite
EOF

# Never let a private key land in the export, even if one was copied by mistake.
find "${dest}" -type f \( -name 'id_ed25519' -o -name 'id_rsa' -o -name 'github_deploy_ed25519' -o -name '*.pem' \) -delete

python3 "${scanner}" --sanitize-in-place "${dest}"

printf 'exported public tree: %s\n' "${dest}"
