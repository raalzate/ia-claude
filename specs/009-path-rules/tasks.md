# Tasks: Path-Scoped Conditional Rules

**Input**: Design documents from `/specs/009-path-rules/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] on story tasks
- Traceability: `[TS-001, TS-002]`, never prose ranges

## Phase 1: Setup

- [ ] T001 Create source tree `katas/009_path_rules/` with empty `__init__.py`, and mirrored test tree `tests/katas/009_path_rules/{unit,contract,integration,features,step_defs,fixtures}/` with empty `conftest.py`.
- [ ] T002 [P] Add `pyyaml`, `pydantic>=2`, `pytest`, `pytest-bdd` to workshop dependencies (edit `pyproject.toml` `[project.optional-dependencies].dev`); pin `pyyaml` usage to `safe_load` only (per plan Technical Context).
- [ ] T003 [P] Register `pytest-bdd` discovery of `tests/katas/009_path_rules/features/path_rules.feature` in `tests/katas/009_path_rules/conftest.py` via `scenarios("features/path_rules.feature")`.
- [ ] T004 [P] Copy the three approved `.feature` files from `specs/009-path-rules/tests/features/` into `tests/katas/009_path_rules/features/` (`testing_rules_auto_inject.feature`, `zero_tokens_on_unrelated_edits.feature`, `new_rule_file_activation.feature`) — verbatim, DO NOT MODIFY.
- [ ] T005 [P] Copy the three JSON Schemas from `specs/009-path-rules/contracts/` into `tests/katas/009_path_rules/contract/schemas/` so contract tests resolve local paths without traversing `specs/`.

## Phase 2: Foundational

- [ ] T006 Define pydantic v2 models in `katas/009_path_rules/models.py`: `RuleFile` (with `path`, `filename`, `paths: list[PathPattern]`, `precedence: int = 1000`, `body: str`, `body_byte_size: int`), `PathPattern` (`glob`, `owning_rule`), `ActiveRuleSet` (`turn_id`, `edited_file_paths`, `members`, `events`, `total_body_bytes`), `MatchingEvent` (`turn_id`, `timestamp`, `edited_path`, `rule_file`, `matched_pattern`, `precedence`), `LoaderDiagnostic` (`severity`, `code`, `rule_file`, `message`). Enforce invariants from `data-model.md`.
- [ ] T007 Define `FrontmatterError(Exception)` in `katas/009_path_rules/frontmatter.py` with `path`, `reason: Literal[...]` (closed set from data-model.md), `detail`. Export the literal set as `FrontmatterReason`.
- [ ] T008 Implement YAML frontmatter parser `parse_frontmatter(path: pathlib.Path) -> tuple[dict, str]` in `katas/009_path_rules/frontmatter.py` using `yaml.safe_load`; raise `FrontmatterError(reason="no_frontmatter_fence")` when the opening `---` is absent; raise `reason="yaml_parse_error"` on `yaml.YAMLError`.
- [ ] T009 Implement glob matcher `match(edited_path: str, pattern: str) -> bool` in `katas/009_path_rules/matcher.py` following data-model.md rule: normalize to `/`, use `fnmatch.fnmatchcase` when pattern contains `**`, else `pathlib.PurePath.match`; case-sensitive.
- [ ] T010 Implement precedence resolver `resolve_precedence(rules: list[RuleFile]) -> list[RuleFile]` in `katas/009_path_rules/matcher.py`: stable sort by `(precedence ascending, filename ascending)`, deduplicate by `filename`.
- [ ] T011 Implement JSONL audit writer `AuditWriter` in `katas/009_path_rules/audit.py` appending one line per `MatchingEvent` to `runs/<session-id>/rule-activation.jsonl`, mirroring Kata 1's `events.py` append-only shape.

## Phase 3: User Story 1 — Testing rules auto-inject on test edits (P1)

**Goal**: `.claude/rules/testing.md` activates exactly when the turn edits a file matching its `paths` glob, and only then.

**Independent Test**: `pytest tests/katas/009_path_rules/features/testing_rules_auto_inject.feature -v` passes with scenarios `@TS-001`..`@TS-005` green, using fixture `tests/katas/009_path_rules/fixtures/rules/single_match/`.

### Tests

- [ ] T012 [P] [US1] Create fixture tree `tests/katas/009_path_rules/fixtures/rules/single_match/.claude/rules/testing.md` with frontmatter `paths: ["**/*.test.tsx"]` and a non-trivial body.
- [ ] T013 [P] [US1] Create fixture tree `tests/katas/009_path_rules/fixtures/rules/multi_rule_files/.claude/rules/{testing.md,api-conventions.md,styles.md}` — only `testing.md` targets `**/*.test.tsx`; others declare non-matching globs. Supports `@TS-002`.
- [ ] T014 [US1] Implement step definitions for `@TS-001` in `tests/katas/009_path_rules/step_defs/test_path_rules_steps.py`: fixtures-dir `given`, edit-file `when`, active-rule-set-contains + audit-log-records `then`. [TS-001]
- [ ] T015 [US1] Implement step definitions for `@TS-002` asserting exclusivity across multi-rule fixtures and single audit entry. [TS-002]
- [ ] T016 [P] [US1] Implement step definition `Scenario Outline` handler for `@TS-003` parameterizing `edited_path` against single-match fixture. [TS-003]
- [ ] T017 [US1] Implement step definition for `@TS-004`: two `.test.tsx` edits, one rule member, two `MatchingEvent` rows. [TS-004]
- [ ] T018 [P] [US1] Add contract test `tests/katas/009_path_rules/contract/test_schema_rule_activation_event.py` validating emitted JSONL lines against `contracts/rule-activation-event.schema.json`; wired from step for `@TS-005`. [TS-005]

### Implementation

- [ ] T019 [US1] Implement `PathScopedRuleLoader` in `katas/009_path_rules/loader.py`: `__init__(rules_dir: pathlib.Path)` discovers `*.md`, calls `parse_frontmatter`, constructs `RuleFile`s — FrontmatterError bubbles.
- [ ] T020 [US1] Implement `PathScopedRuleLoader.activate(turn_id: str, edited_file_paths: list[str]) -> ActiveRuleSet`: fan-out match, build `MatchingEvent` per (edited_path × matching RuleFile), call `resolve_precedence` for `members`, set `total_body_bytes`. [TS-001, TS-002, TS-003, TS-004]
- [ ] T021 [US1] Wire `AuditWriter` into `PathScopedRuleLoader.activate` so every `MatchingEvent` is emitted as JSONL immediately (schema-locked by `rule-activation-event.schema.json`). [TS-005]

**Checkpoint**: US1 tests (`@TS-001`..`@TS-005`) all pass. Kata delivers the P1 headline behavior.

## Phase 4: User Story 2 — No rule tokens spent on unrelated edits (P2)

**Goal**: Turns that edit only non-matching files produce an empty `ActiveRuleSet` with `total_body_bytes == 0`, and adding new rule files does not change token cost for unmatched turns.

**Independent Test**: `pytest tests/katas/009_path_rules/features/zero_tokens_on_unrelated_edits.feature -v` passes `@TS-006`..`@TS-011` green with fixture `tests/katas/009_path_rules/fixtures/rules/no_match/`.

### Tests

- [ ] T022 [P] [US2] Create fixture `tests/katas/009_path_rules/fixtures/rules/no_match/.claude/rules/api.md` declaring `paths: ["src/api/**/*.ts"]` (no match for `README.md`).
- [ ] T023 [US2] Implement step definitions for `@TS-006` in `test_path_rules_steps.py`: edit `README.md` → `ActiveRuleSet.members == []` and audit log has zero lines for the turn. [TS-006]
- [ ] T024 [US2] Implement step definitions for `@TS-007`: composed prompt byte size equals baseline and `total_body_bytes == 0`. [TS-007]
- [ ] T025 [US2] Implement step definitions for `@TS-008`: read-only tool call path is NOT fed into `edited_file_paths`; active rule set is empty. [TS-008]
- [ ] T026 [P] [US2] Implement `Scenario Outline` step for `@TS-009` parameterizing `(inert_pattern, unrelated_path)` pairs; assert diagnostic `inert_pattern_no_match_in_turn` is surfaced. [TS-009]
- [ ] T027 [P] [US2] Implement `@TS-010` contract test scanning host-repo `CLAUDE.md` for domain-specific heuristics — keyword allowlist only (Constitution-level rules allowed). [TS-010]
- [ ] T028 [US2] Add zero-activation property test `tests/katas/009_path_rules/unit/test_zero_activation_property.py` implementing `@TS-011`: baseline prompt bytes vs. post-addition bytes, asserted equal within tolerance. [TS-011]

### Implementation

- [ ] T029 [US2] In `PathScopedRuleLoader.activate`, ensure the "no match" code path does NOT concatenate any rule body into returned context — assert in code via a `_compose_prompt_suffix` method returning `""` when `members` is empty. [TS-006, TS-007, TS-011]
- [ ] T030 [US2] Add `LoaderDiagnostic(code="inert_pattern_no_match_in_turn")` emission in `loader.py` for any `RuleFile` whose patterns matched zero edited paths this turn (alongside, not inside, the `ActiveRuleSet`). [TS-009]
- [ ] T031 [US2] Expose `PathScopedRuleLoader.compose_prompt_suffix(active: ActiveRuleSet) -> str` used by both production composition and the byte-parity test so there is a single call site to audit. [TS-007, TS-011]
- [ ] T032 [US2] Implement `edited_file_paths` filter that rejects paths from read-only tool metadata (spec edge case); add helper `filter_writable_edits(tool_events) -> list[str]` used by the CLI runner. [TS-008]

**Checkpoint**: US2 tests pass. Context Economy property holds.

## Phase 5: User Story 3 — New rule file activates only on matching edits (P3)

**Goal**: Dropping a new rule file into `.claude/rules/` with a new pattern activates on matching edits and stays dormant elsewhere — no code change, no restart.

**Independent Test**: `pytest tests/katas/009_path_rules/features/new_rule_file_activation.feature -v` passes `@TS-012`..`@TS-019` green across `new_rule_pattern/`, `multi_overlap/`, `invalid_frontmatter/`, `empty_patterns/`, `very_large/` fixtures.

### Tests

- [ ] T033 [P] [US3] Create fixture `tests/katas/009_path_rules/fixtures/rules/new_rule_pattern/.claude/rules/api-conventions.md` with `paths: ["src/api/**/*.ts"]`.
- [ ] T034 [P] [US3] Create fixture `tests/katas/009_path_rules/fixtures/rules/multi_overlap/.claude/rules/{a-rules.md,b-rules.md,c-rules.md}` — all declare `paths: ["src/**/*.ts"]` with precedences 50, 100, 100 respectively, for `@TS-014`.
- [ ] T035 [P] [US3] Create seven fixture files under `tests/katas/009_path_rules/fixtures/rules/invalid_frontmatter/.claude/rules/` — one per `FrontmatterReason` literal — covering `yaml_parse_error`, `missing_paths_key`, `paths_not_list`, `paths_empty`, `empty_glob`, `precedence_not_int`, `no_frontmatter_fence`. Used by `@TS-015`.
- [ ] T036 [P] [US3] Create fixture `tests/katas/009_path_rules/fixtures/rules/very_large/.claude/rules/huge.md` whose body exceeds the `large_rule_body` threshold (configurable via env; default 20 000 bytes) for `@TS-019`.
- [ ] T037 [US3] Implement step definitions for `@TS-012` (new-file matching edit) and `@TS-013` (non-matching edit stays dormant) in `test_path_rules_steps.py`. [TS-012, TS-013]
- [ ] T038 [US3] Implement step definitions for `@TS-014` asserting ordering `a-rules.md → b-rules.md → c-rules.md` and determinism across two runs. [TS-014]
- [ ] T039 [US3] Implement `Scenario Outline` step for `@TS-015` mapping each defect → `FrontmatterError.reason` literal. Use fixture tree from T035. [TS-015]
- [ ] T040 [P] [US3] Add contract test `tests/katas/009_path_rules/contract/test_schema_loader_diagnostic.py` validating diagnostics against `contracts/loader-diagnostic.schema.json` (used by `@TS-016`). [TS-016]
- [ ] T041 [P] [US3] Add contract test `tests/katas/009_path_rules/contract/test_schema_rule_file_frontmatter.py` validating parsed frontmatter against `contracts/rule-file-frontmatter.schema.json` (used by `@TS-017`). [TS-017]
- [ ] T042 [US3] Implement step definitions for `@TS-018`: dual-edit turn activates both `testing.md` and `api-conventions.md` once each, all events logged. [TS-018]
- [ ] T043 [US3] Implement step definitions for `@TS-019` asserting very-large rule still appears in the audit log and a `large_rule_body` diagnostic is surfaced. [TS-019]
- [ ] T044 [P] [US3] Add unit test `tests/katas/009_path_rules/unit/test_frontmatter_parse.py` covering each `FrontmatterReason` literal directly on `parse_frontmatter`, independent of `.feature` runner. [TS-015]
- [ ] T045 [P] [US3] Add unit test `tests/katas/009_path_rules/unit/test_matcher_precedence.py` covering `resolve_precedence` ordering + dedup invariants. [TS-014]
- [ ] T046 [P] [US3] Add unit test `tests/katas/009_path_rules/unit/test_audit_log_shape.py` asserting every written JSONL line has `(turn_id, timestamp, edited_path, rule_file, matched_pattern, precedence)`. [TS-018]

### Implementation

- [ ] T047 [US3] Extend `PathScopedRuleLoader` to detect new rule files at loader construction (directory scan, not agent restart) — documented behavior for US3. [TS-012, TS-013]
- [ ] T048 [US3] Implement `frontmatter.validate_parsed(data, path)` emitting the exact reason literal for each failure mode — the single authority for FR-003 closed reason set. [TS-015, TS-017]
- [ ] T049 [US3] Implement `LoaderDiagnostic(code="large_rule_body", severity="warning")` when `RuleFile.body_byte_size` > threshold; threshold overridable via env `KATA9_LARGE_RULE_BYTES`. [TS-019]
- [ ] T050 [US3] Implement CLI demo runner `katas/009_path_rules/runner.py` — `python -m katas.009_path_rules.runner --edited-path <p> [--rules-dir ...]` — prints the `ActiveRuleSet` as JSON for quickstart. [TS-012]
- [ ] T051 [P] [US3] Add optional integration test `tests/katas/009_path_rules/integration/test_live_rule_injection.py` gated by `LIVE_API=1`; stubs by default, exercises anthropic SDK when live. [TS-012]

**Checkpoint**: US3 tests pass. Kata end-to-end deliverable complete.

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T052 [P] Author `katas/009_path_rules/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — write-allow / read-allow / deny path patterns derived from `paths` globs, glob precedence, per-edit rule injection (vs always-on), frontmatter-validated rule files, deduplication by filename, read-only tool path exclusion — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`loader` → `frontmatter` → `models` → `matcher` → `audit` → `runner`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — scoped-injection-per-edit, deterministic precedence ordering, frontmatter-as-contract, machine-validated rule files — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, III Context Economy, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — matching algorithm (`**` → `fnmatch.fnmatchcase`; no `**` → `PurePath.match`), ordering `(precedence asc, filename asc)`, deduplication by `filename`, read-only tool paths excluded (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T053 [P] Add module-level docstring to each `katas/009_path_rules/*.py` file (`loader.py`, `frontmatter.py`, `models.py`, `matcher.py`, `audit.py`, `runner.py`) stating purpose, FR/SC traces, and invariants owned.
- [ ] T054 [P] Add why-comments on non-trivial functions: `PathScopedRuleLoader.activate`, `matcher.match`, `matcher.resolve_precedence`, `frontmatter.parse_frontmatter`, `frontmatter.validate_parsed`, `AuditWriter.append`. Each comment explains the anti-pattern being defended against.
- [ ] T056 [P] Verify `specs/009-path-rules/quickstart.md`: every scenario named in its table maps to an existing `@TS-NNN`, every fixture named (`single_match/`, `no_match/`, `multi_overlap/`, `invalid_frontmatter/`, `new_rule_pattern/`) exists under `tests/katas/009_path_rules/fixtures/rules/`.
- [ ] T057 Run quickstart validation: execute the exact commands from `specs/009-path-rules/quickstart.md` (`pip install -e ".[dev]"`, `pytest tests/katas/009_path_rules -v`, `python -m katas.009_path_rules.runner --edited-path "src/components/button.test.tsx"`) — all must succeed on a fresh clone.
- [ ] T058 [P] Run `ruff check katas/009_path_rules tests/katas/009_path_rules` and `ruff format --check` — zero findings.
- [ ] T059 [P] Run `mypy --strict katas/009_path_rules` — zero errors.
- [ ] T060 [P] Update `.specify/dashboard.html` via the dashboard-refresh script after tasks.md lands.
- [ ] T061 Mark the "Done" checkbox for `tasks.md` in `specs/009-path-rules/quickstart.md` (the `[ ] tasks.md` line).

## Dependencies & Execution Order

- Phase 1 (T001–T005) gates everything.
- Phase 2 (T006–T011) gates all story phases — models, matcher, frontmatter, audit are consumed by every user story.
- Phase 3 (US1, T012–T021) depends on Phase 2. Delivers MVP.
- Phase 4 (US2, T022–T032) depends on Phase 2 and benefits from Phase 3 (`compose_prompt_suffix`). May proceed independently once T019–T020 land.
- Phase 5 (US3, T033–T051) depends on Phase 2; fixtures (T033–T036, T044–T046) can start immediately in parallel.
- Final Phase (T052–T061) depends on all stories green. T057 (quickstart validation) must run after every other non-polish task is complete.

## Parallel Opportunities

- T002–T005 run concurrently after T001.
- T012, T013 (fixtures) run concurrently with T022, T033–T036 (fixtures for other stories).
- T016, T018 (US1 outline + contract) parallel with T014–T015.
- T040, T041, T044, T045, T046, T051 (US3 unit + contract + integration tests) parallel with step-def tasks.
- All polish tasks T052–T054, T058–T060 run in parallel.

## Implementation Strategy (MVP)

1. Land Phase 1 + Phase 2 (T001–T011) — models, matcher, audit.
2. Land US1 (T012–T021) — this alone is a shippable kata demonstrating headline behavior.
3. Land US2 (T022–T032) — proves Context Economy and pins SC-001.
4. Land US3 (T033–T051) — proves extensibility and closes edge cases.
5. Polish (T052–T061).

Stop-at points: after US1 you have a demo; after US2 you have the defended anti-pattern; after US3 you have the full kata.

## Notes

- Every `@TS-NNN` tag in `tests/features/*.feature` has at least one implementation task citing its ID — trace table is load-bearing for `/iikit-06-analyze`.
- Fixture directories are the single source of truth for scenario data; do not hard-code rule content in step definitions.
- `runs/<session-id>/rule-activation.jsonl` is gitignored — do not check it in.
- `CLAUDE.md` leak test (`@TS-010`) scans the host repo, not the kata dir; keep the keyword allowlist small and explicit.
- Do NOT edit `.feature` files or `tests/features/*.feature` — if requirements shift, re-run `/iikit-04-testify`.
