# Phase 1 Data Model: Adaptive Investigation

Pydantic v2 models at `katas/019_adaptive_investigation/models.py`.

## ExploratoryDirective

Input to the investigation run.

| Field | Type | Notes |
|-------|------|-------|
| `directive_id` | `str` | UUID. |
| `prompt` | `str` | e.g. "Add tests for the payments module". |
| `target_path` | `str` | Repo-root-relative. |
| `budget` | `ExplorationBudget` | |

## TopologyMap

Produced by `TopologyMapper` before any `Plan` is built.

| Field | Type | Notes |
|-------|------|-------|
| `generated_at` | `datetime` | UTC. |
| `modules` | `list[ModuleNode]` | One per discovered package/module. |
| `dependency_graph` | `dict[str, list[str]]` | Adjacency list by module id. |
| `coverage_flags` | `dict[str, bool]` | module_id → has_tests. |

## ModuleNode

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | e.g. `katas.005_defensive_extraction`. |
| `path` | `str` | |
| `size_bytes` | `int` | |
| `external_deps` | `list[str]` | Best-effort import analysis. |

## Plan

A prioritized, structured plan. Never prose.

| Field | Type | Notes |
|-------|------|-------|
| `plan_id` | `str` | UUID per revision. |
| `directive_id` | `str` | FK. |
| `steps` | `list[PlanStep]` | Ordered by priority then position. |
| `created_at` | `datetime` | UTC. |
| `revision_index` | `int` (≥ 0) | 0 = initial. |
| `budget_exhausted` | `bool` | Set on final best-effort plan (D-003). |

## PlanStep

| Field | Type | Notes |
|-------|------|-------|
| `step_id` | `str` | Stable across revisions when semantically the same. |
| `priority` | `int` | Lower = sooner. |
| `description` | `str` | Short machine-grep-able label. |
| `affects_modules` | `list[str]` | ModuleNode ids. |
| `preconditions` | `list[str]` | e.g. `step_id=="mock_external_deps"`. |

## PlanRevision

| Field | Type | Notes |
|-------|------|-------|
| `revision_id` | `str` | UUID. |
| `plan_id` | `str` | FK. |
| `trigger` | `Literal["precondition_failed", "new_dependency_discovered", "cycle_detected", "surprise_constraint"]` | Enumerated, no "other". |
| `diff_summary` | `str` | Computed via difflib over step-id sequences. |
| `timestamp` | `datetime` | UTC. |

## ExplorationBudget

| Field | Type | Notes |
|-------|------|-------|
| `max_wall_seconds` | `int` (≥ 1) | Default 600. |
| `max_revisions` | `int` (≥ 1) | Default 5. |
| `started_at` | `datetime \| None` | Set on first plan build. |

**Exhaustion**: any predicate fires → `Planner.finalize_best_effort()` → final
plan emitted with `budget_exhausted=True`; further revisions raise.

## Relationships

```
ExploratoryDirective
  └── TopologyMap (built first — cannot plan without this)
        └── Plan (revision_index=0, then 1..max_revisions)
              └── PlanRevision (one per transition)
```
