# Phase 3: Expert Loading Updates

**Priority:** P2 (Depends on Phase 2)

## Changes

### 3.1 Update ExpertLoader

**File:** `.orchestrator/core/expert_loader.py`

Update to use combined expert pool:

```python
class ExpertLoader:
    def __init__(self, project_root: Path, project_id: str = None):
        self.project_root = project_root
        self.project_id = project_id  # CHANGED: Renamed from project_slug
        self.console = Console()
        self._repo = None

    @property
    def repo(self):
        """Lazy-load expert repository."""
        if self._repo is None:
            from db.repositories.expert_definition import get_expert_definition_repository
            self._repo = get_expert_definition_repository()
        return self._repo

    def discover_experts(self, include_project: bool = True) -> List[ExpertDefinition]:
        """Discover all available experts.

        Args:
            include_project: If True and project_id is set, include project-specific experts.

        Returns:
            Combined list of global + project experts (if applicable).
        """
        if include_project and self.project_id:
            # Use combined pool
            return self.repo.list_combined(self.project_id)
        else:
            # Global only
            return self.repo.list_global()

    def get_expert(self, name: str) -> Optional[ExpertDefinition]:
        """Get a specific expert by name.

        Checks project-specific first, then global.
        """
        if self.project_id:
            # Check project-specific first
            experts = self.repo.list_by_project(self.project_id)
            for expert in experts:
                if expert.name == name:
                    return expert

        # Fall back to global
        return self.repo.get_by_name(name)

    # ... rest of methods unchanged ...
```

### 3.2 Update ExpertSelector

**File:** `.orchestrator/core/expert_selector.py`

Update to pass project_id to ExpertLoader:

```python
class ExpertSelector:
    def __init__(self, project_root: Path, project_id: str = None):
        self.project_root = project_root.resolve()
        self.project_id = project_id
        self.knowledge_store = KnowledgeStore(project_root)
        self.expert_loader = ExpertLoader(project_root, project_id=project_id)
        self._index: Optional[ExpertIndex] = None
```

### 3.3 Update Callers

Any code that creates `ExpertSelector` or `ExpertLoader` needs to pass `project_id`.

**File:** `.orchestrator/workflows/planning.py`

```python
# Find where ExpertSelector is instantiated
# Add project_id from context

from db.project_context import project_context

project_id = project_context.get_project_id()
selector = ExpertSelector(project_root, project_id=project_id)
```

**File:** `.orchestrator/workflows/building.py` (if it uses ExpertSelector)

Same pattern - get project_id from context and pass to selector.

## Verification

```python
# Test with a project that has custom experts
from core.expert_selector import ExpertSelector
from db.project_context import project_context

# Set project context
project_context.set_project_sync("test-project-id", "test-project")

# Create selector
selector = ExpertSelector(Path("/path/to/project"), project_id="test-project-id")

# Discover should include both global and project experts
experts = selector.expert_loader.discover_experts()
print(f"Total experts in pool: {len(experts)}")

# Check a project-specific expert is present (after creating one)
project_experts = [e for e in experts if e.scope == "project"]
print(f"Project-specific experts: {len(project_experts)}")
```
