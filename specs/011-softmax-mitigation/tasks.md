# Tasks: Softmax Dilution Mitigation

**Input**: Design documents from `/specs/011-softmax-mitigation/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] = parallelizable (different files, no deps)
- [USn] = required on user-story tasks; omit on Setup/Foundational/Polish
- Traceability: list test IDs as comma-separated, e.g. `[TS-001, TS-002]`, NEVER "TS-001 through TS-007"

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/011_softmax_mitigation/__init__.py` (empty marker) and mirror test package `tests/katas/011_softmax_mitigation/__init__.py`
- [ ] T002 [P] Extend the repo-root `pyproject.toml` `[dev]` extras to declare `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, and `tiktoken` per plan.md Technical Context (if already declared by kata 001, add only missing pins)
- [ ] T003 [P] Confirm `ruff` + `black` config in `pyproject.toml` covers `katas/011_softmax_mitigation/` and `tests/katas/011_softmax_mitigation/`; exclude `runs/` and fixtures subtree
- [ ] T004 [P] Ensure `runs/kata-011/` is covered by the existing `runs/` entry in `.gitignore` (per plan.md: live-sweep artifacts are gitignored)
- [ ] T005 [P] Create `tests/katas/011_softmax_mitigation/conftest.py` stub that declares the `pytest-bdd` features directory `tests/katas/011_softmax_mitigation/features/`, exposes a fixture-session loader helper, and wires a deterministic `tiktoken` tokenizer fixture

---

## Phase 2: Foundational

Shared infrastructure blocking all stories — pydantic models, JSON schemas wired into tests, injectable SDK client, typed exceptions, and tokenizer accessor. No story label.

- [ ] T006 [P] Implement shared pydantic v2 entities in `katas/011_softmax_mitigation/models.py`: `CriticalRule`, `EdgeRegion`, `PromptLayout`, `CompactionEvent`, `ComplianceRecord`, plus `Literal` types for `layout_label`, `edge_position`, and `compliance_outcome` — all per `data-model.md`; every model declares `extra="forbid"`
- [ ] T007 [P] Declare typed exceptions in `katas/011_softmax_mitigation/exceptions.py`: `EdgePlacementViolation` (FR-005), `AntiPatternNotAuthorized` (FR-006), `CompactionOverdue` (FR-002, SC-003), `RuleMissingAfterCompaction` (FR-003, SC-004); each carries enough structured context (rule id, usage fraction, region position) for the audit log
- [ ] T008 [P] Add a contract-schema loader in `tests/katas/011_softmax_mitigation/conftest.py::load_contract_schema(name)` that resolves paths under `specs/011-softmax-mitigation/contracts/` so step defs and unit tests can validate serialized payloads against the frozen JSON Schemas
- [ ] T009 [P] Implement the thin injectable Anthropic client wrapper in `katas/011_softmax_mitigation/client.py` exposing a single `send(messages, tools, response_schema) -> RawResponse` surface; real SDK behind a `LiveClient`, fixture replay behind a `RecordedClient` that reads `tests/katas/011_softmax_mitigation/fixtures/<name>.json`
- [ ] T010 [P] Implement a deterministic tokenizer adapter in `katas/011_softmax_mitigation/tokenizer.py` wrapping `tiktoken` with a stable `count_tokens(text) -> int` helper — this is the sole source of `length_tokens`, `mid_body_tokens`, `total_tokens`, and the `usage_fraction` used by the compaction trigger (plan.md Constraints)
- [ ] T011 [P] Implement append-only session writers in `katas/011_softmax_mitigation/runlog.py`: opens `runs/kata-011/<session-id>/layouts/<label>.txt`, `compliance.jsonl`, and `compactions.jsonl`; enforces `ComplianceRecord` / `CompactionEvent` schemas on every write (no prose fields admitted — Principle II + plan.md storage contract)

**Checkpoint**: Foundation ready — entities, typed exceptions, contract loader, injectable client, tokenizer adapter, and the run-log writers are all in place. Builder, trigger, and harness logic can now be implemented against them.

---

## Phase 3: User Story 1 - Edge Placement of Critical Rule (Priority: P1) MVP

**Goal**: A practitioner authors a long prompt with a declared critical rule anchored at both the primacy and latency edges, runs a representative adversarial request batch, and observes a rule-compliance rate of at least 95%. Construction rejects any content that would evict a rule from its edge region; multi-rule contention is resolved by a declared priority integer with input-order tie-break.

**Independent Test**: Run the kata harness against `edge_placed_short.json` and the boundary/contention fixtures; assert edge-placed compliance rate ≥ 95%, every declared rule id appears in both edge regions, and construction raises `EdgePlacementViolation` on the oversized-content and oversized-rule fixtures.

### Tests for User Story 1

- [ ] T012 [P] [US1] Record fixture session `tests/katas/011_softmax_mitigation/fixtures/edge_placed_short.json` — short critical rule anchored at both edges, adversarial batch returning structured probe payloads validating against `compliance_probe_schema`
- [ ] T013 [P] [US1] Record fixture session `tests/katas/011_softmax_mitigation/fixtures/edge_placed_boundary.json` — rule whose `length_tokens` is exactly `budget_tokens - 1` (boundary case), both edges anchored
- [ ] T014 [P] [US1] Record fixture session `tests/katas/011_softmax_mitigation/fixtures/rule_evicts_content.json` — filler corpus sized so placing it would push the critical rule out of the primacy region (drives `EdgePlacementViolation`)
- [ ] T015 [P] [US1] Record fixture session `tests/katas/011_softmax_mitigation/fixtures/multi_rule_priority.json` — two critical rules whose combined size exceeds the edge budget, with declared priorities exercising the three cases in the TS-006 Scenario Outline examples
- [ ] T016 [P] [US1] Copy/symlink `specs/011-softmax-mitigation/tests/features/edge_placement_of_critical_rule.feature` to `tests/katas/011_softmax_mitigation/features/edge_placement_of_critical_rule.feature` so pytest-bdd can discover it
- [ ] T017 [US1] Implement BDD step definitions for [TS-001, TS-002] in `tests/katas/011_softmax_mitigation/step_defs/test_edge_placement_steps.py` — steps wire to `RecordedClient`, drive the compliance harness against `edge_placed_short.json` + `edge_placed_boundary.json`, and assert the observed compliance rate ≥ 95% plus every `"obeyed"` ComplianceRecord carries a probe payload validating against the rule's `compliance_probe_schema`
- [ ] T018 [US1] Extend `tests/katas/011_softmax_mitigation/step_defs/test_edge_placement_steps.py` with step definitions for [TS-003] — assert every declared rule id appears in both `primacy_region.placed_rule_ids` and `latency_region.placed_rule_ids` and nowhere in the `deferred_rule_ids` lists
- [ ] T019 [US1] Extend `tests/katas/011_softmax_mitigation/step_defs/test_edge_placement_steps.py` with step definitions for [TS-004, TS-005] — drive `PromptBuilder` with oversized-filler and oversized-rule configurations and assert `EdgePlacementViolation` is raised and no `PromptLayout` instance is returned
- [ ] T020 [US1] Extend `tests/katas/011_softmax_mitigation/step_defs/test_edge_placement_steps.py` with step definitions for [TS-006] — drive the Scenario Outline examples against `multi_rule_priority.json` and assert the placed/deferred rule ids match per priority with input-order tie-break (D-005)
- [ ] T021 [US1] Extend `tests/katas/011_softmax_mitigation/step_defs/test_edge_placement_steps.py` with step definitions for [TS-007] — serialize the edge-placed `PromptLayout`, validate it against `specs/011-softmax-mitigation/contracts/prompt-layout.schema.json`, and assert `primacy_region.position == "primacy"` and `latency_region.position == "latency"`
- [ ] T022 [P] [US1] Add unit test `tests/katas/011_softmax_mitigation/unit/test_prompt_builder_edges.py` covering every branch of the edge-placement validator: rule fits, rule exactly fills the budget, rule exceeds budget, filler exactly fills remainder, filler exceeds remainder — for both `edge_placed` and `edge_placed_with_compaction` labels (FR-001, FR-003, FR-005)
- [ ] T023 [P] [US1] Add unit test `tests/katas/011_softmax_mitigation/unit/test_rule_priority_competition.py` exercising the declared priority + input-order tie-break on synthetic rule lists — proves the deterministic placement rule from D-005 (edge case "multi-rule competition for edge real estate")
- [ ] T024 [P] [US1] Add unit test `tests/katas/011_softmax_mitigation/unit/test_reject_content_gate.py` asserting `EdgePlacementViolation` is raised on (a) content that would push a placed rule past `budget_tokens` and (b) a rule whose own `length_tokens` exceeds `budget_tokens` — FR-005 + spec.md edge case "critical rule longer than edge budget"
- [ ] T025 [P] [US1] Add AST lint test `tests/katas/011_softmax_mitigation/lint/test_no_prose_matching.py` — parses `katas/011_softmax_mitigation/compliance.py` and fails if it imports `re`, calls `.find(`/`.index(`/`.search(`/`.match(` on response text, or uses the `in` operator to test response-text substrings; scoring MUST consume only the typed `ComplianceOutcome` / `probe_payload` pair (plan.md Constraints, Principle I)

### Implementation for User Story 1

- [ ] T026 [US1] Implement `katas/011_softmax_mitigation/prompt_builder.py::PromptBuilder` — `build(label, rules, filler_corpus, context_window_tokens, allow_anti_pattern=False)` returns a validated `PromptLayout`; for `edge_placed` it places every rule verbatim at both edges, fills the middle with the corpus, computes `total_tokens` and `usage_fraction` via the tokenizer adapter, and raises `EdgePlacementViolation` on any budget breach (FR-001, FR-005)
- [ ] T027 [US1] In `katas/011_softmax_mitigation/prompt_builder.py`, implement the multi-rule priority resolver: sort declared rules by `priority` ascending with input-order tie-break, greedily place into each `EdgeRegion` until the budget is exhausted, and record overflow rules in `deferred_rule_ids` — never silently drop a rule (spec.md edge case + D-005)
- [ ] T028 [US1] In `katas/011_softmax_mitigation/compliance.py`, implement `score_trial(response, rule) -> ComplianceRecord` that validates the model's structured response against `rule.compliance_probe_schema`, assigns `outcome` in `{"obeyed", "violated", "undetermined"}` purely from the structured payload (no regex over prose), and populates `prompt_hash` from the exact rendered prompt (FR-007, D-006)
- [ ] T029 [US1] Implement the CLI entrypoint `katas/011_softmax_mitigation/runner.py` with `python -m katas.011_softmax_mitigation.runner --layout edge_placed --trials N`; reads `LIVE_API` to choose `LiveClient` vs `RecordedClient`; on exit prints the `runs/kata-011/<session-id>/` path and the observed compliance rate

**Checkpoint**: US1 fully functional — edge-placed fixture runs clear the 95% target, multi-rule competition resolves deterministically, oversized filler and oversized rules raise `EdgePlacementViolation`, AST lint blocks any reintroduction of prose-matched scoring, and BDD scenarios [TS-001, TS-002, TS-003, TS-004, TS-005, TS-006, TS-007] all pass.

---

## Phase 4: User Story 2 - Anti-Pattern Demonstration: Rule Buried in the Middle (Priority: P2)

**Goal**: A practitioner runs the controlled anti-pattern variant (same rule, same adversarial batch) with the rule placed in the middle third of the prompt, observes a compliance drop of at least 20 percentage points versus the edge-placed baseline, and receives a clearly labelled anti-pattern report attributing the violations to mid-context burying. The anti-pattern layout cannot be constructed without an explicit opt-in flag.

**Independent Test**: Render the same rule + corpus as US1 under the `mid_buried` label with `allow_anti_pattern=True`, replay the same adversarial batch, compute the compliance delta against the US1 baseline, and assert the delta is ≥ 20 pp and the anti-pattern report names every violating trial.

### Tests for User Story 2

- [ ] T030 [P] [US2] Record fixture session `tests/katas/011_softmax_mitigation/fixtures/mid_buried_short.json` — same rule + adversarial batch as `edge_placed_short.json` but rendered with the rule buried in the mid-body, returning probe payloads that demonstrate the dilution effect
- [ ] T031 [P] [US2] Copy/symlink `specs/011-softmax-mitigation/tests/features/antipattern_mid_buried_rule.feature` to `tests/katas/011_softmax_mitigation/features/antipattern_mid_buried_rule.feature`
- [ ] T032 [US2] Implement BDD step definitions for [TS-010] in `tests/katas/011_softmax_mitigation/step_defs/test_antipattern_mid_buried_steps.py` — steps record the edge-placed baseline rate (from US1 harness), run the harness against `mid_buried_short.json`, and assert the compliance rate drops by at least 20 pp and the delta is recorded against `PromptLayout.min_delta_pct`
- [ ] T033 [US2] Extend `tests/katas/011_softmax_mitigation/step_defs/test_antipattern_mid_buried_steps.py` with step definitions for [TS-011] — assert the generated anti-pattern report is clearly labelled, names each violating trial by `ComplianceRecord.trial_id`, and attributes the violations to mid-context burying of the critical rule
- [ ] T034 [US2] Extend `tests/katas/011_softmax_mitigation/step_defs/test_antipattern_mid_buried_steps.py` with step definitions for [TS-012] — drive `PromptBuilder.build(label="mid_buried", allow_anti_pattern=False)` and assert `AntiPatternNotAuthorized` is raised and no `PromptLayout` is returned (FR-006)
- [ ] T035 [US2] Extend `tests/katas/011_softmax_mitigation/step_defs/test_antipattern_mid_buried_steps.py` with step definitions for [TS-013] — assert the `mid_buried` layout renders with empty `placed_rule_ids` on both regions and the rule text appears only inside the mid-body portion of `rendered_prompt`
- [ ] T036 [US2] Extend `tests/katas/011_softmax_mitigation/step_defs/test_antipattern_mid_buried_steps.py` with step definitions for [TS-014] — serialize the `mid_buried` layout, validate it against `contracts/prompt-layout.schema.json`, and assert `min_delta_pct` is present and ≥ 20 and `compliance_target_pct` is present and ≤ 100
- [ ] T037 [P] [US2] Add unit test `tests/katas/011_softmax_mitigation/unit/test_anti_pattern_flag.py` covering: `allow_anti_pattern=False` + `label="mid_buried"` → `AntiPatternNotAuthorized`; `allow_anti_pattern=True` + `label="edge_placed"` → also forbidden (flag is meaningful only for the anti-pattern label); `allow_anti_pattern=True` + `label="mid_buried"` → builds successfully with empty edge regions (FR-006)
- [ ] T038 [P] [US2] Add unit test `tests/katas/011_softmax_mitigation/unit/test_structured_disambiguation.py` — drive synthetic probe payloads that are ambiguous on the surface text but unambiguous under the typed `compliance_probe_schema`, and assert the scorer returns `"obeyed"` / `"violated"` / `"undetermined"` strictly from the structured fields, never from prose (D-006 + Principle I)

### Implementation for User Story 2

- [ ] T039 [US2] In `katas/011_softmax_mitigation/prompt_builder.py`, implement the `mid_buried` branch: require `allow_anti_pattern=True` (else raise `AntiPatternNotAuthorized`), render with both edge regions empty of rules, place the rule text inside the mid-body, and populate `min_delta_pct` (default 20 pp from D-003) on the returned layout (FR-006, FR-007)
- [ ] T040 [US2] In `katas/011_softmax_mitigation/compliance.py`, implement `generate_anti_pattern_report(edge_placed_run, mid_buried_run) -> AntiPatternReport` that computes the pp delta, enumerates every violating `ComplianceRecord.trial_id`, attributes each violation to mid-context burying, and writes the report into `runs/kata-011/<session-id>/anti_pattern_report.md` for audit (FR-004, FR-007)
- [ ] T041 [US2] In `katas/011_softmax_mitigation/runner.py`, add a `--compare` mode that executes the edge-placed + mid-buried sweep pair end-to-end, writes both `ComplianceRecord` JSONL files, invokes `generate_anti_pattern_report`, and surfaces the delta in stdout — this is the harness behind US2's acceptance scenario

**Checkpoint**: US2 fully functional — mid-buried fixture produces a compliance drop ≥ 20 pp, the anti-pattern report is generated and labelled, construction without `allow_anti_pattern=True` raises `AntiPatternNotAuthorized`, structured-disambiguation unit tests keep scoring signal-driven, and BDD scenarios [TS-010, TS-011, TS-012, TS-013, TS-014] all pass.

---

## Phase 5: User Story 3 - Proactive Compaction and Re-Anchoring (Priority: P3)

**Goal**: A practitioner drives a long multi-turn session past the 55% capacity threshold, observes a `CompactionEvent` firing inside the 55–60% band, verifies every declared critical rule is re-anchored verbatim at both edges of the post-compaction prompt, and replays the adversarial batch against the compacted session with compliance still at the ≥ 95% target. Sessions that reach 0.61 without a compaction attempt raise `CompactionOverdue` and refuse to dispatch the turn.

**Independent Test**: Script a session that ramps `usage_fraction` through 0.49, 0.55, 0.59, 0.60, 0.61; assert the trigger fires inside `[0.55, 0.60)`, `CompactionOverdue` raises at 0.61 with no prior fire, the post-compaction prompt contains every rule verbatim at both edges, and the replayed adversarial batch clears the ≥ 95% compliance target.

### Tests for User Story 3

- [ ] T042 [P] [US3] Record fixture session `tests/katas/011_softmax_mitigation/fixtures/compaction_event_boundary.json` — multi-turn session whose cumulative token usage crosses the 55–60% band, with the post-compaction probe payloads needed to drive [TS-020, TS-023, TS-025]
- [ ] T043 [P] [US3] Copy/symlink `specs/011-softmax-mitigation/tests/features/proactive_compaction_and_reanchoring.feature` to `tests/katas/011_softmax_mitigation/features/proactive_compaction_and_reanchoring.feature`
- [ ] T044 [US3] Implement BDD step definitions for [TS-020] in `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` — drive the session until `usage_fraction` crosses 0.55, assert a `CompactionEvent` is emitted before `usage_fraction > 0.60`, and `event.fired_at_usage_fraction` lies in `[0.55, 0.60)`
- [ ] T045 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-021] — evaluate the `CompactionTrigger` at the Scenario Outline examples `{0.49, 0.55, 0.59, 0.60, 0.61}` and assert the fire decision matches the expected boolean
- [ ] T046 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-022] — drive a session whose `usage_fraction` reaches 0.61 without any prior `CompactionEvent` and assert `CompactionOverdue` is raised and the turn is refused
- [ ] T047 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-023] — after a completed `CompactionEvent`, render the post-compaction `PromptLayout` and assert every declared rule appears verbatim in both edge regions' `placed_rule_ids` and the content is byte-identical to the pre-compaction rule content
- [ ] T048 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-024] — attempt to construct a `CompactionEvent` with a non-empty `rules_missing_after` and assert `RuleMissingAfterCompaction` is raised and no event is persisted to `compactions.jsonl`
- [ ] T049 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-025] — record a pre-compaction edge-placed compliance rate, run the adversarial batch against the post-compaction prompt, and assert the post-compaction rate is not materially lower than the pre-compaction rate and remains ≥ 95%
- [ ] T050 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-026] — serialize the `CompactionEvent`, validate against `contracts/compaction-event.schema.json`, and assert the record carries `event_id`, `session_id`, `fired_at_usage_fraction`, `collapsed_turn_count`, `rules_preserved`, and `rules_missing_after == []`
- [ ] T051 [US3] Extend `tests/katas/011_softmax_mitigation/step_defs/test_proactive_compaction_steps.py` with step definitions for [TS-027] — run a full sweep covering `edge_placed`, `mid_buried`, and `edge_placed_with_compaction`, validate every `ComplianceRecord` against `contracts/compliance-record.schema.json`, and assert each record carries `trial_id`, `layout_label`, `rule_id`, `outcome`, `prompt_hash`, and every `"obeyed"` record has a non-null `probe_payload`
- [ ] T052 [P] [US3] Add unit test `tests/katas/011_softmax_mitigation/unit/test_compaction_trigger_threshold.py` — boundary table covering `{0.49, 0.54, 0.55, 0.59, 0.60, 0.61}` with expected fire decisions (explicit superset of feature TS-021's `{0.49, 0.55, 0.59, 0.60, 0.61}` — 0.54 is an additional below-threshold data point for unit-level coverage; fire/no-fire decisions match TS-021 for every shared value), plus a test asserting `fired_at_usage_fraction` values outside `[0.55, 0.60)` raise on `CompactionEvent` construction (FR-002, SC-003)
- [ ] T053 [P] [US3] Add unit test `tests/katas/011_softmax_mitigation/unit/test_compliance_record_shape.py` asserting every emitted `ComplianceRecord` validates against `contracts/compliance-record.schema.json`, `prompt_hash` is sha256 hex of the exact rendered prompt, and records with `outcome=="obeyed"` always carry a non-null `probe_payload` (FR-007)

### Implementation for User Story 3

- [ ] T054 [US3] Implement `katas/011_softmax_mitigation/compaction.py::CompactionTrigger` — `should_fire(usage_fraction) -> bool` returns True for `usage_fraction >= 0.55`; `fire(session) -> CompactionEvent` summarises older turns, preserves every `CriticalRule` verbatim, populates `rules_preserved`, and raises `RuleMissingAfterCompaction` if any rule fails re-anchoring (FR-002, FR-003, SC-003, SC-004)
- [ ] T055 [US3] In `katas/011_softmax_mitigation/compaction.py`, implement the `CompactionOverdue` guard: if `should_fire(usage)` returned False and the next observed usage exceeds 0.60 without any prior `CompactionEvent` on the session, raise `CompactionOverdue` and refuse to dispatch the turn (FR-002, SC-003 fail-closed)
- [ ] T056 [US3] In `katas/011_softmax_mitigation/prompt_builder.py`, implement the `edge_placed_with_compaction` re-anchoring branch: after a `CompactionEvent` fires, render a fresh `PromptLayout` whose mid-body is replaced by `summary_text` and whose edge regions carry every declared rule verbatim — byte-identical to the pre-compaction rule content (FR-003, SC-004)
- [ ] T057 [US3] In `katas/011_softmax_mitigation/runner.py`, add a `--session` mode that drives a scripted long session, invokes the trigger on each turn, writes every `CompactionEvent` to `runs/kata-011/<session-id>/compactions.jsonl`, and prints the trigger fraction on exit — this is the harness behind US3's acceptance scenarios

**Checkpoint**: US3 fully functional — compaction fires inside the 55–60% band, `CompactionOverdue` fails closed at 0.61 with no prior fire, post-compaction prompts re-anchor every rule verbatim at both edges, replayed adversarial batch stays ≥ 95%, and BDD scenarios [TS-020, TS-021, TS-022, TS-023, TS-024, TS-025, TS-026, TS-027] all pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T058 [P] Author `katas/011_softmax_mitigation/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — softmax-collapse / lost-in-the-middle problem, edge-placement anchoring, proactive compaction at 55% trigger, structured-disambiguation probes (`compliance_probe_schema`), reject-content gate, signal-driven compliance scoring vs prose-coercion, A/B mid-buried fixture for self-proof — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`prompt_builder` → `models` → `compaction` → `compliance` → `tokenizer` → `client` → `runlog` → `runner`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — edge-placement-over-middle, proactive-compaction-before-saturation, structured-probe-for-scoring, reject-undetermined-instead-of-coerce — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, III Context Economy, V Test-First, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — `runs/kata-011/<session-id>/{layouts,compliance.jsonl,compactions.jsonl,anti_pattern_report.md}` is the single source of truth; SC-001..SC-004 re-derivable from those files alone (Principle VII); structured-disambiguation strategy (D-006) — model emits JSON against `CriticalRule.compliance_probe_schema`, scorer reads typed fields only, ambiguous responses surface as `outcome="undetermined"` rather than coerced (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T059 [P] Add module-level docstrings to each of `katas/011_softmax_mitigation/models.py`, `prompt_builder.py`, `compaction.py`, `compliance.py`, `client.py`, `tokenizer.py`, `runlog.py`, `exceptions.py`, `runner.py` — each docstring states the module's role in the softmax-dilution defense (Principle VIII)
- [ ] T060 [P] Add why-comments (per Constitution Principle VIII) on every non-trivial validator, builder branch, and trigger decision across `katas/011_softmax_mitigation/*.py` — each comment ties the code choice back to the kata's Principle III context-economy objective (edge anchoring / reject-content gate / 55% trigger / re-anchoring) rather than describing *what* the code does
- [ ] T061 [P] Verify `specs/011-softmax-mitigation/quickstart.md` usage walkthrough is accurate against the final file layout; update paths, commands, and the scenario→spec mapping if drift was introduced during implementation
- [ ] T062 Run `quickstart.md` end-to-end: `pytest tests/katas/011_softmax_mitigation -v` against fixtures, then optional `LIVE_API=1 python -m katas.011_softmax_mitigation.runner --compare --trials 20` smoke run; record both outputs as part of PR evidence
- [ ] T064 [P] Run `ruff check katas/011_softmax_mitigation tests/katas/011_softmax_mitigation` and `black --check` over the same paths; fix any findings
- [ ] T065 [P] Produce a coverage report (`pytest --cov=katas.011_softmax_mitigation`) and archive it at `runs/coverage/011_softmax_mitigation.txt`; target ≥ 90% line coverage on `prompt_builder.py`, `compaction.py`, and `compliance.py`
- [ ] T066 Final self-audit: read the emitted `compliance.jsonl` + `compactions.jsonl` from a compare-mode run and confirm they satisfy SC-001, SC-002, SC-003, SC-004 — record the check in the PR description

---

## Dependencies & Execution Order

**Phase order (strict):** Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6.

**Within-phase dependencies:**
- Phase 2: T006–T011 all live in different files and are [P]. T006 blocks all later entity uses; T007 blocks every raise-site; T009 blocks every harness run; T010 blocks every `length_tokens` / `usage_fraction` computation; T011 blocks every audit write.
- Phase 3: T012–T016 (fixtures + feature copy) can run in parallel. T017–T021 all live in the same step-def file and must run sequentially. T022–T025 are [P] once T006/T007/T010 exist. T026 depends on T006, T007, T010. T027 depends on T026. T028 depends on T006, T009, T011. T029 depends on T026, T028.
- Phase 4: T030, T031 are [P]. T032–T036 live in the same step-def file and must run sequentially. T037, T038 are [P] once T006/T007 exist. T039 depends on T026. T040 depends on T028, T011. T041 depends on T029, T039, T040.
- Phase 5: T042, T043 are [P]. T044–T051 live in the same step-def file and must run sequentially. T052, T053 are [P] once T006/T007 exist. T054 depends on T006, T007, T010. T055 depends on T054. T056 depends on T026, T054. T057 depends on T029, T054, T056.
- Phase 6: T058–T061, T064, T065 are [P]. T062 depends on all prior phases complete. T066 depends on T062.

**Story dependencies:**
- US2 consumes the edge-placed baseline produced by US1 — cannot assert the 20 pp delta until T026–T029 land.
- US3 extends the builder built in US1 (the `edge_placed_with_compaction` re-anchoring branch) and consumes the harness built in US1/US2 — cannot validate post-compaction compliance until prior stories have produced a baseline.

---

## Parallel Opportunities

**Phase 1 [P]:** T002, T003, T004, T005 (different config / conftest files).

**Phase 2 [P]:** T006, T007, T008, T009, T010, T011 (distinct modules).

**Phase 3 [P]:** fixture recording batch — T012, T013, T014, T015, T016 all in parallel; then T022, T023, T024, T025 in parallel once T006/T007/T010 exist; T017–T021 gate on fixtures + T006/T009/T011.

**Phase 4 [P]:** T030, T031 fixture/feature batch in parallel; T037, T038 in parallel once foundational entities exist.

**Phase 5 [P]:** T042, T043 in parallel; T052, T053 in parallel once foundational entities exist.

**Phase 6 [P]:** T058, T059, T060, T061, T064, T065 all in parallel.

---

## Implementation Strategy

- **MVP**: Phase 1 + Phase 2 + Phase 3 (US1). At this point the kata demonstrates Principle III end-to-end: edge-placed anchoring, deterministic multi-rule priority, the reject-content gate, signal-driven compliance scoring, and the AST lint blocking prose-matching. This is already a credible Principle III kata deliverable.
- **Incremental delivery**: land Phase 4 (US2) next — adds the anti-pattern red-team (mid-buried rendering, 20 pp delta assertion, anti-pattern report). Then Phase 5 (US3) adds proactive compaction, `CompactionOverdue` fail-closed, and re-anchoring. Phase 6 documents and polishes.
- **Blast radius**: every phase is gated by BDD scenarios failing first (TDD per Constitution V); Phase 6's `quickstart.md` run is the final acceptance gate.

---

## Notes

- `[P]` = different files, no shared state, no ordering dependency.
- Each user story is independently testable — US1 against `edge_placed_short.json` + boundary/contention fixtures, US2 against `mid_buried_short.json` + the US1 baseline, US3 against `compaction_event_boundary.json` + a scripted usage-fraction ramp.
- Verify every `.feature` scenario fails before writing the matching production code (Constitution V — TDD). Do NOT make tests pass by editing assertions; fix the builder/trigger/scorer instead (assertion-integrity rule).
- AST lint test `tests/katas/011_softmax_mitigation/lint/test_no_prose_matching.py` is the irreversible guardrail against regression into prose-matched scoring — keep it green at all times after T025.
- Structured-disambiguation strategy (D-006) is what makes the compliance score signal-driven: the model emits JSON against `CriticalRule.compliance_probe_schema`, the scorer reads typed fields only, and ambiguous responses surface as `outcome="undetermined"` rather than being coerced — document this in `notebook.ipynb` (T058) alongside the anti-pattern defense.
