"""Introduce configurable RDP programmes and programme versions.

Revision ID: rdp0003_programme_builder
Revises: rdp0002_payments
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rdp0003_programme_builder"
down_revision: Union[str, Sequence[str], None] = "rdp0002_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reusable programme definitions
    op.create_table(
        "rdp_programmes",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "is_published", sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
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
    )

    op.create_index(
        "ix_rdp_programmes_slug",
        "rdp_programmes",
        ["slug"],
        unique=True,
    )

    # Versioned programme structures
    op.create_table(
        "rdp_programme_versions",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "programme_id",
            sa.Integer(),
            sa.ForeignKey(
                "rdp_programmes.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "version_number", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "title", sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "overview", sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "duration_value", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "duration_unit", sa.String(20),
            nullable=False,
            server_default="months",
        ),
        sa.Column(
            "learning_outcomes", sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "published_at", sa.DateTime(),
            nullable=True,
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
            "programme_id",
            "version_number",
            name="uq_rdp_programme_version",
        ),
    )

    op.create_index(
        "ix_rdp_programme_versions_programme_id",
        "rdp_programme_versions",
        ["programme_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rdp_programme_versions_programme_id",
        table_name="rdp_programme_versions",
    )
    op.drop_table("rdp_programme_versions")

    op.drop_index(
        "ix_rdp_programmes_slug",
        table_name="rdp_programmes",
    )
    op.drop_table("rdp_programmes")
