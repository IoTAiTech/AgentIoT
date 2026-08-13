<!-- SPDX-License-Identifier: MIT -->
# Install guide

Author: Dr. Babak Sarkhpour, with AI assistance  
Version: 0.157.21 | Date: 2026-08-14  
production_claim: false

## Requirements

- Docker Engine 24+ and Docker Compose plugin
- x86_64 **or** aarch64 (ARM64) Linux
- 2 GB RAM minimum (4 GB recommended on ARM boards)
- Outbound HTTPS only if you install from GitHub or npm

Do not put secrets in Git. Create them on the box.

## curl (recommended)

Detects architecture and loads the matching image when a release exists.

```bash
export GITHUB_REPO="IoTAiTech/AgentIoT"
curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/main/packaging/curl/install.sh" | bash
```

Offline: copy `packaging/curl/install.sh` onto the box and run
`sh install.sh --offline /path/to/image.tar`.

## npm

```bash
npm install -g agentiot-greenovax-install
agentiot-install
```

The npm command is a thin wrapper around the same curl installer.

## Docker from source

```bash
git clone https://github.com/IoTAiTech/AgentIoT.git
cd AgentIoT
docker build -t agentiot-greenovax:0.157.21 -f docker/Dockerfile .
cp docker/compose.public.yaml docker-compose.yaml
# edit environment values; never commit secrets
docker compose up -d
```

ARM64 source build:

```bash
docker build --platform linux/arm64 -t agentiot-greenovax:0.157.21-arm64 -f docker/Dockerfile .
```

## First sign-in

1. Open the published HTTPS or HTTP URL for the box.
2. Sign in with the administrator identity created at deploy time.
3. Change the administrator password immediately.
4. Confirm `/api/version` shows **0.157.21** on every box.

## Same version on every box

x86 and ARM must report the same version string. If they differ, rebuild or
reload the matching image. Do not mix tags.

## Uninstall

```bash
docker compose -f docker/compose.public.yaml down
docker image rm agentiot-greenovax:0.157.21 agentiot-greenovax:0.157.21-arm64 || true
```
