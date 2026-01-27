# Phase 5: Project Lifecycle Hooks

**Priority:** P4 (Final integration)

## Changes

### 5.1 Update ProjectService

**File:** `.orchestrator/core/project_service.py`

Add expert soft-delete on archive and restore:

```python
from db.repositories.expert_definition import get_expert_definition_repository


class ProjectService:
    # ... existing code ...

    def archive_project(self, project_id: str) -> bool:
        """Archive a project and soft-delete its experts."""
        # Existing archive logic
        project = self.repo.get_by_id(project_id)
        if not project:
            return False

        project.status = "archived"
        project.archived_at = datetime.utcnow()
        self.repo.session.commit()

        # NEW: Soft delete project experts
        expert_repo = get_expert_definition_repository()
        deleted_count = expert_repo.soft_delete_by_project(project_id)

        self.console.print(f"[dim]Archived {deleted_count} project experts[/dim]")

        return True

    def restore_project(self, project_id: str) -> bool:
        """Restore an archived project and its experts."""
        project = self.repo.get_by_id(project_id)
        if not project or project.status != "archived":
            return False

        project.status = "ready"
        project.archived_at = None
        self.repo.session.commit()

        # NEW: Restore project experts
        expert_repo = get_expert_definition_repository()
        restored_count = expert_repo.restore_by_project(project_id)

        self.console.print(f"[dim]Restored {restored_count} project experts[/dim]")

        return True

    def delete_project(self, project_id: str, hard_delete: bool = False) -> bool:
        """Delete a project.

        Args:
            project_id: Project to delete
            hard_delete: If True, permanently delete. If False, just archive.
        """
        if not hard_delete:
            return self.archive_project(project_id)

        # Hard delete - CASCADE will handle expert_definitions due to FK
        project = self.repo.get_by_id(project_id)
        if not project:
            return False

        self.repo.session.delete(project)
        self.repo.session.commit()

        self.console.print(f"[red]Permanently deleted project and all its data[/red]")
        return True
```

### 5.2 Update Portal Project Routes

**File:** `.orchestrator/portal/routes/projects.py`

Add expert count to project responses:

```python
class ProjectDetailResponse(BaseModel):
    # ... existing fields ...
    expert_count: int = 0  # NEW: Count of project-specific experts


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str):
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404)

    # Get expert count
    expert_repo = get_expert_definition_repository()
    experts = expert_repo.list_by_project(project_id)

    return ProjectDetailResponse(
        # ... existing fields ...
        expert_count=len(experts)
    )
```

### 5.3 Add CLI Feedback

**File:** `.orchestrator/commands.py`

Update project commands to show expert status:

```python
@app.command("project")
def project_info(project_slug: str):
    """Show project information."""
    # ... existing code ...

    # Add expert count
    expert_repo = get_expert_definition_repository()
    experts = expert_repo.list_by_project(project.project_id)

    console.print(f"[dim]Project experts:[/dim] {len(experts)}")
    for expert in experts:
        console.print(f"  - {expert.name} ({expert.expert_type})")
```

## Verification

```bash
# Create a project with experts
orch project add /path/to/project --name test-project
# Via Portal: create some project-specific experts

# Verify experts exist
curl http://localhost:8000/api/projects/{project_id}/experts
# Should list the created experts

# Archive project
orch project archive test-project

# Verify experts are soft-deleted
curl "http://localhost:8000/api/projects/{project_id}/experts?include_inactive=true"
# Should show experts with is_active=false

# Restore project
orch project restore test-project

# Verify experts are restored
curl http://localhost:8000/api/projects/{project_id}/experts
# Should show experts with is_active=true
```

## Edge Cases

1. **Archive then hard delete**: Hard delete uses CASCADE, so experts are permanently removed
2. **Multiple archive/restore cycles**: Should work correctly (toggle is_active)
3. **Expert created while project is archived**: Should not happen (project not accessible), but if it does, expert will have is_active=True
