# Phase 2: Repository Layer Updates

**Priority:** P1 (Depends on Phase 1)

## Changes

### 2.1 Update ExpertDefinitionRepository

**File:** `.orchestrator/db/repositories/expert_definition.py`

Add scope-aware methods:

```python
class ExpertDefinitionRepository:
    # ... existing methods ...

    def list_global(self) -> List[ExpertDefinition]:
        """Get all global (bundled) experts."""
        return self.session.query(ExpertDefinition).filter(
            ExpertDefinition.scope == "global",
            ExpertDefinition.is_active == True
        ).all()

    def list_by_project(self, project_id: str) -> List[ExpertDefinition]:
        """Get all experts for a specific project."""
        return self.session.query(ExpertDefinition).filter(
            ExpertDefinition.scope == "project",
            ExpertDefinition.project_id == project_id,
            ExpertDefinition.is_active == True
        ).all()

    def list_combined(self, project_id: str) -> List[ExpertDefinition]:
        """Get global experts + project-specific experts.

        This is what ExpertSelector uses - combined pool for scoring.
        """
        return self.session.query(ExpertDefinition).filter(
            ExpertDefinition.is_active == True,
            or_(
                ExpertDefinition.scope == "global",
                and_(
                    ExpertDefinition.scope == "project",
                    ExpertDefinition.project_id == project_id
                )
            )
        ).all()

    def create_project_expert(
        self,
        project_id: str,
        name: str,
        description: str,
        system_prompt: str,
        expert_type: str = "domain",
        trigger_keywords: List[str] = None,
        trigger_paths: List[str] = None,
        trigger_topics: List[str] = None,
        weight: float = 1.0
    ) -> ExpertDefinition:
        """Create a project-specific expert."""
        expert = ExpertDefinition(
            name=name,
            scope="project",
            project_id=project_id,
            description=description,
            system_prompt=system_prompt,
            expert_type=expert_type,
            trigger_keywords_json=json.dumps(trigger_keywords or []),
            trigger_paths_json=json.dumps(trigger_paths or []),
            trigger_topics_json=json.dumps(trigger_topics or []),
            weight=weight,
            is_active=True
        )
        self.session.add(expert)
        self.session.commit()
        return expert

    def soft_delete_by_project(self, project_id: str) -> int:
        """Soft delete all experts for a project (on archive).

        Returns count of affected rows.
        """
        count = self.session.query(ExpertDefinition).filter(
            ExpertDefinition.project_id == project_id
        ).update({"is_active": False})
        self.session.commit()
        return count

    def restore_by_project(self, project_id: str) -> int:
        """Restore all experts for a project (on unarchive).

        Returns count of affected rows.
        """
        count = self.session.query(ExpertDefinition).filter(
            ExpertDefinition.project_id == project_id
        ).update({"is_active": True})
        self.session.commit()
        return count

    def get_project_expert(self, expert_id: int, project_id: str) -> Optional[ExpertDefinition]:
        """Get a specific project expert (with ownership check)."""
        return self.session.query(ExpertDefinition).filter(
            ExpertDefinition.id == expert_id,
            ExpertDefinition.project_id == project_id,
            ExpertDefinition.scope == "project"
        ).first()

    def update_project_expert(
        self,
        expert_id: int,
        project_id: str,
        **kwargs
    ) -> Optional[ExpertDefinition]:
        """Update a project expert (with ownership check)."""
        expert = self.get_project_expert(expert_id, project_id)
        if not expert:
            return None

        # Prevent changing scope or project_id
        kwargs.pop('scope', None)
        kwargs.pop('project_id', None)

        for key, value in kwargs.items():
            if hasattr(expert, key):
                setattr(expert, key, value)

        self.session.commit()
        return expert

    def delete_project_expert(self, expert_id: int, project_id: str) -> bool:
        """Soft delete a single project expert."""
        expert = self.get_project_expert(expert_id, project_id)
        if not expert:
            return False

        expert.is_active = False
        self.session.commit()
        return True
```

### 2.2 Add Required Imports

```python
from sqlalchemy import or_, and_
```

## Verification

```python
# Test in Python shell
from db.repositories.expert_definition import get_expert_definition_repository

repo = get_expert_definition_repository()

# Should return bundled experts
global_experts = repo.list_global()
print(f"Global experts: {len(global_experts)}")

# Should return empty (no project experts yet)
project_experts = repo.list_by_project("some-project-id")
print(f"Project experts: {len(project_experts)}")

# Combined should equal global (for now)
combined = repo.list_combined("some-project-id")
print(f"Combined: {len(combined)}")
```
