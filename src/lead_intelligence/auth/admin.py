"""Employee administration; caller owns the transaction and admin row lock."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.lead_intelligence.auth.security import (
    hash_password,
    normalize_username,
    verify_password,
)
from src.lead_intelligence.database.models import UserRecord
from src.lead_intelligence.database.repositories.auth import (
    SessionRepository,
    UserRepository,
)


class EmployeeExistsError(Exception):
    pass


class EmployeeNotFoundError(Exception):
    pass


def validate_display_name(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 100 or any(not char.isprintable() for char in value):
        raise ValueError("Invalid display name")
    return value


class EmployeeService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)

    def create(self, username: str, display_name: str, password: str) -> UserRecord:
        statement = (
            insert(UserRecord)
            .values(
                username=normalize_username(username),
                display_name=validate_display_name(display_name),
                password_hash=hash_password(password),
                role="employee",
                is_active=True,
                must_change_password=True,
            )
            .on_conflict_do_nothing(index_elements=[UserRecord.username])
            .returning(UserRecord)
        )
        user = self.session.scalar(statement)
        if user is None:
            raise EmployeeExistsError()
        return user

    def list(self, *, limit: int, offset: int) -> list[UserRecord]:
        statement = (
            select(UserRecord)
            .where(UserRecord.role == "employee")
            .order_by(UserRecord.username, UserRecord.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def _employee(self, user_id: UUID) -> UserRecord:
        user = self.users.lock_by_id(user_id)
        if user is None or user.role != "employee":
            raise EmployeeNotFoundError()
        return user

    def _revoke(self, user_id: UUID) -> None:
        now = self.session.scalar(select(func.clock_timestamp()))
        self.sessions.revoke_all(user_id, now)

    def update(
        self, user_id: UUID, *, display_name: str | None, is_active: bool | None
    ) -> UserRecord:
        user = self._employee(user_id)
        if display_name is not None:
            user.display_name = validate_display_name(display_name)
        if is_active is not None and user.is_active != is_active:
            self._revoke(user.id)
            user.is_active = is_active
        self.session.flush()
        return user

    def reset_password(self, user_id: UUID, password: str) -> None:
        user = self._employee(user_id)
        if verify_password(password, user.password_hash):
            raise ValueError("Choose a different password")
        user.password_hash = hash_password(password)
        user.must_change_password = True
        self._revoke(user.id)
        self.session.flush()
