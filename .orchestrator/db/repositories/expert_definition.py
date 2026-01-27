"""
Repository for expert definition CRUD operations.

This module provides database access for expert definitions that replace
the .orchestrator/agents/experts/*.md files.
"""
import json
from typing import Optional, List
from sqlalchemy import select, or_, and_

from .base import BaseRepository
from db.models import ExpertDefinition


class ExpertDefinitionRepository(BaseRepository):
    """Repository for managing expert definitions in database."""

    model = ExpertDefinition
    table_name = "expert_definitions"

    JSON_FIELDS = ["domain_keywords", "trigger_keywords", "trigger_paths", "trigger_topics"]

    def get_by_name(
        self, name: str, project_id: Optional[str] = None
    ) -> Optional[ExpertDefinition]:
        """
        Get expert definition by name and optional project_id.

        Args:
            name: Expert name
            project_id: If None, returns global expert. If set, returns project-specific expert.
        """
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.name == name,
                ExpertDefinition.project_id == project_id
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if expert:
                session.expunge(expert)  # Detach from session to allow access after close
            return expert

    def list_all(self, active_only: bool = True) -> List[ExpertDefinition]:
        """List all expert definitions."""
        with self.session() as session:
            stmt = select(ExpertDefinition)
            if active_only:
                stmt = stmt.where(ExpertDefinition.is_active == True)
            stmt = stmt.order_by(ExpertDefinition.name)
            experts = list(session.execute(stmt).scalars())
            for expert in experts:
                session.expunge(expert)  # Detach from session
            return experts

    def list_global(self, active_only: bool = True) -> List[ExpertDefinition]:
        """List all global (bundled) expert definitions."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.scope == "global"
            )
            if active_only:
                stmt = stmt.where(ExpertDefinition.is_active == True)
            stmt = stmt.order_by(ExpertDefinition.name)
            experts = list(session.execute(stmt).scalars())
            for expert in experts:
                session.expunge(expert)
            return experts

    def list_by_project(
        self, project_id: str, active_only: bool = True
    ) -> List[ExpertDefinition]:
        """List project-specific expert definitions."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.scope == "project",
                ExpertDefinition.project_id == project_id
            )
            if active_only:
                stmt = stmt.where(ExpertDefinition.is_active == True)
            stmt = stmt.order_by(ExpertDefinition.name)
            experts = list(session.execute(stmt).scalars())
            for expert in experts:
                session.expunge(expert)
            return experts

    def list_combined(
        self, project_id: str, active_only: bool = True
    ) -> List[ExpertDefinition]:
        """
        Get global experts + project-specific experts combined.

        This is what ExpertSelector uses - combined pool for scoring.
        Returns all global experts plus project-specific experts for the given project.
        """
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                or_(
                    ExpertDefinition.scope == "global",
                    and_(
                        ExpertDefinition.scope == "project",
                        ExpertDefinition.project_id == project_id
                    )
                )
            )
            if active_only:
                stmt = stmt.where(ExpertDefinition.is_active == True)
            stmt = stmt.order_by(ExpertDefinition.name)
            experts = list(session.execute(stmt).scalars())
            for expert in experts:
                session.expunge(expert)
            return experts

    def list_by_type(self, expert_type: str) -> List[ExpertDefinition]:
        """List experts by type (tech, domain, module)."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.expert_type == expert_type
            ).order_by(ExpertDefinition.name)
            experts = list(session.execute(stmt).scalars())
            for expert in experts:
                session.expunge(expert)
            return experts

    def list_by_category(self, category: str) -> List[ExpertDefinition]:
        """List experts by category (language, framework, tool, general)."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.category == category
            ).order_by(ExpertDefinition.name)
            experts = list(session.execute(stmt).scalars())
            for expert in experts:
                session.expunge(expert)
            return experts

    def find_by_keywords(self, keywords: List[str]) -> List[ExpertDefinition]:
        """Find experts matching any of the given keywords."""
        all_experts = self.list_all()
        matched = []
        keywords_lower = [k.lower() for k in keywords]

        for expert in all_experts:
            domain_keywords = json.loads(expert.domain_keywords_json or "[]")
            trigger_keywords = json.loads(expert.trigger_keywords_json or "[]")
            all_kw = [k.lower() for k in domain_keywords + trigger_keywords]

            if any(kw in all_kw for kw in keywords_lower):
                matched.append(expert)

        return matched

    def exists(self, name: str, project_id: Optional[str] = None) -> bool:
        """Check if expert exists for given scope."""
        return self.get_by_name(name, project_id) is not None

    def create(
        self,
        name: str,
        system_prompt: str,
        description: str = None,
        expert_type: str = "tech",
        category: str = "general",
        domain_keywords: List[str] = None,
        module_path: str = None,
        trigger_keywords: List[str] = None,
        trigger_paths: List[str] = None,
        trigger_topics: List[str] = None,
        weight: float = 1.0,
        version: str = "1.0",
        scope: str = "global",
        project_id: Optional[str] = None,
        is_active: bool = True,
    ) -> ExpertDefinition:
        """
        Create a new expert definition.

        Args:
            scope: 'global' for bundled experts, 'project' for project-specific
            project_id: Required if scope='project', must be None if scope='global'
            is_active: Whether expert is active (for soft delete support)
        """
        with self.session() as session:
            expert = ExpertDefinition(
                name=name,
                version=version,
                scope=scope,
                project_id=project_id,
                is_active=is_active,
                description=description,
                expert_type=expert_type,
                category=category,
                system_prompt=system_prompt,
                domain_keywords_json=json.dumps(domain_keywords or []),
                module_path=module_path,
                trigger_keywords_json=json.dumps(trigger_keywords or []),
                trigger_paths_json=json.dumps(trigger_paths or []),
                trigger_topics_json=json.dumps(trigger_topics or []),
                weight=weight,
            )
            session.add(expert)
            session.commit()
            session.refresh(expert)
            return expert

    def create_project_expert(
        self,
        project_id: str,
        name: str,
        system_prompt: str,
        description: str = None,
        expert_type: str = "domain",
        category: str = "general",
        trigger_keywords: List[str] = None,
        trigger_paths: List[str] = None,
        trigger_topics: List[str] = None,
        weight: float = 1.0,
    ) -> ExpertDefinition:
        """
        Create a project-specific expert.

        Convenience method that sets scope='project' automatically.
        """
        return self.create(
            name=name,
            system_prompt=system_prompt,
            description=description,
            expert_type=expert_type,
            category=category,
            trigger_keywords=trigger_keywords,
            trigger_paths=trigger_paths,
            trigger_topics=trigger_topics,
            weight=weight,
            scope="project",
            project_id=project_id,
            is_active=True,
        )

    def update(self, name: str, **updates) -> Optional[ExpertDefinition]:
        """Update an expert definition."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(ExpertDefinition.name == name)
            expert = session.execute(stmt).scalar_one_or_none()
            if not expert:
                return None

            # Handle JSON fields
            json_fields = ['domain_keywords', 'trigger_keywords', 'trigger_paths', 'trigger_topics']
            for field in json_fields:
                if field in updates:
                    updates[f'{field}_json'] = json.dumps(updates.pop(field))

            for key, value in updates.items():
                if hasattr(expert, key):
                    setattr(expert, key, value)

            session.commit()
            session.refresh(expert)
            return expert

    def delete(self, name: str, project_id: Optional[str] = None) -> bool:
        """Delete an expert definition (hard delete)."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.name == name,
                ExpertDefinition.project_id == project_id
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if expert:
                session.delete(expert)
                session.commit()
                return True
            return False

    def deactivate(self, name: str, project_id: Optional[str] = None) -> bool:
        """Soft delete an expert by setting is_active=False."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.name == name,
                ExpertDefinition.project_id == project_id
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if expert:
                expert.is_active = False
                session.commit()
                return True
            return False

    def activate(self, name: str, project_id: Optional[str] = None) -> bool:
        """Restore a soft-deleted expert by setting is_active=True."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.name == name,
                ExpertDefinition.project_id == project_id
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if expert:
                expert.is_active = True
                session.commit()
                return True
            return False

    def deactivate_by_project(self, project_id: str) -> int:
        """Deactivate all experts for a project (used during archive)."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.project_id == project_id,
                ExpertDefinition.is_active == True
            )
            experts = list(session.execute(stmt).scalars())
            count = 0
            for expert in experts:
                expert.is_active = False
                count += 1
            session.commit()
            return count

    def activate_by_project(self, project_id: str) -> int:
        """Activate all experts for a project (used during restore)."""
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.project_id == project_id,
                ExpertDefinition.is_active == False
            )
            experts = list(session.execute(stmt).scalars())
            count = 0
            for expert in experts:
                expert.is_active = True
                count += 1
            session.commit()
            return count

    def get_project_expert(
        self, expert_id: int, project_id: str
    ) -> Optional[ExpertDefinition]:
        """
        Get a specific project expert by ID with ownership check.

        Only returns experts that belong to the specified project.
        """
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.id == expert_id,
                ExpertDefinition.project_id == project_id,
                ExpertDefinition.scope == "project"
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if expert:
                session.expunge(expert)
            return expert

    def update_project_expert(
        self, expert_id: int, project_id: str, **kwargs
    ) -> Optional[ExpertDefinition]:
        """
        Update a project expert by ID with ownership check.

        Prevents changing scope or project_id.
        """
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.id == expert_id,
                ExpertDefinition.project_id == project_id,
                ExpertDefinition.scope == "project"
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if not expert:
                return None

            # Prevent changing scope or project_id
            kwargs.pop('scope', None)
            kwargs.pop('project_id', None)

            # Handle JSON fields
            json_fields = ['domain_keywords', 'trigger_keywords', 'trigger_paths', 'trigger_topics']
            for field in json_fields:
                if field in kwargs:
                    kwargs[f'{field}_json'] = json.dumps(kwargs.pop(field))

            for key, value in kwargs.items():
                if hasattr(expert, key):
                    setattr(expert, key, value)

            session.commit()
            session.refresh(expert)
            session.expunge(expert)
            return expert

    def delete_project_expert(self, expert_id: int, project_id: str) -> bool:
        """
        Soft delete a project expert by ID with ownership check.

        Sets is_active=False rather than hard deleting.
        """
        with self.session() as session:
            stmt = select(ExpertDefinition).where(
                ExpertDefinition.id == expert_id,
                ExpertDefinition.project_id == project_id,
                ExpertDefinition.scope == "project"
            )
            expert = session.execute(stmt).scalar_one_or_none()
            if not expert:
                return False

            expert.is_active = False
            session.commit()
            return True

    def to_dict(self, expert: ExpertDefinition) -> dict:
        """Convert expert definition to dictionary."""
        return {
            "id": expert.id,
            "name": expert.name,
            "version": expert.version,
            "scope": expert.scope,
            "project_id": expert.project_id,
            "is_active": expert.is_active,
            "description": expert.description,
            "expert_type": expert.expert_type,
            "category": expert.category,
            "module_path": expert.module_path,
            "domain_keywords": json.loads(expert.domain_keywords_json or "[]"),
            "system_prompt": expert.system_prompt,
            "weight": expert.weight,
            "trigger_keywords": json.loads(expert.trigger_keywords_json or "[]"),
            "trigger_paths": json.loads(expert.trigger_paths_json or "[]"),
            "trigger_topics": json.loads(expert.trigger_topics_json or "[]"),
            "created_at": expert.created_at.isoformat() if expert.created_at else None,
            "updated_at": expert.updated_at.isoformat() if expert.updated_at else None,
        }


# Singleton instance
_repository: Optional[ExpertDefinitionRepository] = None


def get_expert_definition_repository() -> ExpertDefinitionRepository:
    """Get singleton repository instance."""
    global _repository
    if _repository is None:
        _repository = ExpertDefinitionRepository()
    return _repository
