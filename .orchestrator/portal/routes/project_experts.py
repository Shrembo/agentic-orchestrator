"""
API routes for project-specific expert management.

These routes allow CRUD operations on experts that belong to a specific project,
separate from the global (bundled) experts.
"""
import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from db.repositories.expert_definition import get_expert_definition_repository


router = APIRouter(prefix="/api/projects/{project_id}/experts", tags=["Project Experts"])


# --- Schemas ---

class ExpertTriggers(BaseModel):
    """Trigger conditions for expert selection."""
    keywords: List[str] = Field(default_factory=list)
    paths: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)


class CreateProjectExpertRequest(BaseModel):
    """Request model for creating a project-specific expert."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    system_prompt: str = Field(..., min_length=10)
    expert_type: str = Field(default="domain")  # domain, tech, module
    category: str = Field(default="general")
    triggers: ExpertTriggers = Field(default_factory=ExpertTriggers)
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


class UpdateProjectExpertRequest(BaseModel):
    """Request model for updating a project-specific expert."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=10)
    expert_type: Optional[str] = None
    category: Optional[str] = None
    triggers: Optional[ExpertTriggers] = None
    weight: Optional[float] = Field(None, ge=0.1, le=10.0)


class ProjectExpertResponse(BaseModel):
    """Response model for a project-specific expert."""
    id: int
    name: str
    description: str
    expert_type: str
    category: str
    system_prompt: str
    triggers: ExpertTriggers
    weight: float
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]


# --- Routes ---

@router.get("", response_model=List[ProjectExpertResponse])
async def list_project_experts(
    project_id: str,
    include_inactive: bool = False
):
    """List all experts for a project."""
    repo = get_expert_definition_repository()
    experts = repo.list_by_project(project_id, active_only=not include_inactive)
    return [_to_response(e) for e in experts]


@router.post("", response_model=ProjectExpertResponse, status_code=status.HTTP_201_CREATED)
async def create_project_expert(
    project_id: str,
    request: CreateProjectExpertRequest
):
    """Create a new project-specific expert."""
    repo = get_expert_definition_repository()

    # Check for duplicate name in this project
    if repo.exists(request.name, project_id=project_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Expert '{request.name}' already exists in this project"
        )

    expert = repo.create_project_expert(
        project_id=project_id,
        name=request.name,
        system_prompt=request.system_prompt,
        description=request.description,
        expert_type=request.expert_type,
        category=request.category,
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

    update_data = request.model_dump(exclude_unset=True)

    # Handle triggers separately - convert to JSON fields
    if "triggers" in update_data:
        triggers = update_data.pop("triggers")
        if triggers:
            update_data["trigger_keywords"] = triggers.get("keywords", [])
            update_data["trigger_paths"] = triggers.get("paths", [])
            update_data["trigger_topics"] = triggers.get("topics", [])

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

    # First check if expert exists (including inactive)
    expert = repo.get_project_expert(expert_id, project_id)

    # If not found with standard query, try to find inactive one
    if not expert:
        # Get all including inactive and look for this one
        all_experts = repo.list_by_project(project_id, active_only=False)
        expert = next((e for e in all_experts if e.id == expert_id), None)

    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expert {expert_id} not found in project {project_id}"
        )

    # Activate the expert
    repo.activate(expert.name, project_id=project_id)

    # Refetch to get updated state
    expert = repo.get_project_expert(expert_id, project_id)
    return _to_response(expert)


# --- Helper ---

def _to_response(expert) -> ProjectExpertResponse:
    """Convert database expert to response model."""
    return ProjectExpertResponse(
        id=expert.id,
        name=expert.name,
        description=expert.description or "",
        expert_type=expert.expert_type or "domain",
        category=expert.category or "general",
        system_prompt=expert.system_prompt,
        triggers=ExpertTriggers(
            keywords=json.loads(expert.trigger_keywords_json or "[]"),
            paths=json.loads(expert.trigger_paths_json or "[]"),
            topics=json.loads(expert.trigger_topics_json or "[]")
        ),
        weight=expert.weight or 1.0,
        is_active=expert.is_active,
        created_at=expert.created_at.isoformat() if expert.created_at else None,
        updated_at=expert.updated_at.isoformat() if expert.updated_at else None
    )
