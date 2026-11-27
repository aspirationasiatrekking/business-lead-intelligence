"""Transactional authentication primitives; not a public login endpoint.

Use one clean READ COMMITTED session per operation. Commit before issuing a
credential, and finish the transaction promptly. All credential/session writers
must lock the owning user first. HTTP rate limiting must precede login calls.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.lead_intelligence.auth.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    normalize_username,
    verify_password,
)
from src.lead_intelligence.database.models import UserRecord, UserSessionRecord
from src.lead_intelligence.database.repositories.auth import (
    SessionRepository,
    UserRepository,
)

SESSION_LIFETIME = timedelta(hours=8)
TEMPORARY_SESSION_LIFETIME = timedelta(minutes=10)
# Public dummy verifier generated from a discarded random password. Never used
# to authenticate a user; it only reduces unknown-account timing differences.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$UZdzEPhyqreYSmfv+jgbig$"
    "mXEybbf9WjjMjP6zOBGt8hI9CgCIuYEhxZOX1qKthcA"
)


class InvalidCredentialsError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


class PasswordChangeRequiredError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    id: UUID
    username: str
    display_name: str
    role: str
    must_change_password: bool


@dataclass(frozen=True, slots=True)
class LoginResult:
    principal: Principal
    expires_at: datetime
    token: str = field(repr=False)


def _principal(user: UserRecord) -> Principal:
    return Principal(
        user.id, user.username, user.display_name, user.role, user.must_change_password
    )


class AuthenticationService:
    def __init__(self, session: Session):
        self.session = session
        self.users = UserRepository(session)
        self.sessions = SessionRepository(session)

    def _begin(self) -> None:
        if self.session.new or self.session.dirty or self.session.deleted:
            raise RuntimeError("Authentication requires a clean database session")
        if self.session.scalar(text("SHOW transaction_isolation")) != "read committed":
            raise RuntimeError("Authentication requires READ COMMITTED isolation")

    def _now(self) -> datetime:
        return self.session.scalar(select(func.clock_timestamp()))

    def login(self, username: str, password: str) -> LoginResult:
        self._begin()
        try:
            normalized = normalize_username(username)
        except ValueError:
            normalized = None
        user = self.users.lock_by_username(normalized) if normalized else None
        eligible = user is not None and user.is_active
        valid = verify_password(
            password, user.password_hash if eligible else _DUMMY_HASH
        )
        if not eligible or not valid:
            raise InvalidCredentialsError("Invalid username or password")
        now = self._now()
        lifetime = (
            TEMPORARY_SESSION_LIFETIME
            if user.must_change_password
            else SESSION_LIFETIME
        )
        token = generate_session_token()
        expires_at = now + lifetime
        user.last_login_at = max(now, user.last_login_at or now)
        self.sessions.create(user.id, hash_session_token(token), now, expires_at)
        return LoginResult(_principal(user), expires_at, token)

    def _locked_session(
        self, token: str
    ) -> tuple[UserRecord, UserSessionRecord, datetime]:
        try:
            digest = hash_session_token(token)
        except ValueError:
            raise InvalidSessionError("Invalid or expired session") from None
        owner_id = self.sessions.owner_id(digest)
        if owner_id is None:
            raise InvalidSessionError("Invalid or expired session")
        user = self.users.lock_by_id(owner_id)
        if user is None or not user.is_active:
            raise InvalidSessionError("Invalid or expired session")
        record = self.sessions.find(owner_id, digest)
        now = self._now()
        if record is None or record.revoked_at is not None or record.expires_at <= now:
            raise InvalidSessionError("Invalid or expired session")
        return user, record, now

    def authenticate(
        self, token: str, *, allow_password_change: bool = False
    ) -> Principal:
        self._begin()
        user, _, _ = self._locked_session(token)
        if user.must_change_password and not allow_password_change:
            raise PasswordChangeRequiredError("Password change required")
        return _principal(user)

    def logout(self, token: str) -> None:
        self._begin()
        try:
            _, record, now = self._locked_session(token)
        except InvalidSessionError:
            return
        record.revoked_at = max(now, record.created_at)
        self.session.flush()

    def change_password(self, token: str, current: str, replacement: str) -> None:
        self._begin()
        user, _, _ = self._locked_session(token)
        if not verify_password(current, user.password_hash):
            raise InvalidCredentialsError("Invalid current password")
        if current == replacement:
            raise ValueError("Choose a different password")
        user.password_hash = hash_password(replacement)
        user.must_change_password = False
        self.sessions.revoke_all(user.id, self._now())
        self.session.flush()
