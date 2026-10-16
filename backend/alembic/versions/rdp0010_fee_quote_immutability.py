"""Protect issued RDP fee quotes and instalments using MariaDB triggers.

Revision ID: rdp0010_fee_quote_immutability
Revises: rdp0009_fee_quotes
"""

from alembic import op


revision = "rdp0010_fee_quote_immutability"
down_revision = "rdp0009_fee_quotes"
branch_labels = None
depends_on = None


TRIGGERS = {
    "trg_rdp_quote_bi": """
        CREATE TRIGGER trg_rdp_quote_bi
        BEFORE INSERT ON rdp_fee_quotes
        FOR EACH ROW
        BEGIN
            IF NEW.status <> 'draft'
               OR NEW.accepted_at IS NOT NULL THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'New quotations must begin as drafts';
            END IF;
        END
    """,

    "trg_rdp_quote_bu": """
        CREATE TRIGGER trg_rdp_quote_bu
        BEFORE UPDATE ON rdp_fee_quotes
        FOR EACH ROW
        BEGIN
            DECLARE v_count INT DEFAULT 0;
            DECLARE v_total BIGINT DEFAULT 0;
            DECLARE v_missing INT DEFAULT 0;
            DECLARE v_invalid INT DEFAULT 0;
            DECLARE v_min INT DEFAULT 0;
            DECLARE v_max INT DEFAULT 0;

            IF OLD.status <> 'draft' AND (
                NOT (NEW.id <=> OLD.id)
                OR NOT (NEW.application_id <=> OLD.application_id)
                OR NOT (NEW.fee_plan_id <=> OLD.fee_plan_id)
                OR NOT (NEW.package_id <=> OLD.package_id)
                OR NOT (NEW.quote_number <=> OLD.quote_number)
                OR NOT (BINARY NEW.package_name_snapshot
                        <=> BINARY OLD.package_name_snapshot)
                OR NOT (BINARY NEW.entitlements_snapshot_json
                        <=> BINARY OLD.entitlements_snapshot_json)
                OR NOT (BINARY NEW.currency
                        <=> BINARY OLD.currency)
                OR NOT (NEW.gross_total_subunit
                        <=> OLD.gross_total_subunit)
                OR NOT (NEW.scholarship_subunit
                        <=> OLD.scholarship_subunit)
                OR NOT (NEW.payable_total_subunit
                        <=> OLD.payable_total_subunit)
                OR NOT (NEW.effective_date <=> OLD.effective_date)
                OR NOT (NEW.expires_at <=> OLD.expires_at)
                OR NOT (NEW.created_at <=> OLD.created_at)
            ) THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Issued quotation terms are immutable';
            END IF;

            IF NEW.status <> OLD.status THEN
                IF NOT (
                    (OLD.status = 'draft'
                     AND NEW.status = 'offered')
                    OR
                    (OLD.status = 'offered'
                     AND NEW.status IN (
                         'accepted', 'expired', 'superseded'
                     ))
                ) THEN
                    SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = 'Invalid quotation status transition';
                END IF;
            END IF;

            IF NOT (NEW.accepted_at <=> OLD.accepted_at) THEN
                IF NOT (
                    OLD.status = 'offered'
                    AND NEW.status = 'accepted'
                    AND OLD.accepted_at IS NULL
                    AND NEW.accepted_at IS NOT NULL
                ) THEN
                    SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = 'Invalid acceptance timestamp change';
                END IF;
            END IF;

            IF NEW.status = 'accepted'
               AND NEW.accepted_at IS NULL THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Accepted quotation needs timestamp';
            END IF;

            IF OLD.status = 'draft'
               AND NEW.status = 'offered' THEN

                SELECT
                    COUNT(*),
                    COALESCE(SUM(amount_subunit), 0),
                    COALESCE(SUM(due_date IS NULL), 0),
                    COALESCE(SUM(amount_subunit <= 0), 0),
                    COALESCE(MIN(sequence_number), 0),
                    COALESCE(MAX(sequence_number), 0)
                INTO
                    v_count, v_total, v_missing,
                    v_invalid, v_min, v_max
                FROM rdp_fee_quote_installments
                WHERE fee_quote_id = OLD.id;

                IF NEW.scholarship_subunit > NEW.gross_total_subunit
                   OR NEW.payable_total_subunit < 0
                   OR v_total <> NEW.payable_total_subunit
                   OR v_missing > 0
                   OR v_invalid > 0
                   OR (
                       NEW.payable_total_subunit > 0
                       AND v_count = 0
                   )
                   OR (
                       NEW.payable_total_subunit = 0
                       AND v_count <> 0
                   )
                   OR (
                       v_count > 0
                       AND (v_min <> 1 OR v_max <> v_count)
                   )
                THEN
                    SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = 'Cannot issue inconsistent quote';
                END IF;
            END IF;
        END
    """,

    "trg_rdp_quote_bd": """
        CREATE TRIGGER trg_rdp_quote_bd
        BEFORE DELETE ON rdp_fee_quotes
        FOR EACH ROW
        BEGIN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Quotation deletion is prohibited';
        END
    """,

    "trg_rdp_quote_line_bi": """
        CREATE TRIGGER trg_rdp_quote_line_bi
        BEFORE INSERT ON rdp_fee_quote_installments
        FOR EACH ROW
        BEGIN
            DECLARE v_status VARCHAR(30);

            SELECT status INTO v_status
            FROM rdp_fee_quotes
            WHERE id = NEW.fee_quote_id
            FOR UPDATE;

            IF COALESCE(v_status, '') <> 'draft' THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Cannot add lines to issued quote';
            END IF;
        END
    """,

    "trg_rdp_quote_line_bu": """
        CREATE TRIGGER trg_rdp_quote_line_bu
        BEFORE UPDATE ON rdp_fee_quote_installments
        FOR EACH ROW
        BEGIN
            DECLARE v_status VARCHAR(30);

            SELECT status INTO v_status
            FROM rdp_fee_quotes
            WHERE id = OLD.fee_quote_id
            FOR UPDATE;

            IF COALESCE(v_status, '') <> 'draft'
               OR NOT (NEW.fee_quote_id <=> OLD.fee_quote_id) THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Cannot modify issued quote lines';
            END IF;
        END
    """,

    "trg_rdp_quote_line_bd": """
        CREATE TRIGGER trg_rdp_quote_line_bd
        BEFORE DELETE ON rdp_fee_quote_installments
        FOR EACH ROW
        BEGIN
            DECLARE v_status VARCHAR(30);

            SELECT status INTO v_status
            FROM rdp_fee_quotes
            WHERE id = OLD.fee_quote_id
            FOR UPDATE;

            IF COALESCE(v_status, '') <> 'draft' THEN
                SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Cannot delete issued quote lines';
            END IF;
        END
    """,
}


def upgrade() -> None:
    for sql in TRIGGERS.values():
        op.execute(sql)


def downgrade() -> None:
    for name in reversed(tuple(TRIGGERS)):
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
