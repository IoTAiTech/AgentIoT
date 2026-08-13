#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.21 | Date: 2026-08-14
# Public box installer for x86_64 and aarch64. No private documents.
set -euo pipefail

VERSION="${AGENTIOT_VERSION:-0.157.21}"
GITHUB_REPO="${GITHUB_REPO:-IoTAiTech/AgentIoT}"
IMAGE_NAME="${AGENTIOT_IMAGE_NAME:-agentiot-greenovax}"
INSTALL_DIR="${AGENTIOT_INSTALL_DIR:-${PWD}/agentiot-greenovax}"

arch="$(uname -m)"
case "${arch}" in
  x86_64|amd64) tag="${VERSION}"; asset="agentiot-greenovax-${VERSION}-amd64.tar.gz" ;;
  aarch64|arm64) tag="${VERSION}-arm64"; asset="agentiot-greenovax-${VERSION}-arm64.tar.gz" ;;
  *)
    echo "unsupported architecture: ${arch}" >&2
    exit 2
    ;;
esac

offline=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --offline)
      offline="${2:-}"
      shift 2
      ;;
    --version)
      VERSION="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

if [ -n "${offline}" ]; then
  docker load -i "${offline}"
else
  if docker pull "${IMAGE_NAME}:${tag}" 2>/dev/null; then
    :
  else
    echo "No published image yet. After GitHub Releases exist, this script loads ${asset}."
    echo "Offline: sh install.sh --offline /path/to/${asset}"
  fi
fi

if [ ! -f compose.yaml ]; then
  if [ -f "${GITHUB_REPO}" ]; then
    :
  fi
  cat > compose.yaml <<EOF
services:
  agentiot:
    image: ${IMAGE_NAME}:${tag}
    ports:
      - "127.0.0.1:8080:8080"
    environment:
      AGENTIOT_OLLAMA_PRIMARY_URL: "\${AGENTIOT_OLLAMA_PRIMARY_URL:-http://ollama.example.internal:11434}"
    volumes:
      - agentiot_data:/app/data
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=64m
volumes:
  agentiot_data:
EOF
fi

echo "Install directory: ${INSTALL_DIR}"
echo "Architecture: ${arch}"
echo "Image tag: ${IMAGE_NAME}:${tag}"
echo "Set AGENTIOT_OLLAMA_PRIMARY_URL to your private model host, then:"
echo "  docker compose up -d"
echo "production_claim: false"
