"""Eligibility rules for legacy and Programme Builder admissions."""

from typing import Literal

QUOTE_OFFERED_STATUS = "quote_offered"

BillingFlow = Literal["legacy", "quote"]


def resolve_billing_flow(
    *,
    programme_version_id: int | None,
    package_id: int | None,
) -> BillingFlow:
    """Determine the admission billing workflow."""

    if programme_version_id is None:
        if package_id is not None:
            raise ValueError(
                "A package-linked fee plan requires a versioned programme"
            )
        return "legacy"

    if package_id is None:
        raise ValueError(
            "A versioned programme requires a configured package"
        )

    return "quote"


def validate_quote_acceptance_eligibility(
    *,
    application_status: str,
    application_fee_plan_id: int | None,
    quote_fee_plan_id: int,
    quote_status: str,
) -> None:
    """Check eligibility to accept a financial quotation."""

    if application_status != QUOTE_OFFERED_STATUS:
        raise ValueError(
            "Application has not been approved for quotation acceptance"
        )

    if (
        application_fee_plan_id is None
        or application_fee_plan_id != quote_fee_plan_id
    ):
        raise ValueError(
            "Quotation does not match the application's approved fee plan"
        )

    if quote_status != "offered":
        raise ValueError(
            "Only an offered quotation can be accepted"
        )


def validate_quote_issuance_eligibility(
    *,
    application_status: str,
    application_fee_plan_id: int | None,
    proposed_fee_plan_id: int,
) -> None:
    """Require administrative approval before issuing a quotation."""

    if application_status != QUOTE_OFFERED_STATUS:
        raise ValueError(
            "Application has not been approved for quotation issuance"
        )

    if (
        application_fee_plan_id is None
        or application_fee_plan_id != proposed_fee_plan_id
    ):
        raise ValueError(
            "Proposed quotation does not match the approved fee plan"
        )


def validate_admission_billing_configuration(
    *,
    cohort_id: int,
    cohort_programme_version_id: int | None,
    fee_plan_cohort_id: int,
    fee_plan_package_id: int | None,
    fee_plan_is_active: bool,
    package_programme_version_id: int | None,
    package_is_active: bool | None,
) -> BillingFlow:
    """Validate fee-plan and package relationships before admission."""

    if fee_plan_cohort_id != cohort_id:
        raise ValueError(
            "Fee plan does not belong to the applicant's cohort"
        )

    if not fee_plan_is_active:
        raise ValueError(
            "Inactive fee plan cannot be used for admission"
        )

    flow = resolve_billing_flow(
        programme_version_id=cohort_programme_version_id,
        package_id=fee_plan_package_id,
    )

    if flow == "quote":
        if package_programme_version_id != cohort_programme_version_id:
            raise ValueError(
                "Package does not belong to the cohort's programme version"
            )

        if package_is_active is not True:
            raise ValueError(
                "Missing or inactive package cannot be used for admission"
            )

    return flow
