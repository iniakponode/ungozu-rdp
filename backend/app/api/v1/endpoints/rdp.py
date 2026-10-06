"""Ungozu R & D Researcher Development Programme operational API."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from jwt import PyJWTError as JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_active_admin, get_current_rdp_mentee
from app.auth.jwt import create_password_reset_token, decode_password_reset_token
from app.auth.password import hash_password, verify_password
from app.core.config import settings
from app.core.rate_limit import limiter, RateLimits
from app.db.session import get_db
from app.models.rdp import (
    RDPApplication, RDPApplicationReview, RDPCohort, RDPDevelopmentPlan, RDPEnrollment,
    RDPFeePlan, RDPInvoice, RDPMonthlyCheckIn, RDPPayment, RDPProgrammeEvent,
    RDPResource, RDPScholarshipRequest, RDPPaymentPlatformSettings,
    RDPPaymentProviderConfig, RDPPaymentAuditLog, RDPPaymentWebhookEvent,
)
from app.models.user import User
from app.schemas.rdp import (
    RDPApplicationAdminOut, RDPApplicationCreate, RDPApplicationPublicStatus,
    RDPApplicationReceipt, RDPCheckInOut, RDPCheckInUpdate, RDPCohortOut,
    RDPDashboardStats, RDPDecisionRequest, RDPDecisionResponse, RDPDevelopmentPlanOut,
    RDPDevelopmentPlanUpdate, RDPEnrollmentOut, RDPEventOut, RDPFeePlanOut,
    RDPInvoiceOut, RDPPaymentInitRequest, RDPPaymentInitResponse, RDPPaymentOut,
    RDPPortalDashboard, RDPResourceOut, RDPReviewOut, RDPReviewUpsert,
    RDPScholarshipCreate, RDPScholarshipDecisionRequest, RDPScholarshipOut,
    RDPEventCreate, RDPEventAdminOut, RDPResourceCreate, RDPResourceAdminOut,
    RDPAdminCheckInUpdate, RDPEnrollmentAdminDetail, RDPAdminDevelopmentPlanUpdate,
    RDPPublicPaymentProvider, RDPPaymentProviderList, RDPPaymentPlatformSettingsOut,
    RDPPaymentPlatformSettingsUpdate, RDPPaymentProviderConfigUpdate,
    RDPPaymentProviderConfigOut, RDPPaymentProviderTestOut, RDPPaymentAuditOut,
    RDPPaymentProviderHealthOut, RDPPaymentHealthOut,
)
from app.services.rdp import (
    application_reference, create_invoices, ensure_enrollment_after_payment, recalculate_unpaid_invoices,
    get_application_by_ref, get_public_cohort, issue_token, payment_reference,
    payment_revenue_stats, send_application_confirmation, send_decision_email, send_payment_confirmation,
    token_hash, verify_access_token,
)
from app.services.email import send_email
from app.services.rdp_payments import (
    DEFAULTS, SUPPORTED_PROVIDERS, GatewayConfig, GatewayVerification, PaymentGatewayError,
    available_gateway_configs, get_platform_settings, infer_environment_from_key,
    initialize_gateway_transaction, load_gateway_config, normalize_webhook,
    test_gateway_connection, valid_gateway_webhook_signature, validate_key_environment,
    verify_gateway_transaction, webhook_environment,
)
from app.services.credential_crypto import decrypt_credentials, encrypt_credentials, mask_secret

router = APIRouter(prefix="/rdp", tags=["researcher-development-programme"])
DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(get_current_active_admin)]
MenteeDep = Annotated[User, Depends(get_current_rdp_mentee)]


def _review_out(r: RDPApplicationReview) -> RDPReviewOut:
    return RDPReviewOut(
        id=r.id, application_id=r.application_id, reviewer_id=r.reviewer_id,
        motivation_score=r.motivation_score, development_need_score=r.development_need_score,
        programme_fit_score=r.programme_fit_score, commitment_score=r.commitment_score,
        potential_score=r.potential_score, total_score=r.total_score,
        recommendation=r.recommendation, notes=r.notes,
        reviewer_name=(r.reviewer.full_name or r.reviewer.email) if r.reviewer else None,
    )


def _application_admin_out(a: RDPApplication) -> RDPApplicationAdminOut:
    return RDPApplicationAdminOut(
        id=a.id, cohort_id=a.cohort_id, application_ref=a.application_ref,
        full_name=a.full_name, email=a.email, country=a.country, institution=a.institution,
        career_stage=a.career_stage, discipline=a.discipline,
        research_interests=a.research_interests, goals=a.goals, challenges=a.challenges,
        current_outputs=a.current_outputs, commitment=a.commitment,
        scholarship_interest=a.scholarship_interest, referral_source=a.referral_source,
        status=a.status, fee_plan_id=a.fee_plan_id, acceptance_deadline=a.acceptance_deadline,
        admission_notes=a.admission_notes, submitted_at=a.submitted_at, decided_at=a.decided_at,
        fee_plan=RDPFeePlanOut.model_validate(a.fee_plan) if a.fee_plan else None,
        reviews=[_review_out(r) for r in (a.reviews or [])],
        scholarship_request=RDPScholarshipOut.model_validate(a.scholarship_request) if a.scholarship_request else None,
        invoices=[RDPInvoiceOut.model_validate(i) for i in (a.invoices or [])],
    )


async def _load_application(db: AsyncSession, application_id: int) -> RDPApplication:
    stmt = (
        select(RDPApplication)
        .where(RDPApplication.id == application_id)
        .options(
            selectinload(RDPApplication.fee_plan),
            selectinload(RDPApplication.reviews).selectinload(RDPApplicationReview.reviewer),
            selectinload(RDPApplication.scholarship_request),
            selectinload(RDPApplication.invoices),
            selectinload(RDPApplication.cohort),
        )
    )
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Application not found")
    return obj


async def _load_payment(db: AsyncSession, reference: str) -> RDPPayment | None:
    stmt = (
        select(RDPPayment)
        .where(RDPPayment.reference == reference)
        .options(
            selectinload(RDPPayment.invoice).selectinload(RDPInvoice.application).selectinload(RDPApplication.cohort),
            selectinload(RDPPayment.invoice).selectinload(RDPInvoice.application).selectinload(RDPApplication.fee_plan),
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _apply_verified_payment(db: AsyncSession, payment: RDPPayment, result: GatewayVerification) -> RDPPayment:
    """Apply one verified provider result idempotently and activate programme access."""
    if payment.status == "success":
        return payment
    if result.reference != payment.reference:
        raise HTTPException(400, "Payment reference mismatch")
    payment.provider_session_id = result.provider_session_id or payment.provider_session_id
    payment.provider_payload = json.dumps(result.raw, default=str)[:50000]
    if result.status != "success":
        payment.status = result.status or "failed"
        await db.commit()
        return payment
    if int(result.amount_subunit) != payment.amount_subunit:
        raise HTTPException(400, "Payment amount mismatch")
    if result.currency.upper() != payment.currency.upper():
        raise HTTPException(400, "Payment currency mismatch")
    payment.status = "success"
    payment.provider_id = result.provider_id
    payment.paid_at = result.paid_at or datetime.utcnow()
    invoice = payment.invoice
    invoice.status = "paid"
    invoice.paid_at = payment.paid_at
    # Activate the next scheduled invoice.
    next_invoice = (await db.execute(
        select(RDPInvoice).where(
            RDPInvoice.application_id == invoice.application_id,
            RDPInvoice.sequence == invoice.sequence + 1,
        )
    )).scalar_one_or_none()
    if next_invoice and next_invoice.status == "scheduled":
        next_invoice.status = "pending"
    await ensure_enrollment_after_payment(db, payment)
    # All invoices paid => fully paid enrollment.
    outstanding = (await db.execute(
        select(func.count()).select_from(RDPInvoice).where(
            RDPInvoice.application_id == invoice.application_id,
            RDPInvoice.status != "paid",
        )
    )).scalar_one()
    enrollment = (await db.execute(select(RDPEnrollment).where(RDPEnrollment.application_id == invoice.application_id))).scalar_one_or_none()
    if enrollment and outstanding == 0:
        enrollment.status = "active_paid"
    await db.commit()
    await send_payment_confirmation(payment)
    return payment


async def _payment_audit(
    db: AsyncSession,
    admin_user_id: int | None,
    action: str,
    *,
    provider: str | None = None,
    environment: str | None = None,
    details: dict | None = None,
) -> None:
    # Never pass raw credentials to this helper.
    safe_details = json.dumps(details or {}, default=str, separators=(",", ":"))[:10000] if details else None
    db.add(RDPPaymentAuditLog(
        admin_user_id=admin_user_id, action=action, provider=provider,
        environment=environment, details=safe_details,
    ))


def _provider_urls(provider: str) -> tuple[str, str]:
    base = settings.BACKEND_PUBLIC_URL.rstrip("/")
    webhook = f"{base}/api/v1/rdp/public/payments/webhooks/{provider}"
    callback = f"{base}/api/v1/rdp/public/payments/{provider}/callback"
    return webhook, callback


# ── Public: cohort, application, scholarship, status ─────────────────────────

@router.get("/public/cohort", response_model=RDPCohortOut)
async def public_cohort(db: DbDep, slug: str | None = None):
    cohort = await get_public_cohort(db, slug)
    if not cohort:
        raise HTTPException(404, "No published cohort")
    return cohort


@router.post("/public/applications", response_model=RDPApplicationReceipt, status_code=201)
@limiter.limit(RateLimits.PUBLIC_FORM)
async def submit_application(request: Request, payload: RDPApplicationCreate, db: DbDep):
    cohort = await get_public_cohort(db, payload.cohort_slug)
    if not cohort:
        raise HTTPException(404, "Cohort not found")
    today = datetime.now(ZoneInfo("Africa/Lagos")).date()
    if not settings.RDP_ALLOW_OUT_OF_WINDOW_APPLICATIONS and not (cohort.application_open_date <= today <= cohort.application_deadline):
        raise HTTPException(400, "Applications are not currently open for this cohort")
    duplicate = (await db.execute(select(RDPApplication).where(
        RDPApplication.cohort_id == cohort.id, RDPApplication.email == str(payload.email)
    ))).scalar_one_or_none()
    if duplicate:
        raise HTTPException(409, "An application already exists for this email and cohort")
    token = issue_token()
    obj = RDPApplication(
        cohort_id=cohort.id, application_ref=application_reference(), access_token_hash=token_hash(token),
        full_name=payload.full_name.strip(), email=str(payload.email).lower(), country=payload.country.strip(),
        institution=payload.institution.strip(), career_stage=payload.career_stage.strip(), discipline=payload.discipline.strip(),
        research_interests=payload.research_interests.strip(), goals=payload.goals.strip(), challenges=payload.challenges.strip(),
        current_outputs=(payload.current_outputs or "").strip() or None, commitment=payload.commitment.strip(),
        scholarship_interest=payload.scholarship_interest, referral_source=(payload.referral_source or "").strip() or None,
        status="submitted", submitted_at=datetime.utcnow(),
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    await send_application_confirmation(obj, token)
    return RDPApplicationReceipt(
        application_ref=obj.application_ref, access_token=token, status=obj.status,
        message="Application received. Save the reference and private access token.",
    )


@router.get("/public/application-status", response_model=RDPApplicationPublicStatus)
async def application_status(ref: str, token: str, db: DbDep):
    a = await get_application_by_ref(db, ref)
    if not a or not verify_access_token(a, token):
        raise HTTPException(404, "Application not found")
    a = await _load_application(db, a.id)
    return RDPApplicationPublicStatus(
        application_ref=a.application_ref, full_name=a.full_name, cohort_label=a.cohort.label,
        status=a.status, scholarship_status=a.scholarship_request.status if a.scholarship_request else None,
        fee_plan=RDPFeePlanOut.model_validate(a.fee_plan) if a.fee_plan else None,
        acceptance_deadline=a.acceptance_deadline,
        invoices=[RDPInvoiceOut.model_validate(i) for i in a.invoices],
    )


@router.get("/public/payment-summary", response_model=RDPApplicationPublicStatus)
async def payment_summary(ref: str, token: str, db: DbDep):
    a = await get_application_by_ref(db, ref)
    if not a or not verify_access_token(a, token, payment=True):
        raise HTTPException(404, "Admission/payment record not found")
    a = await _load_application(db, a.id)
    if a.status not in {"payment_due", "enrolled"}:
        raise HTTPException(400, "This application is not currently payable")
    return RDPApplicationPublicStatus(
        application_ref=a.application_ref, full_name=a.full_name, cohort_label=a.cohort.label,
        status=a.status, scholarship_status=a.scholarship_request.status if a.scholarship_request else None,
        fee_plan=RDPFeePlanOut.model_validate(a.fee_plan) if a.fee_plan else None,
        acceptance_deadline=a.acceptance_deadline,
        invoices=[RDPInvoiceOut.model_validate(i) for i in a.invoices],
    )


@router.post("/public/scholarships", response_model=RDPScholarshipOut, status_code=201)
@limiter.limit(RateLimits.PUBLIC_FORM)
async def submit_scholarship(request: Request, payload: RDPScholarshipCreate, db: DbDep):
    a = await get_application_by_ref(db, payload.application_ref)
    if not a or not verify_access_token(a, payload.access_token):
        raise HTTPException(404, "Application not found")
    existing = (await db.execute(select(RDPScholarshipRequest).where(RDPScholarshipRequest.application_id == a.id))).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "A scholarship request already exists for this application")
    obj = RDPScholarshipRequest(
        application_id=a.id, support_type=payload.support_type, financial_need=payload.financial_need,
        possible_contribution=payload.possible_contribution, support_case=payload.support_case, status="submitted",
    )
    a.scholarship_interest = True
    db.add(obj)
    await db.commit(); await db.refresh(obj)
    return obj


# ── Public: payments ─────────────────────────────────────────────────────────

@router.get("/public/payment-providers", response_model=RDPPaymentProviderList)
async def public_payment_providers(ref: str, token: str, invoice_id: int, db: DbDep):
    a = await get_application_by_ref(db, ref)
    if not a or not verify_access_token(a, token, payment=True):
        raise HTTPException(404, "Admission/payment record not found")
    if a.status not in {"payment_due", "enrolled"}:
        raise HTTPException(400, "This application is not currently payable")
    invoice = (await db.execute(select(RDPInvoice).where(
        RDPInvoice.id == invoice_id, RDPInvoice.application_id == a.id
    ))).scalar_one_or_none()
    if not invoice or invoice.status not in {"pending", "failed"}:
        raise HTTPException(400, "This invoice is not payable")
    environment, allow_selection, configs = await available_gateway_configs(db, invoice.currency)
    providers = [
        RDPPublicPaymentProvider(
            provider=c.provider, display_name=c.display_name, environment=environment,
            currency=invoice.currency.upper(), priority=c.priority,
        )
        for c in configs
    ]
    return RDPPaymentProviderList(
        active_environment=environment,
        allow_provider_selection=allow_selection,
        providers=providers,
    )


@router.post("/public/payments/initialize", response_model=RDPPaymentInitResponse)
@limiter.limit(RateLimits.PUBLIC_FORM)
async def payment_initialize(request: Request, payload: RDPPaymentInitRequest, db: DbDep):
    a = await get_application_by_ref(db, payload.application_ref)
    if not a or not verify_access_token(a, payload.payment_token, payment=True):
        raise HTTPException(404, "Admission/payment record not found")
    if a.status not in {"payment_due", "enrolled"}:
        raise HTTPException(400, "This application is not currently payable")
    if a.acceptance_deadline and datetime.utcnow() > a.acceptance_deadline and a.status != "enrolled":
        raise HTTPException(410, "The acceptance/payment deadline has passed. Contact the programme team.")
    invoice = (await db.execute(select(RDPInvoice).where(
        RDPInvoice.id == payload.invoice_id, RDPInvoice.application_id == a.id
    ))).scalar_one_or_none()
    if not invoice or invoice.status not in {"pending", "failed"}:
        raise HTTPException(400, "This invoice is not payable")

    environment, allow_selection, configs = await available_gateway_configs(db, invoice.currency)
    if not configs:
        raise HTTPException(503, f"No payment provider is configured for {invoice.currency.upper()}")
    selected = configs[0]
    if payload.provider and allow_selection:
        match = next((c for c in configs if c.provider == payload.provider), None)
        if not match:
            raise HTTPException(400, f"{payload.provider.title()} is not available for this invoice")
        selected = match

    ref = payment_reference(invoice.id)
    payment = RDPPayment(
        invoice_id=invoice.id,
        reference=ref,
        provider=selected.provider,
        environment=environment,
        amount_subunit=invoice.amount_subunit,
        currency=invoice.currency,
        status="initialized",
    )
    db.add(payment)
    await db.flush()

    callback_base = f"{settings.BACKEND_PUBLIC_URL.rstrip('/')}/api/v1/rdp/public/payments/{selected.provider}/callback"
    if selected.provider == "stripe":
        callback = f"{callback_base}?reference={quote(ref)}&session_id={{CHECKOUT_SESSION_ID}}"
    else:
        callback = callback_base
    cancel_url = (
        f"{settings.FRONTEND_URL.rstrip('/')}/payment-result"
        f"?status=cancelled&reference={quote(ref)}&provider={quote(selected.provider)}"
    )
    try:
        result = await initialize_gateway_transaction(
            selected,
            email=a.email,
            amount_subunit=invoice.amount_subunit,
            currency=invoice.currency,
            reference=ref,
            callback_url=callback,
            cancel_url=cancel_url,
            metadata={"application_ref": a.application_ref, "invoice_id": invoice.id, "programme": "ungozu-rdp"},
            description=f"Ungozu R & D programme fee — instalment {invoice.sequence}",
        )
    except PaymentGatewayError as exc:
        payment.status = "initialization_failed"
        payment.provider_payload = json.dumps({"error": str(exc)})[:50000]
        await db.commit()
        raise HTTPException(502, str(exc)) from exc

    payment.provider_session_id = result.provider_session_id
    await db.commit()
    return RDPPaymentInitResponse(
        authorization_url=result.authorization_url,
        access_code=result.access_code,
        reference=result.reference,
        provider=selected.provider,
        environment=environment,
    )


async def _gateway_callback_response(
    provider: str,
    db: AsyncSession,
    *,
    reference: str | None,
    trxref: str | None = None,
    session_id: str | None = None,
):
    resolved_reference = reference or trxref
    if provider not in SUPPORTED_PROVIDERS or not resolved_reference:
        return RedirectResponse(f"{settings.FRONTEND_URL.rstrip('/')}/payment-result?status=unknown")
    payment = await _load_payment(db, resolved_reference)
    if not payment or payment.provider != provider:
        return RedirectResponse(f"{settings.FRONTEND_URL.rstrip('/')}/payment-result?status=unknown")
    try:
        config = await load_gateway_config(db, provider, payment.environment, include_disabled=True)
        if not config or not config.secret_key:
            raise PaymentGatewayError(f"{provider.title()} verification credentials are unavailable")
        result = await verify_gateway_transaction(
            config,
            reference=resolved_reference,
            provider_session_id=session_id or payment.provider_session_id,
        )
        payment = await _apply_verified_payment(db, payment, result)
        status = payment.status
    except (PaymentGatewayError, HTTPException):
        # Preserve an already successful idempotent payment, but record a genuine
        # callback verification failure so health reporting can surface it.
        if payment.status != "success":
            payment.status = "verification_failed"
            await db.commit()
        status = payment.status if payment.status == "success" else "verification_failed"
    return RedirectResponse(
        f"{settings.FRONTEND_URL.rstrip('/')}/payment-result"
        f"?status={quote(status)}&reference={quote(resolved_reference)}&provider={quote(provider)}"
    )


@router.get("/public/payments/{provider}/callback")
async def gateway_payment_callback(
    provider: str,
    db: DbDep,
    reference: str | None = None,
    trxref: str | None = None,
    session_id: str | None = None,
):
    return await _gateway_callback_response(
        provider.lower(), db, reference=reference, trxref=trxref, session_id=session_id
    )


@router.get("/public/payments/callback")
async def legacy_paystack_callback(db: DbDep, reference: str | None = None, trxref: str | None = None):
    """Backward-compatible callback for a Paystack dashboard still pointing at Phase 4."""
    return await _gateway_callback_response("paystack", db, reference=reference, trxref=trxref)


async def _process_gateway_webhook(provider: str, request: Request, db: AsyncSession):
    provider = provider.lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(404, "Unknown payment provider")
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(400, "Invalid webhook payload") from exc

    environment = webhook_environment(provider, payload)
    config = await load_gateway_config(db, provider, environment, include_disabled=True)
    if not config or not config.secret_key:
        raise HTTPException(503, "Webhook verification credentials unavailable")
    signature = (
        request.headers.get("x-paystack-signature")
        if provider == "paystack"
        else request.headers.get("stripe-signature")
    )
    if not valid_gateway_webhook_signature(config, raw_body=raw, signature=signature):
        raise HTTPException(401, "Invalid signature")

    envelope = normalize_webhook(provider, payload, environment)
    digest = hashlib.sha256(raw).hexdigest()
    identity = envelope.event_id or digest
    dedupe_key = hashlib.sha256(f"{provider}:{identity}".encode("utf-8")).hexdigest()
    existing = (await db.execute(select(RDPPaymentWebhookEvent).where(
        RDPPaymentWebhookEvent.dedupe_key == dedupe_key
    ))).scalar_one_or_none()
    if existing:
        return {"ok": True, "duplicate": True}

    receipt = RDPPaymentWebhookEvent(
        provider=provider,
        environment=environment,
        dedupe_key=dedupe_key,
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        payment_reference=envelope.reference,
        payload_digest=digest,
        status="received",
    )
    db.add(receipt)
    await db.flush()

    should_process = False
    if provider == "paystack":
        should_process = envelope.event_type == "charge.success"
    elif provider == "stripe":
        should_process = envelope.event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}

    if not should_process or not envelope.verification or envelope.verification.status != "success":
        receipt.status = "ignored"
        receipt.processed_at = datetime.utcnow()
        await db.commit()
        return {"ok": True}

    payment = await _load_payment(db, envelope.reference or "")
    if not payment or payment.provider != provider or payment.environment != environment:
        receipt.status = "unmatched"
        receipt.processed_at = datetime.utcnow()
        await db.commit()
        return {"ok": True}

    try:
        await _apply_verified_payment(db, payment, envelope.verification)
        receipt.status = "processed"
    except HTTPException:
        receipt.status = "rejected"
        receipt.processed_at = datetime.utcnow()
        await db.commit()
        raise
    receipt.processed_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}


@router.post("/public/payments/webhooks/{provider}", include_in_schema=False)
async def gateway_payment_webhook(provider: str, request: Request, db: DbDep):
    return await _process_gateway_webhook(provider, request, db)


@router.post("/public/payments/webhook", include_in_schema=False)
async def legacy_paystack_webhook(request: Request, db: DbDep):
    """Backward-compatible Phase 4 Paystack webhook route."""
    return await _process_gateway_webhook("paystack", request, db)


# ── Admin dashboard and review workflow ──────────────────────────────────────

@router.get("/admin/dashboard", response_model=RDPDashboardStats)
async def admin_dashboard(db: DbDep, _: AdminDep, cohort_id: int = 1):
    async def count_status(*statuses: str) -> int:
        return int((await db.execute(select(func.count()).select_from(RDPApplication).where(
            RDPApplication.cohort_id == cohort_id, RDPApplication.status.in_(statuses)
        ))).scalar_one())
    total = int((await db.execute(select(func.count()).select_from(RDPApplication).where(RDPApplication.cohort_id == cohort_id))).scalar_one())
    scholarship_requests = int((await db.execute(select(func.count()).select_from(RDPScholarshipRequest).join(RDPApplication).where(RDPApplication.cohort_id == cohort_id))).scalar_one())
    scholarship_approved = int((await db.execute(select(func.count()).select_from(RDPScholarshipRequest).join(RDPApplication).where(
        RDPApplication.cohort_id == cohort_id, RDPScholarshipRequest.status.in_(["approved","partially_approved"])
    ))).scalar_one())
    payments_successful, revenue_by_currency = await payment_revenue_stats(db, cohort_id)
    ngn = revenue_by_currency.get("NGN", 0)
    usd = revenue_by_currency.get("USD", 0)
    cohort = await db.get(RDPCohort, cohort_id)
    return RDPDashboardStats(
        total_applications=total, submitted=await count_status("submitted"), screening=await count_status("screening"),
        shortlisted=await count_status("shortlisted"), accepted_or_payment_due=await count_status("accepted","payment_due"),
        enrolled=await count_status("enrolled"), waitlisted=await count_status("waitlisted"), declined=await count_status("declined"),
        scholarship_requests=scholarship_requests, scholarship_approved=scholarship_approved,
        payments_successful=payments_successful, revenue_ngn_subunit=ngn, revenue_usd_subunit=usd,
        revenue_by_currency_subunit=revenue_by_currency,
        cohort_capacity=cohort.capacity if cohort else 10,
    )


@router.get("/admin/applications", response_model=list[RDPApplicationAdminOut])
async def admin_applications(db: DbDep, _: AdminDep, status: str | None = None, q: str | None = None, limit: int = Query(100, le=500)):
    stmt = select(RDPApplication).options(
        selectinload(RDPApplication.fee_plan),
        selectinload(RDPApplication.reviews).selectinload(RDPApplicationReview.reviewer),
        selectinload(RDPApplication.scholarship_request),
        selectinload(RDPApplication.invoices),
    ).order_by(RDPApplication.submitted_at.desc()).limit(limit)
    if status: stmt = stmt.where(RDPApplication.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((RDPApplication.full_name.like(like)) | (RDPApplication.email.like(like)) | (RDPApplication.application_ref.like(like)))
    rows = (await db.execute(stmt)).scalars().all()
    return [_application_admin_out(a) for a in rows]


@router.get("/admin/applications/{application_id}", response_model=RDPApplicationAdminOut)
async def admin_application(application_id: int, db: DbDep, _: AdminDep):
    return _application_admin_out(await _load_application(db, application_id))


@router.put("/admin/applications/{application_id}/review", response_model=RDPReviewOut)
async def upsert_review(application_id: int, payload: RDPReviewUpsert, db: DbDep, admin: AdminDep):
    await _load_application(db, application_id)
    total = payload.motivation_score + payload.development_need_score + payload.programme_fit_score + payload.commitment_score + payload.potential_score
    review = (await db.execute(select(RDPApplicationReview).where(
        RDPApplicationReview.application_id == application_id, RDPApplicationReview.reviewer_id == admin.id
    ))).scalar_one_or_none()
    if not review:
        review = RDPApplicationReview(application_id=application_id, reviewer_id=admin.id)
        db.add(review)
    for field, value in payload.model_dump().items(): setattr(review, field, value)
    review.total_score = total
    app = await db.get(RDPApplication, application_id)
    if app and app.status == "submitted": app.status = "screening"
    await db.commit(); await db.refresh(review)
    review.reviewer = admin
    return _review_out(review)


@router.post("/admin/applications/{application_id}/decision", response_model=RDPDecisionResponse)
async def decide_application(application_id: int, payload: RDPDecisionRequest, db: DbDep, _: AdminDep):
    a = await _load_application(db, application_id)
    payment_token = None
    if payload.decision == "accepted":
        if not payload.fee_plan_id:
            raise HTTPException(422, "A fee plan is required for accepted applicants")
        fee_plan = await db.get(RDPFeePlan, payload.fee_plan_id)
        if not fee_plan or fee_plan.cohort_id != a.cohort_id or not fee_plan.is_active:
            raise HTTPException(422, "Invalid fee plan")
        occupied = int((await db.execute(select(func.count()).select_from(RDPApplication).where(
            RDPApplication.cohort_id == a.cohort_id,
            RDPApplication.status.in_(["accepted", "payment_due", "enrolled"]),
            RDPApplication.id != a.id,
        ))).scalar_one())
        if occupied >= a.cohort.capacity:
            raise HTTPException(409, "Cohort capacity has been reached; use waitlist instead")
        a.fee_plan_id = fee_plan.id
        deadline = payload.acceptance_deadline
        if deadline and deadline.tzinfo is not None:
            deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)
        a.acceptance_deadline = deadline
        a.status = "payment_due"
        payment_token = issue_token()
        a.payment_token_hash = token_hash(payment_token)
        await create_invoices(db, a, fee_plan)
    else:
        a.status = payload.decision
    a.admission_notes = payload.admission_notes
    a.decided_at = datetime.utcnow()
    await db.commit()
    email_sent = await send_decision_email(a, payment_token=payment_token)
    payment_link = f"{settings.FRONTEND_URL.rstrip('/')}/payment?ref={a.application_ref}&token={payment_token}" if payment_token else None
    return RDPDecisionResponse(status=a.status, payment_link=payment_link, email_sent=email_sent)


@router.put("/admin/scholarships/{scholarship_id}", response_model=RDPScholarshipOut)
async def decide_scholarship(scholarship_id: int, payload: RDPScholarshipDecisionRequest, db: DbDep, _: AdminDep):
    obj = (await db.execute(
        select(RDPScholarshipRequest).where(RDPScholarshipRequest.id == scholarship_id)
        .options(selectinload(RDPScholarshipRequest.application).selectinload(RDPApplication.fee_plan),
                 selectinload(RDPScholarshipRequest.application).selectinload(RDPApplication.invoices))
    )).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "Scholarship request not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    application = obj.application
    if application.fee_plan and application.invoices:
        try:
            await recalculate_unpaid_invoices(db, application, application.fee_plan)
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(409, str(exc)) from exc
    await db.commit(); await db.refresh(obj)
    status_text = obj.status.replace("_", " ")
    award_line = ""
    if obj.status in {"approved", "partially_approved"} and obj.approved_amount_subunit and obj.approved_currency:
        award_line = f"<p><strong>Approved support:</strong> {obj.approved_currency} {obj.approved_amount_subunit / 100:,.2f}</p>"
    await send_email(
        to=application.email,
        subject="Scholarship/support request update — Ungozu R & D",
        html_body=(
            f"<p>Hello {application.full_name},</p>"
            f"<p>Your programme support request is now <strong>{status_text}</strong>.</p>"
            f"{award_line}"
            + (f"<p>{obj.admin_notes}</p>" if obj.admin_notes else "")
        ),
        plain_body=f"Your Ungozu R & D support request is now {status_text}.",
    )
    return obj


@router.get("/admin/enrollments", response_model=list[RDPEnrollmentOut])
async def admin_enrollments(db: DbDep, _: AdminDep, cohort_id: int = 1):
    rows = (await db.execute(select(RDPEnrollment).where(RDPEnrollment.cohort_id == cohort_id).options(selectinload(RDPEnrollment.user)))).scalars().all()
    return [RDPEnrollmentOut(
        id=e.id, cohort_id=e.cohort_id, application_id=e.application_id, user_id=e.user_id,
        status=e.status, enrolled_at=e.enrolled_at, completion_status=e.completion_status,
        certificate_number=e.certificate_number, full_name=e.user.full_name if e.user else None,
        email=e.user.email if e.user else None,
    ) for e in rows]


@router.get("/admin/payments", response_model=list[RDPPaymentOut])
async def admin_payments(db: DbDep, _: AdminDep, limit: int = Query(100, le=500)):
    rows = (await db.execute(select(RDPPayment).order_by(RDPPayment.created_at.desc()).limit(limit))).scalars().all()
    return rows


# ── Admin: payment gateway management ───────────────────────────────────────

async def _provider_config_out(db: AsyncSession, provider: str, environment: str) -> RDPPaymentProviderConfigOut:
    provider = provider.lower()
    environment = environment.lower()
    default = DEFAULTS[provider]
    row = (await db.execute(select(RDPPaymentProviderConfig).where(
        RDPPaymentProviderConfig.provider == provider,
        RDPPaymentProviderConfig.environment == environment,
    ))).scalar_one_or_none()
    source = "database" if row else "unconfigured"
    display_name = str(default["display_name"])
    enabled = False
    public_key = None
    credentials: dict = {}
    currencies = list(default["currencies"])
    priority = int(default["priority"])
    last_tested_at = None
    last_test_status = None
    last_test_message = None
    if row:
        display_name = row.display_name
        enabled = row.is_enabled
        public_key = row.public_key
        try:
            credentials = decrypt_credentials(row.encrypted_credentials)
        except Exception:
            credentials = {}
            last_test_status = "error"
            last_test_message = "Stored credentials cannot be decrypted with the current encryption key"
        try:
            parsed = json.loads(row.supported_currencies_json or "[]")
            currencies = [str(x).upper() for x in parsed if len(str(x)) == 3] or currencies
        except json.JSONDecodeError:
            pass
        priority = row.priority
        last_tested_at = row.last_tested_at
        last_test_status = last_test_status or row.last_test_status
        last_test_message = last_test_message or row.last_test_message
    else:
        fallback = await load_gateway_config(db, provider, environment, include_disabled=True)
        if fallback and fallback.source == "environment":
            source = "environment"
            display_name = fallback.display_name
            enabled = fallback.is_enabled
            public_key = fallback.public_key
            credentials = {"secret_key": fallback.secret_key, "webhook_secret": fallback.webhook_secret}
            currencies = fallback.supported_currencies
            priority = fallback.priority
    webhook_url, callback_url = _provider_urls(provider)
    return RDPPaymentProviderConfigOut(
        provider=provider,
        environment=environment,
        display_name=display_name,
        is_enabled=enabled,
        public_key=public_key,
        secret_configured=bool(credentials.get("secret_key")),
        webhook_secret_configured=(provider == "paystack" and bool(credentials.get("secret_key"))) or bool(credentials.get("webhook_secret")),
        secret_key_masked=mask_secret(str(credentials.get("secret_key") or "")),
        webhook_secret_masked=(
            mask_secret(str(credentials.get("secret_key") or ""))
            if provider == "paystack"
            else mask_secret(str(credentials.get("webhook_secret") or ""))
        ),
        supported_currencies=currencies,
        priority=priority,
        last_tested_at=last_tested_at,
        last_test_status=last_test_status,
        last_test_message=last_test_message,
        source=source,
        webhook_url=webhook_url,
        callback_url=callback_url,
    )


@router.get("/admin/payment-settings", response_model=RDPPaymentPlatformSettingsOut)
async def admin_payment_settings(db: DbDep, _: AdminDep):
    obj = await get_platform_settings(db)
    await db.commit()
    return RDPPaymentPlatformSettingsOut(
        active_environment=obj.active_environment,
        allow_provider_selection=obj.allow_provider_selection,
    )


@router.put("/admin/payment-settings", response_model=RDPPaymentPlatformSettingsOut)
async def admin_update_payment_settings(payload: RDPPaymentPlatformSettingsUpdate, db: DbDep, admin: AdminDep):
    obj = await get_platform_settings(db)
    changing_to_live = obj.active_environment != "live" and payload.active_environment == "live"
    if changing_to_live:
        if not payload.current_password or not verify_password(payload.current_password, admin.hashed_password):
            raise HTTPException(403, "Your current administrator password is required to activate live payments")
        usable = []
        for provider in SUPPORTED_PROVIDERS:
            cfg = await load_gateway_config(db, provider, "live")
            if cfg and cfg.secret_key:
                usable.append(provider)
        if not usable:
            raise HTTPException(400, "Configure and enable at least one LIVE payment provider before activating live payments")
    previous = obj.active_environment
    obj.active_environment = payload.active_environment
    obj.allow_provider_selection = payload.allow_provider_selection
    await _payment_audit(
        db, admin.id, "payment_platform_settings_updated",
        environment=payload.active_environment,
        details={"previous_environment": previous, "allow_provider_selection": payload.allow_provider_selection},
    )
    await db.commit()
    return RDPPaymentPlatformSettingsOut(
        active_environment=obj.active_environment,
        allow_provider_selection=obj.allow_provider_selection,
    )


@router.get("/admin/payment-providers", response_model=list[RDPPaymentProviderConfigOut])
async def admin_payment_providers(db: DbDep, _: AdminDep):
    result = []
    for environment in ("test", "live"):
        for provider in ("paystack", "stripe"):
            result.append(await _provider_config_out(db, provider, environment))
    return result


@router.put("/admin/payment-providers/{provider}/{environment}", response_model=RDPPaymentProviderConfigOut)
async def admin_save_payment_provider(
    provider: str,
    environment: str,
    payload: RDPPaymentProviderConfigUpdate,
    db: DbDep,
    admin: AdminDep,
):
    provider = provider.lower()
    environment = environment.lower()
    if provider not in SUPPORTED_PROVIDERS or environment not in {"test", "live"}:
        raise HTTPException(404, "Payment provider configuration not found")
    if environment == "live":
        if not payload.current_password or not verify_password(payload.current_password, admin.hashed_password):
            raise HTTPException(403, "Your current administrator password is required to change live payment settings")

    row = (await db.execute(select(RDPPaymentProviderConfig).where(
        RDPPaymentProviderConfig.provider == provider,
        RDPPaymentProviderConfig.environment == environment,
    ))).scalar_one_or_none()
    existing_cfg = await load_gateway_config(db, provider, environment, include_disabled=True)
    existing_credentials: dict[str, str] = {}
    if row and row.encrypted_credentials:
        try:
            existing_credentials = {k: str(v) for k, v in decrypt_credentials(row.encrypted_credentials).items()}
        except Exception as exc:
            if not payload.secret_key:
                raise HTTPException(409, "Existing credentials cannot be decrypted. Enter a new secret key to rotate them.") from exc
    elif existing_cfg and existing_cfg.source == "environment":
        existing_credentials = {
            "secret_key": existing_cfg.secret_key,
            "webhook_secret": existing_cfg.webhook_secret or "",
        }

    secret_key = (payload.secret_key or "").strip() or existing_credentials.get("secret_key", "")
    webhook_secret = (payload.webhook_secret or "").strip() or existing_credentials.get("webhook_secret", "")
    public_key = payload.public_key if payload.public_key is not None else (row.public_key if row else (existing_cfg.public_key if existing_cfg else None))
    try:
        validate_key_environment(provider, environment, secret_key or None, public_key)
    except PaymentGatewayError as exc:
        raise HTTPException(400, str(exc)) from exc

    if not row:
        row = RDPPaymentProviderConfig(
            provider=provider,
            environment=environment,
            display_name=payload.display_name or str(DEFAULTS[provider]["display_name"]),
            is_enabled=False,
            supported_currencies_json=json.dumps(DEFAULTS[provider]["currencies"]),
            priority=int(DEFAULTS[provider]["priority"]),
        )
        db.add(row)
        await db.flush()

    if payload.display_name is not None:
        row.display_name = payload.display_name.strip()
    if payload.is_enabled is not None:
        row.is_enabled = payload.is_enabled
    if payload.public_key is not None:
        row.public_key = payload.public_key.strip() or None
    if payload.supported_currencies is not None:
        row.supported_currencies_json = json.dumps(payload.supported_currencies)
    if payload.priority is not None:
        row.priority = payload.priority
    if row.is_enabled and not secret_key:
        raise HTTPException(400, "A secret key is required before this provider can be enabled")
    if provider == "stripe" and row.is_enabled and not webhook_secret:
        # Hosted checkout callbacks still work, but warn clearly through health/UI rather than block setup.
        row.last_test_message = "Stripe is enabled, but its webhook signing secret is not configured"
    row.public_key = row.public_key or public_key
    row.encrypted_credentials = encrypt_credentials({
        "secret_key": secret_key,
        "webhook_secret": webhook_secret,
    }) if (secret_key or webhook_secret) else None
    row.configured_by_user_id = admin.id

    rotated = bool(payload.secret_key or payload.webhook_secret)
    await _payment_audit(
        db, admin.id, "payment_credentials_rotated" if rotated else "payment_provider_updated",
        provider=provider, environment=environment,
        details={
            "enabled": row.is_enabled,
            "currencies": json.loads(row.supported_currencies_json or "[]"),
            "priority": row.priority,
            "credentials_changed": rotated,
        },
    )
    await db.commit()
    return await _provider_config_out(db, provider, environment)


@router.post("/admin/payment-providers/{provider}/{environment}/test", response_model=RDPPaymentProviderTestOut)
async def admin_test_payment_provider(provider: str, environment: str, db: DbDep, admin: AdminDep):
    provider = provider.lower()
    environment = environment.lower()
    if provider not in SUPPORTED_PROVIDERS or environment not in {"test", "live"}:
        raise HTTPException(404, "Payment provider configuration not found")
    config = await load_gateway_config(db, provider, environment, include_disabled=True)
    if not config or not config.secret_key:
        raise HTTPException(400, "Secret key is not configured")
    tested_at = datetime.utcnow()
    success = False
    try:
        message = await test_gateway_connection(config)
        success = True
    except PaymentGatewayError as exc:
        message = str(exc)

    row = (await db.execute(select(RDPPaymentProviderConfig).where(
        RDPPaymentProviderConfig.provider == provider,
        RDPPaymentProviderConfig.environment == environment,
    ))).scalar_one_or_none()
    if row:
        row.last_tested_at = tested_at
        row.last_test_status = "success" if success else "failed"
        row.last_test_message = message[:500]
    await _payment_audit(
        db, admin.id, "payment_provider_connection_test",
        provider=provider, environment=environment,
        details={"success": success, "message": message[:500]},
    )
    await db.commit()
    return RDPPaymentProviderTestOut(
        provider=provider, environment=environment, success=success,
        message=message, tested_at=tested_at,
    )


@router.get("/admin/payment-health", response_model=RDPPaymentHealthOut)
async def admin_payment_health(db: DbDep, _: AdminDep, environment: str | None = None):
    platform = await get_platform_settings(db)
    selected_environment = (environment or platform.active_environment or "test").lower()
    if selected_environment not in {"test", "live"}:
        raise HTTPException(400, "Environment must be test or live")
    items: list[RDPPaymentProviderHealthOut] = []
    for provider in ("paystack", "stripe"):
        cfg_out = await _provider_config_out(db, provider, selected_environment)
        last_webhook = (await db.execute(select(RDPPaymentWebhookEvent).where(
            RDPPaymentWebhookEvent.provider == provider,
            RDPPaymentWebhookEvent.environment == selected_environment,
        ).order_by(RDPPaymentWebhookEvent.created_at.desc()).limit(1))).scalar_one_or_none()
        successful = int((await db.execute(select(func.count()).select_from(RDPPayment).where(
            RDPPayment.provider == provider,
            RDPPayment.environment == selected_environment,
            RDPPayment.status == "success",
        ))).scalar_one())
        failed = int((await db.execute(select(func.count()).select_from(RDPPayment).where(
            RDPPayment.provider == provider,
            RDPPayment.environment == selected_environment,
            RDPPayment.status.in_(["failed", "initialization_failed", "verification_failed", "abandoned"]),
        ))).scalar_one())
        items.append(RDPPaymentProviderHealthOut(
            provider=provider,
            environment=selected_environment,
            display_name=cfg_out.display_name,
            enabled=cfg_out.is_enabled,
            configured=cfg_out.secret_configured,
            connection_status=cfg_out.last_test_status,
            last_tested_at=cfg_out.last_tested_at,
            last_test_message=cfg_out.last_test_message,
            last_webhook_at=last_webhook.created_at if last_webhook else None,
            webhook_status=last_webhook.status if last_webhook else None,
            successful_payments=successful,
            failed_payments=failed,
        ))
    return RDPPaymentHealthOut(active_environment=platform.active_environment, providers=items)


@router.get("/admin/payment-audit", response_model=list[RDPPaymentAuditOut])
async def admin_payment_audit(db: DbDep, _: AdminDep, limit: int = Query(50, ge=1, le=250)):
    rows = (await db.execute(select(RDPPaymentAuditLog).order_by(
        RDPPaymentAuditLog.created_at.desc()
    ).limit(limit))).scalars().all()
    return rows


@router.get("/admin/enrollments/{enrollment_id}", response_model=RDPEnrollmentAdminDetail)
async def admin_enrollment_detail(enrollment_id: int, db: DbDep, _: AdminDep):
    stmt = select(RDPEnrollment).where(RDPEnrollment.id == enrollment_id).options(
        selectinload(RDPEnrollment.user),
        selectinload(RDPEnrollment.cohort).selectinload(RDPCohort.fee_plans),
        selectinload(RDPEnrollment.application).selectinload(RDPApplication.invoices),
        selectinload(RDPEnrollment.development_plan),
    )
    e = (await db.execute(stmt)).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "Enrollment not found")
    checkins = (await db.execute(select(RDPMonthlyCheckIn).where(
        RDPMonthlyCheckIn.enrollment_id == e.id
    ).order_by(RDPMonthlyCheckIn.month_number))).scalars().all()
    enrollment_out = RDPEnrollmentOut(
        id=e.id, cohort_id=e.cohort_id, application_id=e.application_id, user_id=e.user_id,
        status=e.status, enrolled_at=e.enrolled_at, completion_status=e.completion_status,
        certificate_number=e.certificate_number, full_name=e.user.full_name if e.user else None,
        email=e.user.email if e.user else None,
    )
    return RDPEnrollmentAdminDetail(
        enrollment=enrollment_out, cohort=RDPCohortOut.model_validate(e.cohort),
        development_plan=RDPDevelopmentPlanOut.model_validate(e.development_plan) if e.development_plan else None,
        checkins=[RDPCheckInOut.model_validate(c) for c in checkins],
        invoices=[RDPInvoiceOut.model_validate(i) for i in e.application.invoices],
    )


@router.put("/admin/enrollments/{enrollment_id}/development-plan", response_model=RDPDevelopmentPlanOut)
async def admin_review_development_plan(enrollment_id: int, payload: RDPAdminDevelopmentPlanUpdate, db: DbDep, _: AdminDep):
    plan = (await db.execute(select(RDPDevelopmentPlan).where(
        RDPDevelopmentPlan.enrollment_id == enrollment_id
    ))).scalar_one_or_none()
    if not plan:
        raise HTTPException(404, "Development plan not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    if payload.mentor_notes is not None and payload.status is None:
        plan.status = "reviewed"
    await db.commit(); await db.refresh(plan)
    return plan


@router.put("/admin/checkins/{checkin_id}", response_model=RDPCheckInOut)
async def admin_review_checkin(checkin_id: int, payload: RDPAdminCheckInUpdate, db: DbDep, _: AdminDep):
    obj = await db.get(RDPMonthlyCheckIn, checkin_id)
    if not obj:
        raise HTTPException(404, "Check-in not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    if payload.mentor_feedback is not None or payload.status == "reviewed":
        obj.reviewed_at = datetime.utcnow()
        if payload.status is None:
            obj.status = "reviewed"
    await db.commit(); await db.refresh(obj)
    return obj


@router.get("/admin/events", response_model=list[RDPEventAdminOut])
async def admin_events(db: DbDep, _: AdminDep, cohort_id: int = 1):
    return list((await db.execute(select(RDPProgrammeEvent).where(
        RDPProgrammeEvent.cohort_id == cohort_id
    ).order_by(RDPProgrammeEvent.starts_at))).scalars().all())


@router.post("/admin/events", response_model=RDPEventAdminOut, status_code=201)
async def admin_create_event(payload: RDPEventCreate, db: DbDep, _: AdminDep, cohort_id: int = 1):
    if not await db.get(RDPCohort, cohort_id):
        raise HTTPException(404, "Cohort not found")
    obj = RDPProgrammeEvent(cohort_id=cohort_id, **payload.model_dump())
    db.add(obj); await db.commit(); await db.refresh(obj)
    return obj


@router.put("/admin/events/{event_id}", response_model=RDPEventAdminOut)
async def admin_update_event(event_id: int, payload: RDPEventCreate, db: DbDep, _: AdminDep):
    obj = await db.get(RDPProgrammeEvent, event_id)
    if not obj:
        raise HTTPException(404, "Event not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    await db.commit(); await db.refresh(obj)
    return obj


@router.delete("/admin/events/{event_id}", status_code=204)
async def admin_delete_event(event_id: int, db: DbDep, _: AdminDep):
    obj = await db.get(RDPProgrammeEvent, event_id)
    if not obj:
        raise HTTPException(404, "Event not found")
    await db.delete(obj); await db.commit()


@router.get("/admin/resources", response_model=list[RDPResourceAdminOut])
async def admin_resources(db: DbDep, _: AdminDep, cohort_id: int = 1):
    return list((await db.execute(select(RDPResource).where(
        RDPResource.cohort_id == cohort_id
    ).order_by(RDPResource.month_number, RDPResource.sort_order, RDPResource.title))).scalars().all())


@router.post("/admin/resources", response_model=RDPResourceAdminOut, status_code=201)
async def admin_create_resource(payload: RDPResourceCreate, db: DbDep, _: AdminDep, cohort_id: int = 1):
    if not await db.get(RDPCohort, cohort_id):
        raise HTTPException(404, "Cohort not found")
    obj = RDPResource(cohort_id=cohort_id, **payload.model_dump())
    db.add(obj); await db.commit(); await db.refresh(obj)
    return obj


@router.put("/admin/resources/{resource_id}", response_model=RDPResourceAdminOut)
async def admin_update_resource(resource_id: int, payload: RDPResourceCreate, db: DbDep, _: AdminDep):
    obj = await db.get(RDPResource, resource_id)
    if not obj:
        raise HTTPException(404, "Resource not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    await db.commit(); await db.refresh(obj)
    return obj


@router.delete("/admin/resources/{resource_id}", status_code=204)
async def admin_delete_resource(resource_id: int, db: DbDep, _: AdminDep):
    obj = await db.get(RDPResource, resource_id)
    if not obj:
        raise HTTPException(404, "Resource not found")
    await db.delete(obj); await db.commit()


# ── Participant portal ───────────────────────────────────────────────────────

async def _enrollment_for_user(db: AsyncSession, user_id: int) -> RDPEnrollment:
    stmt = select(RDPEnrollment).where(RDPEnrollment.user_id == user_id).options(
        selectinload(RDPEnrollment.cohort).selectinload(RDPCohort.fee_plans),
        selectinload(RDPEnrollment.application).selectinload(RDPApplication.invoices),
        selectinload(RDPEnrollment.development_plan),
        selectinload(RDPEnrollment.user),
    )
    e = (await db.execute(stmt)).scalars().first()
    if not e: raise HTTPException(404, "Programme enrolment not found")
    return e


@router.get("/portal/dashboard", response_model=RDPPortalDashboard)
async def portal_dashboard(db: DbDep, mentee: MenteeDep):
    e = await _enrollment_for_user(db, mentee.id)
    checkins = (await db.execute(select(RDPMonthlyCheckIn).where(RDPMonthlyCheckIn.enrollment_id == e.id).order_by(RDPMonthlyCheckIn.month_number))).scalars().all()
    events = (await db.execute(select(RDPProgrammeEvent).where(
        RDPProgrammeEvent.cohort_id == e.cohort_id, RDPProgrammeEvent.is_published.is_(True), RDPProgrammeEvent.starts_at >= datetime.utcnow()
    ).order_by(RDPProgrammeEvent.starts_at).limit(8))).scalars().all()
    resources = (await db.execute(select(RDPResource).where(
        RDPResource.cohort_id == e.cohort_id, RDPResource.is_published.is_(True)
    ).order_by(RDPResource.month_number, RDPResource.sort_order))).scalars().all()
    enrollment_out = RDPEnrollmentOut(
        id=e.id, cohort_id=e.cohort_id, application_id=e.application_id, user_id=e.user_id,
        status=e.status, enrolled_at=e.enrolled_at, completion_status=e.completion_status,
        certificate_number=e.certificate_number, full_name=mentee.full_name, email=mentee.email,
    )
    return RDPPortalDashboard(
        enrollment=enrollment_out, cohort=RDPCohortOut.model_validate(e.cohort),
        development_plan=RDPDevelopmentPlanOut.model_validate(e.development_plan) if e.development_plan else None,
        checkins=[RDPCheckInOut.model_validate(c) for c in checkins],
        upcoming_events=[RDPEventOut.model_validate(x) for x in events],
        resources=[RDPResourceOut.model_validate(x) for x in resources],
        invoices=[RDPInvoiceOut.model_validate(x) for x in e.application.invoices],
    )


@router.put("/portal/development-plan", response_model=RDPDevelopmentPlanOut)
async def update_development_plan(payload: RDPDevelopmentPlanUpdate, db: DbDep, mentee: MenteeDep):
    e = await _enrollment_for_user(db, mentee.id)
    plan = e.development_plan
    if not plan:
        plan = RDPDevelopmentPlan(enrollment_id=e.id, status="draft"); db.add(plan)
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(plan, k, v)
    await db.commit(); await db.refresh(plan)
    return plan


@router.put("/portal/checkins/{month_number}", response_model=RDPCheckInOut)
async def update_checkin(month_number: int, payload: RDPCheckInUpdate, db: DbDep, mentee: MenteeDep):
    if month_number < 1 or month_number > 12: raise HTTPException(422, "Month must be 1–12")
    e = await _enrollment_for_user(db, mentee.id)
    obj = (await db.execute(select(RDPMonthlyCheckIn).where(
        RDPMonthlyCheckIn.enrollment_id == e.id, RDPMonthlyCheckIn.month_number == month_number
    ))).scalar_one_or_none()
    if not obj:
        obj = RDPMonthlyCheckIn(enrollment_id=e.id, month_number=month_number, status="draft"); db.add(obj)
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(obj, k, v)
    if obj.status == "submitted" and not obj.submitted_at: obj.submitted_at = datetime.utcnow()
    await db.commit(); await db.refresh(obj)
    return obj


# ── Participant password setup ───────────────────────────────────────────────

class PasswordResetRequestPayload(BaseModel):
    email: str


@router.post("/public/password-reset/request")
@limiter.limit(RateLimits.PASSWORD_RESET)
async def request_participant_password_reset(request: Request, payload: PasswordResetRequestPayload, db: DbDep):
    user = (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none()
    if user and user.is_active:
        enrollment = (await db.execute(select(RDPEnrollment.id).where(RDPEnrollment.user_id == user.id))).scalar_one_or_none()
        if enrollment is not None:
            token = create_password_reset_token(user.email)
            link = f"{settings.FRONTEND_URL.rstrip('/')}/set-password?token={token}"
            await send_email(
                to=user.email,
                subject="Ungozu R & D participant portal password reset",
                html_body=f"<p>Hello {user.full_name or user.email},</p><p><a href=\"{link}\">Reset your participant portal password</a></p>",
                plain_body=f"Reset your participant portal password: {link}",
            )
    return {"message": "If that participant account exists, a password reset link has been sent."}


class PasswordSetPayload(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/public/set-password")
async def set_participant_password(payload: PasswordSetPayload, db: DbDep):
    try:
        email = decode_password_reset_token(payload.token)
    except JWTError as exc:
        raise HTTPException(400, "Invalid or expired password setup link") from exc
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(400, "Invalid or expired password setup link")
    enrollment = (await db.execute(select(RDPEnrollment.id).where(RDPEnrollment.user_id == user.id))).scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(400, "Invalid or expired password setup link")
    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    return {"message": "Password set successfully"}
