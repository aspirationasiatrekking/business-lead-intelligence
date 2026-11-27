import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.lead_intelligence.database.base import (
    DATABASE_SCHEMA,
    Base,
)
from src.lead_intelligence.database.session import (
    create_session_factory,
    session_scope,
)


@pytest.fixture
def engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE test_records (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        )

    yield engine

    engine.dispose()


def test_declarative_base_schema():
    assert Base.metadata.schema == DATABASE_SCHEMA


def test_create_session_factory(engine):
    factory = create_session_factory(engine)

    with factory() as session:
        assert isinstance(session, Session)
        assert session.bind is engine
        assert session.autoflush is False
        assert session.expire_on_commit is False


def test_session_scope_commits_successful_transaction(engine):
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(
            text("INSERT INTO test_records (name) VALUES (:name)"),
            {"name": "Demo Business"},
        )

    with engine.connect() as connection:
        result = connection.execute(text("SELECT name FROM test_records")).scalar_one()

    assert result == "Demo Business"


def test_session_scope_rolls_back_failed_transaction(engine):
    factory = create_session_factory(engine)

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with session_scope(factory) as session:
            session.execute(
                text("INSERT INTO test_records (name) VALUES (:name)"),
                {"name": "Failed Business"},
            )

            raise RuntimeError("Simulated failure")

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM test_records")
        ).scalar_one()

    assert count == 0


def test_multiple_transactions_remain_independent(engine):
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(
            text("INSERT INTO test_records (name) VALUES (:name)"),
            {"name": "Committed Business"},
        )

    with pytest.raises(RuntimeError):
        with session_scope(factory) as session:
            session.execute(
                text("INSERT INTO test_records (name) VALUES (:name)"),
                {"name": "Failed Business"},
            )
            raise RuntimeError("Simulated failure")

    with engine.connect() as connection:
        names = (
            connection.execute(text("SELECT name FROM test_records")).scalars().all()
        )

    assert names == ["Committed Business"]
