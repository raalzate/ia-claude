# Tasks: Structured Human Handoff Protocol

**Input**: Design documents from `/specs/016-human-handoff/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-005"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/016_human_handoff/__init__.py` (empty marker) and mirror test package `tests/katas/016_human_handoff/__init__.py`
- [ ] T002 [P] Ensure repo `pyproject.toml` declares Python 3.11+ and the `[dev]` extras include `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, `jsonschema` per plan.md §Technical Context (extend only if already absent)
- [ ] T003 [P] Add `runs/handoffs/` and `runs/*/events.jsonl` glob to `.gitignore` so operator-queue writes and per-session audit logs stay out of version control (plan.md §Storage)
- [ ] T004 [P] Create `tests/katas/016_human_handoff/conftest.py` stub: pytest-bdd `features` dir pointer, fixture loader helper for `tests/katas/016_human_handoff/fixtures/`, and a tmpdir-backed `runs_dir` fixture that isolates `runs/handoffs/` per test
- [ ] T005 [P] Copy/symlink the three `.feature` files from `specs/016-human-handoff/tests/features/` into `tests/katas/016_human_handoff/features/` so pytest-bdd can discover them (`structured_handoff_payload.feature`, `antipattern_prose_handoff_defense.feature`, `schema_evolution_required_field.feature`)

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, JSON-Schema-bound tool definition, session suspension guard, operator-queue sink, audit-log writer, CLI scaffolding. No story label.

- [ ] T006 [P] Implement pydantic v2 entities in `katas/016_human_handoff/models.py` per `data-model.md`: `Severity` (Literal `"low","medium","high","critical"`), `EscalationReason` (Literal closed enum), `ActionRecord`, `HandoffPayload` (with `issue_summary` `maxlen=500`, `customer_id` required-non-null, `escalation_id` UUID4 default-factory, `extra="forbid"`), `EscalationEvent`, `OperatorQueueEntry`, `SessionState` (Literal `"ACTIVE","SUSPENDED"`)
- [ ] T007 [P] Implement `katas/016_human_handoff/preconditions.py`: `EscalationPrecondition` registry covering policy-breach, out-of-policy-demand, operational-limit, unresolved-after-retries, explicit-user-request; each class exposes `evaluate(session_ctx) -> EscalationReason | None` and is registered without free-text branching (plan.md §FR-001 traceability)
- [ ] T008 [P] Implement `katas/016_human_handoff/tools.py`: declarative `escalate_to_human` tool definition whose `input_schema` is built by calling `HandoffPayload.model_json_schema()` — binds the schema to the tool-use site (FR-003, FR-004). Also declare a separate `write_handoff_note` plain-text tool guarded behind a `_ANTI_PATTERN_ONLY=True` flag so it is only registered by the anti-pattern fixture harness (FR-008)
- [ ] T009 [P] Implement `katas/016_human_handoff/session.py`: `SessionSuspendedError` exception + `SuspensionAwareClient` wrapper around the Anthropic SDK that flips `SessionState` to `SUSPENDED` the moment an `escalate_to_human` `tool_use` block is observed and raises `SessionSuspendedError` on every subsequent `messages.create` (FR-002, US1 Independent Test — zero bytes)
- [ ] T010 [P] Implement `katas/016_human_handoff/operator_queue.py`: `OperatorQueue.accept(payload: HandoffPayload) -> OperatorQueueEntry` — runs `HandoffPayload.model_validate`, computes `sha256` of the serialized payload as `handoff_payload_hash`, writes `runs/handoffs/<escalation_id>.json`, and appends a one-line index record to `runs/handoffs/index.jsonl`. On `ValidationError`, emits a `SchemaRejected` audit event and does NOT write the queue file (FR-006, FR-007, FR-009, SC-001, SC-004)
- [ ] T011 [P] Implement `katas/016_human_handoff/events.py`: JSONL audit-log writer at `runs/<session_id>/events.jsonl`; `emit(event: EscalationEvent)` with `extra="forbid"` on the pydantic model; reject any record carrying a non-schema field (mirror of kata 1 shape) — so prose fields like `transcript_excerpt` are structurally impossible (Principle VII)
- [ ] T012 Wire `katas/016_human_handoff/runner.py` CLI: `python -m katas.016_human_handoff.runner --scenario <fixture_name>`, reads `LIVE_API` env var to pick `SuspensionAwareClient(live=True)` vs a recorded client, constructs the `OperatorQueue` + event-log pair, prints the `runs/<session_id>/events.jsonl` path on exit (quickstart.md)

**Checkpoint**: Foundation ready — models, tool schema, suspension guard, operator queue, audit log writer, CLI scaffolding all in place. Every user story can now be implemented against them.

---

## Phase 3: User Story 1 - Escalation suspends chat and emits schema-valid payload (Priority: P1) MVP

**Goal**: A practitioner trips a declared escalation precondition; the agent suspends further conversational output, invokes `escalate_to_human` exactly once, and emits a schema-valid `HandoffPayload` routed to the operator queue with a traceable id.

**Independent Test**: Run the kata against `policy-breach-mid-tool-call.json`, `unknown-customer.json`, `empty-actions-taken.json`, and `repeated-escalation-same-session.json`; assert (a) zero bytes of further conversational text post-escalation, (b) exactly one `escalate_to_human` invocation per trigger, (c) schema-valid payload written under `runs/handoffs/<escalation_id>.json`.

### Tests for User Story 1

- [ ] T013 [P] [US1] Record fixture session `tests/katas/016_human_handoff/fixtures/policy-breach-mid-tool-call.json`: mid-tool-call precondition fires, `actions_taken` reflects only completed steps
- [ ] T014 [P] [US1] Record fixture session `tests/katas/016_human_handoff/fixtures/unknown-customer.json`: session with no bound customer — uses the `"unknown"` sentinel
- [ ] T015 [P] [US1] Record fixture session `tests/katas/016_human_handoff/fixtures/empty-actions-taken.json`: escalation fires before any action was taken, empty list is expected
- [ ] T016 [P] [US1] Record fixture session `tests/katas/016_human_handoff/fixtures/repeated-escalation-same-session.json`: two escalations within one session, distinct `escalation_id` per event
- [ ] T017 [US1] Implement BDD step definitions for [TS-001, TS-002, TS-003, TS-006, TS-007, TS-008, TS-009, TS-010, TS-011] in `tests/katas/016_human_handoff/step_defs/test_structured_handoff_payload_steps.py` — steps wire to the `SuspensionAwareClient` + recorded fixtures and assert event-log records, operator-queue files, and suspension semantics
- [ ] T018 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_handoff_payload_required_fields.py` asserting `customer_id`, `issue_summary`, `actions_taken`, `escalation_reason` are all required (pydantic `ValidationError` on omission) [TS-008]
- [ ] T019 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_tool_schema_is_handoff_payload.py` — deep-equal the `escalate_to_human` tool's `input_schema` with `HandoffPayload.model_json_schema()` [TS-005]
- [ ] T020 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_actions_taken_structured.py` — `actions_taken: list[str]` raises `ValidationError`; only `list[ActionRecord]` passes [TS-004]
- [ ] T021 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_session_suspension_zero_bytes.py` — trigger an escalation then invoke `SuspensionAwareClient.messages.create(...)` again and assert `SessionSuspendedError` plus `len(post_escalation_text) == 0` [TS-002, TS-010]
- [ ] T022 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_repeated_escalations_distinct.py` — replay `repeated-escalation-same-session.json` and assert two distinct UUID4 files under `runs/handoffs/` [TS-006]
- [ ] T023 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_mid_tool_call_actions_taken.py` — assert `actions_taken` length matches only *completed* tool steps when the precondition fires mid-call [TS-007]
- [ ] T024 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_unknown_customer_sentinel.py` — assert `customer_id=""` raises `ValidationError`, `customer_id="unknown"` passes [TS-008]
- [ ] T025 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_empty_actions_taken_valid.py` — `actions_taken=[]` passes validation and `escalation_reason` still populated [TS-009]
- [ ] T026 [P] [US1] Add unit test `tests/katas/016_human_handoff/unit/test_operator_queue_traceable_id.py` — every accepted payload produces `runs/handoffs/<escalation_id>.json` AND an index line referencing it [TS-003, TS-011]

### Implementation for User Story 1

- [ ] T027 [US1] In `katas/016_human_handoff/session.py`, implement the post-trigger guard: on detecting an `escalate_to_human` `tool_use` block in the SDK response, flip `SessionState` to `SUSPENDED`, capture the raw tool input, and raise `SessionSuspendedError` on any follow-up `messages.create` (FR-002) — MUST NOT inspect prose to make this decision [TS-002, TS-010]
- [ ] T028 [US1] In `katas/016_human_handoff/preconditions.py`, wire the fixture-loader entry point: given a loaded scenario, evaluate the registered preconditions in order and return the first matching `EscalationReason` (FR-001) [TS-001, TS-011]
- [ ] T029 [US1] In `katas/016_human_handoff/operator_queue.py`, finalize the happy-path write: `accept` runs `HandoffPayload.model_validate`, writes `runs/handoffs/<escalation_id>.json`, emits an `EscalationEvent(kind="delivered")` via the audit log, returns the `OperatorQueueEntry` (FR-003, FR-004, FR-009) [TS-001, TS-003]
- [ ] T030 [US1] In `katas/016_human_handoff/runner.py`, implement the end-to-end trigger → suspend → emit → persist flow and print the resulting `runs/handoffs/<escalation_id>.json` path. On repeated escalations within the same run, mint a fresh UUID4 per trigger (FR-011) [TS-006]
- [ ] T031 [US1] In `katas/016_human_handoff/session.py`, ensure partial assistant messages accumulated prior to trigger are suppressed from the handoff payload and NEVER forwarded to the user — `issue_summary` is filled only from the tool-use input, never from streamed prose (edge case + FR-007) [TS-010]

**Checkpoint**: US1 fully functional — practitioner can run the kata against any P1 fixture, observe zero further conversational bytes, and inspect a schema-valid operator-queue file. BDD scenarios @TS-001, @TS-002, @TS-003, @TS-004, @TS-005, @TS-006, @TS-007, @TS-008, @TS-009, @TS-010, @TS-011 all pass.

---

## Phase 4: User Story 2 - Schema rejects prose-only handoff (anti-pattern defense) (Priority: P2)

**Goal**: A practitioner attempts to coax the agent into a prose-only or transcript-dumping handoff; the schema layer rejects the attempt structurally — the only handoff surface is the schema-bound tool, and the plain-text `write_handoff_note` tool registered in the anti-pattern fixture is refused by the validator.

**Independent Test**: Run the kata against `prose-handoff-attempt.json` with the anti-pattern harness registered; assert (a) the `write_handoff_note` input is rejected with a deterministic validation error, (b) no file appears under `runs/handoffs/`, (c) the audit log records a `SchemaRejected` event, (d) a payload whose `issue_summary` exceeds 500 chars is rejected.

### Tests for User Story 2

- [ ] T032 [P] [US2] Record fixture session `tests/katas/016_human_handoff/fixtures/prose-handoff-attempt.json`: model selects `write_handoff_note` with free-text content and/or a transcript dump (anti-pattern fixture per plan.md §Constraints)
- [ ] T033 [US2] Implement BDD step definitions for [TS-012, TS-013, TS-014, TS-015, TS-016, TS-017] in `tests/katas/016_human_handoff/step_defs/test_antipattern_prose_handoff_defense_steps.py` — steps register the anti-pattern tool harness, trigger the escalation, and assert the queue stays empty while the audit log records the rejection
- [ ] T034 [P] [US2] Add unit test `tests/katas/016_human_handoff/unit/test_handoff_payload_maxlen_summary.py` — `issue_summary` > 500 chars raises `ValidationError`; exactly 500 chars passes (FR-007 transcript-dumping defense) [TS-015]
- [ ] T035 [P] [US2] Add unit test `tests/katas/016_human_handoff/unit/test_schema_rejects_prose_only.py` — call `OperatorQueue.accept` with (a) a prose string, (b) a payload missing a required field, (c) a payload with extra/unknown fields; each MUST raise and leave `runs/handoffs/` empty (FR-006, FR-008) [TS-012, TS-014]
- [ ] T036 [P] [US2] Add unit test `tests/katas/016_human_handoff/unit/test_raw_transcript_refused.py` — `write_handoff_note` tool invocation path is NEVER accepted by `OperatorQueue`; test registers the anti-pattern tool and asserts `SchemaRejected` in the audit log (FR-007, SC-002) [TS-013, TS-017]
- [ ] T037 [P] [US2] Add unit test `tests/katas/016_human_handoff/unit/test_operator_queue_only_schema_valid.py` — walk `runs/handoffs/` after the P2 run and assert every `.json` file schema-validates against `specs/016-human-handoff/contracts/operator-queue-entry.schema.json` (SC-001, SC-002) [TS-016]

### Implementation for User Story 2

- [ ] T038 [US2] In `katas/016_human_handoff/operator_queue.py`, harden `accept` to reject (a) non-`HandoffPayload` inputs (raise `TypeError`), (b) `ValidationError` outcomes (emit `EscalationEvent(kind="rejected", reason=<validation_detail>)` via the audit log, do NOT write to disk) — guarantees zero raw-transcript handoffs reach the queue (FR-006, FR-007, FR-008, SC-002) [TS-012, TS-014, TS-016]
- [ ] T039 [US2] In `katas/016_human_handoff/tools.py`, keep `write_handoff_note` permanently gated behind the `_ANTI_PATTERN_ONLY` flag and assert at module import time that production runner paths never register it — if accidentally registered, `OperatorQueue` refuses its output because the content has no `escalation_id` / `handoff_payload_hash` binding (FR-008) [TS-013, TS-017]
- [ ] T040 [US2] In `katas/016_human_handoff/models.py`, confirm `HandoffPayload` sets `model_config = ConfigDict(extra="forbid", str_max_length=None)` and `issue_summary: Annotated[str, StringConstraints(max_length=500)]` so summary-slot transcript dumping is structurally impossible (FR-007) [TS-015]

**Checkpoint**: US2 fully functional — prose-handoff attempts, transcript dumps, and malformed payloads all raise before reaching disk; the queue directory contains only schema-valid files; every rejection is recorded in the audit log. BDD scenarios @TS-012, @TS-013, @TS-014, @TS-015, @TS-016, @TS-017 all pass.

---

## Phase 5: User Story 3 - Adding a required field propagates across escalations (Priority: P3)

**Goal**: A practitioner extends `HandoffPayload` by adding a new required field (`severity`); subsequent escalations MUST include it or fail validation, and no change to the agent prompt text is needed — the schema is the source of truth.

**Independent Test**: Re-run the P1 fixtures against a `HandoffPayload` variant where `severity` is required; legacy payloads fail `model_validate`, new payloads with a valid `severity` pass, and the audit log records the rejection and the delivery separately with distinct escalation ids.

### Tests for User Story 3

- [ ] T041 [US3] Implement BDD step definitions for [TS-018, TS-019, TS-020, TS-021, TS-022, TS-023] in `tests/katas/016_human_handoff/step_defs/test_schema_evolution_required_field_steps.py` — steps load the v1.1 schema, replay P1 fixtures without `severity`, assert rejection; replay with `severity`, assert delivery; assert audit log contains both
- [ ] T042 [P] [US3] Add unit test `tests/katas/016_human_handoff/unit/test_schema_rejects_missing_severity.py` — construct `HandoffPayload` sans `severity` and assert `ValidationError`; include a `valid_severity` positive case that passes (FR-010, SC-001) [TS-018, TS-019, TS-021]
- [ ] T043 [P] [US3] Add unit test `tests/katas/016_human_handoff/unit/test_prompt_text_unchanged.py` — AST/textual check that no file under `katas/016_human_handoff/` was edited to reference `"severity"` in prompt strings (only in the pydantic model + JSON Schema); proves the schema alone propagates the requirement (FR-010) [TS-020]
- [ ] T044 [P] [US3] Add unit test `tests/katas/016_human_handoff/unit/test_documentation_describes_contract.py` — scans `katas/016_human_handoff/README.md` for required sections: preconditions taxonomy, handoff schema, anti-pattern defense (FR-012, Principle VIII) [TS-022]
- [ ] T045 [P] [US3] Add unit test `tests/katas/016_human_handoff/unit/test_escalation_id_traceable_end_to_end.py` — take an `escalation_id` from `runs/handoffs/index.jsonl`, assert it also appears in a `runs/<session-id>/events.jsonl` record (delivered or rejected) and in the corresponding `runs/handoffs/<escalation_id>.json` payload (FR-009, SC-004) [TS-023]

### Implementation for User Story 3

- [ ] T046 [US3] In `katas/016_human_handoff/models.py`, make `severity: Severity` a required field on `HandoffPayload` (no default) and `OperatorQueueEntry.severity` mirrors it — schema v1.1 per `data-model.md` (FR-010) [TS-018, TS-019]
- [ ] T047 [US3] In `specs/016-human-handoff/contracts/handoff-payload.schema.json` and `operator-queue-entry.schema.json`, add `severity` to `required` and to `properties` with `enum: ["low","medium","high","critical"]`; re-run schema validation in T037 and T045 against the updated contracts (FR-010, SC-001) [TS-020]
- [ ] T048 [US3] In `katas/016_human_handoff/operator_queue.py`, on every `accept`, record the schema version actually applied (`"1.1"`) in the audit-log event so future schema rolls produce a traceable version delta (FR-010 extended) [TS-021, TS-023]

**Checkpoint**: US3 fully functional — new required field propagates via the pydantic model alone; legacy payloads are rejected with a deterministic `ValidationError`; the audit log shows the version bump; agent prompt text is unchanged. BDD scenarios @TS-018, @TS-019, @TS-020, @TS-021, @TS-022, @TS-023 all pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T049 [P] Write `katas/016_human_handoff/README.md` per plan.md §Principle VIII deliverable with the following mandatory sections: **Objective** (Principle VI Human-in-the-Loop contract for this kata), **Escalation Trigger Taxonomy** (policy-breach, out-of-policy-demand, operational-limit, unresolved-after-retries, explicit-user-request — one short paragraph each tying to `preconditions.py`), **Handoff Payload Schema** (copy of the pydantic model shape + JSON Schema `$id`), **Anti-Pattern Defense** (explain *why* prose-only handoffs and raw-transcript dumping are structurally impossible — no silent auto-approve), **Escalation Policy & Resume Semantics** (`ACTIVE → SUSPENDED` is terminal for the session; the spec deliberately does NOT define un-suspension — operator concern, out of kata scope), **Run** (mirror `quickstart.md` — fixture commands + `LIVE_API=1` smoke), **Reflection** answering: (1) "How does this kata enforce Constitution Principle VIII by making the schema the single source of handoff truth?", (2) "How does it enforce Constitution Principle VI Human-in-the-Loop by making escalation a terminal state rather than a soft boundary?"
- [ ] T050 [P] Add module-level docstrings to every file under `katas/016_human_handoff/*.py` (`__init__.py`, `models.py`, `tools.py`, `preconditions.py`, `session.py`, `operator_queue.py`, `events.py`, `runner.py`) explaining the module's role in the suspend-and-structured-handoff contract (Principle VIII)
- [ ] T051 [P] Add why-comments on every non-trivial function in `katas/016_human_handoff/*.py` (per Constitution Principle VIII — each comment ties the code choice back to one of: FR-00X, SC-00X, or the anti-pattern defense — NOT what the code does line by line)
- [ ] T052 [P] Document the escalation policy and resume semantics explicitly in `katas/016_human_handoff/README.md` (single subsection): which preconditions fire, what the payload guarantees, why there is no programmatic resume path, and how an operator would take over the session out-of-band (plan.md §Complexity Tracking — no session resumption after suspension)
- [ ] T053 [P] Verify `specs/016-human-handoff/quickstart.md` usage walkthrough is accurate against the final layout; update any paths or commands that drifted during implementation
- [ ] T054 Run `quickstart.md` end-to-end: `pytest tests/katas/016_human_handoff -v` against fixtures, plus the optional `LIVE_API=1 python -m katas.016_human_handoff.runner --scenario policy-breach-mid-tool-call` smoke; attach both outputs as PR evidence
- [ ] T055 [P] Run `ruff check katas/016_human_handoff tests/katas/016_human_handoff` and `black --check` over the same paths; fix any findings
- [ ] T056 [P] Produce a coverage report (`pytest --cov=katas.016_human_handoff`) and archive it at `runs/coverage/016_human_handoff.txt`; target >= 90% line coverage on `session.py`, `operator_queue.py`, and `models.py`
- [ ] T057 Final self-audit: inspect `runs/handoffs/index.jsonl` and one `runs/handoffs/<escalation_id>.json` from the happy-path run; confirm SC-001 (100% schema-valid), SC-002 (zero raw-transcript handoffs), SC-004 (end-to-end traceability). Note SC-003 is declared but pedagogically demonstrated only in the README — flagged by `@needs-clarify SC-003`. Record the audit in the PR description

---

## Dependencies & Execution Order

**Phase order (strict):** Phase 1 -> Phase 2 -> Phase 3 (US1) -> Phase 4 (US2) -> Phase 5 (US3) -> Phase 6.

**Within-phase dependencies:**
- Phase 1: T001 before all tests; T002–T005 [P] (different files).
- Phase 2: T006–T011 are [P] (distinct modules). T012 depends on T006, T008, T009, T010, T011.
- Phase 3: T013–T016 (fixtures) in parallel. T017 depends on T005 + T013–T016 + T009 + T010. T018–T026 [P] once T006–T011 exist. T027 depends on T006 + T009. T028 depends on T006 + T007. T029 depends on T006 + T010 + T011. T030 depends on T012 + T027 + T029. T031 depends on T009.
- Phase 4: T032 [P] (fixture). T033 depends on T032 + T005 + T008. T034–T037 [P] once T006 + T010 exist. T038 depends on T010 + T029. T039 depends on T008. T040 depends on T006.
- Phase 5: T041 depends on T005 + US1 implementation + T046. T042–T045 [P] once T046 + T047 are done. T046 depends on T006. T047 depends on T006. T048 depends on T011 + T029.
- Phase 6: T049–T053, T055–T056 [P]. T054 depends on all prior phases. T057 depends on T054.

**Story dependencies:**
- US2 extends US1's `OperatorQueue` + `SuspensionAwareClient` — Phase 4 cannot begin before T027–T031 land.
- US3 mutates the `HandoffPayload` schema US1 and US2 rely on — Phase 5 runs last because its tests assert on both the new-schema happy path and the legacy-payload rejection.

---

## Parallel Opportunities

**Phase 1 [P]:** T002, T003, T004, T005 (different config or test files).

**Phase 2 [P]:** T006, T007, T008, T009, T010, T011 (one module each).

**Phase 3 [P]:** fixture recording batch — T013, T014, T015, T016 in parallel; then unit-test batch T018–T026 all parallel once foundation is in place; T017 gates on fixtures + step-def wiring.

**Phase 4 [P]:** T034, T035, T036, T037 unit-test batch parallel once T032 fixture exists.

**Phase 5 [P]:** T042, T043, T044, T045 parallel once T046 + T047 land.

**Phase 6 [P]:** T049, T050, T051, T052, T053, T055, T056 all parallel.

---

## Implementation Strategy

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1). At this point the kata demonstrates Principle VI end-to-end: a declared precondition fires, the session suspends, a schema-valid `HandoffPayload` lands on disk with a traceable id. This is already a credible kata deliverable (the "escalation sink" described in plan.md §Summary).
- **Incremental delivery**: Phase 4 (US2) next — adds the anti-pattern red-team that makes the protocol trustworthy (Principle II — Schema-Enforced Boundaries). Then Phase 5 (US3) adds the evolvability proof (schema is the source of truth, not prompt text). Phase 6 closes the Principle VIII documentation loop and verifies the `quickstart.md` walkthrough.
- **Blast radius**: every phase is gated by BDD scenarios failing first (Constitution V — TDD). Phase 6's `quickstart.md` run is the final acceptance gate. Per the assertion-integrity rule, NEVER modify `.feature` assertions to make tests pass — fix the production code in `katas/016_human_handoff/` instead.

---

## Notes

- `[P]` = different files, no shared state, no ordering dependency.
- Each user story is independently testable — US1 against the four P1 fixtures; US2 against `prose-handoff-attempt.json`; US3 by re-running P1 fixtures against the v1.1 schema.
- Verify every `.feature` scenario fails before writing the matching production code (Constitution V — TDD). Do NOT make tests pass by editing assertions; fix the kata code instead (assertion-integrity rule).
- The suspension guard in `session.py` (T027) is the irreversible anti-pattern barrier — keep the zero-bytes assertion green at all times after T021 lands. Any regression into prose-driven branching violates Principle I (Determinism Over Probability) and Principle VI (Human-in-the-Loop Escalation).
- `write_handoff_note` is ONLY registered by the anti-pattern test harness; it must never leak into `runner.py` or any production path (T039 enforces this at import time).
- SC-003 (median resolution-time delta) is declared but not empirically measured in this kata — plan.md §Complexity Tracking flags it as a clarify follow-up; the pedagogic delta is demonstrated in the README, not in a test assertion.
