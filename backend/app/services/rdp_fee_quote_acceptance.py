"""Transactional acceptance of RDP financial quotations."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rdp import RDPApplication, RDPFeePlan, RDPInvoice, RDPPayment
from app.models.rdp_fee_quotes import (
    RDPFeeQuote,
    RDPFeeQuoteInstallment,
)
from app.services.rdp_fee_quote_rules import (
    QuoteInstallmentTerm,
    validate_fee_quote_terms,
)
from app.services.rdp_quote_eligibility import validate_quote_acceptance_eligibility
from app.services.rdp_fee_quote_lifecycle import (
    validate_quote_transition,
)


async def accept_fee_quote(
    db: AsyncSession,
    *,
    application_id: int,
    quote_id: int,
    accepted_at: datetime | None = None,
) -> RDPFeeQuote:
    """Accept an issued quotation without committing the transaction."""

    now = accepted_at or datetime.now(timezone.utc)

    if now.tzinfo is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    # Lock the application first, consistent with issuance.
    application = (
        await db.execute(
            select(RDPApplication)
            .where(RDPApplication.id == application_id)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if application is None:
        raise ValueError("Application not found")

    quote = (
        await db.execute(
            select(RDPFeeQuote)
            .where(
                RDPFeeQuote.id == quote_id,
                RDPFeeQuote.application_id == application_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    if quote is None:
        raise ValueError("Quotation not found for this application")

    fee_plan = await db.get(RDPFeePlan, quote.fee_plan_id)

    if fee_plan is None or application.cohort_id != fee_plan.cohort_id:
        raise ValueError("Quotation belongs to another cohort")

    validate_quote_acceptance_eligibility(
        application_status=application.status,
        application_fee_plan_id=application.fee_plan_id,
        quote_fee_plan_id=quote.fee_plan_id,
        quote_status=quote.status,
    )

    validate_quote_transition(
        current_status=quote.status,
        new_status="accepted",
        now=now,
        expires_at=quote.expires_at,
    )

    # Existing invoices or payment attempts must not be
    # silently associated with a newly accepted quotation.
    existing_invoice_count = (
        await db.execute(
            select(func.count())
            .select_from(RDPInvoice)
            .where(RDPInvoice.application_id == application_id)
        )
    ).scalar_one()

    if existing_invoice_count:
        raise ValueError(
            "Existing invoices require legacy payment handling"
        )

    existing_payment_count = (
        await db.execute(
            select(func.count())
            .select_from(RDPPayment)
            .join(RDPInvoice)
            .where(RDPInvoice.application_id == application_id)
        )
    ).scalar_one()

    if existing_payment_count:
        raise ValueError(
            "Quotation cannot be accepted after payment processing"
        )

    other_accepted = (
        await db.execute(
            select(RDPFeeQuote.id)
            .where(
                RDPFeeQuote.application_id == application_id,
                RDPFeeQuote.status == "accepted",
                RDPFeeQuote.id != quote_id,
            )
            .with_for_update()
        )
    ).first()

    if other_accepted:
        raise ValueError(
            "Another quotation has already been accepted"
        )

    lines = (
        await db.execute(
            select(RDPFeeQuoteInstallment)
            .where(RDPFeeQuoteInstallment.fee_quote_id == quote.id)
            .order_by(RDPFeeQuoteInstallment.sequence_number)
            .with_for_update()
        )
    ).scalars().all()

    validate_fee_quote_terms(
        gross_total_subunit=quote.gross_total_subunit,
        scholarship_subunit=quote.scholarship_subunit,
        payable_total_subunit=quote.payable_total_subunit,
        installments=[
            QuoteInstallmentTerm(
                sequence_number=line.sequence_number,
                amount_subunit=line.amount_subunit,
                due_date=line.due_date,
            )
            for line in lines
        ],
    )

    quote.status = "accepted"
    quote.accepted_at = now

    await db.flush()

    return quote
