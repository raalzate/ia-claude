# Tasks: Defensive Structured Extraction with JSON Schemas

**Input**: Design documents from `/specs/005-defensive-extraction/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] required on story tasks
- Traceability: `[TS-001, TS-002]`, never ranges

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton at `katas/kata_005_defensive_extraction/__init__.py` with module docstring declaring the kata objective (schema-governed extraction, zero fabrication).
- [ ] T002 Create test package skeleton at `tests/katas/kata_005_defensive_extraction/__init__.py` (empty, marks directory as test package).
- [ ] T003 Ensure `pyproject.toml` at repo root exposes `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd` in the `[dev]` extras (required by `plan.md` Technical Context). Add if missing; no-op if already declared by Kata 1.
- [ ] T004 [P] Add `runs/` to `.gitignore` if not already present (artifact directory per `plan.md` Storage).
- [ ] T005 [P] Create `tests/katas/kata_005_defensive_extraction/conftest.py` with the fixture loader stub, recorded-response client fixture, and `LIVE_API=1` gate. Signatures only; implementations land in later tasks.

---

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [ ] T006 Implement pydantic v2 `ExtractedRecord` model in `katas/kata_005_defensive_extraction/models.py` with `model_config = ConfigDict(extra="forbid")`, required fields (`subject`, `reported_at`), nullable optional fields (`nickname`, `location`, `status_details`), and `status: Literal["active","inactive","other","unclear"]`. Reference `data-model.md`.
- [ ] T007 Implement `model_validator(mode="after")` on `ExtractedRecord` in `katas/kata_005_defensive_extraction/models.py` enforcing the AmbiguityMarker pairing: when `status in {"other","unclear"}`, `status_details` MUST be a non-empty string (FR-005).
- [ ] T008 Implement `SchemaDefinition` pydantic model in `katas/kata_005_defensive_extraction/models.py` with fields `name`, `description`, `input_schema`, `required_fields`, `optional_fields`, `escape_options` per `data-model.md`.
- [ ] T009 Implement `AmbiguityMarker` pydantic model and `AmbiguityMarker.from_record(record, field_name)` classmethod in `katas/kata_005_defensive_extraction/models.py` (spec Key Entities, FR-005).
- [ ] T010 Implement `FabricationMetric` pydantic model and `FabricationMetric.compute(record, fixture_labels)` classmethod in `katas/kata_005_defensive_extraction/models.py` per `data-model.md` (SC-001, SC-004).
- [ ] T011 Implement thin injectable Anthropic client wrapper in `katas/kata_005_defensive_extraction/client.py` sharing the shape declared by Kata 1 (`specs/001-agentic-loop/plan.md`). Supports recorded-response injection for offline tests.
- [ ] T012 Author the seven labeled fixture cases under `tests/katas/kata_005_defensive_extraction/fixtures/` (`well_formed/`, `missing_optional/`, `ambiguous_enum/`, `contradictory/`, `empty_source/`, `out_of_enum_value/`, `mixed_language/`), each with `source.txt` and `expected.json` encoding `null_map` and `escape_map` per `quickstart.md`. `mixed_language/` supplies the fixture consumed by T039 for the `[TS-014]` mixed-language escape-enum assertion.
- [ ] T013 Implement fixture loader in `tests/katas/kata_005_defensive_extraction/conftest.py` that reads a fixture directory and returns `(source_text, FixtureLabels)` where `FixtureLabels` carries `null_map` and `escape_map`.
- [ ] T014 Copy the three locked feature files from `specs/005-defensive-extraction/tests/features/` to `tests/katas/kata_005_defensive_extraction/features/` (`schema_valid_extraction.feature`, `nullable_optional_fields.feature`, `ambiguity_escape_enum.feature`). Do NOT modify scenarios — they are assertion-integrity anchored.

**Checkpoint**: Foundational layer complete. `ExtractedRecord` validates, fixtures load, `.feature` files are in place. No user-story work can begin until this phase passes.

---

## Phase 3: User Story 1 — Well-Formed Source Produces Schema-Valid Record (P1) — MVP

**Goal**: A well-formed source yields a typed `ExtractedRecord` delivered via a schema-bound, forced tool call, with every required field non-null and extra keys rejected.

**Independent Test**: Feed the `well_formed` fixture to the extractor; assert the returned record validates, `tool_choice.type == "any"` was sent, and no extra keys are present.

### Tests for User Story 1

- [ ] T015 [P] [US1] Register the `schema_valid_extraction.feature` scenarios in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py` via `pytest-bdd` `scenarios(...)`.
- [ ] T016 [P] [US1] Author unit test `tests/katas/kata_005_defensive_extraction/unit/test_tool_choice_forced.py` asserting every outgoing `messages.create` request carries `tool_choice={"type": "any"}` (FR-002). Covers `[TS-002]` at contract level.
- [ ] T017 [P] [US1] Author unit test `tests/katas/kata_005_defensive_extraction/unit/test_extra_forbid.py` asserting `ExtractedRecord.model_validate({...extra_key...})` raises with `"extra_forbidden"` (FR-010). Covers `[TS-004]`.

### Implementation for User Story 1

- [ ] T018 [US1] Implement `build_extraction_tool(schema_def: SchemaDefinition) -> dict` in `katas/kata_005_defensive_extraction/extractor.py` returning the Anthropic tool dict whose `input_schema` is `ExtractedRecord.model_json_schema()` (FR-001).
- [ ] T019 [US1] Implement `run_extraction(source: str, client, schema_def) -> ExtractedRecord` in `katas/kata_005_defensive_extraction/extractor.py` that calls `messages.create` with `tool_choice={"type": "any"}`, selects the first `content` block whose `type == "tool_use"`, and validates `tool_use.input` through `ExtractedRecord.model_validate` (FR-002, FR-006).
- [ ] T020 [US1] Implement step defs for `[TS-001]` (returned record validates with zero errors; null rate on required == 0) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T021 [US1] Implement step defs for `[TS-002]` (response content block is `tool_use`; tool name equals declared; no free-text block consumed) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T022 [US1] Implement step defs for `[TS-003]` (every required field non-null, type matches declared JSON Schema type) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T023 [US1] Implement step defs for `[TS-004]` (model response with extra key → validation fails with `extra_forbidden`, no record returned) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T024 [US1] Implement step defs for `[TS-005]` (source omits required field → validation fails with missing-required-field error; no coerced-to-null record emitted) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T025 [US1] Implement step defs for `[TS-006]` (empty source → validation fails on at least one required field; no fabricated-defaults record emitted) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.

**Checkpoint**: US1 MVP complete. `pytest tests/katas/kata_005_defensive_extraction -v -k "US-001 or test_tool_choice_forced or test_extra_forbid"` passes against recorded fixtures.

---

## Phase 4: User Story 2 — Missing Optional Fields Return Null, Not Fabrications (P2)

**Goal**: Optional fields absent from the source come back as `null` via nullable union types — never a plausible-sounding invented value — and zero fabrications are observed across the labeled corpus.

**Independent Test**: Run the extractor against the labeled fixture corpus; assert for every fixture, every field in its `null_map` is `None`; assert corpus-wide `fabrication_count == 0` and mean `null_rate >= 0.99`.

### Tests for User Story 2

- [ ] T026 [P] [US2] Register the `nullable_optional_fields.feature` scenarios in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py` via `pytest-bdd` `scenarios(...)`.
- [ ] T027 [P] [US2] Author unit test `tests/katas/kata_005_defensive_extraction/unit/test_schema_lint.py` that walks `ExtractedRecord.model_fields.items()` and asserts every non-required field's annotation is a union including `NoneType` whose non-None arm is not a bare `str` (FR-004). Covers `[TS-008]`.
- [ ] T028 [P] [US2] Author unit test `tests/katas/kata_005_defensive_extraction/unit/test_fabrication_rate.py` that loads the full labeled corpus, computes `FabricationMetric` per fixture, and asserts `sum(fabrication_count) == 0` and `mean(null_rate) >= 0.99` (SC-001, SC-004). Covers `[TS-010, TS-011]`.

### Implementation for User Story 2

- [ ] T029 [US2] Implement `audit_corpus(extractor, fixtures) -> list[FabricationMetric]` in `katas/kata_005_defensive_extraction/audit.py` that runs extraction per fixture and produces one `FabricationMetric` each (SC-001, SC-004). Why-comment ties to FR-007.
- [ ] T030 [US2] Implement step defs for `[TS-007]` (absent optional returned as `null`; value is not `"unknown"` or any free-form guess) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T031 [US2] Implement step defs for `[TS-008]` backed by `test_schema_lint.py` — reference the lint test and assert it fails closed if any optional is reverted to bare `str` (FR-004) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T032 [US2] Implement step defs for `[TS-009]` (generated JSON Schema `type` array for `nickname`/`location`/`status_details` includes both `"null"` and `"string"`) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T033 [US2] Implement step defs for `[TS-010]` (for every fixture, every null_map field is `None`; total `fabrication_count == 0`) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T034 [US2] Implement step defs for `[TS-011]` (mean `null_rate >= 0.99` across corpus) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.

**Checkpoint**: US2 complete. Schema lint blocks the bare-`str` anti-pattern; fabrication audit is green. `pytest tests/katas/kata_005_defensive_extraction -v -k "US-002 or test_schema_lint or test_fabrication_rate"` passes.

---

## Phase 5: User Story 3 — Ambiguous Values Route to Escape Enum (P3)

**Goal**: Ambiguous, contradictory, mixed-language, or out-of-enum enumerated values route to `"other"` / `"unclear"` with the paired `status_details` field populated; 100% of ambiguous fixtures escape-route; validation failures surface the offending field path.

**Independent Test**: Feed the four ambiguity fixtures (`ambiguous_enum`, `contradictory`, `out_of_enum_value`, plus a mixed-language scenario if present); assert `status` is an escape option and `status_details` is non-empty; assert no ambiguous fixture resolves to a concrete enum value.

### Tests for User Story 3

- [ ] T035 [P] [US3] Register the `ambiguity_escape_enum.feature` scenarios in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py` via `pytest-bdd` `scenarios(...)`.

### Implementation for User Story 3

- [ ] T036 [US3] Implement `AmbiguityMarker.from_record` consumers in `katas/kata_005_defensive_extraction/audit.py`: helper that, given an `ExtractedRecord`, returns the list of `AmbiguityMarker` instances for every field currently holding an escape value (FR-005).
- [ ] T037 [US3] Implement step defs for `[TS-012]` (out-of-enum source → `status == "other"`; `status_details` non-empty capturing raw value) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T038 [US3] Implement step defs for `[TS-013]` (contradictory source → escape option selected; `status_details` preserves both values verbatim or summarized) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T039 [US3] Implement step defs for `[TS-014]` (mixed-language source → escape option; `status_details` notes the language mix) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`, loading the `mixed_language/` fixture authored by T012.
- [ ] T040 [US3] Implement step defs for `[TS-015]` (across the ambiguity fixture set, 100% of flagged enumerated fields resolve to an escape option; zero resolve to concrete values) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py` (SC-003).
- [ ] T041 [US3] Implement step defs for `[TS-016]` (record with escape status but empty `status_details` raises `ValidationError` via the `model_validator(mode="after")`) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py`.
- [ ] T042 [US3] Implement step defs for `[TS-017]` (on validation failure, the extractor raises with a payload that names the offending field path and states the reason) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py` (FR-008).
- [ ] T043 [US3] Implement step defs for `[TS-018]` (`SchemaDefinition` snapshot exposes `required_fields`, `optional_fields`, and `escape_options` per enumerated field) in `tests/katas/kata_005_defensive_extraction/step_defs/test_defensive_extraction_steps.py` (FR-009).
- [ ] T044 [US3] Wire `SchemaDefinition` construction in `katas/kata_005_defensive_extraction/extractor.py` so `required_fields`, `optional_fields`, and `escape_options` are populated from `ExtractedRecord` introspection at module load time (FR-001, FR-009).

**Checkpoint**: US3 complete. All 18 `@TS-NNN` scenarios green; the kata passes end-to-end against recorded fixtures.

---

## Final Phase: Polish & Cross-Cutting Concerns

### Runner & CLI

- [ ] T045 Implement CLI entrypoint in `katas/kata_005_defensive_extraction/runner.py` exposing `python -m katas.kata_005_defensive_extraction.runner --model claude-opus-4-7 --source path/to/source.txt` and writing `runs/<session-id>/extraction.jsonl` per `quickstart.md`.

### Documentation (Principle VIII — Mandatory)

- [ ] T046 [P] Write `katas/kata_005_defensive_extraction/README.md`: kata objective, defensive-extraction architecture, anti-pattern defense (bare-`str` optionals + forced enum coercion), run instructions (recorded + LIVE_API), reflection section answering the three prompts in `quickstart.md` (Principle VIII).
- [ ] T047 [P] Add module-level docstrings to `katas/kata_005_defensive_extraction/models.py`, `extractor.py`, `client.py`, `audit.py`, and `runner.py` explaining each file's defensive role (schema source-of-truth, forced tool choice, fabrication audit, etc.).
- [ ] T048 [P] Add *why*-comments on `build_extraction_tool`, `run_extraction`, the `ExtractedRecord` `model_validator`, `FabricationMetric.compute`, `AmbiguityMarker.from_record`, and the schema-lint walker — each tying to its FR-XXX / SC-XXX anchor (Principle VIII).
- [ ] T049 [P] Document the extraction fallback ladder in `katas/kata_005_defensive_extraction/README.md`: schema-first (tool call validates), then structured fallbacks (escape enum + details, surfaced `ValidationError`) — explicitly call out that prose parsing is NOT a fallback step.
- [ ] T050 [P] Verify `specs/005-defensive-extraction/quickstart.md` — confirm every section (Install, recorded run, live run, fixture table, scenario map, Completion Standards checklist) matches the implemented layout.
- [ ] T051 Run quickstart validation: execute `pytest tests/katas/kata_005_defensive_extraction -v` from repo root and confirm every `@TS-NNN` scenario and unit test passes; capture output.

### Standard Polish

- [ ] T052 [P] Confirm `katas/kata_005_defensive_extraction/` has no imports outside `anthropic`, `pydantic`, stdlib (no extraneous deps per `plan.md` Complexity Tracking).
- [ ] T053 [P] Run `ruff check katas/kata_005_defensive_extraction tests/katas/kata_005_defensive_extraction` and fix any findings.
- [ ] T054 [P] Run `mypy katas/kata_005_defensive_extraction` (if mypy is configured in `pyproject.toml`) and fix any findings; the nullable-union types are the point of the kata and must type-check cleanly.
- [ ] T055 Regenerate the dashboard: `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` (per project rule `dashboard-refresh`).

---

## Dependencies & Execution Order

- **Setup (T001–T005)** must complete before Foundational.
- **Foundational (T006–T014)** blocks every user-story phase. `T006`→`T007`→`T008`→`T009`→`T010` are sequential (same file, `models.py`). `T011`, `T012`, `T013`, `T014` may run in parallel with each other once `T006–T010` are done.
- **US1 (T015–T025)** depends on Foundational only.
- **US2 (T026–T034)** depends on Foundational and reuses the extractor from US1 (`T019`); author the lint (`T027`) and audit tests (`T028`) in parallel with US1 if the extractor is stubbed early.
- **US3 (T035–T044)** depends on Foundational, the `model_validator` from `T007`, and the extractor from `T019`.
- **Polish (T045–T055)** runs last. `T051` depends on every test having been authored.

## Parallel Opportunities

- `[P]` markers above. Notably:
  - T004 and T005 in Setup.
  - T011, T012, T013, T014 in Foundational (after models are in place).
  - T015, T016, T017 in US1 tests.
  - T026, T027, T028 in US2 tests (different files).
  - T046, T047, T048, T049, T050, T052, T053, T054 in the final Polish phase.
- Within a story, step-def tasks (T020–T025, T030–T034, T037–T043) all write to the same file (`test_defensive_extraction_steps.py`) and are therefore **sequential**, not parallel.

## Implementation Strategy (MVP)

1. Land Setup + Foundational (T001–T014). `.feature` files are copied verbatim and lock the assertion integrity anchor.
2. Land US1 (T015–T025) for the P1 MVP slice: schema-bound forced tool call + happy-path validation. This is the earliest demoable point.
3. Land US2 (T026–T034) to close the fabrication anti-pattern — the kata's primary defect target. Schema lint + fabrication audit are the gates.
4. Land US3 (T035–T044) to close the ambiguity anti-pattern. Escape-enum + `status_details` invariant + validation-failure surfacing.
5. Polish (T045–T055): CLI, documentation (Principle VIII), quickstart validation, dashboard refresh.

## Notes

- Every `@TS-NNN` scenario in `tests/features/*.feature` has at least one implementation task citing its TS ID; see T020–T025 (US1: TS-001..TS-006), T030–T034 (US2: TS-007..TS-011), T037–T043 (US3: TS-012..TS-018).
- Traceability uses individual IDs (`[TS-007]`, `[TS-010, TS-011]`), never ranges — per the rule at the top of this file.
- `.feature` files are treated as read-only per `assertion-integrity.md`. If requirements change, re-run `/iikit-04-testify`; do not edit scenarios by hand.
- The kata is intentionally small (~250–400 LOC production + comparable test code per `plan.md`). Resist adding retries, JSON-mode fallbacks, multi-shot extraction, or DB persistence — the Complexity Tracking section explicitly excludes these.
- Recorded-response mode is the default (`LIVE_API` unset). CI never calls the live API.
