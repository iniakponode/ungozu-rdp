"""Read-only plan for safely duplicating cohort fee schedules.

This function never writes data; the admin route commits the full draft atomically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from app.services.rdp_fee_schedule_rules import FeeScheduleLine, validate_fee_plan_schedule


@dataclass(frozen=True)
class PlannedFeePlan:
    source_id: int
    target_package_id: int
    code: str
    region: str
    name: str
    currency: str
    total_amount_subunit: int
    description: str | None
    sort_order: int
    installments: tuple[FeeScheduleLine, ...]
    installment_descriptions: tuple[str | None, ...]


def plan_cohort_fee_clone(
    fee_plans: Iterable[Any],
    installments_by_plan: Mapping[int, Iterable[Any]],
    source_packages_by_id: Mapping[int, Any],
    target_packages_by_code: Mapping[str, Any],
) -> tuple[PlannedFeePlan, ...]:
    """Validate all source amounts and map packages by stable code, never by ID.

    Caller must ensure the target version is published and all objects came from
    the intended source/target versions. Fail completely on incomplete mappings.
    """
    plans = list(fee_plans)
    if not plans:
        raise ValueError("Source cohort has no fee plans to clone")

    output: list[PlannedFeePlan] = []
    codes: set[str] = set()
    for plan in plans:
        if plan.code in codes:
            raise ValueError(f"Duplicate source fee-plan code: {plan.code}")
        codes.add(plan.code)
        if plan.package_id is None:
            raise ValueError(f"Fee plan '{plan.code}' uses a legacy/unlinked package; cannot clone safely")
        source_package = source_packages_by_id.get(plan.package_id)
        if not source_package:
            raise ValueError(f"Source package missing for fee plan '{plan.code}'")
        target_package = target_packages_by_code.get(source_package.code)
        if not target_package or not target_package.is_active:
            raise ValueError(
                f"Target version needs an active package with code '{source_package.code}' "
                f"(required by fee plan '{plan.code}')"
            )
        lines = list(installments_by_plan.get(plan.id, []))
        validated = validate_fee_plan_schedule(
            total_amount_subunit=plan.total_amount_subunit,
            installment_count=plan.installment_count,
            lines=[FeeScheduleLine(x.sequence_number, x.amount_subunit, x.due_offset_days) for x in lines],
        )
        by_sequence = {x.sequence_number: x for x in lines}
        output.append(PlannedFeePlan(
            source_id=plan.id,
            target_package_id=target_package.id,
            code=plan.code,
            region=plan.region,
            name=plan.name,
            currency=plan.currency,
            total_amount_subunit=plan.total_amount_subunit,
            description=plan.description,
            sort_order=plan.sort_order,
            installments=validated,
            installment_descriptions=tuple(by_sequence[x.sequence_number].description for x in validated),
        ))
    return tuple(output)
