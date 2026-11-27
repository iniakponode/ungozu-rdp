"""M4 protected document lifecycle, immutable replacement history and audit.

Revision ID: rdp0018_learning_resource_lifecycle
Revises: rdp0017_resource_curriculum_module
"""
from alembic import op
import sqlalchemy as sa
revision = 'rdp0018_learning_resource_lifecycle'
down_revision = 'rdp0017_resource_curriculum_module'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rdp_learning_resources', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('rdp_learning_resources', sa.Column('file_revision', sa.Integer(), nullable=False, server_default='1'))
    op.create_table('rdp_learning_resource_revisions',
        sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column('resource_id',sa.Integer(),sa.ForeignKey('rdp_learning_resources.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('revision_number',sa.Integer(),nullable=False),
        sa.Column('original_filename',sa.String(255),nullable=False),
        sa.Column('storage_key',sa.String(100),nullable=False,unique=True),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('size_bytes',sa.Integer(),nullable=False),
        sa.Column('replaced_at',sa.DateTime(),nullable=False),
        sa.Column('replaced_by_user_id',sa.Integer(),nullable=True),
        sa.UniqueConstraint('resource_id','revision_number',name='uq_rdp_resource_revision_number'))
    op.create_index('ix_rdp_resource_revision_resource','rdp_learning_resource_revisions',['resource_id'])
    op.create_table('rdp_learning_resource_audit',
        sa.Column('id',sa.Integer(),primary_key=True,autoincrement=True),
        sa.Column('resource_id',sa.Integer(),sa.ForeignKey('rdp_learning_resources.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('actor_user_id',sa.Integer(),nullable=True),
        sa.Column('action',sa.String(40),nullable=False),
        sa.Column('details',sa.String(2000),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_rdp_resource_audit_resource','rdp_learning_resource_audit',['resource_id'])


def downgrade():
    op.drop_index('ix_rdp_resource_audit_resource',table_name='rdp_learning_resource_audit')
    op.drop_table('rdp_learning_resource_audit')
    op.drop_index('ix_rdp_resource_revision_resource',table_name='rdp_learning_resource_revisions')
    op.drop_table('rdp_learning_resource_revisions')
    op.drop_column('rdp_learning_resources','file_revision')
    op.drop_column('rdp_learning_resources','is_archived')
