# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-08-09

"""Fail-closed provider network policy regression tests."""

import pytest

import agentiot.app as app_module


@pytest.mark.parametrize(
    ("family", "ip_value"),
    [
        pytest.param(app_module.socket.AF_INET, "100.64.0.1", id="cgnat-ipv4"),
        pytest.param(
            app_module.socket.AF_INET6,
            "::ffff:100.64.0.1",
            id="cgnat-ipv4-mapped-ipv6",
        ),
    ],
)
def test_cloud_target_rejects_non_global_addresses_before_socket_creation(
    monkeypatch,
    family,
    ip_value,
) -> None:
    socket_created = False

    def fake_getaddrinfo(host, port, type=None):
        sockaddr = (
            (ip_value, port)
            if family == app_module.socket.AF_INET
            else (ip_value, port, 0, 0)
        )
        return [(family, app_module.socket.SOCK_STREAM, 6, "", sockaddr)]

    def fail_socket(*_args, **_kwargs):
        nonlocal socket_created
        socket_created = True
        raise AssertionError("socket must not be created")

    monkeypatch.setattr(app_module.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(app_module.socket, "socket", fail_socket)

    with pytest.raises(ValueError, match="resolves to private network"):
        app_module.validated_cloud_provider_target(
            "openai",
            "https://api.openai.com/v1/responses",
        )
    assert socket_created is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("100.64.0.0", True),
        ("100.127.255.255", True),
        ("100.63.255.255", False),
        ("100.128.0.0", False),
        ("::ffff:100.64.0.1", True),
        ("::ffff:127.0.0.1", True),
        ("::ffff:169.254.169.254", True),
        ("::ffff:8.8.8.8", False),
    ],
)
def test_cloud_address_global_reachability_policy(value, expected) -> None:
    assert app_module.unsafe_network_address(value) is expected
