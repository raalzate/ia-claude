# Phase 1 Data Model: Safe Exploration via Plan Mode

All entities are pydantic v2 models under `katas/007_plan_mode/models.py`.
Each model exports a JSON schema under `specs/007-plan-mode/contracts/`
with `$id = "https://ia-claude.local/schemas/kata-007/<name>.schema.json"`.
Required fields are truly required; optional lists are nullable, not
empty-string-defaulted (Constitution Principle II, NON-NEGOTIABLE).

## SessionMode (type alias)

```python
SessionMode = Literal["plan", "execute"]
```

- Closed enumeration — no `"other"` escape value because the state machine
  is total. Every transition is logged via `SessionModeTransition`.
- The active mode is the single source of truth for which tool registry is
  passed to `messages.create(tools=...)`.

## ReadOnlyTools vs WriteTools registry

Two frozen sets of pydantic-backed `ToolDefinition` records, constructed
once at module import:

| Registry | Members | Registered when |
|----------|---------|-----------------|
| `ReadOnlyTools` | `read_file`, `grep`, `glob` | `SessionMode == "plan"` AND every turn in `"execute"` (read tools are always safe) |
| `WriteTools` | `edit_file`, `write_file` | `SessionMode == "execute"` only, AND only after a verified `HumanApprovalEvent` matching the current plan |

The `modes.select_tools(mode, approval)` helper is the single authority
for which `tools=[...]` array is passed to the SDK. Any attempt to
register a `WriteTools` member while `mode == "plan"` raises
`WriteAttemptedInPlanMode` — this exception is the SC-001 test oracle and
is asserted across every member of `WriteTools`.

## PlanDocument

```python
class PlanDocument(BaseModel):
    task_id: str                         # stable id, used as filename stem
    summary: str                         # one-paragraph human summary
    affected_files: list[str]            # required, non-empty; sorted
    risks: list[str]                     # required, may be empty list
    migration_steps: list[str]           # required, ordered
    out_of_scope: list[str] | None = None
    open_questions: list[str] | None = None

    def to_markdown(self) -> str: ...
    def compute_hash(self) -> str:       # sha256(to_markdown())
        ...
```

- Serialized to `specs/fixtures/refactor-plans/<task_id>.md` in tests.
- `affected_files` is the authoritative scope list for the scope-change
  detector. Paths are repo-relative, sorted, deduplicated on construction.
- `to_markdown()` is deterministic (no clocks, no UUIDs, stable ordering)
  so that `compute_hash()` is reproducible across processes.

## HumanApprovalEvent

```python
class HumanApprovalEvent(BaseModel):
    task_id: str
    approved_by: str                     # actor identifier (email / id)
    approved_at: datetime                # aware UTC
    plan_hash: str                       # sha256 hex of plan markdown
    approval_note: str | None = None
```

- The transition `plan → execute` is authorized iff
  `event.plan_hash == PlanDocument.compute_hash()` re-read from disk at
  transition time.
- Mismatch → refuse transition, emit a labelled event
  (`reason="plan_hash_mismatch"`), stay in plan mode. This implements the
  spec's edge case "human edits the plan after approval".
- Revocation is represented as a follow-up event with the same schema and
  `approval_note = "revoked"`; the session halts on observing it mid-exec
  (edge case: approval revoked / interrupted).

## SessionModeTransition

```python
class SessionModeTransition(BaseModel):
    session_id: str
    from_mode: SessionMode
    to_mode: SessionMode
    at: datetime                         # aware UTC
    plan_task_id: str | None = None      # populated when crossing plan→execute or execute→plan
    plan_hash: str | None = None         # populated when crossing plan→execute
    approved_by: str | None = None       # populated when crossing plan→execute
    reason: str                          # e.g. "approval_verified", "scope_change_detected",
                                         # "plan_hash_mismatch", "approval_revoked", "small_refactor_bypass"
```

- Every transition is appended to `runs/<session-id>/events.jsonl`.
- Required fields (`session_id`, `from_mode`, `to_mode`, `at`, `reason`)
  are always populated. Nullable fields are populated per `reason` — the
  transition test suite asserts this matrix explicitly (SC-002
  traceability).

## ScopeChangeEvent

```python
class ScopeChangeEvent(BaseModel):
    session_id: str
    at: datetime
    attempted_target: str                # repo-relative path the agent tried to edit
    current_plan_task_id: str
    current_plan_hash: str
    affected_files_snapshot: list[str]   # frozen copy at halt time, for audit
    tool_name: Literal["edit_file", "write_file"]
```

- Emitted *before* the tool is dispatched. Its presence in
  `events.jsonl` is the SC-004 test oracle.
- After emission the session re-enters plan mode via a
  `SessionModeTransition(reason="scope_change_detected")`.

## WriteAttemptedInPlanMode (exception)

Not a pydantic model but a named exception carrying:

- `mode: SessionMode` (always `"plan"` at raise site),
- `attempted_tool: Literal["edit_file", "write_file"]`,
- `attempted_target: str | None`,
- `at: datetime`.

Caught by the session loop, which writes a JSONL record of the attempt
(FR-007) and re-raises to fail the test turn. The SC-001 test asserts
this exception is raised for every member of `WriteTools`.

## Relationships

```
RefactorRequest ──classify──▶ SessionMode ──select_tools──▶ ToolRegistry
                                   │
                                   ▼
                           PlanDocument (markdown on disk)
                                   │
                     human reviews/edits, then approves
                                   ▼
                         HumanApprovalEvent (plan_hash)
                                   │
                          verify_and_transition()
                                   ▼
                        SessionModeTransition(plan → execute)
                                   │
                                   ▼
                 per-turn: if tool_use targets path ∉ affected_files
                                   ▼
                           ScopeChangeEvent  ──▶  transition(execute → plan)
```
