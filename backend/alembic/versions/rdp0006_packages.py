"""Introduce configurable programme packages and entitlements.

Revision ID: rdp0006_packages
Revises: rdp0005_curriculum
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rdp0006_packages"
down_revision: Union[str, Sequence[str], None] = "rdp0005_curriculum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Programme-specific packages
    op.create_table(
        "rdp_packages",
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
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "sort_order", sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "programme_version_id",
            "code",
            name="uq_rdp_package_version_code",
        ),
    )

    op.create_index(
        "ix_rdp_packages_programme_version_id",
        "rdp_packages",
        ["programme_version_id"],
    )

    # Package benefits and usage limits
    op.create_table(
        "rdp_package_entitlements",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "package_id",
            sa.Integer(),
            sa.ForeignKey(
                "rdp_packages.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit", sa.String(80), nullable=True),
        sa.Column("limit_value", sa.Integer(), nullable=True),
        sa.Column("limit_unit", sa.String(80), nullable=True),
        sa.Column("period", sa.String(40), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_included", sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "sort_order", sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at", sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "package_id",
            "code",
            name="uq_rdp_package_entitlement_code",
        ),
    )

    op.create_index(
        "ix_rdp_package_entitlements_package_id",
        "rdp_package_entitlements",
        ["package_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rdp_package_entitlements_package_id",
        table_name="rdp_package_entitlements",
    )
    op.drop_table("rdp_package_entitlements")

    op.drop_index(
        "ix_rdp_packages_programme_version_id",
        table_name="rdp_packages",
    )
    op.drop_table("rdp_packages")
