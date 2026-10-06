"""Pydantic schemas for the Ungozu R & D Researcher Development Programme."""
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field, model_validator


class RDPFeePlanOut(BaseModel):
    id: int
    code: str
    region: str
    name: str
    currency: str
    total_amount_subunit: int
    installment_count: int
    installment_amount_subunit: int
    description: str | None = None
    is_active: bool
    model_config = {"from_attributes": True}


class RDPCohortOut(BaseModel):
    id: int
    name: str
    slug: str
    label: str
    application_open_date: date
    application_deadline: date
    start_date: date
    graduation_date: date
    end_date: date
    capacity: int
    status: str
    public_summary: str | None = None
    is_published: bool
    fee_plans: list[RDPFeePlanOut] = []
    model_config = {"from_attributes": True}


class RDPApplicationCreate(BaseModel):
    cohort_slug: str = "founding-cohort-2026-2027"
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    country: str = Field(min_length=2, max_length=120)
    institution: str = Field(min_length=2, max_length=255)
    career_stage: str = Field(min_length=2, max_length=120)
    discipline: str = Field(min_length=2, max_length=180)
    research_interests: str = Field(min_length=20, max_length=10000)
    goals: str = Field(min_length=20, max_length=10000)
    challenges: str = Field(min_length=20, max_length=10000)
    current_outputs: str | None = Field(default=None, max_length=10000)
    commitment: str = Field(min_length=20, max_length=10000)
    scholarship_interest: bool = False
    referral_source: str | None = Field(default=None, max_length=255)
    consent: bool

    @model_validator(mode="after")
    def consent_required(self):
        if not self.consent:
            raise ValueError("Consent is required")
        return self


class RDPApplicationReceipt(BaseModel):
    application_ref: str
    access_token: str
    status: str
    message: str


class RDPApplicationPublicStatus(BaseModel):
    application_ref: str
    full_name: str
    cohort_label: str
    status: str
    scholarship_status: str | None = None
    fee_plan: RDPFeePlanOut | None = None
    acceptance_deadline: datetime | None = None
    invoices: list["RDPInvoiceOut"] = []


class RDPScholarshipCreate(BaseModel):
    application_ref: str
    access_token: str
    support_type: str = Field(min_length=2, max_length=100)
    financial_need: str = Field(min_length=20, max_length=10000)
    possible_contribution: str | None = Field(default=None, max_length=255)
    support_case: str = Field(min_length=20, max_length=10000)


class RDPScholarshipOut(BaseModel):
    id: int
    application_id: int
    support_type: str
    financial_need: str
    possible_contribution: str | None = None
    support_case: str
    status: str
    approved_amount_subunit: int | None = None
    approved_currency: str | None = None
    admin_notes: str | None = None
    model_config = {"from_attributes": True}


class RDPReviewUpsert(BaseModel):
    motivation_score: int = Field(ge=0, le=20)
    development_need_score: int = Field(ge=0, le=20)
    programme_fit_score: int = Field(ge=0, le=20)
    commitment_score: int = Field(ge=0, le=20)
    potential_score: int = Field(ge=0, le=20)
    recommendation: str = Field(pattern="^(accept|shortlist|waitlist|decline|hold)$")
    notes: str | None = None


class RDPReviewOut(RDPReviewUpsert):
    id: int
    application_id: int
    reviewer_id: int
    total_score: int
    reviewer_name: str | None = None
    model_config = {"from_attributes": True}


class RDPDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(shortlisted|accepted|waitlisted|declined)$")
    fee_plan_id: int | None = None
    acceptance_deadline: datetime | None = None
    admission_notes: str | None = None


class RDPDecisionResponse(BaseModel):
    status: str
    payment_link: str | None = None
    email_sent: bool = False


class RDPScholarshipDecisionRequest(BaseModel):
    status: str = Field(pattern="^(under_review|approved|partially_approved|declined)$")
    approved_amount_subunit: int | None = Field(default=None, ge=0)
    approved_currency: str | None = Field(default=None, min_length=3, max_length=3)
    admin_notes: str | None = None


class RDPInvoiceOut(BaseModel):
    id: int
    sequence: int
    amount_subunit: int
    currency: str
    due_date: date | None = None
    status: str
    paid_at: datetime | None = None
    model_config = {"from_attributes": True}


class RDPPaymentOut(BaseModel):
    id: int
    invoice_id: int
    reference: str
    provider: str
    environment: str = "test"
    amount_subunit: int
    currency: str
    status: str
    provider_id: str | None = None
    provider_session_id: str | None = None
    paid_at: datetime | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class RDPPaymentInitRequest(BaseModel):
    application_ref: str
    payment_token: str
    invoice_id: int
    provider: str | None = Field(default=None, pattern="^(paystack|stripe)$")


class RDPPaymentInitResponse(BaseModel):
    authorization_url: str
    access_code: str | None = None
    reference: str
    provider: str
    environment: str


class RDPApplicationAdminOut(BaseModel):
    id: int
    cohort_id: int
    application_ref: str
    full_name: str
    email: str
    country: str
    institution: str
    career_stage: str
    discipline: str
    research_interests: str
    goals: str
    challenges: str
    current_outputs: str | None = None
    commitment: str
    scholarship_interest: bool
    referral_source: str | None = None
    status: str
    fee_plan_id: int | None = None
    acceptance_deadline: datetime | None = None
    admission_notes: str | None = None
    submitted_at: datetime
    decided_at: datetime | None = None
    fee_plan: RDPFeePlanOut | None = None
    reviews: list[RDPReviewOut] = []
    scholarship_request: RDPScholarshipOut | None = None
    invoices: list[RDPInvoiceOut] = []
    model_config = {"from_attributes": True}


class RDPDashboardStats(BaseModel):
    total_applications: int
    submitted: int
    screening: int
    shortlisted: int
    accepted_or_payment_due: int
    enrolled: int
    waitlisted: int
    declined: int
    scholarship_requests: int
    scholarship_approved: int
    payments_successful: int
    revenue_ngn_subunit: int
    revenue_usd_subunit: int
    revenue_by_currency_subunit: dict[str, int] = Field(default_factory=dict)
    cohort_capacity: int


class RDPEnrollmentOut(BaseModel):
    id: int
    cohort_id: int
    application_id: int
    user_id: int
    status: str
    enrolled_at: datetime
    completion_status: str
    certificate_number: str | None = None
    full_name: str | None = None
    email: str | None = None
    model_config = {"from_attributes": True}


class RDPDevelopmentPlanUpdate(BaseModel):
    researcher_identity: str | None = None
    twelve_month_goal: str | None = None
    publication_goal: str | None = None
    methods_goal: str | None = None
    funding_goal: str | None = None
    network_goal: str | None = None
    impact_goal: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|submitted|reviewed)$")


class RDPDevelopmentPlanOut(RDPDevelopmentPlanUpdate):
    id: int
    enrollment_id: int
    mentor_notes: str | None = None
    status: str
    model_config = {"from_attributes": True}


class RDPCheckInUpdate(BaseModel):
    progress_summary: str | None = None
    outputs_this_month: str | None = None
    obstacles: str | None = None
    next_actions: str | None = None
    support_requested: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|submitted|reviewed)$")


class RDPCheckInOut(RDPCheckInUpdate):
    id: int
    enrollment_id: int
    month_number: int
    mentor_feedback: str | None = None
    status: str
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    model_config = {"from_attributes": True}


class RDPEventOut(BaseModel):
    id: int
    title: str
    event_type: str
    starts_at: datetime
    ends_at: datetime | None = None
    delivery_mode: str | None = None
    meeting_url: str | None = None
    description: str | None = None
    model_config = {"from_attributes": True}


class RDPResourceOut(BaseModel):
    id: int
    title: str
    resource_type: str
    url: str | None = None
    description: str | None = None
    month_number: int | None = None
    sort_order: int
    model_config = {"from_attributes": True}


class RDPPortalDashboard(BaseModel):
    enrollment: RDPEnrollmentOut
    cohort: RDPCohortOut
    development_plan: RDPDevelopmentPlanOut | None = None
    checkins: list[RDPCheckInOut] = []
    upcoming_events: list[RDPEventOut] = []
    resources: list[RDPResourceOut] = []
    invoices: list[RDPInvoiceOut] = []


class RDPEventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    event_type: str = Field(default="masterclass", min_length=2, max_length=80)
    starts_at: datetime
    ends_at: datetime | None = None
    delivery_mode: str | None = Field(default=None, max_length=80)
    meeting_url: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    is_published: bool = True


class RDPEventAdminOut(RDPEventOut):
    cohort_id: int
    is_published: bool
    model_config = {"from_attributes": True}


class RDPResourceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    resource_type: str = Field(default="document", min_length=2, max_length=80)
    url: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    month_number: int | None = Field(default=None, ge=1, le=12)
    is_published: bool = True
    sort_order: int = Field(default=0, ge=0, le=32767)


class RDPResourceAdminOut(RDPResourceOut):
    cohort_id: int
    is_published: bool
    model_config = {"from_attributes": True}


class RDPAdminCheckInUpdate(BaseModel):
    mentor_feedback: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|submitted|reviewed)$")


class RDPEnrollmentAdminDetail(BaseModel):
    enrollment: RDPEnrollmentOut
    cohort: RDPCohortOut
    development_plan: RDPDevelopmentPlanOut | None = None
    checkins: list[RDPCheckInOut] = []
    invoices: list[RDPInvoiceOut] = []


class RDPAdminDevelopmentPlanUpdate(BaseModel):
    mentor_notes: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|submitted|reviewed)$")


# ── Multi-gateway payment administration ────────────────────────────────────

class RDPPublicPaymentProvider(BaseModel):
    provider: str
    display_name: str
    environment: str
    currency: str
    priority: int


class RDPPaymentProviderList(BaseModel):
    active_environment: str
    allow_provider_selection: bool
    providers: list[RDPPublicPaymentProvider]


class RDPPaymentPlatformSettingsOut(BaseModel):
    active_environment: str
    allow_provider_selection: bool


class RDPPaymentPlatformSettingsUpdate(BaseModel):
    active_environment: str = Field(pattern="^(test|live)$")
    allow_provider_selection: bool = True
    current_password: str | None = Field(default=None, min_length=1, max_length=128)


class RDPPaymentProviderConfigUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=100)
    is_enabled: bool | None = None
    public_key: str | None = Field(default=None, max_length=255)
    secret_key: str | None = Field(default=None, max_length=500)
    webhook_secret: str | None = Field(default=None, max_length=500)
    supported_currencies: list[str] | None = None
    priority: int | None = Field(default=None, ge=1, le=999)
    current_password: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def normalize_currencies(self):
        if self.supported_currencies is not None:
            values: list[str] = []
            for currency in self.supported_currencies:
                code = currency.strip().upper()
                if len(code) != 3 or not code.isalpha():
                    raise ValueError(f"Invalid currency code: {currency}")
                if code not in values:
                    values.append(code)
            if not values:
                raise ValueError("At least one supported currency is required")
            self.supported_currencies = values
        return self


class RDPPaymentProviderConfigOut(BaseModel):
    provider: str
    environment: str
    display_name: str
    is_enabled: bool
    public_key: str | None = None
    secret_configured: bool
    webhook_secret_configured: bool
    secret_key_masked: str | None = None
    webhook_secret_masked: str | None = None
    supported_currencies: list[str]
    priority: int
    last_tested_at: datetime | None = None
    last_test_status: str | None = None
    last_test_message: str | None = None
    source: str = "database"
    webhook_url: str
    callback_url: str


class RDPPaymentProviderTestOut(BaseModel):
    provider: str
    environment: str
    success: bool
    message: str
    tested_at: datetime


class RDPPaymentAuditOut(BaseModel):
    id: int
    admin_user_id: int | None = None
    action: str
    provider: str | None = None
    environment: str | None = None
    details: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class RDPPaymentProviderHealthOut(BaseModel):
    provider: str
    environment: str
    display_name: str
    enabled: bool
    configured: bool
    connection_status: str | None = None
    last_tested_at: datetime | None = None
    last_test_message: str | None = None
    last_webhook_at: datetime | None = None
    webhook_status: str | None = None
    successful_payments: int = 0
    failed_payments: int = 0


class RDPPaymentHealthOut(BaseModel):
    active_environment: str
    providers: list[RDPPaymentProviderHealthOut]
