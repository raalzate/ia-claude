# Phase 0 Research: Adaptive Investigation (Dynamic Decomposition)

## Decisions

### D-001 — Topology-first ordering

- **Decision**: `Planner.build_plan()` raises `TopologyNotYetMappedError` if
  no `TopologyMap` has been materialized in the current run. Plan cannot be
  constructed before exploration. AST test asserts `Planner.build_plan`'s
  body reads a `TopologyMap` instance before constructing `Plan`.
- **Rationale**: Spec US3 + FR-001. Rigid-plan anti-pattern is the #1 risk;
  making it structurally impossible beats advisory rules.
- **Alternatives**: Lint comment / review guideline — rejected (drift risk).

### D-002 — Topology mapping tools

- **Decision**: `pathlib.Path.rglob` + stdlib `re.compile` for regex search
  over file contents. No LLM-based mapping. These live inside
  `TopologyMapper` and are isolated from the `Planner` (so the Planner never
  sees raw filesystem I/O — Principle IV).
- **Rationale**: Deterministic, fast, auditable. Saves the API call budget
  for actual decision-making.

### D-003 — Budget shape

- **Decision**: `ExplorationBudget(max_wall_seconds=600, max_revisions=5)`.
  Exhaustion → `Planner.finalize_best_effort()` which emits the most recent
  plan with a `budget_exhausted=True` flag. No further revisions accepted.
- **Rationale**: Infinite-exploration anti-pattern needs a hard ceiling.
  These defaults fit workshop-scale codebases; override via constructor.

### D-004 — Plan-revision triggers

- **Decision**: Explicit enumerated triggers: `precondition_failed`,
  `new_dependency_discovered`, `cycle_detected`, `surprise_constraint`. Each
  revision carries its trigger verbatim; generic "other" is forbidden.
- **Rationale**: SC-004 demands every revision have a logged trigger; free
  text loses auditability.

### D-005 — Deterministic plan diff

- **Decision**: `PlanRevision.diff_summary` is computed via difflib over
  step-id sequences, not natural-language descriptions.
- **Rationale**: Repeatable across runs. Operators can grep revisions.

### D-006 — Cycle detection in dependency graph

- **Decision**: `TopologyMap.dependency_graph` builds a `networkx`-free
  adjacency dict; cycle detection uses iterative DFS coloring. `cycle_detected`
  trigger fires the moment a back-edge is seen; planner emits a
  "break cycle" step and re-plans.
- **Rationale**: Named dependency is one file; stdlib is enough; no extra
  package.

## Tessl Tiles

`tessl search investigation` / `tessl search planner` — no applicable tile.
None installed.

## Unknowns

None.
