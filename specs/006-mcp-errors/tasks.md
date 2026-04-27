# Tasks: MCP Integration with Structured Error Handling

**Input**: Design documents from `/specs/006-mcp-errors/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no shared state, no ordering dependency)
- [USn] = required on user-story tasks; omit on Setup / Foundational / Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-NNN"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/006_mcp_errors/__init__.py` with a package-level docstring stating the kata objective (typed MCP errors) and a Principle VIII reminder (README + why-comments required).
- [ ] T002 [P] Create test package skeleton `tests/katas/006_mcp_errors/__init__.py` plus empty subpackages `tests/katas/006_mcp_errors/unit/__init__.py`, `tests/katas/006_mcp_errors/step_defs/__init__.py`, `tests/katas/006_mcp_errors/lint/__init__.py`, `tests/katas/006_mcp_errors/fixtures/__init__.py`.
- [ ] T003 [P] Add `pytest`, `pytest-bdd`, `pydantic>=2`, `anthropic`, `mcp` to `[project.optional-dependencies].dev` in `pyproject.toml` — tracks plan.md §Primary Dependencies.
- [ ] T004 [P] Copy the frozen `.feature` files from `specs/006-mcp-errors/tests/features/*.feature` into `tests/katas/006_mcp_errors/features/` so `pytest-bdd` can discover them; do NOT modify scenarios (assertion-integrity rule).
- [ ] T005 [P] Copy the four JSON Schemas from `specs/006-mcp-errors/contracts/` into `tests/katas/006_mcp_errors/contracts/` for schema-validation tests: `mcp-tool-call.schema.json`, `structured-error.schema.json`, `retry-budget.schema.json`, `escalation-trigger.schema.json`.
- [ ] T006 [P] Add `runs/` to `.gitignore` — structured-error JSONL logs are per-session artifacts, not source.
- [ ] T007 [P] Create `tests/katas/006_mcp_errors/conftest.py` declaring the `pytest-bdd` features directory at `tests/katas/006_mcp_errors/features/` and exposing fixture-loader and schema-loader helpers.

---

## Phase 2: Foundational

Shared infrastructure that blocks every user story: pydantic models, injectable clock, session helper. No story label.

- [ ] T008 Implement the pydantic v2 `StructuredError` model in `katas/006_mcp_errors/models.py` — closed-enum `errorCategory` (`transient`, `validation`, `auth`, `quota`, `internal`, `transport`, `schema_violation`), `isRetryable: bool`, `detail` (min 1, max 1024), `retry_after_seconds: int | None`, and a `model_validator` enforcing the category→retryable invariants from data-model.md §StructuredError.
- [ ] T009 Implement pydantic v2 `ToolCall`, `MCPResponse`, `RetryBudget`, `RecoveryAction`, `EscalationTrigger`, `ErrorLogRecord` in `katas/006_mcp_errors/models.py` field-for-field per data-model.md; `MCPResponse` enforces "exactly one of `output` / `error`" as a validator; `extra="forbid"` on every model.
- [ ] T010 [P] Implement `RetryBudget.attempt()`, `.remaining()`, `.is_exhausted()` as pure functions that return a new budget instance (no mutation) and raise `BudgetExhausted` when a further attempt would exceed `max_attempts`.
- [ ] T011 [P] Create injectable clock abstraction `katas/006_mcp_errors/clock.py` (`Clock` protocol + `SystemClock` + `FakeClock`) so `backoff_seconds` is exercised in virtual time in tests — no `time.sleep` in the test path.
- [ ] T012 [P] Create session context helper `katas/006_mcp_errors/session.py` that assigns `session_id` (UUID4), resolves `runs/<session-id>/` paths, and exposes the directory to the JSONL log writer (FR-006).

**Checkpoint**: Models import cleanly, invariants are enforced at construction, clock is swappable, session directory resolver works. No business logic or I/O yet.

---

## Phase 3: User Story 1 — Transient Failure with Successful Retry (Priority: P1, MVP)

**Goal**: The agent receives a schema-valid `StructuredError` on a transient failure, branches to `retry` within the declared `RetryBudget`, the retry succeeds, and both attempts are recorded in `runs/<session-id>/errors.jsonl` with a shared `call_id` and `outcome="retried_success"` on the final record.

**Independent Test**: Force the in-kata `MCPServer` to fail transiently on attempt 1 and succeed on attempt 2 (fixture `retryable_success_after_retry.json`); assert `attempt=1` record has `errorCategory="transient"` + `isRetryable=true`, `attempt=2` record has `outcome="retried_success"`, and the two records share a `call_id` — all without a single generic failure string in the agent context.

### Tests for User Story 1 (write first — MUST fail initially per Constitution V)

- [ ] T013 [P] [US1] Fixture `tests/katas/006_mcp_errors/fixtures/retryable_success_after_retry.json` — first response: transient failure; second response: success payload.
- [ ] T014 [P] [US1] Step definitions for `@TS-001` (response carries `isError=true`, `errorCategory="transient"`, `isRetryable=true`, non-empty `detail`) in `tests/katas/006_mcp_errors/step_defs/test_transient_failure_retry_steps.py`. [TS-001]
- [ ] T015 [P] [US1] Step definitions for `@TS-002` (retryable-within-budget → recovery action `"retry"`, next invocation `isError=false`, final result surfaced) in the same steps file. [TS-002]
- [ ] T016 [P] [US1] Step definitions for `@TS-003` (two log records share a `call_id`, first has failure metadata, second has `outcome="retried_success"`, both carry tool identity + attempt + timestamp) in the same steps file. [TS-003]
- [ ] T017 [P] [US1] Step definitions for `@TS-004` (budget decrements on `attempt()`, returned budget reports `elapsed_attempts=1` + `remaining=2`, original budget object unmutated) in the same steps file. [TS-004]
- [ ] T018 [P] [US1] Step definitions for `@TS-005` Scenario Outline (`transient` and `quota` both branch to `"retry"` and construct a `next_call` with `attempt` incremented by 1) in the same steps file. [TS-005]
- [ ] T019 [P] [US1] Unit test `tests/katas/006_mcp_errors/unit/test_structured_error_schema.py` — invalid `errorCategory`, missing `isRetryable`, `detail > 1024` chars, and category/retryability invariant violations all raise `pydantic.ValidationError`. [TS-001]
- [ ] T020 [P] [US1] Unit test `tests/katas/006_mcp_errors/unit/test_retry_budget.py` — `attempt()` returns a new object (immutability), `BudgetExhausted` on overflow, `remaining()` / `is_exhausted()` behave per data-model.md. [TS-004]

### Implementation for User Story 1

- [ ] T021 [US1] Implement `MCPServer` in `katas/006_mcp_errors/server.py` exposing a single tool whose behavior is scripted by a `failure_mode` argument (`transient-once`, `validation`, `budget-exhaust`, `server-crash`, `schema-violation`); every failure path constructs a `StructuredError` via the pydantic model — NO raw strings, NO `"Operation failed"` / `"Error"` / `"Something went wrong"` literals anywhere in the module.
- [ ] T022 [US1] Implement agent-side MCP client wrapper `katas/006_mcp_errors/client.py` that invokes the tool and validates every response through `MCPResponse.model_validate` before returning the typed response to the caller. [TS-001]
- [ ] T023 [US1] Implement `policy.decide(response, call) -> RecoveryAction` in `katas/006_mcp_errors/policy.py` — retryable+budget → `"retry"` with `next_call.attempt` incremented; retryable+exhausted → `"escalate"` with `reason="budget_exhausted"`; non-retryable → `"escalate"` on first attempt; success path not computed. [TS-002, TS-005]
- [ ] T024 [US1] Implement the JSONL writer `katas/006_mcp_errors/log.py` — append-only `runs/<session-id>/errors.jsonl`, one `ErrorLogRecord` per attempt (successes included so SC-003 denominators are countable), UTC timestamps, closed-set `outcome`. [TS-003]
- [ ] T025 [US1] Implement runner orchestration `katas/006_mcp_errors/runner.py` — builds a `ToolCall`, invokes via `client.py`, feeds the `MCPResponse` into `policy.decide`, threads the updated `RetryBudget` through any retry, emits one `ErrorLogRecord` per attempt, surfaces the final result to stdout.
- [ ] T026 [US1] Wire `--scenario transient-recover` on `runner.py` backed by fixture `retryable_success_after_retry.json`.

**Checkpoint**: `pytest tests/katas/006_mcp_errors -k transient_failure_retry -v` is green; `@TS-001`, `@TS-002`, `@TS-003`, `@TS-004`, `@TS-005` all pass; MVP delivered — the kata already demonstrates typed recovery for the retryable path.

---

## Phase 4: User Story 2 — Validation Failure Routes to Escalation (Priority: P2)

**Goal**: Non-retryable MCP failures bypass retries entirely and emit a typed `EscalationTrigger`; transport-layer drops and non-conformant server payloads are synthesized locally into schema-conformant `StructuredError` instances; zero generic failure strings cross the MCP response boundary (anti-pattern defense).

**Independent Test**: Submit a tool-call with input that violates the server's validation rules (fixture `non_retryable_validation.json`); assert `RecoveryAction.action="escalate"`, `EscalationTrigger.reason="non_retryable_category"`, `attempts_taken=1`, the trigger embeds the triggering `StructuredError`, and a transcript scan yields zero occurrences of `"Operation failed"` / `"Something went wrong"` / a bare `"Error"` completion.

### Tests for User Story 2 (write first — MUST fail initially)

- [ ] T027 [P] [US2] Fixtures `tests/katas/006_mcp_errors/fixtures/non_retryable_validation.json`, `tests/katas/006_mcp_errors/fixtures/retryable_exhausted_budget.json`, `tests/katas/006_mcp_errors/fixtures/server_crash.json`, `tests/katas/006_mcp_errors/fixtures/malformed_response.json`, `tests/katas/006_mcp_errors/fixtures/network_drop.json` — one fixture per edge case from plan.md / data-model.md.
- [ ] T028 [P] [US2] Step definitions for `@TS-006` (validation input → `isError=true`, `errorCategory="validation"`, `isRetryable=false`) in `tests/katas/006_mcp_errors/step_defs/test_validation_failure_escalation_steps.py`. [TS-006]
- [ ] T029 [P] [US2] Step definitions for `@TS-007` (zero additional attempts, `EscalationTrigger.attempts_taken=1`) in the same steps file. [TS-007]
- [ ] T030 [P] [US2] Step definitions for `@TS-008` (trigger references originating `call_id`, closed-set `reason="non_retryable_category"`, names declared `escalation_sink`, embeds the triggering `StructuredError`) in the same steps file. [TS-008]
- [ ] T031 [P] [US2] Step definitions for `@TS-009` (scan agent transcript + tool-response log: zero `"Operation failed"`, zero `"Something went wrong"`, zero bare `"Error"` completion) in the same steps file. [TS-009]
- [ ] T032 [P] [US2] Step definitions for `@TS-010` (transport drop → synthesized `StructuredError` with `errorCategory="transport"`, passes schema, no raw exception string reaches agent context) in the same steps file. [TS-010]
- [ ] T033 [P] [US2] Step definitions for `@TS-011` (server returns `isError=true` missing `isRetryable` → synthesized `errorCategory="schema_violation"`, `isRetryable=false`, no generic-string fallback) in the same steps file. [TS-011]
- [ ] T034 [P] [US2] Step definitions for `@TS-012` (retryable failure recurs until budget exhausted → `action="escalate"`, `reason="budget_exhausted"`, log `outcome="retried_exhausted"`) in the same steps file. [TS-012]
- [ ] T035 [P] [US2] Step definitions for `@TS-013` Scenario Outline (`validation`, `auth`, `schema_violation` each → `"escalate"`, zero retries, `attempts_taken=1`) in the same steps file. [TS-013]
- [ ] T036 [P] [US2] Unit test `tests/katas/006_mcp_errors/unit/test_policy_branches.py` — every branch rule in `policy.decide` per data-model.md §RecoveryAction. [TS-007, TS-012, TS-013]
- [ ] T037 [P] [US2] Unit test `tests/katas/006_mcp_errors/unit/test_synthesizer.py` — transport-exception input → valid `StructuredError` (`errorCategory="transport"`); malformed-payload input → `errorCategory="schema_violation"` + `isRetryable=false`. [TS-010, TS-011]
- [ ] T038 [P] [US2] AST/grep lint test `tests/katas/006_mcp_errors/lint/test_no_generic_error_strings.py` — parses the AST of `katas/006_mcp_errors/server.py` and fails the build on any bare string literal equal to `"Operation failed"`, `"Error"`, or `"Something went wrong"`. [TS-009]

### Implementation for User Story 2

- [ ] T039 [US2] Implement `ErrorSynthesizer` in `katas/006_mcp_errors/synthesizer.py` with two entry points: `from_transport_exception(exc, call_id)` → `StructuredError(errorCategory="transport", ...)` and `from_malformed_payload(raw, call_id)` → `StructuredError(errorCategory="schema_violation", isRetryable=False, ...)`. [TS-010, TS-011]
- [ ] T040 [US2] Extend `katas/006_mcp_errors/client.py` to catch transport-layer exceptions and route through `ErrorSynthesizer.from_transport_exception`, wrap the result in an `MCPResponse(isError=True, error=...)`, and feed it to `policy.decide` like any other failure. [TS-010]
- [ ] T041 [US2] Extend `katas/006_mcp_errors/client.py` to catch `pydantic.ValidationError` raised by `MCPResponse.model_validate` and route through `ErrorSynthesizer.from_malformed_payload`. [TS-011]
- [ ] T042 [US2] Extend `katas/006_mcp_errors/policy.py` to construct `EscalationTrigger` with closed-set `reason`: `non_retryable_category` for first-attempt non-retryable, `budget_exhausted` on exhaustion, `schema_violation` on contract violations, `transport_unrecoverable` on unrecoverable transport drops. [TS-008, TS-012, TS-013]
- [ ] T043 [US2] Wire an escalation sink registry in `katas/006_mcp_errors/policy.py` (`"human_handoff" | "clarification_prompt" | "abort_with_explanation"`); the runner declares the sink at startup — default `human_handoff`. [TS-008]
- [ ] T044 [US2] Extend `katas/006_mcp_errors/runner.py` to persist emitted `EscalationTrigger` payloads to `runs/<session-id>/escalations/<trigger_id>.json` and populate `escalation_trigger_id` on the corresponding `ErrorLogRecord`. [TS-008, TS-012]
- [ ] T045 [US2] Add runner CLI scenarios `--scenario validation-escalate`, `--scenario budget-exhaust`, `--scenario server-crash`, `--scenario schema-violation`, `--scenario network-drop` backed by the matching fixtures.

**Checkpoint**: `pytest tests/katas/006_mcp_errors -k validation_failure_escalation -v` green; `@TS-006`, `@TS-007`, `@TS-008`, `@TS-009`, `@TS-010`, `@TS-011`, `@TS-012`, `@TS-013` all pass; AST lint green; transcript scan yields zero generic failure strings (SC-002 met).

---

## Phase 5: User Story 3 — Structured Error Log Inspection and Classification (Priority: P3)

**Goal**: The JSONL log at `runs/<session-id>/errors.jsonl` is aggregable by structured fields alone (no text parsing). Chained tool failures in a single agent turn are logged as independent per-`call_id` chains. Every record validates against the `ErrorLogRecord` schema and time-ordering within a `call_id` forms a coherent recovery chain.

**Independent Test**: Run a session containing at least one transient and one validation failure plus the `chained_failures.json` fixture (three tool calls of mixed categories in one turn); load `errors.jsonl`, group by `errorCategory` and `isRetryable` using only structured fields (never reading `detail`), and verify each `call_id` forms its own time-ordered chain with exactly one terminal outcome.

### Tests for User Story 3 (write first — MUST fail initially)

- [ ] T046 [P] [US3] Fixture `tests/katas/006_mcp_errors/fixtures/chained_failures.json` — one agent turn that fans out to three `ToolCall`s with mixed categories (`transient`, `validation`, `quota`).
- [ ] T047 [P] [US3] Step definitions for `@TS-014` (every failure entry carries `errorCategory`, `isRetryable`, `detail`; every entry carries `outcome` from the closed set `{success, retried_success, retried_exhausted, escalated, aborted}`) in `tests/katas/006_mcp_errors/step_defs/test_structured_error_log_steps.py`. [TS-014]
- [ ] T048 [P] [US3] Step definitions for `@TS-015` (group-by `errorCategory` and `isRetryable` derivable from structured fields alone; aggregation step never reads `detail`) in the same steps file. [TS-015]
- [ ] T049 [P] [US3] Step definitions for `@TS-016` (every JSONL line validates against the `ErrorLogRecord` model; every record carries `session_id`, `call_id`, `attempt`, `tool_name`) in the same steps file. [TS-016]
- [ ] T050 [P] [US3] Step definitions for `@TS-017` (records for one `call_id` are ordered by ascending timestamp; exactly one record carries `outcome="retried_success"`; preceding records carry failure metadata) in the same steps file. [TS-017]
- [ ] T051 [P] [US3] Step definitions for `@TS-018` (single turn with three tool calls → three independent record chains, no `call_id` collapsed, each chain resolves to its own outcome) in the same steps file. [TS-018]
- [ ] T052 [P] [US3] Unit test `tests/katas/006_mcp_errors/unit/test_error_log_shape.py` — shape + closed-set `outcome` + field-presence assertions against the JSONL writer output. [TS-014, TS-016]

### Implementation for User Story 3

- [ ] T053 [US3] Extend `katas/006_mcp_errors/runner.py` so a single agent turn can fan out to multiple `ToolCall`s, each owning its own `RetryBudget`, each producing an independent `ErrorLogRecord` chain — no `call_id` collapsing. [TS-018]
- [ ] T054 [US3] Add a log-reader helper `katas/006_mcp_errors/log.py::iter_records(session_id)` that yields validated `ErrorLogRecord` instances and supports group-by `errorCategory` in a 3-line idiom without reading `detail`. [TS-015, TS-017]
- [ ] T055 [US3] Add runner CLI scenario `--scenario chained-failures` backed by the chained-failures fixture.

**Checkpoint**: `pytest tests/katas/006_mcp_errors -k structured_error_log -v` green; `@TS-014`, `@TS-015`, `@TS-016`, `@TS-017`, `@TS-018` all pass; all three feature files green together.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T056 [P] Author `katas/006_mcp_errors/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — Model Context Protocol (MCP), typed error categories (the seven `errorCategory` values), retry budgets with exhaustion → `budget_exhausted`, escalation triggers (human_handoff / clarification_prompt / abort_with_explanation), structured error contract via pydantic, AST lint banning generic failure strings, fail-closed via `MCPResponse.model_validate` — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`runner` → `client` → MCP `server` → `models.MCPResponse` → `policy` (retry + escalate) → `synthesizer` → `log` (ErrorLogRecord JSONL) → `clock` + `session`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — typed-error-over-string, retry-budget bounding, escalation sink routing, structural anti-pattern lint — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (I Determinism, II Schema-First, V Test-First, VI Human-in-the-Loop, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — MCP error-handling contract — `StructuredError` schema, the 7 errorCategory values × `isRetryable` × `outcome` branch table, `RetryBudget` (`max_attempts`, exhaustion → `budget_exhausted`), `EscalationTrigger` sink options, `ErrorLogRecord` closed-set `outcome` vocabulary, AST lint + schema rejection as the two structural defenses, FR-008 human-review path with `runs/<session-id>/escalations/<trigger_id>.json` (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T057 [P] Add module-level docstrings to every file under `katas/006_mcp_errors/`: `__init__.py`, `server.py`, `client.py`, `models.py`, `policy.py`, `synthesizer.py`, `log.py`, `runner.py`, `clock.py`, `session.py` — each docstring names the FR / SC the module implements.
- [ ] T058 [P] Add *why*-comments (Principle VIII) on every non-trivial function: `policy.decide`, `RetryBudget.attempt`, `ErrorSynthesizer.from_transport_exception`, `ErrorSynthesizer.from_malformed_payload`, `log.iter_records`, `runner.run_scenario`. Each comment ties the choice back to the kata objective (typed branching) rather than describing *what* the code does.
- [ ] T060 [P] Verify `specs/006-mcp-errors/quickstart.md` against the final implementation: every command runs, every row in the scenario-to-spec table maps to an existing fixture under `tests/katas/006_mcp_errors/fixtures/`, and the artifact path (`runs/<session-id>/errors.jsonl`) is reconciled with the code — update quickstart text if the implementation settled on a different filename.
- [ ] T061 Run the quickstart end to end: `pip install -e ".[dev]"` → `pytest tests/katas/006_mcp_errors -v` → `python -m katas.006_mcp_errors.runner --scenario transient-recover` → open `runs/<session-id>/errors.jsonl` and confirm it contains both the failed and the successful attempt records with matching `call_id`. Archive the outputs as PR evidence.
- [ ] T062 [P] Scan the repo (both `katas/006_mcp_errors/` source and a sample `runs/` directory from the quickstart run) for the strings `"Operation failed"`, `"Something went wrong"`, and bare `"Error"` completions; zero occurrences required (SC-002).
- [ ] T063 [P] Audit every emitted `errors.jsonl` record on the fixture corpus for non-null `errorCategory` and `isRetryable` on all failure rows — 100% target (SC-001).
- [ ] T064 [P] Audit every `isRetryable=false` log line for a correlated `escalation_trigger_id` and exactly one attempt per `call_id` (SC-004).
- [ ] T065 [P] Confirm SC-003 resolution: once `/iikit-clarify` has fixed the threshold at 95% on eligible fixtures, regenerate the feature file via `/iikit-04-testify` (never by hand) so the `@needs-clarify SC-003` tag is removed.
- [ ] T066 [P] Run `ruff check katas/006_mcp_errors tests/katas/006_mcp_errors` and `black --check` on the same paths; fix findings.
- [ ] T067 [P] Produce a coverage report (`pytest --cov=katas.006_mcp_errors`) and archive it at `runs/coverage/006_mcp_errors.txt`; target ≥ 90% line coverage on `policy.py`, `synthesizer.py`, and `log.py`.
- [ ] T068 Final Constitution self-audit: for each of principles I, II, V, VI, VII, VIII, record in the notebook Reflection cell which artifact demonstrates compliance (e.g. "II: `MCPResponse.model_validate` at `client.py` line N rejects the anti-pattern").
- [ ] T069 Regenerate the IIKit dashboard: `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` (required by `dashboard-refresh` rule after any `specs/` change).

---

## Dependencies & Execution Order

```
Phase 1 (T001..T007)
    |
Phase 2 (T008..T012)         <- models + clock + session foundation
    |
Phase 3 / US1 (T013..T026)   <- MVP, independently shippable
    |
Phase 4 / US2 (T027..T045)   <- depends on US1 policy + client
    |
Phase 5 / US3 (T046..T055)   <- depends on US2 chained escalation + log shape
    |
Final Phase (T056..T069)
```

**Within-phase dependencies:**
- Phase 1: T001 precedes T002; T003–T007 are [P] after T001.
- Phase 2: T008 precedes T009 (same file); T010 depends on T009 (uses `RetryBudget`); T011 and T012 are [P] after T009.
- Phase 3: T013–T020 run in parallel (distinct files). T021 depends on T008 + T009. T022 depends on T009 + T021. T023 depends on T008 + T009 + T010. T024 depends on T009 + T012. T025 depends on T022 + T023 + T024. T026 depends on T025 + T013.
- Phase 4: T027–T038 parallel. T039 depends on T008. T040 and T041 depend on T022 + T039. T042 depends on T023 + T039. T043 depends on T042. T044 depends on T024 + T042. T045 depends on T025 + T027.
- Phase 5: T046–T052 parallel. T053 depends on T025 + T044. T054 depends on T024. T055 depends on T053 + T046.
- Final Phase: T056–T058, T060, T062–T067 are [P]. T061 depends on T025 + T045 + T055. T068 depends on T061. T069 must run last.

**Story dependencies:**
- US2 extends the policy + client built in US1 (synthesizer, escalation payload) — cannot start until T022 + T023 + T024 land.
- US3 consumes the log emitted by US1/US2 — cannot validate chained-independence until US2's escalation writer (T044) is in place.

---

## Parallel Opportunities

- **Phase 1 [P]**: T002, T003, T004, T005, T006, T007 (distinct files) after T001.
- **Phase 2 [P]**: T010, T011, T012 (distinct modules) after T009.
- **Phase 3 tests [P]**: T013–T020 — fixture, step-defs, and unit tests live in distinct files.
- **Phase 3 implementation**: T021 and T022 parallel-able (distinct modules) once T009 lands; T023 and T024 parallel (policy vs. log writer) once T009 + T010 + T012 land.
- **Phase 4 tests [P]**: T027–T038 — fixture batch and all step-defs live in distinct files.
- **Phase 4 implementation**: T039 parallel to T043 (synthesizer vs. sink registry); T040 + T041 sequence into T042 + T044.
- **Phase 5 tests [P]**: T046–T052 in parallel.
- **Final Phase [P]**: T056–T058, T060, T062–T067 in parallel on distinct deliverables.

---

## Implementation Strategy

1. **Land MVP at end of Phase 3 (US1)**: ship `StructuredError` + `RetryBudget` + `policy.decide` retry branch + JSONL log. The kata already defends against the generic-string anti-pattern on the retryable path.
2. **Land the full anti-pattern defense in Phase 4 (US2)**: AST lint, synthesizer, typed escalation payload. This is where the kata's core learning value is realized — every non-retryable, every transport drop, every schema violation is typed.
3. **Land observability in Phase 5 (US3)**: chained-failure independence + log reader + group-by without text parsing. The system functions without this so it ships last.
4. **Polish and documentation last**: notebook + docstrings + why-comments + quickstart verify + Constitution audit (in notebook Reflection cell) + dashboard refresh. No production code changes in this phase.

---

## Notes

- **`.feature` files are frozen** — do NOT edit `tests/katas/006_mcp_errors/features/*.feature`. Only files in `step_defs/` are edited by hand; if a scenario is wrong, re-run `/iikit-04-testify` from the spec (assertion-integrity rule).
- **Every `@TS-NNN` tag** is referenced in brackets on the step-def task that implements it — traceability is the contract.
- **Fail-closed tests**: the AST lint (T038) must fail the build if `server.py` reintroduces a bare `"Operation failed"` string — regression-proofs SC-002.
- **Clock is injectable** (T011): no `time.sleep()` in tests; backoff runs in virtual time.
- **SC-003 carries a placeholder**: T065 is parked behind `/iikit-clarify`; do not pick the threshold by hand.
- **Dashboard refresh (T069)** is required by the `dashboard-refresh` rule after every `specs/` change.
- **No `--no-verify`, no hook bypass** per `assertion-integrity` rule — if a hash check fails, re-run the relevant `/iikit-*` skill, do not edit the hash.
