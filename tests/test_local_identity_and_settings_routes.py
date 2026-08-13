# SPDX-License-Identifier: MIT
# Author: Dr. Babak Sarkhpour, with AI assistance
# Version: 0.156.0 | Date: 2026-07-29

"""Regression tests for local browser identity and routed administration."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from fastapi.testclient import TestClient

from agentiot import app as app_module
from agentiot.app import create_app


ADMIN_TOKEN = "a" * 64
SESSION_SECRET = "s" * 64
INITIAL_ADMIN_PASSWORD = "Initial-Admin-Password-2026"
REPLACEMENT_ADMIN_PASSWORD = "Replacement-Admin-Password-2026"
OPERATOR_PASSWORD = "Operator-Password-2026"
RESET_OPERATOR_PASSWORD = "Reset-Operator-Password-2026"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def configure_local_identity(monkeypatch, *, production: bool = False) -> None:
    monkeypatch.setenv("AGENTIOT_ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", INITIAL_ADMIN_PASSWORD)
    monkeypatch.setenv("AGENTIOT_SESSION_SECRET", SESSION_SECRET)
    monkeypatch.setenv("AGENTIOT_ENV", "production" if production else "development")
    if production:
        monkeypatch.setenv("AGENTIOT_ALLOWED_HOSTS", "testserver")


def test_password_login_uses_secure_session_without_exposing_admin_token(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "identity.db"))

    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    session = client.get("/api/auth/session")
    admin_read = client.get("/api/admin/access/local-users")

    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert login.json()["role"] == "admin"
    assert "session_token" not in login.json()
    assert ADMIN_TOKEN not in login.text
    assert INITIAL_ADMIN_PASSWORD not in login.text
    assert "agentiot_session=" in login.headers["set-cookie"]
    assert "HttpOnly" in login.headers["set-cookie"]
    assert session.json()["authenticated"] is True
    assert session.json()["username"] == "admin"
    assert admin_read.status_code == 200


def test_self_service_password_change_revokes_old_session_and_password(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "self-password.db"))
    assert client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200

    changed = client.patch(
        "/api/auth/me/password",
        json={
            "current_password": INITIAL_ADMIN_PASSWORD,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
        },
    )
    stale_session = client.get("/api/auth/session")
    old_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    new_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": REPLACEMENT_ADMIN_PASSWORD},
    )

    assert changed.status_code == 200
    assert changed.json()["status"] == "password_changed"
    assert stale_session.json()["authenticated"] is False
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_admin_reset_is_separate_from_idp_assignment_and_revokes_sessions(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    app = create_app(database_path=tmp_path / "admin-reset.db")
    admin = TestClient(app)
    operator = TestClient(app)
    assert admin.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200
    created = admin.post(
        "/api/admin/access/local-users",
        json={
            "username": "operator-one",
            "password": OPERATOR_PASSWORD,
            "role": "operator",
        },
    )
    assert created.status_code == 201
    assert created.json()["item"]["password_change_required"] is True
    assert operator.post(
        "/api/auth/login",
        json={"username": "operator-one", "password": OPERATOR_PASSWORD},
    ).status_code == 200

    reset = admin.patch(
        "/api/admin/access/local-users/operator-one/password",
        json={"new_password": RESET_OPERATOR_PASSWORD},
    )
    stale = operator.get("/api/auth/session")
    old_login = operator.post(
        "/api/auth/login",
        json={"username": "operator-one", "password": OPERATOR_PASSWORD},
    )
    new_login = operator.post(
        "/api/auth/login",
        json={"username": "operator-one", "password": RESET_OPERATOR_PASSWORD},
    )
    users = admin.get("/api/admin/access/local-users")

    assert reset.status_code == 200
    assert stale.json()["authenticated"] is False
    assert old_login.status_code == 401
    assert new_login.status_code == 200
    assert new_login.json()["password_change_required"] is True
    operator_record = next(
        item for item in users.json()["items"] if item["username"] == "operator-one"
    )
    assert operator_record["role"] == "operator"
    assert operator_record["enabled"] is True
    assert "password_hash" not in users.text
    assert "password_salt" not in users.text


def test_identity_contract_rejects_unknown_fields_and_protects_last_admin(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "identity-policy.db"))
    assert client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200

    unknown = client.patch(
        "/api/auth/me/password",
        json={
            "current_password": INITIAL_ADMIN_PASSWORD,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
            "unexpected": "blocked",
        },
    )
    disable = client.patch(
        "/api/admin/access/local-users/admin",
        json={"role": "admin", "enabled": False},
    )
    delete = client.delete("/api/admin/access/local-users/admin")

    assert unknown.status_code == 422
    assert disable.status_code == 409
    assert delete.status_code == 409


def test_machine_admin_token_remains_valid_but_is_not_required_by_browser(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "api-token.db"))

    token_response = client.get(
        "/api/admin/access/local-users",
        headers={"X-Admin-Token": ADMIN_TOKEN},
    )
    no_identity = client.get("/api/admin/access/local-users")

    assert token_response.status_code == 200
    assert no_identity.status_code == 401


def test_production_html_routes_require_login_and_keep_deep_link(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch, production=True)
    client = TestClient(
        create_app(database_path=tmp_path / "production-login.db"),
        base_url="https://testserver",
    )

    denied = client.get("/settings/access", follow_redirects=False)
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    allowed = client.get("/settings/access")

    assert denied.status_code == 303
    assert denied.headers["location"].startswith("/login")
    assert login.status_code == 200
    assert allowed.status_code == 200
    assert "Administration" in allowed.text


def test_sign_in_required_has_a_working_sign_in_path(tmp_path, monkeypatch) -> None:
    temporary_password = "Pilot-Pass"
    configure_local_identity(monkeypatch, production=True)
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", temporary_password)
    monkeypatch.setenv("AGENTIOT_ALLOW_TEMPORARY_ADMIN_PASSWORD", "true")
    client = TestClient(
        create_app(database_path=tmp_path / "signin-path.db"),
        base_url="https://testserver",
    )

    login_page = client.get("/login")
    cockpit = client.get("/dashboard", follow_redirects=False)
    blocked_password_page = client.get(
        "/login/change-password",
        follow_redirects=False,
    )
    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": temporary_password},
    )
    after_login = client.get("/dashboard", follow_redirects=False)
    password_page = client.get("/login/change-password")

    assert login_page.status_code == 200
    assert "Sign In" in login_page.text
    assert cockpit.status_code == 303
    assert cockpit.headers["location"].startswith("/login")
    assert blocked_password_page.status_code == 303
    assert blocked_password_page.headers["location"].startswith("/login")
    assert login.status_code == 200
    assert login.json()["password_change_required"] is True
    assert after_login.status_code == 303
    assert after_login.headers["location"] == "/login/change-password"
    assert password_page.status_code == 200
    assert "Change password" in password_page.text
    assert "/api/auth/me/password" in password_page.text


def test_settings_routes_are_distinct_single_surface_navigation(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "settings-routes.db"))
    page = client.get("/settings/access").text

    for route in (
        "/settings/access",
        "/settings/services",
        "/settings/models",
        "/settings/routing",
        "/settings/quality",
    ):
        assert f'href="{route}"' in page
        response = client.get(route)
        assert response.status_code == 200
    assert "data-settings-section" in page
    assert "settingsSection: 'access'" in page
    assert "settingsSection: 'services'" in page
    assert "settingsSection: 'models'" in page
    assert "settingsSection: 'routing'" in page
    assert "settingsSection: 'quality'" in page
    assert "max-height: min(70vh, 720px)" not in page
    assert "advanced-settings-panel" in page
    assert 'id="local-session-logout"' in page
    assert "window.confirm('Delete local user ' + item.username + '?')" in page
    assert "password.checkValidity()" in page
    assert "window.location.assign('/login?next=/settings/access')" in page
    assert "'Administration': '/settings/access'" in page
    assert 'id="shell-session-signin-link"' in page
    assert 'href="/login?next=/dashboard"' in page
    assert 'href="/login/change-password"' in page
    assert "password_change_required ? '/login/change-password'" in Path(
        PROJECT_ROOT / "src" / "agentiot" / "login_page.html"
    ).read_text()

    visual_qa = (PROJECT_ROOT / "tools" / "run_visual_qa.js").read_text()
    assert "async function authenticateVisualContext" in visual_qa
    assert "baseUrl + '/api/auth/login'" in visual_qa
    assert "admin password control unavailable" not in visual_qa
    for route_name in ("access", "services", "models", "routing", "quality"):
        assert f"['/settings/{route_name}', 'settings-{route_name}']" in visual_qa




def test_logout_invalidates_a_captured_browser_cookie(tmp_path, monkeypatch) -> None:
    configure_local_identity(monkeypatch)
    app = create_app(database_path=tmp_path / "logout-replay.db")
    signed_in = TestClient(app)
    replay = TestClient(app)
    assert signed_in.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200
    captured = signed_in.cookies.get(app_module.BROWSER_SESSION_COOKIE)

    assert signed_in.post("/api/auth/logout").status_code == 200
    replay.cookies.set(app_module.BROWSER_SESSION_COOKIE, captured)

    assert replay.get("/api/auth/session").json()["authenticated"] is False


def test_deleted_and_recreated_username_cannot_replay_old_cookie(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    app = create_app(database_path=tmp_path / "identity-recreate.db")
    admin = TestClient(app)
    operator = TestClient(app)
    replay = TestClient(app)
    assert admin.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200
    create_body = {
        "username": "recreated-user",
        "password": OPERATOR_PASSWORD,
        "role": "operator",
    }
    assert admin.post("/api/admin/access/local-users", json=create_body).status_code == 201
    assert operator.post(
        "/api/auth/login",
        json={"username": "recreated-user", "password": OPERATOR_PASSWORD},
    ).status_code == 200
    captured = operator.cookies.get(app_module.BROWSER_SESSION_COOKIE)

    assert admin.delete("/api/admin/access/local-users/recreated-user").status_code == 200
    assert admin.post("/api/admin/access/local-users", json=create_body).status_code == 201
    replay.cookies.set(app_module.BROWSER_SESSION_COOKIE, captured)

    assert replay.get("/api/auth/session").json()["authenticated"] is False


def test_password_rotation_disables_mounted_password_admin_session(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    app = create_app(database_path=tmp_path / "cross-realm-rotation.db")
    browser = TestClient(app)
    legacy = TestClient(app)
    assert browser.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200
    assert browser.patch(
        "/api/auth/me/password",
        json={
            "current_password": INITIAL_ADMIN_PASSWORD,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
        },
    ).status_code == 200

    old_password = legacy.post(
        "/api/auth/admin-session",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    new_password = legacy.post(
        "/api/auth/admin-session",
        json={"username": "admin", "password": REPLACEMENT_ADMIN_PASSWORD},
    )

    assert old_password.status_code == 401
    assert new_password.status_code == 201


def test_viewer_login_does_not_clear_admin_failures_or_allow_writes(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    app = create_app(database_path=tmp_path / "viewer-boundary.db")
    admin = TestClient(app)
    viewer = TestClient(app)
    attacker = TestClient(app)
    assert admin.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200
    assert admin.post(
        "/api/admin/access/local-users",
        json={
            "username": "read-only-user",
            "password": OPERATOR_PASSWORD,
            "role": "viewer",
        },
    ).status_code == 201
    assert viewer.post(
        "/api/auth/login",
        json={"username": "read-only-user", "password": OPERATOR_PASSWORD},
    ).status_code == 200
    assert viewer.patch(
        "/api/auth/me/password",
        json={
            "current_password": OPERATOR_PASSWORD,
            "new_password": RESET_OPERATOR_PASSWORD,
        },
    ).status_code == 200
    for _attempt in range(app_module.ADMIN_PASSWORD_FAILURE_LIMIT - 1):
        assert attacker.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password-value"},
        ).status_code == 401
        assert viewer.post(
            "/api/auth/login",
            json={"username": "read-only-user", "password": RESET_OPERATOR_PASSWORD},
        ).status_code == 200
    assert attacker.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong-password-value"},
    ).status_code == 401
    blocked = attacker.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    blocked_viewer = viewer.post(
        "/api/auth/login",
        json={"username": "read-only-user", "password": RESET_OPERATOR_PASSWORD},
    )
    denied_write = viewer.post(
        "/api/customer/feedback",
        json={
            "reviewer_role": "viewer",
            "area": "access",
            "rating": 4,
            "comment": "Read-only users must not write feedback.",
        },
    )
    denied_assistant = viewer.post(
        "/api/chat",
        json={"message": "Run a provider-backed assistant request."},
    )

    assert blocked.status_code == 429
    assert blocked_viewer.status_code == 429
    assert denied_write.status_code == 403
    assert denied_assistant.status_code == 403
    assert denied_assistant.json()["detail"] == "Scope required: agent:run"


def test_auth_lockout_is_shared_across_concurrent_application_workers(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    database_path = tmp_path / "shared-auth-limiter.db"
    attempt_count = app_module.ADMIN_PASSWORD_FAILURE_LIMIT + 3
    clients = [
        TestClient(create_app(database_path=database_path))
        for _index in range(attempt_count)
    ]
    barrier = Barrier(attempt_count)

    def failed_login(index: int) -> int:
        barrier.wait(timeout=10)
        return clients[index].post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password-value"},
        ).status_code

    with ThreadPoolExecutor(max_workers=attempt_count) as executor:
        statuses = list(executor.map(failed_login, range(attempt_count)))

    blocked = clients[0].post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )

    assert statuses.count(401) == app_module.ADMIN_PASSWORD_FAILURE_LIMIT
    assert statuses.count(429) == attempt_count - app_module.ADMIN_PASSWORD_FAILURE_LIMIT
    assert blocked.status_code == 429


def test_rotating_unknown_usernames_share_one_bounded_failure_bucket(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    app = create_app(database_path=tmp_path / "unknown-user-spray.db")
    client = TestClient(app)

    statuses = [
        client.post(
            "/api/auth/login",
            json={
                "username": f"unknown-user-{index:02d}",
                "password": "wrong-password-value",
            },
        ).status_code
        for index in range(24)
    ]
    with app.state.store.connect() as connection:
        bucket_count = connection.execute(
            "SELECT COUNT(*) AS count FROM auth_failure_buckets"
        ).fetchone()["count"]

    assert statuses[: app_module.ADMIN_PASSWORD_FAILURE_LIMIT] == [401] * 5
    assert set(statuses[app_module.ADMIN_PASSWORD_FAILURE_LIMIT :]) == {429}
    assert bucket_count == 1


def test_shared_login_bucket_does_not_reveal_known_username(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch)
    client = TestClient(create_app(database_path=tmp_path / "username-oracle.db"))
    assert client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200

    for index in range(app_module.ADMIN_PASSWORD_FAILURE_LIMIT):
        assert client.post(
            "/api/auth/login",
            json={
                "username": f"missing-account-{index}",
                "password": "wrong-password-value",
            },
        ).status_code == 401

    known = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    unknown = client.post(
        "/api/auth/login",
        json={"username": "still-missing", "password": "wrong-password-value"},
    )

    assert known.status_code == 429
    assert unknown.status_code == 429
    assert known.json()["detail"] == unknown.json()["detail"]


def test_public_operations_evidence_omits_record_rows(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch, production=True)
    client = TestClient(
        create_app(database_path=tmp_path / "public-evidence.db"),
        base_url="https://testserver",
    )
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    marker = "private-asset-identifier"
    created = client.post(
        "/api/assets",
        headers=headers,
        json={"asset_id": marker, "name": "Private Asset"},
    )

    public = client.get("/api/operations/evidence")
    privileged = client.get("/api/operations/evidence", headers=headers)

    assert created.status_code == 201
    assert public.status_code == 200
    assert public.json()["detail_level"] == "customer_safe_summary"
    assert public.json()["record_counts"]["assets"] == 1
    assert all(items == [] for items in public.json()["records"].values())
    assert marker not in public.text
    assert privileged.status_code == 200
    assert privileged.json()["detail_level"] == "full"
    assert marker in privileged.text


def test_temporary_bootstrap_requires_password_rotation_before_dashboard_access(
    tmp_path,
    monkeypatch,
) -> None:
    temporary_password = "Pilot-Pass"
    configure_local_identity(monkeypatch, production=True)
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", temporary_password)
    monkeypatch.setenv("AGENTIOT_ALLOW_TEMPORARY_ADMIN_PASSWORD", "true")
    app = create_app(database_path=tmp_path / "temporary-bootstrap.db")
    client = TestClient(app, base_url="https://testserver")
    origin_headers = {
        "Origin": "https://testserver",
        "Sec-Fetch-Site": "same-origin",
    }

    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": temporary_password},
    )
    forced_route = client.get("/dashboard", follow_redirects=False)
    admin_api = client.get("/api/admin/access/local-users")
    assistant = client.post(
        "/api/chat",
        headers=origin_headers,
        json={"message": "Do not run while password rotation is pending."},
    )
    operations_evidence = client.get("/api/operations/evidence")
    assistant_sessions = client.get("/api/assistant/sessions")
    legacy_session = client.post(
        "/api/auth/admin-session",
        headers=origin_headers,
        json={"username": "admin", "password": temporary_password},
    )
    changed = client.patch(
        "/api/auth/me/password",
        headers=origin_headers,
        json={
            "current_password": temporary_password,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
        },
    )
    replacement_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": REPLACEMENT_ADMIN_PASSWORD},
    )
    allowed_admin_api = client.get("/api/admin/access/local-users")

    assert login.status_code == 200
    assert login.json()["password_change_required"] is True
    assert forced_route.status_code == 303
    assert forced_route.headers["location"] == "/login/change-password"
    assert admin_api.status_code == 403
    assert assistant.status_code == 401
    assert operations_evidence.status_code == 200
    assert operations_evidence.json()["detail_level"] == "customer_safe_summary"
    assert assistant_sessions.status_code == 401
    assert legacy_session.status_code == 403
    assert changed.status_code == 200
    assert replacement_login.status_code == 200
    assert replacement_login.json()["password_change_required"] is False
    assert allowed_admin_api.status_code == 200


def test_production_cookie_writes_require_exact_origin_but_machine_tokens_do_not(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch, production=True)
    app = create_app(database_path=tmp_path / "browser-origin.db")
    browser = TestClient(app, base_url="https://testserver")
    assert browser.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200

    missing = browser.patch(
        "/api/auth/me/password",
        json={
            "current_password": INITIAL_ADMIN_PASSWORD,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
        },
    )
    foreign = browser.patch(
        "/api/auth/me/password",
        headers={"Origin": "https://attacker.example", "Sec-Fetch-Site": "cross-site"},
        json={
            "current_password": INITIAL_ADMIN_PASSWORD,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
        },
    )
    same_origin = browser.patch(
        "/api/auth/me/password",
        headers={"Origin": "https://testserver", "Sec-Fetch-Site": "same-origin"},
        json={
            "current_password": INITIAL_ADMIN_PASSWORD,
            "new_password": REPLACEMENT_ADMIN_PASSWORD,
        },
    )
    machine = TestClient(app, base_url="https://testserver").post(
        "/api/assets",
        headers={"X-Admin-Token": ADMIN_TOKEN},
        json={"asset_id": "origin-machine-asset", "name": "Machine API asset"},
    )

    assert missing.status_code == 403
    assert foreign.status_code == 403
    assert same_origin.status_code == 200
    assert machine.status_code == 201


def test_production_session_requires_dedicated_secret_and_is_tenant_bound(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch, production=True)
    monkeypatch.delenv("AGENTIOT_SESSION_SECRET")
    unavailable = TestClient(
        create_app(database_path=tmp_path / "missing-session-secret.db"),
        base_url="https://testserver",
    ).post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    assert unavailable.status_code == 503

    monkeypatch.setenv("AGENTIOT_SESSION_SECRET", SESSION_SECRET)
    app = create_app(database_path=tmp_path / "tenant-session.db")
    signed_in = TestClient(app, base_url="https://testserver")
    assert signed_in.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    ).status_code == 200
    captured = signed_in.cookies.get(app_module.BROWSER_SESSION_COOKIE)
    monkeypatch.setenv("AGENTIOT_DEPLOYMENT_ID", "test-deployment-next")
    deployment_replay = TestClient(app, base_url="https://testserver")
    deployment_replay.cookies.set(app_module.BROWSER_SESSION_COOKIE, captured)
    assert deployment_replay.get("/api/auth/session").json()["authenticated"] is False
    monkeypatch.setenv("AGENTIOT_DEPLOYMENT_ID", "test-deployment-2026")
    monkeypatch.setenv("AGENTIOT_TENANT_ID", "another-tenant")
    replay = TestClient(app, base_url="https://testserver")
    replay.cookies.set(app_module.BROWSER_SESSION_COOKIE, captured)

    assert replay.get("/api/auth/session").json()["authenticated"] is False


def test_production_rejects_session_secret_equal_to_admin_token(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch, production=True)
    monkeypatch.setenv("AGENTIOT_SESSION_SECRET", ADMIN_TOKEN)
    client = TestClient(
        create_app(database_path=tmp_path / "shared-session-secret.db"),
        base_url="https://testserver",
    )

    login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": INITIAL_ADMIN_PASSWORD},
    )
    readiness = client.get("/readyz")

    assert login.status_code == 503
    assert "set-cookie" not in login.headers
    assert readiness.status_code == 503
    assert readiness.json()["browser_session_ready"] is False


def test_login_redirect_rejects_encoded_authority_and_backslash_forms() -> None:
    source = (PROJECT_ROOT / "src" / "agentiot" / "login_page.html").read_text(
        encoding="utf-8"
    )

    assert "safeLocalDestination" in source
    assert "candidate.includes('\\\\')" in source
    assert "/%(?:2f|5c)/i" in source

def test_production_browser_bootstrap_rejects_weak_password(
    tmp_path,
    monkeypatch,
) -> None:
    configure_local_identity(monkeypatch, production=True)
    monkeypatch.setenv("AGENTIOT_ADMIN_PASSWORD", "weak")
    client = TestClient(
        create_app(database_path=tmp_path / "weak-bootstrap.db"),
        base_url="https://testserver",
    )

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "weak"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Admin password does not meet production policy"
