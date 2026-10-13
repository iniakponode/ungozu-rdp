"""Configurable curriculum models for RDP programmes."""

from sqlalchemy import (
    Boolean, ForeignKey, Integer, String,
    Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class RDPCurriculumModule(Base, TimestampMixin):
    __tablename__ = "rdp_curriculum_modules"

    __table_args__ = (
        UniqueConstraint(
            "programme_version_id",
            "sequence_number",
            name="uq_rdp_curriculum_module_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    programme_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "rdp_programme_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    learning_outcomes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    completion_criteria: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )

    programme_version = relationship(
        "RDPProgrammeVersion"
    )

    items: Mapped[list["RDPCurriculumItem"]] = relationship(
        "RDPCurriculumItem",
        back_populates="module",
        lazy="selectin",
    )


class RDPCurriculumItem(Base, TimestampMixin):
    __tablename__ = "rdp_curriculum_items"

    __table_args__ = (
        UniqueConstraint(
            "module_id",
            "sequence_number",
            name="uq_rdp_curriculum_item_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    module_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "rdp_curriculum_modules.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    item_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="lesson"
    )

    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    estimated_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    completion_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )

    module: Mapped["RDPCurriculumModule"] = relationship(
        "RDPCurriculumModule",
        back_populates="items",
    )
