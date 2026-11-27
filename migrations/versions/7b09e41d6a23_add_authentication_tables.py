"""Add authentication storage without altering existing job ownership."""

import sqlalchemy as sa
from alembic import op

revision = "7b09e41d6a23"
down_revision = "2536292d4290"
branch_labels = None
depends_on = None
SCHEMA = "lead_intelligence"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        sa.CheckConstraint(
            "username ~ '^[a-z0-9][a-z0-9_.-]{2,63}$'",
            name=op.f("ck_users_username_format"),
        ),
        sa.CheckConstraint(
            "length(btrim(display_name)) BETWEEN 1 AND 100",
            name=op.f("ck_users_display_name_length"),
        ),
        sa.CheckConstraint("role IN ('admin', 'employee')", name=op.f("ck_users_role")),
        sa.CheckConstraint(
            "password_hash LIKE '$argon2id$%'", name=op.f("ck_users_password_hash_type")
        ),
        sa.CheckConstraint(
            "role <> 'admin' OR is_active", name=op.f("ck_users_admin_active")
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_users_single_admin",
        "users",
        ["role"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("role = 'admin'"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            name=op.f("fk_user_sessions_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_sessions_token_hash")),
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_user_sessions_token_hash_format"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name=op.f("ck_user_sessions_expiry_order")
        ),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name=op.f("ck_user_sessions_revocation_order"),
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_user_sessions_user_id", "user_sessions", ["user_id"], schema=SCHEMA
    )
    for table in ("users", "user_sessions"):
        relation = f"{SCHEMA}.{table}"
        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE {relation} "
            "FROM PUBLIC, anon, authenticated, service_role, bli_app"
        )
        op.execute(f"ALTER TABLE {relation} ENABLE ROW LEVEL SECURITY")
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE {relation} TO bli_app")
        op.execute(
            f"CREATE POLICY bli_app_select ON {relation} "
            "FOR SELECT TO bli_app USING (true)"
        )
        op.execute(
            f"CREATE POLICY bli_app_insert ON {relation} "
            "FOR INSERT TO bli_app WITH CHECK (true)"
        )
        op.execute(
            f"CREATE POLICY bli_app_update ON {relation} "
            "FOR UPDATE TO bli_app USING (true) WITH CHECK (true)"
        )
    op.add_column("search_jobs", sa.Column("created_by", sa.Uuid()), schema=SCHEMA)
    op.create_foreign_key(
        "fk_search_jobs_created_by_users",
        "search_jobs",
        "users",
        ["created_by"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_lead_intelligence_search_jobs_created_by",
        "search_jobs",
        ["created_by"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    # Never silently destroy employee credentials or job attribution.
    raise RuntimeError("Authentication downgrade requires a reviewed restore plan")
