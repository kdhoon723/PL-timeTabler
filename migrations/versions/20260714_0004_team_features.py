"""Add user-owned timetable, review, and completion data.

Revision ID: 20260714_0004
Revises: 20260710_0003
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0004"
down_revision: str | None = "20260710_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("student_number", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120)),
        sa.Column("grade", sa.Integer()),
        sa.Column("department", sa.String(length=200)),
        sa.Column("admission_year", sa.Integer()),
        sa.Column("entry_type", sa.String(length=24)),
        sa.Column("student_type", sa.String(length=24)),
        sa.Column("section_group", sa.String(length=24)),
        sa.Column("major_path", sa.String(length=32)),
        sa.Column("profile_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_student_number", "users", ["student_number"], unique=True)

    op.create_table(
        "privacy_consents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("consent_version", sa.String(length=40), nullable=False),
        sa.Column("agreed", sa.Boolean(), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_privacy_consents_user_id", "privacy_consents", ["user_id"])
    op.create_index(
        "ix_privacy_consents_user_agreed", "privacy_consents", ["user_id", "agreed_at"]
    )

    op.create_table(
        "saved_timetables",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("semester", sa.String(length=20), nullable=False),
        sa.Column("dataset_version", sa.String(length=80)),
        sa.Column("items_snapshot", sa.JSON(), nullable=False),
        sa.Column("preferences_snapshot", sa.JSON(), nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_saved_timetables_user_id", "saved_timetables", ["user_id"])
    op.create_index(
        "ix_saved_timetables_user_semester", "saved_timetables", ["user_id", "semester"]
    )
    op.create_index(
        "ix_saved_timetables_user_favorite", "saved_timetables", ["user_id", "favorite"]
    )

    op.create_table(
        "timetable_shares",
        sa.Column("share_code", sa.String(length=32), primary_key=True),
        sa.Column("timetable_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["timetable_id"], ["saved_timetables.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_timetable_shares_timetable", "timetable_shares", ["timetable_id"])

    op.create_table(
        "course_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("course_name", sa.String(length=240), nullable=False),
        sa.Column("professor", sa.String(length=120)),
        sa.Column("semester", sa.String(length=20), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "course_code",
            "professor",
            "semester",
            name="uq_course_reviews_author_course_offering",
        ),
    )
    op.create_index("ix_course_reviews_user_id", "course_reviews", ["user_id"])
    op.create_index(
        "ix_course_reviews_course_professor", "course_reviews", ["course_code", "professor"]
    )
    op.create_index(
        "ix_course_reviews_user_created", "course_reviews", ["user_id", "created_at"]
    )

    op.create_table(
        "completed_courses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("course_code", sa.String(length=40)),
        sa.Column("course_name", sa.String(length=240), nullable=False),
        sa.Column("credits", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=160), nullable=False),
        sa.Column("area", sa.String(length=120)),
        sa.Column("semester", sa.String(length=20)),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_completed_courses_user_id", "completed_courses", ["user_id"])
    op.create_index(
        "ix_completed_courses_user_status", "completed_courses", ["user_id", "status"]
    )
    op.create_index(
        "ix_completed_courses_user_semester", "completed_courses", ["user_id", "semester"]
    )


def downgrade() -> None:
    op.drop_index("ix_completed_courses_user_semester", table_name="completed_courses")
    op.drop_index("ix_completed_courses_user_status", table_name="completed_courses")
    op.drop_index("ix_completed_courses_user_id", table_name="completed_courses")
    op.drop_table("completed_courses")
    op.drop_index("ix_course_reviews_user_created", table_name="course_reviews")
    op.drop_index("ix_course_reviews_course_professor", table_name="course_reviews")
    op.drop_index("ix_course_reviews_user_id", table_name="course_reviews")
    op.drop_table("course_reviews")
    op.drop_index("ix_timetable_shares_timetable", table_name="timetable_shares")
    op.drop_table("timetable_shares")
    op.drop_index("ix_saved_timetables_user_favorite", table_name="saved_timetables")
    op.drop_index("ix_saved_timetables_user_semester", table_name="saved_timetables")
    op.drop_index("ix_saved_timetables_user_id", table_name="saved_timetables")
    op.drop_table("saved_timetables")
    op.drop_index("ix_privacy_consents_user_agreed", table_name="privacy_consents")
    op.drop_index("ix_privacy_consents_user_id", table_name="privacy_consents")
    op.drop_table("privacy_consents")
    op.drop_index("ix_users_student_number", table_name="users")
    op.drop_table("users")
