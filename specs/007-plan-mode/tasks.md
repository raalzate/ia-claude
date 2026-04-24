# Tasks: Safe Exploration via Plan Mode

**Input**: Design documents from `/specs/007-plan-mode/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-005"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/007_plan_mode/__init__.py` (empty marker) and mirror test package `tests/katas/007_plan_mode/__init__.py`
- [ ] T002 [P] Ensure `pyproject.toml` at repo root declares the `[dev]` extra with `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, `jsonschema` — add only if missing; per plan.md Technical Context
- [ ] T003 [P] Add fixture-plan target directory `specs/fixtures/refactor-plans/.gitkeep` so tests and runner can write PlanDocument markdown (per plan.md Project Structure)
- [ ] T004 [P] Ensure `runs/` is gitignored (event logs + approvals JSONL are gitignored per plan.md Storage section)
- [ ] T005 [P] Create `tests/katas/007_plan_mode/conftest.py` stub that declares the `pytest-bdd` features directory `tests/katas/007_plan_mode/features/`, exposes a fixture-session loader helper, a `plan_hash` helper (sha256 of a file), and a `LIVE_API` skip marker (mirrors Kata 001 baseline)

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, JSON schema loader, injectable SDK client, scope-change detector scaffolding, JSONL event-log writer. No story label.

- [ ] T006 [P] Implement shared pydantic v2 entities in `katas/007_plan_mode/models.py`: `SessionMode` (Literal["plan","execute"]), `ToolDefinition`, `PlanDocument`, `HumanApprovalEvent`, `SessionModeTransition`, `ScopeChangeEvent`, `WriteAttemptedInPlanMode` exception — per `data-model.md`; required lists truly required; `extra="forbid"` on every model (Principle II)
- [ ] T007 [P] Implement contract-schema loader helper `tests/katas/007_plan_mode/conftest.py::load_contract_schema(name)` that resolves paths under `specs/007-plan-mode/contracts/` for `plan-document`, `human-approval-event`, `session-mode-transition`, `scope-change-event` — used by contract tests
- [ ] T008 [P] Implement the thin injectable Anthropic client wrapper in `katas/007_plan_mode/client.py` exposing a single `send(messages, tools) -> RawResponse` surface; real SDK behind `LiveClient`, fixture replay behind `RecordedClient` that reads `tests/katas/007_plan_mode/fixtures/<name>.json`; `LIVE_API` env var gates live mode
- [ ] T009 [P] Implement read/write tool registries in `katas/007_plan_mode/modes.py`: frozen sets `ReadOnlyTools = {read_file, grep, glob}` and `WriteTools = {edit_file, write_file}`; `select_tools(mode, approval) -> list[ToolDefinition]` is the single authority for the SDK `tools=[...]` kwarg (FR-002, FR-006) — raises `WriteAttemptedInPlanMode` if caller tries to register a WriteTools member while `mode == "plan"`
- [ ] T010 [P] Implement the PlanDocument markdown (de)serializer in `katas/007_plan_mode/plan.py`: `PlanDocument.to_markdown()` deterministic (no clocks, stable ordering, sorted+deduped `affected_files`) and `PlanDocument.compute_hash()` returns `sha256(to_markdown())` hex — per data-model.md
- [ ] T011 [P] Implement the JSONL event-log writer in `katas/007_plan_mode/events.py`: opens `runs/<session_id>/events.jsonl` append-only; `emit(record)` serializes one line with stable key order and UTC `at`; approvals go to `runs/<session_id>/approvals.jsonl`; rejects any record containing a prose-derived field (`extra="forbid"` enforcement, Principle I/II)
- [ ] T012 Wire `PlanModeSession` construction in `katas/007_plan_mode/session.py` so it owns the `EventLog`, the current `SessionMode`, the injected `client`, the loaded `PlanDocument | None`, and the latest verified `HumanApprovalEvent | None`; depends on T006, T008, T009, T011

**Checkpoint**: Foundation ready — typed models, JSON schemas wired, injectable client, mode-aware tool registry, plan (de)serializer + hash, and event-log writer are all in place. Story-specific flow can now be implemented against them.

---

## Phase 3: User Story 1 - Large Refactor Triggers a Read-Only Plan Document (Priority: P1) MVP

**Goal**: A multi-file refactor request starts in `SessionMode == "plan"`, the SDK is invoked with `tools=ReadOnlyTools` only, the agent compiles findings into a markdown `PlanDocument` at `specs/fixtures/refactor-plans/<task_id>.md`, and the session halts pending human approval.

**Independent Test**: Submit a multi-file refactor fixture. Verify: `tools=[...]` payload contains only `read_file`, `grep`, `glob`; a markdown plan document is written to `specs/fixtures/refactor-plans/<task_id>.md` with non-empty `affected_files`, `risks`, `migration_steps`; no SessionModeTransition to `execute` is emitted; halt reason is awaiting human approval.

### Tests for User Story 1

- [ ] T013 [P] [US1] Record fixture session `tests/katas/007_plan_mode/fixtures/normal_refactor.json` (multi-file refactor, recorded read/grep/glob tool_use turns, final assistant turn synthesizing the plan) — per plan.md fixture corpus
- [ ] T014 [P] [US1] Record fixture session `tests/katas/007_plan_mode/fixtures/small_refactor.json` (single-file low-risk change; classifier takes bypass path with `reason="small_refactor_bypass"`)
- [ ] T015 [P] [US1] Record fixture session `tests/katas/007_plan_mode/fixtures/infeasible_plan.json` (plan-mode analysis concludes refactor is infeasible; no transition to execute; reason recorded in plan content)
- [ ] T016 [P] [US1] Copy/symlink `specs/007-plan-mode/tests/features/read_only_plan_document.feature` to `tests/katas/007_plan_mode/features/read_only_plan_document.feature` so pytest-bdd can discover it
- [ ] T017 [US1] Implement BDD step definitions citing [TS-001] in `tests/katas/007_plan_mode/step_defs/test_read_only_plan_document_steps.py` — assert `tools=[...]` passed to `messages.create` contains exactly `read_file`, `grep`, `glob` and zero WriteTools members (@TS-001, FR-006, @P1)
- [ ] T018 [US1] Implement BDD step definitions citing [TS-002] in `tests/katas/007_plan_mode/step_defs/test_read_only_plan_document_steps.py` — assert markdown plan file is written to `specs/fixtures/refactor-plans/<task_id>.md` with non-empty `affected_files`, `risks`, and ordered `migration_steps` sections (@TS-002, FR-003, SC-003)
- [ ] T019 [US1] Implement BDD step definitions citing [TS-003] in `tests/katas/007_plan_mode/step_defs/test_read_only_plan_document_steps.py` — assert the session halts in `"plan"` mode, no SessionModeTransition to `"execute"` is emitted, and the halt reason recorded is awaiting human approval (@TS-003, FR-001)
- [ ] T020 [US1] Implement BDD step definitions citing [TS-004] in `tests/katas/007_plan_mode/step_defs/test_read_only_plan_document_steps.py` — Scenario Outline driving `normal_refactor`, `scope_creep_injection`, `plan_edit_after_approval`, `infeasible_plan` fixtures; assert produced Plan Document lists every expected affected file at 100% completeness (@TS-004, FR-003, SC-003)
- [ ] T021 [US1] Implement BDD step definitions citing [TS-005] in `tests/katas/007_plan_mode/step_defs/test_read_only_plan_document_steps.py` — assert on `infeasible_plan` fixture: plan records infeasibility in content, session remains in `"plan"` mode, no HumanApprovalEvent is requested (@TS-005, FR-006)
- [ ] T022 [US1] Implement BDD step definitions citing [TS-006] in `tests/katas/007_plan_mode/step_defs/test_read_only_plan_document_steps.py` — assert on `small_refactor` fixture: a SessionModeTransition with `reason="small_refactor_bypass"` is recorded and no multi-file Plan Document is required (@TS-006, FR-006)
- [ ] T023 [P] [US1] Add unit test `tests/katas/007_plan_mode/unit/test_plan_document_serialization.py` asserting `PlanDocument.to_markdown()` is deterministic (stable ordering, no clocks), sorted+deduped `affected_files`, and `compute_hash()` is reproducible across processes on the same input
- [ ] T024 [P] [US1] Add lint test `tests/katas/007_plan_mode/lint/test_write_tools_absent_in_plan_mode.py` — asserts `tools=[...]` kwarg passed to `messages.create` contains zero WriteTools members whenever `SessionMode == "plan"` across every fixture (structural SC-001 defense, plan.md Constraints section)

### Implementation for User Story 1

- [ ] T025 [US1] Implement the request classifier in `katas/007_plan_mode/session.py::classify_request(refactor_request) -> SessionMode + reason` — multi-file refactors enter `"plan"`; single-file low-risk tasks emit `SessionModeTransition(reason="small_refactor_bypass")` and skip the full Plan Document (FR-006, edge case small task). Bypass requires ALL three of: (1) exactly one file touched, (2) no new cross-package imports introduced, (3) no governance paths edited (`CONSTITUTION.md`, `CLAUDE.md`, `.tessl/**`, `.claude/**`) — per spec.md §Clarifications (F-001).
- [ ] T026 [US1] Implement the plan-mode agent loop in `katas/007_plan_mode/session.py::run_plan_mode(session, refactor_request)` — calls `client.send(messages, tools=ReadOnlyTools)` each turn, dispatches only `read_file`/`grep`/`glob` tool_use results back, accumulates findings, and terminates when the model signals it has enough context (FR-006)
- [ ] T027 [US1] Implement PlanDocument synthesis in `katas/007_plan_mode/plan.py::synthesize_plan(session, findings) -> PlanDocument` — populates `affected_files`, `risks`, `migration_steps`, optional `out_of_scope`/`open_questions`; writes markdown to `specs/fixtures/refactor-plans/<task_id>.md` (FR-003)
- [ ] T028 [US1] Implement the plan-mode halt in `katas/007_plan_mode/session.py` — after `synthesize_plan`, record halt reason "awaiting human approval", emit NO SessionModeTransition to `"execute"`, remain in `"plan"` mode (FR-001, US1 TS-003)
- [ ] T029 [US1] Implement the infeasible-plan path in `katas/007_plan_mode/plan.py` / `session.py` — when analysis concludes the refactor is infeasible, record the infeasibility inside the PlanDocument content and emit a SessionModeTransition with an appropriate `reason` that does NOT cross into `"execute"` (FR-001, FR-005, edge case)
- [ ] T030 [US1] Implement the CLI entrypoint `katas/007_plan_mode/runner.py` with `python -m katas.007_plan_mode.runner --request "..."` as documented in `quickstart.md`; reads `LIVE_API` env var; prints `runs/<session-id>/events.jsonl` path on halt

**Checkpoint**: US1 fully functional — practitioner can run the kata against `normal_refactor.json`; PlanDocument is written to `specs/fixtures/refactor-plans/<task_id>.md`; read/grep/glob are the only tools registered during plan mode; lint asserts zero WriteTools in plan-mode payloads; BDD scenarios @TS-001, @TS-002, @TS-003, @TS-004, @TS-005, @TS-006 all pass.

---

## Phase 4: User Story 2 - Direct Writes During Plan Mode Are Blocked (Priority: P2)

**Goal**: Any write/edit/delete capability invoked during plan mode raises `WriteAttemptedInPlanMode`, leaves disk unchanged, and is logged with mode, target, and UTC timestamp. Write tools are structurally absent from the SDK `tools=[...]` payload. Across the full corpus, zero files are modified during plan mode.

**Independent Test**: Force the agent into plan mode, attempt `edit_file` and `write_file` against a scratch target path; assert `WriteAttemptedInPlanMode` is raised with `mode="plan"` and `attempted_tool=<tool>`; assert the target is unchanged on disk; assert an entry is appended to `runs/<session-id>/events.jsonl` with tool name, target, mode, and UTC timestamp.

### Tests for User Story 2

- [ ] T031 [P] [US2] Record fixture session `tests/katas/007_plan_mode/fixtures/write_attempt_in_plan_mode.json` — simulates an over-eager tool_use for `edit_file`/`write_file` while the session mode asserted alongside is `"plan"` (P2, SC-001)
- [ ] T032 [P] [US2] Copy/symlink `specs/007-plan-mode/tests/features/write_gate_enforcement.feature` to `tests/katas/007_plan_mode/features/write_gate_enforcement.feature`
- [ ] T033 [US2] Implement BDD step definitions citing [TS-007] in `tests/katas/007_plan_mode/step_defs/test_write_gate_enforcement_steps.py` — Scenario Outline: for each of `edit_file` and `write_file`, attempt the call in plan mode, assert `WriteAttemptedInPlanMode` is raised, target file on disk is unchanged, and the exception carries `mode="plan"` and `attempted_tool=<write_tool>` (@TS-007, FR-002, SC-001)
- [ ] T034 [US2] Implement BDD step definitions citing [TS-008] in `tests/katas/007_plan_mode/step_defs/test_write_gate_enforcement_steps.py` — structurally inspect the tools payload built for `messages.create`, assert zero WriteTools members and that the mode asserted alongside is `"plan"` (@TS-008, FR-002, SC-001)
- [ ] T035 [US2] Implement BDD step definitions citing [TS-009] in `tests/katas/007_plan_mode/step_defs/test_write_gate_enforcement_steps.py` — after a raised `WriteAttemptedInPlanMode`, assert a JSONL entry is appended to `runs/<session-id>/events.jsonl` with attempted tool, attempted target, current mode `"plan"`, and a UTC timestamp (@TS-009, FR-007)
- [ ] T036 [US2] Implement BDD step definitions citing [TS-010] in `tests/katas/007_plan_mode/step_defs/test_write_gate_enforcement_steps.py` — run every fixture in the Plan Mode corpus, inspect filesystem diff per run, assert the count of files modified during `"plan"` mode across all runs equals 0 (@TS-010, FR-002, SC-001)
- [ ] T037 [P] [US2] Add unit test `tests/katas/007_plan_mode/unit/test_mode_gate.py` covering `select_tools(mode, approval)` across every combination — `plan` returns only ReadOnlyTools, `execute` + verified approval returns ReadOnlyTools ∪ WriteTools, `execute` without approval falls back or raises — per data-model.md ReadOnlyTools/WriteTools table

### Implementation for User Story 2

- [ ] T038 [US2] In `katas/007_plan_mode/modes.py`, implement the `WriteAttemptedInPlanMode` raise site for both `edit_file` and `write_file` entry points — exception carries `mode="plan"`, `attempted_tool`, `attempted_target`, `at` (UTC); never touches disk (FR-002, SC-001, data-model.md)
- [ ] T039 [US2] In `katas/007_plan_mode/session.py`, catch `WriteAttemptedInPlanMode` at the session loop boundary; write a JSONL record of the attempt to `runs/<session-id>/events.jsonl` with mode, tool, target, UTC timestamp, then re-raise to fail the offending turn (FR-007)
- [ ] T040 [US2] In `katas/007_plan_mode/modes.py::select_tools`, make WriteTools structurally absent from the payload when `mode == "plan"` — this is the primary (non-advisory) defense: the model cannot emit a valid `tool_use` for a tool that was never registered (FR-002, FR-006, SC-001)

**Checkpoint**: US2 fully functional — every write attempt in plan mode raises `WriteAttemptedInPlanMode` with typed payload; disk is never touched; every blocked attempt is logged with mode/target/timestamp; lint + BDD confirm zero WriteTools in plan-mode SDK payloads across the whole corpus. BDD scenarios @TS-007, @TS-008, @TS-009, @TS-010 all pass.

---

## Phase 5: User Story 3 - Approved Plan Unlocks Direct Execution (Priority: P3)

**Goal**: A verified `HumanApprovalEvent` whose `plan_hash` matches the on-disk PlanDocument transitions the session from `"plan"` to `"execute"`, registers WriteTools, and lets the agent apply only changes covered by `plan.affected_files`. Hash mismatches refuse the transition; scope changes emit `ScopeChangeEvent` before dispatch and re-enter plan mode; revocation halts the session.

**Independent Test**: Produce a PlanDocument, emit a `HumanApprovalEvent` with matching `plan_hash`, verify the session transitions to `"execute"` and logs a SessionModeTransition carrying `plan_task_id`, `plan_hash`, and `approved_by`. Then: edit the markdown post-approval and assert transition is refused with `reason="plan_hash_mismatch"`; inject a scope-creep write and assert `ScopeChangeEvent` emits before dispatch and the session re-enters `"plan"`; observe an approval-revoked event and assert execution halts.

### Tests for User Story 3

- [ ] T041 [P] [US3] Record fixture session `tests/katas/007_plan_mode/fixtures/scope_creep_injection.json` — after approved execute, agent proposes editing a file absent from `plan.affected_files` (SC-004)
- [ ] T042 [P] [US3] Record fixture session `tests/katas/007_plan_mode/fixtures/plan_edit_after_approval.json` — plan markdown modified after `HumanApprovalEvent`; `plan_hash` no longer matches current on-disk hash (edge case plan edited post-approval)
- [ ] T043 [P] [US3] Record fixture session `tests/katas/007_plan_mode/fixtures/approval_revoked.json` — follow-up `HumanApprovalEvent` with `approval_note="revoked"` mid-execute (edge case)
- [ ] T044 [P] [US3] Record fixture session `tests/katas/007_plan_mode/fixtures/interrupted_execution.json` — execute session interrupted mid-way; `SessionModeTransition(reason="execution_interrupted")` recorded (edge case)
- [ ] T045 [P] [US3] Copy/symlink `specs/007-plan-mode/tests/features/approved_plan_unlocks_execution.feature` to `tests/katas/007_plan_mode/features/approved_plan_unlocks_execution.feature`
- [ ] T046 [US3] Implement BDD step definitions citing [TS-011] in `tests/katas/007_plan_mode/step_defs/test_approved_plan_unlocks_execution_steps.py` — assert matching `plan_hash` authorizes transition; a SessionModeTransition is appended carrying `approved_by` and `plan_hash` (@TS-011, FR-001, FR-005, SC-002)
- [ ] T047 [US3] Implement BDD step definitions citing [TS-012] in `tests/katas/007_plan_mode/step_defs/test_approved_plan_unlocks_execution_steps.py` — assert on post-approval edit: transition is refused, session remains in `"plan"` mode, an event is emitted with `reason="plan_hash_mismatch"` (@TS-012, FR-001)
- [ ] T048 [US3] Implement BDD step definitions citing [TS-013] in `tests/katas/007_plan_mode/step_defs/test_approved_plan_unlocks_execution_steps.py` — assert `ScopeChangeEvent` emits BEFORE the write is dispatched, the proposed file is not written, and the session re-enters `"plan"` via a SessionModeTransition with `reason="scope_change_detected"` (@TS-013, FR-004, SC-004)
- [ ] T049 [US3] Implement BDD step definitions citing [TS-014] in `tests/katas/007_plan_mode/step_defs/test_approved_plan_unlocks_execution_steps.py` — Scenario Outline on `scope_creep_injection` fixture; assert every attempted edit outside `plan.affected_files` produces a `ScopeChangeEvent` and scope-change halt rate equals 100% (@TS-014, FR-004, SC-004)
- [ ] T050 [US3] Implement BDD step definitions citing [TS-015] in `tests/katas/007_plan_mode/step_defs/test_approved_plan_unlocks_execution_steps.py` — iterate the event log for every `SessionModeTransition` with `to_mode="execute"`; assert each carries a non-null `plan_task_id`, `plan_hash`, and `approved_by`, with traceability ratio equal to 100% (@TS-015, FR-005, SC-002)
- [ ] T051 [US3] Implement BDD step definitions citing [TS-016] in `tests/katas/007_plan_mode/step_defs/test_approved_plan_unlocks_execution_steps.py` — on follow-up `HumanApprovalEvent` with `approval_note="revoked"`, assert the session halts and does not continue applying changes without a new approval (@TS-016, FR-004)
- [ ] T052 [P] [US3] Add unit test `tests/katas/007_plan_mode/unit/test_plan_hash_integrity.py` — construct a PlanDocument, compute its hash, mutate the on-disk markdown, re-read, assert the mismatched hash is detected (edge case plan edited after approval)
- [ ] T053 [P] [US3] Add unit test `tests/katas/007_plan_mode/unit/test_scope_change_detector.py` — given `plan.affected_files` and a proposed edit target, assert a path in the set is dispatched and a path outside the set halts with `ScopeChangeEvent` emitted BEFORE dispatch (FR-004, SC-004)

### Implementation for User Story 3

- [ ] T054 [US3] Implement `katas/007_plan_mode/approval.py::verify_and_transition(session, event) -> SessionModeTransition` — re-reads the PlanDocument from disk, recomputes its hash, compares to `event.plan_hash`; on match transitions to `"execute"` and emits a SessionModeTransition carrying `plan_task_id`, `plan_hash`, `approved_by`, `reason="approval_verified"`; on mismatch emits `reason="plan_hash_mismatch"` and stays in `"plan"` (FR-001, FR-005, SC-002)
- [ ] T055 [US3] Implement `katas/007_plan_mode/scope.py::check_scope(plan, attempted_target) -> ScopeChangeEvent | None` — returns a `ScopeChangeEvent` if `attempted_target not in plan.affected_files`, otherwise None; this MUST run pre-dispatch inside `run_execute_mode` (FR-004, SC-004)
- [ ] T056 [US3] Implement the execute-mode agent loop in `katas/007_plan_mode/session.py::run_execute_mode(session, plan, approval)` — registers WriteTools via `select_tools("execute", approval)`, per turn: extract `tool_use` target, call `check_scope`, if event returned → emit `ScopeChangeEvent`, emit `SessionModeTransition(reason="scope_change_detected")`, re-enter plan mode; else dispatch tool; handle approval revocation by halting (FR-001, FR-004, FR-005)
- [ ] T057 [US3] Implement the revocation observer in `katas/007_plan_mode/approval.py` — when a follow-up `HumanApprovalEvent` with `approval_note="revoked"` is written to `runs/<session-id>/approvals.jsonl`, the session halts execution and emits a SessionModeTransition with an appropriate halt reason (FR-004, edge case approval revoked)
- [ ] T058 [US3] Extend `katas/007_plan_mode/runner.py` with the `approve` subcommand documented in `quickstart.md` — `python -m katas.007_plan_mode.runner approve --task-id <task_id> --approved-by <actor>` reads `specs/fixtures/refactor-plans/<task_id>.md`, computes sha256, constructs `HumanApprovalEvent`, appends it to `runs/<session-id>/approvals.jsonl`, and signals the waiting runner (FR-001, FR-005)

**Checkpoint**: US3 fully functional — approved plans unlock execute mode and register WriteTools; post-approval edits refuse the transition with labeled event; scope-creep attempts emit `ScopeChangeEvent` before dispatch and re-enter plan mode; approval revocation halts cleanly; every plan→execute transition carries `plan_task_id`, `plan_hash`, `approved_by` (100% traceability). BDD scenarios @TS-011, @TS-012, @TS-013, @TS-014, @TS-015, @TS-016 all pass.

---

## Phase 6: Contract Conformance

**Goal**: Every persisted artifact (PlanDocument, HumanApprovalEvent, SessionModeTransition, ScopeChangeEvent) validates against its declared JSON schema under `specs/007-plan-mode/contracts/`. Structural guarantee required by Constitution Principle II.

- [ ] T059 [P] Copy/symlink `specs/007-plan-mode/tests/features/schema_contracts.feature` to `tests/katas/007_plan_mode/features/schema_contracts.feature`
- [ ] T060 Implement BDD step definitions citing [TS-017] in `tests/katas/007_plan_mode/step_defs/test_schema_contracts_steps.py` — validate a produced PlanDocument's structured representation against `contracts/plan-document.schema.json`; assert required fields `task_id`, `summary`, `affected_files`, `risks`, `migration_steps` are present (@TS-017, FR-003, SC-003)
- [ ] T061 Implement BDD step definitions citing [TS-018] in `tests/katas/007_plan_mode/step_defs/test_schema_contracts_steps.py` — validate an emitted HumanApprovalEvent against `contracts/human-approval-event.schema.json`; assert `plan_hash` is a sha256 hex string (@TS-018, FR-001, FR-005, SC-002)
- [ ] T062 Implement BDD step definitions citing [TS-019] in `tests/katas/007_plan_mode/step_defs/test_schema_contracts_steps.py` — validate a SessionModeTransition record against `contracts/session-mode-transition.schema.json`; assert required fields `session_id`, `from_mode`, `to_mode`, `at`, `reason` are present (@TS-019, FR-005, SC-002)
- [ ] T063 Implement BDD step definitions citing [TS-020] in `tests/katas/007_plan_mode/step_defs/test_schema_contracts_steps.py` — validate a ScopeChangeEvent record against `contracts/scope-change-event.schema.json`; assert required fields `attempted_target`, `current_plan_hash`, `affected_files_snapshot` are present (@TS-020, FR-004, FR-007, SC-004)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T064 [P] Write `katas/007_plan_mode/README.md` (Principle VIII deliverable) covering: kata objective in own words; the plan-mode read-only boundary (ReadOnlyTools vs WriteTools, `select_tools` gate, `ExitPlanMode` / HumanApprovalEvent gate); the anti-pattern defense (jumping straight to edits on an unfamiliar codebase) explained via `write_attempt_in_plan_mode`, `plan_edit_after_approval`, `scope_creep_injection` fixtures; run instructions mirroring `quickstart.md`; reflection section answering the prompts recorded in `quickstart.md` section 7 — names the observed failure mode the kata prevents (advisory plan mode without structural write-gate; scope creep past approved file list); dedicated §Scope Semantics subsection covering FR-004 rename/move rules (destination path must appear in `plan.affected_files`; source deletion is an additional affected-file entry; directory-prefix entries apply to every file under the prefix at approval time) and the classifier bypass contract (single file + no new cross-package imports + no governance-path edits) per spec.md §Clarifications.
- [ ] T065 [P] Document the plan-mode contract in `katas/007_plan_mode/README.md` — explicitly list the read-only tool set (`read_file`, `grep`, `glob`), the structural absence of write tools from SDK `tools=[...]` during plan mode, and the `HumanApprovalEvent` with matching `plan_hash` as the sole gate into execute mode (FR-001, FR-002, FR-006; Principle VI)
- [ ] T066 [P] Add module-level docstrings to each of `katas/007_plan_mode/session.py`, `modes.py`, `plan.py`, `approval.py`, `scope.py`, `events.py`, `client.py`, `models.py`, `runner.py` explaining the module's role in plan→approval→execute gating
- [ ] T067 [P] Add why-comments (per Constitution Principle VIII) on every non-trivial function across `katas/007_plan_mode/*.py` — each comment ties the code choice back to the kata objective (plan-mode gating) or the anti-pattern (jumping straight to edits on an unfamiliar codebase); never describes *what* the code does
- [ ] T068 [P] Verify `specs/007-plan-mode/quickstart.md` usage walkthrough is accurate against the final file layout; update paths or commands only if drift was introduced during implementation
- [ ] T069 Run `quickstart.md` end-to-end: `pytest tests/katas/007_plan_mode -q` against all 8 fixtures, then optional `LIVE_API=1 pytest tests/katas/007_plan_mode -q -k live` smoke; record both outputs as PR evidence; expected under 10 seconds for the default fixture suite
- [ ] T070 [P] Run `ruff check katas/007_plan_mode tests/katas/007_plan_mode` and `black --check` over the same paths; fix any findings
- [ ] T071 [P] Produce a coverage report (`pytest --cov=katas.007_plan_mode`) and archive it at `runs/coverage/007_plan_mode.txt`; target >= 90% line coverage on `session.py`, `modes.py`, `approval.py`, `scope.py`
- [ ] T072 Final self-audit: read the emitted `events.jsonl` from the `normal_refactor` run and a `scope_creep_injection` run, confirm they satisfy SC-001 (0 writes in plan), SC-002 (100% plan→execute traceability), SC-003 (100% affected-files completeness), SC-004 (100% scope-change halt rate); record the check in the PR description

---

## Dependencies & Execution Order

**Phase order (strict):** Phase 1 -> Phase 2 -> Phase 3 (US1) -> Phase 4 (US2) -> Phase 5 (US3) -> Phase 6 (contracts) -> Phase 7 (polish).

**Within-phase dependencies:**
- Phase 2: T006-T011 are all [P] because they live in different files; T012 depends on T006, T008, T009, T011.
- Phase 3: T013-T016 (fixtures + feature copy) can run in parallel. T017-T022 share `test_read_only_plan_document_steps.py` and must be sequenced in that file; each depends on T016 and the relevant fixtures. T023 and T024 are [P] once T006/T009/T010 exist. T025-T030 are sequential in `session.py`/`plan.py`/`runner.py`.
- Phase 4: T031, T032 are [P]. T033-T036 share `test_write_gate_enforcement_steps.py`. T037 is [P]. T038 depends on T009. T039 depends on T011 + T038. T040 depends on T009.
- Phase 5: T041-T045 are [P]. T046-T051 share `test_approved_plan_unlocks_execution_steps.py`. T052, T053 are [P]. T054 depends on T010 + T011. T055 depends on T006. T056 depends on T054, T055, T009. T057 depends on T054. T058 depends on T030 + T054.
- Phase 6: T059 is [P]. T060-T063 share `test_schema_contracts_steps.py` and depend on T059 + produced artifacts from Phases 3-5.
- Phase 7: T064-T068, T070, T071 are [P]. T069 depends on all prior phases complete. T072 depends on T069.

**Story dependencies:**
- US2 extends the mode gate built in US1 (Plan-mode tool registry, session loop) — cannot start until T025-T028 land.
- US3 consumes the PlanDocument and event log emitted by US1/US2 — cannot validate approval/hash/scope flow until both prior stories have produced artifacts.
- Phase 6 (contracts) validates artifacts produced by US1-US3 and therefore gates on them.

---

## Parallel Opportunities

**Phase 1 [P]:** T002, T003, T004, T005 (different files).

**Phase 2 [P]:** T006, T007, T008, T009, T010, T011 (distinct modules).

**Phase 3 [P]:** fixture recording batch — T013, T014, T015, T016 all in parallel; T023, T024 in parallel once foundational modules exist.

**Phase 4 [P]:** T031, T032 fixture/feature batch in parallel; T037 in parallel.

**Phase 5 [P]:** T041, T042, T043, T044, T045 in parallel; T052, T053 in parallel.

**Phase 6 [P]:** T059 in parallel with Phase 5 polish; T060-T063 are sequential within the shared step-def file.

**Phase 7 [P]:** T064, T065, T066, T067, T068, T070, T071 all in parallel.

---

## Implementation Strategy

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1). At this point the kata demonstrates the plan-mode read-only boundary end-to-end: multi-file refactor request produces a PlanDocument at `specs/fixtures/refactor-plans/<task_id>.md`, only ReadOnlyTools are ever registered, lint structurally asserts zero WriteTools in plan-mode payloads, and the session halts pending approval. Already a credible kata deliverable against Principle VI.
- **Incremental delivery**: land Phase 4 (US2) next — adds the anti-pattern defense (write attempts raise `WriteAttemptedInPlanMode`, disk is never touched, every attempt is logged). Then Phase 5 (US3) closes the loop: approved plans unlock execute, hash mismatches refuse transition, scope creep halts pre-dispatch, revocation halts cleanly. Phase 6 adds schema-contract validation. Phase 7 documents and polishes.
- **Blast radius**: every phase is gated by BDD scenarios failing first (TDD per Constitution V); Phase 7's `quickstart.md` run is the final acceptance gate.

---

## Notes

- `[P]` = different files, no shared state, no ordering dependency.
- Each user story is independently testable — US1 against `normal_refactor.json` + `small_refactor.json` + `infeasible_plan.json`, US2 against `write_attempt_in_plan_mode.json`, US3 against `scope_creep_injection.json` + `plan_edit_after_approval.json` + `approval_revoked.json` + `interrupted_execution.json`.
- Verify every `.feature` scenario fails before writing the matching production code (Constitution V — TDD). Do NOT make tests pass by editing assertions; fix the production code instead (assertion-integrity rule).
- Lint test `tests/katas/007_plan_mode/lint/test_write_tools_absent_in_plan_mode.py` is the irreversible structural guardrail against regression (SC-001) — keep it green at all times after T024.
- Transition logic is keyed off typed `HumanApprovalEvent.plan_hash` equality and `path in plan.affected_files` membership — absolutely no prose-matching over model text anywhere in the code or tests (Principle I, plan.md Constraints).
