"""Store normalized curriculum and graduation requirements.

Revision ID: 20260717_0006
Revises: 20260715_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0006"
down_revision: str | None = "20260715_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "requirement_datasets",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("admission_year", sa.Integer()),
        sa.Column("effective_year", sa.Integer()),
        sa.Column("as_of", sa.String(length=20)),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("normalized_checksum", sa.String(length=64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_requirement_datasets_kind_year",
        "requirement_datasets",
        ["kind", "admission_year", "effective_year"],
    )

    op.create_table(
        "curriculum_program_requirements",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=80), nullable=False),
        sa.Column("admission_year", sa.Integer(), nullable=False),
        sa.Column("academic_unit", sa.String(length=240), nullable=False),
        sa.Column("academic_unit_key", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_locators", sa.JSON(), nullable=False),
        sa.Column("source_course_count", sa.Integer(), nullable=False),
        sa.Column("required_course_count", sa.Integer(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["requirement_datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "dataset_id", "academic_unit_key", name="uq_curriculum_program_requirement"
        ),
    )
    op.create_index(
        "ix_curriculum_program_requirements_dataset_id",
        "curriculum_program_requirements",
        ["dataset_id"],
    )
    op.create_index(
        "ix_curriculum_program_requirements_year_unit",
        "curriculum_program_requirements",
        ["admission_year", "academic_unit_key"],
    )

    op.create_table(
        "curriculum_program_aliases",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("program_id", sa.String(length=36), nullable=False),
        sa.Column("admission_year", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=240), nullable=False),
        sa.Column("alias_key", sa.String(length=240), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"], ["curriculum_program_requirements.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "admission_year", "alias_key", "program_id", name="uq_curriculum_program_alias"
        ),
    )
    op.create_index(
        "ix_curriculum_program_aliases_program_id",
        "curriculum_program_aliases",
        ["program_id"],
    )
    op.create_index(
        "ix_curriculum_program_aliases_year_key",
        "curriculum_program_aliases",
        ["admission_year", "alias_key"],
    )

    op.create_table(
        "curriculum_required_courses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("program_id", sa.String(length=36), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=False),
        sa.Column("course_name", sa.String(length=240), nullable=False),
        sa.Column("credits", sa.Float()),
        sa.Column("grade", sa.Integer()),
        sa.Column("semesters", sa.JSON(), nullable=False),
        sa.Column("source_locator", sa.JSON(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"], ["curriculum_program_requirements.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "program_id",
            "classification",
            "course_code",
            name="uq_curriculum_required_course",
        ),
    )
    op.create_index(
        "ix_curriculum_required_courses_program_id",
        "curriculum_required_courses",
        ["program_id"],
    )
    op.create_index(
        "ix_curriculum_required_courses_program",
        "curriculum_required_courses",
        ["program_id", "classification"],
    )
    op.create_index(
        "ix_curriculum_required_courses_code",
        "curriculum_required_courses",
        ["course_code"],
    )

    op.create_table(
        "graduation_requirement_rules",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("dataset_id", sa.String(length=80), nullable=False),
        sa.Column("rule_kind", sa.String(length=80), nullable=False),
        sa.Column("category_code", sa.String(length=40)),
        sa.Column("academic_unit", sa.String(length=240)),
        sa.Column("academic_unit_key", sa.String(length=240)),
        sa.Column("admission_year_start", sa.Integer()),
        sa.Column("admission_year_end", sa.Integer()),
        sa.Column("effective_year", sa.Integer()),
        sa.Column("student_type", sa.String(length=40)),
        sa.Column("program_path", sa.String(length=40)),
        sa.Column("description", sa.Text()),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["requirement_datasets.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_graduation_requirement_rules_dataset_id",
        "graduation_requirement_rules",
        ["dataset_id"],
    )
    op.create_index(
        "ix_graduation_requirement_rules_dataset",
        "graduation_requirement_rules",
        ["dataset_id", "rule_kind"],
    )
    op.create_index(
        "ix_graduation_requirement_rules_lookup",
        "graduation_requirement_rules",
        ["academic_unit_key", "admission_year_start", "admission_year_end", "effective_year"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_graduation_requirement_rules_lookup", table_name="graduation_requirement_rules"
    )
    op.drop_index(
        "ix_graduation_requirement_rules_dataset", table_name="graduation_requirement_rules"
    )
    op.drop_index(
        "ix_graduation_requirement_rules_dataset_id", table_name="graduation_requirement_rules"
    )
    op.drop_table("graduation_requirement_rules")
    op.drop_index("ix_curriculum_required_courses_code", table_name="curriculum_required_courses")
    op.drop_index(
        "ix_curriculum_required_courses_program", table_name="curriculum_required_courses"
    )
    op.drop_index(
        "ix_curriculum_required_courses_program_id", table_name="curriculum_required_courses"
    )
    op.drop_table("curriculum_required_courses")
    op.drop_index("ix_curriculum_program_aliases_year_key", table_name="curriculum_program_aliases")
    op.drop_index(
        "ix_curriculum_program_aliases_program_id", table_name="curriculum_program_aliases"
    )
    op.drop_table("curriculum_program_aliases")
    op.drop_index(
        "ix_curriculum_program_requirements_year_unit",
        table_name="curriculum_program_requirements",
    )
    op.drop_index(
        "ix_curriculum_program_requirements_dataset_id",
        table_name="curriculum_program_requirements",
    )
    op.drop_table("curriculum_program_requirements")
    op.drop_index("ix_requirement_datasets_kind_year", table_name="requirement_datasets")
    op.drop_table("requirement_datasets")
