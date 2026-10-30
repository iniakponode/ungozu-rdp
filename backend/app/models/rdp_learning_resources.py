"""Version-bound protected learning files. Never store public URLs or raw bytes in database."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base

class RDPLearningResource(Base):
    __tablename__ = 'rdp_learning_resources'
    __table_args__ = (UniqueConstraint('programme_version_id', 'resource_code', name='uq_rdp_learning_resource_version_code'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_version_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_programme_versions.id', ondelete='RESTRICT'), nullable=False, index=True)
    module_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_curriculum_modules.id', ondelete='RESTRICT'), nullable=False, index=True)
    resource_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    audience: Mapped[str] = mapped_column(String(20), nullable=False)  # participant or staff
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
