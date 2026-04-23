# Phase 1 Data Model: MCP Integration with Structured Error Handling

All entities below are implemented as pydantic v2 models at
`katas/006_mcp_errors/models.py`. Validation runs on construction; any
invalid payload raises `pydantic.ValidationError` and the call halts before
the agent sees it — this is the schema floor Principle II (NN) demands and is
the only way FR-001 / FR-002 / FR-007 are enforceable as gates rather than
guidelines.

## ToolCall

One invocation of an MCP-exposed tool. Owns its own retry budget so
exhaustion decisions are local and replayable (FR-005).

| Field | Type | Notes |
|-------|------|-------|
| `call_id` | `str` (UUID4) | Stable identity across retries of the same logical call. |
| `tool_name` | `str` (pattern `^[a-zA-Z][\w-]{0,63}$`) | Must match a server-registered tool. |
| `input` | `dict[str, Any]` | Payload the server validates against its declared input schema. |
| `attempt` | `int` (≥ 1) | 1-indexed attempt counter — `1` means first try. |
| `budget` | `RetryBudget` | Travels with the call; see below. |
| `parent_call_id` | `str \| None` | Set on retries — links to the original call for the chained-failures fixture. |

**Invariants**
- `attempt ≤ budget.max_attempts` at construction — exceeding it is a
  programmer error, not a runtime state.
- Retries MUST construct a NEW `ToolCall` with `parent_call_id` set and
  `attempt` incremented — mutation is forbidden (simplifies event-log replay,
  Principle VII).

## MCPResponse

Every response from the server — success or failure — runs through this
model. The failure variant carries the `StructuredError` payload; the success
variant is an opaque `output`.

| Field | Type | Notes |
|-------|------|-------|
| `call_id` | `str` | Echoes `ToolCall.call_id`. |
| `isError` | `bool` | `True` iff the response is a failure (FR-001). |
| `output` | `Any \| None` | Present iff `isError=False`. |
| `error` | `StructuredError \| None` | Present iff `isError=True` (FR-002). |

**Invariants**
- Exactly one of `output` / `error` is non-null.
- `isError=True` with `error is None` is a pydantic validation error —
  operationalizes FR-007 at the schema layer.

## StructuredError

The failure-metadata contract. This is the single object that drives every
agent branch decision (FR-004).

| Field | Type | Notes |
|-------|------|-------|
| `isError` | `Literal[True]` | Redundant with `MCPResponse.isError` but carried inside the payload so logs remain self-describing (Principle VII). |
| `errorCategory` | `Literal["transient", "validation", "auth", "quota", "internal", "transport", "schema_violation"]` | Closed enumeration — see research.md D-003. |
| `isRetryable` | `bool` | Policy input — FR-004 branches here directly. |
| `detail` | `str` (min 1, max 1024) | Human-readable explanation. Length-capped to keep Principle III (Context Economy) happy. |
| `retry_after_seconds` | `int \| None` | Advisory backoff hint (e.g. from a rate-limit header). `None` means "use budget default". |

**Invariants**
- `errorCategory == "validation"` → `isRetryable == False`.
- `errorCategory == "auth"` → `isRetryable == False`.
- `errorCategory == "schema_violation"` → `isRetryable == False`.
- `errorCategory == "transient"` → `isRetryable == True`.
- `errorCategory == "quota"` → `isRetryable == True` (with `retry_after_seconds` strongly preferred).
- These invariants are enforced as a pydantic `model_validator` so a server
  that returns `validation` + `isRetryable=True` fails at the boundary.

## RetryBudget

Declared retry capacity attached to each `ToolCall` (FR-005).

| Field | Type | Notes |
|-------|------|-------|
| `max_attempts` | `int` (≥ 1) | Inclusive cap. Default `3`. |
| `backoff_seconds` | `float` (≥ 0) | Base delay between retries. Clock is injectable for tests. |
| `elapsed_attempts` | `int` (≥ 0, ≤ max_attempts) | Attempts already consumed. |

**Methods (pure functions returning a new budget)**
- `attempt() -> RetryBudget` — increment `elapsed_attempts` by 1; raises
  `BudgetExhausted` if the result would exceed `max_attempts`.
- `remaining() -> int` — `max_attempts - elapsed_attempts`.
- `is_exhausted() -> bool` — `remaining() == 0`.

**Invariants**
- `elapsed_attempts ≤ max_attempts` at construction.
- `attempt()` is idempotent per attempt — callers MUST threadthe returned
  budget through to the next `ToolCall`.

## RecoveryAction

The typed verdict produced by `policy.decide(response, call)`. This is the
agent's branch (FR-004).

| Field | Type | Notes |
|-------|------|-------|
| `action` | `Literal["retry", "escalate", "abort"]` | Closed set. |
| `reason` | `str` (min 1) | Why this action was chosen (e.g. `"retryable-within-budget"`). Goes to the log. |
| `next_call` | `ToolCall \| None` | Populated iff `action == "retry"`. |
| `escalation` | `EscalationTrigger \| None` | Populated iff `action == "escalate"` or `action == "abort"`. |

**Branch rules (policy.py)**
- `response.isError == False` → action not computed (success path).
- `StructuredError.isRetryable == False` → `action = "escalate"`,
  `escalation != None`, zero retries executed (SC-004).
- `StructuredError.isRetryable == True` AND `budget.remaining() > 0` →
  `action = "retry"`, `next_call` has `attempt += 1`.
- `StructuredError.isRetryable == True` AND `budget.is_exhausted()` →
  `action = "escalate"` with `escalation.reason = "budget_exhausted"`
  (edge case 3, FR-005, Principle VI).

## EscalationTrigger

The typed hand-off payload to a human or higher-level policy (Principle VI,
FR-008).

| Field | Type | Notes |
|-------|------|-------|
| `trigger_id` | `str` (UUID4) | For correlation with the log. |
| `source_call_id` | `str` | The `ToolCall.call_id` that caused the escalation. |
| `reason` | `Literal["non_retryable_category", "budget_exhausted", "schema_violation", "transport_unrecoverable"]` | Closed set — drives the receiving sink's routing. |
| `error` | `StructuredError` | The triggering payload (may be synthesized — see research.md D-007). |
| `attempts_taken` | `int` | How many attempts were consumed before escalating. |
| `escalation_sink` | `Literal["human_handoff", "clarification_prompt", "abort_with_explanation"]` | Declared recipient — explicit and human-reviewable (FR-008). |

**Invariants**
- `attempts_taken ≥ 1` — you cannot escalate before trying.
- `attempts_taken == 1` for every `StructuredError.isRetryable == False` case
  (SC-004 invariant).

## ErrorLogRecord

The JSONL line written to `runs/<session-id>/errors.jsonl`. One record per
attempt — successful attempts are also recorded to satisfy SC-003's
denominator counting (FR-006).

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | `str` (UUID4) | Parent session. |
| `timestamp` | `datetime` (UTC) | Emission time. |
| `call_id` | `str` | `ToolCall.call_id`. |
| `attempt` | `int` | `ToolCall.attempt`. |
| `tool_name` | `str` | Echoed for grouping. |
| `outcome` | `Literal["success", "retried_success", "retried_exhausted", "escalated", "aborted"]` | Closed set — enables SC-003 aggregation without text parsing. |
| `error_category` | `str \| None` | `None` iff `outcome == "success"`. |
| `is_retryable` | `bool \| None` | `None` iff `outcome == "success"`. |
| `detail` | `str \| None` | `None` iff `outcome == "success"`. |
| `escalation_trigger_id` | `str \| None` | Populated iff `outcome in {"escalated", "aborted"}`. |

**Invariants**
- One record per attempt.
- Records for the same `call_id` form a time-ordered chain whose final
  outcome is one of `{"retried_success", "retried_exhausted", "escalated",
  "aborted", "success"}`.
- No free-text field is allowed beyond `detail` — the log is aggregated by
  structured fields (SC-003 auditability).

## Relationships

```
AgentSession
  ├── tool_calls: [ToolCall]
  │     ├── budget: RetryBudget       (travels with the call)
  │     ├── response: MCPResponse     (one per attempt)
  │     │     └── error: StructuredError | None
  │     └── recovery: RecoveryAction
  │           └── escalation: EscalationTrigger | None
  └── error_log: [ErrorLogRecord]     (one per attempt, ordered)
```

## What is deliberately NOT modeled

- **Multi-server routing / failover.** One kata, one MCPServer. Adding
  failover logic would dilute the structured-error lesson (YAGNI — same
  rationale as Kata 1's §"What is deliberately NOT modeled").
- **Exponential backoff tuning / jitter.** The kata teaches *budget as
  data*; backoff curves are a distinct concern.
- **Persistent error store across sessions.** JSONL per run is the scope of
  SC-003. Cross-session analytics belong to Kata 20 (data provenance), not
  here.
- **Retry budget shared across tool calls.** Each call owns its budget —
  chained-failures fixture depends on this isolation.
