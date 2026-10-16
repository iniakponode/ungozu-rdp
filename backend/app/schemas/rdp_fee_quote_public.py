from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
)


class RDPQuotationAccessRequest(BaseModel):
    """Applicant credentials supplied in a POST request body."""

    model_config = ConfigDict(extra="forbid")

    application_ref: str = Field(
        min_length=1,
        max_length=100,
    )

    # SecretStr prevents normal model representations
    # from displaying the raw applicant access token.
    access_token: SecretStr = Field(
        min_length=20,
        max_length=512,
    )


class RDPQuotationInstallmentOut(BaseModel):
    sequence_number: int
    amount_subunit: int
    due_date: date | None
    description: str | None = None


class RDPQuotationReviewResponse(BaseModel):
    """Financial terms shown before applicant acceptance."""

    application_ref: str
    quote_id: int
    quote_number: int

    status: str
    package_name: str | None = None
    entitlements_snapshot_json: str | None = None

    currency: str
    gross_total_subunit: int
    scholarship_subunit: int
    payable_total_subunit: int

    effective_date: date | None = None
    expires_at: datetime | None = None
    accepted_at: datetime | None = None

    installments: list[RDPQuotationInstallmentOut]


class RDPQuotationInvoiceOut(BaseModel):
    sequence: int
    amount_subunit: int
    currency: str
    due_date: date | None
    status: str


class RDPQuotationAcceptResponse(BaseModel):
    """Returned only after successful transaction commit."""

    application_ref: str
    quote_id: int
    quote_status: Literal["accepted"]
    application_status: Literal["payment_due"]

    # This is the newly issued payment credential.
    # The endpoint must never return it before commit.
    payment_token: str

    invoices: list[RDPQuotationInvoiceOut]
