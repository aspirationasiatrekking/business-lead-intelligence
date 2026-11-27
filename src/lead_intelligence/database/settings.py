import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Validated configuration for PostgreSQL connectivity."""

    host: str
    username: str
    password: str = field(repr=False)

    database: str = "postgres"
    port: int = 5432

    sslmode: str = "verify-full"
    sslrootcert: Path | None = None

    connect_timeout: int = 10
    pool_size: int = 3
    max_overflow: int = 2
    pool_timeout: int = 30
    pool_recycle: int = 1800
    statement_timeout_ms: int = 30000

    def __post_init__(self) -> None:
        for name in ("host", "username", "database"):
            value = getattr(self, name)

            if (
                not isinstance(value, str)
                or not value.strip()
                or any(c.isspace() or ord(c) < 32 for c in value)
            ):
                raise ValueError(f"Invalid database {name}")

        if (
            not isinstance(self.password, str)
            or not self.password
            or any(ord(c) < 32 for c in self.password)
        ):
            raise ValueError("Invalid database password")

        bounds = (
            ("port", 1, 65535),
            ("connect_timeout", 1, 30),
            ("pool_size", 1, 10),
            ("max_overflow", 0, 5),
            ("pool_timeout", 1, 60),
            ("pool_recycle", 60, 3600),
            ("statement_timeout_ms", 1000, 120000),
        )

        for name, minimum, maximum in bounds:
            value = getattr(self, name)

            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be between {minimum} and {maximum}")

        if self.sslmode != "verify-full":
            raise ValueError("Database SSL mode must be verify-full")

        if not isinstance(self.sslrootcert, Path):
            raise ValueError("Database SSL root certificate is required")

        if not self.sslrootcert.is_file():
            raise ValueError("Database SSL root certificate was not found")

    @classmethod
    def load(
        cls,
        env_file: Path | None = None,
        *,
        migration: bool = False,
    ) -> "DatabaseSettings":
        """Load runtime or dedicated migration database credentials."""

        if type(migration) is not bool:
            raise TypeError("Migration flag must be a boolean")

        values = (
            dotenv_values(
                env_file,
                interpolate=False,
            )
            if env_file
            else {}
        )

        values.update(os.environ)

        def required(name: str) -> str:
            value = values.get(name)

            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

            return value

        def integer(name: str, default: int) -> int:
            value = values.get(name, str(default))

            if (
                not isinstance(value, str)
                or not value.isascii()
                or not value.isdecimal()
            ):
                raise ValueError(f"{name} must be an integer")

            return int(value)

        credential_prefix = "MIGRATION_DATABASE" if migration else "DATABASE"

        username = required(f"{credential_prefix}_USER")
        password = required(f"{credential_prefix}_PASSWORD")

        if migration:
            role_name = username.split(".", 1)[0]

            if role_name != "bli_migrator":
                raise ValueError("Migration credentials must use the bli_migrator role")

        return cls(
            host=required("DATABASE_HOST"),
            username=username,
            password=password,
            database=values.get("DATABASE_NAME", "postgres"),
            port=integer("DATABASE_PORT", 5432),
            sslmode=values.get("DATABASE_SSLMODE", "verify-full"),
            sslrootcert=Path(required("DATABASE_SSLROOTCERT")).expanduser(),
            connect_timeout=integer("DATABASE_CONNECT_TIMEOUT", 10),
            pool_size=integer("DATABASE_POOL_SIZE", 3),
            max_overflow=integer("DATABASE_MAX_OVERFLOW", 2),
            pool_timeout=integer("DATABASE_POOL_TIMEOUT", 30),
            pool_recycle=integer("DATABASE_POOL_RECYCLE", 1800),
            statement_timeout_ms=integer(
                "DATABASE_STATEMENT_TIMEOUT_MS",
                30000,
            ),
        )
