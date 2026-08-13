<!-- SPDX-License-Identifier: MIT -->
# Project: AgentIoT Dashboard
# Customer: GreeNovaX
# Contractor: IoT-AI.Tech
# Version: 0.157.10
# Date: 2026-08-11
# Language: English
# License: MIT

# NOTICE

This project is an independent clean-room implementation. Prepared for GreeNovaX by IoT-AI.Tech.

## Third-Party Dependencies

| Component | Use | License family | Release gate |
|---|---|---|---|
| Python | Runtime | PSF | Runtime base image verified for version 3.12.13 |
| Hatchling | Build backend | MIT | Development/build backend; not installed in runtime image |
| FastAPI | Backend API framework | MIT | Runtime image version verified below |
| Pydantic | Data validation | MIT | Runtime image version verified below |
| PyJWT | JWT validation | MIT | Runtime image version verified below |
| cryptography | RS256/JWKS validation support | Apache-2.0 OR BSD-3-Clause | Runtime image version verified below |
| gmqtt | Optional MQTT broker subscriber | MIT | Runtime image version verified below |
| Starlette | ASGI layer via FastAPI | BSD-3-Clause | Runtime image version verified below |
| Uvicorn | ASGI server | BSD-3-Clause | Runtime image version verified below |
| pytest | Test runner | MIT | Development dependency only |
| httpx | Test client transport | BSD-3-Clause | Development dependency only |
| NGINX | Optional HTTPS reverse proxy container | BSD-2-Clause | Runtime helper image; not bundled into the application image |

## Runtime Dependency Audit - Version 0.157.10

Audit command basis: package metadata from the Docker runtime image using `python -m pip show`.

| Package | Version | License metadata |
|---|---:|---|
| fastapi | 0.138.1 | MIT |
| starlette | 1.3.1 | BSD-3-Clause |
| pydantic | 2.13.4 | MIT |
| pydantic_core | 2.46.4 | MIT |
| uvicorn | 0.49.0 | BSD-3-Clause |
| PyJWT | 2.13.0 | MIT |
| cryptography | 48.0.1 | Apache-2.0 OR BSD-3-Clause |
| gmqtt | 0.7.0 | MIT |
| cffi | 2.0.0 | MIT |
| pycparser | 3.0 | BSD-3-Clause |
| anyio | 4.14.1 | MIT |
| click | 8.4.2 | BSD-3-Clause |
| h11 | 0.16.0 | MIT |
| httptools | 0.8.0 | MIT |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| uvloop | 0.22.1 | MIT |
| watchfiles | 1.2.0 | MIT |
| websockets | 16.0 | BSD-3-Clause |
| typing_extensions | 4.15.0 | PSF-2.0 |
| typing-inspection | 0.4.2 | MIT |
| annotated-types | 0.7.0 | MIT classifier |
| annotated-doc | 0.0.4 | MIT |
| idna | 3.18 | BSD-3-Clause |

Compatibility result: PASS for MIT delivery basis. No incompatible strong copyleft runtime dependency was identified in the audited runtime image.

## Background and Foreground IP Boundary

- Foreground IP is the project-specific source code, tests, runtime configuration, and customer documentation authored for this product and released under MIT.
- Background IP includes contractor methods, reusable engineering know-how, confidential authoring material, and non-deliverable tooling. It is not transferred in the customer bundle.
- Third-party components remain governed by their own licenses as listed above.
- This technical classification supports clean release packaging and does not amend the signed contract or any mandatory ownership term.

## Clean-Room Notice

No legacy product code, documentation text, comments, route names, non-product operating material, or private administrative details are approved for transfer into this repository.

## Audit Requirement

Before every contracted delivery release, rerun the dependency and license audit and update this file with exact package versions.
