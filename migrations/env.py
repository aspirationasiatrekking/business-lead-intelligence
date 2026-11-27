from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import text

from src.lead_intelligence.database.base import DATABASE_SCHEMA, Base
from src.lead_intelligence.database.engine import create_database_engine
from src.lead_intelligence.database.models import BusinessRecord
from src.lead_intelligence.database.settings import DatabaseSettings

config = context.config

if config.config_file_name is not None:
    fileConfig(
        config.config_file_name,
        disable_existing_loggers=False,
    )

target_metadata = BusinessRecord.metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION_TABLE = "alembic_version"

if target_metadata is not Base.metadata:
    raise RuntimeError("Unexpected migration metadata")


def include_name(name, type_, parent_names):
    """Restrict database reflection to the application schema."""

    if type_ == "schema":
        return name == DATABASE_SCHEMA

    if type_ == "table":
        return (
            parent_names.get("schema_name") == DATABASE_SCHEMA and name != VERSION_TABLE
        )

    return True


def configure_context(**kwargs) -> None:
    """Apply consistent migration configuration."""

    context.configure(
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table=VERSION_TABLE,
        version_table_schema=DATABASE_SCHEMA,
        compare_type=True,
        compare_server_default=True,
        transactional_ddl=True,
        **kwargs,
    )


def run_migrations_offline() -> None:
    """Generate PostgreSQL migration SQL without connecting."""

    configure_context(
        dialect_name="postgresql",
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Execute migrations using dedicated migration credentials."""

    settings = DatabaseSettings.load(
        PROJECT_ROOT / ".env",
        migration=True,
    )

    engine = create_database_engine(settings)

    try:
        with engine.connect() as connection:
            with connection.begin():
                current_role = connection.execute(
                    text("SELECT current_user")
                ).scalar_one()

                if current_role != "bli_migrator":
                    raise RuntimeError("Unexpected database migration role")

            configure_context(connection=connection)

            with context.begin_transaction():
                context.run_migrations()

    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
