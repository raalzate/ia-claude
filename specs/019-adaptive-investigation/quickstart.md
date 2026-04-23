# Kata 19 — Quickstart

## What you'll build

An investigation runner that maps topology FIRST (via `pathlib.rglob` + regex
search — no LLM calls) then emits a structured, prioritized `Plan`. On
precondition failures or surprise dependencies the `Planner` produces a
`PlanRevision` with an enumerated `trigger`. An `ExplorationBudget` (seconds +
revisions) guarantees the run terminates — no endless exploration.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/019_adaptive_investigation -v
```

Asserts:
- Topology mapped before any plan built (AST test on `Planner.build_plan`).
- `PlanRevision` emitted when preconditions fail or an external dependency
  surfaces; trigger is one of the enumerated values.
- Budget exhaustion path: run halts cleanly, final plan has
  `budget_exhausted=True`.
- Cycle in dependency graph: detected and a break-cycle step inserted.
- Plan is a structured object, never a free-text block.

## Run a live investigation

```bash
LIVE_API=1 python -m katas.019_adaptive_investigation.runner \
  --directive "Add tests for a legacy payments module" \
  --target ./legacy/payments \
  --max-seconds 300 --max-revisions 3
```

Writes:
- `runs/<session>/plan-revisions.jsonl` — one `PlanRevision` per transition.
- `runs/<session>/final_plan.json` — the last plan (budget_exhausted flag set
  if applicable).

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Topology-first plan | US1, FR-001 | `legacy_payments/` |
| Surprise dependency triggers revision | US2, SC-002 | `injected_dependency/` |
| Budget caps exploration | US3, SC-003 | `huge_codebase/` with tight budget |
| Cycle detected + break step | Edge #3 | `cyclic_deps/` |
| Surprise contradicts directive | Edge #4 | `contradicting_surprise/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Rigid-plan + endless-exploration anti-patterns defended by AST lint +
      budget.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- Which trigger fired most often in your run? Does that tell you something
  about the codebase or about your initial plan?
- Would you tighten the budget or widen it after this run, and why?
