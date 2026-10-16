from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rdp import RDPApplication, RDPInvoice
from app.models.rdp_fee_quotes import RDPFeeQuote

from app.services.rdp import issue_token, token_hash
from app.services.rdp_fee_quote_acceptance import (
    accept_fee_quote,
)
from app.services.rdp_fee_quote_invoicing import (
    create_invoices_from_accepted_quote,
)


async def accept_quote_and_prepare_payment(
    db: AsyncSession,
    *,
    application_id: int,
    quote_id: int,
    accepted_at: datetime | None = None,
) -> tuple[RDPFeeQuote, list[RDPInvoice], str]:
    """Accept a quotation and prepare payment atomically.

    The caller MUST:
    - Verify participant ownership and authorisation.
    - Never trust a client-supplied acceptance timestamp.
    - Commit before returning or communicating the payment token.
    - Roll back the transaction if any operation fails.

    This service does not commit, send email, or call gateways.
    """

    # The acceptance service locks and validates the
    # application, quotation, expiry and financial terms.
    quote = await accept_fee_quote(
        db,
        application_id=application_id,
        quote_id=quote_id,
        accepted_at=accepted_at,
    )

    # Generate invoices from the frozen accepted quotation.
    # No amounts or due dates are recalculated.
    invoices = await create_invoices_from_accepted_quote(
        db,
        application_id=application_id,
        quote_id=quote.id,
    )

    if not invoices:
        raise ValueError(
            "Accepted quotation produced no payable invoices"
        )

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

    if application.fee_plan_id != quote.fee_plan_id:
        raise ValueError(
            "Application fee plan differs from accepted quotation"
        )

    if application.payment_token_hash is not None:
        raise ValueError(
            "A payment token already exists for this application"
        )

    # The quotation expiry deadline governs acceptance.
    # Once accepted, payment is governed by invoice due dates.
    # Do not let the expired offer deadline block later
    # instalment payments.
    application.acceptance_deadline = None

    payment_token = issue_token()

    application.payment_token_hash = token_hash(
        payment_token
    )

    application.status = "payment_due"

    await db.flush()

    return quote, invoices, payment_token
