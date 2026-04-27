# Implementation Plan: Adaptive Investigation (Dynamic Decomposition)

**Branch**: `019-adaptive-investigation` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/019-adaptive-investigation/spec.md`

## Summary

Build a coordinator agent under `katas/019_adaptive_investigation/` that, given an
open exploratory directive, **MUST** perform a topology-mapping pass *before*
emitting any plan, then produce a prioritized, re-adaptable plan whose every
revision is triggered by a structured event and logged with provenance. A
dedicated `TopologyMapper` sweeps the target workspace via filename-pattern
(`pathlib.rglob`) and regex-search (`re`) — this is the only code path in which
`re` is permitted, because it is **data scanning**, not decision-flow, and the
Principle I prohibition targets prose classification, not filename/content
indexing. A pydantic `TopologyMap` is handed to a `Planner` that emits a
structured `Plan` of ordered `PlanStep`s; `Planner.revise(trigger)` produces a
new immutable `Plan` whenever a precondition check fails, a surprise surfaces,
a cycle is detected, or the budget is exhausted. An `ExplorationBudget` enforces
wall-clock + revision caps so the agent never explores indefinitely (FR-004,
SC-003). All revisions are appended to `runs/<session-id>/plan-revisions.jsonl`
with an unambiguous `trigger` (FR-005, SC-004). An AST lint asserts the
`Planner` never constructs a `Plan` before a `TopologyMap` materializes
(FR-001, US3 anti-pattern defense). Delivered under Constitution v1.3.0
principles I (NN), IV, and VIII (NN).

## Technical Context

**Language/Version**: Python 3.11+ (matches shared baseline from
`specs/001-agentic-loop/plan.md`).
**Primary Dependencies**:
- `anthropic` — `Planner` and `Coordinator` drive Claude via
  `anthropic.Anthropic().messages.create`. Structured `stop_reason` keys
  control the loop; the `Planner`'s plan-vs-revise decision is signal-driven
  (Principle I), never inferred from prose.
- `pydantic` v2 — `ExploratoryDirective`, `TopologyMap`, `Plan`, `PlanStep`,
  `PlanRevision`, `TriggerEvent`, and `ExplorationBudget` are pydantic v2
  models with `model_config = ConfigDict(extra="forbid")`. All inter-component
  handoffs go through `model_validate` / `model_dump_json` (Principle II NN,
  FR-002, FR-005, FR-008).
- `pathlib` (stdlib) + `re` (stdlib) — **scoped exclusively** to
  `topology_mapper.py`. `pathlib.Path.rglob` backs filename-pattern sweeps and
  `re.compile` / `re.search` backs regex-search sweeps (FR-001). Every other
  module (notably `planner.py`) is AST-lint-forbidden from importing `re`.
- `pytest` + `pytest-bdd` — BDD runner consumes the Gherkin file produced by
  `/iikit-04-testify`. Assertion-integrity hashes lock the acceptance set.
**Storage**: Local filesystem only. Per-run artifacts written to
`runs/<session-id>/` (gitignored):
- `plan-revisions.jsonl` — append-only log, one `PlanRevision` per line, carrying
  `revision_id`, `trigger`, `diff_summary`, `timestamp` (FR-005, SC-004).
- `topology-map.json` — the final `TopologyMap` snapshot (or best-effort snapshot
  at budget exhaustion) for audit diff against the plan.
- `events.jsonl` — coordinator-level structured events (directive received,
  topology-pass start, plan emitted, budget exhausted) — mirrors Kata 1 D-003.
Findings that must survive a `/compact` reset are mirrored to the kata-18
scratchpad when the surrounding session opts into it (see spec.md §018 hook);
this plan does not reimplement that machinery, it consumes it.
**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit +
integration + AST lint. Fixture corpora under
`tests/katas/019_adaptive_investigation/fixtures/` are synthetic mini-codebases
(directory trees of inert `.py` files) with pre-recorded `RecordedClient`
responses for the `Planner`'s SDK calls. Live API runs are gated behind
`LIVE_API=1`.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.
**Project Type**: Single project. Kata lives at
`katas/019_adaptive_investigation/`; tests at
`tests/katas/019_adaptive_investigation/`.
**Performance Goals**: Not latency-bound. Recorded-fixture acceptance suite
completes in under 5 seconds locally. Default `ExplorationBudget.max_wallclock_s
= 30`, `max_revisions = 8` — values chosen so tests are deterministic and so
the budget is reachable in the "injected surprise" fixture without flakiness
(see research.md D-003).
**Constraints**:
- `katas/019_adaptive_investigation/planner.py` MUST NOT `import re`, call
  `str.find`, or use the `in` operator where the right-hand side is a `str`
  literal — enforced by `tests/katas/019_adaptive_investigation/lint/test_no_prose_matching.py`
  (Principle I NN, FR-002). `re` is permitted **only** inside
  `topology_mapper.py` because its role is data scanning (filename/content
  indexing), not control-flow classification.
- `planner.py` MUST NOT construct a `Plan` before a `TopologyMap` has been
  materialized in the current run — enforced by
  `tests/katas/019_adaptive_investigation/lint/test_topology_first.py`
  (AST + runtime guard) (FR-001, US3 anti-pattern).
- Every `PlanRevision` written to `plan-revisions.jsonl` MUST carry a non-null
  `trigger` whose `category` is one of the enumerated `TriggerCategory` values
  — enforced by pydantic `extra="forbid"` + a JSONL replay assertion in
  `test_plan_revision_log_shape.py` (FR-005, SC-004).
- Cyclic dependency detection in the `TopologyMap` MUST flag, not recurse —
  `TopologyMapper.detect_cycles()` returns a list of cycles that becomes a
  `TriggerEvent(category="cycle_detected")` feeding `Planner.revise()` (spec
  Edge Case: cyclic dependency).
- Budget exhaustion MUST itself be a `TriggerEvent(category="budget_exhausted")`
  that forces a final "best-effort plan" emission and halts the loop (FR-004,
  SC-003).
**Scale/Scope**: One kata, ~500–700 LOC implementation + comparable test code;
one README; fixture corpus of 5 synthetic codebases (happy path, injected
surprise, cycle, trivial topology, budget-limited) + 5 recorded planner
sessions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | `Planner`'s branch-between-plan-and-revise decision is driven by structured `TriggerEvent` pydantic instances + `stop_reason`, never by grepping model prose. AST lint (`test_no_prose_matching.py`) fails the build if `re` or prose-substring ops appear in `planner.py`. The scoped `re` usage in `topology_mapper.py` is data scanning (indexing file contents), which is the Principle-compliant use, and is documented in research.md D-002. |
| II. Schema-Enforced Boundaries (NN) | `ExploratoryDirective`, `TopologyMap`, `Plan`, `PlanStep`, `PlanRevision`, `TriggerEvent`, `ExplorationBudget` are pydantic v2 models with `extra="forbid"`. Every JSON schema under `contracts/` sets `additionalProperties: false` and pins `$id` under the `kata-019` namespace. |
| III. Context Economy | The `Planner` receives only the validated `TopologyMap` + `ExploratoryDirective` — it never sees raw file contents or the mapper's internal scan state. This caps the prompt irrespective of codebase size and matches the Principle III "compact before continuing" discipline when paired with Kata 18's scratchpad. |
| IV. Subagent Isolation | `TopologyMapper` and `Planner` are separate modules behind a hub-and-spoke boundary: the `Coordinator` is the hub; the mapper and planner are spokes receiving only typed payloads. Reuses the `TaskSpawner`-style primitive from Kata 4 (see research.md D-005). The planner module has no reference to the mapper's private scan state. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code per Constitution v1.3.0 Development Workflow. Hashes locked in `.specify/context.json` before implement. |
| VI. Human-in-the-Loop | When a discovery contradicts the original directive (FR-007) the coordinator emits a typed `TriggerEvent(category="directive_contradiction")` and halts with a labeled escalation payload — never silently forces the directive through. |
| VII. Provenance & Self-Audit | `plan-revisions.jsonl` is the append-only audit trail; each `PlanRevision` links `revision_id → trigger → diff_summary`. Every high-priority `PlanStep` carries a `topology_refs: list[str]` back-pointer into `TopologyMap` node ids (FR-008) — an auditor can walk from any prioritized step to its evidence. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function (topology sweep, cycle detector, planner branch, budget enforcer, revision logger) will carry a *why* comment tied to the kata objective or to the rigid-plan anti-pattern. A single `notebook.ipynb` produced at `/iikit-07-implement` is the Principle VIII deliverable: it explains the kata, results, every Claude architecture concept exercised, the architecture walkthrough, applied patterns + principles, practitioner recommendations, the contract details, run cells, and the reflection. No separate `README.md`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/019-adaptive-investigation/
  plan.md              # this file
  research.md          # Phase 0 output — decisions D-001..D-007 + budget defaults + Tessl note
  data-model.md        # Phase 1 output — entity schemas
  quickstart.md        # Phase 1 output — install, fixture run, scenario→spec map, completion checklist
  contracts/           # Phase 1 output — JSON Schema Draft 2020-12, $id namespace kata-019
    exploratory-directive.schema.json
    topology-map.schema.json
    plan.schema.json
    plan-revision.schema.json
    budget.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # already present
  # (kata narrative lives in katas/.../notebook.ipynb — no spec-side README)
```

### Source Code (repository root)

```text
katas/
  019_adaptive_investigation/
    __init__.py
    coordinator.py           # Hub: receives ExploratoryDirective, orchestrates mapper→planner→revise loop
    topology_mapper.py       # filename-pattern (pathlib.rglob) + regex-search (re) sweeps; emits TopologyMap; scoped `re` usage
    planner.py               # consumes TopologyMap + Directive, emits Plan; .revise(trigger) emits a new Plan; MUST NOT import `re`
    budget.py                # ExplorationBudget enforcer (wall-clock + revision counter); emits budget_exhausted TriggerEvent
    revision_log.py          # append-only JSONL writer for runs/<session-id>/plan-revisions.jsonl
    models.py                # pydantic: ExploratoryDirective, TopologyMap, Plan, PlanStep, PlanRevision, TriggerEvent, ExplorationBudget
    client.py                # thin injectable Anthropic client wrapper (mirrors Kata 1 D-001)
    runner.py                # CLI entrypoint: `python -m katas.019_adaptive_investigation.runner`
    notebook.ipynb           # Principle VIII deliverable — kata narrative + Claude architecture certification concepts (written during /iikit-07)

tests/
  katas/
    019_adaptive_investigation/
      conftest.py
      features/
        adaptive_investigation.feature         # produced by /iikit-04-testify
      step_defs/
        test_adaptive_investigation_steps.py
      unit/
        test_topology_mapper.py                # FR-001: pattern + regex sweeps produce a valid TopologyMap
        test_planner_emits_structured_plan.py  # FR-002, FR-008: priority + topology_refs back-pointers
        test_planner_revises_on_trigger.py     # FR-003, US2-AS1..AS3
        test_budget_enforcer.py                # FR-004, FR-006, US3, SC-003
        test_cycle_detection.py                # Edge case: cyclic dependency
        test_directive_contradiction.py        # FR-007, spec Edge Case
      lint/
        test_no_prose_matching.py              # AST: planner.py MUST NOT import `re`, call str.find, or use `in` on str literal
        test_re_scoped_to_mapper.py            # AST: `re` imports live only in topology_mapper.py
        test_topology_first.py                 # AST + runtime: Planner never constructs Plan before TopologyMap materializes (FR-001, US3)
      integration/
        test_injected_surprise.py              # SC-002: planted external dependency triggers a revise + "mock this first" step
        test_plan_revision_log_shape.py        # FR-005, SC-004: every revision has a logged trigger with unambiguous category
        test_budget_limited_annotation.py      # FR-006, US3-AS2: partial plan carries confidence indicator
      fixtures/
        happy_path/                            # synthetic mini-codebase + recorded planner session
        injected_surprise/                     # corpus with a hidden network client — forces mocking revision
        cyclic_dependency/                     # corpus whose import graph forms a cycle
        trivial_topology/                      # single-file corpus
        budget_limited/                        # oversized corpus that cannot be mapped within default budget

runs/                                          # gitignored; one subdirectory per session_id
  <session-id>/
    events.jsonl
    topology-map.json
    plan-revisions.jsonl
```

**Structure Decision**: Single-project layout matching the Kata 1 / Kata 4
convention (see `specs/001-agentic-loop/plan.md` §Structure Decision). Mapper
and Planner live in **separate modules** for two reasons: (a) the AST lint
needs a module boundary to enforce "`re` lives only in mapper", (b) the hub-
and-spoke discipline from Kata 4 is easier to re-apply when the spokes are
physical files. `revision_log.py` is a separate module so `planner.py` can
remain side-effect-free for unit tests; the coordinator owns the JSONL
handle. Runs are written to `runs/<session-id>/` (gitignored) matching Kata 1
provenance layout. Findings that must survive `/compact` are mirrored to the
kata-18 scratchpad by the coordinator, not by the planner (keeps the planner
pure).

## Architecture

```
┌────────────────────┐
│    Coordinator     │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  Topology Mapper   │───────│      Planner       │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Plan Revision L…│ │Budget Enforcer │ │   Filesystem   │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Coordinator` is the kata entry point; `Topology Mapper` owns the core control flow
for this kata's objective; `Planner` is the primary collaborator/policy reference;
`Plan Revision Log`, `Budget Enforcer`, and `Filesystem` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Scoped `re` import in `topology_mapper.py` | FR-001 mandates regex-search as one of the two topology signals; `re` is the stdlib regex engine. The Principle I prohibition targets prose classification in control flow, not data scanning — research.md D-002 documents the distinction and the AST lint `test_re_scoped_to_mapper.py` enforces it. | "Banning `re` everywhere" would make FR-001 unsatisfiable without rolling a custom matcher, which adds surface area with no pedagogical gain and still performs regex — the hazard is unchanged. |
