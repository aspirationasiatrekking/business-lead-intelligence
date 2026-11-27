"""Create the initial administrator interactively on a trusted host."""

import getpass
import sys
import warnings
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.lead_intelligence.auth.security import hash_password, normalize_username
from src.lead_intelligence.database.engine import create_database_engine
from src.lead_intelligence.database.models import UserRecord
from src.lead_intelligence.database.session import create_session_factory
from src.lead_intelligence.database.settings import DatabaseSettings


def create_initial_admin(
    session: Session, username: str, display_name: str, password: str
) -> None:
    if session.scalar(text("SELECT current_user")) != "bli_app":
        raise RuntimeError("Administrator bootstrap requires the runtime role")
    username = normalize_username(username)
    display_name = display_name.strip()
    if not 1 <= len(display_name) <= 100 or any(
        ord(char) < 32 or ord(char) == 127 for char in display_name
    ):
        raise ValueError("Invalid display name")
    if session.scalar(select(UserRecord.id).where(UserRecord.role == "admin")):
        raise RuntimeError("Administrator already exists")
    session.add(
        UserRecord(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
            must_change_password=False,
        )
    )
    # The unique partial index also rejects simultaneous bootstrap attempts.
    session.flush()


def main() -> int:
    if not sys.stdin.isatty():
        print(
            "Administrator bootstrap requires an interactive terminal.", file=sys.stderr
        )
        return 1
    engine = None
    try:
        username = normalize_username(input("Administrator username: "))
        display_name = input("Display name: ")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Password (at least 15 characters): ")
            confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise ValueError("Passwords do not match")
        settings = DatabaseSettings.load(Path(__file__).resolve().parents[1] / ".env")
        if settings.username.split(".", 1)[0] != "bli_app":
            raise RuntimeError("Invalid database role")
        engine = create_database_engine(settings)
        factory = create_session_factory(engine)
        with factory.begin() as session:
            create_initial_admin(session, username, display_name, password)
        print("Initial administrator created.")
        return 0
    except (
        ValueError,
        RuntimeError,
        SQLAlchemyError,
        getpass.GetPassWarning,
        EOFError,
        KeyboardInterrupt,
        OSError,
    ):
        # Do not print raw exception messages, SQL parameters or credentials.
        print(
            "Administrator creation failed; no success was confirmed.", file=sys.stderr
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
