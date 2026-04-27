# Tasks: Mass Processing with Messages Batch API

**Input**: Design documents from `/specs/017-batch-processing/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] story only
- Traceability: `[TS-001, TS-002]`, never ranges

## Phase 1: Setup

- [ ] T001 Create kata package directory `katas/017_batch_processing/` with empty `__init__.py` so the module is importable per plan.md Project Structure.
- [ ] T002 [P] Create test tree `tests/katas/017_batch_processing/` with `__init__.py`, `conftest.py`, `features/`, `step_defs/`, `unit/`, and `fixtures/` subpackages matching plan.md layout.
- [ ] T003 [P] Pin `anthropic`, `pydantic>=2`, `pytest`, and `pytest-bdd` in the project dependency manifest (root `pyproject.toml` or `requirements.txt`) per plan.md Primary Dependencies.
- [ ] T004 [P] Copy the three authoritative `.feature` files from `specs/017-batch-processing/tests/features/` into `tests/katas/017_batch_processing/features/` so pytest-bdd can discover them.
- [ ] T005 [P] Copy the five JSON Schemas from `specs/017-batch-processing/contracts/` into a runtime-visible location (`katas/017_batch_processing/contracts/` or referenced from tests) so contract scenarios (TS-006, TS-010, TS-017) can load them.
- [ ] T006 Add `runs/` to the repository `.gitignore` so per-job artifacts (`submission.json`, `results.jsonl`, `cost_delta.json`, `failure_bucket.json`) never enter version control (plan.md Structure Decision).

## Phase 2: Foundational

- [ ] T007 Implement pydantic v2 `WorkloadProfile` model in `katas/017_batch_processing/models.py` with `is_blocking`, `latency_budget_seconds` (≥0), `item_count` (≥1), `expected_cost_usd` (Decimal) per data-model.md.
- [ ] T008 Implement pydantic v2 `BatchedItem` model in `katas/017_batch_processing/models.py` with URL-safe `custom_id` (length 1–128) and `request` dict per data-model.md.
- [ ] T009 Implement pydantic v2 `BatchJob` model in `katas/017_batch_processing/models.py` with a model validator on `items` that rejects duplicate `custom_id`s pre-submit (FR-009, edge case #3); `job_id`, `submitted_at`, `processing_status` fields.
- [ ] T010 Implement pydantic v2 `BatchedResult` model in `katas/017_batch_processing/models.py` with `result_type` Literal, and validator enforcing `result_type == "succeeded"` iff `response is not None` (data-model.md invariant).
- [ ] T011 Implement pydantic v2 `ResponseMapping` model in `katas/017_batch_processing/models.py` with `by_custom_id`, `missing`, `errored` fields and a custom `MissingResultError` exception raised when any submitted `custom_id` is absent (FR-007, SC-003).
- [ ] T012 Implement pydantic v2 `FailureBucket` model in `katas/017_batch_processing/models.py` with `round` (≥1), `items`, `parent_job_id`, `max_rounds` (default 4) per data-model.md.
- [ ] T013 Implement pydantic v2 `CostReport` model in `katas/017_batch_processing/models.py` with `calibration_corpus_id`, `sync_cost_usd`, `batch_cost_usd`, `reduction_pct` per data-model.md.
- [ ] T014 Define `BatchClient` Protocol in `katas/017_batch_processing/client.py` with `create(requests)`, `retrieve(job_id)`, and `results(job_id)` methods so tests can swap `RecordedBatchClient` for the real SDK adapter (plan.md Constraints).
- [ ] T015 Implement real SDK adapter `AnthropicBatchClient` in `katas/017_batch_processing/client.py` wrapping `client.messages.batches.create/retrieve/results` per plan.md Primary Dependencies.
- [ ] T016 Implement `RecordedBatchClient` stub in `katas/017_batch_processing/client.py` that replays fixture JSON through `create`/`retrieve`/`results` so the default test run is offline and deterministic (plan.md Testing).
- [ ] T017 [P] Create recorded fixture `tests/katas/017_batch_processing/fixtures/all_succeed.json` with every item returning `result.type=succeeded` per plan.md fixtures list.
- [ ] T018 [P] Create recorded fixture `tests/katas/017_batch_processing/fixtures/all_fail.json` with every item returning `result.type=errored` (edge case all-fail, TS-014).
- [ ] T019 [P] Create recorded fixture `tests/katas/017_batch_processing/fixtures/mixed.json` with majority-succeeded, minority-errored results (TS-011 input).
- [ ] T020 [P] Create recorded fixture `tests/katas/017_batch_processing/fixtures/duplicate_custom_id.json` capturing a pre-submit duplicate rejection input (TS-004, no SDK call).
- [ ] T021 [P] Create recorded fixture `tests/katas/017_batch_processing/fixtures/very_small_batch.json` with `item_count` below the cost-benefit threshold (TS-009).
- [ ] T022 [P] Create recorded fixture `tests/katas/017_batch_processing/fixtures/window_exceeded.json` with `processing_status=canceled` past `expires_at` for FR-010 timeout (TS-015).
- [ ] T023 Wire pytest-bdd feature discovery and shared fixtures (injectable `BatchClient`, classifier thresholds, recorded fixtures loader) in `tests/katas/017_batch_processing/conftest.py` so Background steps resolve across all three `.feature` files.

## Phase 3: User Story 1 — Classify and submit async-tolerant workload (P1)

- [ ] T024 [US1] Implement `WorkloadClassifier` in `katas/017_batch_processing/classifier.py` returning `Literal["batchable","synchronous"]` from `WorkloadProfile` thresholds (`is_blocking`, `latency_budget_seconds`, `item_count`) per data-model.md and scenario-outline examples in TS-005 (FR-001).
- [ ] T025 [US1] Implement `build_batch_job(items)` in `katas/017_batch_processing/batch_job.py` that constructs a `BatchJob`, runs the duplicate-`custom_id` validator, and assigns a local UUID4 draft id pre-submit (FR-002, FR-009).
- [ ] T026 [US1] Implement `submit_batch(job, client)` in `katas/017_batch_processing/batch_job.py` that calls the injected `BatchClient.create` only after classifier verdict is `batchable` and refuses submission otherwise (FR-001, FR-008).
- [ ] T027 [US1] Implement `ResponseMapper.map(results_stream, submitted_ids)` in `katas/017_batch_processing/mapper.py` producing a `ResponseMapping` and raising `MissingResultError` if any submitted `custom_id` is absent (FR-003, FR-007, SC-002, SC-003).
- [ ] T028 [US1] [P] Add pytest-bdd step definitions for TS-001 in `tests/katas/017_batch_processing/step_defs/test_classify_and_submit_steps.py` covering Given/When/Then for async-tolerant classification and unique `custom_id` submission [TS-001].
- [ ] T029 [US1] [P] Add pytest-bdd step definitions for TS-002 in `tests/katas/017_batch_processing/step_defs/test_classify_and_submit_steps.py` covering result correlation by `custom_id` [TS-002].
- [ ] T030 [US1] [P] Add pytest-bdd step definitions for TS-003 in `tests/katas/017_batch_processing/step_defs/test_classify_and_submit_steps.py` covering blocking-workload rejection from the batch pathway [TS-003].
- [ ] T031 [US1] [P] Add pytest-bdd step definitions for TS-004 in `tests/katas/017_batch_processing/step_defs/test_classify_and_submit_steps.py` covering duplicate-`custom_id` pre-submit rejection and no-SDK-call assertion [TS-004].
- [ ] T032 [US1] [P] Add pytest-bdd step definitions for TS-005 Scenario Outline rows in `tests/katas/017_batch_processing/step_defs/test_classify_and_submit_steps.py` covering threshold-driven verdicts [TS-005].
- [ ] T033 [US1] [P] Add pytest-bdd step definitions for TS-006 in `tests/katas/017_batch_processing/step_defs/test_classify_and_submit_steps.py` validating a constructed `BatchJob` payload against `contracts/batch-job.schema.json` [TS-006].
- [ ] T034 [US1] [P] Add unit test `tests/katas/017_batch_processing/unit/test_classifier_thresholds.py` exercising classifier edges beyond TS-005 rows (boundary values for latency budget and item count).
- [ ] T035 [US1] [P] Add unit test `tests/katas/017_batch_processing/unit/test_duplicate_custom_id_rejected.py` asserting the pydantic validator raises before any network call.
- [ ] T036 [US1] [P] Add unit test `tests/katas/017_batch_processing/unit/test_mapper_no_silent_drop.py` asserting `MissingResultError` for a synthetic gap in `custom_id` coverage (FR-007, SC-003).

## Phase 4: User Story 2 — Demonstrate cost reduction vs synchronous baseline (P2)

- [ ] T037 [US2] Implement `SyncBaselineHarness` in `katas/017_batch_processing/cost_delta.py` that processes the calibration corpus through the synchronous pathway and records per-request cost (FR-006).
- [ ] T038 [US2] Implement `BatchCostTotaliser` in `katas/017_batch_processing/cost_delta.py` that sums per-item batch costs from a completed `BatchJob` + `BatchedResult` stream (FR-006).
- [ ] T039 [US2] Implement `compute_cost_delta(sync_totals, batch_totals, corpus_id)` in `katas/017_batch_processing/cost_delta.py` returning a `CostReport` and asserting `reduction_pct >= 0.50` on the frozen corpus (SC-001).
- [ ] T040 [US2] Implement `flag_missed_savings(workload, pathway_used)` in `katas/017_batch_processing/cost_delta.py` that annotates the report when an async-tolerant workload ran synchronously, quantifying avoidable spend (TS-008, FR-006).
- [ ] T041 [US2] Implement `flag_no_cost_benefit(profile)` in `katas/017_batch_processing/classifier.py` (or cost_delta.py) that surfaces a typed escalation when `item_count` is below the cost-benefit threshold instead of silently routing (TS-009, FR-001, FR-006, edge case #4).
- [ ] T042 [US2] Persist `cost_delta.json` under `runs/<job_id>/cost_delta.json` with `calibration_corpus_id`, `sync_cost_usd`, `batch_cost_usd`, `reduction_pct`, source model ids and batch ids (plan.md Storage, TS-010).
- [ ] T043 [US2] [P] Add pytest-bdd step definitions for TS-007 in `tests/katas/017_batch_processing/step_defs/test_cost_reduction_steps.py` covering the ≥50% cost-reduction assertion [TS-007].
- [ ] T044 [US2] [P] Add pytest-bdd step definitions for TS-008 in `tests/katas/017_batch_processing/step_defs/test_cost_reduction_steps.py` covering missed-savings anti-pattern flagging [TS-008].
- [ ] T045 [US2] [P] Add pytest-bdd step definitions for TS-009 in `tests/katas/017_batch_processing/step_defs/test_cost_reduction_steps.py` covering no-cost-benefit escalation for very small batches [TS-009].
- [ ] T046 [US2] [P] Add pytest-bdd step definitions for TS-010 in `tests/katas/017_batch_processing/step_defs/test_cost_reduction_steps.py` validating `cost_delta.json` against its declared schema [TS-010].
- [ ] T047 [US2] [P] Add unit test `tests/katas/017_batch_processing/unit/test_cost_delta_target.py` asserting `reduction_pct >= 0.50` on the frozen calibration corpus and rejecting drift.

## Phase 5: User Story 3 — Isolate, fragment, and reprocess failing items (P3)

- [ ] T048 [US3] Implement `FailureBucket.collect(mapping)` in `katas/017_batch_processing/failure_bucket.py` isolating only `errored`/`expired` `custom_id`s into the bucket without touching successful items (FR-004).
- [ ] T049 [US3] Implement `fragment(items)` in `katas/017_batch_processing/failure_bucket.py` that splits failing sources into smaller pieces for resubmission, preserving a stitch-back reference to the original `custom_id` (FR-005).
- [ ] T050 [US3] Implement `reprocess(bucket, client)` in `katas/017_batch_processing/failure_bucket.py` that submits a follow-up batch containing only fragments and bounds the loop by `max_rounds`, marking remainders `unrecoverable` at exhaustion (FR-005, SC-004).
- [ ] T051 [US3] Implement `stitch(fragment_results, origin_map)` in `katas/017_batch_processing/failure_bucket.py` that merges fragment responses back onto their source `custom_id` on convergence (FR-003, FR-005).
- [ ] T052 [US3] Implement `detect_all_fail(mapping)` terminal-state surfacing in `katas/017_batch_processing/failure_bucket.py` that emits a distinct condition when the bucket equals the submitted set (edge case all-fail, TS-014, FR-004, FR-007).
- [ ] T053 [US3] Implement batch-window timeout handling in `katas/017_batch_processing/batch_job.py` that reads `processing_status` / `expires_at` from the client, emits an explicit `timed_out` terminal state, and accounts every submitted `custom_id` as timed out — never converting to a synchronous retry (FR-007, FR-010, edge case batch window exceeded).
- [ ] T054 [US3] Persist `failure_bucket.json` under `runs/<job_id>/failure_bucket.json` per round per plan.md Storage so TS-017 contract validation has a concrete artifact.
- [ ] T055 [US3] [P] Add pytest-bdd step definitions for TS-011 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` covering isolation of only failing `custom_id`s [TS-011].
- [ ] T056 [US3] [P] Add pytest-bdd step definitions for TS-012 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` covering fragmentation and follow-up batch submission [TS-012].
- [ ] T057 [US3] [P] Add pytest-bdd step definitions for TS-013 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` covering fragment-to-source stitch-back and convergence within `max_recovery_rounds` [TS-013].
- [ ] T058 [US3] [P] Add pytest-bdd step definitions for TS-014 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` covering the all-fail distinct-terminal-state assertion [TS-014].
- [ ] T059 [US3] [P] Add pytest-bdd step definitions for TS-015 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` covering batch-window timeout surfacing without synchronous retry [TS-015].
- [ ] T060 [US3] [P] Add pytest-bdd step definitions for TS-016 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` covering bounded recovery rounds and `unrecoverable` marking [TS-016].
- [ ] T061 [US3] [P] Add pytest-bdd step definitions for TS-017 in `tests/katas/017_batch_processing/step_defs/test_isolate_fragment_steps.py` validating `FailureBucket` against `contracts/failure-bucket.schema.json` [TS-017].
- [ ] T062 [US3] [P] Add unit test `tests/katas/017_batch_processing/unit/test_failure_bucket_fragments.py` asserting fragmentation preserves origin mapping and that bounded rounds terminate.

## Final Phase: Polish

- [ ] T063 Implement `runner.py` CLI entrypoint `python -m katas.017_batch_processing.runner --corpus <path>` in `katas/017_batch_processing/runner.py` orchestrating classify → submit → map → bucket → cost-delta end-to-end (plan.md Source Code).
- [ ] T064 Add module docstrings to every file in `katas/017_batch_processing/` (`classifier.py`, `batch_job.py`, `client.py`, `mapper.py`, `failure_bucket.py`, `cost_delta.py`, `models.py`, `runner.py`) naming the FR the module defends (Principle VIII).
- [ ] T065 Add why-comments to non-trivial functions and validators (duplicate-`custom_id` validator → FR-009 + edge case #3; mapper missing-id raise → FR-007 + SC-003; bounded recovery → SC-004) per plan.md Constitution Check row VIII.
- [ ] T066 [P] Author `katas/017_batch_processing/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — Message Batches API, classifier (sync vs async-tolerant routing), `custom_id` contract for batch entry mapping, partial-failure bucketing, bounded re-submit on isolation/fragment, cost-delta measurement, batch lifecycle (`submitted → in_progress → ended | canceled | expired`) — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`classifier` → `batch_job` → `client` (Batches API) → `mapper` → `failure_bucket` → `cost_delta` → `models` → `runner`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — async-route-when-tolerant, no-silent-drop, bounded-recovery, custom_id-as-contract — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, III Context Economy (cost), VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — batch lifecycle (`submitted → in_progress → ended | canceled | expired`); partial-failure handling (isolate → fragment → bounded re-submit → stitch); duplicate-`custom_id` validator (FR-009, edge case #3); mapper missing-id raise (FR-007, SC-003) (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T067 Verify and run the quickstart: follow `specs/017-batch-processing/quickstart.md` end-to-end against recorded fixtures and the `LIVE_API=1` dry-run corpus; ensure the scenario→spec mapping and Kata Completion checklist all pass.
- [ ] T068 Run the full acceptance + unit suite `pytest tests/katas/017_batch_processing/ -v` and confirm every `@TS-NNN` scenario passes; fix production code (never assertions) on failure.
- [ ] T069 Regenerate the dashboard via `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` so the feature's completion is reflected.
