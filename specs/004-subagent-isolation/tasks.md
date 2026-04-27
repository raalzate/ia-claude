# Tasks: Strict Subagent Context Isolation (Hub-and-Spoke)

**Input**: Design documents from `/specs/004-subagent-isolation/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] on story tasks
- Traceability: `[TS-001, TS-002]`, never prose ranges

## Phase 1: Setup

- [ ] T001 Create package skeleton `katas/kata_004_subagent_isolation/__init__.py` and test package skeleton `tests/katas/kata_004_subagent_isolation/__init__.py` (+ `unit/`, `lint/`, `integration/`, `features/`, `step_defs/`, `fixtures/` subpackages with empty `__init__.py`)
- [ ] T002 [P] Ensure `pyproject.toml` extras include `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, `jsonschema` under `[project.optional-dependencies].dev`; install with `pip install -e ".[dev]"`
- [ ] T003 [P] Add `runs/` to `.gitignore` (provenance dir per plan.md §Storage; per-run artifacts must not be tracked)
- [ ] T004 [P] Configure `pytest.ini` / `pyproject.toml` `[tool.pytest.ini_options]` to register `bdd_features_base_dir = tests/katas/kata_004_subagent_isolation/features` and collect `tests/katas/kata_004_subagent_isolation`
- [ ] T004a [P] Prereq verification: confirm all three JSON Schemas exist under `specs/004-subagent-isolation/contracts/` — `subtask-payload.schema.json`, `subagent-result.schema.json`, `handoff-contract.schema.json`. Each must be Draft 2020-12 with its declared `$id`. Fail-closed gate for every downstream task that consumes a schema (blocks T009, T037, T041, T054 from starting if any file is missing). If missing, re-run `/iikit-02-plan` Phase 1 output step rather than hand-authoring the schema here.

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [ ] T005 Define pydantic models in `katas/kata_004_subagent_isolation/models.py`: `SubtaskPayload`, `SubagentResult`, `SubagentError`, `HandoffContract` with `model_config = ConfigDict(extra="forbid")` per data-model.md
- [ ] T006 Define terminal exceptions in `katas/kata_004_subagent_isolation/models.py`: `SubagentResultValidationError`, `SubtaskPayloadBuildError`, `RoleNotRegistered`
- [ ] T007 [P] Define `TaskSpawner` Protocol in `katas/kata_004_subagent_isolation/task_spawner.py` with `spawn(payload: SubtaskPayload) -> SubagentResult`
- [ ] T008 [P] Implement injectable Anthropic client wrapper in `katas/kata_004_subagent_isolation/client.py` mirroring Kata 1 D-001 (class with `messages_create(**kwargs)` seam so subagent tests can inject a `RecordedSubagentClient`)
- [ ] T009 Copy JSON Schemas from `specs/004-subagent-isolation/contracts/` into a loader helper in `katas/kata_004_subagent_isolation/models.py` (or reference by path) so `HandoffContract.input_schema` / `output_schema` can be validated at construction against Draft 2020-12
- [ ] T010 Wire per-run audit writer in `katas/kata_004_subagent_isolation/runner.py`: creates `runs/<session-id>/` and opens `coordinator_history.json`, `subagent_inputs.jsonl`, `subagent_outputs.jsonl` handles (FR-005)

**Checkpoint**: Models + exceptions + spawner protocol + client seam + audit writer all importable; no business logic yet.

## Phase 3: User Story 1 — Scoped Fan-Out from Coordinator (Priority: P1) [US1]

**Goal**: Coordinator decomposes a task, spawns one subagent per subtask with a scoped `SubtaskPayload`, and recomposes schema-valid `SubagentResult`s into a final answer.

**Independent Test**: Submit a decomposable task against `happy_path.json` fixture; assert one `SubtaskPayload` per subtask, each input contains only declared fields, each returned `SubagentResult` validates, and default subagents do not hold the task-spawning tool.

### Tests for User Story 1 (write first; all must fail before implementation)

- [ ] T011 [P] [US1] Copy `tests/features/scoped_fanout_coordinator.feature` from `specs/004-subagent-isolation/tests/features/` into `tests/katas/kata_004_subagent_isolation/features/scoped_fanout_coordinator.feature` (verbatim — DO NOT MODIFY SCENARIOS)
- [ ] T012 [P] [US1] Create recorded fixture `tests/katas/kata_004_subagent_isolation/fixtures/happy_path.json` (coordinator spawns 2 subagents; both return valid `SubagentResult`)
- [ ] T013 [US1] Step definitions for `@TS-001` in `tests/katas/kata_004_subagent_isolation/step_defs/test_scoped_fanout_steps.py`: "Coordinator emits one scoped payload per subtask" [TS-001]
- [ ] T014 [US1] Step definitions for `@TS-002` in the same file: "Subagent input contains only fields declared by the payload schema" [TS-002]
- [ ] T015 [US1] Step definitions for `@TS-003` in the same file: "Subagent result validates against declared SubagentResult schema" [TS-003]
- [ ] T016 [US1] Step definitions for `@TS-004` in the same file: "Coordinator consumes only declared fields of the subagent result" [TS-004]
- [ ] T017 [US1] Step definitions for `@TS-005` in the same file: "Subagents do not hold the task-spawning tool by default" [TS-005]
- [ ] T018 [US1] Step definitions for `@TS-006` in the same file: "Empty decomposition returns a defined no-op outcome" [TS-006]
- [ ] T019 [P] [US1] Unit test `tests/katas/kata_004_subagent_isolation/unit/test_payload_minimization.py` asserting serialized `SubtaskPayload` byte length never exceeds sum of declared field sizes plus schema overhead [FR-001]
- [ ] T020 [P] [US1] Unit test `tests/katas/kata_004_subagent_isolation/unit/test_tool_allowlist.py` asserting default subagents' allowed-tools list excludes the task-spawning tool [FR-006, TS-005]

### Implementation for User Story 1

- [ ] T021 [US1] Implement `Subagent` class in `katas/kata_004_subagent_isolation/subagent.py`: `run(payload: SubtaskPayload) -> SubagentResult`, opens fresh `messages.create` per call seeded only from the payload, wraps raw response with `SubagentResult.model_validate_json` and converts `ValidationError` to `SubagentResultValidationError`
- [ ] T022 [US1] Implement default `LocalTaskSpawner` in `katas/kata_004_subagent_isolation/task_spawner.py` that looks up the `Subagent` for `payload.role_name` and calls `.run(payload)`
- [ ] T023 [US1] Implement `Coordinator` class in `katas/kata_004_subagent_isolation/coordinator.py` with `session_id`, `model`, private `_history`, private `_scratchpad`, `task_spawner: TaskSpawner`, `handoff_contracts: dict[str, HandoffContract]`
- [ ] T024 [US1] Implement `Coordinator.spawn_subtask(role_name, payload_fields)` building a `SubtaskPayload` from the closed-dict inputs; raises `SubtaskPayloadBuildError` on extra fields; never touches `_history` or `_scratchpad`
- [ ] T025 [US1] Implement `Coordinator.run(task)` — decomposes, iterates spawns through `task_spawner.spawn(payload)`, logs each `(SubtaskPayload, SubagentResult)` to `subagent_inputs.jsonl` / `subagent_outputs.jsonl` (FR-005), and recomposes only declared `SubagentResult.output` fields
- [ ] T026 [US1] Implement no-op branch in `Coordinator.run` for empty decomposition: returns defined no-op outcome, spawns zero subagents, does not hang [TS-006]
- [ ] T027 [US1] Implement CLI entry in `katas/kata_004_subagent_isolation/runner.py`: `python -m katas.kata_004_subagent_isolation.runner --model --prompt`; reads `LIVE_API` env to choose real vs. recorded client

**Checkpoint**: `pytest tests/katas/kata_004_subagent_isolation/features/scoped_fanout_coordinator.feature tests/katas/kata_004_subagent_isolation/unit/test_payload_minimization.py tests/katas/kata_004_subagent_isolation/unit/test_tool_allowlist.py` passes. US1 delivers end-to-end scoped fan-out on the happy path.

## Phase 4: User Story 2 — Leak-Probe Defense (Priority: P2) [US2]

**Goal**: Prove the isolation boundary holds — UUID probes seeded in coordinator-private history never appear in any subagent's input payload; raw transcripts are rejected by schema; audit log captures exact payloads and results; nested spawns remain isolated.

**Independent Test**: Run the `leak_probe.json` fixture; scan every line of `subagent_inputs.jsonl` for the probe UUID and assert `grep -c` equals zero (SC-004). Submit a raw transcript as `inputs` and assert `SubtaskPayloadBuildError`.

### Tests for User Story 2

- [ ] T028 [P] [US2] Copy `tests/features/leak_probe_isolation.feature` into `tests/katas/kata_004_subagent_isolation/features/leak_probe_isolation.feature` (verbatim)
- [ ] T029 [P] [US2] Create fixture `tests/katas/kata_004_subagent_isolation/fixtures/leak_probe.json` (coordinator history seeded with UUID; 2 subagents; expected clean inputs)
- [ ] T030 [P] [US2] Create fixture `tests/katas/kata_004_subagent_isolation/fixtures/nested_spawn.json` (subagent authorized to spawn one child; scoped payload only)
- [ ] T031 [US2] Step definitions for `@TS-007` in `tests/katas/kata_004_subagent_isolation/step_defs/test_leak_probe_steps.py`: "Leak-probe UUID does not appear in any subagent input" [TS-007]
- [ ] T032 [US2] Step definitions for `@TS-008` in the same file: "Coordinator-private scratchpad does not leak into subagent input" [TS-008]
- [ ] T033 [US2] Step definitions for `@TS-009` in the same file: "Forwarding the raw coordinator transcript is rejected as a schema violation" [TS-009]
- [ ] T034 [US2] Step definitions for `@TS-010` in the same file: "Audit log captures exact payload and result per subagent" [TS-010]
- [ ] T035 [US2] Step definitions for `@TS-011` in the same file: "Nested subagent spawning applies isolation recursively" [TS-011]
- [ ] T036 [US2] Step definitions for `@TS-012` Scenario Outline in the same file: "Coordinator-private content is blocked across representative leak channels" (examples: `conversation_history`, `scratchpad_note`, `prior_tool_result`, `earlier_user_turn`) [TS-012]
- [ ] T037 [P] [US2] AST+grep lint test `tests/katas/kata_004_subagent_isolation/lint/test_no_history_leak.py` asserting `subagent.py` has no import of `katas.kata_004_subagent_isolation.coordinator` and no attribute access matching `_history`, `_messages`, `_transcript`, `_scratchpad`, `_private_history` [FR-002, SC-001]
- [ ] T038 [P] [US2] Integration test `tests/katas/kata_004_subagent_isolation/integration/test_leak_probe.py` running coordinator with seeded UUID, scanning `runs/<session-id>/subagent_inputs.jsonl`, asserting zero occurrences [SC-001, SC-004]
- [ ] T039 [P] [US2] Unit test `tests/katas/kata_004_subagent_isolation/unit/test_nested_spawning.py` asserting a child subagent input contains neither parent subagent turns nor coordinator history [FR-007]
- [ ] T039a [P] [US2] Unit test `tests/katas/kata_004_subagent_isolation/unit/test_authorized_nested_spawn.py` exercising FR-006 + FR-007 together: a parent subagent whose `SubtaskPayload.nested_spawn_authorizations` declares a narrower allow-list successfully spawns exactly that authorized subset, a child spawn attempt outside the allow-list raises a terminal error, and the child's input contains neither coordinator history nor parent subagent turns [FR-006, FR-007, TS-005, TS-011]

### Implementation for User Story 2

- [ ] T040 [US2] Harden `Coordinator.spawn_subtask` to reject a `SubtaskPayload.inputs` dict whose values are or contain the raw `_history`/`_scratchpad` structures; raise `SubtaskPayloadBuildError` before SDK call [TS-009, FR-001]
- [ ] T041 [US2] Implement audit writer finalization: every spawn writes one line to `subagent_inputs.jsonl` (exact serialized `SubtaskPayload`) and one line to `subagent_outputs.jsonl` (raw SDK string + validated `SubagentResult.model_dump_json()`) [TS-010, FR-005]
- [ ] T042 [US2] Implement recursive/nested spawn support: expose opt-in authorization on a subagent via a narrowly scoped inner `TaskSpawner` instance that does NOT forward the parent subagent's turns or coordinator history; child receives only its own `SubtaskPayload` [TS-011, FR-007]
- [ ] T043 [US2] Ensure `subagent.py` module remains clean of any import or attribute access that would break `test_no_history_leak.py` — refactor any accidental reference discovered when lint runs [FR-002]

**Checkpoint**: `pytest tests/katas/kata_004_subagent_isolation/features/leak_probe_isolation.feature tests/katas/kata_004_subagent_isolation/lint tests/katas/kata_004_subagent_isolation/integration tests/katas/kata_004_subagent_isolation/unit/test_nested_spawning.py` passes. Isolation is observably verified, not merely asserted.

## Phase 5: User Story 3 — Swappable Subagent via Typed Contract (Priority: P3) [US3]

**Goal**: Swap one subagent implementation behind the same `HandoffContract` and prove the coordinator runs unchanged; malformed or extra-field outputs surface as terminal errors.

**Independent Test**: Run the reference happy-path task with the default `Subagent`, then rerun with a `StubTaskSpawner` returning canned `SubagentResult`s under the same contract, and assert identical coordinator-observable behavior. Feed malformed JSON and extra-field outputs; assert terminal `SubagentResultValidationError`.

### Tests for User Story 3

- [ ] T044 [P] [US3] Copy `tests/features/swappable_subagent_contract.feature` into `tests/katas/kata_004_subagent_isolation/features/swappable_subagent_contract.feature` (verbatim)
- [ ] T045 [P] [US3] Create fixture `tests/katas/kata_004_subagent_isolation/fixtures/swap_equivalent.json` (stub subagent honors same contract as default)
- [ ] T046 [P] [US3] Create fixture `tests/katas/kata_004_subagent_isolation/fixtures/malformed_result.json` (subagent returns non-parseable or contract-violating JSON)
- [ ] T047 [US3] Step definitions for `@TS-013` in `tests/katas/kata_004_subagent_isolation/step_defs/test_swappable_steps.py`: "Swap a subagent implementation that honors the same contract" [TS-013]
- [ ] T048 [US3] Step definitions for `@TS-014` in the same file: "Swapped subagent output violating the contract surfaces a terminal error" [TS-014]
- [ ] T049 [US3] Step definitions for `@TS-015` in the same file: "Malformed JSON from subagent is a terminal error with no silent fallback" [TS-015]
- [ ] T050 [US3] Step definitions for `@TS-016` in the same file: "Extra fields in subagent result are rejected under extra=\"forbid\"" [TS-016]
- [ ] T051 [US3] Step definitions for `@TS-017` Scenario Outline in the same file: "Terminal validation errors are surfaced with labeled reasons" (examples: `non_parseable_json`, `missing_required_field`, `extra_undeclared_field`, `task_id_mismatch` → `schema_violation`) [TS-017]
- [ ] T052 [US3] Step definitions for `@TS-018` in the same file: "Coordinator depends only on the typed contract, not subagent internals" [TS-018]
- [ ] T053 [P] [US3] Unit test `tests/katas/kata_004_subagent_isolation/unit/test_swap_equivalence.py` wiring a `StubTaskSpawner` through the same seam and asserting identical coordinator-observable behavior to the default [FR-008, SC-003]
- [ ] T054 [P] [US3] Unit test `tests/katas/kata_004_subagent_isolation/unit/test_result_validation.py` covering malformed JSON, missing required field, extra undeclared field, and task_id mismatch each raising `SubagentResultValidationError` with `category="schema_violation"` [FR-003, FR-004, SC-002]

### Implementation for User Story 3

- [ ] T055 [US3] Implement `StubTaskSpawner` in `katas/kata_004_subagent_isolation/task_spawner.py` (or a dedicated `testing.py`) that returns canned `SubagentResult`s under a given contract, for swap-equivalence use
- [ ] T056 [US3] Enforce `task_id` / `role_name` echo in `SubagentResult` validation inside `Subagent.run` and `Coordinator._consume_result`: any mismatch raises `SubagentResultValidationError` (terminal) [TS-017, data-model.md invariants]
- [ ] T057 [US3] Ensure the coordinator exposes a single injection point (`Coordinator(task_spawner=...)`) and contains no code path that references subagent-internal state — validated by T053 [FR-008, TS-018]
- [ ] T058 [US3] Label every `SubagentResultValidationError` with a `reason` field drawn from `SubagentError.category` enum (`schema_violation` | `tool_failure` | `refusal` | `other`) [TS-017]

**Checkpoint**: `pytest tests/katas/kata_004_subagent_isolation/features/swappable_subagent_contract.feature tests/katas/kata_004_subagent_isolation/unit/test_swap_equivalence.py tests/katas/kata_004_subagent_isolation/unit/test_result_validation.py` passes. Swap equivalence + terminal-error posture proven.

## Final Phase: Polish & Cross-Cutting Concerns

### Documentation (Principle VIII — Mandatory Documentation)

- [ ] T059 [P] Author `katas/kata_004_subagent_isolation/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — hub-and-spoke subagent orchestration, scoped fan-out, structured handoff contract (`SubtaskPayload` / `SubagentResult`), AST lint as governance, leak-probe UUID scan, pydantic `extra="forbid"` triple defense, fresh SDK session per subagent call — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`Coordinator` (hub) → `TaskSpawner` (injection seam) → `Subagent` (spoke) → `models` (HandoffContract) → `client` (Anthropic seam) → `runner` (CLI + audit)) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — closed-payload handoff, no-history-leak, fresh-session-per-spawn, ValidationError-as-terminal — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, IV Subagent Isolation, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — subagent isolation contract — context boundary (only `SubtaskPayload` crosses), return value (only `SubagentResult`), no-leakage triple defense (AST lint + leak-probe UUID + `extra="forbid"`) (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T060 [P] Add module-level docstrings to every file explaining its role in subagent orchestration: `coordinator.py` (hub, owns history), `subagent.py` (spoke, seeded from payload only), `task_spawner.py` (injection seam, swap point), `models.py` (typed handoff contract), `client.py` (Anthropic seam), `runner.py` (CLI + audit writer)
- [ ] T061 [P] Add why-comments on non-trivial functions: `Coordinator.spawn_subtask` (Principle IV — why we build payload from a closed dict, not from history), `Coordinator.run` (why audit log is mandatory before returning, FR-005), `Subagent.run` (why fresh SDK session per call), `SubagentResult.model_validate_json` call site (why `ValidationError` is terminal, FR-004)
- [ ] T063 [P] Verify `specs/004-subagent-isolation/quickstart.md` matches implemented CLI flags, fixture paths, and audit file layout; update any drift

### Validation

- [ ] T064 Run quickstart validation: execute every command in `specs/004-subagent-isolation/quickstart.md` top-to-bottom (`pytest tests/katas/kata_004_subagent_isolation -v`, optional `LIVE_API=1` CLI run, jq+ajv audit commands); confirm all assertions pass
- [ ] T065 [P] Run `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` to refresh dashboard after adding `katas/kata_004_subagent_isolation/` files and `tasks.md`
- [ ] T066 [P] Ensure `.specify/context.json` assertion-integrity hashes for US-001, US-002, US-003 feature files are present and locked (re-run `/iikit-04-testify` only if feature files changed; otherwise verify hashes match)
- [ ] T067 Full test sweep: `pytest tests/katas/kata_004_subagent_isolation -v --strict-markers` green; AST lint (T037) green; leak-probe UUID count = 0 across all `runs/<session-id>/subagent_inputs.jsonl` lines (SC-001, SC-004); 100% of subagent outputs either schema-valid or quarantined (SC-002); swap-equivalence leaves coordinator unchanged (SC-003)

## Dependencies & Execution Order

- **Phase 1 (Setup, T001–T004)** → must complete before Phase 2
- **Phase 2 (Foundational, T005–T010)** → models, protocol, client wrapper, audit writer block all user stories
- **Phase 3 (US1, T011–T027)** → depends on Phase 2; delivers MVP end-to-end
- **Phase 4 (US2, T028–T043)** → depends on Phase 3 (Coordinator.run + audit writer exist); leak-probe extends, not rewrites
- **Phase 5 (US3, T044–T058)** → depends on Phase 2 TaskSpawner Protocol + Phase 3 default spawner; US3 tests can be written in parallel with US2 but implementation sequenced after US2 to preserve audit output for SC-003 demonstration
- **Final Phase (T059–T067)** → depends on all user stories complete

User-story independence: any US can be verified in isolation via its own feature file + fixture set, but implementation order above gives the shortest green path.

## Parallel Opportunities

Within a single phase, tasks marked `[P]` touch disjoint files and may be run in parallel:

- **Phase 1**: T002, T003, T004 parallel (different config files)
- **Phase 2**: T007, T008 parallel (distinct modules)
- **Phase 3 tests**: T011, T012, T019, T020 parallel (feature copy, fixture, two unit tests — no overlap)
- **Phase 4 tests**: T028, T029, T030, T037, T038, T039 parallel (feature copy + fixtures + lint + integration + nested-spawn unit)
- **Phase 5 tests**: T044, T045, T046, T053, T054 parallel (feature copy + fixtures + two unit tests)
- **Final Phase docs**: T059, T060, T061, T063 parallel (notebook, docstrings, why-comments, quickstart verify touch disjoint files)
- **Final Phase validation**: T065, T066 parallel after T064

Step-definition files (T013–T018, T031–T036, T047–T052) are sequential within each file because they share a single Python module per feature.

## Implementation Strategy

1. Land **Phase 1 + Phase 2** in one PR or sitting — these are foundational and expose no coordinator logic yet.
2. Land **US1 MVP** (Phase 3) — at checkpoint the kata runs end-to-end on the happy path and is independently demonstrable.
3. Land **US2 leak-probe defense** (Phase 4) — adds the observable proof that isolation holds; this is where the kata's pedagogical core (Principle IV) becomes testable.
4. Land **US3 swap equivalence** (Phase 5) — the architectural payoff of the typed contract.
5. Close with **Final Phase** — Principle VIII documentation, quickstart re-run, dashboard refresh.

Suggested commit cadence: one commit per phase checkpoint; additional commits for doc polish are fine.

## Notes

- Feature files in `tests/katas/kata_004_subagent_isolation/features/` MUST be verbatim copies of the files in `specs/004-subagent-isolation/tests/features/`. Per assertion-integrity rule, never edit `.feature` files directly — re-run `/iikit-04-testify` if requirements change.
- The AST lint test (T037) is the load-bearing architectural guard for Principle IV. If it flakes or is deleted, the kata silently loses its anti-pattern defense.
- The leak-probe UUID scan (T038) operates on the real `runs/<session-id>/subagent_inputs.jsonl`, not on a stubbed in-memory object — this is deliberate so the audit file itself is part of the contract (FR-005).
- Per plan.md §Complexity Tracking: concurrent fan-out, retry budgets, and shared-utility refactors are deliberately NOT in scope; YAGNI until a second kata needs them.
- Every `[TS-NNN]` tag traces to a scenario in the copied `.feature` files; the step-definition tasks (T013–T018, T031–T036, T047–T052) cite the exact TS IDs for pytest-bdd scenario binding.
