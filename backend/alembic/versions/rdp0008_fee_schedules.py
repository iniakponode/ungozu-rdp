"""Introduce configurable fee-plan instalment schedules.

Revision ID: rdp0008_fee_schedules
Revises: rdp0007_fee_plan_packages
"""

from alembic import op
import sqlalchemy as sa


revision = "rdp0008_fee_schedules"
down_revision = "rdp0007_fee_plan_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rdp_fee_plan_installments",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "fee_plan_id",
            sa.Integer(),
            sa.ForeignKey(
                "rdp_fee_plans.id",
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
            "amount_subunit",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "due_offset_days",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "description",
            sa.String(255),
            nullable=True,
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
            "fee_plan_id",
            "sequence_number",
            name="uq_rdp_fee_plan_installment_sequence",
        ),

        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_rdp_installment_sequence_positive",
        ),

        sa.CheckConstraint(
            "amount_subunit >= 0",
            name="ck_rdp_installment_amount_nonnegative",
        ),

        sa.CheckConstraint(
            "due_offset_days >= 0",
            name="ck_rdp_installment_due_offset_nonnegative",
        ),
    )

    op.create_index(
        "ix_rdp_fee_plan_installments_fee_plan_id",
        "rdp_fee_plan_installments",
        ["fee_plan_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rdp_fee_plan_installments_fee_plan_id",
        table_name="rdp_fee_plan_installments",
    )

    op.drop_table(
        "rdp_fee_plan_installments"
    )
