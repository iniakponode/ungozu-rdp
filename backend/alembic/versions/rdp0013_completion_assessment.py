"""Milestone C: versioned assessment criteria and evidence-based certification.

Revision ID: rdp0013_completion_assessment
Revises: rdp0012_package_capacity
"""
from alembic import op
import sqlalchemy as sa

revision = 'rdp0013_completion_assessment'
down_revision = 'rdp0012_package_capacity'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('rdp_assessment_criteria',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('programme_version_id', sa.Integer, sa.ForeignKey('rdp_programme_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(80), nullable=False, server_default='research'),
        sa.Column('max_score', sa.SmallInteger, nullable=False),
        sa.Column('pass_score', sa.SmallInteger, nullable=False),
        sa.Column('required', sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('programme_version_id','code',name='uq_rdp_criterion_version_code'),
        sa.CheckConstraint('max_score > 0 AND pass_score >= 0 AND pass_score <= max_score',name='ck_rdp_criterion_score_range'),
    )
    op.create_index('ix_rdp_assessment_criteria_programme_version_id','rdp_assessment_criteria',['programme_version_id'])
    op.create_table('rdp_assessment_evaluations',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('enrollment_id', sa.Integer, sa.ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('criterion_id', sa.Integer, sa.ForeignKey('rdp_assessment_criteria.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('assessor_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('score', sa.SmallInteger, nullable=False),
        sa.Column('evidence', sa.Text, nullable=False),
        sa.Column('feedback', sa.Text, nullable=False),
        sa.Column('assessed_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('score >= 0',name='ck_rdp_evaluation_score_nonnegative'),
    )
    op.create_index('ix_rdp_assessment_evaluations_enrollment_id','rdp_assessment_evaluations',['enrollment_id'])
    op.create_index('ix_rdp_assessment_evaluations_criterion_id','rdp_assessment_evaluations',['criterion_id'])
    op.create_table('rdp_completion_decisions',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('enrollment_id', sa.Integer, sa.ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('decided_by_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('decision', sa.String(30), nullable=False),
        sa.Column('rationale', sa.Text, nullable=False),
        sa.Column('evidence_snapshot_json', sa.Text, nullable=False),
        sa.Column('decided_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("decision IN ('approved','needs_work','not_approved')",name='ck_rdp_completion_decision_enum'),
    )
    op.create_index('ix_rdp_completion_decisions_enrollment_id','rdp_completion_decisions',['enrollment_id'])
    op.create_table('rdp_curriculum_progress',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('enrollment_id', sa.Integer, sa.ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('item_id', sa.Integer, sa.ForeignKey('rdp_curriculum_items.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='draft'),
        sa.Column('evidence', sa.Text, nullable=False),
        sa.Column('reviewed_feedback', sa.Text, nullable=True),
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('enrollment_id','item_id',name='uq_rdp_curriculum_progress_item'),
    )
    op.create_index('ix_rdp_curriculum_progress_enrollment_id','rdp_curriculum_progress',['enrollment_id'])
    op.create_index('ix_rdp_curriculum_progress_item_id','rdp_curriculum_progress',['item_id'])
    op.create_table('rdp_certificates',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('enrollment_id', sa.Integer, sa.ForeignKey('rdp_enrollments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('certificate_number', sa.String(100), nullable=False),
        sa.Column('verification_token', sa.String(96), nullable=False),
        sa.Column('recipient_name_snapshot', sa.String(255), nullable=False),
        sa.Column('programme_title_snapshot', sa.String(255), nullable=False),
        sa.Column('cohort_label_snapshot', sa.String(255), nullable=False),
        sa.Column('duration_snapshot', sa.String(80), nullable=True),
        sa.Column('issued_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('issued_by_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('revoked_at', sa.DateTime, nullable=True),
        sa.Column('revoke_reason', sa.Text, nullable=True),
        sa.Column('revoked_by_user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True),
        sa.UniqueConstraint('enrollment_id',name='uq_rdp_certificate_enrollment'),
        sa.UniqueConstraint('certificate_number',name='uq_rdp_certificate_number'),
        sa.UniqueConstraint('verification_token',name='uq_rdp_certificate_token'),
    )


def downgrade():
    op.drop_table('rdp_certificates')
    op.drop_index('ix_rdp_curriculum_progress_item_id',table_name='rdp_curriculum_progress')
    op.drop_index('ix_rdp_curriculum_progress_enrollment_id',table_name='rdp_curriculum_progress')
    op.drop_table('rdp_curriculum_progress')
    op.drop_index('ix_rdp_completion_decisions_enrollment_id',table_name='rdp_completion_decisions')
    op.drop_table('rdp_completion_decisions')
    op.drop_index('ix_rdp_assessment_evaluations_criterion_id',table_name='rdp_assessment_evaluations')
    op.drop_index('ix_rdp_assessment_evaluations_enrollment_id',table_name='rdp_assessment_evaluations')
    op.drop_table('rdp_assessment_evaluations')
    op.drop_index('ix_rdp_assessment_criteria_programme_version_id',table_name='rdp_assessment_criteria')
    op.drop_table('rdp_assessment_criteria')
