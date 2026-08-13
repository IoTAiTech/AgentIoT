<!-- SPDX-License-Identifier: MIT -->
# AgentIoT Dashboard

<p align="center">
  <img src="docs/brand/greenovax-logo-horizontal.png" alt="GreeNovaX" height="56">
  &nbsp;&nbsp;
  <img src="docs/brand/iot-ai-tech-company-logo.png" alt="IoT-AI.Tech" height="56">
</p>

> Version **0.157.21** · License **MIT** · Prepared for **GreeNovaX** by **IoT-AI.Tech**  
> Status: development preview · `production_claim: false`

**AgentIoT Dashboard** is an AI-powered, fault-tolerant IoT monitoring
portal. It unifies multi-vendor device monitoring, agentic fault
detection, and operator-approved recovery so heterogeneous IoT
environments become more transparent, resilient, and easier to manage.

This public text follows the GreeNovaX LinkedIn product posts
([announcement](https://www.linkedin.com/posts/greenovax_aiagent-efrenrw-euinmyregion-activity-7471229081251053568-qp94),
[collaboration](https://www.linkedin.com/posts/greenovax_fault-iot-monitoring-activity-7479850814988156928-CEsN)).
Full public product page: [docs/public/ABOUT.md](docs/public/ABOUT.md).

## Why it exists

IoT sites in homes, commercial buildings, and light industry are still
run through fragmented, vendor-specific dashboards. Operators switch
systems just to check status, diagnose faults, or start a correction.
That hides the fleet, raises cost, and shortens device life when a
vendor drops support.

AgentIoT is a practical prototype for more sustainable use of connected
devices: keep existing hardware working, extend lifetimes, and reduce
unnecessary electronic waste (circular economy).

## Capabilities

- Unified monitoring of heterogeneous, multi-vendor IoT devices
- AI-agent anomaly detection and automated diagnosis
- Agent-proposed corrective actions (self-healing stays behind human approval)
- Secure central web cockpit with asset and configuration management
- Edge-native runtime for x86_64 and ARM64
- Grounded operator assistant with Finding / Evidence / Agents / Next review / Approval

| Layer | Choice |
|---|---|
| API | Python FastAPI |
| Runtime | Docker |
| Store | SQLite |
| UI | Server-rendered operations cockpit |
| Assistant | Grounded local model with evidence labels |

AgentIoT is an independent MIT-licensed product. It does not share
another product's contracts or source trees.

## Organisations

| | |
|---|---|
| Product | [GreeNovaX](https://www.linkedin.com/company/greenovax) · [greenovax.de](https://www.greenovax.de) · Green Innovative Tech (X) Made in Germany |
| Contractor | [IoT-AI.Tech](https://www.linkedin.com/company/iot-ai-tech) · [IoT-AI.Tech](https://IoT-AI.Tech) · Dr.-Ing. Babak Sorkhpour |

## Documentation

| Document | Path |
|---|---|
| About the product | [docs/public/ABOUT.md](docs/public/ABOUT.md) |
| Install | [docs/public/INSTALL.md](docs/public/INSTALL.md) |
| Operator manual | [docs/public/OPERATOR_MANUAL.md](docs/public/OPERATOR_MANUAL.md) |
| Help | [docs/public/HELP.md](docs/public/HELP.md) |
| Development status | [STATUS.md](STATUS.md) |
| Packaging | [docs/public/PACKAGING.md](docs/public/PACKAGING.md) |
| Coder publication guide | [docs/github/CODER_GUIDE.md](docs/github/CODER_GUIDE.md) |
| What may be published | [docs/github/PUBLICATION_POLICY.md](docs/github/PUBLICATION_POLICY.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |

## Install

### curl (x86_64 or ARM64)

```bash
export GITHUB_REPO="IoTAiTech/AgentIoT"
curl -fsSL https://raw.githubusercontent.com/IoTAiTech/AgentIoT/main/packaging/curl/install.sh | bash
```

### npm

```bash
export GITHUB_REPO="IoTAiTech/AgentIoT"
npx agentiot-greenovax-install
```

### Docker from this tree

```bash
docker build -t agentiot-greenovax:0.157.21 -f docker/Dockerfile .
docker compose -f docker/compose.public.yaml up -d
```

Both architectures must report the same `/api/version` field.

## Usage

1. Sign in as the deployment administrator.
2. Open the operations cockpit.
3. Register assets and devices, then ingest telemetry.
4. Review alerts. Approve recovery only after physical checks.

Default local HTTP port after compose: `8080`.

## Development and commit gate

Every commit that can leave this host must be public-clean and tested.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
./tools/check_commit.sh
```

`tools/check_commit.sh` runs the publication scan and the approved
pytest set. A failing scan is a failed commit.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

Marks: GreeNovaX (product) and IoT-AI.Tech (contractor). Logos live in
[docs/brand/](docs/brand/).
