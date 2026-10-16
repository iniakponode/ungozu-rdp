"""Transactional issuance of versioned RDP fee quotations."""

import json
from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rdp import (
    RDPApplication,
    RDPFeePlan,
    RDPInvoice,
    RDPScholarshipRequest,
)
from app.models.rdp_packages import (
    RDPPackage,
    RDPPackageEntitlement,
)
from app.models.rdp_fee_schedules import RDPFeePlanInstallment
from app.models.rdp_fee_quotes import (
    RDPFeeQuote,
    RDPFeeQuoteInstallment,
)
from app.services.rdp_fee_schedule_rules import (
    FeeScheduleLine,
    validate_fee_plan_schedule,
)
from app.services.rdp_fee_quote_rules import (
    QuoteInstallmentTerm,
    validate_fee_quote_terms,
)
from app.services.rdp_fee_quote_lifecycle import (
    validate_quote_transition,
)


from app.services.rdp_quote_eligibility import validate_quote_issuance_eligibility


async def issue_fee_quote(
    db: AsyncSession,
    *,
    application_id: int,
    fee_plan_id: int,
    effective_date: date,
    expires_at: datetime | None = None,
    adjusted_amounts_subunit: Sequence[int] | None = None,
) -> RDPFeeQuote:
    """Issue a validated quote without committing the transaction.

    The caller must commit or roll back the same transaction.
    All competing quote writers must lock the application row.
    """

    application = (
        await db.execute(
            select(RDPApplication)
            .where(RDPApplication.id == application_id)
            .with_for_update()
        )
    ).scalar_one_or_none()

    if application is None:
        raise ValueError("Application not found")

    if application.status == "enrolled":
        raise ValueError("Cannot issue a new quote for an enrolled applicant")

    fee_plan = await db.get(RDPFeePlan, fee_plan_id)

    if (
        fee_plan is None
        or fee_plan.cohort_id != application.cohort_id
        or not fee_plan.is_active
    ):
        raise ValueError("Invalid or inactive fee plan")

    validate_quote_issuance_eligibility(
        application_status=application.status,
        application_fee_plan_id=application.fee_plan_id,
        proposed_fee_plan_id=fee_plan.id,
    )


    invoice_count = (
        await db.execute(
            select(func.count())
            .select_from(RDPInvoice)
            .where(RDPInvoice.application_id == application_id)
        )
    ).scalar_one()

    if invoice_count:
        raise ValueError(
            "Existing invoices must not be replaced by a new quote"
        )

    previous_quotes = (
        await db.execute(
            select(RDPFeeQuote)
            .where(RDPFeeQuote.application_id == application_id)
            .order_by(RDPFeeQuote.quote_number)
            .with_for_update()
        )
    ).scalars().all()

    if any(
        quote.status not in {"expired", "superseded"}
        for quote in previous_quotes
    ):
        raise ValueError(
            "An existing quotation must be resolved before reissuing"
        )

    next_quote_number = (
        max((q.quote_number for q in previous_quotes), default=0) + 1
    )

    scholarship = (
        await db.execute(
            select(RDPScholarshipRequest)
            .where(
                RDPScholarshipRequest.application_id == application_id
            )
            .with_for_update()
        )
    ).scalar_one_or_none()

    scholarship_amount = 0

    if (
        scholarship is not None
        and scholarship.status in {"approved", "partially_approved"}
    ):
        scholarship_amount = int(
            scholarship.approved_amount_subunit or 0
        )

        if (
            scholarship_amount > 0
            and scholarship.approved_currency != fee_plan.currency
        ):
            raise ValueError(
                "Approved scholarship currency differs from fee plan"
            )

    schedules = (
        await db.execute(
            select(RDPFeePlanInstallment)
            .where(RDPFeePlanInstallment.fee_plan_id == fee_plan_id)
            .order_by(RDPFeePlanInstallment.sequence_number)
        )
    ).scalars().all()

    gross_lines = validate_fee_plan_schedule(
        total_amount_subunit=fee_plan.total_amount_subunit,
        installment_count=fee_plan.installment_count,
        lines=[
            FeeScheduleLine(
                sequence_number=line.sequence_number,
                amount_subunit=line.amount_subunit,
                due_offset_days=line.due_offset_days,
            )
            for line in schedules
        ],
    )

    if adjusted_amounts_subunit is None:
        if scholarship_amount:
            raise ValueError(
                "Scholarship allocation across instalments is required"
            )
        amounts = [line.amount_subunit for line in gross_lines]
    else:
        amounts = list(adjusted_amounts_subunit)

    if len(amounts) != len(gross_lines):
        raise ValueError("Adjusted instalment count is incorrect")

    for gross_line, amount in zip(gross_lines, amounts):
        if (
            type(amount) is not int
            or amount < 0
            or amount > gross_line.amount_subunit
        ):
            raise ValueError(
                "Adjusted instalment amount is outside allowed bounds"
            )

    payable_total = fee_plan.total_amount_subunit - scholarship_amount

    quote_lines = [
        QuoteInstallmentTerm(
            sequence_number=number,
            amount_subunit=amount,
            due_date=effective_date + timedelta(
                days=gross_line.due_offset_days
            ),
        )
        for number, (gross_line, amount) in enumerate(
            (
                (line, amount)
                for line, amount in zip(gross_lines, amounts)
                if amount > 0
            ),
            start=1,
        )
    ]

    validated_lines = validate_fee_quote_terms(
        gross_total_subunit=fee_plan.total_amount_subunit,
        scholarship_subunit=scholarship_amount,
        payable_total_subunit=payable_total,
        installments=quote_lines,
    )

    validate_quote_transition(
        current_status="draft",
        new_status="offered",
        now=datetime.utcnow(),
        expires_at=expires_at,
    )

    package_name = fee_plan.name
    entitlements = []

    if fee_plan.package_id is not None:
        package = await db.get(RDPPackage, fee_plan.package_id)

        if package is None or not package.is_active:
            raise ValueError("Linked programme package is inactive")

        package_name = package.name

        records = (
            await db.execute(
                select(RDPPackageEntitlement)
                .where(
                    RDPPackageEntitlement.package_id == package.id
                )
                .order_by(
                    RDPPackageEntitlement.sort_order,
                    RDPPackageEntitlement.id,
                )
            )
        ).scalars().all()

        entitlements = [
            {
                "code": item.code,
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "limit_value": item.limit_value,
                "limit_unit": item.limit_unit,
                "period": item.period,
                "description": item.description,
                "is_included": item.is_included,
            }
            for item in records
        ]

    quote = RDPFeeQuote(
        application_id=application.id,
        fee_plan_id=fee_plan.id,
        package_id=fee_plan.package_id,
        quote_number=next_quote_number,
        package_name_snapshot=package_name,
        entitlements_snapshot_json=json.dumps(
            {"schema_version": 1, "items": entitlements},
            sort_keys=True,
        ),
        currency=fee_plan.currency,
        gross_total_subunit=fee_plan.total_amount_subunit,
        scholarship_subunit=scholarship_amount,
        payable_total_subunit=payable_total,
        status="draft",
        effective_date=effective_date,
        expires_at=expires_at,
    )

    db.add(quote)
    await db.flush()

    for line in validated_lines:
        db.add(
            RDPFeeQuoteInstallment(
                fee_quote_id=quote.id,
                sequence_number=line.sequence_number,
                amount_subunit=line.amount_subunit,
                due_date=line.due_date,
            )
        )

    await db.flush()

    # Seal the complete quotation only after its instalments exist.
    quote.status = "offered"
    await db.flush()
    return quote
