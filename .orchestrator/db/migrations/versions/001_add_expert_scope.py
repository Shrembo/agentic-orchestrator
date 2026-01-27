"""Add scope and project_id to expert_definitions

This migration adds support for project-specific experts by adding:
- scope: 'global' or 'project' to distinguish bundled vs project experts
- project_id: Foreign key to projects table for project-specific experts
- is_active: Soft delete flag for archive/restore functionality

Revision ID: 001_add_expert_scope
Revises: None
Create Date: 2026-01-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_add_expert_scope'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns with defaults so existing rows get values
    op.add_column('expert_definitions',
        sa.Column('scope', sa.String(20), nullable=False, server_default='global'))

    op.add_column('expert_definitions',
        sa.Column('project_id', sa.String(36), nullable=True))

    op.add_column('expert_definitions',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Add indexes for query performance
    op.create_index('ix_expert_definitions_scope', 'expert_definitions', ['scope'])
    op.create_index('ix_expert_definitions_project_id', 'expert_definitions', ['project_id'])
    op.create_index('ix_expert_definitions_is_active', 'expert_definitions', ['is_active'])

    # Add foreign key constraint to projects table
    op.create_foreign_key(
        'fk_expert_definitions_project_id',
        'expert_definitions', 'projects',
        ['project_id'], ['project_id'],
        ondelete='CASCADE'
    )

    # Drop old unique constraint on name only
    # Note: constraint name may vary by database, try common patterns
    try:
        op.drop_constraint('expert_definitions_name_key', 'expert_definitions', type_='unique')
    except Exception:
        try:
            op.drop_constraint('uq_expert_definitions_name', 'expert_definitions', type_='unique')
        except Exception:
            # If no constraint exists, that's fine
            pass

    # Drop the unique index if it exists (SQLAlchemy sometimes creates index instead of constraint)
    try:
        op.drop_index('ix_expert_definitions_name', 'expert_definitions')
    except Exception:
        pass

    # Add new composite unique constraint (name unique per project)
    op.create_unique_constraint(
        'uq_expert_name_project',
        'expert_definitions',
        ['name', 'project_id']
    )


def downgrade() -> None:
    # Remove composite unique constraint
    op.drop_constraint('uq_expert_name_project', 'expert_definitions', type_='unique')

    # Remove foreign key
    op.drop_constraint('fk_expert_definitions_project_id', 'expert_definitions', type_='foreignkey')

    # Remove indexes
    op.drop_index('ix_expert_definitions_is_active', 'expert_definitions')
    op.drop_index('ix_expert_definitions_project_id', 'expert_definitions')
    op.drop_index('ix_expert_definitions_scope', 'expert_definitions')

    # Remove columns
    op.drop_column('expert_definitions', 'is_active')
    op.drop_column('expert_definitions', 'project_id')
    op.drop_column('expert_definitions', 'scope')

    # Restore original unique constraint on name
    op.create_unique_constraint('expert_definitions_name_key', 'expert_definitions', ['name'])
