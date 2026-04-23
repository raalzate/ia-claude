# Implementation Plan: Multi-Pass Prompt Chaining

**Branch**: `012-prompt-chaining` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/012-prompt-chaining/spec.md`

## Summary

Decompose a macro audit task ("audit this 15-file PR") into an ordered list of
typed `ChainStage` passes. Stage 1 (`PerFileAnalysisStage`) emits one structured
local report per file; Stage 2 (`IntegrationAnalysisStage`) consumes only the
accumulated per-file reports and emits an integration-only report. A `Chain`
orchestrator runs stages in order, persists intermediate payloads as JSON under
`runs/<session-id>/stage-<n>.json`, validates each payload against the stage's
declared `output_schema`, enforces a per-stage `max_prompt_tokens` size-budget
gate (halts with `StageBudgetExceeded` when exceeded — FR-003 / SC-002), and
fails loud if a payload is malformed (FR-004 / SC-003). The chain is
forward-extensible: adding a new stage (e.g. `SecurityScanStage`) requires zero
edits to earlier stage files (FR-005 / SC-004), verified by diff. A
baseline-vs-chain fixture measures finding-coverage delta on the same 15-file
PR corpus (SC-001). Delivered under Constitution v1.3.0 Principles III (Context
Economy), IV (Subagent Isolation), VIII (Mandatory Documentation, NN).

## Technical Context

**Language/Version**: Python 3.11+ (shared baseline across all katas).
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — each stage issues one `messages.create`
  call; the SDK response is the only signal we read (FR-001, traces to
  Constitution Principle I carried over from Kata 1).
- `pydantic` v2 — `ChainStage`, `MacroTask`, `IntermediatePayload`, `FinalReport`
  are pydantic models; stage `input_schema` / `output_schema` are pydantic
  classes used at the stage boundary (FR-002, FR-004; Principle II).
- `pytest` + `pytest-bdd` — BDD runner for `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).
- `tiktoken` (local tokenizer, no network) — deterministic token counting for
  the `max_prompt_tokens` budget gate (FR-003, SC-002). No behavioral coupling
  to any particular tokenizer flavor: the gate only needs a stable upper bound.
**Storage**: Local filesystem only.
- Intermediate payloads: `runs/<session-id>/stage-<n>.json`
  (one file per stage boundary, JSON-schema-validated on write AND on read).
- Final integration report: `runs/<session-id>/final.json`.
- Baseline comparison artifact: `runs/<session-id>/baseline.json`.
- Everything under `runs/` is gitignored.
**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit + schema
contract tests. Recorded JSON fixtures under
`tests/katas/012_prompt_chaining/fixtures/` drive the default offline run. Live
SDK calls are gated behind `LIVE_API=1` and never part of CI.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.
**Project Type**: Single project — one kata module at
`katas/012_prompt_chaining/` with tests at `tests/katas/012_prompt_chaining/`,
mirroring the Kata-1 layout.
**Performance Goals**: Not latency-bound. Acceptance scenarios against recorded
fixtures complete under 5 s locally. Baseline-vs-chain delta comparison runs
offline over the 15-file fixture corpus.
**Constraints**:
- Each stage MUST validate its output against its declared `output_schema`
  before the payload is persisted — no best-effort parsing (FR-004, Principle
  II).
- A stage's prompt MUST be scoped to its declared responsibility — the
  integration stage prompt MUST NOT reference raw file content, only the
  accumulated per-file reports (FR-003, Principle IV / Subagent Isolation).
- One failed per-file analysis MUST surface as an explicit error in the chain
  output; silent skip is forbidden (FR-008, SC-003).
- Adding a new stage MUST NOT require editing any earlier stage's file —
  verified by a diff-based test (FR-005, SC-004).
**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test code;
one README (Principle VIII); fixture corpus = one 15-file PR, plus small
degenerate corpora for the edge cases (1-file, oversize per-file report,
malformed payload, single-file failure).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Chain progression keys off structured return payloads validated by pydantic, not off model prose. Budget-gate and malformed-payload halts are typed exceptions (`StageBudgetExceeded`, `MalformedIntermediatePayload`), not string matches. |
| II. Schema-Enforced Boundaries (NN) | `MacroTask`, `ChainStage.input_schema`, `ChainStage.output_schema`, `IntermediatePayload`, `FinalReport` are all pydantic v2 models. Each stage boundary runs `model_validate` on the incoming payload AND on the outgoing payload before persistence. |
| III. Context Economy | This is the kata's raison d'être. Each stage's prompt is scoped to its declared responsibility (per-file vs integration); integration prompt feeds on distilled per-file reports, not raw files. `max_prompt_tokens` budget gate makes prompt-size bloat fail loud instead of silently degrading. |
| IV. Subagent Isolation | Hub-and-spoke modeled as stage-to-stage: each stage receives only the typed JSON payload it declares, never inherited prompt context from earlier stages. Orchestrator does not leak upstream model turns into downstream stages. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code per Constitution; `tasks.md` will reference the hashed scenario set. Anti-pattern test (monolithic prompt baseline) captured in the feature file so it fails closed if chain is bypassed. |
| VI. Human-in-the-Loop | `StageBudgetExceeded` and `MalformedIntermediatePayload` halt with a labeled reason and stage index — the human reviewing the halted payload is the escalation target. No silent retry. |
| VII. Provenance & Self-Audit | Every intermediate payload records the originating stage name and index (FR-007); every finding in the final report carries a back-reference to the per-file report it was derived from. `runs/<session-id>/stage-<n>.json` is the audit trail. |
| VIII. Mandatory Documentation (NN) | Every non-trivial class (`ChainStage`, `Chain`, concrete stages, `StageBudgetExceeded`) will carry a *why* comment tied to the saturation anti-pattern. Kata README covers objective, walkthrough, anti-pattern defense, run instructions, reflection (written during `/iikit-07-implement`). |

**Result:** PASS. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/012-prompt-chaining/
  plan.md              # this file
  research.md          # Phase 0 output (decisions + Tessl discovery notes)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output (JSON schemas, $id kata-012)
    macro-task.schema.json
    stage-definition.schema.json
    intermediate-payload.schema.json
    final-report.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  012_prompt_chaining/
    __init__.py
    chain.py              # Chain orchestrator (ordered list of stages, persistence, budget gate)
    stages/
      __init__.py
      base.py             # ChainStage pydantic-abstract-base: name, responsibility, input_schema, output_schema, run()
      per_file.py         # PerFileAnalysisStage — local analysis, one report per input file
      integration.py      # IntegrationAnalysisStage — inter-module coherence only
      security.py         # SecurityScanStage — demo extension (User Story 3)
    budget.py             # StageBudgetExceeded exception + token-counting helper
    payloads.py           # pydantic models: MacroTask, IntermediatePayload, FinalReport
    errors.py             # MalformedIntermediatePayload, ChainHalt exceptions
    client.py             # thin injectable Anthropic client wrapper (shared pattern from Kata 1)
    runner.py             # CLI entrypoint: `python -m katas.012_prompt_chaining.runner`
    README.md             # kata narrative (written during /iikit-07)

tests/
  katas/
    012_prompt_chaining/
      conftest.py         # fixture corpus loader + LIVE_API gate
      features/           # Gherkin files produced by /iikit-04-testify
        prompt_chaining.feature
      step_defs/
        test_prompt_chaining_steps.py
      unit/
        test_chain_orchestration.py     # ordered execution + persistence
        test_budget_gate.py             # StageBudgetExceeded halts (FR-003, SC-002)
        test_malformed_payload.py       # fail-loud on malformed payload (FR-004, SC-003)
        test_stage_traceability.py      # originating-stage field on every artifact (FR-007)
      contract/
        test_schema_validation.py       # all contracts/*.schema.json validate sample payloads
      integration/
        test_baseline_vs_chain.py       # coverage-delta comparison (US2, SC-001)
        test_chain_extension_diff.py    # adding SecurityScanStage touches zero earlier files (FR-005, SC-004)
      fixtures/
        corpus_15_files/                # 15-file PR corpus — shared by baseline and chain
        chain_happy_path.json           # recorded: per-file + integration stages succeed
        oversize_per_file_report.json   # triggers budget gate on integration stage
        malformed_payload.json          # missing required field in stage-1 output
        single_file_failure.json        # 1 per-file stage emits error; chain halts loud
        baseline_monolithic.json        # recorded single-prompt baseline for delta comparison
```

**Structure Decision**: Single-project kata package under
`katas/012_prompt_chaining/`, matching the Kata-1 precedent set by FDD
delivery cadence (Constitution Development Workflow §Build by Feature).
Stages live in a `stages/` sub-package so adding `SecurityScanStage` is a
pure file-add — the diff-based extension test (FR-005 / SC-004) becomes a
natural check. Runs written to `runs/<session-id>/` (gitignored).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified.**

_No violations._ Intentionally omitted: parallel per-file stage execution
(sequential is clearer pedagogy and matches FR-002's "accumulated payload"
semantics), streaming responses, cross-session state, cost-based budget (token
budget is the kata's teachable gate). All of these are out of scope for the
kata objective and would dilute the decomposition lesson.

## Trace — Technology ↔ Requirement / Success Criterion

| Technology choice | Serves |
|-------------------|--------|
| `pydantic` v2 stage boundaries | FR-001, FR-002, FR-004, FR-006, FR-007; Principle II |
| Per-stage JSON file at `runs/<session-id>/stage-<n>.json` | FR-002, FR-006, FR-007; SC-003 (auditability of halts) |
| `max_prompt_tokens` + `tiktoken` + `StageBudgetExceeded` | FR-003; SC-002 |
| Ordered-list `Chain` orchestrator | FR-001, FR-005; SC-004 |
| Diff-based extension test | FR-005; SC-004 |
| Baseline-vs-chain fixture + delta assertion | US2-AS2; SC-001 |
| Fail-loud malformed-payload test | FR-004, FR-008; SC-003 |
| `tests/.../conftest.py` + `LIVE_API` gate | Shared baseline (no API quota in CI) |
| `pytest-bdd` `.feature` execution | Principle V (TDD); Constitution §Kata Completion Standards #2 |
