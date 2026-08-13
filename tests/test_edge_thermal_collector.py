# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.157.10 | Date: 2026-08-13

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentiot import edge_thermal_collector as collector
from agentiot.edge_thermal_collector import (
    RejectRedirectHandler,
    default_endpoint,
    post_telemetry,
    read_secret,
    read_temperature,
    validate_endpoint,
)


class FakeResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return b'{"telemetry_id": 17}'


def test_reads_millidegree_linux_thermal_sensor(tmp_path) -> None:
    sensor = tmp_path / "temp"
    sensor.write_text("52777\n", encoding="ascii")

    assert read_temperature(sensor) == 52.78


def test_reads_secret_without_returning_whitespace(tmp_path) -> None:
    secret = tmp_path / "device_ingest_token"
    secret.write_text("runtime-secret\n", encoding="utf-8")

    assert read_secret(secret) == "runtime-secret"


def test_posts_real_temperature_with_token_only_in_header(tmp_path) -> None:
    captured = {}

    def opener(request, *, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return FakeResponse()

    result = post_telemetry(
        endpoint=(
            "https://127.0.0.1:8040/api/devices/edge-thermal-1/telemetry"
        ),
        device_id="edge-thermal-1",
        value=52.78,
        device_token="runtime-secret",
        ca_file=tmp_path / "ca.crt",
        opener=opener,
        context_factory=lambda **_kwargs: object(),
        sample_id="a" * 32,
        sampled_at=datetime(2026, 8, 11, 12, 0, tzinfo=UTC),
    )

    request = captured["request"]
    payload = json.loads(request.data.decode("utf-8"))
    assert result == {"telemetry_id": 17}
    assert payload["device_id"] == "edge-thermal-1"
    assert payload["metric"] == "temperature_c"
    assert payload["value"] == 52.78
    assert payload["sample_id"] == "a" * 32
    assert payload["sampled_at"] == "2026-08-11T12:00:00+00:00"
    assert request.get_header("X-device-ingest-token") == "runtime-secret"
    assert "runtime-secret" not in request.full_url


def test_rejects_remote_or_ambiguous_token_destinations() -> None:
    device_id = "edge-thermal-1"
    for endpoint in (
        "http://127.0.0.1:8040/api/devices/edge-thermal-1/telemetry",
        "https://127.0.0.1:8080/api/devices/edge-thermal-1/telemetry",
        "https://127.0.0.1:8443/api/devices/edge-thermal-1/telemetry",
        "https://127.0.0.1:8040/api/devices/edge-thermal-1/telemetry?target=remote",
        "https://127.0.0.1:8040/api/devices",
        "https://127.0.0.1:8040/api/devices/another-device/telemetry",
    ):
        with pytest.raises(ValueError, match="local HTTPS API"):
            validate_endpoint(endpoint, device_id)


def test_production_opener_rejects_redirects(tmp_path, monkeypatch) -> None:
    captured = {}

    class FakeDirector:
        def open(self, request, *, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

    def fake_build_opener(*handlers):
        captured["handlers"] = handlers
        return FakeDirector()

    monkeypatch.setattr(collector, "build_opener", fake_build_opener)
    result = post_telemetry(
        endpoint="https://127.0.0.1:8040/api/devices/edge-thermal-1/telemetry",
        device_id="edge-thermal-1",
        value=52.78,
        device_token="runtime-secret",
        ca_file=tmp_path / "ca.crt",
        context_factory=lambda **_kwargs: object(),
        sample_id="b" * 32,
        sampled_at=datetime(2026, 8, 11, 12, 0, tzinfo=UTC),
    )

    assert result == {"telemetry_id": 17}
    assert any(isinstance(item, RejectRedirectHandler) for item in captured["handlers"])


def test_default_endpoint_is_bound_to_the_selected_device() -> None:
    endpoint = default_endpoint("edge-thermal-1")

    assert endpoint == (
        "https://127.0.0.1:8040/api/devices/edge-thermal-1/telemetry"
    )
    validate_endpoint(endpoint, "edge-thermal-1")


def test_launcher_applies_edge_resource_and_secret_controls() -> None:
    launcher = Path("docker/launch_edge_thermal_collector.sh").read_text(
        encoding="utf-8"
    )

    for expected in (
        "--read-only",
        "--cap-drop ALL",
        "--security-opt no-new-privileges:true",
        "--pids-limit 32",
        "--memory 64m",
        "--cpus 0.10",
        '${device_token_file}:/run/secrets/device_ingest_token:ro',
        "AGENTIOT_EDGE_DEVICE_TOKEN_FILE=/run/secrets/device_ingest_token",
        "AGENTIOT_SOURCE_COMMIT",
        "AGENTIOT_RUNTIME_DIGEST",
        "compute_customer_runtime_digest.py",
        'image_id="$(docker image inspect',
        '"${image_id}"',
        "--once",
    ):
        assert expected in launcher
    assert "X-Operator-Token" not in launcher
    assert "operator_token" not in launcher
    environment_start = launcher.index('image_environment="$(')
    environment_end = launcher.index('image_source_commit="$(')
    environment_block = launcher[environment_start:environment_end]
    assert '"${image_id}"' in environment_block
    assert '"${image}"' not in environment_block
