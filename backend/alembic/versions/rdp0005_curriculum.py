"""Introduce configurable curriculum modules and items.

Revision ID: rdp0005_curriculum
Revises: rdp0004_cohort_version
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rdp0005_curriculum"
down_revision: Union[str, Sequence[str], None] = (
    "rdp0004_cohort_version"
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rdp_curriculum_modules",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "programme_version_id",
            sa.Integer(),
            sa.ForeignKey(
                "rdp_programme_versions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "learning_outcomes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "completion_criteria",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "programme_version_id",
            "sequence_number",
            name="uq_rdp_curriculum_module_sequence",
        ),
    )

    op.create_index(
        "ix_rdp_curriculum_modules_programme_version_id",
        "rdp_curriculum_modules",
        ["programme_version_id"],
    )

    op.create_table(
        "rdp_curriculum_items",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "module_id",
            sa.Integer(),
            sa.ForeignKey(
                "rdp_curriculum_modules.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "sequence_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "item_type",
            sa.String(50),
            nullable=False,
            server_default="lesson",
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "instructions",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "estimated_minutes",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "completion_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "module_id",
            "sequence_number",
            name="uq_rdp_curriculum_item_sequence",
        ),
    )

    op.create_index(
        "ix_rdp_curriculum_items_module_id",
        "rdp_curriculum_items",
        ["module_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rdp_curriculum_items_module_id",
        table_name="rdp_curriculum_items",
    )
    op.drop_table("rdp_curriculum_items")

    op.drop_index(
        "ix_rdp_curriculum_modules_programme_version_id",
        table_name="rdp_curriculum_modules",
    )
    op.drop_table("rdp_curriculum_modules")
