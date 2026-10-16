"""Introduce optional cohort-level limits for RDP packages.

Revision ID: rdp0012_package_capacity
Revises: rdp0011_fee_quote_expiry_guard

NULL capacity means no additional package-specific limit.
The parent cohort capacity always remains applicable.
"""

from alembic import op
import sqlalchemy as sa


revision = "rdp0012_package_capacity"
down_revision = "rdp0011_fee_quote_expiry_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rdp_packages",
        sa.Column(
            "capacity",
            sa.SmallInteger(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_rdp_packages_capacity_positive",
        "rdp_packages",
        "capacity IS NULL OR capacity > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_rdp_packages_capacity_positive",
        "rdp_packages",
        type_="check",
    )

    op.drop_column(
        "rdp_packages",
        "capacity",
    )
