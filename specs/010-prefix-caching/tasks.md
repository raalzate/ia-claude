# Tasks: Economic Optimization via Prefix Caching

**Input**: Design documents from `/specs/010-prefix-caching/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] story only
- Traceability: `[TS-001, TS-002]`, never ranges

---

## Phase 1: Setup

- [ ] T001 Create package skeleton `katas/kata_010_prefix_caching/__init__.py` with module docstring describing the prefix-caching kata objective (Principle VIII).
- [ ] T002 [P] Create test package skeleton `tests/katas/kata_010_prefix_caching/__init__.py` and `tests/katas/kata_010_prefix_caching/features/__init__.py`, `tests/katas/kata_010_prefix_caching/step_defs/__init__.py`, `tests/katas/kata_010_prefix_caching/unit/__init__.py`, `tests/katas/kata_010_prefix_caching/lint/__init__.py`, `tests/katas/kata_010_prefix_caching/harness/__init__.py`.
- [ ] T003 [P] Add `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd` dev dependencies to `pyproject.toml` under the `[project.optional-dependencies] dev` extra; verify import with a lightweight smoke import.
- [ ] T004 [P] Copy feature files into runtime test tree: move/link `specs/010-prefix-caching/tests/features/warm_cache_sequential_requests.feature`, `prefix_mutation_breaks_cache.feature`, and `suffix_only_variation_preserves_cache.feature` to `tests/katas/kata_010_prefix_caching/features/` for pytest-bdd discovery.
- [ ] T005 [P] Add `runs/` to `.gitignore` so `runs/<session-id>/metrics.jsonl` output is not committed.
- [ ] T006 [P] Create fixture directory `tests/katas/kata_010_prefix_caching/fixtures/` with placeholder files `warm_cache.json`, `cold_start.json`, `mutation_break.json`, `under_min_size.json`, `suffix_only_variation.json` (shape per data-model `CacheMetric` / `response.usage`).

---

## Phase 2: Foundational

- [ ] T007 Implement `katas/kata_010_prefix_caching/models.py` with pydantic v2 models `ContentBlock`, `StaticPrefixRegion`, `DynamicSuffixRegion`, `PromptComposition`, `CacheMetric`, `PrefixMutationDiagnostic` per `data-model.md`; include module docstring citing Principle II and why-comments on each invariant (nullable unions over empty defaults, structurally forbidden `cache_control` on dynamic suffix).
- [ ] T008 Implement `katas/kata_010_prefix_caching/blocks.py` block builders (`make_static_system_block`, `make_static_context_block`, `make_dynamic_suffix_block`) that attach `cache_control: {"type": "ephemeral"}` only to static regions above the minimum cacheable threshold; compute `source_digest` (sha256 of concatenated block text); include why-comment explaining the digest is the runtime mutation anchor (FR-006, SC-004).
- [ ] T009 Implement `katas/kata_010_prefix_caching/composer.py` `PromptComposer` with `build()` that enforces static-before-dynamic ordering, raises `InterleavingRejected` on interleaved segments, refuses `cache_control` on dynamic blocks, sets `under_min_size_warning` when the static region is below threshold, and exposes `declare_prefix_change(revision_id: str)` for intentional prefix revisions (FR-001, FR-002, FR-003, FR-006, FR-007); include module docstring and why-comments tied to FR-IDs.
- [ ] T010 Implement `katas/kata_010_prefix_caching/metrics.py` `CacheMetric` extraction from `response.usage`; derive `uncached_input_tokens` and `hit_rate` (never trusted from external input); JSONL writer to `runs/<session-id>/metrics.jsonl`; include why-comment referencing Principle VII provenance and FR-004.
- [ ] T011 Implement `katas/kata_010_prefix_caching/client.py` thin injectable Anthropic client wrapper supporting recorded-fixture replay (offline default) and `LIVE_API=1` live mode; include docstring explaining offline-first policy.
- [ ] T012 Implement `katas/kata_010_prefix_caching/mutation.py` deliberate-mutation helper (prepend timestamp / inject UUID into static region) for the anti-pattern test, plus runtime mutation detector that compares static-region `source_digest` across consecutive iterations within the TTL window (FR-006).

---

## Phase 3: User Story 1 — Sequential Requests Hit the Cache (P1)

**Goal**: Prove observable KV cache reuse across N sequential calls sharing a static prefix; runs 2..N report cache hits >= 0.90 hit-rate and <= 15% of uncached input-token cost.

**Independent Test**: Run harness with fixed static prefix and varied dynamic suffixes; assert cache-hit rate on runs 2..N >= 0.90 and per-request billable input tokens drop by >= 85% vs. run 1.

- [ ] T013 [P] [US1] Populate `tests/katas/kata_010_prefix_caching/fixtures/warm_cache.json` with recorded `response.usage` snapshots for a 5-call sequence showing rising `cache_read_input_tokens` on iterations 2..5 and `cache_creation_input_tokens > 0` only on iteration 1.
- [ ] T014 [P] [US1] Populate `tests/katas/kata_010_prefix_caching/fixtures/cold_start.json` with a single-call `response.usage` showing `cache_creation_input_tokens > 0` and `cache_read_input_tokens == 0`.
- [ ] T015 [P] [US1] Populate `tests/katas/kata_010_prefix_caching/fixtures/under_min_size.json` with a `response.usage` where no cache entry is created (both cache fields zero) to exercise the under-minimum-size warning path.
- [ ] T016 [US1] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_warm_cache_steps.py` for scenario "Second back-to-back request reports cache hits and cost collapse" [TS-001], asserting non-zero `cache_read_input_tokens` on iteration 2 and billable <= 15% of baseline.
- [ ] T017 [US1] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_warm_cache_steps.py` for scenario "Runs 2..N within the TTL window each hit the full static prefix" (Scenario Outline n=3, n=5) [TS-002], asserting iteration 1 records `cache_creation_input_tokens > 0` / `cache_read_input_tokens == 0` and iterations 2..N reach derived hit_rate >= 0.90.
- [ ] T018 [US1] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_warm_cache_steps.py` for scenario "Billable input tokens drop by at least 85 percent after warmup" [TS-003], asserting mean iterations-2..N billable <= 15% of iteration-1 baseline.
- [ ] T019 [US1] Implement contract test in `tests/katas/kata_010_prefix_caching/step_defs/test_warm_cache_steps.py` for scenario "CacheMetric records conform to the declared JSON schema" [TS-004], validating each JSONL record against `contracts/cache-metric-record.schema.json` and checking required fields.
- [ ] T020 [US1] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_warm_cache_steps.py` for scenario "Static region below the minimum cacheable size emits an explicit warning" [TS-005], asserting `under_min_size_warning is True` and no `cache_control` attached to any block.
- [ ] T021 [US1] Implement `katas/kata_010_prefix_caching/harness.py` measurement harness: issues N sequential Messages API calls (offline or `LIVE_API=1`), records a `CacheMetric` per iteration, computes warmup delta, enforces `declared_target_hit_rate` (default 0.9); include module docstring and why-comments tying behavior to SC-001, SC-002.
- [ ] T022 [P] [US1] Implement unit test `tests/katas/kata_010_prefix_caching/harness/test_warm_cache_hit_rate.py` driving the harness against `warm_cache.json` fixture and asserting SC-001 (>=0.90) / SC-002 (<=15%) thresholds hold.

**Checkpoint**: US1 is independently runnable and verifiable — the core economic claim of the kata is green against fixtures.

---

## Phase 4: User Story 2 — Anti-Pattern Defense: Prefix Mutation Breaks Caching (P2)

**Goal**: Prove prefix mutation zeros out cache hits and is caught by CI lint before merge; distinguish intentional revisions from accidental mutation.

**Independent Test**: Re-run the P1 sequence after prepending a per-request timestamp ahead of the static region; assert hit rate ~ 0 and input cost returns to uncached baseline; run the source-tree lint and confirm it emits a diagnostic for any volatile symbol in a static block.

- [ ] T023 [P] [US2] Populate `tests/katas/kata_010_prefix_caching/fixtures/mutation_break.json` with recorded `response.usage` for a 5-call sequence where every iteration reports `cache_read_input_tokens == 0` after a timestamp is prepended ahead of the static prefix.
- [ ] T024 [US2] Implement `katas/kata_010_prefix_caching/lint.py` AST/regex lint gate that scans composer source for non-allowlisted dynamic symbols (`datetime.datetime.now`, `uuid.uuid4`, `os.environ`, `time.time`) reached from within a static-block builder, and emits a `PrefixMutationDiagnostic` of `kind="lint_violation"` with file path, line, offending symbol, and `declared_as_intentional=false`; include why-comment tying each banned symbol back to FR-002/FR-005.
- [ ] T025 [US2] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_mutation_steps.py` for scenario "Per-request timestamp prepended ahead of static region zeroes out cache hits" [TS-006], asserting every iteration records `cache_read_input_tokens == 0` and mean billable equals the uncached baseline.
- [ ] T026 [US2] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_mutation_steps.py` for scenario "CI prefix-integrity lint fails on PR reordering volatile values before static region" [TS-007], asserting the lint exits non-zero and reports offending file path, line, and symbol.
- [ ] T027 [US2] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_mutation_steps.py` for Scenario Outline "Lint rejects non-allowlisted dynamic sources referenced from static-block construction" [TS-008] across examples `datetime.datetime.now`, `uuid.uuid4`, `os.environ`, `time.time`, asserting each emits a `lint_violation` diagnostic naming the offending symbol with `declared_as_intentional=false`.
- [ ] T028 [US2] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_mutation_steps.py` for scenario "Intentional prefix revision is distinguishable from accidental mutation" [TS-009], asserting `declare_prefix_change(revision_id)` causes iteration 1 to record `cache_creation_input_tokens > 0` / `cache_read_input_tokens == 0` and the `CacheMetric` echoes `intentional_prefix_change=true` with a populated `prefix_revision_id`.
- [ ] T029 [US2] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_mutation_steps.py` for scenario "Accidental runtime prefix mutation emits a runtime_mutation diagnostic" [TS-010], asserting the detector emits a `PrefixMutationDiagnostic` of `kind="runtime_mutation"` carrying `previous_source_digest` and `current_source_digest`, with `declared_as_intentional=false`.
- [ ] T030 [US2] Implement contract test in `tests/katas/kata_010_prefix_caching/step_defs/test_mutation_steps.py` for scenario "PrefixMutationDiagnostic records conform to the declared JSON schema" [TS-011], validating records against `contracts/prefix-mutation-diagnostic.schema.json` and checking `kind` is one of `lint_violation`, `runtime_mutation`, `under_min_size`.
- [ ] T031 [P] [US2] Implement lint unit test `tests/katas/kata_010_prefix_caching/lint/test_no_dynamic_in_static.py` exercising the AST lint against a fixture composer source with injected `datetime.now` / `uuid.uuid4` / `os.environ` references and asserting the expected diagnostics.
- [ ] T032 [P] [US2] Implement harness test `tests/katas/kata_010_prefix_caching/harness/test_mutation_breaks_cache.py` driving the harness against `mutation_break.json` and asserting hit_rate collapses to zero (SC-002 delta, SC-004).

**Checkpoint**: US2 is independently runnable; CI now fails any PR that introduces prefix mutation, and the runtime detector labels digest drift correctly.

---

## Phase 5: User Story 3 — Dynamic Suffix Changes Preserve Prefix Cache (P3)

**Goal**: Confirm the positive invariant complementary to US2: arbitrary suffix edits do not invalidate the prefix cache, and the composer structurally prevents interleaving or dynamic-suffix `cache_control`.

**Independent Test**: Run a sequence where each request has a distinct suffix but a byte-identical static region; assert prefix cache hits on runs 2..N regardless of suffix content, length, or structure; confirm composer rejects interleaving and dynamic `cache_control` at build time.

- [ ] T033 [P] [US3] Populate `tests/katas/kata_010_prefix_caching/fixtures/suffix_only_variation.json` with recorded `response.usage` showing byte-identical static prefix across runs 1..3 with varying suffix content and preserved `cache_read_input_tokens` on runs 2..3.
- [ ] T034 [US3] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_suffix_variation_steps.py` for Scenario Outline "Arbitrary suffix edits preserve prefix cache hits across runs 2..N" [TS-012] across examples `user question wording`, `appended timestamp tag`, `session id value`, `reordered suffix lines`, asserting iterations 2 and 3 record `cache_read_input_tokens` covering the full static prefix and `source_digest` is identical across all three iterations.
- [ ] T035 [US3] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_suffix_variation_steps.py` for scenario "Suffix that grows in length between runs still yields prefix cache reads" [TS-013], asserting `cache_read_input_tokens` still covers the full static prefix on runs 2..N and no `cache_control` is attached to any dynamic-suffix block.
- [ ] T036 [US3] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_suffix_variation_steps.py` for scenario "Composer refuses to attach cache_control to a dynamic-suffix block" [TS-014], asserting the composer raises a composition-time error and no request is emitted when a caller attempts to set `cache_control` on a `DynamicSuffixRegion` block.
- [ ] T037 [US3] Implement step definitions in `tests/katas/kata_010_prefix_caching/step_defs/test_suffix_variation_steps.py` for scenario "Composer rejects interleaved static and dynamic segments at build time" [TS-015], asserting `InterleavingRejected` is raised and no request is emitted when a dynamic value appears between two static content blocks.
- [ ] T038 [US3] Implement contract test in `tests/katas/kata_010_prefix_caching/step_defs/test_suffix_variation_steps.py` for scenario "PromptComposition records conform to the declared JSON schema" [TS-016], validating a composer-produced `PromptComposition` against `contracts/prompt-composition.schema.json` and asserting static blocks precede the dynamic block in the emitted message list.
- [ ] T039 [P] [US3] Implement unit test `tests/katas/kata_010_prefix_caching/unit/test_composer_ordering.py` covering static-before-dynamic ordering, interleaving rejection, and FR-001 / FR-003 invariants.
- [ ] T040 [P] [US3] Implement unit test `tests/katas/kata_010_prefix_caching/unit/test_cache_control_placement.py` covering FR-002, FR-003, SC-003 — `cache_control` attached iff static and above min size; structurally forbidden on dynamic.
- [ ] T041 [P] [US3] Implement unit test `tests/katas/kata_010_prefix_caching/unit/test_min_size_warning.py` covering FR-007 edge case: below-threshold static region emits the `under_min_size_warning` and no `cache_control` is attached.
- [ ] T042 [P] [US3] Implement unit test `tests/katas/kata_010_prefix_caching/unit/test_cache_metric_shape.py` covering pydantic validation of `CacheMetric` (required fields, derived `hit_rate`, iteration-1 cold-start invariant) per data-model (Principles II, VII).
- [ ] T043 [P] [US3] Implement harness test `tests/katas/kata_010_prefix_caching/harness/test_suffix_only_variation.py` driving the harness against `suffix_only_variation.json` and asserting prefix reuse across varied suffixes.

**Checkpoint**: US3 is independently runnable; the suffix is the only safe locus of variability, proven structurally and empirically.

---

## Final Phase: Polish

- [ ] T044 Implement `katas/kata_010_prefix_caching/runner.py` CLI entry point (`python -m katas.kata_010_prefix_caching.runner` / `probe --n 5` / `probe --mutate-prefix`) wiring composer + harness + metrics writer; include module docstring.
- [ ] T045 [P] Author `katas/kata_010_prefix_caching/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — ephemeral `cache_control: {"type": "ephemeral"}`, static-vs-dynamic prompt regions, minimum cacheable threshold, hit-rate measurement from `response.usage`, intentional prefix revisions via `declare_prefix_change(revision_id)`, AST mutation lint (banned dynamic symbols `datetime.datetime.now`, `uuid.uuid4`, `os.environ`, `time.time` inside static builders), `source_digest` as runtime mutation anchor — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`models` → `blocks` builders → `composer` (`PromptComposer`) → `metrics` → `client` (recorded + `LIVE_API=1`) → `harness` → `lint`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — static-before-dynamic ordering, structurally-forbidden cache_control on dynamic, declared-revision over silent mutation, lint-gate over reviewer-gate — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, III Context Economy (token reuse via cache), VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — composer build invariants (`InterleavingRejected` raised on interleaved segments; refuses `cache_control` on dynamic blocks; `under_min_size_warning` when static region below threshold); `declared_target_hit_rate` default 0.9; `PrefixMutationDiagnostic` `kind="lint_violation"` shape (file path, line, offending symbol, `declared_as_intentional=false`) (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T046 [P] Audit every `katas/kata_010_prefix_caching/*.py` module for a module docstring and why-comments on non-trivial branches tied to FR-IDs (Principle VIII); add any missing.
- [ ] T047 [P] Run `pytest tests/katas/kata_010_prefix_caching -v` against fixtures and verify all scenarios pass; record result in the quickstart "Done" checklist.
- [ ] T048 [P] Execute the quickstart commands from `specs/010-prefix-caching/quickstart.md` end-to-end (install, fixture run, `LIVE_API=1` probe if a key is available, mutation demo) and confirm printed output matches the documented format.
- [ ] T049 [P] Regenerate the IIKit dashboard via `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` after completing the kata.
