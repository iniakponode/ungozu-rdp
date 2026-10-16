"""Link existing fee plans to configurable programme packages.

Revision ID: rdp0007_fee_plan_packages
Revises: rdp0006_packages
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rdp0007_fee_plan_packages"
down_revision: Union[str, Sequence[str], None] = "rdp0006_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rdp_fee_plans",
        sa.Column(
            "package_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_rdp_fee_plans_package_id",
        "rdp_fee_plans",
        ["package_id"],
    )

    op.create_foreign_key(
        "fk_rdp_fee_plans_package_id",
        "rdp_fee_plans",
        "rdp_packages",
        ["package_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_rdp_fee_plans_package_id",
        "rdp_fee_plans",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_rdp_fee_plans_package_id",
        table_name="rdp_fee_plans",
    )

    op.drop_column(
        "rdp_fee_plans",
        "package_id",
    )
