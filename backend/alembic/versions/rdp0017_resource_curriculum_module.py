"""Optional curriculum-module references for cohort resources.

Revision ID: rdp0017_resource_curriculum_module
Revises: rdp0016_learning_resources
"""
from alembic import op
import sqlalchemy as sa

revision = 'rdp0017_resource_curriculum_module'
down_revision = 'rdp0016_learning_resources'
branch_labels = None
depends_on = None

def upgrade():
    # Existing M3 databases use VARCHAR(32), which is too short
    # for the M4 Alembic revision identifiers.
    op.alter_column(
        'alembic_version',
        'version_num',
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    # Nullable: all existing and legacy resources remain valid as cohort references.
    op.add_column('rdp_resources', sa.Column('module_id', sa.Integer(), nullable=True))
    op.create_index('ix_rdp_resources_module_id', 'rdp_resources', ['module_id'])
    op.create_foreign_key('fk_rdp_resources_module_id', 'rdp_resources', 'rdp_curriculum_modules', ['module_id'], ['id'], ondelete='RESTRICT')

def downgrade():
    op.drop_constraint('fk_rdp_resources_module_id', 'rdp_resources', type_='foreignkey')
    op.drop_index('ix_rdp_resources_module_id', table_name='rdp_resources')
    op.drop_column('rdp_resources', 'module_id')
