# Phase 1 Data Model: Structured Human Handoff Protocol

All entities are pydantic v2 models at `katas/016_human_handoff/models.py`.

## HandoffPayload

The canonical escalation envelope. This IS the `escalate_to_human` tool's
input schema.

| Field | Type | Notes |
|-------|------|-------|
| `escalation_id` | `UUID` | Generated at construction. |
| `customer_id` | `str` | Required. May be `"unknown"` (explicit sentinel) if the session truly has none — never null. |
| `issue_summary` | `str` (maxlen 500) | Machine-friendly summary, not the raw transcript. |
| `actions_taken` | `list[ActionRecord]` | Ordered history of prior agent actions. May be empty; emptiness is permitted but logged. |
| `escalation_reason` | `Literal[...]` | Closed enum: policy-breach, out-of-policy-demand, operational-limit, unresolved-after-retries, explicit-user-request. |
| `severity` | `Literal["low","medium","high","critical"]` | Added in schema v1.1 — required. |
| `created_at` | `datetime` | UTC. |

## ActionRecord

One prior step the agent took before escalating.

| Field | Type | Notes |
|-------|------|-------|
| `step_id` | `str` | |
| `action_type` | `str` | e.g. `"tool_invoked"`, `"retry_attempted"`, `"policy_violation"`. |
| `description` | `str` | Short — the queue renders these as a bullet list. |
| `outcome` | `Literal["ok", "error", "blocked"]` | |
| `timestamp` | `datetime` | UTC. |

## SessionSuspended (exception, not a model)

Raised by `SuspensionAwareClient` whenever `messages.create` is called after
`escalate_to_human`. Test asserts 0 bytes of additional conversational content
emitted after that point (FR-001).

## EscalationEvent (event-log record)

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | `UUID` | |
| `escalation_id` | `UUID` | FK to HandoffPayload. |
| `source_kata` | `str \| None` | When the escalation originated upstream (kata 2 / kata 6), name captured here. |
| `handoff_payload_hash` | `str` | sha256 of the serialized payload for tamper detection. |
| `timestamp` | `datetime` | UTC. |

## OperatorQueueEntry

What lands in `runs/handoffs/index.jsonl`.

| Field | Type | Notes |
|-------|------|-------|
| `escalation_id` | `UUID` | |
| `severity` | `Literal[...]` | Mirrors HandoffPayload.severity. |
| `created_at` | `datetime` | UTC. |
| `status` | `Literal["pending", "acknowledged", "resolved"]` | Managed by the human operator. |
| `queue_path` | `str` | Relative path to the full payload file. |

## Relationships

```
HandoffPayload
  ├── ActionRecord (0..N)
  └── EscalationEvent (1..1 — recorded on emission)
        → OperatorQueueEntry (1..1 — index entry)
```

## Why this shape

- Making `customer_id` required-non-null with an explicit `"unknown"` sentinel
  forces a conscious decision instead of silently dropping the field.
- `handoff_payload_hash` closes the provenance loop: the payload as received
  by the operator is cryptographically tied to what the agent emitted.
- `severity` as a required literal (not free text) constrains downstream
  routing logic at schema level.
