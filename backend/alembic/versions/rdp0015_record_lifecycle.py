"""Audit and archive ledger for builder record lifecycle.

Revision ID: rdp0015_record_lifecycle
Revises: rdp0014_applicant_preferences
"""
from alembic import op
import sqlalchemy as sa

revision = 'rdp0015_record_lifecycle'
down_revision = 'rdp0014_applicant_preferences'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('rdp_record_archives',
        sa.Column('record_type', sa.String(30), primary_key=True),
        sa.Column('record_id', sa.Integer(), primary_key=True),
        sa.Column('previous_status', sa.String(50)),
        sa.Column('previous_published', sa.Boolean()),
        sa.Column('archived_at', sa.DateTime(), nullable=False),
        sa.Column('archived_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False))
    op.create_table('rdp_record_lifecycle_audit',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('record_type', sa.String(30), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('previous_state', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_index('ix_rdp_record_lifecycle_audit_target', 'rdp_record_lifecycle_audit', ['record_type','record_id'])


def downgrade():
    op.drop_index('ix_rdp_record_lifecycle_audit_target', table_name='rdp_record_lifecycle_audit')
    op.drop_table('rdp_record_lifecycle_audit')
    op.drop_table('rdp_record_archives')
