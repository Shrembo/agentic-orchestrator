# Expert Architecture Refactor - Overview

## Goal

Implement clear separation between **global** (orchestrator-bundled) and **project-specific** (DB-stored) experts.

## Design Decisions

| Decision | Choice |
|----------|--------|
| Global agents/experts location | Orchestrator repo code (bundled) |
| Can projects override global? | No - projects can only ADD, not override |
| Project expert storage | DB only (clean repos) |
| Project expert management | Portal UI only |
| On project archive | Soft delete (recoverable) |
| Token impact | None (selection before injection) |

## Architecture

```
ORCHESTRATOR REPO (Immutable)
├── agents/
│   ├── planner.md       ← CORE (global)
│   ├── builder.md       ← CORE (global)
│   └── scout.md         ← CORE (global)
└── experts/
    ├── python.md        ← GLOBAL EXPERT
    ├── fastapi.md       ← GLOBAL EXPERT
    └── ...

DATABASE
├── expert_definitions
│   ├── scope='global'   ← Seeded from repo
│   └── scope='project'  ← Created via Portal
└── expert_index         ← Per-project, combines both pools
```

## Phases

| Phase | Priority | Description |
|-------|----------|-------------|
| [01](./01-database-schema.md) | P0 | Database schema changes |
| [02](./02-repository-layer.md) | P1 | Repository scope-aware methods |
| [03](./03-expert-loading.md) | P2 | Expert loader combines pools |
| [04](./04-portal-api.md) | P3 | Portal API for project experts |
| [05](./05-project-lifecycle.md) | P4 | Archive/restore hooks |

## Selection Flow (After Implementation)

```
Request → ExpertSelector
            │
            ├─ Load global experts (20+)
            ├─ Load project experts (5-10)
            ├─ Score ALL by relevance
            └─ Return top 3
                   │
                   ▼
          Same token cost as before
```
