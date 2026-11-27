from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.lead_intelligence.database.base import Base
from src.lead_intelligence.database.models.common import (
    CreatedAtMixin,
    TimestampMixin,
    UUIDMixin,
)


class UserRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "username ~ '^[a-z0-9][a-z0-9_.-]{2,63}$'", name="username_format"
        ),
        CheckConstraint(
            "length(btrim(display_name)) BETWEEN 1 AND 100", name="display_name_length"
        ),
        CheckConstraint("role IN ('admin', 'employee')", name="role"),
        CheckConstraint("password_hash LIKE '$argon2id$%'", name="password_hash_type"),
        CheckConstraint("role <> 'admin' OR is_active", name="admin_active"),
        Index(
            "uq_users_single_admin",
            "role",
            unique=True,
            postgresql_where=text("role = 'admin'"),
        ),
    )
    username: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true")
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSessionRecord(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_hash_format"),
        CheckConstraint("expires_at > created_at", name="expiry_order"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at", name="revocation_order"
        ),
        Index("ix_user_sessions_user_id", "user_id"),
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
