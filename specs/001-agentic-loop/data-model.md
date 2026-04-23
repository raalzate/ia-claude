# Phase 1 Data Model: Agentic Loop & Deterministic Control

All entities below are implemented as pydantic v2 models at
`katas/001_agentic_loop/models.py`. Validation runs on construction; any
invalid payload raises `pydantic.ValidationError` and the run halts.

## AgentSession

One workshop run.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | `str` (UUID4) | Used as the runs/ subdirectory name. |
| `model` | `str` | Claude model id used for the session. |
| `registered_tools` | `list[ToolDefinition]` | Immutable for the session. |
| `started_at` | `datetime` (UTC) | Populated at construction. |
| `completed_at` | `datetime \| None` | Populated on terminal halt. |
| `termination` | `TerminationReason \| None` | Final cause; None while running. |

**Invariants**
- `registered_tools` is set once at construction; adding tools mid-session is
  not allowed (would complicate replayability).
- `completed_at` is None until exactly one terminal halt is recorded.

## StopSignal (Literal type)

Closed set of recognized structured stop signals:

```
Literal["tool_use", "end_turn", "max_tokens", "stop_sequence"]
```

Any value outside this set surfaces as an `UnhandledStopSignal` instance (see
below) — never silently mapped to a known value.

## UnhandledStopSignal

| Field | Type | Notes |
|-------|------|-------|
| `raw_value` | `str \| None` | The exact value the API returned, or `None` if absent. |
| `reason_label` | `Literal["unhandled_signal", "absent_signal"]` | Human-readable bucket. |

## Turn

One response cycle.

| Field | Type | Notes |
|-------|------|-------|
| `iteration` | `int` (≥ 0) | Zero-indexed position in the loop. |
| `stop_signal` | `StopSignal \| UnhandledStopSignal` | Structured branching input. |
| `tool_calls` | `list[ToolCall]` | Empty unless `stop_signal == "tool_use"`. |
| `assistant_text_blocks` | `list[str]` | Raw text blocks — stored for the event log ONLY; loop logic MUST NOT read these. |
| `response_id` | `str` | Echo of the SDK response id for audit. |

**State transitions**
1. `Turn` constructed after each SDK response.
2. If `stop_signal == "tool_use"`, loop produces N `ToolInvocation`s and the
   resulting `ToolResult`s are appended to history; a new `Turn` is created on
   the next iteration.
3. If `stop_signal == "end_turn"`, the session transitions to
   `termination = end_turn` and halts.
4. If `stop_signal in {"max_tokens", "stop_sequence"}`, termination =
   `unhandled_handled_explicitly` (i.e. known but not resumable in this kata).
5. If `stop_signal` is an `UnhandledStopSignal`, termination = `unhandled_signal`
   or `absent_signal` and the session halts with that label.

## ToolDefinition

Registered at session start.

| Field | Type | Notes |
|-------|------|-------|
| `name` | `str` | Unique within the session. |
| `description` | `str` | Passed to the model. |
| `input_schema` | `dict[str, Any]` | JSON Schema handed to the SDK. |

Duplicate `name` across registered tools is a `ValueError` at construction.

## ToolCall

Extracted from a `tool_use`-flagged response.

| Field | Type | Notes |
|-------|------|-------|
| `tool_use_id` | `str` | Echo of the SDK id used to correlate with `ToolResult`. |
| `tool_name` | `str` | MUST match a registered `ToolDefinition.name`. |
| `input` | `dict[str, Any]` | Payload conforming to the tool's `input_schema`. |

Validation: if `tool_name` is not registered OR `input` fails the tool's
`input_schema`, a `MalformedToolUse` exception is raised and the loop halts
with termination reason `malformed_tool_use` (FR-008).

## ToolResult

What gets appended to history after executing a `ToolCall`.

| Field | Type | Notes |
|-------|------|-------|
| `tool_use_id` | `str` | Same id as the originating `ToolCall`. |
| `status` | `Literal["ok", "error"]` | Mechanical outcome; never inferred from text. |
| `output` | `Any` (JSON-serializable) | Tool return value on `ok`; structured error object on `error`. |
| `error_category` | `str \| None` | Non-null iff `status == "error"`; echoes MCP-style categorization for forward compat with Kata 6. |

## EventRecord

The JSONL audit line. This is the source of truth for reconstructing a run.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | `str` | UUID of the parent session. |
| `iteration` | `int` | Matches `Turn.iteration`. |
| `timestamp` | `datetime` (UTC) | When the record was emitted. |
| `stop_signal` | `str` | Serialized string form of the structured signal. |
| `branch_taken` | `Literal["tool_dispatch", "terminate", "halt_unhandled"]` | What the loop did after observing the signal. |
| `tool_name` | `str \| None` | Populated on `tool_dispatch`. |
| `tool_outcome` | `Literal["ok", "error", null]` | Populated on `tool_dispatch`. |
| `termination_cause` | `TerminationReason \| None` | Populated only on the terminal iteration. |

**Invariants**
- Exactly one record per iteration.
- Exactly one record in the file has a non-null `termination_cause`.
- No text-derived field is allowed on `EventRecord` — enforced by the model's
  field set (there is no `prose_excerpt` / `completion_hint` / etc.).

## TerminationReason (Literal type)

```
Literal[
  "end_turn",
  "unhandled_signal",
  "absent_signal",
  "max_tokens",
  "stop_sequence",
  "malformed_tool_use",
  "tool_error_unrecoverable",
]
```

`tool_error_unrecoverable` is reserved for the edge case where a tool raises
and the loop cannot continue (e.g. internal invariant broken). Routine tool
errors keep the loop running per FR-007.

## EventLog (writer, not a schema)

A tiny class owning the open file handle at `runs/<session_id>/events.jsonl`.
One method, `emit(record: EventRecord)`, appends one line. The file is
`fsync`ed on close so post-crash replay is guaranteed.

## Relationships

```
AgentSession
  ├── registered_tools: [ToolDefinition]
  ├── turns: [Turn]            (one per loop iteration)
  │     └── tool_calls: [ToolCall]
  │            └── result: ToolResult   (in conversation history, not on Turn)
  └── event_log: [EventRecord]    (one per iteration)
```

## What is deliberately NOT modeled

- Retry budgets / backoff state — out of scope per Complexity Tracking.
- Multi-session state — one session is one kata run.
- Persistent history across sessions — replayable from the JSONL event log.
