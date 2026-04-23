# Phase 0 Research: Deterministic Guardrails via PreToolUse Hooks

## Decisions

### D-001 — Implement `PreToolUseHook` as a Protocol, with a concrete `RefundPolicyHook`

- **Decision**: Define a `PreToolUseHook` `typing.Protocol` with a single
  method `evaluate(payload: ToolCallPayload, policy: PolicyConfig) -> HookVerdict`.
  Ship one concrete implementation, `RefundPolicyHook`, bound to the
  `process_refund` tool. The Anthropic SDK dispatcher calls the hook during its
  PreToolUse phase; the hook is the sole enforcement path before the external
  refund API.
- **Rationale**: FR-001 requires interception *strictly before* the external
  API is called. A Protocol keeps the enforcement contract first-class and
  lets future katas (Kata 7, 15) register additional hooks without touching
  existing ones. Naming the concrete class after the policy it enforces makes
  the "hook is the only control" invariant obvious in the source (Principle I).
- **Alternatives considered**:
  - *Inline the policy check in the tool body.* Rejected: violates FR-001
    (enforcement happens *inside* the tool, after dispatch begins), and also
    violates the anti-pattern defense — tool authors could quietly skip it.
  - *Abstract base class instead of Protocol.* Rejected: `Protocol` avoids an
    inheritance tree for a one-method contract; duck-typing is cleaner for
    this scope.

### D-002 — Pydantic v2 + `decimal.Decimal` for `ToolCallPayload.amount`

- **Decision**: `ToolCallPayload.amount` is a `Decimal` with validator asserting
  `amount > 0` (FR-002, FR-003). Comparison against `PolicyConfig.max_refund`
  uses `Decimal` semantics. Any attempt to construct `ToolCallPayload` from a
  JSON string/bool/missing-field path raises `pydantic.ValidationError` whose
  `errors()` output is used to build the `StructuredError` (FR-005).
- **Rationale**: Principle II (Schema-Enforced Boundaries, NN) plus the spec's
  edge cases (missing, non-numeric, negative). `Decimal` prevents
  `0.1 + 0.2 == 0.30000000000000004` class of policy-evasion bugs — critical
  for a monetary guardrail. pydantic's `ValidationError` carries field path
  and rule, which map 1:1 to `StructuredError.field` and
  `StructuredError.rule_violated`.
- **Alternatives considered**:
  - *`float` amount with epsilon comparison.* Rejected: invites rounding
    defects in a compliance-facing path; impossible to audit deterministically.
  - *TypedDict + manual validators.* Rejected: duplicates pydantic's work and
    provides no runtime enforcement — direct Principle II violation.

### D-003 — Policy is external data, loaded per-invocation from `config/policy.json`

- **Decision**: `PolicyConfig` is loaded fresh at invocation entry via a
  `load_policy_snapshot()` call that reads `config/policy.json` and returns an
  immutable pydantic model. Each `HookVerdict` carries the
  `policy_snapshot_version` it was evaluated against.
- **Rationale**: FR-011 + SC-004 require a policy change to take effect on the
  next invocation with no prompt edit, no redeploy, no retraining. A per-
  invocation read is the simplest mechanism that makes this property
  observable; the `policy_snapshot_version` on the verdict closes the spec's
  "concurrent policy update" edge case by pinning the evaluation to one
  snapshot.
- **Alternatives considered**:
  - *Environment variable holding the limit.* Rejected: process restart needed
    to refresh, defeating FR-011.
  - *In-process policy cache with TTL.* Rejected: adds a time-dependent path
    that breaks FR-010 (identical inputs → identical verdicts) and complicates
    the audit log.
  - *Remote policy service.* Rejected as overkill for the kata; revisit if a
    future kata exercises distributed policy.

### D-004 — Structured error object returned into model context, never free text

- **Decision**: On any reject verdict, the SDK tool-result channel returns a
  `StructuredError` pydantic model serialized to JSON. Fields:
  `verdict="reject"`, `reason_code ∈ {schema_violation, policy_breach,
  hook_failure}`, `field`, `rule_violated`, `policy_id`,
  `policy_snapshot_version`, `correlation_id`, `escalation_pathway`. The model
  sees the object in its next turn and MUST react (FR-005, SC-003).
- **Rationale**: The spec's defining anti-pattern is "prompt says don't
  refund >$500; the model sometimes complies." A structured error forces the
  model to observe the rejection in typed form rather than inferring it from
  prose. Reason codes distinguish `policy_breach` (amount exceeded) from
  `schema_violation` (malformed payload) from `hook_failure` (hook exceptioned)
  per FR-012 and the edge-case list in spec §Edge Cases.
- **Alternatives considered**:
  - *Return a free-text apology.* Rejected: exactly the anti-pattern the
    kata exists to disprove.
  - *Silently skip the tool call.* Rejected: FR-005 explicitly forbids silent
    skips; the model must be given a concrete signal to react to.

### D-005 — Refund API is a local stub that records every call it *does* receive

- **Decision**: The "external" refund API is implemented as
  `refund_api_stub.py`, a local module with one function `process_refund` that
  appends a JSON line to `runs/<session-id>/refund_api_calls.jsonl` for every
  invocation it handles. Tests inspect this file to assert **zero** lines for
  rejected invocations (FR-006, SC-001, SC-002).
- **Rationale**: The kata's pedagogy is *blocking before dispatch*, not
  integrating with a real third party. A local stub keeps tests offline and
  deterministic while making the "zero external calls" assertion mechanical
  rather than observed via prose. Using a file-backed call log makes the
  evidence replayable post-run.
- **Alternatives considered**:
  - *Mock the stub with `unittest.mock`.* Rejected: couples tests to mock
    internals and is harder to audit (no durable artifact). The JSONL call log
    doubles as teaching material during the walkthrough.
  - *Point at a sandbox of a real refund provider.* Rejected: introduces
    network flakiness and a credential surface irrelevant to the kata.

### D-006 — AST lint asserts the policy limit is NOT in the system prompt

- **Decision**: `tests/katas/002_pretool_guardrails/lint/test_prompt_has_no_limit.py`
  parses `katas/002_pretool_guardrails/prompts.py` with `ast` and fails the
  build if any string constant in that module contains a numeric literal equal
  to the current `PolicyConfig.max_refund` (or any obvious variant like the
  bare number or a formatted currency string). This machine-checkable gate
  operationalizes FR-008 and US2-AS4 (the anti-pattern test).
- **Rationale**: Principle I is absolute. Without a CI-enforced check, a
  well-meaning future edit can migrate the limit into the prompt and quietly
  recreate the anti-pattern the kata exists to defend against. An AST test is
  the only durable defense.
- **Alternatives considered**:
  - *Code review only.* Rejected: review drift is exactly what the constitution
    warns against.
  - *String `grep` in a shell script.* Rejected: brittle to formatting and
    escapes; `ast` is exact.

### D-007 — Escalation event emitted on every policy-breach reject (and hook-failure reject)

- **Decision**: `escalation.py` emits an `EscalationEvent` (pydantic model)
  whenever a reject verdict has `reason_code ∈ {policy_breach, hook_failure}`.
  The event is written to the same `runs/<session-id>/events.jsonl` audit log
  with a `kind="escalation"` discriminator and carries `correlation_id`,
  `policy_id`, `policy_snapshot_version`, a payload summary, and a routing
  target. Schema-violation rejects do NOT escalate (those are client bugs, not
  policy events) — this distinction is documented and tested.
- **Rationale**: FR-007 and Principle VI (Human-in-the-Loop, NN) demand a
  typed escalation payload on policy-breaching actions. Keeping escalation in
  the same JSONL audit stream as verdicts simplifies replay and avoids a
  second storage surface.
- **Alternatives considered**:
  - *Escalate on every reject, schema failures included.* Rejected: would flood
    reviewers with client-side bugs, diluting the signal for actual policy
    events.
  - *Emit escalations to a separate queue/service.* Rejected: out of scope for
    the kata and not required by FR-007.

### D-008 — At-limit comparison stance is declared `strict less-than` (amount < limit allowed)

- **Decision**: The policy comparison is strict: `amount < max_refund`. An
  amount exactly equal to `max_refund` is REJECTED with `reason_code =
  policy_breach`. This stance is encoded in `PolicyConfig.comparison_stance =
  "strict_less_than"` and tested by `test_hook_verdict_at_limit_boundary.py`.
- **Rationale**: The spec edge case "amount exactly at the limit" requires an
  explicit, documented stance so audit and tests agree (Principle VII). Strict
  chosen because a limit is inherently a *cap*; equality is the first amount
  that "isn't within".
- **Alternatives considered**:
  - *Inclusive (`amount <= max_refund` allowed).* Viable and internally
    consistent; rejected for this kata because strict is the less ambiguous
    default for "limit" in a compliance register. Revisitable via
    `PolicyConfig.comparison_stance` without code change if a future policy
    demands it.

## Tessl Tiles

`tessl search pretool-hook` and `tessl search guardrail` (both run 2026-04-23)
each returned 0 relevant results for the Anthropic PreToolUse / schema-
enforced-guardrail domain. **No tiles installed for this feature.**

Follow-up: if a community tile for Anthropic SDK hooks or pydantic-v2 policy
validation later appears (search terms: `pretool-hook`, `anthropic-hook`,
`policy-guardrail`, `decimal-money-validator`), revisit at Kata 7 or Kata 15
plan time. No eval scores recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION from the spec (there were 0) has been resolved
by the decisions above.
