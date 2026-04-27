# Implementation Plan: Safe Exploration via Plan Mode

**Branch**: `007-plan-mode` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/007-plan-mode/spec.md`

## Summary

Build a Python kata that forces the Claude agent through a read-only **Plan
Mode** before any destructive edit is permitted on an unfamiliar codebase. A
typed `SessionMode = Literal["plan", "execute"]` gates which tool set the SDK
receives each turn: in plan mode only `ReadOnlyTools = {read_file, grep, glob}`
are registered; in execute mode `WriteTools = {edit_file, write_file}` are
added. The agent compiles its findings into a `PlanDocument` (pydantic v2,
markdown-serialized) listing affected files, risks, migration steps, and
out-of-scope items. Transition to execute requires a `HumanApprovalEvent`
whose `plan_hash` (sha256 of the plan markdown) matches the current document
— otherwise the transition is refused (FR-001, edge case: plan edited after
approval). Any write-tool invocation during plan mode raises
`WriteAttemptedInPlanMode` (FR-002 / SC-001). During execute, if the agent
proposes editing a file absent from `plan.affected_files`, the session halts
with `scope_change_detected` and re-enters plan mode (FR-004 / SC-004).
Delivered under Constitution v1.3.0 principles I (Determinism), II
(Schema-Enforced Boundaries, NN), V (TDD, NN), VI (Human-in-the-Loop, NN —
this kata's reason-to-exist), and VIII (Mandatory Documentation, NN).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — the SDK's per-request `tools=[...]`
  parameter is the single enforcement point for plan/execute tool-set
  swapping. Write tools are literally *not registered* while in plan mode,
  so the model cannot emit a valid `tool_use` for them (FR-002, FR-006).
- `pydantic` v2 — schemas for `PlanDocument`, `HumanApprovalEvent`,
  `SessionModeTransition`, `ScopeChangeEvent` (Principle II, NN).
- `pytest` + `pytest-bdd` — BDD runner for `.feature` files produced by
  `/iikit-04-testify` (Principle V, NN).
- `hashlib` (stdlib) — sha256 for `plan_hash` integrity.

**Storage**: Local filesystem only.
- `PlanDocument` markdown → `specs/fixtures/refactor-plans/<task-id>.md`
  during tests (canonical location used by the spec's examples and the
  scope-change / plan-edit fixtures).
- Session event log → `runs/<session-id>/events.jsonl` (append-only JSONL,
  mirrors Kata 001).
- Approval events → `runs/<session-id>/approvals.jsonl`.

**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit tests. The Anthropic client is injected; fixtures are recorded JSON
sessions shipped under `tests/katas/007_plan_mode/fixtures/`. Live SDK calls
are gated behind `LIVE_API=1` and excluded from CI, matching the Kata 001
baseline.

**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.

**Project Type**: Single project — one kata module under
`katas/007_plan_mode/`, tests mirrored at `tests/katas/007_plan_mode/`.

**Performance Goals**: Not latency-bound. The fixture-driven acceptance suite
MUST complete in under 10 seconds locally (larger than Kata 001 because the
plan corpus spans multi-file refactors, but still snappy).

**Constraints**:
- Plan mode MUST NOT register write tools with the SDK. This is the
  structural defense — the lint test (`tests/katas/007_plan_mode/lint/
  test_write_tools_absent_in_plan_mode.py`) asserts that the `tools`
  kwarg passed to `messages.create` contains zero write-class tool names
  whenever `SessionMode == "plan"`.
- Every mode transition MUST emit a `SessionModeTransition` event carrying
  the approved plan's identifier and hash (FR-005, SC-002 traceability).
- Scope-change detection MUST compare proposed edit targets against
  `plan.affected_files` *before* dispatching the tool, not after (FR-004,
  SC-004).
- All tool-result payloads and events MUST validate against their JSON
  schemas under `contracts/` or the run fails loud (Principle II).
- Absolutely no prose-matching to decide mode transitions — the transition
  is keyed off a typed `HumanApprovalEvent` (Principle I).

**Scale/Scope**: One kata, ~500–700 LOC implementation + comparable test
code; one `README.md` (Principle VIII); fixture corpus ≤ 8 recorded sessions
covering: small-refactor bypass, normal multi-file refactor, scope-creep
injection, plan-edit-after-approval (hash mismatch), infeasible-plan halt,
write-attempt-in-plan-mode, interrupted-execution, and approval-revoked.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Mode gate branches on typed `SessionMode` + typed `HumanApprovalEvent.plan_hash` equality. Scope-change halt keys off `path in plan.affected_files`, never on prose like "this file also". |
| II. Schema-Enforced Boundaries (NN) | `PlanDocument`, `HumanApprovalEvent`, `SessionModeTransition`, `ScopeChangeEvent` are pydantic v2 models with matching JSON-schema exports under `contracts/`. Required lists (`affected_files`, `risks`, `migration_steps`) are actually required; `out_of_scope` is nullable-list, not empty-string-defaulted. |
| III. Context Economy | Plan document is a stable-prefix artifact (re-read each execute turn from disk); the dynamic suffix is the single current tool result. Prevents re-injecting a growing history into each turn. |
| IV. Subagent Isolation | Not load-bearing — this kata runs a single agent across two modes, not a coordinator/subagent split. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code. The four SC metrics are expressed as executable assertions: SC-001 write-count == 0, SC-002 transition log completeness == 100%, SC-003 affected-files completeness per fixture == 100%, SC-004 scope-change halt rate == 100%. |
| VI. Human-in-the-Loop (NN) | **This is the kata.** The entire design is the literal implementation of "exploratory work on unfamiliar code MUST default to read-only planning before direct execution is authorized." The `HumanApprovalEvent` is the typed escalation payload required by Principle VI. |
| VII. Provenance & Self-Audit | Every applied change logs back to `plan_hash` (SC-002). Scope-change halts and blocked writes are logged with mode, target, timestamp (FR-007). |
| VIII. Mandatory Documentation (NN) | Each non-trivial function carries a *why* comment tied to the kata objective (plan-mode gating) or the anti-pattern (jumping straight to edits on unfamiliar code). A single `notebook.ipynb` produced at `/iikit-07-implement` is the Principle VIII deliverable: it explains the kata, results, every Claude architecture concept exercised, the architecture walkthrough, applied patterns + principles, practitioner recommendations, the contract details, run cells, and the reflection. No separate `README.md`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/007-plan-mode/
  plan.md              # this file
  research.md          # Phase 0 output (decisions + Tessl discovery notes)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output (JSON schemas, $id kata-007)
    plan-document.schema.json
    human-approval-event.schema.json
    session-mode-transition.schema.json
    scope-change-event.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  # (kata narrative lives in katas/.../notebook.ipynb — no spec-side README)
```

### Source Code (repository root)

```text
katas/
  007_plan_mode/
    __init__.py
    session.py           # SessionMode + agent loop: per-turn tool-set selection
    modes.py             # ReadOnlyTools / WriteTools registries + mode gate
    plan.py              # PlanDocument pydantic model + markdown (de)serializer
    approval.py          # HumanApprovalEvent, plan_hash computation, verifier
    scope.py             # scope-change detector (pre-dispatch file check)
    events.py            # SessionModeTransition / ScopeChangeEvent writers
    client.py            # thin injectable Anthropic client (shared pattern)
    models.py            # all pydantic v2 models for the kata
    runner.py            # CLI: `python -m katas.007_plan_mode.runner`
    notebook.ipynb       # Principle VIII deliverable — kata narrative + Claude architecture certification concepts (written during /iikit-07)

specs/
  fixtures/
    refactor-plans/      # canonical target for written PlanDocuments in tests
      .gitkeep

tests/
  katas/
    007_plan_mode/
      conftest.py        # fixture loader, plan-hash helpers, LIVE_API gate
      features/          # Gherkin files produced by /iikit-04-testify
        plan_mode.feature
      step_defs/
        test_plan_mode_steps.py
      unit/
        test_mode_gate.py                 # FR-002, SC-001
        test_plan_hash_integrity.py       # edge case: plan edited post-approval
        test_scope_change_detector.py     # FR-004, SC-004
        test_plan_document_serialization.py
      lint/
        test_write_tools_absent_in_plan_mode.py  # structural SC-001 defense
      fixtures/
        small_refactor.json               # edge case: lightweight path
        normal_refactor.json              # P1 happy path
        scope_creep_injection.json        # SC-004
        plan_edit_after_approval.json     # hash mismatch path
        infeasible_plan.json              # edge case
        write_attempt_in_plan_mode.json   # P2, SC-001
        interrupted_execution.json        # edge case
        approval_revoked.json             # edge case
```

**Structure Decision**: Single-project layout, aligned with Kata 001. Each
kata is a first-class package under `katas/NNN_<slug>/`; tests mirror under
`tests/katas/NNN_<slug>/`. The `specs/fixtures/refactor-plans/` directory
is introduced here because it is the documented write target for
`PlanDocument` markdown across the test corpus and any future kata that
produces approved plans (e.g., a hypothetical Kata 13 reviewer). Runs are
written to `runs/<session-id>/` (gitignored), matching the workshop-wide
convention.

## Traceability: Tech Choice → Requirement

| Tech choice | Serves | Why this choice |
|-------------|--------|-----------------|
| Per-request `tools=[...]` swap between `ReadOnlyTools` and `WriteTools` | FR-002, FR-006, SC-001 | Structural, not advisory: model literally cannot call a tool not registered. |
| Pydantic v2 `PlanDocument` with required `affected_files`, `risks`, `migration_steps` | FR-003, SC-003 | Principle II; required fields actually required. |
| Sha256 `plan_hash` on the rendered markdown, verified at transition | Edge case (plan edited post-approval), FR-001 | Deterministic equality check, not prose match. |
| `HumanApprovalEvent` pydantic model | FR-001, FR-005, Principle VI | Typed escalation payload, the only gate into execute mode. |
| Pre-dispatch `path in plan.affected_files` check | FR-004, SC-004 | Halts *before* the write, closing the scope-creep hole. |
| `WriteAttemptedInPlanMode` exception across all write tools | FR-002, FR-007, SC-001 | Uniform refusal surface; event recorded with mode/target/timestamp. |
| JSONL event log for mode transitions and blocked attempts | FR-005, FR-007, SC-002, Principle VII | Append-only, replayable, greppable — matches Kata 001 baseline. |
| `.feature` files + `pytest-bdd` + recorded fixtures | Principle V (NN), every SC | Executable acceptance criteria; deterministic, offline, CI-friendly. |

## Architecture

```
┌────────────────────┐
│  Practitioner CLI  │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│ Plan Mode Session  │───────│  Read-Only Tools   │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Plan Document  │ │ Approval Sink  │ │ Write Executor │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Practitioner CLI` is the kata entry point; `Plan Mode Session` owns the core control flow
for this kata's objective; `Read-Only Tools` is the primary collaborator/policy reference;
`Plan Document`, `Approval Sink`, and `Write Executor` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: sandboxed execution of `edit_file`
(not required by spec — the tool-registration gate is sufficient), multi-user
approval workflow (single `HumanApprovalEvent` is spec-compliant), a GUI
review surface (markdown-on-disk meets FR-003), and any LangChain-style
agent framework (hides the `tools` kwarg the kata relies on — same
rejection as Kata 001 D-001).
