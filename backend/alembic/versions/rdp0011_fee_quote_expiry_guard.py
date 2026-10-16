"""Prevent issuance or acceptance of expired fee quotations.

Revision ID: rdp0011_fee_quote_expiry_guard
Revises: rdp0010_fee_quote_immutability
"""

from alembic import op


revision = "rdp0011_fee_quote_expiry_guard"
down_revision = "rdp0010_fee_quote_immutability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TRIGGER trg_rdp_quote_expiry_bu
        BEFORE UPDATE ON rdp_fee_quotes
        FOR EACH ROW
        FOLLOWS trg_rdp_quote_bu
        BEGIN
            IF (
                (
                    OLD.status = 'draft'
                    AND NEW.status = 'offered'
                )
                OR
                (
                    OLD.status = 'offered'
                    AND NEW.status = 'accepted'
                )
            )
            AND NEW.expires_at IS NOT NULL
            AND NEW.expires_at <= UTC_TIMESTAMP()
            THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT =
                    'Expired quotation cannot be issued or accepted';
            END IF;
        END
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_rdp_quote_expiry_bu"
    )
