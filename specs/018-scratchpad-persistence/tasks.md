# Tasks: Transactional Memory Preservation via Scratchpad

**Input**: Design documents from `/specs/018-scratchpad-persistence/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-006"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/018_scratchpad_persistence/__init__.py` (empty marker) and mirror test package `tests/katas/018_scratchpad_persistence/__init__.py`
- [ ] T002 [P] Extend repo `pyproject.toml` `[dev]` extra so it declares `pydantic>=2`, `ruamel.yaml`, `fasteners`, `anthropic`, `pytest`, `pytest-bdd`, `jsonschema` per plan.md Technical Context
- [ ] T003 [P] Ensure `runs/kata-018/` is gitignored (per plan.md: per-run artifacts under `runs/kata-018/<session-id>/` must not be committed)
- [ ] T004 [P] Create `tests/katas/018_scratchpad_persistence/conftest.py` stub that declares the `pytest-bdd` features directory and exposes shared fixtures: `tmp_scratchpad_path`, `recorded_client`, `fixture_loader`, `flock_barrier`
- [ ] T005 [P] Create empty fixture dir `tests/katas/018_scratchpad_persistence/fixtures/` and placeholder test sub-dirs `unit/`, `lint/`, `step_defs/`, `features/`

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, JSON schema wiring, injectable Anthropic client, module constants. No story label.

- [ ] T006 [P] Implement shared pydantic v2 entities in `katas/018_scratchpad_persistence/models.py`: `Finding`, `Scratchpad`, `ContextAnchor`, `RotationEvent`, and the `ScratchpadSchemaError` exception with byte-offset payload — per `data-model.md`
- [ ] T007 [P] Declare the fixed section enum `SectionName = Literal["map","findings","open_questions","decisions","conflicts"]` and the `CATEGORY_TO_SECTION` routing map in `katas/018_scratchpad_persistence/models.py` — unknown sections rejected at validation time (plan.md constraint; FR-002)
- [ ] T008 [P] Declare module constants `MAX_SCRATCHPAD_BYTES = 100_000` and `COMPACTION_THRESHOLD = 0.55` in `katas/018_scratchpad_persistence/constants.py` with why-comments linking to D-003 and D-004
- [ ] T009 [P] Add contract-schema loader helper `tests/katas/018_scratchpad_persistence/conftest.py::load_contract_schema(name)` that resolves paths under `specs/018-scratchpad-persistence/contracts/` (`scratchpad-document.schema.json`, `finding.schema.json`, `rotation-event.schema.json`, `context-anchor.schema.json`)
- [ ] T010 [P] Implement thin injectable Anthropic client wrapper in `katas/018_scratchpad_persistence/client.py`: `LiveClient` (real SDK, gated by `LIVE_API=1`) and `RecordedClient` replaying fixtures — shared shape with katas 001/011

**Checkpoint**: Foundation ready — pydantic models, section enum, module constants, contract-schema loader, and injectable client are in place. Writer/validator/rotation/bridge can now be implemented against them.

---

## Phase 3: User Story 1 - Long Investigation with Incremental Persistence (Priority: P1) MVP

**Goal**: Every critical finding is appended to the declared scratchpad file the moment it is made — no batching, no end-of-session save, no torn writes, no interleaved concurrent writes.

**Independent Test**: Run an exploratory investigation for at least three distinct findings, terminate the session abruptly, then inspect the scratchpad file. All three findings must be present in their declared sections without any post-session save step.

### Tests for User Story 1

- [ ] T011 [P] [US1] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/running_investigation/` with a mid-session pad holding three findings (one per category) for US1-AS2 replay
- [ ] T012 [P] [US1] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/abrupt_termination/` representing a writer that died after acknowledging 3 findings, for TS-003 replay
- [ ] T013 [P] [US1] Copy/symlink `specs/018-scratchpad-persistence/tests/features/transactional_finding_persistence.feature` to `tests/katas/018_scratchpad_persistence/features/transactional_finding_persistence.feature` so pytest-bdd can discover it
- [ ] T014 [US1] Implement BDD step definitions for [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006] in `tests/katas/018_scratchpad_persistence/step_defs/test_transactional_finding_persistence_steps.py` — steps drive `ScratchpadWriter` against the fresh-path, mid-pad, and concurrent-writer fixtures and assert on file state
- [ ] T015 [P] [US1] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_writer_append_only.py` covering the append-only API surface (`add_finding`, `note_conflict`, `resolve_open_question`) and rejecting any hidden mutation paths [TS-001, TS-002]
- [ ] T016 [P] [US1] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_writer_atomic_write.py` simulating a mid-write kill and asserting the pad parses cleanly with the finding fully-present or fully-absent [TS-005]
- [ ] T017 [P] [US1] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_writer_flock_serialises.py` spawning two `ScratchpadWriter` instances, forcing contention via a barrier, and asserting the POSIX `flock` serialises both writes without interleaving [TS-006]
- [ ] T018 [P] [US1] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_finding_category_routing.py` covering each `category` in `CATEGORY_TO_SECTION` and asserting the finding lands in the mapped section [TS-004]

### Implementation for User Story 1

- [ ] T019 [US1] Implement `katas/018_scratchpad_persistence/scratchpad.py` with `Scratchpad.render_markdown()` (structured → YAML-frontmatter + fixed section bodies) and `Scratchpad.from_markdown()` (file bytes → model), both routed through `ruamel.yaml` round-trip (D-001, FR-010)
- [ ] T020 [US1] Implement `katas/018_scratchpad_persistence/writer.py::ScratchpadWriter` with append-only public API `add_finding`, `note_conflict`, `resolve_open_question`; each call (a) acquires `fasteners` POSIX `flock`, (b) loads current pad or cold-starts empty, (c) appends the new `Finding` to the section routed from its `category`, (d) renders + writes atomically via tmpfile + `os.replace`, (e) releases the lock (FR-001, FR-002, FR-006, FR-008)
- [ ] T021 [US1] In `writer.py`, add post-write parse-round-trip check: after `os.replace`, reload the pad into a `Scratchpad` model and assert equivalence with the in-memory version; any drift raises `ScratchpadSchemaError` (D-006)
- [ ] T022 [US1] In `writer.py`, wire `CATEGORY_TO_SECTION` so `add_finding(category="bug")` routes to `findings`, `category="decision"` to `decisions`, `category="question"` to `open_questions`, `category="architecture"|"data"` to `findings` by default — driven by the typed field, never by text scanning (Principle I; plan.md constraint)
- [ ] T023 [US1] Implement cold-start branch in `writer.py`: if the declared path is missing, create the pad with the fixed section skeleton on the first write (FR-007) — no error on missing-file at startup

**Checkpoint**: At end of User Story 1, every critical finding is durable at the moment of discovery, writes are flock-serialised and atomic, and findings are routed by typed category — MVP ready and independently testable.

---

## Phase 4: User Story 2 - Compaction Survival and Non-Rediscovery (Priority: P2)

**Goal**: After `/compact` or a fresh session, the agent reads the scratchpad before answering the next query, seeds a `ContextAnchor` from `decisions` + `open_questions`, and answers recorded-fact queries with zero rediscovery tool calls.

**Independent Test**: Produce a scratchpad with at least five tracked facts, force `/compact` or new-session, then issue a query that requires those facts; verify zero rediscovery tool calls were made and the answer matches the recorded facts.

### Tests for User Story 2

- [ ] T024 [P] [US2] Record fixture pair `tests/katas/018_scratchpad_persistence/fixtures/pre_compact/` and `.../post_compact/` for the compact-resume round trip at 55% fill [TS-008, TS-009]
- [ ] T025 [P] [US2] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/missing_pad/` representing a declared path that does not exist at session start [TS-011]
- [ ] T026 [P] [US2] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/conflicting_findings/` with two findings of opposed evidence on the same target, to drive conflict routing [TS-010]
- [ ] T027 [P] [US2] Copy/symlink `specs/018-scratchpad-persistence/tests/features/compaction_survival_and_reload.feature` to `tests/katas/018_scratchpad_persistence/features/compaction_survival_and_reload.feature` so pytest-bdd can discover it
- [ ] T028 [US2] Implement BDD step definitions for [TS-007, TS-008, TS-009, TS-010, TS-011] in `tests/katas/018_scratchpad_persistence/step_defs/test_compaction_survival_and_reload_steps.py` — steps drive session-start read, `/compact` trigger, `ContextAnchor` seeding, conflict routing, and cold-start on missing file; default path uses `RecordedClient`, `LIVE_API=1` unlocks the real Anthropic probe
- [ ] T029 [P] [US2] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_compaction_bridge_threshold.py` asserting the `ContextAnchor` build fires at `>= 0.55` context-fill ratio and not below (D-003) [TS-008]
- [ ] T030 [P] [US2] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_context_anchor_shape.py` asserting the emitted anchor carries `decisions_snapshot`, `open_questions_snapshot`, `map_summary` (≤ 400 chars), and `source_pad_id` [TS-009, TS-019]
- [ ] T031 [P] [US2] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_conflict_routing.py` asserting that a new finding on a target already present with opposing evidence is appended to the `conflicts` section with cross-referenced ids, not overwritten (FR-004, Principle VI) [TS-010]
- [ ] T032 [P] [US2] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_missing_scratchpad_cold_start.py` asserting session start against a missing path proceeds as cold start, does not raise, and creates the file on the next write (FR-007) [TS-011]
- [ ] T033 [P] [US2] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_rediscovery_rate.py` with a `RecordedClient` answering from a seeded anchor and asserting zero rediscovery tool calls are issued for recorded facts (SC-001) [TS-009]

### Implementation for User Story 2

- [ ] T034 [US2] Implement `katas/018_scratchpad_persistence/compaction_bridge.py`: `should_compact(session_usage_ratio) -> bool` fires at `>= COMPACTION_THRESHOLD` (0.55); `build_context_anchor(scratchpad) -> ContextAnchor` snapshots `decisions` + `open_questions` verbatim and produces a ≤ 400-char summary of `map` (D-003, FR-009)
- [ ] T035 [US2] In `compaction_bridge.py`, implement `seed_next_session(anchor, session)` that writes `runs/kata-018/<session-id>/anchor.json` for audit and prepends the anchor payload to the resumed session's system context (SC-001, Principle VII)
- [ ] T036 [US2] In `writer.py`, implement `note_conflict(new_finding, existing_finding_id)` that appends both entries to the `conflicts` section with cross-referenced ids and never overwrites; triggered automatically when `add_finding` detects a contradictory evidence statement on the same target — detection is keyed off a declared `target_ref` field equality, not text-matching (FR-004, plan.md constraint)
- [ ] T037 [US2] In `katas/018_scratchpad_persistence/reader.py` (new module), implement `load_on_session_start(path) -> Scratchpad | None`: returns `None` on missing file (cold start, FR-007), raises `ScratchpadSchemaError` on corrupt pad (fail loud, Principle VI), returns a parsed `Scratchpad` otherwise (FR-003)
- [ ] T038 [US2] Wire `reader.load_on_session_start` into the kata's session-start handshake in `katas/018_scratchpad_persistence/runner.py` so the pad is read before the first user query is accepted (FR-003) and re-read after `/compact` before the next query (FR-009)

**Checkpoint**: At end of User Story 2, the scratchpad is load-bearing: the agent reads it on session start, re-reads it after `/compact`, seeds a `ContextAnchor`, answers recorded-fact queries with zero rediscovery, and surfaces conflicts for human review.

---

## Phase 5: User Story 3 - Machine-Parseable Structure on Inspection (Priority: P3)

**Goal**: The scratchpad is a declared, sectioned, schema-enforced document. Every finding maps to exactly one declared section with required metadata, structural drift fails loud with `ScratchpadSchemaError`, and reaching the size cap triggers rotation that preserves prior content.

**Independent Test**: Take a scratchpad produced by a real investigation and run a structural validator against its declared schema. 100% of findings must live under a recognized section and include the required fields. Drift fixtures must each raise `ScratchpadSchemaError` with a byte offset.

### Tests for User Story 3

- [ ] T039 [P] [US3] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/corrupted_pad.md` covering each drift kind (unknown section, missing id, missing timestamp, prose blob outside sections) [TS-016]
- [ ] T040 [P] [US3] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/oversize_pad.md` that is one `add_finding` shy of `MAX_SCRATCHPAD_BYTES` to drive the rotation scenario [TS-017]
- [ ] T041 [P] [US3] Record fixture `tests/katas/018_scratchpad_persistence/fixtures/populated_schema_valid/` pairing a rendered pad with an expected-model JSON for the contract round-trip [TS-012, TS-015]
- [ ] T042 [P] [US3] Copy/symlink `specs/018-scratchpad-persistence/tests/features/machine_parseable_structure.feature` to `tests/katas/018_scratchpad_persistence/features/machine_parseable_structure.feature` so pytest-bdd can discover it
- [ ] T043 [US3] Implement BDD step definitions for [TS-012, TS-013, TS-014, TS-015, TS-016, TS-017, TS-018, TS-019] in `tests/katas/018_scratchpad_persistence/step_defs/test_machine_parseable_structure_steps.py` — steps drive the validator, the contract-schema round-trip against `scratchpad-document.schema.json`, `finding.schema.json`, `rotation-event.schema.json`, and `context-anchor.schema.json`, and the rotation trigger at the cap
- [ ] T044 [P] [US3] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_validator_round_trip.py` asserting every populated pad renders → parses → compares equal to its source model (D-006) [TS-012, TS-015]
- [ ] T045 [P] [US3] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_validator_rejects_drift.py` parametrised over drift kinds and asserting `ScratchpadSchemaError` is raised with the byte offset of the failure (FR-002, FR-010) [TS-016]
- [ ] T046 [P] [US3] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_writer_rejects_missing_metadata.py` asserting a write of a finding missing a required field raises `ScratchpadSchemaError` and leaves the on-disk file untouched [TS-014]
- [ ] T047 [P] [US3] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_rotation_cap.py` asserting that exceeding `MAX_SCRATCHPAD_BYTES` triggers a `RotationEvent`, archives the pad to `<name>.<iso-date>.md`, seeds the fresh pad with a `prior_pad` anchor, and the active size never exceeds the cap (FR-005, SC-004) [TS-017]
- [ ] T048 [P] [US3] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_rotation_event_contract.py` validating an emitted `RotationEvent` against `contracts/rotation-event.schema.json` for `event_id`, `rotated_from`, `rotated_to`, `size_at_rotation`, `rotated_at` [TS-018]
- [ ] T049 [P] [US3] Add unit test `tests/katas/018_scratchpad_persistence/unit/test_context_anchor_contract.py` validating an emitted `ContextAnchor` against `contracts/context-anchor.schema.json` [TS-019]
- [ ] T050 [P] [US3] Add AST lint test `tests/katas/018_scratchpad_persistence/lint/test_no_prose_classification.py` — parses `writer.py` and `validator.py` and fails if either imports `re`, runs `.find(`/`.search(`/`.match(`, or uses `in` against response prose for classification — classification MUST key off the typed `Finding.category` field (plan.md constraint; Principle I)

### Implementation for User Story 3

- [ ] T051 [US3] Implement `katas/018_scratchpad_persistence/validator.py::parse_and_validate(path) -> Scratchpad`: reads bytes, splits YAML frontmatter from markdown body, parses each declared section header, maps each numbered list item to a `Finding`, and raises `ScratchpadSchemaError(byte_offset=...)` on any unknown section, missing required field, or prose outside a declared section (FR-002, FR-010)
- [ ] T052 [US3] In `validator.py`, enforce section-name whitelist against the `SectionName` literal and the required `Finding` field set (`id`, `timestamp`, `category`, `evidence`, `source_ref`) — rejects any drift with a precise byte-offset error payload (FR-002, FR-006, SC-002)
- [ ] T053 [US3] Implement `katas/018_scratchpad_persistence/rotation.py::rotate_if_needed(path) -> RotationEvent | None`: stats the rendered file after each write; if `size_bytes > MAX_SCRATCHPAD_BYTES`, renames to `<name>.<iso-date>.md`, emits a `RotationEvent` to `runs/kata-018/<session-id>/rotation.jsonl`, and seeds a fresh pad whose frontmatter carries `prior_pad` pointing to the archived name (FR-005, SC-004)
- [ ] T054 [US3] Wire `rotation.rotate_if_needed` into `writer.py::_finalize_write` so enforcement is post-write — a crash mid-write cannot leave an oversized active file (plan.md constraint)
- [ ] T055 [US3] Implement the CLI entrypoint `katas/018_scratchpad_persistence/runner.py`: `python -m katas.018_scratchpad_persistence.runner --pad <path> --directive <str>` reads `LIVE_API` to choose `LiveClient` vs `RecordedClient`, opens the pad via `reader.load_on_session_start`, drives the investigation loop, prints `runs/kata-018/<session-id>/` on exit

**Checkpoint**: At end of User Story 3, the scratchpad is schema-enforced end-to-end: validator fails loud on drift, rotation caps size without data loss, and every artefact (scratchpad, rotation event, context anchor) round-trips through its JSON Schema contract.

---

## Final Phase: Polish

Cross-cutting quality, documentation, and the reflection handoff. No story label.

- [ ] T056 [P] Author `katas/018_scratchpad_persistence/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — durable externalisation of investigation findings, fixed-section scratchpad (`map`/`findings`/`open_questions`/`decisions`/`conflicts`), YAML frontmatter + markdown body, atomic flock-serialised writes (tmpfile + `os.replace` + parse-round-trip check), `/compact` at ≥ 0.55 fill emits a `ContextAnchor`, byte-rotation at `MAX_SCRATCHPAD_BYTES = 100_000`, session-start re-read before first user query, no-context-window-hoarding anti-pattern — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`models` → `scratchpad` → `writer` → `reader` → `validator` → `rotation` → `compaction_bridge` → `client` → `runner` → `constants`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — externalise-don't-hoard, atomic-write-with-roundtrip, fill-trigger compaction, byte-bound rotation — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, III Context Economy, VII Provenance, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — every write is flock-serialised, atomic via tmpfile + `os.replace`, followed by parse-round-trip check; `/compact` at ≥ 0.55 fill emits a `ContextAnchor`; rotation at `MAX_SCRATCHPAD_BYTES = 100_000` archives to `<name>.<iso-date>.md`; session start re-reads the pad before the first user query (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T058 [P] Add module docstrings to every kata module (`models.py`, `scratchpad.py`, `writer.py`, `reader.py`, `validator.py`, `rotation.py`, `compaction_bridge.py`, `client.py`, `runner.py`, `constants.py`) — each docstring names the FR(s) the module satisfies and the anti-pattern it defends against (Principle VIII)
- [ ] T059 [P] Add why-comments to every non-trivial function / validator tying the implementation choice to its FR or to the anti-pattern it blocks (Principle VIII, plan.md Constitution Check row)
- [ ] T060 [P] Regenerate the Intent Integrity dashboard via `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` so 018 shows green on tasks
- [ ] T061 Verify and run quickstart: execute every command in `specs/018-scratchpad-persistence/quickstart.md` end-to-end (install, fixture run, inspect-live with `LIVE_API=1`, compact) and fix any drift between the doc and the runner CLI
- [ ] T062 [P] Run the full offline suite `pytest tests/katas/018_scratchpad_persistence -v` and assert every `@TS-NNN` scenario across the three feature files passes; rerun with `LIVE_API=1` and confirm the compact-resume probe scores rediscovery = 0 (SC-001)
- [ ] T063 [P] Run `pytest tests/katas/018_scratchpad_persistence/lint -v` to confirm the AST lint forbids any prose-based classification in `writer.py` / `validator.py` (Principle I)

---

## Dependencies

- Phase 1 (Setup: T001–T005) blocks everything else.
- Phase 2 (Foundational: T006–T010) blocks Phases 3, 4, 5.
- Phase 3 (US1: T011–T023) is independently testable and may ship as MVP.
- Phase 4 (US2: T024–T038) depends on Phase 3's `ScratchpadWriter` / `Scratchpad` model.
- Phase 5 (US3: T039–T055) depends on Phase 3's writer + Phase 4's conflict routing; the validator in T051–T052 is reusable by Phase 4's `reader.load_on_session_start`.
- Final Polish (T056, T058–T063) depends on all prior phases; T062 and T063 are the acceptance gate.
