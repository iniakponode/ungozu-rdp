"""Link cohorts to configurable programme versions.

Revision ID: rdp0004_cohort_version
Revises: rdp0003_programme_builder
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rdp0004_cohort_version"
down_revision: Union[str, Sequence[str], None] = (
    "rdp0003_programme_builder"
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rdp_cohorts",
        sa.Column(
            "programme_version_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_rdp_cohorts_programme_version_id",
        "rdp_cohorts",
        ["programme_version_id"],
    )

    op.create_foreign_key(
        "fk_rdp_cohorts_programme_version_id",
        "rdp_cohorts",
        "rdp_programme_versions",
        ["programme_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_rdp_cohorts_programme_version_id",
        "rdp_cohorts",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_rdp_cohorts_programme_version_id",
        table_name="rdp_cohorts",
    )

    op.drop_column(
        "rdp_cohorts",
        "programme_version_id",
    )
