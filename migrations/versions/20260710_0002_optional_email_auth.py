"""Add optional school-email OTP authentication.

Revision ID: 20260710_0002
Revises: 20260710_0001
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260710_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_otp_challenges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("student_number", sa.String(length=20), nullable=False),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("invalidated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auth_otp_challenges_student_created",
        "auth_otp_challenges",
        ["student_number", "created_at"],
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("student_number", sa.String(length=20), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_student", "auth_sessions", ["student_number"])
    op.create_index(
        "ix_auth_sessions_token_digest",
        "auth_sessions",
        ["token_digest"],
        unique=True,
    )
    op.create_table(
        "auth_rate_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("account_digest", sa.String(length=64), nullable=False),
        sa.Column("ip_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auth_rate_events_account",
        "auth_rate_events",
        ["kind", "account_digest", "created_at"],
    )
    op.create_index(
        "ix_auth_rate_events_ip",
        "auth_rate_events",
        ["kind", "ip_digest", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_rate_events_ip", table_name="auth_rate_events")
    op.drop_index("ix_auth_rate_events_account", table_name="auth_rate_events")
    op.drop_table("auth_rate_events")
    op.drop_index("ix_auth_sessions_token_digest", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_student", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index(
        "ix_auth_otp_challenges_student_created",
        table_name="auth_otp_challenges",
    )
    op.drop_table("auth_otp_challenges")
