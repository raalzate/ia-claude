# Phase 1 Data Model: Deterministic Guardrails via PreToolUse Hooks

All entities below are implemented as pydantic v2 models at
`katas/002_pretool_guardrails/models.py`. Validation runs on construction; any
invalid payload raises `pydantic.ValidationError` and is converted by the hook
into a `StructuredError` with `reason_code = schema_violation` — it does NOT
reach the external refund API (FR-006, SC-002).

## ToolCallPayload

The typed input the agent sends to `process_refund` before dispatch.

| Field | Type | Notes |
|-------|------|-------|
| `tool_name` | `Literal["process_refund"]` | Anything else is not in scope for this kata. |
| `correlation_id` | `str` (UUID4) | Uniquely identifies this invocation across turn → hook → audit → escalation (FR-009). |
| `amount` | `decimal.Decimal` | REQUIRED. Validator asserts `amount > 0` (FR-002, FR-003). Floats and strings are rejected with a schema violation (edge cases: non-numeric, negative). |
| `currency` | `Literal["USD"]` | Fixed to USD for this kata; extending currencies is out of scope. |
| `customer_id` | `str` (non-empty) | Opaque identifier echoed to the refund API stub. |
| `reason` | `str` \| `None` | Optional free-text note from the model; NEVER parsed by the hook. Present in audit log for traceability only. |

**Invariants**
- `amount` MUST be `Decimal`. A float on this field is a programming error; the
  AST lint test `test_no_float_in_amount_path.py` catches it statically.
- `model_config = ConfigDict(extra="forbid")`. Extra fields → schema violation
  (edge case "extra fields" — explicit strict stance per spec §Edge Cases).

## PolicyConfig

Loaded fresh from `config/policy.json` at invocation entry (FR-011, SC-004).

| Field | Type | Notes |
|-------|------|-------|
| `policy_id` | `str` | Stable identifier, e.g. `"refund-policy"`. |
| `policy_snapshot_version` | `str` | Monotonic version string; changes every time the file is edited. |
| `max_refund` | `decimal.Decimal` | The policy threshold. The ONLY place this number lives at runtime. Never duplicated into a prompt (FR-008). |
| `comparison_stance` | `Literal["strict_less_than"]` | Declared stance per D-008. Amount must be `< max_refund` to pass. |
| `escalation_pathway` | `str` | Routing target written into `StructuredError` and `EscalationEvent` (FR-007). |
| `effective_from` | `datetime` (UTC) | When the snapshot became active; recorded on the audit log. |

**Invariants**
- `PolicyConfig` is immutable in-process (`model_config = ConfigDict(frozen=True)`).
- A new invocation MUST reload the policy; the same instance is NOT reused
  across invocations (tested by `test_policy_change_takes_effect.py`).

## HookVerdict

The deterministic decision produced by `RefundPolicyHook.evaluate`.

| Field | Type | Notes |
|-------|------|-------|
| `verdict` | `Literal["allow", "reject"]` | Machine decision — never prose. |
| `reason_code` | `Literal["schema_violation", "policy_breach", "hook_failure"] \| None` | Non-null iff `verdict == "reject"` (FR-003, FR-012). |
| `correlation_id` | `str` (UUID4) | Echo of `ToolCallPayload.correlation_id`. |
| `policy_id` | `str` | Echo of `PolicyConfig.policy_id`. |
| `policy_snapshot_version` | `str` | Echo of the snapshot evaluated against (FR-009). |
| `evaluated_at` | `datetime` (UTC) | Timestamp of the verdict. |
| `offending_field` | `str \| None` | Dotted path, e.g. `"amount"` or `"$"` for whole-payload issues. Non-null iff reject. |
| `offending_value` | `str \| None` | String-serialized value that tripped the rule; `None` if absent or redacted. |

**State transitions**
1. Hook receives `ToolCallPayload` and a `PolicyConfig` snapshot.
2. Hook validates the payload via `ToolCallPayload.model_validate`.
   Validation failure → `HookVerdict(verdict="reject", reason_code="schema_violation", ...)`.
3. If payload is valid, hook compares `amount < policy.max_refund`.
   Comparison failure → `HookVerdict(verdict="reject", reason_code="policy_breach", ...)`.
4. Any internal exception during steps 2–3 → `HookVerdict(verdict="reject", reason_code="hook_failure", ...)` (FR-012, fail-closed).
5. All other inputs → `HookVerdict(verdict="allow", reason_code=None, ...)` and the SDK dispatches to the refund API stub.

**Determinism invariant (FR-010)**: Given the same `(ToolCallPayload,
PolicyConfig)` pair, `HookVerdict` is byte-equivalent except for
`evaluated_at`. The test `test_determinism_repeat_run.py` asserts this by
comparing two verdicts on identical inputs with `evaluated_at` excluded from
the diff.

## StructuredError

The machine-parseable object returned into the model's next context window on
any reject verdict (FR-003, FR-005, SC-003).

| Field | Type | Notes |
|-------|------|-------|
| `verdict` | `Literal["reject"]` | Always reject — allows are not errors. |
| `reason_code` | `Literal["schema_violation", "policy_breach", "hook_failure"]` | Echo of `HookVerdict.reason_code`. |
| `field` | `str` | Offending field path (e.g. `"amount"`). |
| `rule_violated` | `str` | Rule identifier, e.g. `"positive_decimal"`, `"<max_refund"`, `"hook_internal_error"`. |
| `policy_id` | `str \| None` | Non-null iff `reason_code == "policy_breach"`. |
| `policy_snapshot_version` | `str \| None` | Non-null iff `reason_code == "policy_breach"`. |
| `correlation_id` | `str` | Used to join the error to the audit log entry. |
| `escalation_pathway` | `str` | Copied from `PolicyConfig.escalation_pathway` on `policy_breach`; internal route on `hook_failure`; `None` string `"client_fix_required"` on `schema_violation`. |
| `message` | `str` | Short, deterministic English summary, built from the fields above — NOT the enforcement mechanism, purely UX. |

**Invariant**: This is the *only* shape of rejection the model sees.
Free-text apology from the tool channel is forbidden (FR-005).

## EscalationEvent

Emitted on every `policy_breach` or `hook_failure` reject (FR-007,
Principle VI). NOT emitted on `schema_violation` (per D-007).

| Field | Type | Notes |
|-------|------|-------|
| `kind` | `Literal["escalation"]` | Discriminator on the JSONL audit log. |
| `correlation_id` | `str` | Joins the escalation to the verdict, the structured error, and the model turn. |
| `emitted_at` | `datetime` (UTC) | Timestamp. |
| `policy_id` | `str` | Which policy triggered escalation. |
| `policy_snapshot_version` | `str` | Pinned snapshot (spec edge: concurrent policy update). |
| `summary` | `str` | One-sentence description: "Refund of $X for customer Y blocked by policy Z vN." |
| `actions_taken` | `list[str]` | Always `[]` on a pre-call block — the whole point is that no action was taken. Field kept for shape parity with Principle VI escalation payload. |
| `escalation_reason` | `Literal["policy_breach", "hook_failure"]` | Narrower than `HookVerdict.reason_code` — matches the two causes that escalate. |
| `routing_target` | `str` | Copied from `PolicyConfig.escalation_pathway`. |
| `rejected_payload_digest` | `str` | SHA-256 of the JSON-serialized `ToolCallPayload`; the raw payload is NOT included to avoid leaking PII into the audit log. |

## AuditRecord (writer shape, not a distinct new entity)

One JSONL line per event on `runs/<session-id>/events.jsonl`. Records are
tagged by `kind`:

- `kind: "invocation"` — initial payload seen by the hook.
- `kind: "verdict"` — `HookVerdict` serialized.
- `kind: "escalation"` — `EscalationEvent` serialized.
- `kind: "refund_api_call"` — mirror of what the stub actually received (only
  written on allow verdicts; absent on reject by construction — this absence
  is what SC-002 asserts).

**Invariant (FR-009, Principle VII)**: For every `correlation_id`, exactly one
`invocation` record and exactly one `verdict` record exist. A
`refund_api_call` record exists iff the verdict was `allow`. An `escalation`
record exists iff the verdict was `reject` with `reason_code ∈ {policy_breach,
hook_failure}`.

## Relationships

```
ToolCallPayload --(evaluated with)--> PolicyConfig (snapshot)
         \                                  /
          \                                /
           v                              v
                     HookVerdict
                     /     |      \
                allow    reject-breach   reject-schema / reject-hook-failure
                  |       |                 |
           RefundAPI   StructuredError → model context
              stub     EscalationEvent  → audit log (policy_breach / hook_failure only)
              (calls
              logged)
```

## What is deliberately NOT modeled

- Multi-tool policy registries: this kata defends one tool (`process_refund`).
  A generic registry is deferred to a later kata (likely Kata 7 or Kata 15).
- Distributed policy store / remote config service: `config/policy.json` is
  sufficient for FR-011 / SC-004, and adds no teaching value in this kata.
- Retry / exponential backoff on hook-failure: the kata's point is fail-closed
  (FR-012), not fault-tolerant retry.
- PII redaction of the `reason` or `customer_id`: this kata only digests the
  payload for the audit log; full redaction rules are future work.
- Multi-currency amount: `currency` fixed to `"USD"`; adding FX rates would
  confuse the policy-evasion lesson.
