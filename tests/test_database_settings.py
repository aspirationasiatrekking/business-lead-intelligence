from dataclasses import FrozenInstanceError, replace

import pytest

from src.lead_intelligence.database.settings import DatabaseSettings


@pytest.fixture
def settings(tmp_path):
    certificate = tmp_path / "ca.crt"
    certificate.write_text("dummy certificate", encoding="utf-8")

    return DatabaseSettings(
        host="database.example.com",
        username="test_user",
        password="test-secret-password",
        sslrootcert=certificate,
    )


def test_database_settings_defaults(settings):
    assert settings.port == 5432
    assert settings.database == "postgres"
    assert settings.sslmode == "verify-full"
    assert settings.pool_size == 3
    assert settings.max_overflow == 2


def test_password_hidden_from_repr(settings):
    assert settings.password not in repr(settings)


def test_settings_are_immutable(settings):
    with pytest.raises(FrozenInstanceError):
        settings.port = 1234


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("host", ""),
        ("host", "invalid host"),
        ("username", ""),
        ("database", ""),
        ("password", ""),
        ("password", "invalid\npassword"),
        ("port", 0),
        ("port", 65536),
        ("port", True),
        ("connect_timeout", 0),
        ("connect_timeout", 31),
        ("pool_size", 0),
        ("pool_size", 11),
        ("max_overflow", -1),
        ("max_overflow", 6),
        ("pool_timeout", 0),
        ("pool_timeout", 61),
        ("pool_recycle", 59),
        ("pool_recycle", 3601),
        ("statement_timeout_ms", 999),
        ("statement_timeout_ms", 120001),
        ("sslmode", "disable"),
        ("sslmode", "require"),
        ("sslmode", "verify-ca"),
        ("sslrootcert", None),
    ],
)
def test_invalid_database_settings(settings, field, value):
    with pytest.raises(ValueError):
        replace(settings, **{field: value})


def test_missing_certificate(settings, tmp_path):
    with pytest.raises(ValueError, match="certificate was not found"):
        replace(
            settings,
            sslrootcert=tmp_path / "missing.crt",
        )


@pytest.fixture
def environment_file(tmp_path, monkeypatch):
    for name in (
        "DATABASE_HOST",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_NAME",
        "DATABASE_PORT",
        "DATABASE_SSLMODE",
        "DATABASE_SSLROOTCERT",
        "DATABASE_CONNECT_TIMEOUT",
        "DATABASE_POOL_SIZE",
        "DATABASE_MAX_OVERFLOW",
        "DATABASE_POOL_TIMEOUT",
        "DATABASE_POOL_RECYCLE",
        "DATABASE_STATEMENT_TIMEOUT_MS",
        "MIGRATION_DATABASE_USER",
        "MIGRATION_DATABASE_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    certificate = tmp_path / "ca.crt"
    certificate.write_text("dummy certificate", encoding="utf-8")

    env_file = tmp_path / ".env"

    env_file.write_text(
        "DATABASE_HOST=database.example.com\n"
        "DATABASE_USER=test_user\n"
        "DATABASE_PASSWORD=test_password\n"
        "DATABASE_PORT=5432\n"
        f"DATABASE_SSLROOTCERT={certificate.as_posix()}\n",
        encoding="utf-8",
    )

    return env_file


def test_load_database_settings(environment_file):
    settings = DatabaseSettings.load(environment_file)

    assert settings.host == "database.example.com"
    assert settings.username == "test_user"
    assert settings.password == "test_password"
    assert settings.port == 5432


def test_environment_overrides_dotenv(environment_file, monkeypatch):
    monkeypatch.setenv("DATABASE_HOST", "override.example.com")

    settings = DatabaseSettings.load(environment_file)

    assert settings.host == "override.example.com"


def test_missing_required_setting(environment_file, monkeypatch):
    monkeypatch.setenv("DATABASE_PASSWORD", "")

    with pytest.raises(ValueError, match="DATABASE_PASSWORD"):
        DatabaseSettings.load(environment_file)


@pytest.mark.parametrize("value", ["invalid", "-1", "1.5", ""])
def test_invalid_numeric_environment_value(
    environment_file,
    monkeypatch,
    value,
):
    monkeypatch.setenv("DATABASE_PORT", value)

    with pytest.raises(ValueError, match="DATABASE_PORT"):
        DatabaseSettings.load(environment_file)


def test_runtime_credentials_remain_independent(
    environment_file,
    monkeypatch,
):
    monkeypatch.setenv(
        "MIGRATION_DATABASE_USER",
        "bli_migrator.test-project",
    )
    monkeypatch.setenv(
        "MIGRATION_DATABASE_PASSWORD",
        "migration-test-password",
    )

    settings = DatabaseSettings.load(environment_file)

    assert settings.username == "test_user"
    assert settings.password == "test_password"


def test_load_migration_credentials(
    environment_file,
    monkeypatch,
):
    monkeypatch.setenv(
        "MIGRATION_DATABASE_USER",
        "bli_migrator.test-project",
    )
    monkeypatch.setenv(
        "MIGRATION_DATABASE_PASSWORD",
        "migration-test-password",
    )

    settings = DatabaseSettings.load(
        environment_file,
        migration=True,
    )

    assert settings.username == "bli_migrator.test-project"
    assert settings.password == "migration-test-password"
    assert settings.host == "database.example.com"
    assert settings.sslmode == "verify-full"
    assert settings.password not in repr(settings)


def test_missing_migration_username(environment_file):
    with pytest.raises(
        ValueError,
        match="MIGRATION_DATABASE_USER",
    ):
        DatabaseSettings.load(
            environment_file,
            migration=True,
        )


def test_missing_migration_password(
    environment_file,
    monkeypatch,
):
    monkeypatch.setenv(
        "MIGRATION_DATABASE_USER",
        "bli_migrator.test-project",
    )

    with pytest.raises(
        ValueError,
        match="MIGRATION_DATABASE_PASSWORD",
    ):
        DatabaseSettings.load(
            environment_file,
            migration=True,
        )


@pytest.mark.parametrize(
    "username",
    [
        "postgres.test-project",
        "bli_app.test-project",
        "unknown_role.test-project",
    ],
)
def test_migration_rejects_unexpected_roles(
    environment_file,
    monkeypatch,
    username,
):
    monkeypatch.setenv(
        "MIGRATION_DATABASE_USER",
        username,
    )
    monkeypatch.setenv(
        "MIGRATION_DATABASE_PASSWORD",
        "migration-test-password",
    )

    with pytest.raises(
        ValueError,
        match="bli_migrator role",
    ):
        DatabaseSettings.load(
            environment_file,
            migration=True,
        )


@pytest.mark.parametrize(
    "migration",
    [None, 1, "true"],
)
def test_invalid_migration_flag(
    environment_file,
    migration,
):
    with pytest.raises(TypeError, match="must be a boolean"):
        DatabaseSettings.load(
            environment_file,
            migration=migration,
        )


def test_migration_credentials_from_dotenv(
    environment_file,
):
    with environment_file.open("a", encoding="utf-8") as file:
        file.write(
            "\nMIGRATION_DATABASE_USER=bli_migrator.test-project\n"
            "MIGRATION_DATABASE_PASSWORD=migration-test-password\n"
        )

    settings = DatabaseSettings.load(
        environment_file,
        migration=True,
    )

    assert settings.username == "bli_migrator.test-project"
    assert settings.password == "migration-test-password"
