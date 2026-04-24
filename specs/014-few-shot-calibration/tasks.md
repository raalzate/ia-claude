# Tasks: Few-Shot Calibration for Edge Cases

**Input**: Design documents from `/specs/014-few-shot-calibration/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-005"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/014_few_shot_calibration/__init__.py` (empty marker) and mirror test package `tests/katas/014_few_shot_calibration/__init__.py`
- [ ] T002 [P] Ensure `pyproject.toml` at repo root declares the `[dev]` extra with `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd` per plan.md Technical Context (shared with katas 001–013; no-op if already present)
- [ ] T003 [P] Configure lint/format tooling (`ruff` + `black`) in `pyproject.toml` to cover `katas/014_few_shot_calibration/` and `tests/katas/014_few_shot_calibration/`; exclude `runs/` and `tests/katas/014_few_shot_calibration/fixtures/`
- [ ] T004 [P] Confirm `runs/` is in `.gitignore` so per-session calibration reports and JSONL traces are not committed (plan.md Storage)
- [ ] T005 [P] Create `tests/katas/014_few_shot_calibration/conftest.py` stub declaring the `pytest-bdd` features directory `tests/katas/014_few_shot_calibration/features/` and exposing a fixture-session loader helper `load_contract_schema(name)` that resolves paths under `specs/014-few-shot-calibration/contracts/`

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, JSON schemas, injectable SDK client, example-set registry, contradiction validators, measurement harness scaffolding. No story label.

- [ ] T006 [P] Implement shared pydantic v2 entities in `katas/014_few_shot_calibration/models.py`: `ExamplePair`, `ExampleSet`, `FewShotPrompt`, `CalibrationReport`, `ConsistencyMetric`, plus the `ContradictoryExamplesError` exception — per `data-model.md` (schema-enforced boundaries, Principle II)
- [ ] T007 [P] Wire the 2–4 size invariant onto `ExampleSet` in `katas/014_few_shot_calibration/models.py` as a pydantic validator that raises at construction — no silent truncation (FR-006); add the reserved `set_id = "zero_shot"` constant used by the zero-shot control arm (FR-003, SC-004)
- [ ] T008 [P] Reference Phase-1 JSON schemas from tests by extending `tests/katas/014_few_shot_calibration/conftest.py::load_contract_schema(name)` to resolve `example-pair.schema.json`, `example-set.schema.json`, `calibration-report.schema.json`, `consistency-metric.schema.json` under `specs/014-few-shot-calibration/contracts/`
- [ ] T009 [P] Implement the thin injectable Anthropic client wrapper in `katas/014_few_shot_calibration/client.py` exposing a single `send(prompt) -> RawResponse` surface; real SDK behind a `LiveClient` gated by `LIVE_API=1`, fixture replay behind a `RecordedClient` that reads `tests/katas/014_few_shot_calibration/fixtures/*.json`
- [ ] T010 [P] Implement the contradiction validator in `katas/014_few_shot_calibration/validators.py` using the canonical-normalization function declared in research.md (lowercasing + whitespace collapse); raise `ContradictoryExamplesError` when any two pairs share a normalized input but disagree on a same-field output value (FR-005, SC-003)
- [ ] T011 [P] Implement the size-guard and leakage-candidate flagger in `katas/014_few_shot_calibration/validators.py`: flag example pairs whose serialized length exceeds the declared prompt-budget threshold (edge case #4) and flag example pairs marked as leakage-candidate (edge case #2) — flag, do not fatally reject (plan.md Constraints)
- [ ] T012 [P] Implement `ExampleSetRegistry` in `katas/014_few_shot_calibration/registry.py`: in-memory `dict[set_id, ExampleSet]` with `register`, `get(set_id)`, `rotate_all()` iteration; every lookup returns a set whose `set_id` will be stamped onto the run (FR-003, SC-004)
- [ ] T013 [P] Implement coverage-validation on `ExampleSetRegistry` in `katas/014_few_shot_calibration/registry.py`: `validate_coverage(set_id, task_id)` refuses to execute a calibrated run when the declared edge-case distribution is not covered; surfaces a labeled `MissingCoverageError` (FR-002)
- [ ] T014 [P] Implement `FewShotBuilder` in `katas/014_few_shot_calibration/builder.py`: composes `system_instructions + examples_block + target_input` in **static-prefix-first** order so the fixed section is Kata-10 prefix-cache-friendly (Constitution III; plan.md Architecture)
- [ ] T015 Wire the calibration harness scaffold in `katas/014_few_shot_calibration/harness.py`: per-trial `ConsistencyMetric` emission, per-session `CalibrationReport` aggregation, JSONL trace writer at `runs/<session-id>/outputs.jsonl`, and report writer at `runs/<session-id>/calibration.json` — depends on T006, T009, T012, T014

**Checkpoint**: Foundation ready — models, contract schemas, injectable client, example-set registry, contradiction + size validators, builder, and measurement harness scaffolding all in place. Story-level calibration logic can now be implemented against them.

---

## Phase 3: User Story 1 - Zero-Shot Baseline vs. Calibrated Few-Shot on an Edge-Case Corpus (Priority: P1) MVP

**Goal**: A practitioner runs an edge-case corpus (informal culinary measures) under zero-shot and then again with a 2–4 pair calibrated example set; the system records both inconsistency rates, the delta, and the active example set id on the calibration report, proving a ≥ 40% relative reduction (FR-001, FR-003, FR-004, SC-001, SC-002, SC-004).

**Independent Test**: Run the harness against `corpus_informal_measures.json` once zero-shot (with explicit acknowledgement) and once with `example_set_calibrated.json`; assert the produced `calibration.json` shows `inconsistency_rate` reduced by ≥ 40% relative and both runs are traceable to their `set_id`.

### Tests for User Story 1

- [ ] T016 [P] [US1] Record fixture corpus `tests/katas/014_few_shot_calibration/fixtures/corpus_informal_measures.json` (10 informal-measure inputs: "a pinch", "a handful", "a splash", etc., with labeled expected structured outputs)
- [ ] T017 [P] [US1] Record fixture example set `tests/katas/014_few_shot_calibration/fixtures/example_set_calibrated.json` (the canonical 3-pair set for `informal_measures`)
- [ ] T018 [P] [US1] Record recorded-client response fixtures `tests/katas/014_few_shot_calibration/fixtures/responses_zero_shot.json` and `tests/katas/014_few_shot_calibration/fixtures/responses_few_shot_calibrated.json` covering the 10-item corpus for both arms so the offline suite is deterministic
- [ ] T019 [P] [US1] Copy/symlink `specs/014-few-shot-calibration/tests/features/calibrated_few_shot_vs_zero_shot.feature` to `tests/katas/014_few_shot_calibration/features/calibrated_few_shot_vs_zero_shot.feature` so pytest-bdd can discover it
- [ ] T020 [US1] Implement BDD step definitions for [TS-001] in `tests/katas/014_few_shot_calibration/step_defs/test_calibrated_few_shot_vs_zero_shot_steps.py` — asserts the zero-shot baseline run records the corpus inconsistency rate and stamps the reserved `"zero_shot"` example set id on the report
- [ ] T021 [US1] Implement BDD step definitions for [TS-002] in `tests/katas/014_few_shot_calibration/step_defs/test_calibrated_few_shot_vs_zero_shot_steps.py` — asserts the few-shot run records post-calibration rate, the delta against baseline, and a ≥ 40% relative reduction
- [ ] T022 [US1] Implement BDD step definitions for [TS-003] in `tests/katas/014_few_shot_calibration/step_defs/test_calibrated_few_shot_vs_zero_shot_steps.py` — asserts the active example set id is stamped on every run and retrievable for 100% of recorded runs
- [ ] T023 [US1] Implement BDD step definitions for [TS-004] in `tests/katas/014_few_shot_calibration/step_defs/test_calibrated_few_shot_vs_zero_shot_steps.py` — asserts 100% of calibrated outputs validate against the declared task schema and schema-invalid outputs count toward the inconsistency rate (SC-002)
- [ ] T024 [P] [US1] Add unit test `tests/katas/014_few_shot_calibration/unit/test_harness_metric.py` computing `inconsistency_rate`, `schema_violation_rate`, and the zero-shot→few-shot delta over synthetic `ConsistencyMetric` sequences (SC-001, SC-002)
- [ ] T025 [P] [US1] Add unit test `tests/katas/014_few_shot_calibration/unit/test_builder_prefix_suffix_order.py` asserting `FewShotBuilder` emits `system_instructions + examples_block` as a contiguous prefix and `target_input` as the suffix — cross-ref Kata 10 prefix cache (Constitution III)
- [ ] T026 [P] [US1] Add unit test `tests/katas/014_few_shot_calibration/unit/test_report_shape.py` asserting every emitted `CalibrationReport` validates against `specs/014-few-shot-calibration/contracts/calibration-report.schema.json` and every `ConsistencyMetric` validates against `consistency-metric.schema.json`

### Implementation for User Story 1

- [ ] T027 [US1] Implement zero-shot arm in `katas/014_few_shot_calibration/harness.py::run_zero_shot(task_id, corpus, *, acknowledge_zero_shot)` — builds a prompt without examples, calls the recorded/live client per corpus input, collects `ConsistencyMetric` per trial, and writes a `CalibrationReport` with `set_id="zero_shot"` (FR-001, FR-003, SC-004)
- [ ] T027a [US1] Implement the FR-001 precondition gate in `katas/014_few_shot_calibration/harness.py::should_calibrate(baseline_report) -> (bool, str)` — returns `(False, "CalibrationNotIndicated")` when the zero-shot `inconsistency_rate < 0.20`, else `(True, "")`; the few-shot arm MUST NOT run when the gate returns `False` and the `CalibrationReport.skipped_reason` MUST be stamped with the labeled reason (FR-001, plan.md "Zero-shot precondition gate")
- [ ] T028 [US1] Implement few-shot arm in `katas/014_few_shot_calibration/harness.py::run_few_shot(task_id, corpus, set_id)` — resolves the active `ExampleSet` from the registry, builds the prompt via `FewShotBuilder`, calls the client per input, collects metrics, and writes a `CalibrationReport` stamped with the active `set_id` (FR-001, FR-003, SC-004)
- [ ] T029 [US1] Implement `katas/014_few_shot_calibration/harness.py::compute_delta(baseline_report, calibrated_report)` returning absolute + relative reduction and enforcing the ≥ 40% relative-reduction threshold as the build gate (SC-001, FR-004)
- [ ] T029a [P] [US1] Add unit test `tests/katas/014_few_shot_calibration/unit/test_calibration_precondition_gate.py` asserting `should_calibrate` returns `(False, "CalibrationNotIndicated")` for baseline `inconsistency_rate ∈ {0.0, 0.1, 0.199}` and `(True, "")` for `{0.20, 0.5, 0.99}` — proves the FR-001 precondition is machine-enforced and no few-shot API call is made when the baseline is already acceptable
- [ ] T030 [US1] Implement schema-validity scoring in `katas/014_few_shot_calibration/harness.py`: every model output is validated against the declared task schema; schema-invalid outputs set `schema_valid=False` AND count toward `inconsistency_rate` — no silent acceptance (SC-002)
- [ ] T031 [US1] Implement the CLI entrypoint `katas/014_few_shot_calibration/runner.py` with `python -m katas.014_few_shot_calibration.runner --task informal_measures --corpus ... --set-id ...`; reads `LIVE_API` env var to choose `LiveClient` vs `RecordedClient`; on exit prints the `runs/<session-id>/calibration.json` path

**Checkpoint**: US1 fully functional — practitioner runs the harness against the informal-measures corpus in both arms, the calibrated arm measurably beats zero-shot by ≥ 40% relative, every run is traceable to its `set_id`, and BDD scenarios [TS-001, TS-002, TS-003, TS-004] all pass.

---

## Phase 4: User Story 2 - Demonstrate the Anti-Pattern and Measure the Delta (Priority: P2)

**Goal**: A practitioner deliberately runs the defended anti-pattern (silent zero-shot + successive prompt tweaks on a subjective task) on the same inputs as the calibrated run; the runner halts silent zero-shot without `acknowledge_zero_shot=True`, permits the run only with the explicit flag, and records both arms side-by-side with a single computed delta (FR-004, FR-007, SC-001).

**Independent Test**: Invoke `run_zero_shot` on the flagged subjective task without the acknowledgement flag and assert the runner halts *before* any API call is made; invoke it again with `acknowledge_zero_shot=True` and assert the resulting calibration artifact records both arms side-by-side with the delta.

### Tests for User Story 2

- [ ] T032 [P] [US2] Copy/symlink `specs/014-few-shot-calibration/tests/features/anti_pattern_defense_and_delta.feature` to `tests/katas/014_few_shot_calibration/features/anti_pattern_defense_and_delta.feature`
- [ ] T033 [US2] Implement BDD step definitions for [TS-005] in `tests/katas/014_few_shot_calibration/step_defs/test_anti_pattern_defense_and_delta_steps.py` — asserts that zero-shot on a subjective task without acknowledgement halts *before* any API call is made and the halt reason identifies the documented anti-pattern
- [ ] T034 [US2] Implement BDD step definitions for [TS-006] in `tests/katas/014_few_shot_calibration/step_defs/test_anti_pattern_defense_and_delta_steps.py` — asserts that with `acknowledge_zero_shot=True` the runner proceeds and the report is labeled as the defended anti-pattern control
- [ ] T035 [US2] Implement BDD step definitions for [TS-007] in `tests/katas/014_few_shot_calibration/step_defs/test_anti_pattern_defense_and_delta_steps.py` — asserts both arms are recorded side-by-side with a single computed delta (FR-004, SC-001)
- [ ] T036 [US2] Implement BDD step definitions for [TS-008] in `tests/katas/014_few_shot_calibration/step_defs/test_anti_pattern_defense_and_delta_steps.py` — asserts a zero-shot run using successive prompt tweaks is recorded as the defended anti-pattern and cross-references the calibrated few-shot result as the corrective control
- [ ] T037 [P] [US2] Add unit test `tests/katas/014_few_shot_calibration/unit/test_anti_pattern_flag.py` — zero-shot on a task flagged `subjective_or_format_sensitive=True` raises before the client is ever invoked when `acknowledge_zero_shot` is missing or `False` (FR-007)
- [ ] T038 [P] [US2] Record fixture `tests/katas/014_few_shot_calibration/fixtures/zero_shot_prompt_tweak_log.json` — a simulated series of zero-shot prompt tweaks and their failing outcomes, to drive the "defended anti-pattern" recording scenario (US2, [TS-008])

### Implementation for User Story 2

- [ ] T039 [US2] In `katas/014_few_shot_calibration/harness.py::run_zero_shot`, enforce the anti-pattern guard: when the task is flagged subjective/format-sensitive, require `acknowledge_zero_shot=True` and raise a labeled halt *before* any client call otherwise (FR-007)
- [ ] T040 [US2] Tag the resulting zero-shot `CalibrationReport` with `is_anti_pattern_control=True` when the run proceeded only because the flag was set, so downstream artifacts can identify the defended control (FR-007, [TS-006])
- [ ] T041 [US2] Implement a side-by-side comparison artifact writer in `katas/014_few_shot_calibration/harness.py::write_comparison(zero_shot_report, few_shot_report)` → `runs/<session-id>/comparison.json` capturing both rates and the single computed delta (FR-004, SC-001, [TS-007])
- [ ] T042 [US2] Implement prompt-tweak documentation in `katas/014_few_shot_calibration/harness.py::record_prompt_tweak_series(tweak_log, calibrated_report)` — emits a record labeling the tweak series as the defended anti-pattern and cross-referencing the calibrated few-shot result as the corrective control ([TS-008])

**Checkpoint**: US2 fully functional — silent zero-shot on subjective tasks halts before any API call; explicit acknowledgement permits the zero-shot control run; comparison artifact records both arms with a single delta; prompt-tweak anti-pattern is documented with cross-reference to the calibrated corrective. BDD scenarios [TS-005, TS-006, TS-007, TS-008] all pass.

---

## Phase 5: User Story 3 - Rotate the Example Set and Observe Sensitivity (Priority: P3)

**Goal**: A practitioner rotates the active example set across at least two distinct 2–4 pair sets, re-runs the same corpus per set, and produces a sensitivity artifact showing that example **quality** (not count) drives calibrated output quality. Coverage is validated before any rotation is permitted (FR-002, FR-003, FR-004, SC-001, SC-004).

**Independent Test**: Run the corpus with `example_set_calibrated.json` and with `example_set_alternate.json`; assert each run's `CalibrationReport` stamps its own `set_id`, both runs reference the same `corpus_id`, and the comparison artifact documents the sensitivity delta.

### Tests for User Story 3

- [ ] T043 [P] [US3] Record fixture `tests/katas/014_few_shot_calibration/fixtures/example_set_alternate.json` — a distinct 2–4 pair set (the US3 rotation target)
- [ ] T044 [P] [US3] Record recorded-client response fixture `tests/katas/014_few_shot_calibration/fixtures/responses_few_shot_alternate.json` for the alternate set against the same corpus so offline rotation is deterministic
- [ ] T045 [P] [US3] Record fixture `tests/katas/014_few_shot_calibration/fixtures/example_set_missing_coverage.json` — a set that fails `validate_coverage` for the `informal_measures` task (used by [TS-011])
- [ ] T046 [P] [US3] Copy/symlink `specs/014-few-shot-calibration/tests/features/example_set_rotation_and_sensitivity.feature` to `tests/katas/014_few_shot_calibration/features/example_set_rotation_and_sensitivity.feature`
- [ ] T047 [US3] Implement BDD step definitions for [TS-009] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_rotation_and_sensitivity_steps.py` — asserts each rotated run stamps its `set_id` onto the calibration report and records the measured inconsistency rate for that set (FR-003, SC-004)
- [ ] T048 [US3] Implement BDD step definitions for [TS-010] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_rotation_and_sensitivity_steps.py` — asserts the comparison of two rotated runs documents sensitivity to example quality on the comparison artifact and both runs reference the same `corpus_id` (FR-004, SC-001)
- [ ] T049 [US3] Implement BDD step definitions for [TS-011] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_rotation_and_sensitivity_steps.py` — asserts a set lacking coverage causes the runner to refuse execution with a `missing edge-case coverage` reason before any API call (FR-002)
- [ ] T050 [P] [US3] Add unit test `tests/katas/014_few_shot_calibration/unit/test_registry_rotation.py` driving `ExampleSetRegistry.rotate_all()` over two sets and asserting per-run `set_id` stamping and isolation between runs (FR-003, SC-004)

### Implementation for User Story 3

- [ ] T051 [US3] In `katas/014_few_shot_calibration/harness.py`, plumb a rotation loop `run_rotation(task_id, corpus, set_ids)` that calls `run_few_shot` per id, sharing the same `corpus_id` across all runs so the comparison artifact is directly comparable ([TS-010])
- [ ] T052 [US3] In `katas/014_few_shot_calibration/harness.py::write_sensitivity_artifact(reports)`, produce `runs/<session-id>/sensitivity.json` documenting per-set rates, pairwise deltas, and a human-readable sensitivity note attributing the spread to example quality (not count) ([TS-010], US3 narrative)
- [ ] T053 [US3] Enforce the coverage gate on `run_few_shot` by calling `ExampleSetRegistry.validate_coverage(set_id, task_id)` before the first API call; surface `MissingCoverageError` as a labeled refusal reason (FR-002, [TS-011])

**Checkpoint**: US3 fully functional — rotating across `calibrated_primary` and `calibrated_alternate` produces two reports each stamped with its `set_id`; the sensitivity artifact attributes quality spread to example curation; coverage gate refuses runs with insufficient edge-case coverage. BDD scenarios [TS-009, TS-010, TS-011] all pass.

---

## Phase 6: Example-Set Invariants & Contradiction Detection (US1 + US2 cross-cutting, Priority: P1)

**Goal**: `ExampleSet` construction enforces the 2–4 pair envelope and the contradiction-detection rules fail closed *before* any API call. This phase consolidates contract-level tests that span both US1 (size envelope) and US2 (contradiction detection) per the cross-cutting `@US-001 @US-002` tagging on the feature file (FR-005, FR-006, SC-003).

**Independent Test**: Construct `ExampleSet` with `pair_count ∈ {0, 1, 5, 7}` and assert each raises a size-envelope validation error; construct a set whose pairs disagree on a same-field output for similar inputs and assert `ContradictoryExamplesError` fires before any client call.

### Tests for Phase 6

- [ ] T054 [P] Record fixture `tests/katas/014_few_shot_calibration/fixtures/example_set_contradictory.json` — two pairs mapping similar inputs to incompatible outputs (FR-005, [TS-014])
- [ ] T055 [P] Record fixture `tests/katas/014_few_shot_calibration/fixtures/example_set_overlong.json` — an oversized example pair that triggers the size guard (plan.md edge case #4)
- [ ] T056 [P] Record fixture `tests/katas/014_few_shot_calibration/fixtures/example_pair_leakage_candidate.json` — a verbatim canonical input/output flagged non-fatally (plan.md edge case #2)
- [ ] T057 [P] Copy/symlink `specs/014-few-shot-calibration/tests/features/example_set_invariants_and_contradictions.feature` to `tests/katas/014_few_shot_calibration/features/example_set_invariants_and_contradictions.feature`
- [ ] T058 Implement BDD step definitions for [TS-012] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_invariants_and_contradictions_steps.py` — asserts example sets with `pair_count ∈ {0, 1, 5, 7}` are rejected at construction with a size-envelope validation error and no run is executed (FR-006)
- [ ] T059 Implement BDD step definitions for [TS-013] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_invariants_and_contradictions_steps.py` — asserts example sets with `pair_count ∈ {2, 3, 4}` are accepted at construction and assigned a stable `set_id` (FR-006)
- [ ] T060 Implement BDD step definitions for [TS-014] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_invariants_and_contradictions_steps.py` — asserts that a contradictory set raises `ContradictoryExamplesError`, no API call is issued, and zero silently-contradictory sets are accepted across run history (FR-005, SC-003)
- [ ] T061 Implement BDD step definitions for [TS-015] in `tests/katas/014_few_shot_calibration/step_defs/test_example_set_invariants_and_contradictions_steps.py` — asserts the canonical-normalization detector flags pairs that differ only by whitespace/case yet disagree on a same-field output (FR-005, SC-003)
- [ ] T062 [P] Add unit test `tests/katas/014_few_shot_calibration/unit/test_example_set_invariants.py` covering both the size envelope (FR-006: 0, 1, 2, 3, 4, 5, 7) and the contradictory-set error (FR-005): must raise *before* any SDK surface is touched
- [ ] T063 [P] Add unit test `tests/katas/014_few_shot_calibration/unit/test_size_guard_and_leakage_flag.py` asserting the oversized-example fixture triggers the size guard and the leakage-candidate fixture is flagged non-fatally (plan.md edge cases #2 and #4)

**Checkpoint**: Example-set invariants and contradiction detection are irreversible. BDD scenarios [TS-012, TS-013, TS-014, TS-015] all pass. No contradictory or out-of-envelope set can reach the calibration runner.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T064 [P] Write `katas/014_few_shot_calibration/README.md` with: kata objective, few-shot selection + ordering strategy (hand-curated 2–4 pairs placed as a stable prefix), anti-pattern defense (silent zero-shot on subjective tasks, FR-007), run instructions mirroring `quickstart.md`, the example-selection contract + edge-case coverage table (contradictory, overlong, leakage-candidate, missing-coverage), and the Principle VIII reflection section answering the two reflection prompts from `quickstart.md`
- [ ] T065 [P] Add module-level docstrings to each of `katas/014_few_shot_calibration/models.py`, `builder.py`, `registry.py`, `validators.py`, `harness.py`, `client.py`, `runner.py` explaining each module's role in the zero-shot→few-shot calibration loop
- [ ] T066 [P] Add why-comments (per Constitution Principle VIII) on every non-trivial function across `katas/014_few_shot_calibration/*.py` — each comment must tie the code choice back to the kata objective (escape zero-shot defaults on subjective/format-sensitive tasks) or to the specific anti-pattern it defends against (silent zero-shot, contradictory sets, overlong examples, leakage)
- [ ] T067 [P] Document the example-selection contract in `katas/014_few_shot_calibration/README.md`: entry criteria for an `ExamplePair`, size envelope for an `ExampleSet` (2–4), contradiction rule with canonical normalization, size-guard threshold, leakage-candidate flag, and the coverage validation rule — each row citing its FR / SC
- [ ] T068 [P] Verify `specs/014-few-shot-calibration/quickstart.md` usage walkthrough is accurate against the final file layout; update paths or commands if drift was introduced during implementation (runner name, fixture paths, set ids)
- [ ] T069 Run `quickstart.md` end-to-end: `pytest tests/katas/014_few_shot_calibration -v` against fixtures, then optional `LIVE_API=1 python -m katas.014_few_shot_calibration.runner --task informal_measures --set-id v1_pinch_handful_splash` smoke run; archive both outputs as PR evidence
- [ ] T070 [P] Add a "Reproducibility" section to `katas/014_few_shot_calibration/README.md` documenting how `runs/<session-id>/calibration.json` + `outputs.jsonl` are the single source of truth for any reported delta, how `set_id` stamping (FR-003, SC-004) makes any result traceable, and how the ≥ 40% relative-reduction gate is enforced by `compute_delta`
- [ ] T071 [P] Run `ruff check katas/014_few_shot_calibration tests/katas/014_few_shot_calibration` and `black --check` over the same paths; fix any findings
- [ ] T072 [P] Produce a coverage report (`pytest --cov=katas.014_few_shot_calibration`) and archive it at `runs/coverage/014_few_shot_calibration.txt`; target ≥ 90% line coverage on `harness.py`, `builder.py`, `validators.py`, `registry.py`
- [ ] T073 Final self-audit: read the emitted `calibration.json` + `comparison.json` + `sensitivity.json` from the fixture-mode run and confirm they satisfy SC-001, SC-002, SC-003, SC-004 — record the check in the PR description

---

## Dependencies & Execution Order

**Phase order (strict):** Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (invariants) → Phase 7.

**Within-phase dependencies:**
- Phase 2: T006–T014 are all [P] because they live in different files. T007 depends on T006. T010/T011 depend on T006. T012/T013 depend on T006. T014 depends on T006. T015 depends on T006 + T009 + T012 + T014.
- Phase 3: T016–T019 (fixtures + feature copy) run in parallel. T020–T023 depend on T015 + T019 + T016–T018. T024–T026 are [P] once T006/T014/T015 exist. T027 depends on T009 + T015. T028 depends on T012 + T014 + T015. T029 depends on T027 + T028. T030 depends on T015. T031 depends on T027 + T028.
- Phase 4: T032 is [P]. T033–T036 depend on T032 + T027/T028. T037 depends on T027. T038 is [P]. T039 depends on T027. T040 depends on T039. T041 depends on T027 + T028. T042 depends on T038 + T028.
- Phase 5: T043–T046 are [P]. T047–T049 depend on T046 + T028 + T053. T050 depends on T012. T051 depends on T028. T052 depends on T051. T053 depends on T013 + T028.
- Phase 6: T054–T057 are [P]. T058–T061 depend on T057 + T007 + T010. T062 depends on T007 + T010. T063 depends on T011.
- Phase 7: T064–T068 and T070–T072 are [P]. T069 depends on all prior phases complete. T073 depends on T069.

**Story dependencies:**
- US2 extends the zero-shot arm built in US1 (anti-pattern guard, side-by-side comparison) — cannot start until T027 + T028 land.
- US3 extends the few-shot arm built in US1 (rotation loop, sensitivity artifact) — cannot start until T028 lands.
- Phase 6 consolidates invariants that block any calibrated run — can be implemented in parallel with US2/US3 once T006/T007/T010/T011 land.

---

## Parallel Opportunities

**Phase 1 [P]:** T002, T003, T004, T005 (different config/test scaffold files).

**Phase 2 [P]:** T006, T008, T009, T010, T011, T012, T013, T014 (distinct modules); T007 after T006.

**Phase 3 [P]:** fixture batch — T016, T017, T018, T019 all in parallel; unit batch — T024, T025, T026 in parallel once T006/T014/T015 exist.

**Phase 4 [P]:** T032, T037, T038 in parallel.

**Phase 5 [P]:** T043, T044, T045, T046 fixture/feature batch in parallel; T050 in parallel once T012 exists.

**Phase 6 [P]:** T054, T055, T056, T057 fixture/feature batch in parallel; T062, T063 in parallel once validators exist.

**Phase 7 [P]:** T064, T065, T066, T067, T068, T070, T071, T072 all in parallel.

---

## Implementation Strategy

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1) + Phase 6 (invariants). At this point the kata demonstrates Principle I + II end-to-end: calibrated few-shot measurably beats zero-shot on the informal-measures corpus, `ExampleSet` invariants + contradiction detection fail closed, and every run is traceable by `set_id`. This is already a credible kata deliverable.
- **Incremental delivery**: land Phase 4 (US2) next — adds the anti-pattern guard (FR-007) and the side-by-side comparison artifact. Then Phase 5 (US3) adds rotation + sensitivity. Phase 7 documents and polishes.
- **Blast radius**: every phase is gated by BDD scenarios failing first (TDD per Constitution V); Phase 7's `quickstart.md` run is the final acceptance gate. Do NOT edit assertions to make tests pass — fix production code instead (assertion-integrity rule).

---

## Notes

- `[P]` = different files, no shared state, no ordering dependency.
- Each user story is independently testable — US1 against `corpus_informal_measures.json` + `example_set_calibrated.json`, US2 against the anti-pattern guard + comparison artifact, US3 against two rotated sets (`calibrated_primary` and `calibrated_alternate`).
- Phase 6 exists because the `example_set_invariants_and_contradictions.feature` is tagged `@US-001 @US-002` (cross-cutting); splitting it across US1/US2 phases would bury the contradiction-detection contract.
- The contradictory-set and size-envelope fixtures are red tests by design (Constitution V — TDD). They MUST fail closed before validators land.
- `FewShotBuilder` MUST keep `system_instructions + examples_block` as a contiguous prefix and `target_input` as the suffix — this preserves Kata-10 prefix-cache compatibility (Constitution III) and is enforced by T025.
- Zero-shot execution on a task flagged subjective/format-sensitive is the defended anti-pattern (FR-007); silent zero-shot MUST halt before any API call. Any bypass is a regression.
