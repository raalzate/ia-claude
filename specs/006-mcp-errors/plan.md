# Implementation Plan: MCP Integration with Structured Error Handling

**Branch**: `006-mcp-errors` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/006-mcp-errors/spec.md`

## Summary

Deliver a kata that turns every Model Context Protocol (MCP) tool failure into
a **typed, machine-branchable** payload — `isError=true` plus a pydantic
`StructuredError` carrying `errorCategory`, `isRetryable`, `detail`, and an
optional `retry_after_seconds`. An in-kata `MCPServer` deliberately exposes
multiple failure modes (transient-retryable, validation-non-retryable,
server-crash, schema-violation). On the agent side, a declared `RetryBudget`
(`max_attempts=3`, bounded backoff) drives local recovery only when
`isRetryable=true`, and exhaustion routes to an escalation payload conforming
to `escalation_trigger.schema.json`. The anti-pattern — generic
`"Operation failed"` strings — is blocked at source by an AST/grep lint on the
server module and at runtime by the schema on every failure response.

Delivered under Constitution v1.3.0 principles II (Schema-Enforced Boundaries,
NN), VI (Human-in-the-Loop Escalation, NN), VIII (Mandatory Documentation,
NN), with I (Determinism), V (Test-First), VII (Provenance) in direct support.

## Technical Context

**Language/Version**: Python 3.11+ (repo baseline — Kata 1 `plan.md` §Technical Context).

**Primary Dependencies**:
- `anthropic` (official Claude SDK) — drives the agent loop that consumes
  `StructuredError` payloads; same pattern as Kata 1 (no shared module — each
  kata re-declares the client wrapper to preserve per-kata deletability)
  (FR-004, FR-008).
- `pydantic` v2 — `StructuredError`, `ToolCall`, `RetryBudget`,
  `RecoveryAction`, `EscalationTrigger` models. Every MCP response boundary
  runs through `model_validate` — satisfies Principle II (NN) directly and
  operationalizes FR-001/FR-002/FR-007.
- `mcp` (official Python SDK, `modelcontextprotocol/python-sdk`) — in-kata
  MCPServer implements one deliberately failing tool over the SDK's
  stdio/in-memory transport. **See research.md D-006 for the justification and
  the stub-only fallback.** Touches FR-001, FR-002, FR-003, FR-007.
- `pytest` + `pytest-bdd` — BDD runner against the `.feature` file produced by
  `/iikit-04-testify` (Principle V). Fixture-driven, default offline.

**Storage**: Local filesystem only. Structured error log is append-only JSONL
at `runs/<session-id>/errors.jsonl`, one record per Tool Call attempt
(FR-006). No database.

**Testing**:
- pytest + pytest-bdd for acceptance scenarios mapped from User Stories 1–3.
- Plain pytest for unit tests over `StructuredError` schema enforcement,
  `RetryBudget` exhaustion semantics, and the anti-pattern lint.
- Five fixture corpora (see research.md D-005) plus a `LIVE_API=1`-gated path
  that runs the same agent against a real `anthropic.Anthropic` client — same
  pattern Kata 1 established, zero new CI quota spend by default.

**Target Platform**: Developer local machine (macOS/Linux) + GitHub Actions CI.
No server deployment beyond the in-process MCP server started by the kata
runner.

**Project Type**: Single project — sibling package under
`katas/006_mcp_errors/` with tests mirrored at `tests/katas/006_mcp_errors/`.
Matches Kata 1's §Structure Decision — FDD cadence is preserved.

**Performance Goals**: Not latency-bound. Fixture acceptance run completes
under 5 s locally. Backoff between retries uses a test-injectable clock so
scenarios run without real sleep.

**Constraints**:
- No generic failure strings may cross the MCP response boundary — enforced
  by (a) pydantic schema on every response, (b) an AST/grep lint that rejects
  any bare literal `"Operation failed"` / `"Error"` / `"Something went wrong"`
  in `katas/006_mcp_errors/server.py` (FR-003, SC-002).
- Retry budget is declared data, not an ambient loop counter (FR-005).
- Escalation is a typed payload, not a log print (Principle VI, FR-008).

**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test code;
one README (Principle VIII); 5 fixture files; 4 JSON Schema contracts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Agent branches on `StructuredError.isRetryable` (typed) and `RetryBudget.remaining()` (typed) — no regex over response prose. Traces to FR-004. |
| II. Schema-Enforced Boundaries (NN) | Every MCP response, tool input, retry budget, and escalation payload is a pydantic v2 model with a published JSON Schema under `contracts/`. Invalid payloads raise. Traces to FR-001, FR-002, FR-007, SC-001. |
| III. Context Economy | StructuredError.detail is length-capped; log records are the single source of truth so agent context doesn't re-accumulate narrative failure prose. |
| IV. Subagent Isolation | N/A — single-agent kata; retained for kata 4 composition. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before `/iikit-05-tasks`; anti-pattern (generic-string) tests fail closed if the lint is removed. Traces to SC-002. |
| VI. Human-in-the-Loop Escalation (NN) | Exhausted retry budget and every `isRetryable=false` failure emit an `EscalationTrigger` typed payload to a declared sink — never a silent abort or blind loop. Traces to FR-005, FR-008, SC-004. |
| VII. Provenance & Self-Audit | `errors.jsonl` records one line per attempt with tool identity, attempt index, category, retryability, explanation, outcome; sufficient to reconstruct recovery trajectory. Traces to FR-006, SC-003. |
| VIII. Mandatory Documentation (NN) | Per-kata `README.md` (objective / walkthrough / anti-pattern defense / run / reflection) and *why*-comments on every non-trivial function are deliverables of `/iikit-07-implement`. |

**Result:** PASS. Proceed to Phase 0 research.

## FR/SC → Technical Choice Traceability

| Requirement | Satisfied by |
|---|---|
| FR-001 `isError=true` on every failure | `mcp_tool_call.schema.json` response variant; pydantic `MCPResponse` |
| FR-002 category + retryable + explanation on every failure | `structured_error.schema.json`; `StructuredError` model |
| FR-003 no generic failure strings | AST/grep lint on `server.py` + pydantic rejection of free-string failures |
| FR-004 branch on metadata | `RecoveryAction` state machine driven by `StructuredError.isRetryable` |
| FR-005 retry budget enforced | `RetryBudget` model + `retry_budget.schema.json` + exhaustion → escalation |
| FR-006 log every structured error | JSONL `errors.jsonl` writer, one record per attempt |
| FR-007 synthesize local structured error on transport/schema-violation failure | `ErrorSynthesizer` path; dedicated `errorCategory` values `transport`, `schema_violation` |
| FR-008 escalation explicit and human-reviewable | `escalation_trigger.schema.json`; payload goes to declared sink; human-review path (sink registry + on-disk `runs/<session-id>/escalations/<trigger_id>.json` per T044) documented in README §MCP Error Handling Contract (T056, T059) |
| SC-001 100% of failures carry category+retryable | Schema validation rejects missing fields |
| SC-002 0 generic strings | Lint + fixture transcript scan |
| SC-003 X% retryable-resolve-within-budget | **UNRESOLVED placeholder in spec — see Open Questions §SC-003** |
| SC-004 100% non-retryable → escalation, 0 retries | `RecoveryAction` rejects retry when `isRetryable=false`; enforced by unit test |

## Project Structure

### Documentation (this feature)

```text
specs/006-mcp-errors/
  plan.md              # this file
  research.md          # Phase 0 decisions D-001..D-007 + Tessl note
  data-model.md        # Phase 1 entity schemas
  quickstart.md        # Phase 1 how-to (install, MCP server startup, fixtures)
  contracts/           # Phase 1 JSON Schemas ($id kata-006)
    mcp_tool_call.schema.json
    structured_error.schema.json
    retry_budget.schema.json
    escalation_trigger.schema.json
  checklists/
    requirements.md    # (already present — /iikit-01 output)
  tasks.md             # (generated by /iikit-05-tasks)
  README.md            # Principle VIII deliverable (written at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  006_mcp_errors/
    __init__.py
    server.py            # MCPServer exposing a tool w/ multi-mode failure surface
    client.py            # agent-side MCP client wrapper (stdio or in-memory transport)
    models.py            # pydantic: ToolCall, MCPResponse, StructuredError,
                         #           RetryBudget, RecoveryAction, EscalationTrigger
    policy.py            # retry + escalation policy (pure functions, no I/O)
    synthesizer.py       # local StructuredError synthesis for transport/schema-violation
    log.py               # JSONL writer for errors.jsonl
    runner.py            # CLI entry: `python -m katas.006_mcp_errors.runner`
    README.md            # Principle VIII doc (written at /iikit-07)

tests/
  katas/
    006_mcp_errors/
      conftest.py
      features/
        mcp_errors.feature            # produced by /iikit-04-testify
      step_defs/
        test_mcp_errors_steps.py
      unit/
        test_structured_error_schema.py
        test_retry_budget.py
        test_policy_branches.py
        test_synthesizer.py
        test_error_log_shape.py
      lint/
        test_no_generic_error_strings.py   # AST/grep gate — FR-003, SC-002
      fixtures/
        retryable_success_after_retry.json
        retryable_exhausted_budget.json
        non_retryable_validation.json
        server_crash.json
        chained_failures.json
```

**Structure Decision**: Single-project layout, one package per kata. Matches
the decision recorded in `specs/001-agentic-loop/plan.md` §Structure Decision
and the FDD cadence mandated by Constitution §Development Workflow. No shared
`common/` library is introduced (YAGNI — Kata 1 rejected it for the same
reasons; re-evaluate at Kata 4 / subagent isolation).

## Open Questions

### SC-003 — retry-resolution threshold percentage

**Status: NEEDS CLARIFICATION (carried forward from spec.md).**

spec.md currently reads *"in at least X% of runs (target X set during
`/iikit-clarify`; placeholder 90% pending confirmation)"*. The plan preserves
the placeholder rather than silently picking a value.

Recommended resolution path: run `/iikit-clarify` against this spec before
`/iikit-04-testify`. Default proposal for the clarify session:
- **95%** of retryable failures resolve within the declared `RetryBudget` on
  the fixture corpus (4/5 fixtures contain retryable traffic; one hitting the
  exhaustion branch is expected and desired, so the ceiling on the fixture
  corpus is 80% — meaning the 95% target is measured only on the subset of
  fixtures where success is possible, i.e. excluding
  `retryable_exhausted_budget.json`, which tests the exhaustion edge
  deliberately).

Until clarify runs, the testify step MUST NOT emit an assertion with a
concrete percentage — it emits a tagged `@needs-clarify SC-003` scenario so
the gap is visible in CI.

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│     MCP Client     │───────│  MCP Server Stub   │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Retry Budget  │ │Escalation Queue│ │ MCP Event Log  │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `MCP Client` owns the core control flow
for this kata's objective; `MCP Server Stub` is the primary collaborator/policy reference;
`Retry Budget`, `Escalation Queue`, and `MCP Event Log` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Deliberate omissions (all within YAGNI / Kata 1 precedent):

- No distributed tracing backend — JSONL is sufficient for SC-001 / SC-003.
- No exponential backoff tuning beyond a simple linear or small-fixed value —
  the kata teaches *budget as data*, not backoff math.
- No cross-session error aggregation — per-run log is the scope of SC-003.
- No alternate MCP transports beyond what the chosen library ships — a second
  transport would not change any branch the kata exercises.
