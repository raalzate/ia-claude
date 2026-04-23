# Implementation Plan: Deterministic Guardrails via PreToolUse Hooks

**Branch**: `002-pretool-guardrails` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/002-pretool-guardrails/spec.md`

## Summary

Build a Python kata module that intercepts every `process_refund` tool
invocation at a `PreToolUseHook` boundary *before* the Anthropic SDK dispatches
the payload to the external refund API. The hook validates the payload against
a pydantic-v2 schema (amount presence, numeric type, sign, bounds) and compares
the amount against an externally-configured `PolicyConfig.max_refund`. A reject
verdict returns a **structured error object** into the model's next context
window (never a free-text apology) and emits an `EscalationEvent` for
human-in-the-loop review. A local refund-API stub records every call it
receives so acceptance tests can assert **zero** calls on rejected invocations
(FR-006, SC-001, SC-002). An AST gate asserts that the enforcement threshold
(`MAX_REFUND`) is *not* sourced from or embedded in the system prompt — the
hook is the only enforcement path (FR-008). Delivered under Constitution
v1.3.0 principles I, II (NN), V (NN), VI (NN), VII, VIII (NN).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — tool dispatch pipeline whose PreToolUse
  phase the hook plugs into (FR-001).
- `pydantic` v2 — schema enforcement for `ToolCallPayload`, `PolicyConfig`,
  `HookVerdict`, `StructuredError`, `EscalationEvent` (Principle II, FR-002,
  FR-003, FR-005).
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).
- `python-decimal` (stdlib `decimal.Decimal`) — for exact monetary comparison
  against `MAX_REFUND`; float arithmetic is forbidden for the amount field
  (prevents `0.1 + 0.2` class of policy-evasion bugs).
**Storage**: Local filesystem only.
- `runs/<session-id>/events.jsonl` — append-only JSONL audit log of every
  invocation, verdict, and escalation (FR-009, Principle VII).
- `config/policy.json` — externally-editable `PolicyConfig` snapshot; reloaded
  per-invocation so FR-011 / SC-004 pass without redeploy.
- Refund-API stub call log at `runs/<session-id>/refund_api_calls.jsonl` used by
  tests to assert zero calls on reject (FR-006, SC-002).
**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit tests; an AST lint test (`test_prompt_has_no_limit.py`) that parses
`katas/002_pretool_guardrails/prompts.py` and asserts no numeric literal equal
to any configured `PolicyConfig.max_refund` appears inside the system-prompt
string constants (FR-008 machine check). Fixture sessions recorded under
`tests/katas/002_pretool_guardrails/fixtures/`; live SDK calls gated behind
`LIVE_API=1` (same convention as Kata 1, per shared tech baseline).
**Target Platform**: Developer local (macOS/Linux) and GitHub Actions CI
(Linux). No server deployment.
**Project Type**: Single project — one kata module at
`katas/002_pretool_guardrails/` with tests at
`tests/katas/002_pretool_guardrails/`.
**Performance Goals**: Not latency-bound. Acceptance suite against recorded
fixtures completes under 5s locally. Hook evaluation is O(1) per invocation.
**Constraints**:
- No call to the external refund API stub is permitted on a reject verdict —
  the stub's recorded-calls log MUST be empty for those runs (FR-006, SC-002).
- Hook MUST fail closed: if it cannot evaluate (exception, unreadable policy
  file), the invocation is rejected with reason code `hook_failure`, distinct
  from `policy_breach` and `schema_violation` (FR-012, Principle VI).
- Amount comparisons MUST use `decimal.Decimal` — any `float` in the amount
  path is a lint failure.
- The string `"$500"`, `"500"`, or any numeric literal matching the current
  `PolicyConfig.max_refund` MUST NOT appear inside the system-prompt module
  (FR-008, enforced by AST lint).
- Verdicts MUST be deterministic: same `(payload, policy_snapshot)` → same
  `HookVerdict` (FR-010, SC-001).
**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test code;
one README (per Principle VIII); fixture corpus ≤ 12 recorded scenarios
covering happy path, over-limit, at-limit, schema violations (missing,
negative, non-numeric, extra-fields), hook-failure, policy-change mid-run, and
concurrent-policy-update snapshot.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Hook branches on pydantic validation + numeric `Decimal` comparison against `PolicyConfig.max_refund`. No regex over prose. FR-010 / SC-001 measurable: identical `(payload, policy_snapshot)` always yields identical `HookVerdict`. |
| II. Schema-Enforced Boundaries (NN) | Every boundary typed: `ToolCallPayload`, `PolicyConfig`, `HookVerdict`, `StructuredError`, `EscalationEvent` are pydantic v2 models; JSON Schemas under `contracts/` mirror them. FR-002, FR-003, FR-005 map 1:1 to validators. Invalid payload raises — never silently coerced. |
| III. Context Economy | Not load-bearing. System prompt stays terse; structured errors returned into context are field-level (code, path, limit, correlation_id) not prose dumps — keeps post-rejection turns cheap. |
| IV. Subagent Isolation | Not applicable — single-agent kata. Noted to be revisited at Kata 7 (subagent isolation kata) which may reuse `StructuredError`. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code; `.feature` scenarios map to FR-001..FR-013 and SC-001..SC-004. Anti-pattern test (`test_prompt_has_no_limit.py`) fails closed if enforcement is moved into the prompt. |
| VI. Human-in-the-Loop Escalation (NN) | Every policy-breach reject emits an `EscalationEvent` with `summary`, `actions_taken=[]`, `escalation_reason` routed to a human reviewer target (FR-007). Hook-failure reject also escalates, distinguishing cause (FR-012). |
| VII. Provenance & Self-Audit | Every invocation + verdict + escalation is written to `runs/<session-id>/events.jsonl` with correlation id, policy id+version, offending field, and verdict (FR-009). The JSONL log alone reconstructs the run. |
| VIII. Mandatory Documentation (NN) | Every hook, schema, and control-flow branch will carry a *why* comment tied to this kata's anti-pattern (prompt-only enforcement). `README.md` produced at `/iikit-07-implement` covers objective, walkthrough, anti-pattern defense, run instructions, reflection. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/002-pretool-guardrails/
  plan.md              # this file
  research.md          # Phase 0 output (decision records + Tessl note)
  data-model.md        # Phase 1 output (pydantic entities + invariants)
  quickstart.md        # Phase 1 output (install, fixture run, live run, mapping)
  contracts/           # Phase 1 output (JSON Schemas, Draft 2020-12)
    tool-call-payload.schema.json
    hook-verdict.schema.json
    structured-error.schema.json
    policy-config.schema.json
    escalation-event.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — /iikit-01 output)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  002_pretool_guardrails/
    __init__.py
    hook.py              # PreToolUseHook protocol + RefundPolicyHook concrete
    policy.py            # PolicyConfig loader (reads config/policy.json per-invocation, FR-011)
    models.py            # pydantic v2 models: ToolCallPayload, PolicyConfig, HookVerdict,
                         #   StructuredError, EscalationEvent
    errors.py            # reason-code enum: schema_violation, policy_breach, hook_failure
    escalation.py        # EscalationEvent emitter (writes to JSONL audit log)
    refund_api_stub.py   # local stub of the "external" refund API; logs every call it
                         #   receives so tests can assert zero calls on reject (FR-006)
    prompts.py           # system-prompt string constants; MUST NOT contain the policy limit
                         #   (FR-008; enforced by AST lint)
    runner.py            # CLI entrypoint: python -m katas.002_pretool_guardrails.runner
    events.py            # JSONL audit-log writer (shared shape with kata 1's EventLog)
    README.md            # kata narrative (written during /iikit-07)

tests/
  katas/
    002_pretool_guardrails/
      conftest.py        # fixture-session loader, policy snapshotter, stub-API inspector
      features/          # Gherkin files produced by /iikit-04-testify
        pretool_guardrails.feature
      step_defs/
        test_pretool_guardrails_steps.py
      unit/
        test_hook_verdict_within_limit.py         # US1-AS1, FR-001, SC-001
        test_hook_verdict_over_limit.py           # US2-AS1, US2-AS2, US2-AS3, FR-004, FR-006
        test_hook_verdict_at_limit_boundary.py    # Edge: exactly-at-limit; stance declared
        test_schema_violation_missing_amount.py   # Edge: missing amount → schema_violation
        test_schema_violation_non_numeric.py      # Edge: "five hundred" → schema_violation
        test_schema_violation_negative.py         # Edge: -100 → schema_violation
        test_schema_violation_extra_fields.py     # Edge: extra fields stance
        test_hook_failure_failsafe.py             # Edge: corrupt policy → fail closed, hook_failure
        test_policy_change_takes_effect.py        # US3-AS1..AS3, FR-011, SC-004
        test_structured_error_shape.py            # FR-003, FR-005, SC-003
        test_escalation_event_emitted.py          # FR-007, Principle VI
        test_determinism_repeat_run.py            # FR-010
      lint/
        test_prompt_has_no_limit.py               # AST: prompts.py has no numeric literal
                                                  #   matching PolicyConfig.max_refund (FR-008)
        test_no_float_in_amount_path.py           # AST: amount path uses Decimal only
      fixtures/
        within_limit.json
        at_limit.json
        over_limit.json
        missing_amount.json
        negative_amount.json
        non_numeric_amount.json
        extra_fields.json
        hook_failure_corrupt_policy.json
        policy_change_before.json
        policy_change_after.json
        concurrent_policy_update.json
        retry_same_over_limit.json

config/
  policy.json            # seeded example policy snapshot; tests copy to per-run tmpdirs

runs/                    # gitignored; per-session JSONL output
```

**Structure Decision**: Single-project layout, one package per kata under
`katas/NNN_<slug>/`. Kata 2 reuses the same layout convention chosen in
Kata 1's plan so the 20-kata FDD cadence stays uniform. No shared `common/`
library is introduced yet — YAGNI until a second kata concretely needs one of
Kata 2's primitives (a future `guardrails-common/` extraction is noted but not
built here).

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  PreToolUse Hook   │───────│   Policy Config    │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Refund API Stub │ │Escalation Sink │ │ Hook Event Log │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `PreToolUse Hook` owns the core control flow
for this kata's objective; `Policy Config` is the primary collaborator/policy reference;
`Refund API Stub`, `Escalation Sink`, and `Hook Event Log` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted and noted:
- No async hook evaluation / concurrency primitives: spec's concurrent-policy-
  update edge case is solved by **snapshotting** the policy at invocation entry
  (a `PolicySnapshot` field on `HookVerdict`), not by locks.
- No persistent DB for the audit log: JSONL is sufficient for FR-009, same as
  Kata 1.
- No retry / backoff around the refund API stub: not required by the spec and
  would obscure the zero-call assertion (SC-002).
- No custom DSL for the policy: `PolicyConfig` is a flat pydantic model; adding
  expression evaluation would invite prompt-injection surface and is explicitly
  out of scope per Principle VI (limit is data, not behavior).
