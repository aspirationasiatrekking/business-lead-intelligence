from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(
    engine: Engine,
) -> sessionmaker[Session]:
    """Create a factory for short-lived database sessions."""

    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session],
) -> Iterator[Session]:
    """Commit successful transactions and roll back failed transactions."""

    with session_factory.begin() as session:
        yield session
