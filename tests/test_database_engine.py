from unittest.mock import MagicMock, patch

import pytest

from src.lead_intelligence.database.engine import (
    _configure_statement_timeout,
    check_database_connection,
    create_database_engine,
)
from src.lead_intelligence.database.settings import DatabaseSettings


@pytest.fixture
def settings(tmp_path):
    certificate = tmp_path / "ca.crt"
    certificate.write_text("dummy certificate", encoding="utf-8")

    return DatabaseSettings(
        host="database.example.com",
        username="test_user",
        password="password@with:special/characters",
        sslrootcert=certificate,
    )


@pytest.fixture
def dbapi_connection():
    connection = MagicMock()
    connection.autocommit = False

    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("30000", "ms")

    return connection


def test_create_database_engine(settings):
    with (
        patch("src.lead_intelligence.database.engine.create_engine") as mock_create,
        patch("src.lead_intelligence.database.engine.event.listens_for"),
    ):
        engine = create_database_engine(settings)

    assert engine is mock_create.return_value

    url = mock_create.call_args.args[0]
    options = mock_create.call_args.kwargs

    assert url.drivername == "postgresql+psycopg"
    assert url.host == settings.host
    assert url.username == settings.username
    assert url.password == settings.password
    assert url.port == 5432
    assert settings.password not in str(url)

    assert options["pool_size"] == 3
    assert options["max_overflow"] == 2
    assert options["pool_timeout"] == 30
    assert options["pool_recycle"] == 1800
    assert options["pool_pre_ping"] is True
    assert options["pool_use_lifo"] is True
    assert options["hide_parameters"] is True
    assert options["echo"] is False


def test_engine_ssl_configuration(settings):
    with (
        patch("src.lead_intelligence.database.engine.create_engine") as mock_create,
        patch("src.lead_intelligence.database.engine.event.listens_for"),
    ):
        create_database_engine(settings)

    arguments = mock_create.call_args.kwargs["connect_args"]

    assert arguments["sslmode"] == "verify-full"
    assert arguments["sslrootcert"] == str(settings.sslrootcert.resolve())
    assert arguments["connect_timeout"] == 10
    assert "options" not in arguments


def test_engine_rejects_invalid_settings():
    with pytest.raises(TypeError):
        create_database_engine(None)


@pytest.mark.parametrize(
    ("result", "expected"),
    [(1, True), (0, False)],
)
def test_database_connection_check(result, expected):
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value

    connection.execute.return_value.scalar_one.return_value = result

    assert check_database_connection(engine) is expected

    statement = connection.execute.call_args.args[0]
    assert str(statement) == "SELECT 1"

    engine.connect.return_value.__exit__.assert_called_once()


def test_connection_error_propagates():
    engine = MagicMock()
    engine.connect.side_effect = RuntimeError("Connection failed")

    with pytest.raises(RuntimeError):
        check_database_connection(engine)


def test_statement_timeout_applied(dbapi_connection):
    cursor = dbapi_connection.cursor.return_value.__enter__.return_value

    _configure_statement_timeout(
        dbapi_connection,
        None,
        None,
        timeout_ms=30000,
    )

    assert cursor.execute.call_count == 2

    cursor.execute.assert_any_call(
        "SELECT set_config('statement_timeout', %s, false)",
        ("30000",),
    )

    cursor.execute.assert_any_call(
        "SELECT setting, unit FROM pg_settings WHERE name = 'statement_timeout'"
    )

    assert dbapi_connection.autocommit is False


def test_statement_timeout_uses_autocommit(dbapi_connection):
    cursor = dbapi_connection.cursor.return_value.__enter__.return_value

    def execute(*args, **kwargs):
        assert dbapi_connection.autocommit is True

    cursor.execute.side_effect = execute

    _configure_statement_timeout(
        dbapi_connection,
        None,
        None,
        timeout_ms=30000,
    )

    assert dbapi_connection.autocommit is False


def test_existing_autocommit_mode_preserved(dbapi_connection):
    dbapi_connection.autocommit = True

    _configure_statement_timeout(
        dbapi_connection,
        None,
        None,
        timeout_ms=30000,
    )

    assert dbapi_connection.autocommit is True


@pytest.mark.parametrize(
    "result",
    [
        ("120000", "ms"),
        ("30000", "s"),
        ("0", "ms"),
        None,
    ],
)
def test_incorrect_statement_timeout_rejected(
    dbapi_connection,
    result,
):
    cursor = dbapi_connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = result

    with pytest.raises(
        RuntimeError,
        match="statement timeout verification failed",
    ):
        _configure_statement_timeout(
            dbapi_connection,
            None,
            None,
            timeout_ms=30000,
        )

    assert dbapi_connection.autocommit is False


def test_statement_timeout_error_restores_autocommit(
    dbapi_connection,
):
    cursor = dbapi_connection.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = RuntimeError("Simulated failure")

    with pytest.raises(RuntimeError, match="Simulated failure"):
        _configure_statement_timeout(
            dbapi_connection,
            None,
            None,
            timeout_ms=30000,
        )

    assert dbapi_connection.autocommit is False

    dbapi_connection.cursor.return_value.__exit__.assert_called_once()


def test_custom_statement_timeout(dbapi_connection):
    cursor = dbapi_connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("15000", "ms")

    _configure_statement_timeout(
        dbapi_connection,
        None,
        None,
        timeout_ms=15000,
    )

    cursor.execute.assert_any_call(
        "SELECT set_config('statement_timeout', %s, false)",
        ("15000",),
    )


def test_checkout_listener_registered_and_executed(
    settings,
    dbapi_connection,
):
    with (
        patch("src.lead_intelligence.database.engine.create_engine") as mock_create,
        patch("src.lead_intelligence.database.engine.event.listens_for") as mock_listen,
        patch(
            "src.lead_intelligence.database.engine._configure_statement_timeout"
        ) as mock_configure,
    ):
        mock_listen.return_value.side_effect = lambda function: function

        engine = create_database_engine(settings)

        mock_listen.assert_called_once_with(
            mock_create.return_value,
            "checkout",
        )

        callback = mock_listen.return_value.call_args.args[0]

        callback(dbapi_connection, None, None)

        mock_configure.assert_called_once_with(
            dbapi_connection,
            None,
            None,
            timeout_ms=settings.statement_timeout_ms,
        )

        assert engine is mock_create.return_value
