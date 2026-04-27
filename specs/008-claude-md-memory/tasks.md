# Tasks: Hierarchical Memory Orchestration in CLAUDE.md

**Input**: Design documents from `/specs/008-claude-md-memory/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] on story tasks
- Traceability: `[TS-001, TS-002]`, never "TS-001 through TS-NNN"

---

## Phase 1: Setup

- [ ] T001 Create kata package directory `katas/008_claude_md_memory/` with empty `__init__.py` exposing `__all__ = []`
- [ ] T002 [P] Create `katas/008_claude_md_memory/templates/` and `katas/008_claude_md_memory/templates/standards/` directories as placeholders for canonical memory artifacts
- [ ] T003 [P] Create test directory `tests/katas/008_claude_md_memory/` with subdirs `features/`, `step_defs/`, `unit/`, `fixtures/`
- [ ] T004 [P] Add `pydantic>=2.5`, `pytest`, `pytest-bdd`, `anthropic` to project dependencies (pyproject.toml `[project.optional-dependencies].dev`); ensure Python 3.11+ pin
- [ ] T005 [P] Copy `.feature` files from `specs/008-claude-md-memory/tests/features/*.feature` into `tests/katas/008_claude_md_memory/features/` (keep file names identical so `pytest-bdd` auto-discovers)
- [ ] T006 [P] Copy JSON Schemas from `specs/008-claude-md-memory/contracts/*.schema.json` into a runtime-readable location `katas/008_claude_md_memory/contracts/` so contract-validation tests can load them without touching spec dirs

---

## Phase 2: Foundational

**Purpose**: Data model, exception taxonomy, and size budget constant must exist before any scenario step can be implemented. Every later US depends on these.

- [ ] T007 Create `katas/008_claude_md_memory/budget.py` declaring `TEAM_MEMORY_MAX_BYTES = 20 * 1024` plus helper `aggregate_team_bytes(entries) -> int` [TS-019, TS-021]
- [ ] T008 Create `katas/008_claude_md_memory/models.py` with pydantic v2 models: `Scope` (Literal), `PathReference`, `MemoryEntry`, `ResolutionDiagnostic`, `ResolvedMemory` matching `data-model.md` field-for-field; include `effective_for_project_task()` method on `ResolvedMemory` [TS-004, TS-012, TS-018]
- [ ] T009 Extend `katas/008_claude_md_memory/models.py` with exception hierarchy: `MemoryResolutionError` base, `MissingReferenceError`, `CircularReferenceError`, `UnreadableReferenceError`, `OversizeMemoryError`, each carrying `.diagnostic: ResolutionDiagnostic` [TS-014, TS-015, TS-016, TS-017, TS-020]
- [ ] T010 [P] Create `tests/katas/008_claude_md_memory/conftest.py`: fixtures `fixture_root`, `redirect_home(tmp_path, monkeypatch)`, `load_schema(name)` loader, `valid_fixture`, `missing_target_fixture`, `circular_fixture`, `oversize_fixture`, `personal_vs_team_fixture`
- [ ] T011 [P] Create unit test `tests/katas/008_claude_md_memory/unit/test_resolved_memory_schema.py` asserting `ResolvedMemory.model_json_schema()` matches `contracts/resolved-memory.schema.json` structurally (Principle II mirror check)
- [ ] T012 [P] Create unit test `tests/katas/008_claude_md_memory/unit/test_models_construction.py` validating invariants from `data-model.md`: `raw` must start with `@`, `declaration_order` uniqueness, `source_sha256` hex-64 shape, `team_bytes_total <= team_bytes_budget`

**Checkpoint**: `pytest tests/katas/008_claude_md_memory/unit/test_models_construction.py tests/katas/008_claude_md_memory/unit/test_resolved_memory_schema.py` passes before any story work begins.

---

## Phase 3: User Story 1 — Zero-Setup Team Conventions on Fresh Clone (Priority P1)

**Goal**: Resolver loads `.claude/CLAUDE.md` deterministically at startup with no per-user configuration; `@path` references are pulled in; two clones at the same SHA produce byte-identical `ResolvedMemory`.

**Independent Test**: Wipe working copy, re-clone, run `pytest tests/katas/008_claude_md_memory/unit/test_resolver_deterministic.py` plus the `@US-001` scenarios in `fresh_clone_team_conventions.feature`; all pass with zero env-var setup.

### Tests (US1)

- [ ] T013 [P] [US1] Build fixture `tests/katas/008_claude_md_memory/fixtures/valid/.claude/CLAUDE.md` with `@./standards/coding-style.md` + `@./standards/testing.md` references; add the two standards files, keeping aggregated size < 20 KB
- [ ] T014 [P] [US1] Write step definitions in `tests/katas/008_claude_md_memory/step_defs/test_fresh_clone_team_conventions_steps.py` binding the `fresh_clone_team_conventions.feature` scenarios [TS-001, TS-002, TS-003, TS-004]
- [ ] T015 [P] [US1] Write unit test `tests/katas/008_claude_md_memory/unit/test_resolver_deterministic.py` asserting two resolver runs on the `valid/` fixture produce byte-identical `model_dump_json(indent=2, sort_keys=True)` [TS-003]
- [ ] T016 [P] [US1] Write unit test `tests/katas/008_claude_md_memory/unit/test_path_reference_contract.py` validating every `PathReference` produced by the `valid/` fixture against `path-reference.schema.json` [TS-012 shared with US3; anchor here]

### Implementation (US1)

- [ ] T017 [US1] Implement `katas/008_claude_md_memory/resolver.py` function `_read_file(path) -> (bytes, sha256)` returning content + SHA-256 using `hashlib.sha256` [TS-001]
- [ ] T018 [US1] Implement `katas/008_claude_md_memory/resolver.py` function `_scan_path_tokens(content, parent_path) -> list[PathReference]` that finds `@./...` and `@/...` tokens line-by-line, records `declaration_line`, skips fenced code blocks [TS-002]
- [ ] T019 [US1] Implement `katas/008_claude_md_memory/resolver.py` class `MemoryResolver` with `__init__(project_root, home_dir=None)` and public `resolve() -> ResolvedMemory` doing team-scope DFS first [TS-001, TS-002]
- [ ] T020 [US1] Extend `MemoryResolver.resolve()` to assign strictly-increasing `declaration_order` during DFS visit and sort `entries` by it before returning; populate `resolved_at=datetime.now(UTC)` and `project_root` canonical absolute [TS-003]
- [ ] T021 [US1] Implement `katas/008_claude_md_memory/cli.py` entrypoint `python -m katas.008_claude_md_memory.cli validate <path>` that runs `MemoryResolver.resolve()` and prints `model_dump_json(indent=2, sort_keys=True)` [TS-001]
- [ ] T022 [US1] Author canonical template `katas/008_claude_md_memory/templates/CLAUDE.md` pointing at `@./standards/coding-style.md`, `@./standards/testing.md`, `@./standards/commit-message.md` — kept intentionally small (< 2 KB) [TS-022 — anchors here, asserted in US budget phase]
- [ ] T023 [P] [US1] Author `katas/008_claude_md_memory/templates/standards/coding-style.md` with rule headings including `package-manager`, `indent-style`
- [ ] T024 [P] [US1] Author `katas/008_claude_md_memory/templates/standards/testing.md` with rule headings including `test-runner`
- [ ] T025 [P] [US1] Author `katas/008_claude_md_memory/templates/standards/commit-message.md` with rule heading `commit-format`

**Checkpoint**: `pytest tests/katas/008_claude_md_memory -k "US-001 or TS-001 or TS-002 or TS-003 or TS-004"` is green. Fresh-clone determinism works end-to-end independently.

---

## Phase 4: User Story 2 — Team Rules Win Over Personal Preferences (Priority P2)

**Goal**: Personal memory (`~/.claude/CLAUDE.md`) loads under `scope="personal"`; on project tasks, personal entries whose `rule_keys` collide with any team entry are dropped from the effective view and recorded as `personal_overridden_by_team` diagnostic. Non-conflicting personal rules survive. Personal file never in VCS.

**Independent Test**: Set HOME to a temp dir containing a personal `CLAUDE.md` that conflicts on `package-manager`; run `tests/katas/008_claude_md_memory/unit/test_personal_override_blocked.py` and `@US-002` scenarios; all pass.

### Tests (US2)

- [ ] T026 [P] [US2] Build fixture `tests/katas/008_claude_md_memory/fixtures/personal_vs_team/project/.claude/CLAUDE.md` with team rule heading `## package-manager\nuse pnpm` and fixture `.../personal_vs_team/home/.claude/CLAUDE.md` with `## package-manager\nuse npm` plus a non-conflicting `## editor-theme` section
- [ ] T027 [P] [US2] Write step definitions in `tests/katas/008_claude_md_memory/step_defs/test_team_rules_override_personal_steps.py` for `team_rules_override_personal.feature` [TS-005, TS-006, TS-007, TS-008, TS-009]
- [ ] T028 [P] [US2] Write unit test `tests/katas/008_claude_md_memory/unit/test_personal_override_blocked.py` covering: conflict-drop, diagnostic emission, non-conflicting survival, scope-outline rule-matrix [TS-005, TS-006, TS-007, TS-008]
- [ ] T029 [P] [US2] Write unit test `tests/katas/008_claude_md_memory/unit/test_personal_scope_not_in_vcs.py` asserting `.gitignore` excludes `home/` fixture patterns and that no `tests/.../fixtures/**/home/**` path is tracked via `git ls-files` [TS-009]

### Implementation (US2)

- [ ] T030 [US2] Implement `katas/008_claude_md_memory/scope.py` function `extract_rule_keys(content) -> list[str]` that parses markdown `##`-level headings and slugifies them into rule keys [TS-005, TS-008]
- [ ] T031 [US2] Extend `MemoryResolver.resolve()` in `katas/008_claude_md_memory/resolver.py` to also load personal memory from `home_dir / ".claude" / "CLAUDE.md"` (or `$CLAUDE_HOME/CLAUDE.md`) tagged `scope="personal"`, appended after team DFS with continuing `declaration_order` [TS-005]
- [ ] T032 [US2] Implement `katas/008_claude_md_memory/scope.py` function `effective_entries(entries) -> tuple[list[MemoryEntry], list[ResolutionDiagnostic]]` that drops personal entries whose `rule_keys` intersect any team entry's `rule_keys`, emitting `personal_overridden_by_team` diagnostics with `conflicting_rule_key` and `severity="info"` [TS-006]
- [ ] T033 [US2] Wire `ResolvedMemory.effective_for_project_task()` in `katas/008_claude_md_memory/models.py` to delegate to `scope.effective_entries(self.entries)`; append returned diagnostics into `self.diagnostics` view without mutating source entries [TS-007, TS-008]
- [ ] T034 [US2] Assert in `MemoryResolver.resolve()` that the resolver never writes to the personal memory file (read-only open, enforce by path-level assertion in a unit-covered path) [TS-009]

**Checkpoint**: `pytest tests/katas/008_claude_md_memory -k "US-002"` is green without breaking US1 tests.

---

## Phase 5: User Story 3 — Editing a Referenced Manual Updates Agent Behavior (Priority P3)

**Goal**: Editing `standards/coding-style.md` flows into the next resolver run without touching `CLAUDE.md`; removing an `@path` reference drops rules that only lived there; diamond-shaped graphs de-duplicate with a `duplicate_reference` warning.

**Independent Test**: Mutate a fixture standards file between two resolver runs and assert new `source_sha256` + new rule appears; run `@US-003` scenarios; all pass.

### Tests (US3)

- [ ] T035 [P] [US3] Build fixture `tests/katas/008_claude_md_memory/fixtures/live_reference_edit/` with initial `.claude/CLAUDE.md` + `standards/coding-style.md`; test harness rewrites the standards file mid-run
- [ ] T036 [P] [US3] Build fixture `tests/katas/008_claude_md_memory/fixtures/diamond/` where two files both reference `@./standards/shared.md`
- [ ] T037 [P] [US3] Write step definitions in `tests/katas/008_claude_md_memory/step_defs/test_modular_path_references_steps.py` for `modular_path_references.feature` [TS-010, TS-011, TS-012, TS-013]
- [ ] T038 [P] [US3] Write unit test `tests/katas/008_claude_md_memory/unit/test_live_reference_edit.py` asserting second resolver run picks up edited manual and `source_sha256` changes [TS-010]
- [ ] T039 [P] [US3] Write unit test `tests/katas/008_claude_md_memory/unit/test_dereferenced_manual.py` asserting rules from a removed `@path` are absent in the second run [TS-011]
- [ ] T040 [P] [US3] Write unit test `tests/katas/008_claude_md_memory/unit/test_diamond_reference.py` asserting exactly one `MemoryEntry` per unique file plus a `duplicate_reference` severity `warning` diagnostic [TS-013]

### Implementation (US3)

- [ ] T041 [US3] Extend `MemoryResolver.resolve()` to carry a `_visited: dict[str, int]` of canonical paths → declaration_order; on second visit, emit `ResolutionDiagnostic(kind="duplicate_reference", severity="warning")` and skip re-reading [TS-013]
- [ ] T042 [US3] Ensure `_read_file` always re-reads from disk (no cached bytes) so edits between two `resolve()` calls are visible; add an explicit no-cache assertion covered by T038 [TS-010]
- [ ] T043 [US3] Ensure removing an `@path` from the parent file between runs produces no `MemoryEntry` for the target — covered by correct DFS scope but add an explicit unit assertion [TS-011]

**Checkpoint**: `pytest tests/katas/008_claude_md_memory -k "US-003"` green without regressing US1, US2.

---

## Phase 6: Cross-Cutting Fail-Loud Diagnostics + Size Budget (Still P1 per spec)

**Goal**: Every unresolvable reference raises a typed exception with a structured `ResolutionDiagnostic`; oversize aggregated team memory raises `OversizeMemoryError` before construction; only team-scope bytes count toward the budget; canonical template stays well under budget.

**Independent Test**: Run `fail_loud_diagnostics.feature` and `context_economy_size_budget.feature` scenarios against the four fail-loud fixtures and the oversize fixture; all pass.

### Tests (Fail-Loud + Budget)

- [ ] T044 [P] Build fixture `tests/katas/008_claude_md_memory/fixtures/missing_target/.claude/CLAUDE.md` referencing `@./standards/ghost.md` (no such file) [TS-014]
- [ ] T045 [P] Build fixture `tests/katas/008_claude_md_memory/fixtures/circular/` with `.claude/CLAUDE.md` → `@./a.md`, `a.md` → `@./b.md`, `b.md` → `@./a.md` [TS-015]
- [ ] T046 [P] Build fixture `tests/katas/008_claude_md_memory/fixtures/unreadable/` where a referenced file has permissions `0o000` (set in conftest at test time, restored in teardown) [TS-016]
- [ ] T047 [P] Build fixture `tests/katas/008_claude_md_memory/fixtures/oversize/` where `standards/huge.md` is > 25 KB so aggregated team memory exceeds 20 KB [TS-020]
- [ ] T048 [P] Write step definitions `tests/katas/008_claude_md_memory/step_defs/test_fail_loud_diagnostics_steps.py` for `fail_loud_diagnostics.feature` [TS-014, TS-015, TS-016, TS-017, TS-018]
- [ ] T049 [P] Write step definitions `tests/katas/008_claude_md_memory/step_defs/test_context_economy_size_budget_steps.py` for `context_economy_size_budget.feature` [TS-019, TS-020, TS-021, TS-022]
- [ ] T050 [P] Write unit test `tests/katas/008_claude_md_memory/unit/test_missing_target_fails_loud.py` [TS-014]
- [ ] T051 [P] Write unit test `tests/katas/008_claude_md_memory/unit/test_circular_reference.py` asserting `cycle_path` is closed (first == last) [TS-015]
- [ ] T052 [P] Write unit test `tests/katas/008_claude_md_memory/unit/test_unreadable_target.py` [TS-016]
- [ ] T053 [P] Write unit test `tests/katas/008_claude_md_memory/unit/test_fatal_kinds_outline.py` parametrizing the four fatal kinds → typed exceptions matrix [TS-017]
- [ ] T054 [P] Write unit test `tests/katas/008_claude_md_memory/unit/test_resolution_diagnostic_schema.py` validating emitted `ResolutionDiagnostic` JSON against `resolution-diagnostic.schema.json` [TS-018]
- [ ] T055 [P] Write unit test `tests/katas/008_claude_md_memory/unit/test_team_memory_size_budget.py` covering: within-budget success, over-budget raises, only team bytes count, canonical template well below budget [TS-019, TS-020, TS-021, TS-022]

### Implementation (Fail-Loud + Budget)

- [ ] T056 Extend `MemoryResolver` `_resolve_reference()` in `resolver.py` to raise `MissingReferenceError(diagnostic=ResolutionDiagnostic(kind="missing_target", reference=ref, severity="error"))` when the target file does not exist [TS-014]
- [ ] T057 Extend `MemoryResolver` with DFS cycle detection using a `_visiting: set[str]` stack; raise `CircularReferenceError` with `cycle_path` closed (first == last) on re-entry [TS-015]
- [ ] T058 Wrap file reads in `_read_file()` to catch `PermissionError`/`OSError` → raise `UnreadableReferenceError` with severity `"error"` and the offending reference [TS-016]
- [ ] T059 Compute `team_bytes_total` progressively during DFS; when it exceeds `TEAM_MEMORY_MAX_BYTES`, raise `OversizeMemoryError` with `bytes_observed`, `bytes_budget` **before** constructing `ResolvedMemory` [TS-020, TS-021]
- [ ] T060 In `MemoryResolver.resolve()`, ensure no partial `ResolvedMemory` is returned on any error path — every `raise` propagates out of `resolve()` cleanly [TS-017]
- [ ] T061 Emit `ResolutionDiagnostic` JSON via `model_dump(mode="json")` so the schema-mirror test T054 sees canonical enum strings [TS-018]
- [ ] T062 Confirm personal-scope bytes are excluded from `team_bytes_total` accounting in `budget.aggregate_team_bytes()` [TS-021]
- [ ] T063 Assert via T055 that `templates/CLAUDE.md` byte size is below `TEAM_MEMORY_MAX_BYTES // 10` (i.e., top-level file is "well below" budget per TS-022) [TS-022]

**Checkpoint**: All `.feature` scenarios pass; `pytest tests/katas/008_claude_md_memory` is fully green.

---

## Final Phase: Polish & Cross-Cutting Concerns

### Documentation (Principle VIII)

- [ ] T064 [P] Author `katas/008_claude_md_memory/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — layered CLAUDE.md memory (team / personal / standards), precedence merge (team beats personal on rule-key collision), `@path` resolved in declaration order, slugified Level-2 heading as rule-key identity, scope-token scanning, fenced-block skip, DFS cycle detection (`_visiting` vs `_visited`), deterministic ordering for `effective_entries`, no-cache / no-hot-reload memory lifecycle — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`resolver` → `models` → `scope` → `budget` → `cli` → `__init__`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — layered memory precedence, slug-keyed rule identity, declaration-order resolution, deterministic merge — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, III Context Economy, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — precedence/merge rules (team beats personal on rule-key collision; non-conflicting personal survives; `@path` resolved in declaration order); rule-key identity convention (slugified Level-2 `##` heading: lowercase, strip + collapse whitespace to `-`; two entries conflict iff slugified heading sets intersect — spec.md §Clarifications F-002); memory lifecycle (read on resolve, never cached, never hot-reloaded) (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T065 [P] Add module-level docstrings to each of `katas/008_claude_md_memory/resolver.py`, `models.py`, `scope.py`, `budget.py`, `cli.py`, `__init__.py` stating the module's single responsibility and the FR/SC it anchors
- [ ] T066 [P] Add why-comments on non-trivial functions: `_scan_path_tokens` (why fenced-block skip), DFS cycle detection (`_visiting` vs `_visited` distinction), `effective_entries` (why deterministic ordering matters for SC-001)
- [ ] T068 [P] Verify `specs/008-claude-md-memory/quickstart.md` — mark `Done` checklist boxes that tasks.md now fulfills; confirm every scenario-to-fixture mapping row matches a fixture that exists under `tests/katas/008_claude_md_memory/fixtures/`
- [ ] T069 Run quickstart validation: follow `quickstart.md` top-to-bottom from a clean checkout, capture any drift in a final markdown cell of `notebook.ipynb`

### Standard polish

- [ ] T070 [P] Run `ruff check katas/008_claude_md_memory tests/katas/008_claude_md_memory` and fix warnings
- [ ] T071 [P] Run `mypy katas/008_claude_md_memory` with `--strict` on the kata package and resolve any issues
- [ ] T072 [P] Measure `pytest tests/katas/008_claude_md_memory` wall-clock and assert < 3 s (plan performance goal); if slower, identify the slowest fixture and justify in a final markdown cell of `notebook.ipynb`
- [ ] T073 Verify `TEAM_MEMORY_MAX_BYTES` constant is imported from `budget.py` in every place that references it (no magic numbers)
- [ ] T074 Regenerate dashboard: `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh`
- [ ] T075 Final green run: `pytest tests/katas/008_claude_md_memory -v` with 100% of `@TS-NNN` scenarios passing

---

## Dependencies & Execution Order

- **Setup (T001–T006)** blocks everything.
- **Foundational (T007–T012)** blocks all US phases. T008 depends on T007. T009 depends on T008. T010–T012 depend on T008+T009.
- **US1 (T013–T025)** depends on Foundational. Inside US1: tests T013–T016 precede implementation T017–T025 (TDD). T022 (canonical template) gates T063 (budget assertion in US-independent phase).
- **US2 (T026–T034)** depends on US1 core resolver (T019, T020). T030–T034 implement on top of resolver.
- **US3 (T035–T043)** depends on US1 (`_read_file`, DFS). T041 extends existing DFS without breaking US1.
- **Fail-Loud + Budget (T044–T063)** depends on US1 for resolver skeleton; independent of US2/US3 but implemented after to exercise a full resolver surface.
- **Polish (T064–T075)** runs last. T068, T069 depend on all prior phases.

---

## Parallel Opportunities

- **Setup**: T002, T003, T004, T005, T006 all [P] after T001.
- **Foundational tests**: T010, T011, T012 all [P] after T008+T009.
- **US1 tests**: T013, T014, T015, T016 all [P].
- **US1 templates**: T023, T024, T025 all [P] after T022.
- **US2 tests**: T026, T027, T028, T029 all [P].
- **US3 tests**: T035, T036, T037, T038, T039, T040 all [P].
- **Fail-Loud + Budget tests**: T044, T045, T046, T047, T048, T049, T050, T051, T052, T053, T054, T055 all [P].
- **Polish**: T064, T065, T066, T068 all [P]; T070, T071, T072 all [P].

---

## Implementation Strategy (MVP)

1. Complete Setup + Foundational (T001–T012). Data model + budget constant + exception hierarchy are enough to compile every downstream test.
2. Ship **US1 only** (T013–T025). Resolver that loads team memory deterministically IS the minimum viable kata — at this point every other team member on a fresh clone gets reproducible agent behavior.
3. Layer **US2** (T026–T034) to add the anti-pattern defense (personal-pollutes-team). This closes SC-002.
4. Layer **US3** (T035–T043) to prove modularity is live (SC-001 alternate form + FR-002 edge).
5. Harden via **Fail-Loud + Budget** (T044–T063) — every fatal path tested and every byte accounted for. Closes SC-003, SC-004.
6. Finish with **Polish** (T064–T075): documentation (Principle VIII), type/lint gates, performance assertion, dashboard refresh, and green-suite verification.

---

## Notes

- Every production file path follows `katas/008_claude_md_memory/…` per `plan.md` Project Structure; every test path follows `tests/katas/008_claude_md_memory/…`.
- Every `@TS-NNN` Gherkin scenario has at least one step-definition task AND one unit test task citing the TS ID.
- `TEAM_MEMORY_MAX_BYTES = 20 * 1024` is sourced from `plan.md` Constraints and `data-model.md` invariants; the lint test (T055) is the machine-checkable face of Principle III for this kata.
- `effective_for_project_task()` is the SC-002 anchor; its determinism is load-bearing because SC-001 asserts byte-identical serialization.
- The kata does NOT replace Claude's native `@path` loader — the resolver is a **lint / CI tool** that makes governance files testable, per `plan.md` Summary.
- No `--no-verify`, no hook bypass, no editing of `.feature` files: any requirement drift means rerunning `/iikit-04-testify`, per `.tessl/RULES.md` assertion-integrity.
