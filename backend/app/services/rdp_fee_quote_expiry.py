from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rdp import (
    RDPApplication,
    RDPCohort,
    RDPInvoice,
)
from app.models.rdp_fee_quotes import RDPFeeQuote
from app.services.rdp_fee_quote_lifecycle import (
    validate_quote_transition,
)


def _as_utc(value: datetime) -> datetime:
    """Treat stored naive timestamps as UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


async def expire_offered_quote(
    db: AsyncSession,
    *,
    quote_id: int,
    now: datetime | None = None,
) -> bool:
    """Expire one unaccepted quotation and release its seat.

    Returns True when the quotation is newly expired.
    Returns False when no expiry transition is needed.

    Caller owns commit and rollback.
    """

    current_time = _as_utc(
        now if now is not None
        else datetime.now(timezone.utc)
    )

    # Identify the application without acquiring a row lock.
    # Subsequent locking follows the same ordering used
    # by administrator admissions:
    #
    # cohort -> application -> quotation.
    application_id = (
        await db.execute(
            select(RDPFeeQuote.application_id)
            .where(RDPFeeQuote.id == quote_id)
        )
    ).scalar_one_or_none()

    if application_id is None:
        raise ValueError("Quotation not found")

    cohort_id_query = (
        select(RDPApplication.cohort_id)
        .where(RDPApplication.id == application_id)
        .scalar_subquery()
    )

    locked_cohort = (
        await db.execute(
            select(RDPCohort.id)
            .where(RDPCohort.id == cohort_id_query)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if locked_cohort is None:
        raise ValueError("Quotation cohort not found")

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
                RDPFeeQuote.application_id == application.id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    if quote is None:
        raise ValueError("Quotation ownership changed")

    # Already accepted, expired or superseded quotations
    # must not be modified by the expiry process.
    if quote.status != "offered":
        return False

    if quote.expires_at is None:
        return False

    if current_time < _as_utc(quote.expires_at):
        return False

    # Do not accidentally expire an older quotation when
    # the application has received a newer offer.
    latest_quote_id = (
        await db.execute(
            select(RDPFeeQuote.id)
            .where(
                RDPFeeQuote.application_id == application.id
            )
            .order_by(
                RDPFeeQuote.quote_number.desc(),
                RDPFeeQuote.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one()

    if latest_quote_id != quote.id:
        raise ValueError(
            "Cannot release a place using an older quotation"
        )

    if application.status != "quote_offered":
        raise ValueError(
            "Application is not awaiting quotation acceptance"
        )

    if application.fee_plan_id != quote.fee_plan_id:
        raise ValueError(
            "Application and quotation fee plans differ"
        )

    if application.payment_token_hash is not None:
        raise ValueError(
            "Cannot release a place with an active payment token"
        )

    existing_invoice = (
        await db.execute(
            select(RDPInvoice.id)
            .where(
                RDPInvoice.application_id == application.id
            )
            .limit(1)
        )
    ).first()

    if existing_invoice is not None:
        raise ValueError(
            "Cannot expire an offer with existing invoices"
        )

    validate_quote_transition(
        current_status=quote.status,
        new_status="expired",
        now=current_time,
        expires_at=quote.expires_at,
    )

    # Both changes must be committed together.
    # This preserves the original quotation record,
    # including its immutable financial terms.
    quote.status = "expired"

    # This status is excluded from the existing
    # cohort and package occupancy calculations.
    application.status = "offer_expired"

    await db.flush()

    return True
