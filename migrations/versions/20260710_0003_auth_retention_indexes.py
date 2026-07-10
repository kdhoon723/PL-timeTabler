"""Add indexes used by authentication record retention.

Revision ID: 20260710_0003
Revises: 20260710_0002
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260710_0003"
down_revision: str | None = "20260710_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_auth_otp_challenges_created",
        "auth_otp_challenges",
        ["created_at"],
    )
    op.create_index("ix_auth_sessions_expires", "auth_sessions", ["expires_at"])
    op.create_index("ix_auth_sessions_revoked", "auth_sessions", ["revoked_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_revoked", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_expires", table_name="auth_sessions")
    op.drop_index("ix_auth_otp_challenges_created", table_name="auth_otp_challenges")
