# Tasks: Agentic Loop & Deterministic Control

**Input**: Design documents from `/specs/001-agentic-loop/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-005"

---

## Phase 1: Setup

- [x] T001 Create kata package skeleton `katas/kata_001_agentic_loop/__init__.py` (empty marker) and mirror test package `tests/katas/kata_001_agentic_loop/__init__.py`
- [x] T002 [P] Add `pyproject.toml` at repo root declaring Python 3.11+ and the `[dev]` extra with `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd` per plan.md Technical Context
- [x] T003 [P] Configure lint/format tooling (`ruff` + `black`) in `pyproject.toml` with a rule set matching repo conventions; exclude `runs/` and `tests/fixtures/`
- [x] T004 [P] Add `runs/` to `.gitignore` (per plan.md: event logs are gitignored)
- [x] T005 [P] Create `tests/katas/kata_001_agentic_loop/conftest.py` stub that declares the `pytest-bdd` features directory `tests/katas/kata_001_agentic_loop/features/` and exposes a fixture-session loader helper

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, JSON schemas, injectable SDK client, EventLog writer. No story label.

- [x] T006 [P] Implement shared pydantic v2 entities in `katas/kata_001_agentic_loop/models.py`: `StopSignal` (Literal), `UnhandledStopSignal`, `ToolDefinition`, `ToolCall`, `ToolResult`, `Turn`, `EventRecord`, `TerminationReason` (Literal), `AgentSession` — per `data-model.md`
- [x] T007 [P] Copy Phase-1 JSON schemas into the implementation validation path by referencing them from tests — no code change needed, but add a helper `tests/katas/kata_001_agentic_loop/conftest.py::load_contract_schema(name)` that resolves paths under `specs/001-agentic-loop/contracts/`
- [x] T008 [P] Implement the thin injectable Anthropic client wrapper in `katas/kata_001_agentic_loop/client.py` exposing a single `send(messages, tools) -> RawResponse` surface; real SDK behind a `LiveClient`, fixture replay behind a `RecordedClient` that reads `tests/katas/kata_001_agentic_loop/fixtures/<name>.json`
- [x] T009 [P] Implement the tool registry in `katas/kata_001_agentic_loop/tools.py`: `ToolDefinition` registration, duplicate-name rejection (`ValueError`), and a `dispatch(tool_call) -> ToolResult` interface that catches tool exceptions and returns a structured `ToolResult(status="error", ...)` per FR-007
- [x] T010 [P] Implement the EventLog writer in `katas/kata_001_agentic_loop/events.py`: opens `runs/<session_id>/events.jsonl` append-only; `emit(record: EventRecord)` serializes one JSONL line; `close()` fsyncs — enforces `EventRecord` schema (no prose fields allowed)
- [x] T011 Wire `AgentSession` construction in `katas/kata_001_agentic_loop/models.py` (or a new `session.py` imported by `loop.py`) so it owns the `EventLog`, the `ToolRegistry`, and the conversation `history: list[dict]` in memory

**Checkpoint**: Foundation ready — models, contract schemas, injectable client, tool registry, and event-log writer are all in place. Loop logic can now be implemented against them.

---

## Phase 3: User Story 1 - Signal-Driven Loop Termination (Priority: P1) MVP

**Goal**: A practitioner running Kata 1 against a tool-enabled agent session observes the loop terminate the moment the response carries the terminal stop signal (`stop_reason=end_turn`), and only then — with zero participation from substring/regex/keyword search over response prose.

**Independent Test**: Run the kata harness against `happy_path.json` and assert via the event log that termination fired exactly once and its cause is `stop_reason=end_turn`, plus edge fixtures (`max_tokens.json`, `unknown_signal.json`, `absent_signal.json`) each produce a labeled halt within one iteration.

### Tests for User Story 1

- [x] T012 [P] [US1] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/happy_path.json` (one `tool_use` turn then one `end_turn` turn)
- [x] T013 [P] [US1] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/max_tokens.json` (single turn with `stop_reason=max_tokens`)
- [x] T014 [P] [US1] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/unknown_signal.json` (single turn with a made-up signal value)
- [x] T015 [P] [US1] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/absent_signal.json` (single turn with `stop_reason` field absent)
- [x] T016 [P] [US1] Copy/symlink `specs/001-agentic-loop/tests/features/signal_driven_termination.feature` to `tests/katas/kata_001_agentic_loop/features/signal_driven_termination.feature` so pytest-bdd can discover it
- [x] T017 [US1] Implement BDD step definitions for [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006] in `tests/katas/kata_001_agentic_loop/step_defs/test_signal_driven_termination_steps.py` — steps wire to the recorded-client fixtures and assert on event-log records
- [x] T018 [P] [US1] Add unit test `tests/katas/kata_001_agentic_loop/unit/test_loop_branches.py` covering every branch of the loop's `stop_signal` switch (`end_turn`, `tool_use`, `max_tokens`, `stop_sequence`, unhandled, absent) with synthetic `Turn` inputs
- [x] T019 [P] [US1] Add AST lint test `tests/katas/kata_001_agentic_loop/lint/test_no_prose_matching.py` — parses `katas/kata_001_agentic_loop/loop.py` and fails if it imports `re`, calls `.find(`/`.index(`/`.search(`/`.match(` on text, or uses the `in` operator against a string literal against response text (plan.md constraint + FR-004)

### Implementation for User Story 1

- [x] T020 [US1] Implement the agentic loop in `katas/kata_001_agentic_loop/loop.py`: single `run(session, initial_user_message)` function that calls `client.send(...)`, constructs a `Turn` from the response, switches on `Turn.stop_signal`, and halts on `end_turn` / `max_tokens` / `stop_sequence` / unhandled / absent with the matching `TerminationReason` — MUST NOT read `Turn.assistant_text_blocks` for branching (FR-001, FR-003, FR-006)
- [x] T021 [US1] In `loop.py`, implement the `tool_use` branch: iterate extracted `ToolCall`s, call `tool_registry.dispatch(call)`, append each `ToolResult` to `session.history`, then start a new iteration — no termination decision made on this branch (FR-002)
- [x] T022 [US1] In `loop.py`, emit one `EventRecord` per iteration via `session.event_log.emit(...)` recording `iteration`, `stop_signal`, `branch_taken`, `tool_name`, `tool_outcome`, and — on the terminal iteration — `termination_cause` (FR-005)
- [x] T023 [US1] Implement the CLI entrypoint `katas/kata_001_agentic_loop/runner.py` with `python -m katas.kata_001_agentic_loop.runner --model ... --prompt ...`; reads `LIVE_API` env var to choose `LiveClient` vs `RecordedClient`; prints `runs/<session-id>/events.jsonl` path on exit

**Checkpoint**: US1 fully functional — practitioner can run the kata against `happy_path.json`, every edge fixture halts with a labeled termination reason, AST lint blocks any reintroduction of prose matching, and BDD scenarios [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006] all pass.

---

## Phase 4: User Story 2 - Anti-Pattern Defense Against Prose Completion Phrases (Priority: P2)

**Goal**: A practitioner injecting prose completion phrases (e.g. "task complete", "we are done") into intermediate turns whose structured stop signal is still non-terminal observes that the loop does NOT exit early — terminating only on the subsequent genuine `end_turn` signal. Tool invocation failures are captured as structured results, and malformed `tool_use` payloads halt with a labeled reason.

**Independent Test**: Run the kata against `decoy_phrase.json` and `malformed_tool_use.json` and assert: zero early exits attributable to text, exactly one `end_turn` termination in the decoy run, and one `malformed_tool_use` termination in the malformed run.

### Tests for User Story 2

- [x] T024 [P] [US2] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/decoy_phrase.json` — intermediate turn text contains "task complete" / "we are done" / "finished" / "all done" while structured `stop_reason=tool_use`; final turn is genuine `end_turn`
- [x] T025 [P] [US2] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/malformed_tool_use.json` — `stop_reason=tool_use` but the `tool_use` block is missing required fields or names an unknown tool
- [x] T026 [P] [US2] Record fixture session `tests/katas/kata_001_agentic_loop/fixtures/tool_error.json` — `stop_reason=tool_use` where dispatch raises, to exercise FR-007 happy recovery
- [x] T027 [P] [US2] Copy/symlink `specs/001-agentic-loop/tests/features/antipattern_prose_defense.feature` to `tests/katas/kata_001_agentic_loop/features/antipattern_prose_defense.feature`
- [x] T028 [US2] Implement BDD step definitions for [TS-010, TS-011, TS-012, TS-013, TS-014] in `tests/katas/kata_001_agentic_loop/step_defs/test_antipattern_prose_defense_steps.py` — steps assert event-log termination-cause fields and that no record carries any text-derived column

### Implementation for User Story 2

- [x] T029 [US2] In `katas/kata_001_agentic_loop/loop.py`, implement the malformed-tool-use halt: when `ToolCall` validation fails (unknown tool OR input-schema failure), raise a `MalformedToolUse` exception inside the loop and emit a terminal `EventRecord` with `termination_cause="malformed_tool_use"` (FR-008)
- [x] T030 [US2] In `katas/kata_001_agentic_loop/tools.py`, strengthen `dispatch(tool_call)` so that a raised tool exception is caught and wrapped in `ToolResult(status="error", error_category=..., output=...)` and appended to history — and so that `dispatch` NEVER reads response text to decide anything (FR-007)
- [x] T031 [US2] In `katas/kata_001_agentic_loop/events.py`, reject any `EventRecord` whose payload contains a non-schema field (e.g. `prose_excerpt`, `completion_hint`) — relies on pydantic `extra="forbid"` on the model per data-model.md "no text-derived field is allowed"
- [x] T032 [US2] Add unit test `tests/katas/kata_001_agentic_loop/unit/test_decoy_phrases.py` driving synthetic `Turn` objects whose `assistant_text_blocks` contain every phrase from `SC-004` while `stop_signal="tool_use"`; assert the loop continues in all cases

**Checkpoint**: US2 fully functional — decoy-phrase fixture produces exactly one `end_turn` termination; malformed-tool-use fixture halts with labeled reason; tool errors keep the loop running with a structured `ToolResult(error)`; AST lint still green. BDD scenarios [TS-010, TS-011, TS-012, TS-013, TS-014] all pass.

---

## Phase 5: User Story 3 - Observable Event Log for Deterministic Reproduction (Priority: P3)

**Goal**: A practitioner inspects the JSONL event log produced by a kata run and reconstructs the full loop trajectory — iteration count, branch per turn, tool invocations, termination cause — from the log alone, without replaying the model. Two runs against the same fixture yield byte-identical stop-signal and branch-decision sequences.

**Independent Test**: Run the kata twice against `happy_path.json`, diff the `events.jsonl` outputs on the `stop_signal` + `branch_taken` columns, and assert identical sequences. Validate every record against `contracts/event-log-record.schema.json`.

### Tests for User Story 3

- [x] T033 [P] [US3] Copy/symlink `specs/001-agentic-loop/tests/features/observable_event_log.feature` to `tests/katas/kata_001_agentic_loop/features/observable_event_log.feature`
- [x] T034 [US3] Implement BDD step definitions for [TS-020, TS-021, TS-022, TS-023] in `tests/katas/kata_001_agentic_loop/step_defs/test_observable_event_log_steps.py` — steps run the kata twice against one fixture, diff event logs, and validate each record against the JSON Schema loaded from `specs/001-agentic-loop/contracts/event-log-record.schema.json`
- [x] T035 [P] [US3] Add unit test `tests/katas/kata_001_agentic_loop/unit/test_event_log_shape.py` asserting every emitted `EventRecord` validates against `contracts/event-log-record.schema.json`; also asserts exactly one record per run carries a non-null `termination_cause`
- [x] T036 [P] [US3] Add unit test `tests/katas/kata_001_agentic_loop/unit/test_trajectory_reconstruction.py` that takes a sample `events.jsonl` and reconstructs (iteration count, tool_invocations count, termination cause) without reading any other source — proves SC-008

### Implementation for User Story 3

- [x] T037 [US3] In `katas/kata_001_agentic_loop/events.py`, ensure JSONL determinism: stable key ordering on serialization (sort or explicit tuple), UTC `timestamp` with fixed precision, and a `freeze_time`-aware mode the tests use to make the reproducibility diff (SC-007) byte-identical
- [x] T038 [US3] In `katas/kata_001_agentic_loop/runner.py`, on terminal halt emit a final summary line to stdout listing `session_id`, `iterations`, `tool_invocations`, `termination_cause` — all values read back from the event log, not from in-memory state (prove the log is sufficient)
- [x] T039 [US3] Write a tiny trajectory-reconstruction helper at `katas/kata_001_agentic_loop/replay.py::reconstruct_trajectory(events_path) -> TrajectorySummary` used by T036 and referenced from the README

**Checkpoint**: US3 fully functional — two independent kata runs against the same fixture produce byte-identical `stop_signal` + `branch_taken` sequences; every record schema-validates; trajectory reconstruction works from the log alone. BDD scenarios [TS-020, TS-021, TS-022, TS-023] all pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T040 [P] Write `katas/kata_001_agentic_loop/README.md` with: kata objective, architecture walkthrough (CLI → Loop → Tool Registry → Event Log → Fixtures/SDK), anti-pattern defense explanation (how prose matching is structurally impossible here), run instructions mirroring `quickstart.md`, and the Principle VIII reflection section answering the two reflection prompts from `quickstart.md`
- [x] T041 [P] Add module-level docstrings to each of `katas/kata_001_agentic_loop/loop.py`, `client.py`, `tools.py`, `events.py`, `models.py`, `runner.py`, `replay.py` explaining the module's role in the signal-driven loop
- [x] T042 [P] Add why-comments (per Constitution Principle VIII) on every non-trivial function across `katas/kata_001_agentic_loop/*.py` — each comment must tie the code choice back to the kata objective (deterministic signal-driven control) rather than describing *what* the code does
- [x] T043 [P] Verify `specs/001-agentic-loop/quickstart.md` usage walkthrough is accurate against the final file layout; update paths or commands if drift was introduced during implementation
- [x] T044 Run `quickstart.md` end-to-end: `pytest tests/katas/kata_001_agentic_loop -v` against fixtures, then optional `LIVE_API=1 python -m katas.kata_001_agentic_loop.runner ...` smoke run; record both outputs as part of PR evidence
- [x] T045 [P] Add a "Reproducibility" section to `katas/kata_001_agentic_loop/README.md` documenting how `runs/<session-id>/events.jsonl` is the single source of truth, how `replay.py::reconstruct_trajectory` reads it, and how the SC-007 byte-identical diff is produced
- [x] T046 [P] Run `ruff check katas/kata_001_agentic_loop tests/katas/kata_001_agentic_loop` and `black --check` over the same paths; fix any findings
- [x] T047 [P] Produce a coverage report (`pytest --cov=katas.kata_001_agentic_loop`) and archive it at `runs/coverage/001_agentic_loop.txt`; target ≥ 90% line coverage on `loop.py`
- [x] T048 Final self-audit: read the emitted `events.jsonl` from the happy-path run and confirm it satisfies SC-001, SC-002, SC-003, SC-005, SC-007, SC-008 — record the check in the PR description
- [x] T049 [US1] Add unit test `tests/katas/kata_001_agentic_loop/unit/test_history_replay_order.py` asserting that replay from the recorded conversation history reproduces the live run's stop-signal + branch-taken sequence in the same order (FR-010); input is a `history.json` captured from a happy-path run, expected output is the `stop_signal`/`branch_taken` column slice of its `events.jsonl`
- [ ] T050 [P] Enrich `katas/kata_001_agentic_loop/notebook.ipynb` with Claude architecture certification content — additive, keeps existing cells. New ordered sections:
  1. **Concepts (Claude architecture certification)** — every Claude / Anthropic concept this kata exercises with a one-line definition tied to the certification syllabus: agentic loop, signal-driven control via `stop_reason`, tool use round-trip (`tool_use` ↔ `tool_result`), structured output, event-log provenance, deterministic replay, fixture-vs-live SDK seam.
  2. **Architecture walkthrough** — components (CLI → `Loop` → Tool Registry → `EventLog` → Fixtures/SDK) as an ASCII or mermaid block diagram.
  3. **Patterns** — signal-over-prose, schema-first contract, pure-function transition, append-only event log, replay-from-log determinism — each with the trade-off it solves.
  4. **Principles & recommendations** — Constitution principles enforced (I Determinism, II Schema-First, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner checklist for applying signal-driven loops on a real agent. Notebook becomes the Claude-architecture-cert reference for this kata; the existing `README.md` stays as the in-repo summary.

---

## Dependencies & Execution Order

**Phase order (strict):** Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6.

**Within-phase dependencies:**
- Phase 2: T006–T010 are all [P] because they live in different files; T011 depends on T006 and T010.
- Phase 3: T012–T016 (fixtures + feature copy) can run in parallel. T017 depends on T011 + T016 + T012–T015. T018, T019 are [P] once T006 exists. T020 depends on T006, T008, T009, T010, T011. T021 depends on T020. T022 depends on T020 + T010. T023 depends on T020 + T008.
- Phase 4: T024–T027 are [P]. T028 depends on T027 + fixtures. T029 depends on T020. T030 depends on T009. T031 depends on T010. T032 depends on T020.
- Phase 5: T033 is [P]. T034 depends on T033 + completed US1 loop. T035–T036 are [P] once events.py and a sample run exist. T037 depends on T010. T038 depends on T022. T039 depends on T010.
- Phase 6: T040–T043, T045–T047 are [P]. T044 depends on all prior phases complete. T048 depends on T044.

**Story dependencies:**
- US2 extends the loop built in US1 (malformed-tool-use halt, tool-error recovery) — cannot start until T020–T022 land.
- US3 consumes the event log emitted by US1/US2 — cannot validate reproducibility until both prior stories have produced records.

---

## Parallel Opportunities

**Phase 1 [P]:** T002, T003, T004 (different config files).

**Phase 2 [P]:** T006, T007, T008, T009, T010 (distinct modules).

**Phase 3 [P]:** fixture recording batch — T012, T013, T014, T015, T016 all in parallel; then T018, T019 in parallel; T017 gates on fixtures.

**Phase 4 [P]:** T024, T025, T026, T027 fixture/feature batch in parallel.

**Phase 5 [P]:** T033, T035, T036 in parallel.

**Phase 6 [P]:** T040, T041, T042, T043, T045, T046, T047 all in parallel.

---

## Implementation Strategy

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1). At this point the kata demonstrates Principle I end-to-end: signal-driven termination against `happy_path.json` plus all four edge-case fixtures, with AST lint enforcing no-prose-matching. This is already a credible kata deliverable.
- **Incremental delivery**: land Phase 4 (US2) next — adds anti-pattern red-team coverage (decoy phrases, malformed tool_use, tool-error recovery). Then Phase 5 (US3) adds the reproducibility and reviewability guarantees. Phase 6 documents and polishes.
- **Blast radius**: every phase is gated by BDD scenarios failing first (TDD per Constitution V); Phase 6's `/quickstart.md` run is the final acceptance gate.

---

## Notes

- `[P]` = different files, no shared state, no ordering dependency.
- Each user story is independently testable — US1 against `happy_path.json` + edge fixtures, US2 against `decoy_phrase.json` + `malformed_tool_use.json` + `tool_error.json`, US3 by diffing two independent runs.
- Verify every `.feature` scenario fails before writing the matching production code (Constitution V — TDD). Do NOT make tests pass by editing assertions; fix the loop instead (assertion-integrity rule).
- AST lint test `tests/katas/kata_001_agentic_loop/lint/test_no_prose_matching.py` is the irreversible guardrail against regression into prose matching — keep it green at all times after T019.
