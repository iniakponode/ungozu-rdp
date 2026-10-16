from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rdp import RDPApplication, RDPInvoice
from app.models.rdp_fee_quotes import (
    RDPFeeQuote,
    RDPFeeQuoteInstallment,
)
from app.services.rdp_fee_quote_rules import (
    QuoteInstallmentTerm,
    validate_fee_quote_terms,
)


async def create_invoices_from_accepted_quote(
    db: AsyncSession,
    *,
    application_id: int,
    quote_id: int,
) -> list[RDPInvoice]:
    """Create invoices from frozen accepted quotation terms.

    The caller owns the transaction. This function never commits.
    """

    # Maintain the same application-first lock ordering
    # as quotation issuance and acceptance.
    application = (
        await db.execute(
            select(RDPApplication)
            .where(RDPApplication.id == application_id)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if application is None:
        raise ValueError("Application not found")

    if application.status != "quote_offered":
        raise ValueError(
            "Application is not awaiting quotation acceptance"
        )

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

    if quote.status != "accepted":
        raise ValueError(
            "Only an accepted quotation can generate invoices"
        )

    if quote.accepted_at is None:
        raise ValueError(
            "Accepted quotation has no acceptance timestamp"
        )

    if quote.package_id is None:
        raise ValueError(
            "Programme Builder quotation has no package"
        )

    if application.fee_plan_id != quote.fee_plan_id:
        raise ValueError(
            "Application fee plan differs from accepted quotation"
        )

    # Do not create a zero-value payment obligation.
    # Fully sponsored enrolments require a separate workflow.
    if quote.payable_total_subunit <= 0:
        raise ValueError(
            "Fully sponsored quotations require separate handling"
        )

    # Fail closed instead of reusing, replacing or modifying
    # invoices that may already belong to a payment workflow.
    existing = (
        await db.execute(
            select(RDPInvoice.id)
            .where(RDPInvoice.application_id == application_id)
            .with_for_update()
        )
    ).first()

    if existing is not None:
        raise ValueError(
            "Invoices already exist for this application"
        )

    lines = (
        await db.execute(
            select(RDPFeeQuoteInstallment)
            .where(RDPFeeQuoteInstallment.fee_quote_id == quote.id)
            .order_by(RDPFeeQuoteInstallment.sequence_number)
            .with_for_update()
        )
    ).scalars().all()

    # Revalidate the frozen terms immediately before invoicing.
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

    if any(
        line.amount_subunit <= 0 or line.due_date is None
        for line in lines
    ):
        raise ValueError(
            "Payment instalments require positive amounts "
            "and explicit due dates"
        )

    invoices = []

    for index, line in enumerate(lines):
        invoice = RDPInvoice(
            application_id=application.id,
            fee_plan_id=quote.fee_plan_id,
            sequence=line.sequence_number,
            amount_subunit=line.amount_subunit,
            currency=quote.currency,
            due_date=line.due_date,
            status="pending" if index == 0 else "scheduled",
        )

        db.add(invoice)
        invoices.append(invoice)

    await db.flush()

    return invoices
