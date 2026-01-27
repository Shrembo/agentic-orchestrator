# Phase 1: Database Schema Changes

**Priority:** P0 (Foundation - all other phases depend on this)

## Changes

### 1.1 Update ExpertDefinition Model

**File:** `.orchestrator/db/models.py`

Add columns to `ExpertDefinition` class (around line 651):

```python
class ExpertDefinition(Base):
    __tablename__ = "expert_definitions"

    # ... existing fields ...

    # NEW FIELDS
    scope = Column(String(20), default="global", nullable=False, index=True)
    # Values: "global" | "project"

    project_id = Column(
        String(36),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    # NULL for global experts, project UUID for project-specific

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    # For soft delete on project archive

    # UPDATE: Change unique constraint from just 'name' to composite
    __table_args__ = (
        UniqueConstraint('name', 'project_id', name='uq_expert_name_project'),
    )
```

### 1.2 Create Migration

**File:** `.orchestrator/db/migrations/versions/xxx_add_expert_scope.py`

```python
"""Add scope and project_id to expert_definitions

Revision ID: xxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add new columns
    op.add_column('expert_definitions',
        sa.Column('scope', sa.String(20), nullable=False, server_default='global'))
    op.add_column('expert_definitions',
        sa.Column('project_id', sa.String(36), nullable=True))
    op.add_column('expert_definitions',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))

    # Add indexes
    op.create_index('ix_expert_definitions_scope', 'expert_definitions', ['scope'])
    op.create_index('ix_expert_definitions_project_id', 'expert_definitions', ['project_id'])
    op.create_index('ix_expert_definitions_is_active', 'expert_definitions', ['is_active'])

    # Add foreign key
    op.create_foreign_key(
        'fk_expert_definitions_project_id',
        'expert_definitions', 'projects',
        ['project_id'], ['project_id'],
        ondelete='CASCADE'
    )

    # Drop old unique constraint on name
    op.drop_constraint('expert_definitions_name_key', 'expert_definitions', type_='unique')

    # Add new composite unique constraint
    op.create_unique_constraint(
        'uq_expert_name_project',
        'expert_definitions',
        ['name', 'project_id']
    )

def downgrade():
    op.drop_constraint('uq_expert_name_project', 'expert_definitions', type_='unique')
    op.drop_constraint('fk_expert_definitions_project_id', 'expert_definitions', type_='foreignkey')
    op.drop_index('ix_expert_definitions_is_active', 'expert_definitions')
    op.drop_index('ix_expert_definitions_project_id', 'expert_definitions')
    op.drop_index('ix_expert_definitions_scope', 'expert_definitions')
    op.drop_column('expert_definitions', 'is_active')
    op.drop_column('expert_definitions', 'project_id')
    op.drop_column('expert_definitions', 'scope')
    op.create_unique_constraint('expert_definitions_name_key', 'expert_definitions', ['name'])
```

### 1.3 Update Seed Script

**File:** `.orchestrator/db/migrations/seed_from_files.py`

When seeding bundled experts, explicitly set scope:

```python
expert_def = ExpertDefinition(
    name=expert_name,
    scope="global",        # Always global for bundled
    project_id=None,       # No project association
    is_active=True,        # Always active
    # ... rest of fields
)
```

## Verification

```bash
# Run migration
cd .orchestrator
alembic upgrade head

# Verify columns exist
psql -c "SELECT scope, project_id, is_active FROM expert_definitions LIMIT 1;"

# Verify existing experts are global
psql -c "SELECT COUNT(*) FROM expert_definitions WHERE scope = 'global';"
```

## Rollback

```bash
alembic downgrade -1
```
