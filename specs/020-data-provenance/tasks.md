# Tasks: Data Provenance Preservation

**Input**: Design documents from `/specs/020-data-provenance/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] on story tasks
- Traceability: `[TS-001, TS-002]`, never prose ranges

## Phase 1: Setup

- [ ] T001 Create package skeleton `katas/020_data_provenance/__init__.py` and test package skeleton `tests/katas/020_data_provenance/__init__.py` (+ `unit/`, `lint/`, `integration/`, `features/`, `step_defs/`, `fixtures/` subpackages with empty `__init__.py`)
- [ ] T002 [P] Ensure `pyproject.toml` extras include `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, `jsonschema` under `[project.optional-dependencies].dev`; install with `pip install -e ".[dev]"`
- [ ] T003 [P] Add `runs/` to `.gitignore` (per-run audit artifacts per plan.md §Storage; must not be tracked)
- [ ] T004 [P] Configure `pyproject.toml` `[tool.pytest.ini_options]` to register `bdd_features_base_dir = tests/katas/020_data_provenance/features` and collect `tests/katas/020_data_provenance`

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [ ] T005 Define pydantic models in `katas/020_data_provenance/models.py`: `Source`, `ProvenanceRecord`, `Claim`, `SubagentClaimsPayload`, `ClaimGroup`, `ConflictSet`, `ReviewTask`, `AggregationReport` all with `model_config = ConfigDict(extra="forbid")` per data-model.md
- [ ] T006 Define terminal exceptions in `katas/020_data_provenance/models.py`: `OrphanClaimError`, `SubagentPayloadValidationError`, `ProvenanceSchemaError`
- [ ] T007 [P] Implement canonical-claim-key hasher in `katas/020_data_provenance/canonical_key.py`: `canonical_key(text: str) -> str` — sha256 over normalized (lowercased, whitespace-collapsed, punctuation-stripped) claim text per research D-002
- [ ] T008 [P] Implement injectable Anthropic client wrapper in `katas/020_data_provenance/client.py` mirroring Kata 1 D-001 / Kata 4 D-004 (class with `messages_create(**kwargs)` seam so a `RecordedAnthropicClient` can be injected in tests)
- [ ] T009 [P] Implement extraction-tool builder in `katas/020_data_provenance/extraction_tool.py`: `build_claim_tool()` returns an Anthropic tool definition whose `input_schema` is produced via `Claim.model_json_schema()`; hardcodes `tool_choice={"type": "any"}` as the companion constant
- [ ] T010 Copy JSON Schemas from `specs/020-data-provenance/contracts/` into a loader helper in `katas/020_data_provenance/models.py` (or reference by path) so `Claim`, `SubagentClaimsPayload`, `ConflictSet`, `ReviewTask`, and `AggregationReport` can be validated at construction against Draft 2020-12
- [ ] T011 Wire per-run audit writer in `katas/020_data_provenance/runner.py`: creates `runs/<session-id>/` and opens `source_documents.jsonl`, `subagent_claims.jsonl`, `aggregation_report.json`, `review_tasks.jsonl` handles (FR-006)

**Checkpoint**: Models + exceptions + canonical-key hasher + client seam + extraction-tool builder + audit writer all importable; no aggregation logic yet.

## Phase 3: User Story 1 — Provenance-Preserving Aggregation (Priority: P1) [US1]

**Goal**: Two isolated subagents extract claims from two manuals; every emitted `Claim` carries populated `source_url`, `source_name`, and `publication_date` traceable to its originating Source — no prose summaries, no orphan sentences.

**Independent Test**: Pass two distinct manuals to two subagents against the `consistent_aggregation.json` fixture; assert each emitted claim contains all three provenance fields populated, no claim is merged into prose, and duplicate claim text from different sources preserves both provenance records.

### Tests for User Story 1 (write first; all must fail before implementation)

- [ ] T012 [P] [US1] Copy `tests/features/provenance_preserving_aggregation.feature` from `specs/020-data-provenance/tests/features/` into `tests/katas/020_data_provenance/features/provenance_preserving_aggregation.feature` (verbatim — DO NOT MODIFY SCENARIOS)
- [ ] T013 [P] [US1] Create recorded fixture `tests/katas/020_data_provenance/fixtures/consistent_aggregation.json` (two subagents, each returning a `SubagentClaimsPayload` with complete provenance on every `Claim`)
- [ ] T014 [P] [US1] Create recorded fixture `tests/katas/020_data_provenance/fixtures/duplicate_claim_different_sources.json` (two sources emit identical claim text; both provenance records preserved)
- [ ] T015 [P] [US1] Create recorded fixture `tests/katas/020_data_provenance/fixtures/missing_source_url.json` (internal-only source with `source_url=None` and populated `source_name`)
- [ ] T016 [P] [US1] Create recorded fixture `tests/katas/020_data_provenance/fixtures/missing_publication_date.json` (undated memo with `publication_date_sentinel="unknown"`)
- [ ] T017 [US1] Step definitions for `@TS-001` in `tests/katas/020_data_provenance/step_defs/test_provenance_preserving_steps.py`: "Two isolated subagents emit claims with complete provenance" [TS-001]
- [ ] T018 [US1] Step definitions for `@TS-002` in the same file: "Each emitted claim links back to its exact source document" [TS-002]
- [ ] T019 [US1] Step definitions for `@TS-003` in the same file: "No amalgamated prose survives aggregation of N manuals" [TS-003]
- [ ] T020 [US1] Step definitions for `@TS-004` in the same file: "Subagents are forbidden from returning prose summaries" [TS-004]
- [ ] T021 [US1] Step definitions for `@TS-005` in the same file: "Emitted claim records conform to the Claim JSON schema" [TS-005]
- [ ] T022 [US1] Step definitions for `@TS-006` in the same file: "Duplicate claim text from different sources preserves both provenance records" [TS-006]
- [ ] T023 [US1] Step definitions for `@TS-007` Scenario Outline in the same file: "Edge-case provenance fields are preserved verbatim" (examples: `local file path as source_url`, `no URL at all (internal-only)`, `an undated internal memo`) [TS-007]
- [ ] T024 [P] [US1] Unit test `tests/katas/020_data_provenance/unit/test_claim_requires_all_provenance.py` asserting `Claim` construction raises `pydantic.ValidationError` when any of `claim` or `source_name` is missing/empty, and that `source_url=None` / `publication_date=None` are permitted only with their sentinel semantics [FR-001, FR-002, SC-004]
- [ ] T025 [P] [US1] Unit test `tests/katas/020_data_provenance/unit/test_canonical_key_stability.py` asserting identical normalized claim text produces identical sha256 canonical keys across runs and process restarts [data-model.md §Claim invariants]
- [ ] T026 [P] [US1] Unit test `tests/katas/020_data_provenance/unit/test_aggregator_groups_by_key.py` asserting duplicate claim text from distinct sources is preserved as separate `Claim` entries grouped under a single `ClaimGroup.supporting_sources` — provenance metadata is never stripped [FR-008, TS-006]

### Implementation for User Story 1

- [ ] T027 [US1] Implement `Subagent` class in `katas/020_data_provenance/subagent.py`: `run(source: Source) -> SubagentClaimsPayload`, opens a fresh `messages.create` session seeded only from the source document and the tool built in T009, wraps each tool-use block with `Claim.model_validate` and returns a `SubagentClaimsPayload` — `ValidationError` becomes terminal `SubagentPayloadValidationError`
- [ ] T028 [US1] Enforce `tool_choice={"type": "any"}` on every `Subagent.run` SDK call so the subagent cannot satisfy the contract by returning prose [FR-007, TS-004]
- [ ] T029 [US1] Implement `ProvenanceAggregator.aggregate(payloads)` in `katas/020_data_provenance/aggregator.py`: groups `Claim`s by `canonical_key`, emits `ClaimGroup` entries for corroborating sources (multiple supporting `Claim`s that do not numerically disagree), appends both provenance records when claim text collides across sources [FR-008]
- [ ] T030 [US1] Implement CLI entry in `katas/020_data_provenance/runner.py`: `python -m katas.020_data_provenance.runner --manuals <path>...`; reads `LIVE_API` env to choose real vs. recorded client; writes `aggregation_report.json` per FR-006
- [ ] T031 [US1] Wire audit logging: every `SubagentClaimsPayload` appended as one line to `subagent_claims.jsonl`; every ingested `Source` appended to `source_documents.jsonl` before the subagent spawn [FR-006]

**Checkpoint**: `pytest tests/katas/020_data_provenance/features/provenance_preserving_aggregation.feature tests/katas/020_data_provenance/unit/test_claim_requires_all_provenance.py tests/katas/020_data_provenance/unit/test_canonical_key_stability.py tests/katas/020_data_provenance/unit/test_aggregator_groups_by_key.py` passes. US1 delivers end-to-end provenance-preserving extraction on the happy path and on corroborating duplicates.

## Phase 4: User Story 2 — Conflict Surfacing Without Silent Resolution (Priority: P2) [US2]

**Goal**: Contradictory claims across sources surface as a `ConflictSet` with `conflict_detected=true`, preserve both original provenance records, route to a `ReviewTask` for a human — and the aggregator contains zero auto-resolution heuristics.

**Independent Test**: Run the `seeded_contradictions.json` fixture; assert the emitted `AggregationReport` contains a `ConflictSet` whose `claims` list holds both conflicting records with intact provenance, a matching `ReviewTask` is written to `review_tasks.jsonl`, and no single "winning" value is emitted. Run the AST lint to confirm `aggregator.py` holds no forbidden winner-selection symbols.

### Tests for User Story 2

- [ ] T032 [P] [US2] Copy `tests/features/conflict_surfacing_without_silent_resolution.feature` into `tests/katas/020_data_provenance/features/conflict_surfacing_without_silent_resolution.feature` (verbatim)
- [ ] T033 [P] [US2] Create recorded fixture `tests/katas/020_data_provenance/fixtures/seeded_contradictions.json` (two subagents, two conflicting numeric claims for the same fact across two sources)
- [ ] T034 [P] [US2] Create recorded fixture `tests/katas/020_data_provenance/fixtures/corroborating_sources.json` (two sources agree on the same fact — no false-positive conflict)
- [ ] T035 [US2] Step definitions for `@TS-008` in `tests/katas/020_data_provenance/step_defs/test_conflict_surfacing_steps.py`: "Two conflicting numeric claims surface as a conflict record" [TS-008]
- [ ] T036 [US2] Step definitions for `@TS-009` in the same file: "Detected conflict is routed to human review without a winning value" [TS-009]
- [ ] T037 [US2] Step definitions for `@TS-010` in the same file: "Agreeing sources produce no false-positive conflict marker" [TS-010]
- [ ] T038 [US2] Step definitions for `@TS-011` Scenario Outline in the same file: "Forbidden auto-resolution heuristics are absent from the aggregator" (examples: `pick_latest`, `majority_vote`, `confidence_score`, `sort_by_date`) [TS-011]
- [ ] T039 [US2] Step definitions for `@TS-012` in the same file: "Every seeded contradiction in the labeled corpus is detected" [TS-012]
- [ ] T040 [US2] Step definitions for `@TS-013` in the same file: "ConflictSet and ReviewTask records conform to their JSON schemas" [TS-013]
- [ ] T041 [US2] Step definitions for `@TS-014` in the same file: "Aggregation pass logs sources, claim count, and conflict count for audit" [TS-014]
- [ ] T042 [P] [US2] AST lint test `tests/katas/020_data_provenance/lint/test_no_auto_resolution.py` asserting `aggregator.py` contains none of the forbidden symbols `pick_latest`, `majority_vote`, `confidence_score`, `sort_by_date`, nor any attribute access to `max(..., key=lambda c: c.publication_date)` style winner selection [FR-004, TS-011]
- [ ] T043 [P] [US2] Integration test `tests/katas/020_data_provenance/integration/test_seeded_contradictions.py` running the aggregator against `seeded_contradictions.json`, scanning `runs/<session-id>/aggregation_report.json` for `conflict_detected=true`, asserting both provenance blocks survive, and verifying `review_tasks.jsonl` holds one matching `ReviewTask` [FR-003, FR-005, SC-002]
- [ ] T044 [P] [US2] Integration test `tests/katas/020_data_provenance/integration/test_no_false_positive_conflicts.py` running against `corroborating_sources.json` and asserting zero `ConflictSet` entries are emitted when sources agree [FR-003, TS-010]

### Implementation for User Story 2

- [ ] T045 [US2] Extend `ProvenanceAggregator.aggregate` in `katas/020_data_provenance/aggregator.py` with numeric-divergence detection: within a `canonical_key` group, compare extracted numeric tokens across `Claim`s; when values disagree, route the group into a `ConflictSet` with `conflict_detected=true` instead of a `ClaimGroup` [FR-003, TS-008]
- [ ] T046 [US2] Implement `ReviewTask` emission: every `ConflictSet` generates one `ReviewTask` with matching `conflict_set_key`, `status="pending"`, UUID `task_id`; appended as one line to `review_tasks.jsonl` [FR-005, TS-009, TS-013]
- [ ] T047 [US2] Harden `ProvenanceAggregator` to keep all conflicting `Claim`s in the `ConflictSet.claims` list with their original provenance intact — never drop, merge, or select a winner; reviewed against the AST lint in T042 [FR-004, FR-005]
- [ ] T048 [US2] Extend audit writer in `runner.py`: `aggregation_report.json` records the set of source documents consulted, the number of claims emitted, and the number of conflicts surfaced [FR-006, TS-014]
- [ ] T049 [US2] Ensure `aggregator.py` module remains clean of any forbidden winner-selection symbol — refactor any accidental reference flagged by `test_no_auto_resolution.py` [FR-004]

**Checkpoint**: `pytest tests/katas/020_data_provenance/features/conflict_surfacing_without_silent_resolution.feature tests/katas/020_data_provenance/lint tests/katas/020_data_provenance/integration/test_seeded_contradictions.py tests/katas/020_data_provenance/integration/test_no_false_positive_conflicts.py` passes. Conflict surfacing is observably verified; no silent resolution path exists.

## Phase 5: User Story 3 — Fail-Closed on Missing Provenance Schema (Priority: P3) [US3]

**Goal**: A schema missing any required provenance field halts the pipeline with a structured validation error before any claim is emitted; the extraction tool's `input_schema` stays byte-equivalent to `Claim.model_json_schema()`; the orphan-claim lint runs as the terminal step of every aggregation pass.

**Independent Test**: Submit each negative-schema fixture (one per omitted provenance field) and assert the pipeline halts with a structured error naming the missing field and emits zero claims. Submit the orphan-claim fixture and assert `OrphanClaimError` is raised before `aggregation_report.json` is written. Verify `build_claim_tool()` output is byte-equivalent to `Claim.model_json_schema()`.

### Tests for User Story 3

- [ ] T050 [P] [US3] Copy `tests/features/fail_closed_on_missing_provenance_schema.feature` into `tests/katas/020_data_provenance/features/fail_closed_on_missing_provenance_schema.feature` (verbatim)
- [ ] T051 [P] [US3] Create recorded fixture `tests/katas/020_data_provenance/fixtures/orphan_claim.json` (subagent returns a payload whose `Claim` is missing `source_name`)
- [ ] T052 [P] [US3] Create recorded fixture set `tests/katas/020_data_provenance/fixtures/negative_schemas/` — one variant per required provenance field (`no_source_url.json`, `no_source_name.json`, `no_publication_date.json`)
- [ ] T053 [US3] Step definitions for `@TS-015` Scenario Outline in `tests/katas/020_data_provenance/step_defs/test_fail_closed_steps.py`: "Schema omitting a required provenance field halts with a structured error" (examples: `source_url`, `source_name`, `publication_date`) [TS-015]
- [ ] T054 [US3] Step definitions for `@TS-016` in the same file: "Fully-specified schema proceeds normally with provenance-complete output" [TS-016]
- [ ] T055 [US3] Step definitions for `@TS-017` in the same file: "OrphanClaimError halts emission on the first orphan encountered" [TS-017]
- [ ] T056 [US3] Step definitions for `@TS-018` in the same file: "Extraction tool input_schema stays in lockstep with the Claim pydantic model" [TS-018]
- [ ] T057 [US3] Step definitions for `@TS-019` in the same file: "tool_choice is pinned to structured extraction on every subagent spawn" [TS-019]
- [ ] T058 [US3] Step definitions for `@TS-020` in the same file: "Negative test set achieves 100% orphan-claim rejection rate" [TS-020]
- [ ] T059 [P] [US3] Unit test `tests/katas/020_data_provenance/unit/test_tool_schema_mirrors_claim.py` asserting `build_claim_tool()["input_schema"]` is byte-equivalent to `Claim.model_json_schema()`, and that adding a required field to `Claim` propagates without manual edits [FR-002, TS-018]
- [ ] T060 [P] [US3] Unit test `tests/katas/020_data_provenance/unit/test_tool_choice_forces_extraction.py` inspecting a `RecordedAnthropicClient` to assert every recorded invocation has `tool_choice={"type": "any"}` [FR-007, TS-019]
- [ ] T061 [P] [US3] Unit test `tests/katas/020_data_provenance/unit/test_orphan_claim_rejection.py` asserting `OrphanClaimLint.run(payloads)` raises `OrphanClaimError` naming the offending `claim_id` on the first orphan encountered, and that `AggregationReport` is not written [FR-002, SC-004, TS-017]
- [ ] T062 [P] [US3] Integration test `tests/katas/020_data_provenance/integration/test_negative_schema_set.py` iterating over every fixture in `negative_schemas/`, asserting each invocation halts with a structured `ProvenanceSchemaError` naming the omitted field and emits zero claims [FR-002, SC-004, TS-015, TS-020]

### Implementation for User Story 3

- [ ] T063 [US3] Implement `OrphanClaimLint` in `katas/020_data_provenance/orphan_lint.py`: `run(payloads: list[SubagentClaimsPayload]) -> None` scans every `Claim`, raises `OrphanClaimError(claim_id=...)` on the first `Claim` whose `source_name` is missing/empty or whose required provenance contract is violated in a way the pydantic layer did not catch [FR-002, SC-004]
- [ ] T064 [US3] Wire `OrphanClaimLint.run` as the terminal step of `ProvenanceAggregator.aggregate` before the `AggregationReport` is written; any `OrphanClaimError` aborts the write, so no partial `aggregation_report.json` leaks downstream [FR-002, TS-017]
- [ ] T065 [US3] Implement schema-missing-field guard in `extraction_tool.py`: `validate_claim_schema(schema)` compares a caller-supplied schema against `Claim.model_json_schema()` required fields and raises `ProvenanceSchemaError(missing_fields=[...])` naming the omitted fields before any SDK call [FR-002, TS-015, TS-020]
- [ ] T066 [US3] Harden `Subagent.run` to call `validate_claim_schema` on its tool's `input_schema` before `messages.create`; any `ProvenanceSchemaError` is terminal and emits zero claims [FR-002, TS-015]
- [ ] T067 [US3] Ensure `build_claim_tool()` regenerates from `Claim.model_json_schema()` on every call (no cached stale copy) so adding a required field to `Claim` propagates automatically [FR-002, TS-018]

**Checkpoint**: `pytest tests/katas/020_data_provenance/features/fail_closed_on_missing_provenance_schema.feature tests/katas/020_data_provenance/unit/test_tool_schema_mirrors_claim.py tests/katas/020_data_provenance/unit/test_tool_choice_forces_extraction.py tests/katas/020_data_provenance/unit/test_orphan_claim_rejection.py tests/katas/020_data_provenance/integration/test_negative_schema_set.py` passes. Fail-closed posture proven across every negative-schema variant; orphan-claim lint is load-bearing terminal step.

## Final Phase: Polish & Cross-Cutting Concerns

### Documentation (Principle VIII — Mandatory Documentation)

- [ ] T068 [P] Write `katas/020_data_provenance/README.md`: kata objective (preserve the 1:1 mapping between factual claims and their original sources across subagent-processed corporate manuals), provenance-chain architecture (Source → Subagent extraction via `Claim`-shaped tool → `SubagentClaimsPayload` → `ProvenanceAggregator` → `ClaimGroup` or `ConflictSet` + `ReviewTask` → `AggregationReport`), anti-pattern defense (no unattributed assertions — schema-required provenance, `tool_choice={"type": "any"}` blocks prose, orphan-claim lint fails closed, AST lint forbids winner-selection heuristics), run instructions (fixture run via `pytest tests/katas/020_data_provenance -v` and `LIVE_API=1` CLI run), and reflection section answering the quickstart's reflection prompts (Principle VIII + Principle VII Provenance & Self-Audit)
- [ ] T069 [P] Add module-level docstrings to every file in `katas/020_data_provenance/` explaining its role in the provenance chain: `models.py` (typed provenance contract), `subagent.py` (per-source extraction with schema-required Claim tool), `extraction_tool.py` (tool definition mirrored from `Claim.model_json_schema()`), `aggregator.py` (groups claims, detects conflicts, never auto-resolves), `canonical_key.py` (deterministic sha256 claim-key normalization), `orphan_lint.py` (terminal fail-closed guard), `client.py` (Anthropic seam), `runner.py` (CLI + audit writer)
- [ ] T070 [P] Add why-comments on non-trivial functions: `Claim` validator (Principle II NN — why every provenance field is required), `build_claim_tool` (Principle VII — why `input_schema` is generated from the pydantic model, not hand-maintained), `canonical_key` (Principle I — why sha256 over normalized text keeps grouping deterministic), `ProvenanceAggregator.aggregate` (FR-004 — why there is no winner-selection code path), `OrphanClaimLint.run` (FR-002 — why the lint is terminal and fails closed on first orphan), `Subagent.run` `tool_choice={"type": "any"}` call site (FR-007 — why prose outputs are rejected by the contract)
- [ ] T071 [P] Document provenance record schema + verification protocol in `katas/020_data_provenance/README.md`: the `ProvenanceRecord` bundle binds every `Claim` to its `Source` via `source_url`, `source_name`, and `publication_date`; the verification protocol is (a) pydantic `Claim` construction validates at boundary, (b) JSON-schema validation against `contracts/claim.schema.json` at SDK hand-off, (c) `OrphanClaimLint.run` as terminal step of every aggregation pass, (d) AST lint proves absence of auto-resolution, (e) `aggregation_report.json` replay confirms the chain end-to-end (Principle VII self-audit anchor)
- [ ] T072 [P] Verify `specs/020-data-provenance/quickstart.md` matches implemented CLI flags, fixture paths, and audit file layout; update any drift (scenario→spec mapping table, fixture names, `LIVE_API=1` command)

### Validation

- [ ] T073 Run quickstart validation: execute every command in `specs/020-data-provenance/quickstart.md` top-to-bottom (`pytest tests/katas/020_data_provenance -v`, optional `LIVE_API=1` CLI run, inspection of `conflicts[]` and `orphan_claims[]` in `aggregation_report.json`); confirm all assertions pass
- [ ] T074 [P] Run `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` to refresh dashboard after adding `katas/020_data_provenance/` files and `tasks.md`
- [ ] T075 [P] Ensure `.specify/context.json` assertion-integrity hashes for US-001, US-002, US-003 feature files are present and locked (re-run `/iikit-04-testify` only if feature files changed; otherwise verify hashes match)
- [ ] T076 Full test sweep: `pytest tests/katas/020_data_provenance -v --strict-markers` green; AST lint (T042) green; 100% of emitted claims carry populated provenance across the labeled corpus (SC-001); 0 auto-resolved conflicts (SC-002); conflict-detection recall meets/exceeds target on the seeded set (SC-003); 100% orphan-claim rejection on the negative schema set (SC-004)

## Dependencies & Execution Order

- **Phase 1 (Setup, T001–T004)** → must complete before Phase 2
- **Phase 2 (Foundational, T005–T011)** → models, exceptions, canonical-key hasher, client seam, extraction-tool builder, schema loader, and audit writer block all user stories
- **Phase 3 (US1, T012–T031)** → depends on Phase 2; delivers MVP provenance-preserving extraction end-to-end
- **Phase 4 (US2, T032–T049)** → depends on Phase 3 (`ProvenanceAggregator.aggregate` + audit writer exist); conflict surfacing extends, not rewrites
- **Phase 5 (US3, T050–T067)** → depends on Phase 2 `extraction_tool.py` + Phase 3 default subagent; US3 tests may be written in parallel with US2 but implementation is sequenced after US2 so `aggregation_report.json` and `review_tasks.jsonl` exist for `OrphanClaimLint` to guard
- **Final Phase (T068–T076)** → depends on all user stories complete

User-story independence: any US can be verified in isolation via its own feature file + fixture set, but implementation order above gives the shortest green path.

## Parallel Opportunities

Within a single phase, tasks marked `[P]` touch disjoint files and may be run in parallel:

- **Phase 1**: T002, T003, T004 parallel (different config files)
- **Phase 2**: T007, T008, T009 parallel (distinct modules: canonical key, client, extraction tool)
- **Phase 3 tests**: T012, T013, T014, T015, T016, T024, T025, T026 parallel (feature copy + four fixtures + three unit tests — no overlap)
- **Phase 4 tests**: T032, T033, T034, T042, T043, T044 parallel (feature copy + two fixtures + lint + two integration tests)
- **Phase 5 tests**: T050, T051, T052, T059, T060, T061, T062 parallel (feature copy + two fixture sets + four unit/integration tests)
- **Final Phase docs**: T068, T069, T070, T071, T072 parallel (README, docstrings, why-comments, schema-and-protocol doc, quickstart verify touch disjoint files)
- **Final Phase validation**: T074, T075 parallel after T073

Step-definition files (T017–T023, T035–T041, T053–T058) are sequential within each file because they share a single Python module per feature.

## Implementation Strategy

1. Land **Phase 1 + Phase 2** in one PR or sitting — foundational, no aggregation logic yet.
2. Land **US1 MVP** (Phase 3) — kata runs end-to-end on the consistent-aggregation happy path and corroborating duplicates; every emitted `Claim` has provenance.
3. Land **US2 conflict surfacing** (Phase 4) — adds the observable proof that contradictions are never silently resolved; AST lint becomes the architectural guard against Principle VII regressions.
4. Land **US3 fail-closed defense** (Phase 5) — the schema-boundary payoff of Principle II NN: orphan claims and loosened schemas halt the pipeline.
5. Close with **Final Phase** — Principle VIII documentation, quickstart re-run, dashboard refresh.

Suggested commit cadence: one commit per phase checkpoint; additional commits for doc polish are fine.

## Notes

- Feature files in `tests/katas/020_data_provenance/features/` MUST be verbatim copies of the files in `specs/020-data-provenance/tests/features/`. Per assertion-integrity rule, never edit `.feature` files directly — re-run `/iikit-04-testify` if requirements change.
- The AST lint test (T042) is the load-bearing architectural guard for Principle VII (Provenance & Self-Audit anchor): it proves `aggregator.py` holds no auto-resolution heuristic. If it flakes or is deleted, the kata silently loses its anti-pattern defense.
- The orphan-claim lint (T063, T064) runs as the terminal step of every aggregation pass and is the second load-bearing guard: any `Claim` missing `source_name` halts emission of `aggregation_report.json` — partial output never leaks downstream (FR-002, SC-004).
- The tool-schema mirror test (T059) is the third load-bearing guard: if `build_claim_tool()["input_schema"]` drifts from `Claim.model_json_schema()`, adding a required field to the pydantic model would not propagate to the SDK call, silently re-opening the orphan-claim surface.
- Per plan.md §Complexity Tracking: concurrent subagent fan-out, vector-db claim similarity, retry budgets, and any form of automatic conflict resolution are deliberately NOT in scope; YAGNI until a future kata requires them.
- Every `[TS-NNN]` tag traces to a scenario in the copied `.feature` files; the step-definition tasks (T017–T023, T035–T041, T053–T058) cite the exact TS IDs for pytest-bdd scenario binding.
