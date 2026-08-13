# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

"""Collect real edge-node thermal telemetry through the product API."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import signal
import ssl
import sys
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any, Callable
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

METRIC = "temperature_c"
UNIT = "C"
DEFAULT_INTERVAL_SECONDS = 60


class RejectRedirectHandler(HTTPRedirectHandler):
    """Prevent a device credential from following an HTTP redirect."""

    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


def default_endpoint(device_id: str) -> str:
    """Return the local write-only ingestion endpoint for one device."""

    return (
        "https://127.0.0.1:8040/api/devices/"
        f"{quote(device_id, safe='')}/telemetry"
    )


def validate_endpoint(endpoint: str, device_id: str) -> None:
    """Keep the device credential on its local, device-bound TLS endpoint."""

    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}
        or parsed.port != 8040
        or parsed.path != f"/api/devices/{quote(device_id, safe='')}/telemetry"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("telemetry endpoint must be the local HTTPS API")


def read_temperature(path: Path) -> float:
    """Read and normalize a Linux thermal-zone temperature."""

    value = float(path.read_text(encoding="ascii").strip())
    if abs(value) > 200:
        value /= 1000
    if not -50 <= value <= 200:
        raise ValueError("thermal reading is outside the supported range")
    return round(value, 2)


def read_secret(path: Path) -> str:
    """Read a non-empty runtime secret without exposing it to process arguments."""

    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("runtime credential is empty")
    return value


def post_telemetry(
    *,
    endpoint: str,
    device_id: str,
    value: float,
    device_token: str,
    ca_file: Path,
    timeout_seconds: float = 10,
    opener: Callable[..., Any] | None = None,
    context_factory: Callable[..., ssl.SSLContext] = ssl.create_default_context,
    sample_id: str | None = None,
    sampled_at: datetime | None = None,
) -> dict[str, Any]:
    """Post one measured sample and return the accepted API record."""

    validate_endpoint(endpoint, device_id)
    sample_id = sample_id or secrets.token_hex(16)
    sampled_at = sampled_at or datetime.now(UTC)
    if sampled_at.tzinfo is None:
        raise ValueError("sample timestamp must include a timezone")
    payload = json.dumps(
        {
            "device_id": device_id,
            "metric": METRIC,
            "value": value,
            "unit": UNIT,
            "sample_id": sample_id,
            "sampled_at": sampled_at.astimezone(UTC).isoformat(),
        }
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Device-Ingest-Token": device_token,
        },
        method="POST",
    )
    context = context_factory(cafile=str(ca_file))
    if opener is None:
        response_context = build_opener(
            HTTPSHandler(context=context),
            RejectRedirectHandler(),
        ).open(request, timeout=timeout_seconds)
    else:
        response_context = opener(
            request,
            timeout=timeout_seconds,
            context=context,
        )
    with response_context as response:
        if response.status != 201:
            raise RuntimeError("telemetry endpoint rejected the sample")
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict) or "telemetry_id" not in result:
        raise RuntimeError("telemetry endpoint returned an invalid receipt")
    return result


def write_health_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Atomically expose a secret-free liveness receipt for Docker health checks."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def collect_once(
    *,
    endpoint: str,
    device_id: str,
    thermal_path: Path,
    token_path: Path,
    ca_file: Path,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    """Collect one real sample and write an optional health receipt."""

    value = read_temperature(thermal_path)
    result = post_telemetry(
        endpoint=endpoint,
        device_id=device_id,
        value=value,
        device_token=read_secret(token_path),
        ca_file=ca_file,
    )
    receipt = {
        "status": "ok",
        "device_id": device_id,
        "metric": METRIC,
        "value": value,
        "telemetry_id": result["telemetry_id"],
        "collected_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
    if receipt_path is not None:
        write_health_receipt(receipt_path, receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect real edge thermal telemetry")
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(
            os.getenv(
                "AGENTIOT_EDGE_TELEMETRY_INTERVAL",
                str(DEFAULT_INTERVAL_SECONDS),
            )
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 15 <= args.interval <= 3600:
        raise SystemExit("interval must be between 15 and 3600 seconds")

    device_id = os.getenv("AGENTIOT_EDGE_DEVICE_ID", "").strip()
    if not device_id:
        raise SystemExit("AGENTIOT_EDGE_DEVICE_ID is required")
    endpoint = os.getenv(
        "AGENTIOT_EDGE_TELEMETRY_URL",
        default_endpoint(device_id),
    )
    thermal_path = Path(
        os.getenv("AGENTIOT_EDGE_THERMAL_PATH", "/run/host-thermal/temp")
    )
    token_path = Path(
        os.getenv(
            "AGENTIOT_EDGE_DEVICE_TOKEN_FILE",
            "/run/secrets/device_ingest_token",
        )
    )
    ca_file = Path(
        os.getenv("AGENTIOT_EDGE_CA_FILE", "/run/secrets/dashboard-ca.crt")
    )
    receipt_value = os.getenv(
        "AGENTIOT_EDGE_RECEIPT_PATH",
        "/run/agentiot-edge-thermal/last-success.json",
    )
    receipt_path = Path(receipt_value) if receipt_value else None

    stop = Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.is_set():
        try:
            receipt = collect_once(
                endpoint=endpoint,
                device_id=device_id,
                thermal_path=thermal_path,
                token_path=token_path,
                ca_file=ca_file,
                receipt_path=receipt_path,
            )
        except (OSError, ValueError, RuntimeError) as error:
            print(
                json.dumps(
                    {"status": "error", "error_type": type(error).__name__}
                ),
                file=sys.stderr,
                flush=True,
            )
            if args.once:
                return 1
        else:
            if args.once:
                print(json.dumps(receipt, sort_keys=True), flush=True)
                return 0
        stop.wait(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
