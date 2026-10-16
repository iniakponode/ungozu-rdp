"""Financial validation for RDP fee quotations."""

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class QuoteInstallmentTerm:
    sequence_number: int
    amount_subunit: int
    due_date: date


def validate_fee_quote_terms(
    *,
    gross_total_subunit: int,
    scholarship_subunit: int,
    payable_total_subunit: int,
    installments: Sequence[QuoteInstallmentTerm],
) -> tuple[QuoteInstallmentTerm, ...]:
    """Validate a proposed financial agreement and its instalments."""

    if gross_total_subunit < 0:
        raise ValueError("Gross fee cannot be negative")

    if scholarship_subunit < 0:
        raise ValueError("Scholarship cannot be negative")

    if scholarship_subunit > gross_total_subunit:
        raise ValueError("Scholarship exceeds the gross fee")

    expected_payable = gross_total_subunit - scholarship_subunit

    if payable_total_subunit != expected_payable:
        raise ValueError(
            "Payable amount does not match gross fee minus scholarship"
        )

    ordered = tuple(
        sorted(installments, key=lambda item: item.sequence_number)
    )

    if payable_total_subunit == 0:
        if ordered:
            raise ValueError(
                "Fully funded quotes must not contain payable instalments"
            )
        return ordered

    if not ordered:
        raise ValueError(
            "A payable quote requires at least one instalment"
        )

    expected_sequences = list(range(1, len(ordered) + 1))
    actual_sequences = [
        item.sequence_number for item in ordered
    ]

    if actual_sequences != expected_sequences:
        raise ValueError(
            "Instalment sequences must be consecutive from 1"
        )

    if any(item.amount_subunit <= 0 for item in ordered):
        raise ValueError(
            "Payable instalments must have positive amounts"
        )

    if any(
        not isinstance(item.due_date, date)
        for item in ordered
    ):
        raise ValueError(
            "Every payable instalment requires a valid due date"
        )

    due_dates = [item.due_date for item in ordered]

    if due_dates != sorted(due_dates):
        raise ValueError(
            "Instalment due dates must be chronological"
        )

    if sum(item.amount_subunit for item in ordered) != payable_total_subunit:
        raise ValueError(
            "Instalments do not equal the agreed payable amount"
        )

    return ordered
