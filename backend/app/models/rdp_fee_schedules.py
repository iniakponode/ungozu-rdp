"""Configurable instalment schedules for RDP fee plans."""

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class RDPFeePlanInstallment(Base, TimestampMixin):
    __tablename__ = "rdp_fee_plan_installments"

    __table_args__ = (
        UniqueConstraint(
            "fee_plan_id",
            "sequence_number",
            name="uq_rdp_fee_plan_installment_sequence",
        ),
        CheckConstraint(
            "sequence_number >= 1",
            name="ck_rdp_installment_sequence_positive",
        ),
        CheckConstraint(
            "amount_subunit >= 0",
            name="ck_rdp_installment_amount_nonnegative",
        ),
        CheckConstraint(
            "due_offset_days >= 0",
            name="ck_rdp_installment_due_offset_nonnegative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    fee_plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "rdp_fee_plans.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    amount_subunit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    due_offset_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    fee_plan = relationship("RDPFeePlan")
