"""Initial catalog and optimization queue schema.

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "semesters",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("prepared_at", sa.Date(), nullable=False),
        sa.Column("dataset_version", sa.String(length=64), nullable=False, unique=True),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "courses",
        sa.Column("semester_id", sa.String(length=20), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("credits", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("semester_id", "course_code"),
    )
    op.create_table(
        "rooms",
        sa.Column("semester_id", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("building_code", sa.String(length=40)),
        sa.Column("building_name", sa.Text()),
        sa.Column("label", sa.Text()),
        sa.Column("room_type", sa.Text()),
        sa.Column("capacity", sa.Integer()),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("semester_id", "code"),
    )
    op.create_table(
        "sections",
        sa.Column("semester_id", sa.String(length=20), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("section_code", sa.String(length=20), nullable=False),
        sa.Column("professor", sa.Text()),
        sa.Column("raw_lecture_time", sa.Text(), nullable=False),
        sa.Column("time_to_be_announced", sa.Boolean(), nullable=False),
        sa.Column("warning_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["semester_id", "course_code"],
            ["courses.semester_id", "courses.course_code"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("semester_id", "course_code", "section_code"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("semester_id", sa.String(length=20), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("section_code", sa.String(length=20), nullable=False),
        sa.Column("day", sa.String(length=1), nullable=False),
        sa.Column("start_minute", sa.SmallInteger(), nullable=False),
        sa.Column("end_minute", sa.SmallInteger(), nullable=False),
        sa.Column("room_code", sa.String(length=40)),
        sa.CheckConstraint("start_minute >= 0 AND start_minute < 1440", "ck_session_start"),
        sa.CheckConstraint("end_minute > start_minute AND end_minute <= 1440", "ck_session_end"),
        sa.CheckConstraint("day IN ('월','화','수','목','금','토','일')", "ck_session_day"),
        sa.ForeignKeyConstraint(
            ["semester_id", "course_code", "section_code"],
            ["sections.semester_id", "sections.course_code", "sections.section_code"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id", "room_code"],
            ["rooms.semester_id", "rooms.code"],
        ),
    )
    op.create_index(
        "ix_sessions_section",
        "sessions",
        ["semester_id", "course_code", "section_code"],
    )
    op.create_table(
        "data_imports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("semester_id", sa.String(length=20), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("semester_id", "checksum", "parser_version"),
    )
    op.create_table(
        "optimization_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_snapshot", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("error_code", sa.String(length=80)),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("lease_token", sa.String(length=36), unique=True),
        sa.Column("worker_id", sa.String(length=120)),
        sa.Column("leased_until", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_optimization_jobs_status", "optimization_jobs", ["status"])
    op.create_index(
        "ix_optimization_jobs_claim",
        "optimization_jobs",
        ["status", "leased_until", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_optimization_jobs_claim", table_name="optimization_jobs")
    op.drop_index("ix_optimization_jobs_status", table_name="optimization_jobs")
    op.drop_table("optimization_jobs")
    op.drop_table("data_imports")
    op.drop_index("ix_sessions_section", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("sections")
    op.drop_table("rooms")
    op.drop_table("courses")
    op.drop_table("semesters")
