"""Validation rules for configurable RDP instalment schedules."""

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class FeeScheduleLine:
    sequence_number: int
    amount_subunit: int
    due_offset_days: int


def validate_fee_plan_schedule(
    *,
    total_amount_subunit: int,
    installment_count: int,
    lines: Sequence[FeeScheduleLine],
) -> tuple[FeeScheduleLine, ...]:
    """Validate a gross fee schedule before scholarships or discounts."""

    if total_amount_subunit <= 0:
        raise ValueError("Fee plan total must be positive")

    if installment_count < 1:
        raise ValueError("Instalment count must be at least one")

    ordered = tuple(
        sorted(lines, key=lambda x: x.sequence_number)
    )

    if len(ordered) != installment_count:
        raise ValueError(
            "Schedule entry count does not match fee plan"
        )

    expected = list(range(1, installment_count + 1))
    actual = [x.sequence_number for x in ordered]

    if actual != expected:
        raise ValueError(
            "Instalment sequence must be consecutive from 1"
        )

    if any(x.amount_subunit <= 0 for x in ordered):
        raise ValueError(
            "Each instalment amount must be positive"
        )

    offsets = [x.due_offset_days for x in ordered]

    if any(offset < 0 for offset in offsets):
        raise ValueError(
            "Due-date offsets cannot be negative"
        )

    if offsets != sorted(offsets):
        raise ValueError(
            "Instalment due dates must be chronological"
        )

    if sum(x.amount_subunit for x in ordered) != total_amount_subunit:
        raise ValueError(
            "Instalment amounts do not equal the fee plan total"
        )

    return ordered
