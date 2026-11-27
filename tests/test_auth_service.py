from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from src.lead_intelligence.auth.security import (
    generate_session_token,
    hash_session_token,
    verify_password,
)
from src.lead_intelligence.auth.service import (
    SESSION_LIFETIME,
    TEMPORARY_SESSION_LIFETIME,
    AuthenticationService,
    InvalidCredentialsError,
    InvalidSessionError,
    PasswordChangeRequiredError,
)
from src.lead_intelligence.database.models import UserRecord, UserSessionRecord
from src.lead_intelligence.database.repositories.auth import (
    SessionRepository,
    UserRepository,
)

MODULE = "src.lead_intelligence.auth.service"
NOW = datetime(2026, 11, 27, 10, tzinfo=UTC)


@pytest.fixture
def context(monkeypatch):
    db = MagicMock()
    db.new = db.dirty = db.deleted = []
    db.scalar.return_value = "read committed"
    service = AuthenticationService(db)
    service.users = MagicMock()
    service.sessions = MagicMock()
    monkeypatch.setattr(service, "_now", lambda: NOW)
    user = UserRecord(
        id=uuid4(),
        username="employee.01",
        display_name="Employee",
        password_hash="test-hash",
        role="employee",
        is_active=True,
        must_change_password=False,
    )
    token = generate_session_token()
    record = UserSessionRecord(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=NOW - timedelta(minutes=1),
        expires_at=NOW + SESSION_LIFETIME,
    )
    service.users.lock_by_username.return_value = user
    service.users.lock_by_id.return_value = user
    service.sessions.owner_id.return_value = user.id
    service.sessions.find.return_value = record
    verify = MagicMock(return_value=True)
    monkeypatch.setattr(f"{MODULE}.verify_password", verify)
    return service, db, user, record, token, verify


@pytest.mark.parametrize("temporary", [False, True])
def test_login_issues_hashed_token_and_correct_lifetime(context, temporary):
    service, db, user, _, _, verify = context
    user.must_change_password = temporary
    result = service.login(" EMPLOYEE.01 ", "synthetic password")
    service.users.lock_by_username.assert_called_once_with("employee.01")
    verify.assert_called_once_with("synthetic password", user.password_hash)
    lifetime = TEMPORARY_SESSION_LIFETIME if temporary else SESSION_LIFETIME
    assert result.expires_at == NOW + lifetime
    assert result.principal.id == user.id
    assert result.principal.must_change_password is temporary
    assert result.token not in repr(result)
    assert user.password_hash not in repr(result.principal)
    service.sessions.create.assert_called_once_with(
        user.id, hash_session_token(result.token), NOW, result.expires_at
    )
    assert user.last_login_at == NOW
    db.commit.assert_not_called()


@pytest.mark.parametrize("mode", ["unknown", "inactive", "invalid", "wrong"])
def test_login_failures_are_generic_and_never_issue_sessions(context, mode):
    service, _, user, _, _, verify = context
    username = user.username
    if mode == "unknown":
        service.users.lock_by_username.return_value = None
    elif mode == "inactive":
        user.is_active = False
    elif mode == "invalid":
        username = "!"
    else:
        verify.return_value = False
    with pytest.raises(InvalidCredentialsError, match="Invalid username or password"):
        service.login(username, "synthetic password")
    verify.assert_called_once()
    if mode != "wrong":
        assert verify.call_args.args[1].startswith("$argon2id$")
    service.sessions.create.assert_not_called()
    assert user.last_login_at is None


def test_real_dummy_hash_is_valid_argon2():
    from src.lead_intelligence.auth.service import _DUMMY_HASH

    assert not verify_password("synthetic incorrect password", _DUMMY_HASH)


@pytest.mark.parametrize(
    "mode",
    [
        "malformed",
        "unknown",
        "inactive",
        "missing_user",
        "missing_session",
        "revoked",
        "expired",
        "boundary",
    ],
)
def test_invalid_sessions_are_rejected(context, mode):
    service, _, user, record, token, _ = context
    if mode == "malformed":
        token = "bad"
    elif mode == "unknown":
        service.sessions.owner_id.return_value = None
    elif mode == "inactive":
        user.is_active = False
    elif mode == "missing_user":
        service.users.lock_by_id.return_value = None
    elif mode == "missing_session":
        service.sessions.find.return_value = None
    elif mode == "revoked":
        record.revoked_at = NOW
    elif mode == "expired":
        record.expires_at = NOW - timedelta(seconds=1)
    else:
        record.expires_at = NOW
    with pytest.raises(InvalidSessionError, match="Invalid or expired session"):
        service.authenticate(token)


def test_user_is_locked_before_session_is_rechecked(context):
    service, _, user, record, token, _ = context
    order = []
    service.users.lock_by_id.side_effect = lambda _: order.append("user") or user
    service.sessions.find.side_effect = lambda *_: order.append("session") or record
    assert service.authenticate(token).id == user.id
    assert order == ["user", "session"]


def test_temporary_session_cannot_access_protected_operations(context):
    service, _, user, _, token, _ = context
    user.must_change_password = True
    with pytest.raises(PasswordChangeRequiredError):
        service.authenticate(token)
    assert service.authenticate(token, allow_password_change=True).must_change_password


def test_logout_revokes_only_current_session_and_is_idempotent(context):
    service, db, _, record, token, _ = context
    service.logout(token)
    assert record.revoked_at == NOW
    service.sessions.revoke_all.assert_not_called()
    service.logout(token)
    service.logout("bad")
    db.flush.assert_called_once()
    db.commit.assert_not_called()


def test_password_change_revokes_all_sessions(context, monkeypatch):
    service, db, user, _, token, _ = context
    user.must_change_password = True
    hasher = MagicMock(return_value="new-hash")
    monkeypatch.setattr(f"{MODULE}.hash_password", hasher)
    service.change_password(token, "old synthetic password", "new synthetic password")
    hasher.assert_called_once_with("new synthetic password")
    assert user.password_hash == "new-hash"
    assert not user.must_change_password
    service.sessions.revoke_all.assert_called_once_with(user.id, NOW)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.parametrize("mode", ["wrong", "same", "invalid_new"])
def test_password_change_failure_preserves_credentials(context, monkeypatch, mode):
    service, _, user, _, token, verify = context
    user.must_change_password = True
    current = "old synthetic password"
    replacement = current if mode == "same" else "new synthetic password"
    if mode == "wrong":
        verify.return_value = False
    monkeypatch.setattr(f"{MODULE}.hash_password", MagicMock(side_effect=ValueError))
    with pytest.raises((InvalidCredentialsError, ValueError)):
        service.change_password(token, current, replacement)
    assert user.password_hash == "test-hash"
    assert user.must_change_password
    service.sessions.revoke_all.assert_not_called()


@pytest.mark.parametrize("mode", ["pending", "isolation"])
def test_service_rejects_unsafe_transaction(context, mode):
    service, db, _, _, token, _ = context
    if mode == "pending":
        db.dirty = [object()]
    else:
        db.scalar.return_value = "repeatable read"
    with pytest.raises(RuntimeError):
        service.authenticate(token)
    service.sessions.owner_id.assert_not_called()


def test_repository_user_locks_and_fresh_reads():
    db = MagicMock()
    repository = UserRepository(db)
    repository.lock_by_username("employee.01")
    repository.lock_by_id(uuid4())
    for call in db.scalar.call_args_list:
        statement = call.args[0]
        assert "FOR UPDATE" in str(statement.compile(dialect=postgresql.dialect()))
        assert statement.get_execution_options()["populate_existing"]


def test_repository_token_lookup_and_revocation():
    db = MagicMock()
    repository = SessionRepository(db)
    user_id = uuid4()
    digest = hash_session_token(generate_session_token())
    repository.owner_id(digest)
    repository.find(user_id, digest)
    assert db.scalar.call_args.args[0].get_execution_options()["populate_existing"]
    record = repository.create(user_id, digest, NOW, NOW + SESSION_LIFETIME)
    assert record.token_hash == digest
    db.add.assert_called_once_with(record)
    db.flush.assert_called_once()
    repository.revoke_all(user_id, NOW)
    statement = db.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "UPDATE lead_intelligence.user_sessions" in sql
    assert "revoked_at IS NULL" in sql
    assert "greatest" in sql
    db.commit.assert_not_called()
