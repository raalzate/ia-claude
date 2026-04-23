# Phase 1 Data Model: Strict Subagent Context Isolation

All entities below are implemented as pydantic v2 models at
`katas/004_subagent_isolation/models.py`. Validation runs on construction and
on `model_validate_json`; any invalid payload raises `pydantic.ValidationError`
and propagates as a terminal error (FR-003, FR-004, SC-002). All models set
`model_config = ConfigDict(extra="forbid")` so the spec's Edge Case #2
(unexpected fields) is rejected at the boundary, not silently absorbed.

## Coordinator (class, not a pydantic model)

The hub. Holds the full user-facing conversation and decomposes work.

| Attribute | Type | Notes |
|-----------|------|-------|
| `session_id` | `str` (UUID4) | Used for the `runs/<session-id>/` directory. |
| `model` | `str` | Claude model id used for the coordinator's own SDK calls. |
| `_history` | `list[dict]` | **Private.** The coordinator's own conversation transcript. MUST NOT be referenced from `subagent.py`; enforced by AST lint (`test_no_history_leak.py`). |
| `_scratchpad` | `list[str]` | **Private.** Coordinator-only notes. Same leakage ban as `_history`. |
| `task_spawner` | `TaskSpawner` | Protocol-typed dependency. Only channel to a subagent. Swappable for FR-008 / SC-003. |
| `handoff_contracts` | `dict[str, HandoffContract]` | One entry per declared subagent role. Keyed by `role_name`. |

**Invariants**
- `Coordinator.spawn_subtask(role_name, payload_fields)` constructs a
  `SubtaskPayload` from `payload_fields` (a **closed** dict whose keys are
  validated against the declared payload schema for `role_name`) — the
  coordinator never passes `_history` or `_scratchpad` into the builder
  (FR-002, FR-007, Principle IV).
- Before returning the final answer to the user, `Coordinator` MUST have
  logged every `(SubtaskPayload, SubagentResult)` pair to the per-run JSONL
  audit files (FR-005).
- A `SubagentResultValidationError` raised inside `task_spawner.spawn(...)`
  propagates out of `Coordinator.run()` as a terminal error — no
  silent retry, no default value substitution (FR-004, SC-002).

## Subagent (class, not a pydantic model)

The spoke. One instance handles exactly one subtask invocation.

| Attribute | Type | Notes |
|-----------|------|-------|
| `role_name` | `str` | Identifies which `HandoffContract` it implements. |
| `_client` | `AnthropicClient` (injectable wrapper) | Each `.run()` opens a fresh `messages.create` — no shared session with the coordinator or sibling subagents. |
| `contract` | `HandoffContract` | The input/output schema pair it implements. |

**Invariants**
- `Subagent.run(payload: SubtaskPayload) -> SubagentResult` is pure w.r.t. the
  input payload: given the same `SubtaskPayload`, the subagent sees the same
  prompt (modulo model nondeterminism). It does NOT read any process-level
  singleton, environment variable, or shared dict that could carry
  coordinator state (FR-002).
- The `subagent.py` module has **no** import of
  `katas.004_subagent_isolation.coordinator` and **no** attribute access
  matching `_history`, `_messages`, `_transcript`, `_scratchpad`, or
  `_private_history`. Enforced by `test_no_history_leak.py` (AST + grep).
- `Subagent.run()` wraps the raw SDK response string in
  `SubagentResult.model_validate_json(raw)`; on `ValidationError` it raises
  `SubagentResultValidationError` — never returns a partial or coerced result
  (FR-003, FR-004).

## SubtaskPayload (pydantic v2)

The **only** channel of information from coordinator to subagent. FR-001.

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `Literal["1.0"]` | Versioning per FR-001. |
| `role_name` | `str` | Matches a `HandoffContract.role_name`. |
| `task_id` | `str` (UUID4) | Unique per spawn; correlates with audit log. |
| `instruction` | `str` | The narrow, self-contained instruction for this subtask. |
| `inputs` | `dict[str, Any]` | Declared input fields for this role — shape varies by `HandoffContract.input_schema`. |
| `constraints` | `list[str]` | Optional hard rules (length limits, forbidden topics). Defaults to `[]`. |

**Model config**: `extra="forbid"`. Any field not listed above causes a
`ValidationError` at construction, blocking the spawn before the SDK is
called (implements spec US2-AS2 / FR-001).

**Invariants**
- `inputs` is a closed dict validated against the per-role JSON Schema in
  `HandoffContract.input_schema`. The coordinator never pastes its own
  `_history` into `inputs`; a unit test (`test_payload_minimization.py`)
  asserts that the serialized payload's byte-length never exceeds the sum of
  declared field sizes plus schema overhead.

## SubagentResult (pydantic v2)

The **only** channel of information from subagent back to coordinator. FR-003.

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `Literal["1.0"]` | Paired with `SubtaskPayload.schema_version` via `HandoffContract`. |
| `task_id` | `str` (UUID4) | Echoes the originating `SubtaskPayload.task_id` — mismatch is a validation error. |
| `role_name` | `str` | Echoes `SubtaskPayload.role_name`. |
| `status` | `Literal["ok", "error"]` | Mechanical outcome; not inferred from prose. |
| `output` | `dict[str, Any]` | Declared output fields for this role — shape varies by `HandoffContract.output_schema`. Populated iff `status == "ok"`. |
| `error` | `SubagentError \| None` | Populated iff `status == "error"`. |

**Model config**: `extra="forbid"`. Extra fields are rejected (Edge Case #2).

**Invariants**
- Exactly one of `output` and `error` is non-null, keyed on `status`.
- A subagent result whose `task_id` doesn't match the originating
  `SubtaskPayload.task_id` is a terminal `SubagentResultValidationError`
  (defense against accidental cross-wiring during a swap, FR-008 edge).

## SubagentError (pydantic v2)

| Field | Type | Notes |
|-------|------|-------|
| `category` | `Literal["schema_violation", "tool_failure", "refusal", "other"]` | Explicit escape value `"other"` per Principle II. |
| `detail` | `str` | Human-readable context for an auditor. |

## HandoffContract (pydantic v2)

Pairs one input schema with one output schema to define a swappable subagent
role. FR-008, SC-003.

| Field | Type | Notes |
|-------|------|-------|
| `role_name` | `str` | Unique within a coordinator. |
| `schema_version` | `Literal["1.0"]` | Matches the paired payload/result versions. |
| `input_schema` | `dict[str, Any]` | JSON Schema for `SubtaskPayload.inputs`. |
| `output_schema` | `dict[str, Any]` | JSON Schema for `SubagentResult.output`. |

**Invariants**
- A subagent replacement is *safe* iff its new implementation accepts payloads
  valid against `input_schema` and returns results valid against
  `output_schema` — no coordinator code or prompt change is permitted during
  the swap (SC-003). `test_swap_equivalence.py` asserts this by rerunning the
  happy-path scenario after substituting the default subagent with a stub.

## TaskSpawner (Protocol)

```python
class TaskSpawner(Protocol):
    def spawn(self, payload: SubtaskPayload) -> SubagentResult: ...
```

The only seam between `Coordinator` and `Subagent`. Defined in
`task_spawner.py`. The default implementation constructs a `Subagent` for the
matching `role_name` and calls `.run(payload)`. The P3 swap test provides a
`StubTaskSpawner` that returns canned `SubagentResult`s — the coordinator
accepts either without code change (FR-008).

## Exceptions

| Exception | Raised when | Terminal? |
|-----------|-------------|-----------|
| `SubagentResultValidationError` | Raw subagent output fails `SubagentResult.model_validate_json`, OR `task_id`/`role_name` mismatch, OR extra fields present. | Yes — halts coordinator consumption of that result (FR-003, FR-004, SC-002). |
| `SubtaskPayloadBuildError` | Coordinator attempts to construct a `SubtaskPayload` with extra fields or with a raw transcript where `inputs` is expected. | Yes — spawn is blocked before the SDK call (FR-001, spec US2-AS2). |
| `RoleNotRegistered` | Coordinator calls `spawn_subtask(role_name, ...)` for a `role_name` with no matching `HandoffContract`. | Yes. |

## Relationships

```
Coordinator
  ├── _history  (PRIVATE; leakage-banned)
  ├── _scratchpad  (PRIVATE; leakage-banned)
  ├── task_spawner : TaskSpawner
  │      └── .spawn(payload: SubtaskPayload) -> SubagentResult
  │             └── Subagent (fresh anthropic.messages.create session)
  └── handoff_contracts : dict[role_name, HandoffContract]
                                            ├── input_schema  -> validates SubtaskPayload.inputs
                                            └── output_schema -> validates SubagentResult.output
```

## What is deliberately NOT modeled

- Concurrent subagent fan-out — acceptance scenarios are stated sequentially;
  concurrency would obscure the leak-probe audit without pedagogical gain.
- Retry budgets on subagent failure — Edge Case #1 mandates terminal-error
  treatment, not retry (FR-004).
- Persistent multi-session coordinator state — one run is one kata exercise;
  replay is from the per-run JSONL audit files.
- Cross-kata shared model library — YAGNI until a second kata needs it
  (per Kata 1 D-006).
