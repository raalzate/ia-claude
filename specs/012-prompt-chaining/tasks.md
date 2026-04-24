# Tasks: Multi-Pass Prompt Chaining

**Input**: Design documents from `/specs/012-prompt-chaining/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-005"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/012_prompt_chaining/__init__.py` (empty marker) and mirror test package `tests/katas/012_prompt_chaining/__init__.py`
- [ ] T002 Create stages sub-package marker `katas/012_prompt_chaining/stages/__init__.py` (empty) so appending `SecurityScanStage` later is a pure file-add (FR-005 / SC-004)
- [ ] T003 [P] Ensure `pyproject.toml` at repo root declares Python 3.11+ and the `[dev]` extra with `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, `tiktoken`, `jsonschema` per plan.md Technical Context (extend only — do not mutate existing kata entries)
- [ ] T004 [P] Add `runs/` to `.gitignore` if not already present (per plan.md: every `runs/<task_id>/` is gitignored)
- [ ] T005 [P] Create `tests/katas/012_prompt_chaining/conftest.py` stub declaring the `pytest-bdd` features directory `tests/katas/012_prompt_chaining/features/`, exposing a fixture-corpus loader helper, and gating live-SDK paths behind a `LIVE_API` env var
- [ ] T006 [P] Create empty sub-package markers `tests/katas/012_prompt_chaining/step_defs/__init__.py`, `tests/katas/012_prompt_chaining/unit/__init__.py`, `tests/katas/012_prompt_chaining/contract/__init__.py`, `tests/katas/012_prompt_chaining/integration/__init__.py`

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, exception types, injectable SDK client, token counter, contract-schema loader. No story label.

- [ ] T007 [P] Implement shared pydantic v2 entities in `katas/012_prompt_chaining/payloads.py`: `FileRef`, `StageDefinition`, `MacroTask`, `IntermediatePayload` header, `PerFileReport`, `LocalFinding`, `PerFileAnalysisFailure`, `PerFileBundle`, `IntegrationFinding`, `FinalReport`, `SecurityFinding`, `SecurityReport`, `HaltRecord`, `ChainRun` — all with `extra="forbid"` per `data-model.md`
- [ ] T008 [P] Implement exception hierarchy in `katas/012_prompt_chaining/errors.py`: `ChainHalt` base, `MalformedIntermediatePayload(stage_index, stage_name, validation_errors, payload_path)`, and orchestrator-wide `PerFileAnalysisHalt` (cause=`per_file_analysis_failure`) — all carry structured fields, never free prose
- [ ] T009 [P] Implement `katas/012_prompt_chaining/budget.py` with `StageBudgetExceeded(stage_index, stage_name, declared_budget, measured_tokens, overflow)` exception and a `count_tokens(text: str) -> int` helper backed by `tiktoken` (local, offline); helper docstring cites FR-003 / SC-002
- [ ] T010 [P] Implement thin injectable Anthropic client wrapper in `katas/012_prompt_chaining/client.py` exposing a single `send(stage_name, prompt) -> RawResponse` surface; `LiveClient` behind `LIVE_API=1`, `RecordedClient` reads `tests/katas/012_prompt_chaining/fixtures/<name>.json`
- [ ] T011 Implement `ChainStage` abstract base in `katas/012_prompt_chaining/stages/base.py` with fields `name`, `responsibility`, `input_schema`, `output_schema`, `max_prompt_tokens`, and `run(input: BaseModel) -> BaseModel` abstractmethod — input/output validation hooks invoke `model_validate` and raise `MalformedIntermediatePayload` on failure (FR-004, Principle II)
- [ ] T012 Implement the `Chain` orchestrator in `katas/012_prompt_chaining/chain.py`: ordered list of `ChainStage`, per-stage boundary validation, JSON persistence to `runs/<task_id>/stage-<n>.json`, token-budget gate firing BEFORE SDK call, fail-loud halts returning a populated `ChainRun.halted: HaltRecord` — never silent skip (FR-001, FR-002, FR-004, FR-008)
- [ ] T013 [P] Implement contract-schema loader helper in `tests/katas/012_prompt_chaining/conftest.py::load_contract_schema(name)` resolving paths under `specs/012-prompt-chaining/contracts/` (macro-task, stage-definition, intermediate-payload, final-report)

**Checkpoint**: Foundation ready — payload models, exception types, token-budget gate, injectable client, `ChainStage` base, and `Chain` orchestrator are all in place. Concrete stages can now be implemented against them.

---

## Phase 3: User Story 1 - Chained Audit of a Multi-File Pull Request (Priority: P1) MVP

**Goal**: A practitioner feeds a 15-file PR into the workflow; the chain emits exactly 15 per-file reports plus one integration-only report, kept distinct and traceable to the stage that produced them. The integration pass reads accumulated per-file reports (never raw corpus) and evaluates inter-module incoherence only.

**Independent Test**: Run the kata harness against `chain_happy_path.json` over `corpus_15_files/` and assert: 15 `PerFileReport` entries in `stage-0.json`, one `FinalReport` in `stage-1.json`, no `FinalReport` finding duplicates any upstream `LocalFinding`, every payload carries `stage_index` + `stage_name`, and every persisted JSON validates against the Phase-1 contract schemas.

### Tests for User Story 1

- [ ] T014 [P] [US1] Create 15-file PR fixture corpus at `tests/katas/012_prompt_chaining/fixtures/corpus_15_files/` — 15 small source files with deliberately planted local issues plus at least one cross-module incoherence
- [ ] T015 [P] [US1] Record fixture session `tests/katas/012_prompt_chaining/fixtures/chain_happy_path.json` — per-file + integration stages succeed over `corpus_15_files/`
- [ ] T016 [P] [US1] Copy/symlink `specs/012-prompt-chaining/tests/features/chained_multi_file_audit.feature` to `tests/katas/012_prompt_chaining/features/chained_multi_file_audit.feature` so pytest-bdd can discover it
- [ ] T017 [US1] Implement BDD step definitions for [TS-001, TS-002, TS-003, TS-004, TS-005] in `tests/katas/012_prompt_chaining/step_defs/test_chained_multi_file_audit_steps.py` — steps wire to `chain_happy_path.json`, run the orchestrator, assert artifact counts, traceability fields, and that the integration stage prompt contains accumulated per-file reports but no raw corpus content
- [ ] T018 [P] [US1] Add unit test `tests/katas/012_prompt_chaining/unit/test_chain_orchestration.py` asserting ordered stage execution and that `runs/<task_id>/stage-<n>.json` is written per completed stage with `stage_index` equal to its position
- [ ] T019 [P] [US1] Add unit test `tests/katas/012_prompt_chaining/unit/test_stage_traceability.py` asserting every persisted `IntermediatePayload` carries a non-null `stage_index` + `stage_name`; every `LocalFinding.originating_stage == "per_file"`; every `IntegrationFinding.originating_stage == "integration"` and `len(involved_files) >= 2` (FR-007, US1-AS3)
- [ ] T020 [P] [US1] Add contract test `tests/katas/012_prompt_chaining/contract/test_schema_validation.py` validating a sample `IntermediatePayload` and `FinalReport` against `specs/012-prompt-chaining/contracts/intermediate-payload.schema.json` and `final-report.schema.json`; also validate a sample `MacroTask` against `macro-task.schema.json` and a `StageDefinition` against `stage-definition.schema.json`

### Implementation for User Story 1

- [ ] T021 [US1] Implement `PerFileAnalysisStage` in `katas/012_prompt_chaining/stages/per_file.py`: `input_schema=MacroTask`, `output_schema=PerFileBundle`; prompt template restricted to local, file-scoped analysis only (no cross-file language) per FR-003; emits one `PerFileReport` per `FileRef`, appends `PerFileAnalysisFailure` entries on per-file errors (never silent skip — FR-008)
- [ ] T022 [US1] Implement `IntegrationAnalysisStage` in `katas/012_prompt_chaining/stages/integration.py`: `input_schema=PerFileBundle`, `output_schema=FinalReport`; prompt template consumes ONLY the accumulated per-file bundle and carries an explicit instruction to evaluate inter-module incoherences exclusively (FR-003, US1-AS2); validator cross-checks `FinalReport` finding IDs against upstream `PerFileBundle.reports` to reject duplicates (US1-AS3)
- [ ] T023 [US1] Wire the MVP chain in `katas/012_prompt_chaining/chain.py::default_chain()` returning `[PerFileAnalysisStage(), IntegrationAnalysisStage()]` with declared token budgets matching `StageDefinition.max_prompt_tokens`; emit `runs/<task_id>/stage-0.json`, `stage-1.json`, and a `runs/<task_id>/final.json` mirror of the `FinalReport` body
- [ ] T024 [US1] Implement the CLI entrypoint `katas/012_prompt_chaining/runner.py` with `python -m katas.012_prompt_chaining.runner --pr-dir ... --stages per_file_analysis,integration_analysis`; reads `LIVE_API` env to choose `LiveClient` vs `RecordedClient`; prints the `runs/<task_id>/` path on exit

**Checkpoint**: US1 fully functional — practitioner can run the kata against `corpus_15_files/`, get 15 per-file reports plus one integration report, every payload schema-validates, every finding is traceable to its originating stage, no cross-file re-analysis leaks into the integration report. BDD scenarios @TS-001, @TS-002, @TS-003, @TS-004, @TS-005 all pass.

---

## Phase 4: User Story 2 - Baseline Comparison Against the Monolithic Anti-Pattern (Priority: P2)

**Goal**: A practitioner runs the monolithic baseline (one prompt asking for both local + integration analysis) on the same 15-file corpus, then compares it against the chained run. Delta comparison shows the chain's finding coverage exceeds the baseline by at least 25 %. Every stage's prompt stays under its declared token budget; over-budget prompts halt with a labeled `StageBudgetExceeded`.

**Independent Test**: Run both modes against `corpus_15_files/`; produce a delta report classifying findings by originating mode (chain vs baseline); assert `len(chain_findings) >= 1.25 * len(baseline_findings)`. Run the `oversize_per_file_report.json` fixture and assert `StageBudgetExceeded` is raised with fully populated fields and no SDK call fires.

### Tests for User Story 2

- [ ] T025 [P] [US2] Record fixture `tests/katas/012_prompt_chaining/fixtures/baseline_monolithic.json` — single monolithic-prompt response over `corpus_15_files/` asking for both local and integration analysis
- [ ] T026 [P] [US2] Record fixture `tests/katas/012_prompt_chaining/fixtures/oversize_per_file_report.json` — stage-0 `PerFileBundle` whose aggregated size forces the integration-stage assembled prompt over its declared `max_prompt_tokens`
- [ ] T027 [P] [US2] Copy/symlink `specs/012-prompt-chaining/tests/features/baseline_monolithic_comparison.feature` to `tests/katas/012_prompt_chaining/features/baseline_monolithic_comparison.feature`
- [ ] T028 [US2] Implement BDD step definitions for [TS-006, TS-007, TS-008, TS-009, TS-010] in `tests/katas/012_prompt_chaining/step_defs/test_baseline_monolithic_comparison_steps.py` — steps run both modes, perform the delta comparison, exercise the `Scenario Outline` over `PerFileAnalysisStage` / `IntegrationAnalysisStage`, and assert that `StageBudgetExceeded` fires BEFORE any SDK call on the oversize fixture
- [ ] T029 [P] [US2] Add integration test `tests/katas/012_prompt_chaining/integration/test_baseline_vs_chain.py` — loads both fixtures, computes distinct-issue counts per mode, asserts the ≥ 25 % delta threshold (SC-001), classifies findings by originating mode (chain / baseline), and enumerates mode-unique findings separately
- [ ] T030 [P] [US2] Add unit test `tests/katas/012_prompt_chaining/unit/test_budget_gate.py` — synthetic stages with small `max_prompt_tokens`; assert that `StageBudgetExceeded` is raised BEFORE `client.send` is called, that `measured_tokens > declared_budget`, and that `overflow == measured_tokens - declared_budget`

### Implementation for User Story 2

- [ ] T031 [US2] Implement the monolithic baseline path in `katas/012_prompt_chaining/chain.py::run_baseline(task)` — single prompt, single response, single artifact persisted to `runs/<task_id>/baseline.json`; artifact is NOT decomposed into per-stage files (TS-006)
- [ ] T032 [US2] Implement delta-report helper in `katas/012_prompt_chaining/chain.py::compare_coverage(chain_run, baseline_artifact) -> DeltaReport` — every finding is tagged with its originating mode (`"chain"` | `"baseline"`); mode-unique findings are enumerated separately (TS-008)
- [ ] T033 [US2] In `katas/012_prompt_chaining/chain.py`, enforce the token-budget gate at stage boundary: call `budget.count_tokens(prompt)`, compare to `stage.max_prompt_tokens`, raise `StageBudgetExceeded` with all five structured fields before any `client.send(...)` — chain halts with `HaltRecord(cause="stage_budget_exceeded")` and NO `FinalReport` is produced (FR-003, SC-002)

**Checkpoint**: US2 fully functional — baseline artifact produced and gitignored under `runs/`; delta comparison shows the chain exceeds the baseline by the declared margin; oversize prompt halts loud with a fully populated `StageBudgetExceeded`; every stage prompt on the 15-file fixture stays under budget. BDD scenarios @TS-006, @TS-007, @TS-008, @TS-009, @TS-010 all pass.

---

## Phase 5: User Story 3 - Extending the Chain With an Additional Stage (Priority: P3)

**Goal**: A practitioner appends `SecurityScanStage` downstream of `IntegrationAnalysisStage`. The new stage consumes the existing `PerFileBundle` and emits a `SecurityReport` persisted to `stage-2.json`. Adding the stage modifies zero pre-existing files — verified by diff. Malformed intermediate payloads halt loud with `MalformedIntermediatePayload`. A single per-file analysis failure surfaces rather than being absorbed.

**Independent Test**: Diff the working tree before and after adding `SecurityScanStage` against the pre-extension git revision; assert zero changes in `stages/per_file.py`, `stages/integration.py`, `stages/base.py`, and every earlier `StageDefinition`. Run `malformed_payload.json` and `single_file_failure.json` fixtures; assert the declared exception halts each run with the correct `HaltRecord.cause`.

### Tests for User Story 3

- [ ] T034 [P] [US3] Record fixture `tests/katas/012_prompt_chaining/fixtures/malformed_payload.json` — stage-0 `PerFileBundle` missing a required field (e.g. a `PerFileReport` without `file_content_hash`)
- [ ] T035 [P] [US3] Record fixture `tests/katas/012_prompt_chaining/fixtures/single_file_failure.json` — one `PerFileReport` replaced by a `PerFileAnalysisFailure(error_category="parse_error")`; remaining 14 reports populate normally
- [ ] T036 [P] [US3] Copy/symlink `specs/012-prompt-chaining/tests/features/extensible_chain_stage.feature` to `tests/katas/012_prompt_chaining/features/extensible_chain_stage.feature`
- [ ] T037 [US3] Implement BDD step definitions for [TS-011, TS-012, TS-013, TS-014, TS-015] in `tests/katas/012_prompt_chaining/step_defs/test_extensible_chain_stage_steps.py` — steps append `SecurityScanStage`, diff the working tree, drive the `malformed_payload` and `single_file_failure` fixtures, and serialize the `StageDefinition` list pre/post extension for byte-identity comparison on earlier entries
- [ ] T038 [P] [US3] Add integration test `tests/katas/012_prompt_chaining/integration/test_chain_extension_diff.py` — records a git revision (or a hash snapshot of file bytes) before adding `SecurityScanStage`; after addition, asserts `stages/per_file.py`, `stages/integration.py`, `stages/base.py`, and every earlier stage's `output_schema` are byte-identical (FR-005, SC-004). Scope note: because prompt templates are inlined inside the stage modules (`stages/per_file.py`, `stages/integration.py`) rather than extracted to a dedicated file, the byte-identity check on those modules necessarily covers the prompt templates — any text change to an earlier prompt template fails this diff check.
- [ ] T039 [P] [US3] Add unit test `tests/katas/012_prompt_chaining/unit/test_malformed_payload.py` — feeds the malformed fixture into the orchestrator; asserts `MalformedIntermediatePayload` is raised with populated `stage_index`, `stage_name`, `validation_errors`, `payload_path`; asserts no downstream stage is dispatched (FR-004, SC-003)
- [ ] T040 [P] [US3] Add unit test `tests/katas/012_prompt_chaining/unit/test_per_file_failure.py` — feeds `single_file_failure.json`; asserts `PerFileBundle.failures` is non-empty; asserts `IntegrationAnalysisStage.run` refuses to execute while any failure entry is present; asserts `ChainRun.halted.cause == "per_file_analysis_failure"` (FR-008, SC-003)

### Implementation for User Story 3

- [ ] T041 [US3] Implement `SecurityScanStage` as a PURE FILE-ADD at `katas/012_prompt_chaining/stages/security.py`: `input_schema=PerFileBundle`, `output_schema=SecurityReport`; every `SecurityFinding.originating_stage == "security"`; no edits to `stages/per_file.py`, `stages/integration.py`, or `stages/base.py` (FR-005, SC-004)
- [ ] T042 [US3] Expose an extended chain factory in `katas/012_prompt_chaining/chain.py::extended_chain()` returning `[PerFileAnalysisStage(), IntegrationAnalysisStage(), SecurityScanStage()]`; runner accepts `--stages per_file_analysis,integration_analysis,security_scan` and persists `stage-2.json`
- [ ] T043 [US3] In `katas/012_prompt_chaining/stages/integration.py`, add the pre-run guard: if any `PerFileBundle.failures` entry is present, refuse to run and return a `HaltRecord(cause="per_file_analysis_failure", stage_index=..., detail=...)` through the orchestrator — integration prompt MUST NOT be issued (FR-008)
- [ ] T044 [US3] In `katas/012_prompt_chaining/chain.py`, tighten the inter-stage boundary reader so that reading `runs/<task_id>/stage-<n>.json` runs `model_validate` against the downstream stage's `input_schema` and raises `MalformedIntermediatePayload(payload_path=...)` on failure — no best-effort parsing (FR-004)

**Checkpoint**: US3 fully functional — `SecurityScanStage` appended without mutating any earlier stage file (diff-verified); malformed payloads halt loud; per-file failures surface instead of being absorbed; `StageDefinition` byte-identity preserved for pre-existing stages. BDD scenarios @TS-011, @TS-012, @TS-013, @TS-014, @TS-015 all pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T045 [P] Write `katas/012_prompt_chaining/README.md` covering (Principle VIII): kata objective (avoid cognitive saturation via multi-pass decomposition), chain architecture walkthrough (`Chain` → `PerFileAnalysisStage` → `IntegrationAnalysisStage` → optional `SecurityScanStage`, with `runs/<task_id>/stage-<n>.json` as the audit trail), handoff contract (inter-step pydantic schema at every boundary — `MacroTask` → `PerFileBundle` → `FinalReport` / `SecurityReport`), failure isolation (how `StageBudgetExceeded`, `MalformedIntermediatePayload`, and `PerFileAnalysisFailure` fail loud instead of silently degrading), anti-pattern defense (why the monolithic baseline is measurably worse, with the delta figure), run instructions mirroring `quickstart.md`, and a Reflection section answering the two reflection prompts from `quickstart.md`
- [ ] T046 [P] Add module-level docstrings to each of `katas/012_prompt_chaining/chain.py`, `payloads.py`, `errors.py`, `budget.py`, `client.py`, `runner.py`, `stages/base.py`, `stages/per_file.py`, `stages/integration.py`, `stages/security.py` — each docstring explains the module's role in the multi-pass decomposition and cites the FR / SC it serves
- [ ] T047 [P] Add why-comments (per Constitution Principle VIII) on every non-trivial function and class across `katas/012_prompt_chaining/**/*.py` — comments tie the code choice back to the saturation anti-pattern (e.g. "integration stage reads ONLY the per-file bundle because feeding raw files would recreate the saturation the chain is designed to avoid")
- [ ] T048 [P] Document the inter-step payload schema and failure-isolation model in a dedicated `README.md` section listing: header fields (`task_id`, `stage_index`, `stage_name`, `emitted_at`), stage-specific body classes, halt-record taxonomy (`stage_budget_exceeded` | `malformed_intermediate_payload` | `per_file_analysis_failure`), and the JSON-schema contract references under `specs/012-prompt-chaining/contracts/`
- [ ] T049 [P] Verify `specs/012-prompt-chaining/quickstart.md` usage walkthrough is accurate against the final file layout; update paths, `--stages` names, or commands if drift was introduced during implementation
- [ ] T050 Run `quickstart.md` end-to-end: `pytest tests/katas/012_prompt_chaining -v` against fixtures, then optional `LIVE_API=1 python -m katas.012_prompt_chaining.runner --pr-dir tests/katas/012_prompt_chaining/fixtures/corpus_15_files/ --stages per_file_analysis,integration_analysis` smoke run; record both outputs as part of PR evidence
- [ ] T051 [P] Run `ruff check katas/012_prompt_chaining tests/katas/012_prompt_chaining` and `black --check` over the same paths; fix any findings
- [ ] T052 [P] Produce a coverage report (`pytest --cov=katas.012_prompt_chaining`) and archive it at `runs/coverage/012_prompt_chaining.txt`; target ≥ 90 % line coverage on `chain.py` and each concrete stage
- [ ] T053 Final self-audit: read the emitted `runs/<task_id>/stage-*.json` from the happy-path run and confirm it satisfies SC-001, SC-002, SC-003, SC-004 — record the check in the PR description, explicitly quoting the delta figure, the per-stage token counts, and the extension-diff result

---

## Dependencies & Execution Order

**Phase order (strict):** Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6.

**Within-phase dependencies:**
- Phase 1: T003, T004 are [P] (different config files); T001, T002 are ordering-neutral but must precede any import from `katas/012_prompt_chaining/`; T005, T006 are [P] once T001 exists.
- Phase 2: T007, T008, T009, T010, T013 are all [P] (distinct modules). T011 depends on T007 + T008. T012 depends on T007 + T008 + T009 + T011.
- Phase 3: T014, T015, T016 are [P]. T017 depends on T012 + T016 + T014 + T015 + T021 + T022 + T023. T018, T019, T020 are [P] once T007 + T012 exist. T021 depends on T011. T022 depends on T011 + T021 (schema cross-check against upstream bundle). T023 depends on T021 + T022 + T012. T024 depends on T023 + T010.
- Phase 4: T025, T026, T027 are [P]. T028 depends on T027 + T031 + T032 + T033 + fixtures. T029 depends on T031 + T023. T030 depends on T009 + T011. T031 depends on T012 + T010. T032 depends on T031 + T023. T033 depends on T012 + T009.
- Phase 5: T034, T035, T036 are [P]. T037 depends on T036 + T041 + T042 + T043 + T044 + fixtures. T038 depends on T041. T039 depends on T044 + T012. T040 depends on T043 + T022. T041 is a pure file-add depending only on T011 + T007. T042 depends on T041 + T023. T043 depends on T022. T044 depends on T012.
- Phase 6: T045, T046, T047, T048, T049, T051, T052 are [P]. T050 depends on every prior phase complete. T053 depends on T050.

**Story dependencies:**
- US2 compares against the chain built in US1 — cannot start until T021–T023 land.
- US3 extends the chain built in US1/US2 — cannot validate the zero-edit property (SC-004) until earlier stage files are committed at a known revision (pre-condition of `extensible_chain_stage.feature` Background).

---

## Parallel Opportunities

**Phase 1 [P]:** T003, T004, T005, T006 (different config / test-scaffolding files).

**Phase 2 [P]:** T007, T008, T009, T010, T013 (distinct modules, no shared state).

**Phase 3 [P]:** fixture + feature batch — T014, T015, T016 in parallel; unit + contract tests T018, T019, T020 in parallel once T007 + T012 exist. T017 gates on implementation (T021–T023).

**Phase 4 [P]:** fixture + feature batch — T025, T026, T027 in parallel. T029, T030 parallel once the budget gate (T033) and baseline path (T031) exist.

**Phase 5 [P]:** fixture + feature batch — T034, T035, T036 in parallel. T038, T039, T040 parallel once T041–T044 are landed.

**Phase 6 [P]:** T045, T046, T047, T048, T049, T051, T052 all in parallel.

---

## Implementation Strategy

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1). At this point the kata demonstrates Principle III (Context Economy) end-to-end: a 15-file audit decomposed into 15 per-file reports plus one integration-only report, every payload schema-validated, every finding traceable to its originating stage. This is already a credible kata deliverable.
- **Incremental delivery**: land Phase 4 (US2) next — adds the monolithic baseline and the SC-001 delta measurement that empirically justifies the chain's existence, plus the token-budget gate (SC-002). Then Phase 5 (US3) proves forward-extensibility (SC-004) and fail-loud error surfaces (SC-003). Phase 6 documents and polishes.
- **Blast radius**: every phase is gated by BDD scenarios failing first (Constitution V — TDD); Phase 6's `quickstart.md` run is the final acceptance gate. The extension-diff test in T038 is the irreversible structural guard against regression into an edit-existing-stages shortcut — keep it green after T041.

---

## Notes

- `[P]` = different files, no shared state, no ordering dependency.
- Each user story is independently testable — US1 against `chain_happy_path.json` over `corpus_15_files/`, US2 against `baseline_monolithic.json` + `oversize_per_file_report.json`, US3 against `malformed_payload.json` + `single_file_failure.json` plus the extension diff.
- Verify every `.feature` scenario fails before writing the matching production code (Constitution V — TDD). Do NOT make tests pass by editing assertions; fix the chain orchestrator or the concrete stage instead (assertion-integrity rule).
- The integration stage MUST read ONLY the `PerFileBundle` — never the raw corpus. This is the teachable core of the kata; any shortcut that reintroduces raw-file context into the integration prompt resurrects the saturation anti-pattern the chain was built to avoid.
- Every `runs/<task_id>/stage-<n>.json` is the audit trail for Principle VII — keep it deterministic (stable key ordering, UTC timestamps) so the extension-diff and delta-comparison tests stay byte-reproducible.
