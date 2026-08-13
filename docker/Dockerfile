# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.20 | Date: 2026-08-13
# Public image. Does not copy contracts, customer packs, or internal docs.
# production_claim: false

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
LABEL org.opencontainers.image.title="AgentIoT Dashboard" \
      org.opencontainers.image.vendor="GreeNovaX" \
      org.opencontainers.image.authors="IoT-AI.Tech" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir --upgrade "pip==26.1.2" \
    && pip install --no-cache-dir --require-hashes -r requirements.lock

ARG AGENTIOT_SOURCE_COMMIT=unknown
ENV AGENTIOT_SOURCE_COMMIT=${AGENTIOT_SOURCE_COMMIT}

RUN addgroup -S agentiot \
    && adduser -S -D -H -G agentiot agentiot \
    && mkdir -p /app/output /app/data \
    && chown -R agentiot:agentiot /app

COPY --chown=agentiot:agentiot src ./src
COPY --chown=agentiot:agentiot README.md CHANGELOG.md LICENSE NOTICE.md VERSION ./
COPY --chown=agentiot:agentiot docs/public ./docs/public
COPY --chown=agentiot:agentiot docs/brand ./docs/brand
COPY --chown=agentiot:agentiot docs/adr ./docs/adr
RUN chmod -R a+rX /app/src /app/docs \
    && chmod a+r /app/README.md /app/CHANGELOG.md /app/LICENSE /app/NOTICE.md /app/VERSION

ENV PYTHONPATH=/app/src
EXPOSE 8080
USER agentiot
CMD ["uvicorn", "agentiot.app:app", "--host", "0.0.0.0", "--port", "8080"]
