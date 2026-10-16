"""Milestone C: immutable rubric identities, append-only evaluations/decisions and issued certificates."""
from datetime import datetime
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base_class import Base, TimestampMixin


class RDPAssessmentCriterion(Base, TimestampMixin):
    __tablename__ = 'rdp_assessment_criteria'
    __table_args__ = (
        UniqueConstraint('programme_version_id', 'code', name='uq_rdp_criterion_version_code'),
        CheckConstraint('max_score > 0 AND pass_score >= 0 AND pass_score <= max_score', name='ck_rdp_criterion_score_range'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programme_version_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_programme_versions.id', ondelete='RESTRICT'), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default='research')
    max_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)
    pass_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=60)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RDPAssessmentEvaluation(Base):
    __tablename__ = 'rdp_assessment_evaluations'
    __table_args__ = (CheckConstraint('score >= 0', name='ck_rdp_evaluation_score_nonnegative'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False, index=True)
    criterion_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_assessment_criteria.id', ondelete='RESTRICT'), nullable=False, index=True)
    assessor_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class RDPCompletionDecision(Base):
    __tablename__ = 'rdp_completion_decisions'
    __table_args__ = (CheckConstraint("decision IN ('approved','needs_work','not_approved')", name='ck_rdp_completion_decision_enum'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False, index=True)
    decided_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class RDPCertificate(Base):
    __tablename__ = 'rdp_certificates'
    __table_args__ = (
        UniqueConstraint('enrollment_id', name='uq_rdp_certificate_enrollment'),
        UniqueConstraint('certificate_number', name='uq_rdp_certificate_number'),
        UniqueConstraint('verification_token', name='uq_rdp_certificate_token'),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False)
    certificate_number: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_token: Mapped[str] = mapped_column(String(96), nullable=False)
    recipient_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    programme_title_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    cohort_label_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    issued_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=True)


class RDPCurriculumProgress(Base, TimestampMixin):
    """One participant's delivery evidence for one curriculum item."""
    __tablename__ = 'rdp_curriculum_progress'
    __table_args__ = (UniqueConstraint('enrollment_id', 'item_id', name='uq_rdp_curriculum_progress_item'),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey('rdp_curriculum_items.id', ondelete='RESTRICT'), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default='draft')
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=True)
