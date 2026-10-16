"""Business logic for the Ungozu R & D Researcher Development Programme."""
from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_password_reset_token
from app.auth.password import hash_password
from app.core.config import settings
from app.models.rdp import (
    RDPApplication, RDPEnrollment, RDPFeePlan, RDPInvoice, RDPPayment, RDPCohort,
    RDPDevelopmentPlan,
)
from app.models.user import User
from app.services.email import send_email


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token() -> str:
    return secrets.token_urlsafe(32)


def application_reference() -> str:
    return f"URD-{datetime.utcnow():%Y}-{secrets.token_hex(4).upper()}"


def payment_reference(invoice_id: int) -> str:
    return f"URDPAY-{invoice_id}-{secrets.token_hex(5)}"


async def get_public_cohort(db: AsyncSession, slug: str | None = None) -> RDPCohort | None:
    """Resolve a public cohort without leaking draft Programme Builder versions.

    Historical legacy published cohorts remain supported. If no slug is supplied,
    prefer an open/current application cohort, otherwise an upcoming published
    cohort, rather than assuming cohort ID 1.
    """
    from app.api.v1.endpoints.rdp_catalogue import published_cohorts, accepts

    cohorts = await published_cohorts(db)
    if slug:
        return next((c for c in cohorts if c.slug == slug), None)
    return next((c for c in cohorts if accepts(c)), None) or (cohorts[0] if cohorts else None)


async def get_application_by_ref(db: AsyncSession, ref: str) -> RDPApplication | None:
    return (await db.execute(select(RDPApplication).where(RDPApplication.application_ref == ref))).scalar_one_or_none()


def verify_access_token(application: RDPApplication, token: str, *, payment: bool = False) -> bool:
    stored = application.payment_token_hash if payment else application.access_token_hash
    return bool(stored and secrets.compare_digest(stored, token_hash(token)))


async def create_invoices(db: AsyncSession, application: RDPApplication, fee_plan: RDPFeePlan) -> list[RDPInvoice]:
    existing = (await db.execute(select(RDPInvoice).where(RDPInvoice.application_id == application.id))).scalars().all()
    if existing:
        return list(existing)
    due = date.today()
    invoices: list[RDPInvoice] = []
    scholarship_amount = 0
    sr = application.scholarship_request
    if sr and sr.status in {"approved", "partially_approved"} and sr.approved_currency == fee_plan.currency:
        scholarship_amount = max(0, int(sr.approved_amount_subunit or 0))
    total_due = max(0, fee_plan.total_amount_subunit - scholarship_amount)
    count = max(1, fee_plan.installment_count)
    base_amount = total_due // count
    for seq in range(1, count + 1):
        # Final invoice absorbs any integer-subunit remainder.
        amount = base_amount if seq < count else total_due - base_amount * (count - 1)
        inv = RDPInvoice(
            application_id=application.id,
            fee_plan_id=fee_plan.id,
            sequence=seq,
            amount_subunit=amount,
            currency=fee_plan.currency,
            due_date=due,
            status="pending" if seq == 1 else "scheduled",
        )
        db.add(inv)
        invoices.append(inv)
        due = due + timedelta(days=30)
    await db.flush()
    return invoices


async def recalculate_unpaid_invoices(db: AsyncSession, application: RDPApplication, fee_plan: RDPFeePlan) -> list[RDPInvoice]:
    """Recalculate invoice amounts after a scholarship decision, before payment starts.

    To keep Paystack references trustworthy, scholarship amounts cannot change once any
    payment attempt has been created for the application's invoices.
    """
    invoices = (await db.execute(
        select(RDPInvoice).where(RDPInvoice.application_id == application.id).order_by(RDPInvoice.sequence)
    )).scalars().all()
    if not invoices:
        return await create_invoices(db, application, fee_plan)
    payment_count = int((await db.execute(
        select(func.count()).select_from(RDPPayment).join(RDPInvoice).where(RDPInvoice.application_id == application.id)
    )).scalar_one())
    if payment_count:
        raise ValueError("Scholarship amount cannot be changed after payment processing has started")
    scholarship_amount = 0
    sr = application.scholarship_request
    if sr and sr.status in {"approved", "partially_approved"} and sr.approved_currency == fee_plan.currency:
        scholarship_amount = max(0, int(sr.approved_amount_subunit or 0))
    total_due = max(0, fee_plan.total_amount_subunit - scholarship_amount)
    count = len(invoices)
    base_amount = total_due // max(1, count)
    for idx, invoice in enumerate(invoices, start=1):
        invoice.amount_subunit = base_amount if idx < count else total_due - base_amount * (count - 1)
        invoice.currency = fee_plan.currency
        invoice.status = "pending" if idx == 1 else "scheduled"
        invoice.paid_at = None
    await db.flush()
    return list(invoices)


async def send_application_confirmation(application: RDPApplication, access_token: str, *, cohort_label: str | None = None) -> bool:
    status_link = f"{settings.FRONTEND_URL.rstrip('/')}/status?ref={application.application_ref}&token={access_token}"
    from html import escape
    cohort_text = f" for {escape(cohort_label)}" if cohort_label else ""
    return await send_email(
        to=application.email,
        subject=f"Application received — {application.application_ref}",
        html_body=(
            f"<p>Hello {application.full_name},</p>"
            f"<p>We have received your application{cohort_text} to the Ungozu R & D researcher-development programme.</p>"
            f"<p><strong>Application reference:</strong> {application.application_ref}</p>"
            f'<p><a href="{status_link}">View application status</a></p>'
            "<p>Keep this link private; it provides access to your application status.</p>"
        ),
        plain_body=(
            f"Hello {application.full_name},\n\nApplication received.\n"
            f"Reference: {application.application_ref}\nStatus link: {status_link}\n"
        ),
    )


async def send_decision_email(application: RDPApplication, *, payment_token: str | None = None, cohort_label: str | None = None) -> bool:
    from html import escape
    cohort_text = escape(cohort_label) if cohort_label else "your selected cohort"
    if application.status in {"accepted", "payment_due"} and payment_token:
        link = f"{settings.FRONTEND_URL.rstrip('/')}/payment?ref={application.application_ref}&token={payment_token}"
        subject = "Admission offer — Ungozu R & D Researcher Development Programme"
        body = (
            f"<p>Hello {application.full_name},</p>"
            f"<p>Congratulations. You have been offered a place in {cohort_text} of the Ungozu R & D Researcher Development Programme.</p>"
            f'<p><a href="{link}">Review your fee plan and make payment</a></p>'
        )
    elif application.status == "quote_offered":
        subject = (
            "Admission offer - Ungozu R & D "
            "Researcher Development Programme"
        )
        body = (
            f"<p>Hello {application.full_name},</p>"
            f"<p>Congratulations. Your application for {cohort_text} has been approved "
            "and a programme fee quotation has been issued.</p>"
            "<p>You will receive separate instructions for reviewing "
            "and accepting your quotation.</p>"
            "<p>Please do not make payment until you have accepted "
            "the quotation and received official payment instructions.</p>"
        )
    elif application.status == "shortlisted":
        subject = "Application shortlisted — Ungozu R & D Researcher Development Programme"
        body = f"<p>Hello {application.full_name},</p><p>Your application has been shortlisted for the next stage.</p>"
    elif application.status == "waitlisted":
        subject = "Application waitlist update — Ungozu R & D Researcher Development Programme"
        body = f"<p>Hello {application.full_name},</p><p>Your application has been placed on the waitlist. We will contact you if a place becomes available.</p>"
    else:
        subject = "Application outcome — Ungozu R & D Researcher Development Programme"
        body = f"<p>Hello {application.full_name},</p><p>Thank you for your interest. We are unable to offer you a place in this cohort.</p>"
    if application.admission_notes:
        body += f"<p>{application.admission_notes}</p>"
    return await send_email(to=application.email, subject=subject, html_body=body)


async def ensure_enrollment_after_payment(db: AsyncSession, payment: RDPPayment) -> RDPEnrollment:
    invoice = payment.invoice
    application = invoice.application
    existing = (await db.execute(select(RDPEnrollment).where(RDPEnrollment.application_id == application.id))).scalar_one_or_none()
    if existing:
        return existing

    user = (await db.execute(select(User).where(User.email == application.email))).scalar_one_or_none()
    created_user = user is None
    if not user:
        user = User(
            email=application.email,
            full_name=application.full_name,
            role="programme_mentee",
            is_active=True,
            is_admin=False,
            hashed_password=hash_password(secrets.token_urlsafe(32)),
        )
        db.add(user)
        await db.flush()
    # Existing users keep their current role. RDP portal access is granted by the
    # enrollment record, so student/admin privileges are never overwritten.

    enrollment = RDPEnrollment(
        cohort_id=application.cohort_id,
        application_id=application.id,
        user_id=user.id,
        status="active_payment_plan",
        completion_status="in_progress",
    )
    db.add(enrollment)
    await db.flush()
    db.add(RDPDevelopmentPlan(enrollment_id=enrollment.id, status="draft"))
    application.status = "enrolled"

    if created_user:
        reset_token = create_password_reset_token(user.email)
        setup_link = f"{settings.FRONTEND_URL.rstrip('/')}/set-password?token={reset_token}"
        html = (
            f"<p>Hello {application.full_name},</p>"
            "<p>Your programme enrolment is active.</p>"
            f'<p><a href="{setup_link}">Set your participant portal password</a></p>'
        )
        plain = f"Your enrolment is active. Set your password: {setup_link}"
    else:
        login_link = f"{settings.FRONTEND_URL.rstrip('/')}/login"
        html = (
            f"<p>Hello {application.full_name},</p>"
            "<p>Your existing website account now has access to the Ungozu R & D participant portal.</p>"
            f'<p><a href="{login_link}">Sign in with your existing account password</a></p>'
            "<p>If you cannot remember the password, use the participant portal password-reset option.</p>"
        )
        plain = f"Your programme enrolment is active. Sign in with your existing account: {login_link}"
    await send_email(
        to=user.email,
        subject="Your Ungozu R & D participant portal",
        html_body=html,
        plain_body=plain,
    )
    return enrollment


async def send_payment_confirmation(payment: RDPPayment) -> bool:
    invoice = payment.invoice
    application = invoice.application
    amount = payment.amount_subunit / 100
    return await send_email(
        to=application.email,
        subject=f"Payment confirmed — {application.application_ref}",
        html_body=(
            f"<p>Hello {application.full_name},</p>"
            f"<p>We have verified your programme payment of <strong>{payment.currency} {amount:,.2f}</strong>.</p>"
            f"<p><strong>Payment reference:</strong> {payment.reference}</p>"
            f"<p><strong>Instalment:</strong> {invoice.sequence}</p>"
            "<p>Your participant portal and programme records will reflect the verified payment.</p>"
        ),
        plain_body=(
            f"Hello {application.full_name},\n\nPayment confirmed: {payment.currency} {amount:,.2f}\n"
            f"Reference: {payment.reference}\nInstalment: {invoice.sequence}\n"
        ),
    )


async def payment_revenue_stats(db: AsyncSession, cohort_id: int | None = None) -> tuple[int, dict[str, int]]:
    """Return verified payment count and totals grouped by currency."""
    stmt = (
        select(RDPPayment.currency, func.coalesce(func.sum(RDPPayment.amount_subunit), 0), func.count(RDPPayment.id))
        .join(RDPInvoice, RDPPayment.invoice_id == RDPInvoice.id)
        .join(RDPApplication, RDPInvoice.application_id == RDPApplication.id)
        .where(RDPPayment.status == "success")
    )
    if cohort_id is not None:
        stmt = stmt.where(RDPApplication.cohort_id == cohort_id)
    rows = (await db.execute(stmt.group_by(RDPPayment.currency))).all()
    count = 0
    totals: dict[str, int] = {}
    for currency, amount, c in rows:
        count += int(c)
        totals[str(currency).upper()] = int(amount)
    return count, totals
