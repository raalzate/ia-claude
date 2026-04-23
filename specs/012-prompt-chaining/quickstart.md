# Kata 12 — Quickstart

## What you'll build

A `Chain` orchestrator with two concrete stages — `PerFileAnalysisStage` and
`IntegrationAnalysisStage` — that processes a multi-file PR in two passes.
Intermediate payloads persist to `runs/<session-id>/stage-<n>.json`. Each
stage has a declared token budget and a typed output schema; violations halt
the chain fail-loud.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/012_prompt_chaining -v
```

Asserts:
- per-file stage emits one payload per file.
- integration stage receives ONLY the per-file payloads, not raw sources.
- malformed intermediate payload halts the chain with `StageBudgetExceeded` or
  `StageValidationError` — zero silent swallows.
- finding-coverage delta (chain vs monolithic baseline) meets declared target.
- extension stage added via registry doesn't mutate earlier stages' code.

## Run against a local PR corpus

```bash
LIVE_API=1 python -m katas.012_prompt_chaining.runner \
  --pr-dir tests/katas/012_prompt_chaining/fixtures/pr_15_files/ \
  --stages per_file_analysis,integration_analysis
```

Writes `runs/<session-id>/stage-*.json` and `final_report.json`.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Chained audit on 15-file PR | US1, SC-001 | `pr_15_files/` |
| Monolithic baseline comparison | US2, SC-001 | `pr_15_files_monolithic/` |
| Extension stage added without rewiring | US3, SC-004 | `extension_stage_test/` |
| Stage budget exceeded halts | Edge #2 | `oversized_input/` |
| Per-file stage fails loud | Edge #3, FR-004 | `malformed_file/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Anti-pattern (monolithic prompt) defended by baseline comparison fixture.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- At what PR size does the chain stop paying for itself? Where's the crossover?
- What inter-module incoherence did the integration pass find that per-file
  passes missed?
