"""Store the complete DREAMS history archive and link completed courses.

Revision ID: 20260715_0005
Revises: 20260714_0004
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260715_0005"
down_revision: str | None = "20260714_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_archive_manifests",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("source_archive", sa.LargeBinary(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "historical_term_datasets",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("term_code", sa.String(length=8), nullable=False),
        sa.Column("term_name", sa.String(length=80), nullable=False),
        sa.Column("data_status", sa.String(length=24), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("source_archive", sa.LargeBinary(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "academic_year", "term_code", name="uq_historical_term_year_code"
        ),
    )
    op.create_index(
        "ix_historical_term_year_code",
        "historical_term_datasets",
        ["academic_year", "term_code"],
    )
    op.create_table(
        "historical_course_offerings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=20), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("term_code", sa.String(length=8), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("section_code", sa.String(length=40), nullable=False),
        sa.Column("korean_name", sa.String(length=240), nullable=False),
        sa.Column("english_name", sa.String(length=400)),
        sa.Column("professor_name", sa.String(length=240)),
        sa.Column("completion_category", sa.String(length=160)),
        sa.Column("credits", sa.Float()),
        sa.Column("lecture_hours", sa.Float()),
        sa.Column("practice_hours", sa.Float()),
        sa.Column("raw_lecture_time", sa.Text()),
        sa.Column("raw_location", sa.Text()),
        sa.Column("target_grade", sa.String(length=120)),
        sa.Column("listing_status", sa.String(length=40)),
        sa.Column("detail_status", sa.String(length=40)),
        sa.Column("category_contexts", sa.JSON(), nullable=False),
        sa.Column("department_contexts", sa.JSON(), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("department_search_text", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["historical_term_datasets.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "academic_year",
            "term_code",
            "course_code",
            "section_code",
            name="uq_historical_offering_identity",
        ),
    )
    op.create_index(
        "ix_historical_course_offerings_dataset_id",
        "historical_course_offerings",
        ["dataset_id"],
    )
    op.create_index(
        "ix_historical_offering_term",
        "historical_course_offerings",
        ["academic_year", "term_code"],
    )
    op.create_index(
        "ix_historical_offering_course", "historical_course_offerings", ["course_code"]
    )
    op.create_index(
        "ix_historical_offering_name", "historical_course_offerings", ["korean_name"]
    )
    op.create_index(
        "ix_historical_offering_category",
        "historical_course_offerings",
        ["completion_category"],
    )
    op.create_table(
        "historical_curriculum_datasets",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("department_count", sa.Integer(), nullable=False),
        sa.Column("course_record_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("source_archive", sa.LargeBinary(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_historical_curriculum_datasets_academic_year",
        "historical_curriculum_datasets",
        ["academic_year"],
        unique=True,
    )
    op.create_table(
        "historical_curriculum_departments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=20), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("college_code", sa.String(length=40)),
        sa.Column("college_name", sa.String(length=240)),
        sa.Column("department_code", sa.String(length=40), nullable=False),
        sa.Column("department_name", sa.String(length=240), nullable=False),
        sa.Column("course_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["historical_curriculum_datasets.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "academic_year",
            "department_code",
            name="uq_historical_curriculum_department",
        ),
    )
    op.create_index(
        "ix_historical_curriculum_departments_dataset_id",
        "historical_curriculum_departments",
        ["dataset_id"],
    )
    op.create_index(
        "ix_historical_curriculum_department_name",
        "historical_curriculum_departments",
        ["department_name"],
    )
    op.create_table(
        "historical_relation_datasets",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("replacement_count", sa.Integer(), nullable=False),
        sa.Column("equivalent_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("source_archive", sa.LargeBinary(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "historical_course_relations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=40), nullable=False),
        sa.Column("relation_type", sa.String(length=24), nullable=False),
        sa.Column("designated_year", sa.String(length=20)),
        sa.Column("designated_term", sa.String(length=20)),
        sa.Column("original_course_name", sa.String(length=240), nullable=False),
        sa.Column("original_category", sa.String(length=160)),
        sa.Column("original_credits", sa.Float()),
        sa.Column("original_college", sa.String(length=240)),
        sa.Column("original_department", sa.String(length=240)),
        sa.Column("related_course_name", sa.String(length=240), nullable=False),
        sa.Column("related_category", sa.String(length=160)),
        sa.Column("related_credits", sa.Float()),
        sa.Column("related_department", sa.String(length=240)),
        sa.Column("note", sa.Text()),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"], ["historical_relation_datasets.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_historical_course_relations_dataset_id",
        "historical_course_relations",
        ["dataset_id"],
    )
    op.create_index(
        "ix_historical_relation_type_year",
        "historical_course_relations",
        ["relation_type", "designated_year"],
    )
    op.create_index(
        "ix_historical_relation_original_name",
        "historical_course_relations",
        ["original_course_name"],
    )
    op.create_index(
        "ix_historical_relation_related_name",
        "historical_course_relations",
        ["related_course_name"],
    )
    op.add_column(
        "completed_courses", sa.Column("historical_offering_id", sa.String(length=36))
    )
    op.add_column("completed_courses", sa.Column("section_code", sa.String(length=40)))
    op.add_column(
        "completed_courses",
        sa.Column(
            "input_source",
            sa.String(length=32),
            nullable=False,
            server_default="MANUAL",
        ),
    )
    op.add_column("completed_courses", sa.Column("source_snapshot", sa.JSON()))
    op.create_foreign_key(
        "fk_completed_courses_historical_offering",
        "completed_courses",
        "historical_course_offerings",
        ["historical_offering_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_completed_courses_historical_offering_id",
        "completed_courses",
        ["historical_offering_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_completed_courses_historical_offering_id", table_name="completed_courses"
    )
    op.drop_constraint(
        "fk_completed_courses_historical_offering", "completed_courses", type_="foreignkey"
    )
    op.drop_column("completed_courses", "source_snapshot")
    op.drop_column("completed_courses", "input_source")
    op.drop_column("completed_courses", "section_code")
    op.drop_column("completed_courses", "historical_offering_id")
    op.drop_index(
        "ix_historical_relation_related_name", table_name="historical_course_relations"
    )
    op.drop_index(
        "ix_historical_relation_original_name", table_name="historical_course_relations"
    )
    op.drop_index("ix_historical_relation_type_year", table_name="historical_course_relations")
    op.drop_index(
        "ix_historical_course_relations_dataset_id", table_name="historical_course_relations"
    )
    op.drop_table("historical_course_relations")
    op.drop_table("historical_relation_datasets")
    op.drop_index(
        "ix_historical_curriculum_department_name",
        table_name="historical_curriculum_departments",
    )
    op.drop_index(
        "ix_historical_curriculum_departments_dataset_id",
        table_name="historical_curriculum_departments",
    )
    op.drop_table("historical_curriculum_departments")
    op.drop_index(
        "ix_historical_curriculum_datasets_academic_year",
        table_name="historical_curriculum_datasets",
    )
    op.drop_table("historical_curriculum_datasets")
    op.drop_index("ix_historical_offering_category", table_name="historical_course_offerings")
    op.drop_index("ix_historical_offering_name", table_name="historical_course_offerings")
    op.drop_index("ix_historical_offering_course", table_name="historical_course_offerings")
    op.drop_index("ix_historical_offering_term", table_name="historical_course_offerings")
    op.drop_index(
        "ix_historical_course_offerings_dataset_id",
        table_name="historical_course_offerings",
    )
    op.drop_table("historical_course_offerings")
    op.drop_index("ix_historical_term_year_code", table_name="historical_term_datasets")
    op.drop_table("historical_term_datasets")
    op.drop_table("historical_archive_manifests")
