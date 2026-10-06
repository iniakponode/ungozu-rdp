"""phase21 rdp operational platform

Revision ID: rdp0001_initial
Revises: None
Create Date: 2026-10-02
"""
from typing import Sequence, Union
from datetime import date

from alembic import op
import sqlalchemy as sa

revision: str = "rdp0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "rdp_cohorts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("application_open_date", sa.Date(), nullable=False),
        sa.Column("application_deadline", sa.Date(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("graduation_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("capacity", sa.SmallInteger(), nullable=False, server_default="10"),
        sa.Column("status", sa.String(50), nullable=False, server_default="applications_open"),
        sa.Column("public_summary", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_rdp_cohorts_slug", "rdp_cohorts", ["slug"])

    op.create_table(
        "rdp_fee_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("rdp_cohorts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("region", sa.String(80), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("total_amount_subunit", sa.Integer(), nullable=False),
        sa.Column("installment_count", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("installment_amount_subunit", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cohort_id", "code", name="uq_rdp_fee_plan_cohort_code"),
    )
    op.create_index("ix_rdp_fee_plans_cohort_id", "rdp_fee_plans", ["cohort_id"])

    op.create_table(
        "rdp_applications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("rdp_cohorts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("application_ref", sa.String(50), nullable=False),
        sa.Column("access_token_hash", sa.String(64), nullable=False),
        sa.Column("payment_token_hash", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("country", sa.String(120), nullable=False),
        sa.Column("institution", sa.String(255), nullable=False),
        sa.Column("career_stage", sa.String(120), nullable=False),
        sa.Column("discipline", sa.String(180), nullable=False),
        sa.Column("research_interests", sa.Text(), nullable=False),
        sa.Column("goals", sa.Text(), nullable=False),
        sa.Column("challenges", sa.Text(), nullable=False),
        sa.Column("current_outputs", sa.Text(), nullable=True),
        sa.Column("commitment", sa.Text(), nullable=False),
        sa.Column("scholarship_interest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("referral_source", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="submitted"),
        sa.Column("fee_plan_id", sa.Integer(), sa.ForeignKey("rdp_fee_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acceptance_deadline", sa.DateTime(), nullable=True),
        sa.Column("admission_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("application_ref"),
    )
    op.create_index("ix_rdp_applications_cohort_id", "rdp_applications", ["cohort_id"])
    op.create_index("ix_rdp_applications_application_ref", "rdp_applications", ["application_ref"])
    op.create_index("ix_rdp_applications_email", "rdp_applications", ["email"])
    op.create_index("ix_rdp_applications_status", "rdp_applications", ["status"])

    op.create_table(
        "rdp_application_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("rdp_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("motivation_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("development_need_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("programme_fit_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("commitment_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("potential_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("recommendation", sa.String(50), nullable=False, server_default="hold"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("application_id", "reviewer_id", name="uq_rdp_review_application_reviewer"),
    )
    op.create_index("ix_rdp_application_reviews_application_id", "rdp_application_reviews", ["application_id"])

    op.create_table(
        "rdp_scholarship_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("rdp_applications.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("support_type", sa.String(100), nullable=False),
        sa.Column("financial_need", sa.Text(), nullable=False),
        sa.Column("possible_contribution", sa.String(255), nullable=True),
        sa.Column("support_case", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="submitted"),
        sa.Column("approved_amount_subunit", sa.Integer(), nullable=True),
        sa.Column("approved_currency", sa.String(3), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rdp_scholarship_requests_status", "rdp_scholarship_requests", ["status"])

    op.create_table(
        "rdp_invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("rdp_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_plan_id", sa.Integer(), sa.ForeignKey("rdp_fee_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sequence", sa.SmallInteger(), nullable=False),
        sa.Column("amount_subunit", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("application_id", "sequence", name="uq_rdp_invoice_application_sequence"),
    )
    op.create_index("ix_rdp_invoices_application_id", "rdp_invoices", ["application_id"])
    op.create_index("ix_rdp_invoices_status", "rdp_invoices", ["status"])

    op.create_table(
        "rdp_payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("rdp_invoices.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reference", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default="paystack"),
        sa.Column("amount_subunit", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="initialized"),
        sa.Column("provider_id", sa.String(80), nullable=True),
        sa.Column("provider_payload", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_rdp_payments_invoice_id", "rdp_payments", ["invoice_id"])
    op.create_index("ix_rdp_payments_reference", "rdp_payments", ["reference"])
    op.create_index("ix_rdp_payments_status", "rdp_payments", ["status"])

    op.create_table(
        "rdp_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("rdp_cohorts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("rdp_applications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active_payment_plan"),
        sa.Column("enrolled_at", sa.DateTime(), nullable=False),
        sa.Column("completion_status", sa.String(50), nullable=False, server_default="in_progress"),
        sa.Column("certificate_number", sa.String(100), nullable=True, unique=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("cohort_id", "application_id", name="uq_rdp_enrollment_application"),
        sa.UniqueConstraint("cohort_id", "user_id", name="uq_rdp_enrollment_user"),
    )
    op.create_index("ix_rdp_enrollments_cohort_id", "rdp_enrollments", ["cohort_id"])
    op.create_index("ix_rdp_enrollments_user_id", "rdp_enrollments", ["user_id"])

    op.create_table(
        "rdp_development_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("enrollment_id", sa.Integer(), sa.ForeignKey("rdp_enrollments.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("researcher_identity", sa.Text(), nullable=True),
        sa.Column("twelve_month_goal", sa.Text(), nullable=True),
        sa.Column("publication_goal", sa.Text(), nullable=True),
        sa.Column("methods_goal", sa.Text(), nullable=True),
        sa.Column("funding_goal", sa.Text(), nullable=True),
        sa.Column("network_goal", sa.Text(), nullable=True),
        sa.Column("impact_goal", sa.Text(), nullable=True),
        sa.Column("mentor_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "rdp_monthly_checkins",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("enrollment_id", sa.Integer(), sa.ForeignKey("rdp_enrollments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("month_number", sa.SmallInteger(), nullable=False),
        sa.Column("progress_summary", sa.Text(), nullable=True),
        sa.Column("outputs_this_month", sa.Text(), nullable=True),
        sa.Column("obstacles", sa.Text(), nullable=True),
        sa.Column("next_actions", sa.Text(), nullable=True),
        sa.Column("support_requested", sa.Text(), nullable=True),
        sa.Column("mentor_feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("enrollment_id", "month_number", name="uq_rdp_checkin_month"),
    )
    op.create_index("ix_rdp_monthly_checkins_enrollment_id", "rdp_monthly_checkins", ["enrollment_id"])

    op.create_table(
        "rdp_programme_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("rdp_cohorts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False, server_default="masterclass"),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("delivery_mode", sa.String(80), nullable=True),
        sa.Column("meeting_url", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rdp_programme_events_cohort_id", "rdp_programme_events", ["cohort_id"])

    op.create_table(
        "rdp_resources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cohort_id", sa.Integer(), sa.ForeignKey("rdp_cohorts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False, server_default="document"),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("month_number", sa.SmallInteger(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rdp_resources_cohort_id", "rdp_resources", ["cohort_id"])

    # Seed the confirmed Founding Cohort and fee plans.
    cohort = sa.table(
        "rdp_cohorts",
        sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("slug", sa.String),
        sa.column("label", sa.String), sa.column("application_open_date", sa.Date),
        sa.column("application_deadline", sa.Date), sa.column("start_date", sa.Date),
        sa.column("graduation_date", sa.Date), sa.column("end_date", sa.Date),
        sa.column("capacity", sa.SmallInteger), sa.column("status", sa.String), sa.column("is_published", sa.Boolean),
    )
    op.bulk_insert(cohort, [{
        "id": 1,
        "name": "Ungozu R & D Researcher Development Programme",
        "slug": "founding-cohort-2026-2027",
        "label": "Founding Cohort 2026/2027",
        "application_open_date": date(2026, 10, 2),
        "application_deadline": date(2026, 11, 2),
        "start_date": date(2026, 12, 2),
        "graduation_date": date(2027, 11, 27),
        "end_date": date(2027, 12, 2),
        "capacity": 10,
        "status": "applications_open",
        "is_published": True,
    }])
    fees = sa.table(
        "rdp_fee_plans",
        sa.column("cohort_id", sa.Integer), sa.column("code", sa.String), sa.column("region", sa.String),
        sa.column("name", sa.String), sa.column("currency", sa.String), sa.column("total_amount_subunit", sa.Integer),
        sa.column("installment_count", sa.SmallInteger), sa.column("installment_amount_subunit", sa.Integer),
        sa.column("description", sa.Text), sa.column("is_active", sa.Boolean), sa.column("sort_order", sa.SmallInteger),
    )
    op.bulk_insert(fees, [
        {"cohort_id":1,"code":"ng_full","region":"nigeria","name":"Nigeria — Founding Cohort Full Payment","currency":"NGN","total_amount_subunit":15000000,"installment_count":1,"installment_amount_subunit":15000000,"description":"₦150,000 once","is_active":True,"sort_order":1},
        {"cohort_id":1,"code":"ng_three","region":"nigeria","name":"Nigeria — Three Instalments","currency":"NGN","total_amount_subunit":15000000,"installment_count":3,"installment_amount_subunit":5000000,"description":"₦50,000 × 3","is_active":True,"sort_order":2},
        {"cohort_id":1,"code":"ng_monthly","region":"nigeria","name":"Nigeria — Monthly Plan","currency":"NGN","total_amount_subunit":18000000,"installment_count":12,"installment_amount_subunit":1500000,"description":"₦15,000 × 12","is_active":True,"sort_order":3},
        {"cohort_id":1,"code":"africa_full","region":"africa_lmic","name":"Africa/LMIC — Founding Cohort","currency":"USD","total_amount_subunit":35000,"installment_count":1,"installment_amount_subunit":35000,"description":"US$350 full payment","is_active":True,"sort_order":4},
        {"cohort_id":1,"code":"intl_full","region":"international","name":"International — Founding Cohort","currency":"USD","total_amount_subunit":60000,"installment_count":1,"installment_amount_subunit":60000,"description":"US$600 full payment","is_active":True,"sort_order":5},
    ])


def downgrade() -> None:
    for table in [
        "rdp_resources", "rdp_programme_events", "rdp_monthly_checkins", "rdp_development_plans",
        "rdp_enrollments", "rdp_payments", "rdp_invoices", "rdp_scholarship_requests",
        "rdp_application_reviews", "rdp_applications", "rdp_fee_plans", "rdp_cohorts",
    ]:
        op.drop_table(table)
    op.drop_table("users")
