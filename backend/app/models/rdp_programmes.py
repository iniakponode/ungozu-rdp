"""Configurable programme definitions for Ungozu RDP CMS."""

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class RDPProgramme(Base, TimestampMixin):
    __tablename__ = "rdp_programmes"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    versions: Mapped[list["RDPProgrammeVersion"]] = relationship(
        "RDPProgrammeVersion",
        back_populates="programme",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RDPProgrammeVersion(Base, TimestampMixin):
    __tablename__ = "rdp_programme_versions"
    __table_args__ = (
        UniqueConstraint(
            "programme_id", "version_number",
            name="uq_rdp_programme_version"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    programme_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rdp_programmes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    overview: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    duration_value: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    duration_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="months"
    )
    learning_outcomes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    programme: Mapped["RDPProgramme"] = relationship(
        "RDPProgramme",
        back_populates="versions",
    )
