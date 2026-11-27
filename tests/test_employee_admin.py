from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.lead_intelligence.api.app import create_app
from src.lead_intelligence.api.auth import AuthConfig
from src.lead_intelligence.auth.admin import (
    EmployeeExistsError,
    EmployeeNotFoundError,
    EmployeeService,
)
from src.lead_intelligence.auth.service import (
    PasswordChangeRequiredError,
    Principal,
)
from src.lead_intelligence.database.models import UserRecord

MODULE = "src.lead_intelligence.api.admin"
SERVICE = "src.lead_intelligence.auth.admin"
PATH = "/api/v1/admin/users"
HEADERS = {"X-BLI-CSRF": "1", "Origin": "https://localhost"}
PAYLOAD = {
    "username": "employee01",
    "display_name": "Employee One",
    "password": "test-only-temporary-password",
}


def employee(**changes):
    fields = {
        "id": uuid4(),
        "username": PAYLOAD["username"],
        "display_name": PAYLOAD["display_name"],
        "password_hash": "test-only-hash",
        "role": "employee",
        "is_active": True,
        "must_change_password": True,
        "created_at": datetime.now(UTC),
        "last_login_at": None,
    }
    return UserRecord(**(fields | changes))


@pytest.fixture
def api():
    app = create_app(
        engine_factory=lambda: MagicMock(spec=Engine), auth_config=AuthConfig()
    )
    with TestClient(app, base_url="https://localhost") as client:
        factory = MagicMock()
        app.state.session_factory = factory
        with (
            patch(f"{MODULE}.AuthenticationService") as auth,
            patch(f"{MODULE}.EmployeeService") as service,
        ):
            auth.return_value.authenticate.return_value = Principal(
                uuid4(), "admin", "Admin", "admin", False
            )
            client.cookies.set("__Host-bli_session", "a" * 43)
            yield client, factory, auth.return_value, service


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("GET", "", None),
        ("POST", "", PAYLOAD),
        ("PATCH", f"/{uuid4()}", {"is_active": False}),
        ("POST", f"/{uuid4()}/reset-password", {"password": PAYLOAD["password"]}),
    ],
)
@pytest.mark.parametrize("identity", ["anonymous", "employee", "temporary"])
def test_admin_routes_deny_unauthorized(api, method, suffix, body, identity):
    client, _, auth, service = api
    if identity == "anonymous":
        client.cookies.clear()
    elif identity == "employee":
        auth.authenticate.return_value = Principal(
            uuid4(), "employee", "Employee", "employee", False
        )
    else:
        auth.authenticate.side_effect = PasswordChangeRequiredError()
    response = client.request(method, PATH + suffix, json=body, headers=HEADERS)
    assert response.status_code == (401 if identity == "anonymous" else 403)
    service.assert_not_called()


def test_create_rejects_csrf(api):
    client, _, auth, service = api
    assert client.post(PATH, json=PAYLOAD).status_code == 403
    auth.authenticate.assert_not_called()
    service.assert_not_called()


def test_create_returns_safe_fields_and_commits(api):
    client, factory, auth, service = api
    service.return_value.create.return_value = employee()
    response = client.post(PATH, json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 201
    assert response.json()["must_change_password"] is True
    assert "password_hash" not in response.json()
    assert PAYLOAD["password"] not in response.text
    auth.authenticate.assert_called_once_with("a" * 43)
    service.assert_called_once_with(factory.begin.return_value.__enter__.return_value)
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize("extra", [{"role": "admin"}, {"must_change_password": False}])
def test_cannot_create_privileged_user(api, extra):
    client, _, _, service = api
    response = client.post(PATH, json=PAYLOAD | extra, headers=HEADERS)
    assert response.status_code == 422
    assert PAYLOAD["password"] not in response.text
    service.assert_not_called()


def test_duplicate_username(api):
    client, _, _, service = api
    service.return_value.create.side_effect = EmployeeExistsError()
    assert client.post(PATH, json=PAYLOAD, headers=HEADERS).status_code == 409


def test_list_paginated(api):
    client, _, _, service = api
    service.return_value.list.return_value = [employee(), employee()]
    response = client.get(PATH + "?limit=1")
    assert response.status_code == 200
    assert response.json()["has_more"] is True
    assert len(response.json()["items"]) == 1
    assert "password_hash" not in response.text
    service.return_value.list.assert_called_once_with(limit=2, offset=0)


@pytest.mark.parametrize(
    "payload", [{}, {"role": "admin"}, {"is_active": None}, {"is_active": "false"}]
)
def test_invalid_update(api, payload):
    client, _, _, service = api
    response = client.patch(f"{PATH}/{uuid4()}", json=payload, headers=HEADERS)
    assert response.status_code == 422
    service.assert_not_called()


def test_disable_employee(api):
    client, _, _, service = api
    user = employee(is_active=False)
    service.return_value.update.return_value = user
    response = client.patch(
        f"{PATH}/{user.id}", json={"is_active": False}, headers=HEADERS
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    service.return_value.update.assert_called_once_with(
        user.id, display_name=None, is_active=False
    )


def test_reset_password(api):
    client, factory, _, service = api
    user_id = uuid4()
    response = client.post(
        f"{PATH}/{user_id}/reset-password",
        json={"password": PAYLOAD["password"]},
        headers=HEADERS,
    )
    assert response.status_code == 204
    assert response.content == b""
    service.return_value.reset_password.assert_called_once_with(
        user_id, PAYLOAD["password"]
    )
    factory.begin.return_value.__exit__.assert_called_once_with(None, None, None)


def test_commit_failure_returns_no_success(api):
    client, factory, _, service = api
    service.return_value.create.return_value = employee()
    factory.begin.return_value.__exit__.side_effect = SQLAlchemyError("private details")
    response = client.post(PATH, json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 500
    assert "private details" not in response.text


@pytest.fixture
def employee_service():
    session = MagicMock(spec=Session)
    service = EmployeeService(session)
    service.users = MagicMock()
    service.sessions = MagicMock()
    return service, session


def test_create_hash_and_database_conflict_clause(employee_service):
    service, session = employee_service
    session.scalar.return_value = employee()
    with patch(f"{SERVICE}.hash_password", return_value="hashed") as hash_password:
        service.create(" Employee01 ", " Employee One ", PAYLOAD["password"])
    hash_password.assert_called_once_with(PAYLOAD["password"])
    statement = session.scalar.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "ON CONFLICT (username) DO NOTHING" in str(compiled)
    assert compiled.params["role"] == "employee"
    assert compiled.params["must_change_password"] is True
    assert compiled.params["password_hash"] == "hashed"
    assert PAYLOAD["password"] not in compiled.params.values()


def test_duplicate_conflict_is_explicit(employee_service):
    service, session = employee_service
    session.scalar.return_value = None
    with (
        patch(f"{SERVICE}.hash_password", return_value="hashed"),
        pytest.raises(EmployeeExistsError),
    ):
        service.create(
            PAYLOAD["username"], PAYLOAD["display_name"], PAYLOAD["password"]
        )


@pytest.mark.parametrize("role", ["admin", None])
def test_admin_or_missing_cannot_be_changed(employee_service, role):
    service, session = employee_service
    user = employee(role=role) if role else None
    service.users.lock_by_id.return_value = user
    with pytest.raises(EmployeeNotFoundError):
        service.update(uuid4(), display_name=None, is_active=False)
    with pytest.raises(EmployeeNotFoundError):
        service.reset_password(uuid4(), PAYLOAD["password"])
    service.sessions.revoke_all.assert_not_called()
    session.flush.assert_not_called()


@pytest.mark.parametrize("active", [True, False])
def test_activation_changes_revoke_sessions(employee_service, active):
    service, session = employee_service
    user = employee(is_active=not active)
    service.users.lock_by_id.return_value = user
    now = datetime.now(UTC)
    session.scalar.return_value = now
    service.update(user.id, display_name=None, is_active=active)
    assert user.is_active is active
    service.sessions.revoke_all.assert_called_once_with(user.id, now)
    session.flush.assert_called_once()


def test_name_update_preserves_sessions(employee_service):
    service, _ = employee_service
    user = employee()
    service.users.lock_by_id.return_value = user
    service.update(user.id, display_name=" New Name ", is_active=None)
    assert user.display_name == "New Name"
    service.sessions.revoke_all.assert_not_called()


def test_password_reset_revokes_and_forces_change(employee_service):
    service, session = employee_service
    user = employee(must_change_password=False)
    service.users.lock_by_id.return_value = user
    now = datetime.now(UTC)
    session.scalar.return_value = now
    with (
        patch(f"{SERVICE}.verify_password", return_value=False),
        patch(f"{SERVICE}.hash_password", return_value="new-hash"),
    ):
        service.reset_password(user.id, PAYLOAD["password"])
    assert user.password_hash == "new-hash"
    assert user.must_change_password is True
    service.sessions.revoke_all.assert_called_once_with(user.id, now)
    session.flush.assert_called_once()


def test_reset_rejects_reused_password(employee_service):
    service, session = employee_service
    user = employee()
    service.users.lock_by_id.return_value = user
    with (
        patch(f"{SERVICE}.verify_password", return_value=True),
        pytest.raises(ValueError),
    ):
        service.reset_password(user.id, PAYLOAD["password"])
    service.sessions.revoke_all.assert_not_called()
    session.flush.assert_not_called()
