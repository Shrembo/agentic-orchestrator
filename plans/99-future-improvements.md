# Future Improvements (Backlog)

These were identified during analysis but are **out of scope** for the current expert architecture work.

---

## 1. Build Failure UX Improvements

**Priority:** High (separate PR)

### Problem
When a build step fails, users see truncated error messages and no guidance on what to do next.

### Current Gaps
- `last_error` truncated to 60 chars in API responses
- No error categorization (transient vs permanent)
- No step context in failure messages
- Retry history stored but not exposed via API

### Recommended Changes

1. **Add `/api/plans/{plan_id}/steps/{step_id}/error-details` endpoint**
   - Return full error, retry history, full output
   - Include files affected and step context

2. **Add error categorization**
   - Update StepState model with `error_type` field
   - Values: `transient`, `permanent`, `unknown`
   - Guide retry decisions

3. **Improve failure messages**
   - Include step description and target
   - Show what was being attempted
   - Suggest recovery actions

### Files to Modify
- `.orchestrator/workflows/building.py` (lines 1430-1472)
- `.orchestrator/portal/routes/plans.py` (add endpoint)
- `.orchestrator/db/models.py` (add error_type to StepState)

---

## 2. Dead Code Cleanup

**Priority:** Medium (separate PR)

### Deprecated Modules (Safe to Remove)

| File | Status | Replacement |
|------|--------|-------------|
| `.orchestrator/db/config.py` | Deprecated wrapper | Import from `config` module |
| `.orchestrator/portal/config.py` | Deprecated wrapper | Import from `config` module |
| `RegistryFallbackProjectProvider` in project_context.py | Deprecated | DatabaseProjectProvider |

### Duplicate Code

| Location | Issue | Action |
|----------|-------|--------|
| `building.py:759` `_is_placeholder_response()` | Duplicate of agent.py | Remove from building.py |

### Incomplete Features

| File | Line | Issue |
|------|------|-------|
| `workflow_runner.py:987` | TODO: Implement ReviewingWorkflow | Implement or remove stub |
| `projects.py:338` | TODO: auto_index scout trigger | Implement or remove |

### Old File Storage

Run cleanup migration to remove:
- `.orchestrator/config/*.json` (migrated to DB)
- `.orchestrator/agents/*.md` (migrated to DB - but keep as source of truth?)

**Note:** Consider keeping agent/*.md files as source of truth, seeded to DB on startup.

### Scout Workflow Consolidation

Multiple overlapping implementations:
- `scouting.py` (original)
- `smart_scouting.py` (advanced)
- `unified_scout.py` (newest)

**Recommendation:** Audit usage and consolidate to single implementation.

---

## 3. File-Based Budget Storage

**Priority:** Low

### Problem
`BudgetManager` in `core/cost.py` still reads/writes to `budget.json` file as fallback.

### Action
Fully migrate to database, remove JSON fallback (lines 412-430).

---

## Implementation Order

1. **Expert Architecture** (current plan) - Foundation for project-specific config
2. **Build Failure UX** - High user impact
3. **Dead Code Cleanup** - Technical debt reduction
4. **Budget Migration** - Low priority, minor cleanup
