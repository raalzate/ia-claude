# Tasks: Deterministic Guardrails via PreToolUse Hooks

**Input**: Design documents from `/specs/002-pretool-guardrails/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no ordering dependency)
- [USn] = required on story tasks (US1 / US2 / US3)
- Traceability: `[TS-001, TS-002]`, NEVER "TS-001 through TS-005"

---

## Phase 1: Setup

- [ ] T001 Create package skeleton `katas/kata_002_pretool_guardrails/__init__.py` with empty `__all__` and a module docstring naming the kata and its anti-pattern defense (prompt-only enforcement).
- [ ] T002 [P] Create test package skeleton `tests/katas/kata_002_pretool_guardrails/__init__.py` and empty `tests/katas/kata_002_pretool_guardrails/unit/__init__.py`, `tests/katas/kata_002_pretool_guardrails/lint/__init__.py`, `tests/katas/kata_002_pretool_guardrails/step_defs/__init__.py`.
- [ ] T003 [P] Add dev-dependencies `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd` to the repository dependency manifest (pnpm not applicable — Python: `pyproject.toml` or `requirements-dev.txt`) and pin `python>=3.11`.
- [ ] T004 [P] Create `config/policy.json` seed fixture with fields (`policy_id`, `policy_snapshot_version`, `max_refund`, `comparison_stance="strict_less_than"`, `escalation_pathway`, `effective_from`) per `data-model.md`.
- [ ] T005 [P] Add `runs/` to `.gitignore` (per-session JSONL output directory per plan.md Storage section).
- [ ] T006 [P] Configure `pytest-bdd` feature-file discovery to point at `specs/002-pretool-guardrails/tests/features/` in `tests/katas/kata_002_pretool_guardrails/conftest.py` (stub only — real fixtures added in Phase 2).

## Phase 2: Foundational (blocks all story phases)

- [ ] T007 Implement pydantic v2 model `ToolCallPayload` in `katas/kata_002_pretool_guardrails/models.py` with fields per `data-model.md` (`tool_name`, `correlation_id`, `amount: Decimal`, `currency`, `customer_id`, `reason`), `extra="forbid"`, and `amount > 0` validator.
- [ ] T008 [P] Implement pydantic v2 model `PolicyConfig` in `katas/kata_002_pretool_guardrails/models.py` (frozen, `max_refund: Decimal`, `comparison_stance: Literal["strict_less_than"]`, `policy_snapshot_version`, `escalation_pathway`, `effective_from: datetime`).
- [ ] T009 [P] Implement pydantic v2 models `HookVerdict`, `StructuredError`, `EscalationEvent` in `katas/kata_002_pretool_guardrails/models.py` per `data-model.md` field tables.
- [ ] T010 [P] Define reason-code enum (`schema_violation`, `policy_breach`, `hook_failure`) in `katas/kata_002_pretool_guardrails/errors.py`.
- [ ] T011 Implement `PolicyConfig` loader in `katas/kata_002_pretool_guardrails/policy.py` that reads `config/policy.json` fresh on every call, parses decimals safely, and raises a distinguishable exception when the file is unreadable (feeds `hook_failure` path, FR-012).
- [ ] T012 [P] Implement JSONL `EventLog` writer in `katas/kata_002_pretool_guardrails/events.py` that appends `{kind, correlation_id, payload, timestamp}` records to `runs/<session-id>/events.jsonl` (FR-009, Principle VII).
- [ ] T013 [P] Implement local `refund_api_stub` in `katas/kata_002_pretool_guardrails/refund_api_stub.py` that logs every received call to `runs/<session-id>/refund_api_calls.jsonl` and returns a canned success response (enables FR-006 / SC-002 zero-call assertions).
- [ ] T014 [P] Implement `EscalationEvent` emitter in `katas/kata_002_pretool_guardrails/escalation.py` that builds the event from `(HookVerdict, PolicyConfig, payload_digest)` and writes it through the `EventLog` (FR-007, Principle VI).
- [ ] T015 [P] Create `katas/kata_002_pretool_guardrails/prompts.py` containing ONLY descriptive system-prompt string constants for the agent — MUST NOT include any numeric literal equal to `PolicyConfig.max_refund` (FR-008).
- [ ] T016 Implement `PreToolUseHook` protocol and `RefundPolicyHook.evaluate(payload, policy) -> HookVerdict` in `katas/kata_002_pretool_guardrails/hook.py` that: (1) validates `ToolCallPayload` → `schema_violation`, (2) compares `amount < policy.max_refund` → `policy_breach`, (3) wraps all of the above in a `try/except` → `hook_failure` (FR-012 fail closed).
- [ ] T017 Implement CLI entrypoint `python -m katas.kata_002_pretool_guardrails.runner` in `katas/kata_002_pretool_guardrails/runner.py` that loads policy, constructs payload, invokes hook, and either dispatches to the stub on allow or emits `StructuredError` + `EscalationEvent` on reject.
- [ ] T018 Create `tests/katas/kata_002_pretool_guardrails/conftest.py` real fixtures: `session_tmpdir`, `policy_snapshotter` (copies `config/policy.json` into the tmpdir), `stub_api_inspector` (reads `refund_api_calls.jsonl`), `audit_log_reader` (reads `events.jsonl`).
- [ ] T019 [P] Copy the 12 fixture payloads declared in `plan.md` into `tests/katas/kata_002_pretool_guardrails/fixtures/` (`within_limit.json`, `at_limit.json`, `over_limit.json`, `missing_amount.json`, `negative_amount.json`, `non_numeric_amount.json`, `extra_fields.json`, `hook_failure_corrupt_policy.json`, `policy_change_before.json`, `policy_change_after.json`, `concurrent_policy_update.json`, `retry_same_over_limit.json`).

**Checkpoint**: Foundation is usable by every story phase. No story work may start until T007–T019 are green.

---

## Phase 3: User Story 1 (P1) MVP — Refund Within Policy Proceeds Untouched

**Goal**: Prove the hook does not over-block; a schema-valid in-policy refund reaches the stub exactly once and returns a real success outcome.

**Independent Test**: Submit a payload with `amount < max_refund`, observe exactly one entry in `refund_api_calls.jsonl` with the original payload, and a success outcome on the runner stdout.

### Tests for User Story 1

- [ ] T020 [P] [US1] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_hook_verdict_within_limit.py` asserting `RefundPolicyHook.evaluate` returns `HookVerdict(verdict="allow", reason_code=None)` for an amount strictly below `max_refund` [TS-001].
- [ ] T021 [P] [US1] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_within_policy_refund_steps.py` binding the Gherkin clauses of `specs/002-pretool-guardrails/tests/features/within_policy_refund.feature` [TS-001, TS-002].
- [ ] T022 [P] [US1] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_contracts_schemas_published_steps.py` that loads all five files under `specs/002-pretool-guardrails/contracts/` and asserts each is valid Draft 2020-12 JSON Schema [TS-021].

### Implementation for User Story 1

- [ ] T023 [US1] Wire the happy-path branch in `katas/kata_002_pretool_guardrails/runner.py`: on `HookVerdict.allow`, dispatch the un-mutated payload to `refund_api_stub.process_refund` and surface the real stub response to the caller (FR-001, US1-AS1, US1-AS2).
- [ ] T024 [US1] Ensure `events.jsonl` records `kind="invocation"`, `kind="verdict"` (allow), and `kind="refund_api_call"` in that order for the happy path (FR-009 invariant for allow verdicts).

**Checkpoint**: `pytest tests/katas/kata_002_pretool_guardrails/unit/test_hook_verdict_within_limit.py tests/katas/kata_002_pretool_guardrails/step_defs/test_within_policy_refund_steps.py` green. TS-001, TS-002, TS-021 green. Running the CLI with `within_limit.json` produces exactly one stub call.

---

## Phase 4: User Story 2 (P2) — Over-Limit Refund Is Blocked Pre-API by Deterministic Logic

**Goal**: Over-limit, malformed, at-limit, and corrupt-policy invocations are rejected deterministically with zero external API calls and a structured error + escalation.

**Independent Test**: Submit `over_limit.json` — observe zero entries in `refund_api_calls.jsonl`, one `StructuredError` in the captured model context, one escalation record, and identical verdicts on a second run.

### Tests for User Story 2

- [ ] T025 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_hook_verdict_over_limit.py` — over-limit amount → `HookVerdict(verdict="reject", reason_code="policy_breach")`, zero stub calls, one escalation emitted [TS-003, TS-005].
- [ ] T026 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_structured_error_shape.py` asserting the returned `StructuredError` carries `reason_code`, `field`, `rule_violated`, `policy_id`, `correlation_id`, `escalation_pathway`, and a deterministic `message` string [TS-004, TS-018].
- [ ] T027 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_escalation_event_emitted.py` — asserts `actions_taken == []` and `escalation_reason == "policy_breach"` on the written JSONL line [TS-005, TS-020].
- [ ] T028 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_determinism_repeat_run.py` — run evaluate twice on identical inputs; assert byte-equal verdict JSON excluding `evaluated_at` [TS-006].
- [ ] T029 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_hook_verdict_at_limit_boundary.py` — amount exactly equal to `max_refund` → reject under `strict_less_than` stance [TS-013].
- [ ] T030 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_schema_violation_missing_amount.py` — `missing_amount.json` → `schema_violation`, zero stub calls [TS-012, TS-022].
- [ ] T031 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_schema_violation_non_numeric.py` — `non_numeric_amount.json` → `schema_violation`, zero stub calls [TS-012, TS-022].
- [ ] T032 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_schema_violation_negative.py` — `negative_amount.json` → `schema_violation`, zero stub calls [TS-012, TS-022].
- [ ] T033 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_schema_violation_extra_fields.py` — `extra_fields.json` → `schema_violation` under `extra="forbid"` [TS-012].
- [ ] T034 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_hook_failure_failsafe.py` — corrupt `config/policy.json` → `HookVerdict(reject, hook_failure)`, zero stub calls, escalation emitted with `escalation_reason="hook_failure"` [TS-014].
- [ ] T035 [P] [US2] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_concurrent_policy_snapshot.py` — policy file rewritten between payload construction and `evaluate` call; assert the verdict records the snapshot version taken at invocation entry and the audit log matches [TS-015].
- [ ] T036 [P] [US2] Write AST lint test `tests/katas/kata_002_pretool_guardrails/lint/test_prompt_has_no_limit.py` that parses `katas/kata_002_pretool_guardrails/prompts.py` and fails if any string constant contains a numeric literal equal to the current `PolicyConfig.max_refund` (FR-008 machine check) [TS-007].
- [ ] T037 [P] [US2] Write AST lint test `tests/katas/kata_002_pretool_guardrails/lint/test_no_float_in_amount_path.py` that fails if `katas/kata_002_pretool_guardrails/hook.py`, `models.py`, or `runner.py` contain any `float(...)` call or `float` annotation on the amount path.
- [ ] T038 [P] [US2] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_over_limit_blocking_steps.py` binding the clauses of `specs/002-pretool-guardrails/tests/features/over_limit_blocking.feature` [TS-003, TS-004, TS-005, TS-006, TS-007, TS-008].
- [ ] T039 [P] [US2] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_edge_cases_steps.py` binding the clauses of `specs/002-pretool-guardrails/tests/features/edge_cases.feature` including the `Scenario Outline` for malformed payloads [TS-012, TS-013, TS-014, TS-015].
- [ ] T040 [P] [US2] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_contracts_payloads_steps.py` validating `ToolCallPayload`, `HookVerdict`, `StructuredError`, and `EscalationEvent` instances against their JSON Schemas [TS-016, TS-017, TS-018, TS-020, TS-022].

### Implementation for User Story 2

- [ ] T041 [US2] Wire the reject branch in `katas/kata_002_pretool_guardrails/runner.py`: on any `HookVerdict.reject`, build a `StructuredError` and inject it into the model's next context window through the Anthropic tool-result channel — never free text (FR-005, SC-003).
- [ ] T042 [US2] Emit an `EscalationEvent` via `escalation.py` for every `reason_code ∈ {policy_breach, hook_failure}` — NOT for `schema_violation` per D-007 (FR-007, Principle VI).
- [ ] T043 [US2] Ensure the refund API stub is NEVER invoked on a reject verdict — enforced by call-ordering in `runner.py` so `refund_api_stub.process_refund` is reachable only on the allow branch (FR-006, SC-002).
- [ ] T044 [US2] Record a single `kind="invocation"` and single `kind="verdict"` JSONL line per `correlation_id` in `events.jsonl`, plus a `kind="escalation"` line iff the verdict escalates — the AuditRecord invariant from `data-model.md` (FR-009).
- [ ] T045 [US2] Implement `PolicySnapshot` capture at invocation entry inside `hook.py` so the verdict and audit log both reference the same snapshot version even if `config/policy.json` is rewritten concurrently (spec Edge: concurrent policy update).

**Checkpoint**: `pytest tests/katas/kata_002_pretool_guardrails/` green for all US2 tests. TS-003, TS-004, TS-005, TS-006, TS-007, TS-008, TS-012, TS-013, TS-014, TS-015, TS-016, TS-017, TS-018, TS-020, TS-022 green. Manual: running the CLI with `over_limit.json` produces zero lines in `refund_api_calls.jsonl`.

---

## Phase 5: User Story 3 (P3) — Policy Change Takes Effect Without Retraining or Prompt Tuning

**Goal**: Updating `config/policy.json` from limit L1 to L2 (L2 < L1) rejects an amount A with L2 < A < L1 on the next invocation, with no code, prompt, or schema change.

**Independent Test**: With L1 in place and `policy_change_before.json`, observe allow. Overwrite `config/policy.json` with L2. Re-run the same payload; observe reject citing L2 in both `StructuredError.policy_snapshot_version` and `events.jsonl`.

### Tests for User Story 3

- [ ] T046 [P] [US3] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_policy_change_takes_effect.py` that: (1) writes L1 to tmp `config/policy.json`, evaluates amount A → allow; (2) overwrites with L2 (L2 < A < L1); (3) evaluates amount A again → reject with `reason_code="policy_breach"` and `policy_snapshot_version` equal to L2's version [TS-009, TS-011].
- [ ] T047 [P] [US3] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_policy_change_no_prompt_or_schema_edit.py` asserting that before/after byte-digest of `katas/kata_002_pretool_guardrails/prompts.py` and the contract schema files under `specs/002-pretool-guardrails/contracts/` is unchanged across the policy edit [TS-010].
- [ ] T048 [P] [US3] Write unit test `tests/katas/kata_002_pretool_guardrails/unit/test_policy_config_frozen.py` — mutating a loaded `PolicyConfig` instance raises, and two sequential invocations each reload a fresh instance from disk [TS-023].
- [ ] T049 [P] [US3] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_policy_hot_reload_steps.py` binding the clauses of `specs/002-pretool-guardrails/tests/features/policy_hot_reload.feature` [TS-009, TS-010, TS-011].
- [ ] T050 [P] [US3] Write step definitions in `tests/katas/kata_002_pretool_guardrails/step_defs/test_policy_config_schema_steps.py` validating `PolicyConfig` instances against `specs/002-pretool-guardrails/contracts/policy-config.schema.json` [TS-019].

### Implementation for User Story 3

- [ ] T051 [US3] Confirm the per-invocation reload path in `policy.py` is the only read site: no caching of `PolicyConfig` across invocations in `runner.py` or `hook.py` (FR-011, SC-004).
- [ ] T052 [US3] Record `policy_snapshot_version` on every `HookVerdict`, `StructuredError`, and `EscalationEvent` emitted for a given invocation — all three must carry the same version for a single `correlation_id`.

**Checkpoint**: `pytest tests/katas/kata_002_pretool_guardrails/` fully green. TS-009, TS-010, TS-011, TS-019, TS-023 green. Manual: edit `config/policy.json`, re-run CLI — behavior changes without any source edit.

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T053 [P] Write `katas/kata_002_pretool_guardrails/README.md` with the following named H2 subsections, each of which independently satisfies part of FR-013:
  - `## Objective` — kata objective and anti-pattern defended.
  - `## Architecture Walkthrough` — hook → policy → stub / escalation / audit.
  - `## Policy Schema` — documents every field of `PolicyConfig` (policy_id, policy_snapshot_version, max_refund, comparison_stance, escalation_pathway, effective_from) and their invariants; cross-links `specs/002-pretool-guardrails/contracts/policy-config.schema.json`.
  - `## Escalation Flow` — step-by-step narrative of how a `policy_breach` or `hook_failure` reject produces an `EscalationEvent`, where it is written, and what a human reviewer is expected to do with it.
  - `## Hook Contract` — the PreToolUse hook contract (input `ToolCallPayload`, verdict values, reason codes, runner exit codes); cross-referenced by T056.
  - `## Anti-Pattern Defense` — why prompt-only enforcement fails and how the AST lint locks it out.
  - `## Run Instructions` — fixture run + `LIVE_API=1` live run.
  - `## Reflection` — Principles I / II / VI / VIII per Constitution Principle VIII.
- [ ] T054 [P] Add module-level docstrings to each of `katas/kata_002_pretool_guardrails/hook.py`, `policy.py`, `models.py`, `errors.py`, `escalation.py`, `refund_api_stub.py`, `prompts.py`, `runner.py`, `events.py` — each docstring names the module's role in the kata and the FR(s) it owns.
- [ ] T055 [P] Add why-comments on non-trivial functions — specifically `RefundPolicyHook.evaluate` (why fail-closed ordering matters), `policy.load_policy` (why per-invocation reload), `refund_api_stub.process_refund` (why it records calls), and the AST lint tests (why machine-enforced, not reviewer-enforced) — each comment tied to the kata objective.
- [ ] T056 [P] Populate the `## Hook Contract` subsection authored in T053 of `katas/kata_002_pretool_guardrails/README.md` with concrete contract details:
  - Input schema reference (`ToolCallPayload`) with a link to `contracts/tool-call-payload.schema.json`.
  - Decision values (`allow` / `reject`) as pydantic `Literal[...]`.
  - Reason codes (`schema_violation` / `policy_breach` / `hook_failure`) with one-line descriptions.
  - Runner CLI exit-code semantics: `0` on `allow` + success, `10` on `schema_violation`, `11` on `policy_breach`, `20` on `hook_failure` (distinct code so ops can alert on hook failure specifically).
  - A worked example JSON payload → verdict → structured error trace.
- [ ] T057 [P] Verify `specs/002-pretool-guardrails/quickstart.md` walkthrough works end-to-end — follow each step verbatim on a clean clone; fix any drift between the doc and the implementation.
- [ ] T058 Run quickstart validation end-to-end and record the session's `runs/<session-id>/events.jsonl` + `refund_api_calls.jsonl` as evidence attached to the tasks closure note.
- [ ] T059 [P] Run `ruff check katas/kata_002_pretool_guardrails/ tests/katas/kata_002_pretool_guardrails/` and fix all violations; enforce `--select=E,F,W,I,B` minimum.
- [ ] T060 [P] Run `mypy --strict katas/kata_002_pretool_guardrails/` and eliminate all errors; no `# type: ignore` without a kata-specific reason comment.
- [ ] T061 [P] Run `pytest --cov=katas.kata_002_pretool_guardrails tests/katas/kata_002_pretool_guardrails/ --cov-report=term-missing --cov-fail-under=90` and ensure ≥ 90% line coverage; gaps must be justified in the PR description.
- [ ] T062 [P] Run `pip-audit` (or equivalent) against the kata dependency set and document any accepted advisories in `README.md`.
- [ ] T063 Regenerate the IIKit dashboard by running `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` after T058 passes.

---

## Dependencies & Execution Order

- **Phase 1 (Setup: T001–T006)** — prerequisites for everything.
- **Phase 2 (Foundational: T007–T019)** — blocks all story phases. T007 precedes T008/T009 (same file). T011 depends on T008. T016 depends on T007–T015. T017 depends on T011–T016. T018 depends on T011–T017.
- **Phase 3 (US1: T020–T024)** — depends on Phase 2 complete.
- **Phase 4 (US2: T025–T045)** — depends on Phase 2 complete; can start in parallel with Phase 3 once foundation is green, but T041–T045 depend on T023 landing first (shared `runner.py`).
- **Phase 5 (US3: T046–T052)** — depends on Phase 2 complete; T051–T052 touch `runner.py` and `hook.py` and should land after US1+US2 implementation tasks to avoid merge churn.
- **Final Phase (T053–T063)** — depends on all story phases green. T058 depends on T057. T063 depends on T058.

---

## Parallel Opportunities

- All [P] tasks in Phase 1 (T002–T006) can run simultaneously.
- Foundation models (T008, T009, T010) can be authored concurrently after T007 lands.
- All [P] test authoring tasks within a single story phase run in parallel (they touch different test files).
- US1 unit + step-def tests (T020, T021, T022) are fully independent.
- US2 unit tests (T025–T037) are fully independent — 13 parallel agents possible.
- US3 unit + step-def tests (T046–T050) are fully independent.
- Polish tasks T053–T062 are fully parallel (distinct files, distinct tools); only T058 and T063 serialize at the end.

---

## Implementation Strategy (MVP scope)

**MVP = Phase 1 + Phase 2 + Phase 3 (US1) green.** At that point the kata demonstrates a working PreToolUse hook on the happy path: an in-policy refund flows through the hook, reaches the stub, and returns a real success outcome. The anti-pattern defense is NOT yet installed — that lands in Phase 4.

Full kata value arrives at end of Phase 4 (US2) — this is where the guardrail becomes physically unbypassable, which is the stated purpose of this kata. Phase 5 (US3) is the operational story: policy is data, not code.

Suggested ordering for a single engineer: T001 → T007 → T016 → T023 (smoke) → T025 → T041 → T046 → T051 → polish. Parallelize test authoring tasks as a second agent.

---

## Notes

- Every TS-NNN from `specs/002-pretool-guardrails/tests/features/*.feature` is cited at least once in this file: TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007, TS-008, TS-009, TS-010, TS-011, TS-012, TS-013, TS-014, TS-015, TS-016, TS-017, TS-018, TS-019, TS-020, TS-021, TS-022, TS-023.
- No task rewrites `.feature` files directly — per `.tessl/RULES.md` assertion integrity, regenerate via `/iikit-04-testify` if scenarios need to change.
- Runner CLI module path is `katas.kata_002_pretool_guardrails.runner`. The canonical Python-importable package name is `kata_002_pretool_guardrails` (Python disallows a leading digit in module names); this decision is pinned in plan.md §Source Code and is not optional at implementation time.
- No external secrets required; `LIVE_API=1` is opt-in and gated in `conftest.py`.
- No pnpm here — this kata is Python-only; the user preference for pnpm applies to JS tooling elsewhere.
