import importlib.util
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from scripts.create_admin import create_initial_admin
from src.lead_intelligence.auth.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    normalize_username,
    verify_password,
)
from src.lead_intelligence.database.models import (
    SearchJobRecord,
    UserRecord,
    UserSessionRecord,
)


@pytest.mark.parametrize("value", ["a", "abc def", "äbc", "a/b", "a" * 65, None])
def test_invalid_username(value):
    with pytest.raises(ValueError):
        normalize_username(value)


def test_username_normalization():
    assert normalize_username(" Employee.01 ") == "employee.01"


@pytest.mark.parametrize(
    "value",
    ["short", " " * 20, "a" * 1025, "é" * 513, "a" * 20 + "\x00", None, "\ud800" * 20],
)
def test_invalid_password(value):
    with pytest.raises(ValueError):
        hash_password(value)


def test_password_hash_salted_and_verified():
    password = "a synthetic testing phrase"
    first = hash_password(password)
    second = hash_password(password)
    assert first.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password("a wrong testing phrase", first)
    assert not verify_password(password, first.replace("m=65536", "m=99999999"))


@pytest.mark.parametrize("value", ["invalid", "", None, "$argon2id$" + "a" * 600])
def test_invalid_stored_hash(value):
    assert not verify_password("a synthetic testing phrase", value)


def test_token_is_random_and_only_digest_persistable():
    first = generate_session_token()
    second = generate_session_token()
    assert len(first) == 43
    assert first != second
    digest = hash_session_token(first)
    assert len(digest) == 64
    assert digest == hash_session_token(first)
    assert digest != hash_session_token(second)
    assert first not in digest


@pytest.mark.parametrize("token", ["", "a" * 42, "a" * 44, "/" * 43, None])
def test_invalid_token(token):
    with pytest.raises(ValueError):
        hash_session_token(token)


def test_auth_schema_and_job_attribution():
    dialect = postgresql.dialect()
    users = str(CreateTable(UserRecord.__table__).compile(dialect=dialect))
    sessions = str(CreateTable(UserSessionRecord.__table__).compile(dialect=dialect))
    index = next(iter(UserRecord.__table__.indexes))
    assert "WHERE role = 'admin'" in str(CreateIndex(index).compile(dialect=dialect))
    assert index.unique
    assert "UNIQUE (username)" in users
    assert "UNIQUE (token_hash)" in sessions
    assert "ON DELETE RESTRICT" in sessions
    assert SearchJobRecord.__table__.c.created_by.nullable


def test_migration_offline_sql(monkeypatch):
    file = (
        Path(__file__).resolve().parents[1]
        / "migrations/versions/7b09e41d6a23_add_authentication_tables.py"
    )
    spec = importlib.util.spec_from_file_location("auth_revision", file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    out = StringIO()
    ctx = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": out}
    )
    monkeypatch.setattr(migration, "op", Operations(ctx))
    migration.upgrade()
    sql = out.getvalue()
    for table in ("users", "user_sessions"):
        relation = f"lead_intelligence.{table}"
        assert f"ALTER TABLE {relation} ENABLE ROW LEVEL SECURITY" in sql
        assert f"GRANT SELECT, INSERT, UPDATE ON TABLE {relation} TO bli_app" in sql
        assert f"REVOKE ALL PRIVILEGES ON TABLE {relation}" in sql
    assert "ADD COLUMN created_by UUID" in sql
    assert "DROP TABLE" not in sql
    with pytest.raises(RuntimeError):
        migration.downgrade()


def test_bootstrap_hashes_password_and_flushes_without_commit():
    session = MagicMock()
    session.scalar.side_effect = ["bli_app", None]
    password = "a synthetic testing phrase"
    create_initial_admin(session, "Admin.01", "Admin", password)
    user = session.add.call_args.args[0]
    assert user.username == "admin.01"
    assert user.role == "admin"
    assert user.is_active
    assert not user.must_change_password
    assert verify_password(password, user.password_hash)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.parametrize("values", [["bli_migrator"], ["bli_app", "existing"]])
def test_bootstrap_refuses_wrong_role_or_existing_admin(values):
    session = MagicMock()
    session.scalar.side_effect = values
    with pytest.raises(RuntimeError):
        create_initial_admin(session, "admin", "Admin", "a synthetic testing phrase")
    session.add.assert_not_called()
