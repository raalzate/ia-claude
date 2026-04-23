# Implementation Plan: Structured Human Handoff Protocol

**Branch**: `016-human-handoff` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/016-human-handoff/spec.md`

## Summary

Build a Python kata module that acts as the **escalation sink** for the entire
workshop: when an agent trips a declared policy gap or operational limit, it
MUST register an `escalate_to_human` tool with the Anthropic SDK whose
`input_schema` is the full `HandoffPayload` pydantic v2 schema. Once the model
invokes that tool, the session enters a `SessionSuspended` state — subsequent
`messages.create` calls raise and **zero bytes** of further conversational text
are emitted (FR-001, FR-002). Validated payloads land as JSONL at
`runs/handoffs/<escalation_id>.json` through an `OperatorQueue` sink, every
entry indexed by a traceable `escalation_id` (FR-009, SC-004). The anti-pattern
— prose-only or raw-transcript handoffs — is blocked structurally: the only
handoff surface is the schema-bound tool, and a separate plain-text tool is
registered in the anti-pattern fixture to prove the validator rejects it
(FR-007, FR-008, SC-002). Evolvability is demonstrated by adding `severity` to
the required set and asserting legacy payloads fail (FR-010, SC-001).

This kata is the downstream consumer of every `EscalationEvent` emitted by
Kata 2 (PreToolUse guardrails) and every exhausted-budget `EscalationTrigger`
from Kata 6 (MCP errors) — their escalation payload shapes converge on
`HandoffPayload` here. Delivered under Constitution v1.3.0 principles II
(Schema-Enforced Boundaries, NN), VI (Human-in-the-Loop Escalation, NN), VIII
(Mandatory Documentation, NN), with I (Determinism), V (Test-First), VII
(Provenance) in direct support.

## Technical Context

**Language/Version**: Python 3.11+ (repo baseline — Kata 1 plan §Technical Context).

**Primary Dependencies**:
- `anthropic` (official Claude SDK) — `escalate_to_human` is registered as a
  standard tool via `tools=[...]` on `messages.create`; its `input_schema`
  **is** the JSON Schema view of `HandoffPayload`, forcing the model to
  produce valid JSON at the tool-use site rather than after parsing prose
  (FR-003, FR-004, FR-006).
- `pydantic` v2 — `HandoffPayload`, `ActionRecord`, `EscalationEvent`,
  `OperatorQueueEntry`, `SessionState` models. `model_validate` on every
  tool-use input block; invalid inputs raise immediately (FR-006, Principle
  II NN).
- `pytest` + `pytest-bdd` — BDD runner consuming the `.feature` file produced
  by `/iikit-04-testify` (Principle V NN). Fixture-driven; live SDK calls
  gated behind `LIVE_API=1` (Kata 1 convention).
- `uuid` (stdlib) — `escalation_id` is a UUID4 minted on trigger; reused as
  the JSONL filename stem so audit joins are one hop (FR-009, FR-011,
  SC-004).

**Storage**: Local filesystem only.
- `runs/handoffs/<escalation_id>.json` — one validated `OperatorQueueEntry`
  per escalation, written by the `OperatorQueue` sink (FR-009, SC-004).
- `runs/<session-id>/events.jsonl` — append-only audit log; one record per
  escalation attempt including `rejected` outcomes for schema-failed
  payloads (FR-006, Principle VII).

**Testing**:
- pytest + pytest-bdd for acceptance scenarios mapped from US1/US2/US3 and
  the five edge cases.
- Plain pytest for unit tests over `HandoffPayload` validation, session
  suspension semantics, and the `OperatorQueue` sink shape.
- An AST/behavioural test that imports the kata module, triggers an
  escalation, then asserts **zero bytes** are emitted on any follow-up
  `messages.create` attempt (FR-002, US1 Independent Test).
- A schema-extension test that re-imports the model with `severity` required
  and re-runs the happy-path fixture — payloads without `severity` MUST fail
  (FR-010, SC-001).
- Fixtures under `tests/katas/016_human_handoff/fixtures/` (see tree below).

**Target Platform**: Developer local (macOS/Linux) and GitHub Actions CI
(Linux). No server deployment.

**Project Type**: Single project — one kata module at
`katas/016_human_handoff/` with tests at `tests/katas/016_human_handoff/`.
Matches the §Structure Decision recorded in Kata 1's plan; FDD cadence
preserved.

**Performance Goals**: Not latency-bound. Acceptance suite against recorded
fixtures completes under 5 s locally. Handoff emission is O(1) per trigger
(one validation + one JSONL write + one state transition).

**Constraints**:
- **Zero bytes** of conversational text after suspension — enforced by a
  `SessionSuspended` guard on the SDK wrapper: any further `messages.create`
  raises `SessionSuspendedError`; test asserts `len(post_escalation_text) == 0`
  (FR-002, US1 Independent Test).
- `escalate_to_human` is the **only** schema-bound handoff tool. A separate
  plain-text `write_handoff_note` tool is registered *only in the anti-
  pattern fixture* to prove the validator path rejects prose (FR-007,
  FR-008, SC-002).
- `issue_summary` MUST be ≤ 500 characters (`maxlen=500` on the pydantic
  field) — prevents transcript-dumping via the summary slot (FR-007,
  anti-pattern defense).
- `escalation_id` is a UUID4, minted once per trigger, and is the filename
  stem of the operator-queue entry — repeated escalations in one session
  MUST produce distinct files (FR-011).
- `actions_taken` is a `list[ActionRecord]` (structured), never
  `list[str]` — empty list is valid but free-form prose is not
  (FR-005).
- The handoff schema is the source of truth: adding `severity` to required
  fields MUST NOT require any change to agent prompt text (FR-010).

**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test
code; one README (Principle VIII); fixture corpus of 5 scenarios (one per
edge case and one anti-pattern); 4 JSON Schema contracts under `contracts/`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Session suspension branches on a typed `SessionState` enum and on the presence of an `escalate_to_human` `tool_use` block — not on free text. The SDK wrapper halts via a raised `SessionSuspendedError`, never via prose matching. Traces to FR-001, FR-002. |
| II. Schema-Enforced Boundaries (NN) | `HandoffPayload` is a pydantic v2 model whose JSON Schema is bound as the tool's `input_schema`, so the model is forced to emit valid JSON at the tool-use site. Every `OperatorQueueEntry` goes through `model_validate` before it hits disk. Invalid payloads raise — no best-effort parsing. Traces to FR-003, FR-004, FR-005, FR-006, FR-010, SC-001. |
| III. Context Economy | `issue_summary` is length-capped at 500 chars; `actions_taken` is structured, not narrative — keeps operator-queue payloads small and survivable in downstream prompts. Prevents transcript-dumping via the summary slot. |
| IV. Subagent Isolation | Not load-bearing here; noted as the handoff target that Kata 4's coordinator emits when a subagent reports policy failure — `HandoffPayload` is the typed summary shape that crosses the boundary. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code; `.feature` scenarios map to FR-001..FR-012 and SC-001..SC-004. Anti-pattern test (prose-only handoff via plain-text tool) fails closed. Schema-extension test (`severity`) fails closed if the schema is bypassed. |
| VI. Human-in-the-Loop Escalation (NN) | This kata **is** the canonical implementation of Principle VI. Every declared precondition → one schema-bound `escalate_to_human` invocation → `SessionSuspended` → `OperatorQueueEntry` at `runs/handoffs/<escalation_id>.json`. Traces to FR-001..FR-004, FR-009, SC-004. |
| VII. Provenance & Self-Audit | Every escalation event (trigger, validation outcome, queue write) is appended to `runs/<session-id>/events.jsonl` with the `escalation_id`, precondition that fired, and validation verdict. The JSONL log alone reconstructs the handoff trajectory. Traces to FR-009, FR-011, SC-004. |
| VIII. Mandatory Documentation (NN) | `README.md` (objective / walkthrough / anti-pattern defense / run / reflection) and *why*-comments on every non-trivial function are deliverables of `/iikit-07-implement`. Traces to FR-012. |

**Result:** PASS. Proceed to Phase 0 research.

## FR/SC → Technical Choice Traceability

| Requirement | Satisfied by |
|---|---|
| FR-001 detect precondition, trigger handoff | `EscalationPrecondition` registry + policy check; fixtures cover each precondition class |
| FR-002 suspend conversational text after trigger | `SessionSuspended` state on SDK wrapper; any follow-up `messages.create` raises; test asserts 0 bytes of emitted text |
| FR-003 single `escalate_to_human` invocation | Tool registered once with the SDK; `HandoffPayload` as `input_schema` forces schema-valid JSON at the tool-use site |
| FR-004 payload includes required fields | `HandoffPayload` pydantic model with `customer_id`, `issue_summary`, `actions_taken`, `escalation_reason` marked required |
| FR-005 `actions_taken` is structured | `ActionRecord` pydantic model; `list[ActionRecord]` type — not `list[str]` |
| FR-006 reject schema-invalid escalations | `model_validate` on every tool-use input; failure → `SchemaRejected` event, no queue write |
| FR-007 no raw-transcript handoff | `issue_summary` capped at 500 chars; `OperatorQueue` only accepts `OperatorQueueEntry` (no free-text sink) |
| FR-008 no prose-only handoff | Prose attempt uses a separate `write_handoff_note` tool registered only in anti-pattern fixture; validator rejects — see `prose-handoff-attempt.json` |
| FR-009 unique traceable id logged | `escalation_id: UUID4` minted on trigger; filename stem of JSONL entry; echoed in audit log |
| FR-010 schema extension propagates | `HandoffPayload` is the single source of truth; schema-extension test adds `severity` to required and re-runs happy path |
| FR-011 distinct ids per escalation | UUID4 minted per trigger; repeated-escalation fixture asserts two distinct files under `runs/handoffs/` |
| FR-012 docs describe preconditions + schema + anti-pattern | `README.md` (Principle VIII deliverable) + *why*-comments |
| SC-001 100% schema-valid payloads delivered | Validator at the queue boundary rejects invalid before write; test asserts `runs/handoffs/` contains only schema-conformant files |
| SC-002 0 raw-transcript handoffs | Anti-pattern fixture proves plain-text handoff is rejected; queue inspection scan asserts no transcript fields |
| SC-003 human resolution time delta | Declared but not empirically measured in this kata — noted as a clarify follow-up; the pedagogic delta is demonstrated by the structured-vs-prose contrast in the README |
| SC-004 every escalation id traceable end-to-end | Audit log joins session → precondition → `escalation_id` → queue-file path; one JSONL grep reconstructs the chain |

## Project Structure

### Documentation (this feature)

```text
specs/016-human-handoff/
  plan.md              # this file
  research.md          # Phase 0 decision records D-001..D-007 + Tessl note
  data-model.md        # Phase 1 entity schemas + invariants
  quickstart.md        # Phase 1 how-to (install, fixture run, operator-queue inspection)
  contracts/           # Phase 1 JSON Schemas ($id kata-016)
    handoff_payload.schema.json
    action_record.schema.json
    escalation_event.schema.json
    operator_queue_entry.schema.json
  checklists/
    requirements.md    # (already present — /iikit-01 output)
  tasks.md             # (generated by /iikit-05-tasks)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  016_human_handoff/
    __init__.py
    models.py            # pydantic v2: HandoffPayload, ActionRecord, EscalationEvent,
                         #   OperatorQueueEntry, SessionState, EscalationReason (Literal),
                         #   Severity (Literal)
    tools.py             # escalate_to_human tool definition; its input_schema is the
                         #   JSON Schema view of HandoffPayload (FR-003, FR-004)
    preconditions.py     # EscalationPrecondition registry (policy-breach, out-of-policy-
                         #   demand, operational-limit, unresolved-after-retries,
                         #   explicit-user-request) — one reason code per class (FR-001)
    session.py           # SessionState machine (ACTIVE → SUSPENDED) + SessionSuspendedError;
                         #   SDK wrapper that raises on post-suspension messages.create
    operator_queue.py    # OperatorQueue sink: writes runs/handoffs/<escalation_id>.json
                         #   after pydantic validation; rejects on ValidationError (FR-006,
                         #   FR-009, SC-001, SC-004)
    events.py            # JSONL audit-log writer (shared shape with kata 1/2)
    runner.py            # CLI entry: python -m katas.016_human_handoff.runner
    README.md            # Principle VIII doc (written at /iikit-07)

tests/
  katas/
    016_human_handoff/
      conftest.py                                # fixture loader, queue inspector, session wrapper
      features/
        human_handoff.feature                    # produced by /iikit-04-testify
      step_defs/
        test_human_handoff_steps.py
      unit/
        test_handoff_payload_required_fields.py  # US1-AS1, FR-004
        test_handoff_payload_maxlen_summary.py   # FR-007 (500-char cap)
        test_actions_taken_structured.py         # FR-005
        test_session_suspension_zero_bytes.py    # FR-002, US1 Independent Test
        test_tool_schema_is_handoff_payload.py   # FR-003, binds HandoffPayload to input_schema
        test_schema_rejects_prose_only.py        # US2-AS1/AS2, FR-008, SC-002
        test_schema_rejects_missing_severity.py  # US3-AS1/AS2, FR-010, SC-001
        test_operator_queue_traceable_id.py      # FR-009, FR-011, SC-004
        test_repeated_escalations_distinct.py    # Edge, FR-011
        test_mid_tool_call_actions_taken.py      # Edge (mid-tool-call)
        test_empty_actions_taken_valid.py        # Edge (empty actions)
        test_unknown_customer_sentinel.py        # Edge (unknown customer_id)
      fixtures/
        policy-breach-mid-tool-call.json
        unknown-customer.json
        empty-actions-taken.json
        repeated-escalation-same-session.json
        prose-handoff-attempt.json               # anti-pattern fixture

runs/
  handoffs/                                      # gitignored; one JSONL per escalation_id
  <session-id>/
    events.jsonl                                 # per-session audit log
```

**Structure Decision**: Single-project layout, one package per kata under
`katas/NNN_<slug>/`. Matches the decision recorded in
`specs/001-agentic-loop/plan.md` §Structure Decision and continues the FDD
cadence mandated by Constitution §Development Workflow. No shared `common/`
library is introduced; the `HandoffPayload` / `EscalationEvent` shapes are
intentionally re-declared here rather than shared with Kata 2 / Kata 6 — this
kata is the **schema of record** for escalation, and cross-kata extraction
is deferred until a second consumer concretely needs it (YAGNI, Kata 1
precedent).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Deliberate omissions (all within YAGNI / Kata 1 precedent):

- **No operator UI / real queue backend.** `OperatorQueue` is a JSONL sink on
  disk; a real queue (SQS, Kafka, etc.) would not change any branch the kata
  exercises and would obscure the schema-enforcement lesson.
- **No SLA clock / severity-driven routing.** `severity` enters only in the
  schema-extension test (US3); wiring it to routing logic is out of scope.
- **No session resumption after suspension.** The spec explicitly freezes the
  session; un-suspending is an operator concern and out of the kata scope.
- **No automated measurement of SC-003 (human resolution time delta).**
  Declared in the spec as an empirical target; the kata demonstrates the
  structured-vs-prose contrast pedagogically in the README, and an
  `@needs-clarify SC-003` tag is emitted by `/iikit-04-testify` so the gap
  is visible in CI until a clarify pass fills it.
