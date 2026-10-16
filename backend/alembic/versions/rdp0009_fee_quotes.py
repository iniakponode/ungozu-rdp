"""Introduce versioned fee quotes and agreed instalment terms.

Revision ID: rdp0009_fee_quotes
Revises: rdp0008_fee_schedules
"""

from alembic import op
import sqlalchemy as sa


revision = "rdp0009_fee_quotes"
down_revision = "rdp0008_fee_schedules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rdp_fee_quotes",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True, autoincrement=True,
        ),
        sa.Column(
            "application_id", sa.Integer(),
            sa.ForeignKey(
                "rdp_applications.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "fee_plan_id", sa.Integer(),
            sa.ForeignKey(
                "rdp_fee_plans.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "package_id", sa.Integer(),
            sa.ForeignKey(
                "rdp_packages.id",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
        sa.Column(
            "quote_number", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "package_name_snapshot",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "entitlements_snapshot_json",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "currency", sa.String(3),
            nullable=False,
        ),
        sa.Column(
            "gross_total_subunit", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "scholarship_subunit", sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "payable_total_subunit", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status", sa.String(30),
            nullable=False,
            server_default="offered",
        ),
        sa.Column(
            "effective_date", sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "expires_at", sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "accepted_at", sa.DateTime(),
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
            "application_id",
            "quote_number",
            name="uq_rdp_fee_quote_application_number",
        ),
        sa.CheckConstraint(
            "gross_total_subunit >= 0",
            name="ck_rdp_quote_gross_nonnegative",
        ),
        sa.CheckConstraint(
            "scholarship_subunit >= 0",
            name="ck_rdp_quote_scholarship_nonnegative",
        ),
        sa.CheckConstraint(
            "payable_total_subunit = "
            "gross_total_subunit - scholarship_subunit",
            name="ck_rdp_quote_total_consistent",
        ),
    )

    op.create_index(
        "ix_rdp_fee_quotes_application_id",
        "rdp_fee_quotes",
        ["application_id"],
    )

    op.create_table(
        "rdp_fee_quote_installments",
        sa.Column(
            "id", sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "fee_quote_id", sa.Integer(),
            sa.ForeignKey(
                "rdp_fee_quotes.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "sequence_number", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "amount_subunit", sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "due_date", sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "description", sa.String(255),
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
            "fee_quote_id",
            "sequence_number",
            name="uq_rdp_fee_quote_installment_sequence",
        ),
        sa.CheckConstraint(
            "sequence_number >= 1",
            name="ck_rdp_quote_line_sequence_positive",
        ),
        sa.CheckConstraint(
            "amount_subunit >= 0",
            name="ck_rdp_quote_line_amount_nonnegative",
        ),
    )

    op.create_index(
        "ix_rdp_fee_quote_installments_fee_quote_id",
        "rdp_fee_quote_installments",
        ["fee_quote_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rdp_fee_quote_installments_fee_quote_id",
        table_name="rdp_fee_quote_installments",
    )
    op.drop_table("rdp_fee_quote_installments")

    op.drop_index(
        "ix_rdp_fee_quotes_application_id",
        table_name="rdp_fee_quotes",
    )
    op.drop_table("rdp_fee_quotes")
