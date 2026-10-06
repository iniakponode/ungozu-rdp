"""
SQLAlchemy declarative base and common column mixin.
All models should inherit from Base (via their module) and may use TimestampMixin.
"""
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base. Import this everywhere, never re-declare it."""
    pass


class TimestampMixin:
    """Adds created_at / updated_at to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
