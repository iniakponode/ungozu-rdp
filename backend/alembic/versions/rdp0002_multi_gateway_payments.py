"""phase27 multi gateway payments

Revision ID: rdp0002_payments
Revises: rdp0001_initial
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "rdp0002_payments"
down_revision: Union[str, Sequence[str], None] = "rdp0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rdp_payments",
        sa.Column("environment", sa.String(10), nullable=False, server_default="test"),
    )
    op.add_column(
        "rdp_payments",
        sa.Column("provider_session_id", sa.String(255), nullable=True),
    )
    op.alter_column(
        "rdp_payments",
        "provider_id",
        existing_type=sa.String(80),
        type_=sa.String(255),
        existing_nullable=True,
    )

    op.create_table(
        "rdp_payment_platform_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active_environment", sa.String(10), nullable=False, server_default="test"),
        sa.Column("allow_provider_selection", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "rdp_payment_provider_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("environment", sa.String(10), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("public_key", sa.String(255), nullable=True),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("supported_currencies_json", sa.Text(), nullable=False),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="100"),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_status", sa.String(30), nullable=True),
        sa.Column("last_test_message", sa.String(500), nullable=True),
        sa.Column("configured_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "environment", name="uq_rdp_payment_provider_environment"),
    )
    op.create_index("ix_rdp_payment_provider_configs_provider", "rdp_payment_provider_configs", ["provider"])
    op.create_index("ix_rdp_payment_provider_configs_environment", "rdp_payment_provider_configs", ["environment"])

    op.create_table(
        "rdp_payment_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(40), nullable=True),
        sa.Column("environment", sa.String(10), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rdp_payment_audit_logs_admin_user_id", "rdp_payment_audit_logs", ["admin_user_id"])
    op.create_index("ix_rdp_payment_audit_logs_action", "rdp_payment_audit_logs", ["action"])
    op.create_index("ix_rdp_payment_audit_logs_created_at", "rdp_payment_audit_logs", ["created_at"])

    op.create_table(
        "rdp_payment_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("environment", sa.String(10), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=True),
        sa.Column("event_type", sa.String(120), nullable=True),
        sa.Column("payment_reference", sa.String(100), nullable=True),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="received"),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dedupe_key", name="uq_rdp_payment_webhook_dedupe"),
    )
    op.create_index("ix_rdp_payment_webhook_events_provider", "rdp_payment_webhook_events", ["provider"])
    op.create_index("ix_rdp_payment_webhook_events_environment", "rdp_payment_webhook_events", ["environment"])
    op.create_index("ix_rdp_payment_webhook_events_payment_reference", "rdp_payment_webhook_events", ["payment_reference"])
    op.create_index("ix_rdp_payment_webhook_events_created_at", "rdp_payment_webhook_events", ["created_at"])

    settings_table = sa.table(
        "rdp_payment_platform_settings",
        sa.column("id", sa.Integer),
        sa.column("active_environment", sa.String),
        sa.column("allow_provider_selection", sa.Boolean),
    )
    op.bulk_insert(settings_table, [{
        "id": 1,
        "active_environment": "test",
        "allow_provider_selection": True,
    }])


def downgrade() -> None:
    op.drop_table("rdp_payment_webhook_events")
    op.drop_table("rdp_payment_audit_logs")
    op.drop_table("rdp_payment_provider_configs")
    op.drop_table("rdp_payment_platform_settings")
    op.alter_column(
        "rdp_payments",
        "provider_id",
        existing_type=sa.String(255),
        type_=sa.String(80),
        existing_nullable=True,
    )
    op.drop_column("rdp_payments", "provider_session_id")
    op.drop_column("rdp_payments", "environment")
