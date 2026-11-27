"""Authentication queries. Callers own transactions; user rows serialize changes."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from src.lead_intelligence.database.models import UserRecord, UserSessionRecord


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def lock_by_username(self, username: str) -> UserRecord | None:
        return self.session.scalar(
            select(UserRecord)
            .where(UserRecord.username == username)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    def lock_by_id(self, user_id: UUID) -> UserRecord | None:
        return self.session.scalar(
            select(UserRecord)
            .where(UserRecord.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )


class SessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def owner_id(self, token_hash: str) -> UUID | None:
        return self.session.scalar(
            select(UserSessionRecord.user_id).where(
                UserSessionRecord.token_hash == token_hash
            )
        )

    def find(self, user_id: UUID, token_hash: str) -> UserSessionRecord | None:
        # The caller must already hold the owning user row lock.
        return self.session.scalar(
            select(UserSessionRecord)
            .where(
                UserSessionRecord.user_id == user_id,
                UserSessionRecord.token_hash == token_hash,
            )
            .execution_options(populate_existing=True)
        )

    def create(
        self, user_id: UUID, token_hash: str, now: datetime, expires_at: datetime
    ) -> UserSessionRecord:
        record = UserSessionRecord(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def revoke_all(self, user_id: UUID, now: datetime) -> None:
        # Use greatest to preserve timestamp constraints after clock corrections.
        self.session.execute(
            update(UserSessionRecord)
            .where(
                UserSessionRecord.user_id == user_id,
                UserSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=func.greatest(now, UserSessionRecord.created_at))
        )
