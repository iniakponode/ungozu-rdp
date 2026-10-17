"""Operational models for the Ungozu R & D Researcher Development Programme."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class RDPCohort(Base, TimestampMixin):
    __tablename__ = "rdp_cohorts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    programme_version_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "rdp_programme_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    application_open_date: Mapped[date] = mapped_column(Date, nullable=False)
    application_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    graduation_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    capacity: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="applications_open")
    public_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    fee_plans: Mapped[list["RDPFeePlan"]] = relationship(
        "RDPFeePlan", back_populates="cohort", cascade="all, delete-orphan", lazy="selectin"
    )


class RDPFeePlan(Base, TimestampMixin):
    __tablename__ = "rdp_fee_plans"
    __table_args__ = (UniqueConstraint("cohort_id", "code", name="uq_rdp_fee_plan_cohort_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("rdp_packages.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_amount_subunit: Mapped[int] = mapped_column(Integer, nullable=False)
    installment_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    installment_amount_subunit: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    cohort: Mapped[RDPCohort] = relationship("RDPCohort", back_populates="fee_plans")


class RDPApplication(Base, TimestampMixin):
    __tablename__ = "rdp_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_cohorts.id", ondelete="RESTRICT"), nullable=False, index=True)
    application_ref: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payment_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    career_stage: Mapped[str] = mapped_column(String(120), nullable=False)
    discipline: Mapped[str] = mapped_column(String(180), nullable=False)
    research_interests: Mapped[str] = mapped_column(Text, nullable=False)
    goals: Mapped[str] = mapped_column(Text, nullable=False)
    challenges: Mapped[str] = mapped_column(Text, nullable=False)
    current_outputs: Mapped[str | None] = mapped_column(Text, nullable=True)
    commitment: Mapped[str] = mapped_column(Text, nullable=False)
    scholarship_interest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    referral_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="submitted", index=True)
    fee_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rdp_fee_plans.id", ondelete="SET NULL"), nullable=True)
    # Applicant preference only: never a reservation, invoice or approved price.
    preferred_package_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rdp_packages.id", ondelete="SET NULL"), nullable=True, index=True)
    preferred_fee_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("rdp_fee_plans.id", ondelete="SET NULL"), nullable=True, index=True)
    acceptance_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    admission_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cohort: Mapped[RDPCohort] = relationship("RDPCohort", lazy="selectin")
    fee_plan: Mapped[RDPFeePlan | None] = relationship("RDPFeePlan", lazy="selectin")
    reviews: Mapped[list["RDPApplicationReview"]] = relationship(
        "RDPApplicationReview", back_populates="application", cascade="all, delete-orphan", lazy="selectin"
    )
    scholarship_request: Mapped["RDPScholarshipRequest | None"] = relationship(
        "RDPScholarshipRequest", back_populates="application", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    invoices: Mapped[list["RDPInvoice"]] = relationship(
        "RDPInvoice", back_populates="application", cascade="all, delete-orphan", lazy="selectin"
    )


class RDPApplicationReview(Base, TimestampMixin):
    __tablename__ = "rdp_application_reviews"
    __table_args__ = (UniqueConstraint("application_id", "reviewer_id", name="uq_rdp_review_application_reviewer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    motivation_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    development_need_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    programme_fit_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    commitment_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    potential_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False, default="hold")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped[RDPApplication] = relationship("RDPApplication", back_populates="reviews")
    reviewer = relationship("User", lazy="selectin")


class RDPScholarshipRequest(Base, TimestampMixin):
    __tablename__ = "rdp_scholarship_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_applications.id", ondelete="CASCADE"), nullable=False, unique=True)
    support_type: Mapped[str] = mapped_column(String(100), nullable=False)
    financial_need: Mapped[str] = mapped_column(Text, nullable=False)
    possible_contribution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    support_case: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="submitted", index=True)
    approved_amount_subunit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approved_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    application: Mapped[RDPApplication] = relationship("RDPApplication", back_populates="scholarship_request")


class RDPInvoice(Base, TimestampMixin):
    __tablename__ = "rdp_invoices"
    __table_args__ = (UniqueConstraint("application_id", "sequence", name="uq_rdp_invoice_application_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    fee_plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_fee_plans.id", ondelete="RESTRICT"), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    amount_subunit: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    application: Mapped[RDPApplication] = relationship("RDPApplication", back_populates="invoices")
    fee_plan: Mapped[RDPFeePlan] = relationship("RDPFeePlan", lazy="selectin")
    payments: Mapped[list["RDPPayment"]] = relationship("RDPPayment", back_populates="invoice", lazy="selectin")


class RDPPayment(Base, TimestampMixin):
    __tablename__ = "rdp_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    reference: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="paystack")
    amount_subunit: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="initialized", index=True)
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    environment: Mapped[str] = mapped_column(String(10), nullable=False, default="test")
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    invoice: Mapped[RDPInvoice] = relationship("RDPInvoice", back_populates="payments", lazy="selectin")


class RDPPaymentPlatformSettings(Base, TimestampMixin):
    """Global payment behaviour. A single row (id=1) controls the active gateway environment."""
    __tablename__ = "rdp_payment_platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_environment: Mapped[str] = mapped_column(String(10), nullable=False, default="test")
    allow_provider_selection: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RDPPaymentProviderConfig(Base, TimestampMixin):
    """Encrypted per-provider configuration for test/live environments."""
    __tablename__ = "rdp_payment_provider_configs"
    __table_args__ = (
        UniqueConstraint("provider", "environment", name="uq_rdp_payment_provider_environment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    public_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    supported_currencies_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_test_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    configured_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class RDPPaymentAuditLog(Base):
    """Immutable administrative audit log. Secret values are never stored here."""
    __tablename__ = "rdp_payment_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(10), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class RDPPaymentWebhookEvent(Base):
    """Webhook receipt ledger for idempotency and gateway health monitoring."""
    __tablename__ = "rdp_payment_webhook_events"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_rdp_payment_webhook_dedupe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    environment: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class RDPEnrollment(Base, TimestampMixin):
    __tablename__ = "rdp_enrollments"
    __table_args__ = (
        UniqueConstraint("cohort_id", "application_id", name="uq_rdp_enrollment_application"),
        UniqueConstraint("cohort_id", "user_id", name="uq_rdp_enrollment_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_cohorts.id", ondelete="RESTRICT"), nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_applications.id", ondelete="RESTRICT"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active_payment_plan")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completion_status: Mapped[str] = mapped_column(String(50), nullable=False, default="in_progress")
    certificate_number: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    cohort: Mapped[RDPCohort] = relationship("RDPCohort", lazy="selectin")
    application: Mapped[RDPApplication] = relationship("RDPApplication", lazy="selectin")
    user = relationship("User", lazy="selectin")
    development_plan: Mapped["RDPDevelopmentPlan | None"] = relationship(
        "RDPDevelopmentPlan", back_populates="enrollment", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )


class RDPDevelopmentPlan(Base, TimestampMixin):
    __tablename__ = "rdp_development_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_enrollments.id", ondelete="CASCADE"), nullable=False, unique=True)
    researcher_identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    twelve_month_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    methods_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    funding_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    network_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    mentor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")

    enrollment: Mapped[RDPEnrollment] = relationship("RDPEnrollment", back_populates="development_plan")


class RDPMonthlyCheckIn(Base, TimestampMixin):
    __tablename__ = "rdp_monthly_checkins"
    __table_args__ = (UniqueConstraint("enrollment_id", "month_number", name="uq_rdp_checkin_month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    month_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    progress_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    outputs_this_month: Mapped[str | None] = mapped_column(Text, nullable=True)
    obstacles: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_requested: Mapped[str | None] = mapped_column(Text, nullable=True)
    mentor_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RDPProgrammeEvent(Base, TimestampMixin):
    __tablename__ = "rdp_programme_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, default="masterclass")
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivery_mode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RDPResource(Base, TimestampMixin):
    __tablename__ = "rdp_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cohort_id: Mapped[int] = mapped_column(Integer, ForeignKey("rdp_cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False, default="document")
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    month_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
