from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from src.lead_intelligence.api.app import create_app
from src.lead_intelligence.api.auth import AuthConfig, LoginLimiter, require_admin
from src.lead_intelligence.auth.service import (
    InvalidCredentialsError,
    InvalidSessionError,
    LoginResult,
    PasswordChangeRequiredError,
    Principal,
)

MODULE = "src.lead_intelligence.api.auth"
HEADERS = {"X-BLI-CSRF": "1", "Origin": "https://localhost"}
TOKEN = "a" * 43
PAYLOAD = {"username": "employee", "password": "example-not-real-password"}


@pytest.fixture
def principal():
    return Principal(uuid4(), "employee", "Employee", "employee", False)


@pytest.fixture
def api(principal):
    app = create_app(
        engine_factory=lambda: MagicMock(spec=Engine), auth_config=AuthConfig()
    )
    with TestClient(app, base_url="https://localhost") as client:
        factory = MagicMock()
        app.state.session_factory = factory
        with patch(f"{MODULE}.AuthenticationService") as service:
            service.return_value.authenticate.return_value = principal
            service.return_value.login.return_value = LoginResult(
                principal, datetime.now(UTC) + timedelta(hours=8), TOKEN
            )
            yield client, factory, service.return_value


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/jobs"),
        ("GET", "/api/v1/jobs/" + str(uuid4())),
        ("GET", "/api/v1/locations"),
        ("GET", "/api/v1/exports?country_code=NP&city=Kathmandu"),
        ("POST", "/api/v1/jobs"),
        ("POST", "/api/v1/searches/check"),
        ("GET", "/api/v1/auth/me"),
    ],
)
def test_protected_routes_without_cookie(api, method, path):
    client, factory, _ = api
    response = client.request(
        method,
        path,
        headers=HEADERS,
        json={"country_code": "NP", "city": "Kathmandu", "query": "Travel"}
        if method == "POST"
        else None,
    )
    assert response.status_code == 401
    factory.begin.assert_not_called()
    factory.assert_not_called()
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-BLI-CSRF": "1", "Origin": "https://evil.example"},
        {"X-BLI-CSRF": "1", "Sec-Fetch-Site": "cross-site"},
    ],
)
def test_login_csrf_rejected(api, headers):
    client, factory, _ = api
    assert (
        client.post("/api/v1/auth/login", json=PAYLOAD, headers=headers).status_code
        == 403
    )
    factory.begin.assert_not_called()


def test_login_sets_secure_cookie_after_commit(api):
    client, factory, service = api
    response = client.post("/api/v1/auth/login", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["role"] == "employee"
    assert TOKEN not in response.text
    assert "password_hash" not in response.text
    cookie = response.headers["set-cookie"].lower()
    assert "__host-bli_session=" in cookie
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    assert "domain=" not in cookie and "path=/" in cookie
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)
    service.login.assert_called_once_with(PAYLOAD["username"], PAYLOAD["password"])
    assert client.get("/api/v1/auth/me").status_code == 200
    service.authenticate.assert_called_once_with(TOKEN, allow_password_change=True)


def test_failed_login_generic(api):
    client, _, service = api
    service.login.side_effect = InvalidCredentialsError("private error")
    response = client.post("/api/v1/auth/login", headers=HEADERS, json=PAYLOAD)
    assert response.status_code == 401
    assert "private error" not in response.text
    assert "set-cookie" not in response.headers


def test_invalid_session_denied(api):
    client, _, service = api
    client.cookies.set("__Host-bli_session", TOKEN)
    service.authenticate.side_effect = InvalidSessionError("secret")
    response = client.get("/api/v1/jobs")
    assert response.status_code == 401
    assert "secret" not in response.text


def test_temporary_session_cannot_access_jobs(api):
    client, _, service = api
    client.cookies.set("__Host-bli_session", TOKEN)
    service.authenticate.side_effect = PasswordChangeRequiredError()
    response = client.get("/api/v1/jobs")
    assert response.status_code == 403
    assert response.json()["code"] == "password_change_required"
    service.authenticate.assert_called_once_with(TOKEN, allow_password_change=False)


def test_logout_revokes_and_clears(api):
    client, factory, service = api
    client.cookies.set("__Host-bli_session", TOKEN)
    response = client.post("/api/v1/auth/logout", headers=HEADERS)
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    service.logout.assert_called_once_with(TOKEN)
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)


def test_change_password_revokes_and_clears(api):
    client, factory, service = api
    client.cookies.set("__Host-bli_session", TOKEN)
    response = client.post(
        "/api/v1/auth/change-password",
        headers=HEADERS,
        json={
            "current_password": PAYLOAD["password"],
            "new_password": "new-example-password",
        },
    )
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    service.change_password.assert_called_once_with(
        TOKEN, PAYLOAD["password"], "new-example-password"
    )
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)


def test_account_rate_limit(api):
    client, _, service = api
    service.login.side_effect = InvalidCredentialsError()
    for _ in range(5):
        assert (
            client.post("/api/v1/auth/login", headers=HEADERS, json=PAYLOAD).status_code
            == 401
        )
    response = client.post("/api/v1/auth/login", headers=HEADERS, json=PAYLOAD)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert service.login.call_count == 5


def test_global_concurrent_hash_limit():
    limiter = LoginLimiter()
    with limiter.attempt("peer1", "user1"), limiter.attempt("peer2", "user2"):
        with pytest.raises(HTTPException) as exc, limiter.attempt("peer3", "user3"):
            pass
    assert exc.value.status_code == 429
    with limiter.attempt("peer3", "user3"):
        pass


def test_employee_cannot_require_admin(principal):
    with pytest.raises(HTTPException) as exc:
        require_admin(principal)
    assert exc.value.status_code == 403
    admin = Principal(uuid4(), "admin", "Admin", "admin", False)
    assert require_admin(admin) == admin


@pytest.mark.parametrize(
    "origin,development",
    [
        ("http://localhost", False),
        ("http://example.com", True),
        ("https://localhost/path", False),
    ],
)
def test_bad_auth_config(origin, development):
    with pytest.raises(ValueError):
        AuthConfig(origin, development)


def test_http_rejected_by_default(api):
    client, factory, _ = api
    response = client.post(
        "http://localhost/api/v1/auth/login", json=PAYLOAD, headers=HEADERS
    )
    assert response.status_code == 403
    factory.begin.assert_not_called()


def test_invalid_password_input_not_echoed(api):
    client, _, _ = api
    response = client.post(
        "/api/v1/auth/login",
        headers=HEADERS,
        json={"username": 123, "password": "private-password"},
    )
    assert response.status_code == 422
    assert "private-password" not in response.text


def test_commit_failure_does_not_issue_cookie(api):
    from sqlalchemy.exc import SQLAlchemyError

    client, factory, _ = api
    factory.begin.return_value.__exit__.side_effect = SQLAlchemyError("private")
    response = client.post("/api/v1/auth/login", headers=HEADERS, json=PAYLOAD)
    assert response.status_code == 500
    assert "private" not in response.text
    assert "set-cookie" not in response.headers


def test_authenticated_job_history_uses_business_session(api):
    client, factory, service = api
    client.cookies.set("__Host-bli_session", TOKEN)
    business_session = factory.return_value.__enter__.return_value
    business_session.execute.return_value.all.return_value = []
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert response.json()["items"] == []
    service.authenticate.assert_called_once_with(TOKEN, allow_password_change=False)
    business_session.execute.assert_called_once()
