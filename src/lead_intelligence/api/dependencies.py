from collections.abc import Iterator
from pathlib import Path

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.lead_intelligence.database.engine import create_database_engine
from src.lead_intelligence.database.settings import DatabaseSettings


def build_runtime_engine() -> Engine:
    """Load runtime credentials only, when the application starts."""
    root = Path(__file__).resolve().parents[3]
    settings = DatabaseSettings.load(root / ".env")
    if settings.username.split(".", 1)[0] != "bli_app":
        raise RuntimeError("API requires the restricted runtime database role.")
    return create_database_engine(settings)


def get_session(request: Request) -> Iterator[Session]:
    """Provide a request-local session; services own commit boundaries."""
    with request.app.state.session_factory() as session:
        yield session
