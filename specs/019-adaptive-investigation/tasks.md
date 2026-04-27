# Tasks: Adaptive Investigation (Dynamic Decomposition)

**Input**: Design documents from `/specs/019-adaptive-investigation/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] on story tasks
- Traceability: `[TS-001, TS-002]`, never prose ranges

## Phase 1: Setup

- [ ] T001 Create package skeleton `katas/019_adaptive_investigation/__init__.py` and test package skeleton `tests/katas/019_adaptive_investigation/__init__.py` (+ `unit/`, `lint/`, `integration/`, `features/`, `step_defs/`, `fixtures/` subpackages with empty `__init__.py`)
- [ ] T002 [P] Ensure `pyproject.toml` extras include `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, `jsonschema` under `[project.optional-dependencies].dev`; install with `pip install -e ".[dev]"`
- [ ] T003 [P] Add `runs/` to `.gitignore` (plan.md §Storage — per-session `events.jsonl`, `topology-map.json`, `plan-revisions.jsonl` must never be tracked)
- [ ] T004 [P] Configure `pytest.ini` / `pyproject.toml` `[tool.pytest.ini_options]` to register `bdd_features_base_dir = tests/katas/019_adaptive_investigation/features` and collect `tests/katas/019_adaptive_investigation`

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [ ] T005 Define pydantic v2 models in `katas/019_adaptive_investigation/models.py`: `ExploratoryDirective`, `TopologyMap`, `ModuleNode`, `Plan`, `PlanStep`, `PlanRevision`, `TriggerEvent`, `ExplorationBudget` with `model_config = ConfigDict(extra="forbid")` per data-model.md (FR-002, FR-005, FR-008)
- [ ] T006 Define the `TriggerCategory` Literal enum in `katas/019_adaptive_investigation/models.py` with values `precondition_failed`, `new_dependency_discovered`, `cycle_detected`, `surprise_constraint`, `budget_exhausted`, `directive_contradiction`, `tooling_unavailable` (FR-005, SC-004, plan.md Constraints)
- [ ] T007 Define terminal exceptions in `katas/019_adaptive_investigation/models.py`: `TopologyFirstViolation` (raised when `Planner` constructs a `Plan` before a `TopologyMap` materializes), `BudgetExhaustedError`, `RevisionAfterBudgetExhaustion`
- [ ] T008 [P] Implement injectable Anthropic client wrapper in `katas/019_adaptive_investigation/client.py` mirroring Kata 1 D-001 (class exposing `messages_create(**kwargs)` seam so planner tests can inject a `RecordedClient`)
- [ ] T009 [P] Copy JSON Schemas from `specs/019-adaptive-investigation/contracts/` (`exploratory-directive.schema.json`, `topology-map.schema.json`, `plan.schema.json`, `plan-revision.schema.json`, `budget.schema.json`) into a loader helper accessible from `katas/019_adaptive_investigation/models.py` so contract tests can validate against Draft 2020-12
- [ ] T010 Wire per-run audit writer in `katas/019_adaptive_investigation/revision_log.py`: opens `runs/<session-id>/plan-revisions.jsonl` append-only, `topology-map.json`, and `events.jsonl` handles; the coordinator (not the planner) owns the filesystem handle so `planner.py` stays side-effect-free (FR-005, plan.md §Structure Decision)

**Checkpoint**: Models + exceptions + client seam + audit writer all importable; no business logic yet.

## Phase 3: User Story 1 — Open Directive Triggers Topology-First Planning (Priority: P1) [US1]

**Goal**: Coordinator refuses to emit a plan until a `TopologyMap` is materialized; every high-priority `PlanStep` back-points to a discovered `ModuleNode` id.

**Independent Test**: Run the `happy_path/` fixture; assert the first observable tool calls are `pathlib.rglob` + `re.search` sweeps, that the emitted `Plan` validates against `contracts/plan.schema.json`, and that every `PlanStep` with priority <= configured high-priority threshold lists at least one `topology_refs` entry present in the recorded `TopologyMap`.

### Tests for User Story 1 (write first; all must fail before implementation)

- [ ] T011 [P] [US1] Copy `tests/features/topology_first_planning.feature` from `specs/019-adaptive-investigation/tests/features/` into `tests/katas/019_adaptive_investigation/features/topology_first_planning.feature` (verbatim — DO NOT MODIFY SCENARIOS)
- [ ] T012 [P] [US1] Create recorded fixture directory `tests/katas/019_adaptive_investigation/fixtures/happy_path/` containing a synthetic mini-codebase (three uncovered `.py` modules) plus a recorded `Planner` SDK session
- [ ] T013 [US1] Step definitions for `@TS-001` in `tests/katas/019_adaptive_investigation/step_defs/test_topology_first_steps.py`: "Topology mapping precedes plan emission" [TS-001]
- [ ] T014 [US1] Step definitions for `@TS-002` in the same file: "Emitted plan is structured and grounded in discovered modules" [TS-002]
- [ ] T015 [US1] Step definitions for `@TS-003` in the same file: "Every prioritized plan item traces to a topology finding" [TS-003]
- [ ] T016 [US1] Step definitions for `@TS-004` in the same file: "Planner module never constructs a Plan before TopologyMap materializes" (AST lint) [TS-004]
- [ ] T017 [US1] Step definitions for `@TS-005` in the same file: "Emitted Plan conforms to the declared JSON schema" (contract) [TS-005]
- [ ] T018 [P] [US1] AST lint test `tests/katas/019_adaptive_investigation/lint/test_topology_first.py` asserting no code path in `planner.py` constructs a `Plan` before a `TopologyMap` is observed in the run (AST + runtime guard per plan.md Constraints) [TS-004, FR-001]
- [ ] T019 [P] [US1] AST lint test `tests/katas/019_adaptive_investigation/lint/test_no_prose_matching.py` asserting `katas/019_adaptive_investigation/planner.py` does NOT `import re`, call `str.find`, or use `in` on a `str` literal (Principle I NN, plan.md Constraints) [FR-002]
- [ ] T020 [P] [US1] AST lint test `tests/katas/019_adaptive_investigation/lint/test_re_scoped_to_mapper.py` asserting `import re` appears ONLY in `katas/019_adaptive_investigation/topology_mapper.py` across the kata package (plan.md §Complexity Tracking — scoped `re` exception)
- [ ] T021 [P] [US1] Unit test `tests/katas/019_adaptive_investigation/unit/test_topology_mapper.py` asserting `TopologyMapper` performs at least one filename-pattern query and one regex-search query and returns a `TopologyMap` whose `modules` and `dependency_graph` are populated from the real fixture tree [FR-001]
- [ ] T022 [P] [US1] Unit test `tests/katas/019_adaptive_investigation/unit/test_planner_emits_structured_plan.py` asserting the `Plan` returned by `Planner.build_plan(topology_map, directive)` has explicit integer priorities, ordered `steps`, and every high-priority step has non-empty `topology_refs` resolving to nodes in the input `TopologyMap` [FR-002, FR-008, TS-002, TS-003]

### Implementation for User Story 1

- [ ] T023 [US1] Implement `TopologyMapper` class in `katas/019_adaptive_investigation/topology_mapper.py`: `sweep(target_path) -> TopologyMap` using `pathlib.Path.rglob` for filename-pattern pass and `re.compile` / `re.search` for content regex pass; this is the ONLY module permitted to `import re` (plan.md §Complexity Tracking, FR-001)
- [ ] T024 [US1] Implement `TopologyMapper.detect_cycles()` returning a list of cycles over `dependency_graph` adjacency, used later by US2 cycle path; flag-only semantics (no recursion) per plan.md Constraints
- [ ] T025 [US1] Implement `Planner` class in `katas/019_adaptive_investigation/planner.py`: `build_plan(topology_map: TopologyMap, directive: ExploratoryDirective) -> Plan` with a runtime guard that raises `TopologyFirstViolation` if `topology_map is None` (FR-001, TS-004)
- [ ] T026 [US1] Inside `Planner.build_plan`, construct `PlanStep` instances whose `affects_modules` / high-priority entries draw ONLY from `topology_map.modules` ids; any step that cannot be traced back is rejected at construction (FR-008, TS-003)
- [ ] T027 [US1] Implement `Coordinator` class in `katas/019_adaptive_investigation/coordinator.py`: owns `session_id`, `budget: ExplorationBudget`, `mapper: TopologyMapper`, `planner: Planner`, `revision_log: RevisionLog`; `run(directive)` orchestrates `mapper.sweep → planner.build_plan → revision_log.append(initial revision)` in that order (plan.md Architecture, FR-001)
- [ ] T028 [US1] Implement CLI entry in `katas/019_adaptive_investigation/runner.py`: `python -m katas.019_adaptive_investigation.runner --directive --target --max-seconds --max-revisions`; reads `LIVE_API` env to choose real vs. recorded client (quickstart.md)

**Checkpoint**: `pytest tests/katas/019_adaptive_investigation/features/topology_first_planning.feature tests/katas/019_adaptive_investigation/lint tests/katas/019_adaptive_investigation/unit/test_topology_mapper.py tests/katas/019_adaptive_investigation/unit/test_planner_emits_structured_plan.py` passes. US1 delivers an MVP end-to-end: open directive in, topology-first grounded plan out.

## Phase 4: User Story 2 — Injected Surprise Forces Plan Re-adaptation (Priority: P2) [US2]

**Goal**: When an unknown external dependency surfaces during plan execution, the coordinator halts the current step, produces an immutable new `PlanRevision` with a structured `trigger`, inserts an isolation step, and resumes execution from the revised plan only.

**Independent Test**: Run the `injected_surprise/` fixture (a hidden network client planted inside the codebase). Scan `runs/<session-id>/plan-revisions.jsonl`: expect exactly one revision with `trigger.category="new_dependency_discovered"`, a new isolation step preceding any step that exercises the dependency, and that the next step dispatched after the revision comes from the revised plan.

### Tests for User Story 2

- [ ] T029 [P] [US2] Copy `tests/features/plan_readaptation_on_surprise.feature` into `tests/katas/019_adaptive_investigation/features/plan_readaptation_on_surprise.feature` (verbatim)
- [ ] T030 [P] [US2] Create fixture `tests/katas/019_adaptive_investigation/fixtures/injected_surprise/` — synthetic codebase with a hidden network client planted mid-execution plus recorded planner session showing the revision + isolation step
- [ ] T031 [US2] Step definitions for `@TS-006` in `tests/katas/019_adaptive_investigation/step_defs/test_plan_readaptation_steps.py`: "Discovery of unknown external dependency halts step and creates revision" [TS-006]
- [ ] T032 [US2] Step definitions for `@TS-007` in the same file: "Resumed execution draws from the revised plan only" [TS-007]
- [ ] T033 [US2] Step definitions for `@TS-008` in the same file: "External-call surprise inserts an isolation step before any exercising step" [TS-008]
- [ ] T034 [US2] Step definitions for `@TS-009` in the same file: "Prior plan revisions are immutable once superseded" [TS-009]
- [ ] T035 [US2] Step definitions for `@TS-010` in the same file: "Every PlanRevision entry conforms to the declared JSON schema" (contract) [TS-010]
- [ ] T036 [P] [US2] Unit test `tests/katas/019_adaptive_investigation/unit/test_planner_revises_on_trigger.py` asserting `Planner.revise(prior_plan, trigger)` returns a NEW `Plan` with a higher `revision_index` and that the prior `Plan` object is unchanged (FR-003, TS-009)
- [ ] T037 [P] [US2] Integration test `tests/katas/019_adaptive_investigation/integration/test_injected_surprise.py` running `Coordinator.run` against the `injected_surprise/` fixture and asserting the `plan-revisions.jsonl` sequence and isolation-step placement (SC-002, TS-008)
- [ ] T038 [P] [US2] Integration test `tests/katas/019_adaptive_investigation/integration/test_plan_revision_log_shape.py` asserting every line of `plan-revisions.jsonl` validates against `contracts/plan-revision.schema.json` with `additionalProperties: false` and a non-null `trigger` whose `category` is an enumerated `TriggerCategory` value (FR-005, SC-004, TS-010)

### Implementation for User Story 2

- [ ] T039 [US2] Implement `Planner.revise(prior_plan: Plan, trigger: TriggerEvent) -> Plan` returning an IMMUTABLE new `Plan` with `revision_index = prior.revision_index + 1`; prior plan must remain unchanged by construction (pydantic frozen model + defensive copy) (FR-003, TS-009)
- [ ] T040 [US2] Implement isolation-insertion rule inside `Planner.revise`: when `trigger.category == "new_dependency_discovered"` and the discovered dependency is external/network-like, prepend an isolation/mock `PlanStep` via `preconditions` so every step that would exercise the dependency lists the isolation `step_id` as a precondition (TS-008, FR-003)
- [ ] T041 [US2] Implement `Coordinator` execution loop: iterate `plan.steps`, before each step re-check preconditions against the current `TopologyMap` / execution state; on any precondition failure or freshly discovered dependency, emit a `TriggerEvent`, call `Planner.revise`, append the new `PlanRevision` to `plan-revisions.jsonl`, and resume dispatching from the revised plan (FR-003, FR-005, TS-006, TS-007)
- [ ] T042 [US2] Implement `RevisionLog.append(revision: PlanRevision)` in `katas/019_adaptive_investigation/revision_log.py`: serialize with `model_dump_json()`, append-only write, enforces that `trigger` is non-null and `category` is one of `TriggerCategory` before the line is written; coalesces or flags duplicates (see US3 / edge-case task T054) (FR-005, SC-004, TS-010)
- [ ] T043 [US2] Ensure `Coordinator` halts the in-flight step BEFORE the revision write (step is not committed as "completed") and that step dispatch resumes from the new revision only (TS-006, TS-007)

**Checkpoint**: `pytest tests/katas/019_adaptive_investigation/features/plan_readaptation_on_surprise.feature tests/katas/019_adaptive_investigation/unit/test_planner_revises_on_trigger.py tests/katas/019_adaptive_investigation/integration/test_injected_surprise.py tests/katas/019_adaptive_investigation/integration/test_plan_revision_log_shape.py` passes. Rigid-plan anti-pattern is observably defended.

## Phase 5: User Story 3 — Bounded Exploration Still Produces a Plan (Priority: P3) [US3]

**Goal**: An `ExplorationBudget` (wall-clock seconds + revision count) forces the coordinator to converge on a structured plan even when topology mapping is incomplete, labels that plan `budget_exhausted=True` with a confidence indicator, and rejects further revisions.

**Independent Test**: Run the `budget_limited/` oversized fixture with `max_wall_seconds=1` or `max_revisions=1`; assert the run halts at or before budget exhaustion, emits a structured `Plan` with `budget_exhausted=True` and a `partial_topology` / confidence annotation, and that the final `PlanRevision` carries `trigger.category="budget_exhausted"`.

### Tests for User Story 3

- [ ] T044 [P] [US3] Copy `tests/features/bounded_exploration_budget.feature` into `tests/katas/019_adaptive_investigation/features/bounded_exploration_budget.feature` (verbatim)
- [ ] T045 [P] [US3] Create fixture `tests/katas/019_adaptive_investigation/fixtures/budget_limited/` — oversized synthetic corpus that cannot be fully mapped within the default `ExplorationBudget`
- [ ] T046 [US3] Step definitions for `@TS-011` in `tests/katas/019_adaptive_investigation/step_defs/test_bounded_budget_steps.py`: "Budget exhaustion halts exploration and still yields a structured plan" [TS-011]
- [ ] T047 [US3] Step definitions for `@TS-012` in the same file: "Budget-limited plan carries a partial-topology annotation and confidence indicator" [TS-012]
- [ ] T048 [US3] Step definitions for `@TS-013` in the same file: "No run performs unbounded topology mapping without emitting a plan" [TS-013]
- [ ] T049 [US3] Step definitions for `@TS-014` in the same file: "Budget exhaustion is itself a logged trigger event" [TS-014]
- [ ] T050 [US3] Step definitions for `@TS-015` Scenario Outline in the same file: "ExplorationBudget predicates trip on the configured bound" (examples: `max_wall_seconds=1`, `max_revisions=1`, `max_wall_seconds=30`, `max_revisions=5`) [TS-015]
- [ ] T051 [P] [US3] Unit test `tests/katas/019_adaptive_investigation/unit/test_budget_enforcer.py` asserting `ExplorationBudget.check()` trips deterministically at or before each configured bound and emits a `TriggerEvent(category="budget_exhausted")` (FR-004, SC-003, TS-015)
- [ ] T052 [P] [US3] Integration test `tests/katas/019_adaptive_investigation/integration/test_budget_limited_annotation.py` asserting a budget-limited run's final `Plan` carries `budget_exhausted=True`, a `partial_topology` annotation, and a `confidence` indicator surfaced in `plan.schema.json` (FR-006, TS-012)

### Implementation for User Story 3

- [ ] T053 [US3] Implement `ExplorationBudget` predicates in `katas/019_adaptive_investigation/budget.py`: `check()` evaluates wall-clock vs. `max_wall_seconds` and revision count vs. `max_revisions`, returns a `TriggerEvent(category="budget_exhausted")` on trip; `started_at` is stamped on first call (FR-004, data-model.md)
- [ ] T054 [US3] Implement `Planner.finalize_best_effort(topology_map, directive)` emitting a final structured `Plan` with `budget_exhausted=True`, `partial_topology=True`, and a `confidence` indicator computed from topology coverage; subsequent `revise` calls raise `RevisionAfterBudgetExhaustion` (FR-006, SC-003, TS-012, TS-014)
- [ ] T055 [US3] Wire budget checks into `Coordinator.run`: call `budget.check()` before each mapper pass and before each `planner.revise`; on trip, route through `Planner.finalize_best_effort`, append the final `PlanRevision` with `trigger.category="budget_exhausted"`, and halt (FR-004, SC-003, TS-011, TS-014)
- [ ] T056 [US3] Extend `plan.schema.json` consumers so the contract test accepts `budget_exhausted`, `partial_topology`, and `confidence` fields under `extra="forbid"`; if the live schema lacks them, update the pydantic `Plan` model to expose those fields without silently adding `additionalProperties: true` (FR-006, TS-012)

**Checkpoint**: `pytest tests/katas/019_adaptive_investigation/features/bounded_exploration_budget.feature tests/katas/019_adaptive_investigation/unit/test_budget_enforcer.py tests/katas/019_adaptive_investigation/integration/test_budget_limited_annotation.py` passes. Endless-exploration anti-pattern is observably defended.

## Phase 6: Edge Cases & Contradictions (spans US1/US2/US3)

**Goal**: Surface contradictions, degrade gracefully on tool failure, flag cycles, coalesce duplicate revisions, and handle trivial topologies — without falling back to prose matching.

### Tests

- [ ] T057 [P] Copy `tests/features/edge_cases_and_contradictions.feature` into `tests/katas/019_adaptive_investigation/features/edge_cases_and_contradictions.feature` (verbatim)
- [ ] T058 [P] Create fixtures `tests/katas/019_adaptive_investigation/fixtures/cyclic_dependency/`, `tests/katas/019_adaptive_investigation/fixtures/trivial_topology/`, and `tests/katas/019_adaptive_investigation/fixtures/contradicting_surprise/` (per plan.md §Project Structure and quickstart.md mapping)
- [ ] T059 Step definitions for `@TS-016` in `tests/katas/019_adaptive_investigation/step_defs/test_edge_cases_steps.py`: "Discovery that contradicts the original directive halts with escalation" [TS-016]
- [ ] T060 Step definitions for `@TS-017` in the same file: "Topology tool failure triggers safe-default plan with tooling-unavailable trigger" [TS-017]
- [ ] T061 Step definitions for `@TS-018` in the same file: "Cyclic dependency in the topology map forces a revision with an explicit cut point" [TS-018]
- [ ] T062 Step definitions for `@TS-019` in the same file: "Duplicate plan revisions are coalesced or flagged to prevent log spam" [TS-019]
- [ ] T063 Step definitions for `@TS-020` in the same file: "Trivial topology still produces a plan with a trivial-topology flag" [TS-020]
- [ ] T064 [P] Unit test `tests/katas/019_adaptive_investigation/unit/test_cycle_detection.py` asserting `TopologyMapper.detect_cycles()` returns at least one cycle for the `cyclic_dependency/` fixture and that `Planner.revise` emits a `trigger.category="cycle_detected"` plus a `PlanStep` marked as a cut point (TS-018, FR-003)
- [ ] T065 [P] Unit test `tests/katas/019_adaptive_investigation/unit/test_directive_contradiction.py` asserting a discovery contradicting the directive raises through `TriggerEvent(category="directive_contradiction")`, halts execution, and does NOT emit a further plan revision (TS-016, FR-007)

### Implementation

- [ ] T066 Implement tool-failure handling in `Coordinator.run`: when `TopologyMapper.sweep` raises or returns empty, emit `TriggerEvent(category="tooling_unavailable")`, call `Planner.finalize_safe_default(directive)` to produce a minimal plan labeled `tooling_unavailable`, and log the revision (TS-017, FR-001, FR-005)
- [ ] T067 Implement directive-contradiction escalation: when a trigger with `category="directive_contradiction"` is observed, `Coordinator.run` halts, appends the revision with an `escalation` payload, and returns a labeled escalation result instead of continuing (TS-016, FR-007, Principle VI)
- [ ] T068 Implement cycle-trigger path: after `TopologyMapper.detect_cycles()` returns non-empty, `Coordinator.run` emits `TriggerEvent(category="cycle_detected")` and `Planner.revise` inserts an explicit cut-point `PlanStep` rather than recursing into the cycle (TS-018, FR-003, plan.md Constraints)
- [ ] T069 Implement duplicate-revision coalescing inside `RevisionLog.append`: compute a stable hash over `(plan_id, step_id sequence, trigger.category)`; if identical to the immediately prior revision, either skip the append (coalesce) or write a `noop=True` marker record, never both (TS-019, FR-005)
- [ ] T070 Implement trivial-topology flag in `Planner.build_plan`: when the input `TopologyMap.modules` has exactly one entry, emit a plan with a `trivial_topology=True` flag and do not fabricate additional steps (TS-020, FR-002, spec Edge Case)

**Checkpoint**: `pytest tests/katas/019_adaptive_investigation/features/edge_cases_and_contradictions.feature tests/katas/019_adaptive_investigation/unit/test_cycle_detection.py tests/katas/019_adaptive_investigation/unit/test_directive_contradiction.py` passes.

## Final Phase: Polish & Cross-Cutting Concerns

### Documentation (Principle VIII — Mandatory Documentation)

- [ ] T071 [P] Author `katas/019_adaptive_investigation/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — topology-first sweep (filename-pattern + regex data-scan, `re` scoped to `topology_mapper`), adaptive loop (evidence → hypothesis → probe), `TopologyFirstViolation` runtime guard + `test_topology_first.py` AST lint, exploration budget (wall-clock + revision cap), plan revision triggers, `directive_contradiction` halt condition, signal-driven planner (no prose matching), append-only revision log with non-null trigger invariant — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`coordinator` → `topology_mapper` → `planner` → `budget` → `revision_log` → `models` → `client` → `runner`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — evidence-before-hypothesis, bounded-exploration, structured-revision-trigger, fail-loud-on-budget-exhaustion — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (I Determinism, II Schema-First, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — `PlanStep` schema (`step_id`, `priority`, `description`, `affects_modules`, `preconditions`, `topology_refs`); `PlanRevision` schema with enumerated `TriggerCategory`; stopping condition — coordinator halts when EITHER `plan.budget_exhausted is True`, OR a `directive_contradiction` trigger fires, OR the plan has no unexecuted steps remaining (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T072 [P] Add module-level docstrings to every file explaining its role in the adaptive-investigation loop: `coordinator.py` (hub, owns budget + revision log + orchestration), `topology_mapper.py` (filename-pattern + regex data-scan — the ONLY module permitted to import `re`), `planner.py` (signal-driven plan/revise; prose-matching forbidden), `budget.py` (wall-clock + revision cap enforcer), `revision_log.py` (append-only JSONL with non-null trigger invariant), `models.py` (typed handoff contract with `extra="forbid"`), `client.py` (Anthropic seam), `runner.py` (CLI entry point)
- [ ] T073 [P] Add why-comments on non-trivial functions: `TopologyMapper.sweep` (why `re` is scoped here per plan.md §Complexity Tracking — data scanning, not control-flow classification), `Planner.build_plan` (why the `TopologyFirstViolation` guard is load-bearing for FR-001 and US1 anti-pattern defense), `Planner.revise` (why a NEW immutable `Plan` per trigger, FR-003, TS-009), `Planner.finalize_best_effort` (why budget exhaustion must still emit a structured plan, SC-003), `RevisionLog.append` (why `trigger` is non-null before write, FR-005, SC-004), `ExplorationBudget.check` (why the loop trip is a `TriggerEvent`, not an exception, FR-004)
- [ ] T075 [P] Verify `specs/019-adaptive-investigation/quickstart.md` matches the implemented CLI flags, fixture paths, and `runs/<session-id>/` layout; update any drift (quickstart "Done" checklist items for `tasks.md`, `.feature`, a final markdown cell of `notebook.ipynb`)

### Validation

- [ ] T076 Run quickstart validation: execute every command in `specs/019-adaptive-investigation/quickstart.md` top-to-bottom (`pip install -e ".[dev]"`, `pytest tests/katas/019_adaptive_investigation -v`, optional `LIVE_API=1` CLI run); confirm all assertions pass and `runs/<session-id>/plan-revisions.jsonl` + `final_plan.json` are produced as documented
- [ ] T077 [P] Run `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` to refresh dashboard after adding `katas/019_adaptive_investigation/` files and `tasks.md`
- [ ] T078 [P] Ensure `.specify/context.json` assertion-integrity hashes for US-001, US-002, US-003 feature files plus the edge-cases feature file are present and locked (re-run `/iikit-04-testify` only if feature files changed; otherwise verify hashes match)
- [ ] T079 Full test sweep: `pytest tests/katas/019_adaptive_investigation -v --strict-markers` green; AST lint (T018, T019, T020) green; SC-001 (every run emits a structured plan) verified across fixtures; SC-002 (injected-surprise revision rate) verified on `injected_surprise/`; SC-003 (no endless-exploration runs) verified on `budget_limited/`; SC-004 (every revision has a logged trigger) verified by re-running `test_plan_revision_log_shape.py`

## Dependencies & Execution Order

- **Phase 1 (Setup, T001–T004)** → must complete before Phase 2
- **Phase 2 (Foundational, T005–T010)** → models, exceptions, client seam, audit writer block all user stories
- **Phase 3 (US1, T011–T028)** → depends on Phase 2; delivers MVP end-to-end (topology-first plan)
- **Phase 4 (US2, T029–T043)** → depends on Phase 3 (Coordinator.run + Planner + revision_log exist); re-adaptation extends, not rewrites
- **Phase 5 (US3, T044–T056)** → depends on Phase 2 + Phase 3; budget predicates plug into the Phase 3 coordinator loop and the Phase 4 revise path
- **Phase 6 (Edge cases, T057–T070)** → depends on Phase 3 + Phase 4 + Phase 5 scaffolding; tests and implementations may land alongside the relevant user story if preferred
- **Final Phase (T071–T079)** → depends on all prior phases complete

User-story independence: each US can be verified in isolation via its own feature file + fixture set; Phase 6 edge cases explicitly span US1/US2/US3 per the `@US-001 @US-002 @US-003` tags on `edge_cases_and_contradictions.feature`.

## Parallel Opportunities

Within a single phase, tasks marked `[P]` touch disjoint files and may be run in parallel:

- **Phase 1**: T002, T003, T004 parallel (different config files)
- **Phase 2**: T008, T009 parallel (distinct modules)
- **Phase 3 tests**: T011, T012, T018, T019, T020, T021, T022 parallel (feature copy, fixture, three lint tests, two unit tests — no overlap)
- **Phase 4 tests**: T029, T030, T036, T037, T038 parallel (feature copy, fixture, unit + two integration tests)
- **Phase 5 tests**: T044, T045, T051, T052 parallel (feature copy, fixture, unit + integration)
- **Phase 6 tests**: T057, T058, T064, T065 parallel (feature copy, fixtures, two unit tests)
- **Final Phase docs**: T071, T072, T073, T075 parallel (notebook, docstrings, why-comments, quickstart verify touch disjoint files)
- **Final Phase validation**: T077, T078 parallel after T076

Step-definition files (T013–T017, T031–T035, T046–T050, T059–T063) are sequential within each file because they share a single Python module per feature.

## Implementation Strategy

1. Land **Phase 1 + Phase 2** together — foundational models, exceptions, client seam, and audit writer surface no business logic yet.
2. Land **US1 MVP** (Phase 3) — at checkpoint the kata runs end-to-end on `happy_path/` and the rigid-plan anti-pattern is structurally blocked by `test_topology_first.py`.
3. Land **US2 re-adaptation** (Phase 4) — adds the observable proof that the plan is mutable under typed triggers; this is where the kata's pedagogical core (adaptive investigation loop) becomes testable.
4. Land **US3 bounded exploration** (Phase 5) — adds the safety rail: the endless-exploration anti-pattern is observably blocked by `test_budget_enforcer.py`.
5. Land **Phase 6 edge cases** — polishes the trigger taxonomy (cycle, contradiction, tooling-unavailable, duplicate, trivial topology).
6. Close with **Final Phase** — Principle VIII `notebook.ipynb` + docstrings + why-comments, quickstart re-run, dashboard refresh.

Suggested commit cadence: one commit per phase checkpoint; additional commits for doc polish are fine.

## Notes

- Feature files in `tests/katas/019_adaptive_investigation/features/` MUST be verbatim copies of the files in `specs/019-adaptive-investigation/tests/features/`. Per assertion-integrity rule, never edit `.feature` files directly — re-run `/iikit-04-testify` if requirements change.
- The AST lint tests (T018 topology-first, T019 no-prose-matching, T020 `re` scoped to mapper) are the load-bearing architectural guards for Principles I and VIII anti-pattern defense. If any of them flakes or is deleted, the kata silently loses its anti-pattern defense.
- The scoped `re` exception inside `topology_mapper.py` is documented in `plan.md` §Complexity Tracking and research.md D-002 — it is data scanning (filename/content indexing), not prose classification. T020 enforces the boundary.
- `runs/<session-id>/plan-revisions.jsonl`, `topology-map.json`, and `events.jsonl` are part of the contract (FR-005, SC-004); integration tests (T037, T038, T052, T067-path) operate on real disk artifacts, not in-memory mocks.
- Per plan.md §Complexity Tracking: no additional violations beyond the scoped `re` import; fan-out concurrency, retry budgets, and shared-utility refactors are deliberately NOT in scope.
- Every `[TS-NNN]` tag (TS-001 through TS-020) traces to a scenario in the copied `.feature` files; the step-definition tasks cite the exact TS IDs for pytest-bdd scenario binding.
