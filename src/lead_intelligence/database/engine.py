from sqlalchemy import URL, create_engine, event, text
from sqlalchemy.engine import Engine

from src.lead_intelligence.database.settings import DatabaseSettings


def _configure_statement_timeout(
    dbapi_connection,
    connection_record,
    connection_proxy,
    *,
    timeout_ms: int,
) -> None:
    """Apply and verify the timeout before a pooled connection is used."""

    original_autocommit = dbapi_connection.autocommit

    try:
        dbapi_connection.autocommit = True

        with dbapi_connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, false)",
                (str(timeout_ms),),
            )

            cursor.execute(
                "SELECT setting, unit FROM pg_settings WHERE name = 'statement_timeout'"
            )

            result = cursor.fetchone()

            if result != (str(timeout_ms), "ms"):
                raise RuntimeError("Database statement timeout verification failed")

    finally:
        dbapi_connection.autocommit = original_autocommit


def create_database_engine(
    settings: DatabaseSettings,
) -> Engine:
    """Create a bounded, TLS-verified PostgreSQL engine."""

    if not isinstance(settings, DatabaseSettings):
        raise TypeError("Expected DatabaseSettings")

    url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.username,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )

    engine = create_engine(
        url,
        connect_args={
            "sslmode": settings.sslmode,
            "sslrootcert": str(settings.sslrootcert.resolve()),
            "connect_timeout": settings.connect_timeout,
        },
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        pool_pre_ping=True,
        pool_use_lifo=True,
        echo=False,
        hide_parameters=True,
    )

    @event.listens_for(engine, "checkout")
    def configure_connection(
        dbapi_connection,
        connection_record,
        connection_proxy,
    ) -> None:
        _configure_statement_timeout(
            dbapi_connection,
            connection_record,
            connection_proxy,
            timeout_ms=settings.statement_timeout_ms,
        )

    return engine


def check_database_connection(engine: Engine) -> bool:
    """Check database availability using a minimal read-only query."""

    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1
