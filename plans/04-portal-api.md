# Phase 4: Portal API for Project Experts

**Priority:** P3 (Depends on Phase 2)

## Changes

### 4.1 Add API Routes

**File:** `.orchestrator/portal/routes/project_experts.py` (NEW FILE)

```python
"""Routes for project-specific expert management."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field

from db.repositories.expert_definition import get_expert_definition_repository
from portal.dependencies import get_current_project_id

router = APIRouter(prefix="/api/projects/{project_id}/experts", tags=["Project Experts"])


# --- Schemas ---

class ExpertTriggers(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    paths: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)


class CreateProjectExpertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    system_prompt: str = Field(..., min_length=10)
    expert_type: str = Field(default="domain")  # domain, tech, module
    triggers: ExpertTriggers = Field(default_factory=ExpertTriggers)
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


class UpdateProjectExpertRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=10)
    expert_type: Optional[str] = None
    triggers: Optional[ExpertTriggers] = None
    weight: Optional[float] = Field(None, ge=0.1, le=10.0)


class ProjectExpertResponse(BaseModel):
    id: int
    name: str
    description: str
    expert_type: str
    system_prompt: str
    triggers: ExpertTriggers
    weight: float
    is_active: bool
    created_at: str
    updated_at: str


# --- Routes ---

@router.get("", response_model=List[ProjectExpertResponse])
async def list_project_experts(
    project_id: str,
    include_inactive: bool = False
):
    """List all experts for a project."""
    repo = get_expert_definition_repository()

    if include_inactive:
        # Get all including soft-deleted
        experts = repo.session.query(repo.model).filter(
            repo.model.project_id == project_id,
            repo.model.scope == "project"
        ).all()
    else:
        experts = repo.list_by_project(project_id)

    return [_to_response(e) for e in experts]


@router.post("", response_model=ProjectExpertResponse, status_code=status.HTTP_201_CREATED)
async def create_project_expert(
    project_id: str,
    request: CreateProjectExpertRequest
):
    """Create a new project-specific expert."""
    repo = get_expert_definition_repository()

    # Check for duplicate name in this project
    existing = repo.list_by_project(project_id)
    if any(e.name == request.name for e in existing):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Expert '{request.name}' already exists in this project"
        )

    expert = repo.create_project_expert(
        project_id=project_id,
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        expert_type=request.expert_type,
        trigger_keywords=request.triggers.keywords,
        trigger_paths=request.triggers.paths,
        trigger_topics=request.triggers.topics,
        weight=request.weight
    )

    return _to_response(expert)


@router.get("/{expert_id}", response_model=ProjectExpertResponse)
async def get_project_expert(project_id: str, expert_id: int):
    """Get a specific project expert."""
    repo = get_expert_definition_repository()
    expert = repo.get_project_expert(expert_id, project_id)

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expert {expert_id} not found in project {project_id}"
        )

    return _to_response(expert)


@router.put("/{expert_id}", response_model=ProjectExpertResponse)
async def update_project_expert(
    project_id: str,
    expert_id: int,
    request: UpdateProjectExpertRequest
):
    """Update a project expert."""
    repo = get_expert_definition_repository()

    update_data = request.dict(exclude_unset=True)

    # Handle triggers separately
    if "triggers" in update_data:
        triggers = update_data.pop("triggers")
        update_data["trigger_keywords_json"] = json.dumps(triggers.get("keywords", []))
        update_data["trigger_paths_json"] = json.dumps(triggers.get("paths", []))
        update_data["trigger_topics_json"] = json.dumps(triggers.get("topics", []))

    expert = repo.update_project_expert(expert_id, project_id, **update_data)

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expert {expert_id} not found in project {project_id}"
        )

    return _to_response(expert)


@router.delete("/{expert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_expert(project_id: str, expert_id: int):
    """Soft delete a project expert."""
    repo = get_expert_definition_repository()
    success = repo.delete_project_expert(expert_id, project_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expert {expert_id} not found in project {project_id}"
        )


@router.post("/{expert_id}/restore", response_model=ProjectExpertResponse)
async def restore_project_expert(project_id: str, expert_id: int):
    """Restore a soft-deleted project expert."""
    repo = get_expert_definition_repository()

    expert = repo.session.query(repo.model).filter(
        repo.model.id == expert_id,
        repo.model.project_id == project_id,
        repo.model.scope == "project"
    ).first()

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expert {expert_id} not found"
        )

    expert.is_active = True
    repo.session.commit()

    return _to_response(expert)


# --- Helper ---

def _to_response(expert) -> ProjectExpertResponse:
    import json
    return ProjectExpertResponse(
        id=expert.id,
        name=expert.name,
        description=expert.description or "",
        expert_type=expert.expert_type or "domain",
        system_prompt=expert.system_prompt,
        triggers=ExpertTriggers(
            keywords=json.loads(expert.trigger_keywords_json or "[]"),
            paths=json.loads(expert.trigger_paths_json or "[]"),
            topics=json.loads(expert.trigger_topics_json or "[]")
        ),
        weight=expert.weight or 1.0,
        is_active=expert.is_active,
        created_at=expert.created_at.isoformat() if expert.created_at else "",
        updated_at=expert.updated_at.isoformat() if expert.updated_at else ""
    )
```

### 4.2 Register Router

**File:** `.orchestrator/portal/app.py`

```python
from portal.routes.project_experts import router as project_experts_router

# Add to router registration
app.include_router(project_experts_router)
```

## API Usage Examples

```bash
# List project experts
GET /api/projects/{project_id}/experts

# Create project expert
POST /api/projects/{project_id}/experts
{
  "name": "legacy-api-rules",
  "description": "Rules for working with our legacy API",
  "system_prompt": "When working with the legacy API...",
  "expert_type": "domain",
  "triggers": {
    "keywords": ["legacy", "old-api", "v1"],
    "paths": ["src/legacy/*"],
    "topics": ["api", "migration"]
  }
}

# Update expert
PUT /api/projects/{project_id}/experts/{expert_id}
{
  "system_prompt": "Updated prompt..."
}

# Delete expert (soft delete)
DELETE /api/projects/{project_id}/experts/{expert_id}

# Restore deleted expert
POST /api/projects/{project_id}/experts/{expert_id}/restore
```

## Verification

```bash
# Start portal
orch portal

# Create expert
curl -X POST http://localhost:8000/api/projects/test-project-id/experts \
  -H "Content-Type: application/json" \
  -d '{"name": "test-expert", "system_prompt": "Test expert prompt..."}'

# List experts
curl http://localhost:8000/api/projects/test-project-id/experts

# Verify expert appears in selector
orch plan "test with legacy keyword"
# Should select the project expert if keywords match
```
