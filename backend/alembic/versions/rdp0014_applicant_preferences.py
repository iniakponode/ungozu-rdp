"""Record optional applicant package and fee-plan preferences without changing admissions.

Revision ID: rdp0014_applicant_preferences
Revises: rdp0013_completion_assessment
"""
from alembic import op
import sqlalchemy as sa

revision = 'rdp0014_applicant_preferences'
down_revision = 'rdp0013_completion_assessment'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rdp_applications', sa.Column(
        'preferred_package_id', sa.Integer(),
        sa.ForeignKey('rdp_packages.id', ondelete='SET NULL'), nullable=True))
    op.add_column('rdp_applications', sa.Column(
        'preferred_fee_plan_id', sa.Integer(),
        sa.ForeignKey('rdp_fee_plans.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_rdp_applications_preferred_package_id', 'rdp_applications', ['preferred_package_id'])
    op.create_index('ix_rdp_applications_preferred_fee_plan_id', 'rdp_applications', ['preferred_fee_plan_id'])


def downgrade():
    # Downgrading deliberately discards preferences; take a backup first.
    op.drop_index('ix_rdp_applications_preferred_fee_plan_id', table_name='rdp_applications')
    op.drop_index('ix_rdp_applications_preferred_package_id', table_name='rdp_applications')
    op.drop_column('rdp_applications', 'preferred_fee_plan_id')
    op.drop_column('rdp_applications', 'preferred_package_id')
