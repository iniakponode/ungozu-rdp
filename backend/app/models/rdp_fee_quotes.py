"""Versioned fee quotes and agreed instalment terms."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class RDPFeeQuote(Base, TimestampMixin):
    __tablename__ = "rdp_fee_quotes"

    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "quote_number",
            name="uq_rdp_fee_quote_application_number",
        ),
        CheckConstraint(
            "gross_total_subunit >= 0",
            name="ck_rdp_quote_gross_nonnegative",
        ),
        CheckConstraint(
            "scholarship_subunit >= 0",
            name="ck_rdp_quote_scholarship_nonnegative",
        ),
        CheckConstraint(
            "payable_total_subunit = gross_total_subunit - scholarship_subunit",
            name="ck_rdp_quote_total_consistent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rdp_applications.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    fee_plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rdp_fee_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    package_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("rdp_packages.id", ondelete="RESTRICT"),
        nullable=True,
    )

    quote_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    package_name_snapshot: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    entitlements_snapshot_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    currency: Mapped[str] = mapped_column(
        String(3), nullable=False
    )

    gross_total_subunit: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    scholarship_subunit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    payable_total_subunit: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="offered"
    )

    effective_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    installments: Mapped[list["RDPFeeQuoteInstallment"]] = relationship(
        "RDPFeeQuoteInstallment",
        back_populates="quote",
        lazy="selectin",
    )


class RDPFeeQuoteInstallment(Base, TimestampMixin):
    __tablename__ = "rdp_fee_quote_installments"

    __table_args__ = (
        UniqueConstraint(
            "fee_quote_id",
            "sequence_number",
            name="uq_rdp_fee_quote_installment_sequence",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_rdp_quote_line_sequence_positive",
        ),
        CheckConstraint(
            "amount_subunit >= 0",
            name="ck_rdp_quote_line_amount_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    fee_quote_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rdp_fee_quotes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    amount_subunit: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    due_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    quote: Mapped["RDPFeeQuote"] = relationship(
        "RDPFeeQuote",
        back_populates="installments",
    )
