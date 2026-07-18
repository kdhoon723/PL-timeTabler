"""Normalize graduation requirements into typed relations.

Revision ID: 20260718_0007
Revises: 20260717_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260718_0007"
down_revision: str | None = "20260717_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graduation_assessment_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), nullable=False),
        sa.Column("source_rule_id", sa.String(length=160), nullable=False),
        sa.Column("effective_year", sa.Integer(), nullable=False),
        sa.Column("academic_unit", sa.String(length=240), nullable=False),
        sa.Column("academic_unit_key", sa.String(length=240), nullable=False),
        sa.Column("transition_mode", sa.String(length=40), nullable=False),
        sa.Column("transition_source_text", sa.Text(), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "transition_mode IN ('STANDARDIZED_ONLY', 'LEGACY_OR_STANDARDIZED', 'LEGACY_ONLY')",
            name="ck_graduation_assessment_transition_mode",
        ),
        sa.CheckConstraint(
            "effective_year BETWEEN 1900 AND 2100", name="ck_graduation_assessment_effective_year"
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["requirement_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "academic_unit_key",
            "effective_year",
            name="uq_graduation_assessment_profile_scope",
        ),
        sa.UniqueConstraint(
            "dataset_id", "source_rule_id", name="uq_graduation_assessment_profile_source_rule"
        ),
    )
    op.create_index(
        "ix_graduation_assessment_profile_lookup",
        "graduation_assessment_profiles",
        ["academic_unit_key", "effective_year"],
        unique=False,
    )
    op.create_table(
        "graduation_legacy_requirements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), nullable=False),
        sa.Column("source_rule_id", sa.String(length=160), nullable=False),
        sa.Column("effective_year", sa.Integer(), nullable=False),
        sa.Column("academic_unit", sa.String(length=240), nullable=False),
        sa.Column("academic_unit_key", sa.String(length=240), nullable=False),
        sa.Column("eligibility_requirement", sa.Text(), nullable=True),
        sa.Column("form_thesis", sa.Boolean(), nullable=False),
        sa.Column("form_report", sa.Boolean(), nullable=False),
        sa.Column("form_practical_or_artwork", sa.Boolean(), nullable=False),
        sa.Column("form_exam", sa.Boolean(), nullable=False),
        sa.Column("substitute_international_certification", sa.Text(), nullable=True),
        sa.Column("substitute_national_technical_certification", sa.Text(), nullable=True),
        sa.Column("substitute_national_professional_certification", sa.Text(), nullable=True),
        sa.Column("substitute_national_accredited_private_certification", sa.Text(), nullable=True),
        sa.Column("substitute_private_certification", sa.Text(), nullable=True),
        sa.Column("substitute_other", sa.Text(), nullable=True),
        sa.Column("pass_requirement", sa.Text(), nullable=True),
        sa.Column("double_major_pass_requirement", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "effective_year BETWEEN 1900 AND 2100", name="ck_graduation_legacy_effective_year"
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["requirement_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id", "source_rule_id", name="uq_graduation_legacy_requirement_source_rule"
        ),
    )
    op.create_index(
        "ix_graduation_legacy_requirement_lookup",
        "graduation_legacy_requirements",
        ["academic_unit_key", "effective_year"],
        unique=False,
    )
    op.create_table(
        "graduation_liberal_requirement_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), nullable=False),
        sa.Column("signature", sa.String(length=64), nullable=False),
        sa.Column("admission_year", sa.Integer(), nullable=False),
        sa.Column("student_type", sa.String(length=40), nullable=False),
        sa.Column("required_credits_min", sa.Integer(), nullable=False),
        sa.Column("elective_credits_min", sa.Integer(), nullable=False),
        sa.Column("total_credits_min", sa.Integer(), nullable=False),
        sa.Column("total_credits_max", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "admission_year BETWEEN 1900 AND 2100", name="ck_graduation_liberal_set_admission_year"
        ),
        sa.CheckConstraint(
            "required_credits_min >= 0 AND elective_credits_min >= 0 "
            "AND total_credits_min >= 0 AND "
            "(total_credits_max IS NULL OR total_credits_max >= total_credits_min)",
            name="ck_graduation_liberal_set_credits",
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["requirement_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id", "signature", name="uq_graduation_liberal_requirement_set_signature"
        ),
    )
    op.create_index(
        "ix_graduation_liberal_sets_year_type",
        "graduation_liberal_requirement_sets",
        ["admission_year", "student_type"],
        unique=False,
    )
    op.create_table(
        "graduation_assessment_source_refs",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_graduation_assessment_source_ref_position",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["graduation_assessment_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("profile_id", "position"),
        sa.UniqueConstraint("profile_id", "source_ref", name="uq_graduation_assessment_source_ref"),
    )
    op.create_table(
        "graduation_legacy_source_refs",
        sa.Column("legacy_requirement_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_graduation_legacy_source_ref_position",
        ),
        sa.ForeignKeyConstraint(
            ["legacy_requirement_id"],
            ["graduation_legacy_requirements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("legacy_requirement_id", "position"),
        sa.UniqueConstraint(
            "legacy_requirement_id",
            "source_ref",
            name="uq_graduation_legacy_source_ref",
        ),
    )
    op.create_table(
        "graduation_assessment_categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("category_code", sa.String(length=1), nullable=False),
        sa.Column("category_name", sa.String(length=240), nullable=False),
        sa.Column("primary_none", sa.Text(), nullable=True),
        sa.Column("primary_one", sa.Text(), nullable=True),
        sa.Column("primary_two", sa.Text(), nullable=True),
        sa.Column("double_major_none", sa.Text(), nullable=True),
        sa.Column("double_major_one", sa.Text(), nullable=True),
        sa.Column("requirement_detail", sa.Text(), nullable=True),
        sa.Column("reference_note", sa.Text(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "category_code IN ('A', 'C', 'E', 'S')", name="ck_graduation_assessment_category_code"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["graduation_assessment_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id", "category_code", name="uq_graduation_assessment_category"
        ),
    )
    op.create_table(
        "graduation_assessment_credentials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("international_or_national_certification", sa.Text(), nullable=True),
        sa.Column("private_or_other_certification", sa.Text(), nullable=True),
        sa.Column("foreign_language", sa.Text(), nullable=True),
        sa.Column("awards", sa.Text(), nullable=True),
        sa.Column("employment_or_experience", sa.Text(), nullable=True),
        sa.Column("double_major_requirement", sa.Text(), nullable=True),
        sa.Column("reference_note", sa.Text(), nullable=True),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.CheckConstraint("position >= 0", name="ck_graduation_assessment_credential_position"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["graduation_assessment_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id", "position", name="uq_graduation_assessment_credential_position"
        ),
    )
    op.create_table(
        "graduation_credit_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=80), nullable=False),
        sa.Column("source_rule_id", sa.String(length=160), nullable=False),
        sa.Column("liberal_requirement_set_id", sa.String(length=36), nullable=False),
        sa.Column("academic_unit", sa.String(length=240), nullable=False),
        sa.Column("academic_unit_key", sa.String(length=240), nullable=False),
        sa.Column("admission_year", sa.Integer(), nullable=False),
        sa.Column("student_type", sa.String(length=40), nullable=False),
        sa.Column("program_path", sa.String(length=40), nullable=False),
        sa.Column("total_credits_min", sa.Integer(), nullable=False),
        sa.Column("major_foundation_min", sa.Integer(), nullable=False),
        sa.Column("major_required_min", sa.Integer(), nullable=False),
        sa.Column("major_elective_min", sa.Integer(), nullable=False),
        sa.Column("additional_major_min", sa.Integer(), nullable=True),
        sa.Column("primary_major_min", sa.Integer(), nullable=False),
        sa.Column("secondary_program_min", sa.Integer(), nullable=True),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "program_path IN ('ADVANCED_MAJOR', 'DOUBLE_MAJOR', 'MINOR', 'MICRO_MAJOR')",
            name="ck_graduation_credit_profile_path",
        ),
        sa.CheckConstraint(
            "admission_year BETWEEN 1900 AND 2100",
            name="ck_graduation_credit_profile_admission_year",
        ),
        sa.CheckConstraint(
            "total_credits_min >= 0 AND major_foundation_min >= 0 "
            "AND major_required_min >= 0 AND major_elective_min >= 0 "
            "AND (additional_major_min IS NULL OR additional_major_min >= 0) "
            "AND primary_major_min >= 0 "
            "AND (secondary_program_min IS NULL OR secondary_program_min >= 0)",
            name="ck_graduation_credit_profile_credits",
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["requirement_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["liberal_requirement_set_id"],
            ["graduation_liberal_requirement_sets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "academic_unit_key",
            "admission_year",
            "student_type",
            "program_path",
            name="uq_graduation_credit_profile_scope",
        ),
        sa.UniqueConstraint(
            "dataset_id", "source_rule_id", name="uq_graduation_credit_profile_source_rule"
        ),
    )
    op.create_index(
        "ix_graduation_credit_profile_lookup",
        "graduation_credit_profiles",
        ["academic_unit_key", "admission_year", "student_type", "program_path"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graduation_credit_profiles_liberal_requirement_set_id"),
        "graduation_credit_profiles",
        ["liberal_requirement_set_id"],
        unique=False,
    )
    op.create_table(
        "graduation_credit_profile_academic_unit_aliases",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=240), nullable=False),
        sa.Column("alias_key", sa.String(length=240), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_graduation_credit_profile_academic_unit_alias_position",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["graduation_credit_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("profile_id", "position"),
        sa.UniqueConstraint(
            "profile_id",
            "alias_key",
            name="uq_graduation_credit_profile_academic_unit_alias",
        ),
    )
    op.create_table(
        "graduation_credit_profile_source_refs",
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_ref", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "position >= 0",
            name="ck_graduation_credit_profile_source_ref_position",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["graduation_credit_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("profile_id", "position"),
        sa.UniqueConstraint(
            "profile_id", "source_ref", name="uq_graduation_credit_profile_source_ref"
        ),
    )
    op.create_table(
        "graduation_legacy_cohorts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("legacy_requirement_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("expression", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "start_year IS NULL OR end_year IS NULL OR start_year <= end_year",
            name="ck_graduation_legacy_cohort_range",
        ),
        sa.CheckConstraint("position >= 0", name="ck_graduation_legacy_cohort_position"),
        sa.ForeignKeyConstraint(
            ["legacy_requirement_id"], ["graduation_legacy_requirements.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legacy_requirement_id", "expression", name="uq_graduation_legacy_cohort_expression"
        ),
        sa.UniqueConstraint(
            "legacy_requirement_id", "position", name="uq_graduation_legacy_cohort_position"
        ),
    )
    op.create_table(
        "graduation_liberal_area_requirements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requirement_set_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(length=160), nullable=False),
        sa.Column("min_courses", sa.Integer(), nullable=False),
        sa.Column("min_credits", sa.Integer(), nullable=True),
        sa.CheckConstraint("min_courses >= 0", name="ck_graduation_liberal_area_courses"),
        sa.CheckConstraint(
            "min_credits IS NULL OR min_credits >= 0", name="ck_graduation_liberal_area_credits"
        ),
        sa.CheckConstraint("position >= 0", name="ck_graduation_liberal_area_position"),
        sa.ForeignKeyConstraint(
            ["requirement_set_id"], ["graduation_liberal_requirement_sets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_set_id", "area", name="uq_graduation_liberal_area"),
        sa.UniqueConstraint(
            "requirement_set_id", "position", name="uq_graduation_liberal_area_position"
        ),
    )
    op.create_table(
        "graduation_liberal_required_courses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requirement_set_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.String(length=40), nullable=True),
        sa.Column("course_name", sa.String(length=240), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.CheckConstraint("credits > 0", name="ck_graduation_liberal_course_credits"),
        sa.CheckConstraint(
            "grade IS NULL OR grade BETWEEN 1 AND 6", name="ck_graduation_liberal_course_grade"
        ),
        sa.CheckConstraint("position >= 0", name="ck_graduation_liberal_course_position"),
        sa.ForeignKeyConstraint(
            ["requirement_set_id"], ["graduation_liberal_requirement_sets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requirement_set_id", "course_code", name="uq_graduation_liberal_course_code"
        ),
        sa.UniqueConstraint(
            "requirement_set_id", "position", name="uq_graduation_liberal_course_position"
        ),
    )
    op.create_table(
        "graduation_credit_profile_warnings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("calculated", sa.Integer(), nullable=False),
        sa.Column("printed", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "calculated >= 0 AND printed >= 0", name="ck_graduation_credit_profile_warning_values"
        ),
        sa.CheckConstraint("position >= 0", name="ck_graduation_credit_profile_warning_position"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["graduation_credit_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "code", name="uq_graduation_credit_profile_warning"),
        sa.UniqueConstraint(
            "profile_id", "position", name="uq_graduation_credit_profile_warning_position"
        ),
    )
    op.create_table(
        "graduation_liberal_course_aliases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=240), nullable=False),
        sa.Column("alias_key", sa.String(length=240), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_graduation_liberal_course_alias_position"),
        sa.ForeignKeyConstraint(
            ["course_id"], ["graduation_liberal_required_courses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "alias_key", name="uq_graduation_liberal_course_alias"),
        sa.UniqueConstraint(
            "course_id", "position", name="uq_graduation_liberal_course_alias_position"
        ),
    )
    op.create_table(
        "graduation_liberal_course_terms",
        sa.Column("course_id", sa.String(length=36), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.CheckConstraint("semester IN (1, 2)", name="ck_graduation_liberal_course_term"),
        sa.ForeignKeyConstraint(
            ["course_id"], ["graduation_liberal_required_courses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("course_id", "semester"),
    )
    op.drop_index(
        "ix_curriculum_program_requirements_dataset_id",
        table_name="curriculum_program_requirements",
    )
    op.drop_index(
        "ix_curriculum_required_courses_program_id",
        table_name="curriculum_required_courses",
    )
    op.drop_index(
        "ix_graduation_requirement_rules_dataset_id",
        table_name="graduation_requirement_rules",
    )
    op.create_check_constraint(
        "ck_requirement_datasets_record_count",
        "requirement_datasets",
        "record_count >= 0",
    )
    op.create_check_constraint(
        "ck_requirement_datasets_admission_year",
        "requirement_datasets",
        "admission_year IS NULL OR admission_year BETWEEN 1900 AND 2100",
    )
    op.create_check_constraint(
        "ck_requirement_datasets_effective_year",
        "requirement_datasets",
        "effective_year IS NULL OR effective_year BETWEEN 1900 AND 2100",
    )
    op.create_check_constraint(
        "ck_curriculum_program_admission_year",
        "curriculum_program_requirements",
        "admission_year BETWEEN 1900 AND 2100",
    )
    op.create_check_constraint(
        "ck_curriculum_program_course_counts",
        "curriculum_program_requirements",
        "source_course_count >= 0 AND required_course_count >= 0",
    )
    op.create_check_constraint(
        "ck_curriculum_required_course_classification",
        "curriculum_required_courses",
        "classification IN ('전기', '전필')",
    )
    op.create_check_constraint(
        "ck_required_course_credits",
        "curriculum_required_courses",
        "credits IS NULL OR credits >= 0",
    )
    op.create_check_constraint(
        "ck_required_course_grade",
        "curriculum_required_courses",
        "grade IS NULL OR grade BETWEEN 1 AND 6",
    )
    op.create_check_constraint(
        "ck_graduation_rule_admission_year_range",
        "graduation_requirement_rules",
        "admission_year_start IS NULL OR admission_year_end IS NULL "
        "OR admission_year_start <= admission_year_end",
    )
    op.alter_column(
        "requirement_datasets",
        "as_of",
        existing_type=sa.String(length=20),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="as_of::date",
    )


def downgrade() -> None:
    op.alter_column(
        "requirement_datasets",
        "as_of",
        existing_type=sa.Date(),
        type_=sa.String(length=20),
        existing_nullable=True,
        postgresql_using="as_of::text",
    )
    op.drop_constraint(
        "ck_graduation_rule_admission_year_range",
        "graduation_requirement_rules",
        type_="check",
    )
    op.drop_constraint("ck_required_course_grade", "curriculum_required_courses", type_="check")
    op.drop_constraint("ck_required_course_credits", "curriculum_required_courses", type_="check")
    op.drop_constraint(
        "ck_curriculum_required_course_classification",
        "curriculum_required_courses",
        type_="check",
    )
    op.drop_constraint(
        "ck_curriculum_program_course_counts",
        "curriculum_program_requirements",
        type_="check",
    )
    op.drop_constraint(
        "ck_curriculum_program_admission_year",
        "curriculum_program_requirements",
        type_="check",
    )
    op.drop_constraint(
        "ck_requirement_datasets_effective_year",
        "requirement_datasets",
        type_="check",
    )
    op.drop_constraint(
        "ck_requirement_datasets_admission_year",
        "requirement_datasets",
        type_="check",
    )
    op.drop_constraint(
        "ck_requirement_datasets_record_count",
        "requirement_datasets",
        type_="check",
    )
    op.create_index(
        "ix_graduation_requirement_rules_dataset_id",
        "graduation_requirement_rules",
        ["dataset_id"],
    )
    op.create_index(
        "ix_curriculum_required_courses_program_id",
        "curriculum_required_courses",
        ["program_id"],
    )
    op.create_index(
        "ix_curriculum_program_requirements_dataset_id",
        "curriculum_program_requirements",
        ["dataset_id"],
    )
    op.drop_table("graduation_liberal_course_terms")
    op.drop_table("graduation_liberal_course_aliases")
    op.drop_table("graduation_credit_profile_warnings")
    op.drop_table("graduation_liberal_required_courses")
    op.drop_table("graduation_liberal_area_requirements")
    op.drop_table("graduation_legacy_cohorts")
    op.drop_table("graduation_credit_profile_source_refs")
    op.drop_table("graduation_credit_profile_academic_unit_aliases")
    op.drop_index(
        "ix_graduation_credit_profiles_liberal_requirement_set_id",
        table_name="graduation_credit_profiles",
    )
    op.drop_index(
        "ix_graduation_credit_profile_lookup",
        table_name="graduation_credit_profiles",
    )
    op.drop_table("graduation_credit_profiles")
    op.drop_table("graduation_assessment_credentials")
    op.drop_table("graduation_assessment_categories")
    op.drop_table("graduation_legacy_source_refs")
    op.drop_table("graduation_assessment_source_refs")
    op.drop_index(
        "ix_graduation_liberal_sets_year_type",
        table_name="graduation_liberal_requirement_sets",
    )
    op.drop_table("graduation_liberal_requirement_sets")
    op.drop_index(
        "ix_graduation_legacy_requirement_lookup",
        table_name="graduation_legacy_requirements",
    )
    op.drop_table("graduation_legacy_requirements")
    op.drop_index(
        "ix_graduation_assessment_profile_lookup",
        table_name="graduation_assessment_profiles",
    )
    op.drop_table("graduation_assessment_profiles")
