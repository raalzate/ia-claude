# Tasks: PostToolUse Cognitive Load Normalization

**Input**: Design documents from `/specs/003-posttool-normalize/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallelizable, [USn] on story tasks
- Traceability: `[TS-001, TS-002]`, never "TS-001 through TS-005"

---

## Phase 1: Setup

- [ ] T001 Create package directory `katas/kata_003_posttool_normalize/` with `__init__.py` declaring module docstring for Kata 3 (PostToolUse normalization)
- [ ] T002 Create test directory tree `tests/katas/kata_003_posttool_normalize/{features,step_defs,unit,fixtures}` with empty `__init__.py` files where needed
- [ ] T003 [P] Add `lxml`, `pydantic>=2`, `anthropic`, `pytest`, `pytest-bdd` to `pyproject.toml` `[dev]` extras (baseline already declares shared deps; confirm `lxml` is newly added per plan.md Complexity Tracking)
- [ ] T004 [P] Copy locked Gherkin feature files from `specs/003-posttool-normalize/tests/features/*.feature` into `tests/katas/kata_003_posttool_normalize/features/` (four feature files: `clean_normalized_output.feature`, `baseline_vs_normalized_comparison.feature`, `schema_contract_conformance.feature`, `status_map_extension.feature`)
- [ ] T005 [P] Create `tests/katas/kata_003_posttool_normalize/conftest.py` skeleton exposing fixture loader, session-scoped audit-log temp dir, and token-count harness entry points

---

## Phase 2: Foundational

- [ ] T006 Define pydantic v2 model `RawToolResponse` in `katas/kata_003_posttool_normalize/models.py` with fields `tool_use_id`, `tool_name`, `raw_bytes`, `content_type`, `received_at` (data-model.md §RawToolResponse)
- [ ] T007 Define pydantic v2 model `StatusMapping` in `katas/kata_003_posttool_normalize/models.py` with `entries: dict[str, str]` and `unknown_marker: Literal["unknown"]`, including validator rejecting `"unknown"` as a value (FR-003)
- [ ] T008 Define pydantic v2 models `StatusField` and `NormalizedPayload` in `katas/kata_003_posttool_normalize/models.py` including `field_validator` on every string-typed field that rejects `<`, `>`, and CDATA sentinels (FR-004, SC-002)
- [ ] T009 Define pydantic v2 model `AuditRecord` in `katas/kata_003_posttool_normalize/models.py` with fields from data-model.md §AuditRecord (session_id, tool_use_id, tool_name, received_at, raw_bytes_b64, raw_sha256, parse_status, normalized_token_count, raw_token_count)
- [ ] T010 [P] Create `katas/kata_003_posttool_normalize/tokens.py` implementing a token counter that uses the `anthropic` tokenizer when available and falls back to a documented stub counter (plan.md D-006, SC-001)
- [ ] T011 [P] Add JSON Schema validation helper in `tests/katas/kata_003_posttool_normalize/conftest.py` that loads the four schemas from `specs/003-posttool-normalize/contracts/` and exposes a `validate_against(schema_name, instance)` fixture
- [ ] T012 [P] Author fixture `tests/katas/kata_003_posttool_normalize/fixtures/happy_path.json` with representative legacy XML + known status codes
- [ ] T013 [P] Author fixture `tests/katas/kata_003_posttool_normalize/fixtures/malformed_markup.json` (unclosed tags / truncated block, Edge #1)
- [ ] T014 [P] Author fixture `tests/katas/kata_003_posttool_normalize/fixtures/unknown_code.json` (status code absent from `STATUS_MAPPING`, Edge #2)
- [ ] T015 [P] Author fixture `tests/katas/kata_003_posttool_normalize/fixtures/empty_response.json` (no body, Edge #3)
- [ ] T016 [P] Author fixture `tests/katas/kata_003_posttool_normalize/fixtures/oversized_payload.json` (well beyond typical, Edge #4)
- [ ] T017 [P] Author fixture `tests/katas/kata_003_posttool_normalize/fixtures/nested_blocks.json` (legacy-in-legacy + multi-code, Edge #5)

---

## Phase 3: User Story 1 — Clean minimal JSON replaces raw legacy output (P1) [US1]

**Goal**: PostToolUse hook intercepts every legacy tool response, emits a schema-conformant `NormalizedPayload`, and appends only that payload to conversation history — never the raw legacy markup.

**Independent Test**: Call the legacy data tool with a representative fixture, capture the message appended to history, verify it validates against `NormalizedPayload` schema, contains no legacy markup, and all known codes are resolved.

### Tests for US1 (write first — TDD, Constitution V)

- [ ] T018 [P] [US1] Implement pytest-bdd step defs for `clean_normalized_output.feature` in `tests/katas/kata_003_posttool_normalize/step_defs/test_clean_normalized_output_steps.py` covering [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007]
- [ ] T019 [P] [US1] Implement pytest-bdd step defs for `schema_contract_conformance.feature` in `tests/katas/kata_003_posttool_normalize/step_defs/test_schema_contract_conformance_steps.py` covering [TS-030, TS-031, TS-032, TS-035] (P1 scenarios only; P2 scenarios TS-033, TS-034 covered in US2 step defs)
- [ ] T020 [P] [US1] Write unit test `tests/katas/kata_003_posttool_normalize/unit/test_normalizer_unknown_code.py` asserting `{"code": "unknown", "raw": "<arcane-code>"}` shape for absent codes (FR-003, SC-003) [TS-004]
- [ ] T021 [P] [US1] Write unit test `tests/katas/kata_003_posttool_normalize/unit/test_hook_markup_leak.py` scanning every string field of emitted `NormalizedPayload` for `<`, `>`, CDATA sentinels across all fixtures (FR-004, SC-002) [TS-002, TS-032]

### Implementation for US1

- [ ] T022 [US1] Implement defused XML parser in `katas/kata_003_posttool_normalize/parser.py` wrapping `lxml.etree.XMLParser(resolve_entities=False, no_network=True, recover=True)` exposing `parse(raw_bytes) -> (dict, parse_status)` (FR-007, Edge #1)
- [ ] T023 [US1] Implement `STATUS_MAPPING: dict[str, str]` constant and pure `normalize(raw: RawToolResponse, mapping: StatusMapping) -> NormalizedPayload` function in `katas/kata_003_posttool_normalize/normalizer.py`, resolving known codes, emitting `"unknown"` marker with raw preserved for misses, flattening nested blocks (FR-003, FR-007, Edge #5)
- [ ] T024 [US1] Implement `PostToolUseHook` protocol and `LegacyDBNormalizer` class in `katas/kata_003_posttool_normalize/hook.py` that (a) constructs `RawToolResponse`, (b) calls normalizer, (c) returns `NormalizedPayload` as the message appended to conversation history (FR-001, FR-006)
- [ ] T025 [US1] Wire empty-response handling in `katas/kata_003_posttool_normalize/normalizer.py` to produce `parse_status="empty"` `NormalizedPayload` with empty content dict (FR-007, Edge #3)
- [ ] T026 [US1] Wire malformed-markup handling in `katas/kata_003_posttool_normalize/normalizer.py` to produce `parse_status="degraded"` `NormalizedPayload` with diagnostic notes (FR-007, Edge #1)

**Checkpoint US1**: `pytest tests/katas/kata_003_posttool_normalize/features/clean_normalized_output.feature tests/katas/kata_003_posttool_normalize/unit/test_normalizer_unknown_code.py tests/katas/kata_003_posttool_normalize/unit/test_hook_markup_leak.py` passes. Appending the hook output to a stub conversation history shows only `NormalizedPayload` instances, no legacy markup.

---

## Phase 4: User Story 2 — Baseline vs. normalized comparison (P2) [US2]

**Goal**: Running the kata with the hook off reproduces the anti-pattern (raw legacy markup in context); running with hook on demonstrates ≥70% token reduction and fewer downstream misinterpretations, with audit trail intact for both.

**Independent Test**: Toggle the hook on/off across two identical runs over the same fixture; assert run B token count ≤ 30% of run A, strictly fewer misinterpretation events in run B, and audit records present for both.

### Tests for US2

- [ ] T027 [P] [US2] Implement pytest-bdd step defs for `baseline_vs_normalized_comparison.feature` in `tests/katas/kata_003_posttool_normalize/step_defs/test_baseline_vs_normalized_steps.py` covering [TS-010, TS-011, TS-012, TS-013, TS-014, TS-015]
- [ ] T028 [P] [US2] Extend `tests/katas/kata_003_posttool_normalize/step_defs/test_schema_contract_conformance_steps.py` (or sibling file) with step defs for [TS-033, TS-034] covering audit schema validation + SHA-256 roundtrip
- [ ] T029 [P] [US2] Write unit test `tests/katas/kata_003_posttool_normalize/unit/test_audit_roundtrip.py` computing SHA-256 of every fixture, running through hook, reopening `audit.jsonl`, asserting byte-for-byte match (FR-005, SC-004) [TS-034]
- [ ] T030 [P] [US2] Write unit test `tests/katas/kata_003_posttool_normalize/unit/test_token_reduction.py` asserting averaged normalized/raw token ratio ≤ 0.30 across the six fixtures (SC-001) [TS-012]

### Implementation for US2

- [ ] T031 [US2] Implement append-only JSONL `AuditLog` writer in `katas/kata_003_posttool_normalize/audit.py` with `write(record: AuditRecord)` + `fsync` on close, one line per record, path `runs/<session-id>/audit.jsonl` (FR-005)
- [ ] T032 [US2] Integrate `AuditLog` write into `LegacyDBNormalizer.__call__` in `katas/kata_003_posttool_normalize/hook.py` so the audit line is flushed BEFORE the normalized message is appended to history (FR-005 crash-safety invariant)
- [ ] T033 [US2] Implement comparison runner in `katas/kata_003_posttool_normalize/runner.py` accepting `--fixture`, `--compare`, `--model`, producing `runs/<session-id>/comparison.json` with `{raw_tokens, normalized_tokens, reduction_ratio, markup_leaks_baseline, markup_leaks_normalized}` (US2-AS1, US2-AS2, US2-AS3)
- [ ] T034 [US2] Add baseline (hook-disabled) code path in `katas/kata_003_posttool_normalize/runner.py` that injects raw fixture bytes directly into the stub conversation history — the documented anti-pattern (US2-AS3, [TS-010])
- [ ] T035 [US2] Implement downstream-misinterpretation counter in `katas/kata_003_posttool_normalize/runner.py` comparing model decisions against a fixture-declared expected-decision set (US2-AS2, [TS-013])

**Checkpoint US2**: `pytest tests/katas/kata_003_posttool_normalize/features/baseline_vs_normalized_comparison.feature tests/katas/kata_003_posttool_normalize/unit/test_audit_roundtrip.py tests/katas/kata_003_posttool_normalize/unit/test_token_reduction.py` passes. `python -m katas.kata_003_posttool_normalize.runner --fixture happy_path --compare` writes a `comparison.json` showing the reduction ratio and zero markup leaks on the normalized side.

---

## Phase 5: User Story 3 — Status map extension as pure data change (P3) [US3]

**Goal**: A practitioner adds one entry to `STATUS_MAPPING`; a previously-unknown code now resolves to its label with no edits to prompts, model settings, or agent wiring.

**Independent Test**: Run `unknown_code.json` through the hook, observe `status.code == "unknown"`, add the one entry, re-run, observe the resolved label, diff the working tree — only `normalizer.py` appears.

### Tests for US3

- [ ] T036 [P] [US3] Implement pytest-bdd step defs for `status_map_extension.feature` in `tests/katas/kata_003_posttool_normalize/step_defs/test_status_map_extension_steps.py` covering [TS-020, TS-021, TS-022]
- [ ] T037 [P] [US3] Write unit test `tests/katas/kata_003_posttool_normalize/unit/test_mapping_extension.py` exercising the "add one entry, observe resolved label, no other module touched" loop programmatically (US3-AS1, US3-AS2) [TS-020, TS-022]

### Implementation for US3

- [ ] T038 [US3] Expose `StatusMapping.extend(code, label) -> StatusMapping` helper returning a new frozen mapping (immutability preserved) in `katas/kata_003_posttool_normalize/normalizer.py` so test code can demonstrate the single-point-of-change without mutating the module constant
- [ ] T039 [US3] Confirm `katas/kata_003_posttool_normalize/normalizer.py` is the ONLY import edge touched when adding a mapping — add a unit assertion (importing `hook.py`, `parser.py`, `models.py` does not require re-running after a mapping edit) backing [TS-021]

**Checkpoint US3**: `pytest tests/katas/kata_003_posttool_normalize/features/status_map_extension.feature tests/katas/kata_003_posttool_normalize/unit/test_mapping_extension.py` passes. Git diff after adding one entry shows only `katas/kata_003_posttool_normalize/normalizer.py` modified.

---

## Final Phase: Polish & Cross-Cutting Concerns

### Documentation (Principle VIII — mandatory)

- [ ] T040 [P] Author `katas/kata_003_posttool_normalize/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — PostToolUse hooks, schema-first parsing, defensive XML parsing (defused parser), structured-payload normalization, append-only audit ledger, token-reduction measurement, recorded-vs-LIVE_API seam — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`runner` → `PostToolUseHook` → `parser` → `normalizer` → `models.NormalizedPayload` → `audit` ledger → tokens metric) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — hook-after-tool, parse-then-normalize pipeline, append-only audit, raw-vs-normalized diff measurement — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, V Test-First, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — PostToolUse hook contract (Raw → Audit → Parse → Map → NormalizedPayload → history), normalization pipeline mirroring plan.md Architecture, `STATUS_MAPPING`, audit ledger crash-safety guarantees (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T041 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/hook.py` explaining its role as the PostToolUse interception point (FR-001, FR-006)
- [ ] T042 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/normalizer.py` explaining its role as the pure normalization function + `STATUS_MAPPING` owner (FR-003)
- [ ] T043 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/parser.py` explaining its role as the defused malformed-tolerant XML boundary (FR-007)
- [ ] T044 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/models.py` explaining each entity's role in the normalization pipeline (FR-002)
- [ ] T045 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/audit.py` explaining its role as the crash-safe append-only raw-payload ledger (FR-005, SC-004)
- [ ] T046 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/tokens.py` explaining its role in measuring SC-001 reduction ratio
- [ ] T047 [P] Add module-level docstring to `katas/kata_003_posttool_normalize/runner.py` explaining its role as the baseline-vs-normalized comparison harness (US2)
- [ ] T048 [P] Add why-comments on non-trivial functions across `hook.py`, `normalizer.py`, `parser.py`, `audit.py` tying each branch / validator / guard to its FR-XXX / SC-XXX / anti-pattern (Principle VIII)

### Quickstart verification

- [ ] T050 [P] Verify every step of `specs/003-posttool-normalize/quickstart.md` walkthrough works as written: install, fixture run, live run gated by `LIVE_API=1`, `jq` anti-pattern defense checks, scenario→spec table accuracy
- [ ] T051 Run quickstart validation end-to-end: `pytest tests/katas/kata_003_posttool_normalize -v` and `python -m katas.kata_003_posttool_normalize.runner --fixture happy_path --compare`, confirming every artifact listed in quickstart §Artifacts is produced

### Standard polish

- [ ] T052 [P] Lint `katas/kata_003_posttool_normalize/` and `tests/katas/kata_003_posttool_normalize/` with ruff/black (or project linter), fix findings
- [ ] T053 [P] Run coverage on `katas/kata_003_posttool_normalize/`; ensure ≥90% branch coverage on `hook.py`, `normalizer.py`, `parser.py`, `audit.py` (Constitution Kata Completion Standards)
- [ ] T054 Performance check: normalize each fixture in < 50 ms on dev hardware (plan.md Performance Goals); record in the notebook Reflection cell
- [ ] T055 Confirm assertion-integrity hashes in `specs/003-posttool-normalize/context.json` match the locked test set — pre-commit hook enforces; DO NOT bypass, re-run `/iikit-04-testify` if mismatched
- [ ] T056 [P] Write unit test `tests/katas/kata_003_posttool_normalize/unit/test_normalized_payload_schema_closed.py` asserting that `NormalizedPayload.model_json_schema()` emits `additionalProperties: false` at the top level and on every nested object schema — operationalizes the FR-002 "bounded field set" guarantee beyond `extra="forbid"` (FR-002)

---

## Dependencies & Execution Order

- **Setup (T001–T005)** must complete before any other phase.
- **Foundational (T006–T017)** must complete before US1/US2/US3 tests and implementation. T006–T009 are sequential within `models.py` but can be one commit. Fixture authoring (T012–T017) is parallelizable with model definitions.
- **US1 (T018–T026)** depends on Foundational. Within US1: tests (T018–T021) before implementation (T022–T026) per Constitution V. T022 (parser) and T023 (normalizer) must land before T024 (hook) and before T025/T026 (empty + degraded handling).
- **US2 (T027–T035)** depends on US1 being green (hook must emit `NormalizedPayload` before audit integration is meaningful). T031 (audit writer) precedes T032 (hook integration). T033 (runner) precedes T034 (baseline path) and T035 (misinterpretation counter).
- **US3 (T036–T039)** depends on US1 (normalizer + `STATUS_MAPPING`). Independent of US2.
- **Polish (T040–T055)** depends on all prior phases. T051 (quickstart run) depends on T050 (walkthrough verify). T053 (coverage) depends on all tests existing. T055 (assertion integrity) is last — it gates the commit.

Phases 3 (US1) → 4 (US2) → 5 (US3) follow priority order; each phase is an independently-deliverable MVP increment.

---

## Parallel Opportunities

- **Setup**: T003, T004, T005 run in parallel after T001/T002.
- **Foundational**: T010, T011, and all fixture tasks T012–T017 run in parallel after T006–T009.
- **US1 tests**: T018, T019, T020, T021 all parallelizable (different files).
- **US2 tests**: T027, T028, T029, T030 all parallelizable (different files).
- **US3 tests**: T036, T037 parallelizable.
- **Docs**: T040–T048 all parallelizable (different files / disjoint cells of the notebook).
- **Polish**: T050, T052, T053 parallelizable; T051 and T054 serial.

---

## Implementation Strategy (MVP)

1. **MVP = US1 only (T001–T026)**: a working PostToolUse hook that emits a schema-conformant `NormalizedPayload` for every fixture, with legacy markup fully stripped and known codes resolved. Satisfies FR-001, FR-002, FR-003, FR-004, FR-006, FR-007 against fixtures.
2. **Increment 1 = + US2 (T027–T035)**: add audit log + baseline/normalized comparison runner, surfacing SC-001 token-reduction evidence and SC-004 byte-for-byte audit recovery. Makes the anti-pattern measurable.
3. **Increment 2 = + US3 (T036–T039)**: validate that extending the status map is a pure data change — proves the design scales.
4. **Finalize = Polish (T040–T055)**: documentation, quickstart validation, lint, coverage, performance, assertion-integrity check. Ship the kata.

Each increment is independently testable (see per-phase Independent Test) and constitutes a committable slice under FDD vertical delivery.

---

## Notes

- All file paths are absolute relative to repo root; prefixing with `/Users/raul.alzate/Documents/maestria/maestria/project/ia-claude/` resolves to the workspace.
- `lxml` is the only newly-introduced dependency vs. Kata 1 baseline (justified in plan.md Complexity Tracking).
- FR-004 is absolute: any test that observes `<`, `>`, or a CDATA sentinel in any string field of any `NormalizedPayload` fails closed and fails the build. Do not weaken the validator to pass a test; fix the production code.
- FR-003 is absolute: never emit a guessed label. The unknown marker is `{"code": "unknown", "raw": "<arcane-code>"}` — literal `"unknown"` as the resolved value is reserved for this miss path.
- SC-001 is measured as an AVERAGE across the six fixtures, not per-fixture — tiny empty payloads may individually beat or miss the threshold.
- Assertion integrity: DO NOT modify `.feature` files or `test-specs.md` directly — re-run `/iikit-04-testify` if requirements change (Constitution Assertion Integrity rule).
- After modifying any file under `specs/` or project root, regenerate the dashboard per `.tessl/tiles/.../rules/dashboard-refresh.md`.
