"""Configurable programme packages and participant entitlements."""

from sqlalchemy import (
    SmallInteger,
    Boolean, ForeignKey, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class RDPPackage(Base, TimestampMixin):
    __tablename__ = "rdp_packages"

    __table_args__ = (
        UniqueConstraint(
            "programme_version_id",
            "code",
            name="uq_rdp_package_version_code",
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

    code: Mapped[str] = mapped_column(
        String(80), nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Optional limit for this package within each cohort.
    # NULL means the cohort's overall capacity is the only limit.
    capacity: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        default=None,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    programme_version = relationship(
        "RDPProgrammeVersion"
    )

    entitlements: Mapped[list["RDPPackageEntitlement"]] = relationship(
        "RDPPackageEntitlement",
        back_populates="package",
        lazy="selectin",
    )


class RDPPackageEntitlement(Base, TimestampMixin):
    __tablename__ = "rdp_package_entitlements"

    __table_args__ = (
        UniqueConstraint(
            "package_id",
            "code",
            name="uq_rdp_package_entitlement_code",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )

    package_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "rdp_packages.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(80), nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    quantity: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    unit: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )

    limit_value: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    limit_unit: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )

    period: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    is_included: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    package: Mapped["RDPPackage"] = relationship(
        "RDPPackage",
        back_populates="entitlements",
    )
