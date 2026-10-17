"""Pure validation of an applicant's package/fee-plan preference.

Preferences do NOT reserve package capacity or establish payable terms.
"""
from __future__ import annotations


def validate_package_preference(*, cohort_id: int, programme_version_id: int | None,
                                requested_package_id: int | None, requested_fee_plan_id: int | None,
                                package, plan) -> None:
    if programme_version_id is None:
        raise ValueError("Package preferences are only available for current programme cohorts")
    if requested_package_id is None or requested_fee_plan_id is None:
        raise ValueError("Choose a mentoring package and a payment plan")
    if package is None or plan is None:
        raise ValueError("The selected package or payment plan is no longer available")
    if (package.id != requested_package_id or
            package.programme_version_id != programme_version_id or
            not package.is_active or
            plan.id != requested_fee_plan_id or
            plan.cohort_id != cohort_id or
            plan.package_id != requested_package_id or
            not plan.is_active):
        raise ValueError("The selected package and payment plan are not available for this cohort")
