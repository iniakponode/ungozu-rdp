"""Protected academic learning resources.

Revision ID: rdp0016_learning_resources
Revises: rdp0015_record_lifecycle
"""
from alembic import op
import sqlalchemy as sa
revision = 'rdp0016_learning_resources'
down_revision = 'rdp0015_record_lifecycle'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('rdp_learning_resources',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('programme_version_id', sa.Integer(), sa.ForeignKey('rdp_programme_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('rdp_curriculum_modules.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('resource_code', sa.String(100), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('audience', sa.String(20), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('storage_key', sa.String(100), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('programme_version_id','resource_code',name='uq_rdp_learning_resource_version_code'),
        sa.UniqueConstraint('storage_key',name='uq_rdp_learning_resource_storage_key'),
    )
    op.create_index('ix_rdp_learning_resource_version','rdp_learning_resources',['programme_version_id'])
    op.create_index('ix_rdp_learning_resource_module','rdp_learning_resources',['module_id'])

def downgrade():
    op.drop_index('ix_rdp_learning_resource_module', table_name='rdp_learning_resources')
    op.drop_index('ix_rdp_learning_resource_version', table_name='rdp_learning_resources')
    op.drop_table('rdp_learning_resources')
