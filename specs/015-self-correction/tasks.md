# Tasks: Critical Evaluation & Self-Correction

**Input**: Design documents from `/specs/015-self-correction/`
**Prerequisites**: plan.md, spec.md, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] required on story tasks
- Traceability: `[TS-001, TS-002]`, never ranges

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton at `katas/015_self_correction/__init__.py` with module docstring declaring the kata objective (dual-total cross-audit, silent-overwrite defense, human-review routing).
- [ ] T002 Create test package skeleton at `tests/katas/015_self_correction/__init__.py` (empty, marks directory as test package).
- [ ] T003 Ensure `pyproject.toml` at repo root exposes `anthropic`, `pydantic>=2`, `pytest`, `pytest-bdd`, and `jsonschema` in the `[dev]` extras (required by `plan.md` Technical Context). Add if missing; no-op if already declared by prior katas.
- [ ] T004 [P] Add `runs/` to `.gitignore` if not already present (artifact directory per `plan.md` Storage — `runs/<session-id>/extractions.jsonl` and `runs/<session-id>/review-queue.jsonl`).
- [ ] T005 [P] Create `tests/katas/015_self_correction/conftest.py` with the fixture loader stub, `tolerance_cents` default fixture, `RecordedClient` wiring, and `LIVE_API=1` gate. Signatures only; implementations land in later tasks.

---

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [ ] T006 Implement pydantic v2 `LineItem` model in `katas/015_self_correction/models.py` with `Decimal` money fields (`quantity`, `unit_price`, `line_total`), optional `sku` and `source_page`, and a `model_validator(mode="after")` that enforces `line_total == quantity * unit_price` within 1-cent tolerance (data-model.md).
- [ ] T007 Implement pydantic v2 `CalculationTrace` model in `katas/015_self_correction/models.py` as an ordered list of per-line entries (`sku`, `description`, `amount`, `running_sum`) backing the audit trail (FR-007).
- [ ] T008 Implement pydantic v2 `InvoiceExtraction` model in `katas/015_self_correction/models.py` with fields `invoice_id`, `currency`, `stated_total: Decimal`, `calculated_total: Decimal`, `line_items: list[LineItem]`, `tolerance_cents: int = 1`, and `conflict_detected: bool` (data-model.md, FR-001, FR-003, FR-008).
- [ ] T009 Implement `model_validator(mode="after")` on `InvoiceExtraction` in `katas/015_self_correction/models.py` that re-sums `line_items[*].line_total` into `calculated_total`, sets `conflict_detected = abs(stated_total - calculated_total) > tolerance_cents/100`, and raises `ValidationError` if a model-emitted `conflict_detected` contradicts the derived value — this is the forgery gate (FR-002, FR-003, FR-004).
- [ ] T010 Implement pydantic v2 `ConflictRecord` model in `katas/015_self_correction/models.py` with `record_id` (UUID4), `invoice_id`, frozen `stated_total` / `calculated_total`, signed `delta`, `line_items_snapshot`, and `detected_at` (UTC) per `data-model.md`.
- [ ] T011 Implement pydantic v2 `ReviewQueueEntry` model in `katas/015_self_correction/models.py` with `entry_id` (UUID4), `conflict_record_id`, `priority` (`Literal["low","medium","high"]`), `status` (`Literal["pending","in_review","resolved"]`), and optional `resolution_note` (data-model.md, FR-005).
- [ ] T012 Implement thin injectable Anthropic client wrapper in `katas/015_self_correction/client.py` sharing the `RecordedClient` shape used by prior katas; default run is offline against recorded responses, live mode gated by `LIVE_API=1`.
- [ ] T013 Author the seven labeled fixture cases under `tests/katas/015_self_correction/fixtures/` (`consistent_invoice.json`, `line_sum_mismatch.json`, `missing_line_items.json`, `non_numeric_amounts.json`, `currency_mismatch.json`, `rounding_only_diff.json`, `very_long_invoice.json` ≥ 50 line items) per `plan.md` Project Structure.
- [ ] T014 Implement fixture loader in `tests/katas/015_self_correction/conftest.py` that reads a fixture JSON and returns a structured invoice plus expected-labels payload (expected `stated_total`, expected `calculated_total`, expected `conflict_detected`).
- [ ] T015 Copy the three locked feature files from `specs/015-self-correction/tests/features/` to `tests/katas/015_self_correction/features/` (`consistent_invoice_passes_cross_audit.feature`, `conflicting_invoice_routes_to_review.feature`, `totals_never_silently_overwritten.feature`). Do NOT modify scenarios — they are assertion-integrity anchored.

**Checkpoint**: Foundational layer complete. `InvoiceExtraction` re-sums and flags conflict mechanically, `ConflictRecord` / `ReviewQueueEntry` validate, fixtures load, `.feature` files are in place. No user-story work can begin until this phase passes.

---

## Phase 3: User Story 1 — Consistent Invoice Passes Cross-Audit (P1) — MVP

**Goal**: A consistent invoice yields `stated_total`, an independently recomputed `calculated_total`, `conflict_detected=false`, and a per-line-item calculation trace — proving the pipeline actually recomputes rather than echoing the stated figure.

**Independent Test**: Feed the `consistent_invoice.json` fixture to the extractor; assert both totals emit verbatim, `conflict_detected=false`, the calculation trace has one entry per line, and the schema validates against `contracts/invoice-extraction.schema.json`.

### Tests for User Story 1

- [ ] T016 [P] [US1] Register the `consistent_invoice_passes_cross_audit.feature` scenarios in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` via `pytest-bdd` `scenarios(...)`.
- [ ] T017 [P] [US1] Author unit test `tests/katas/015_self_correction/unit/test_validator_resum.py` asserting `InvoiceExtraction` re-sums `line_items` into `calculated_total` regardless of any model-provided value (FR-002, FR-004). Covers `[TS-001]` at unit level.
- [ ] T018 [P] [US1] Author unit test `tests/katas/015_self_correction/unit/test_tolerance_is_logged.py` asserting `tolerance_cents` is persisted on the extraction record and surfaced in the calculation trace (FR-008). Covers `[TS-002]`.
- [ ] T019 [P] [US1] Author unit test `tests/katas/015_self_correction/unit/test_calculation_trace_shape.py` asserting `CalculationTrace` has one entry per line item with `amount` and `running_sum`, in document order (FR-007, SC-003). Covers `[TS-003]`.

### Implementation for User Story 1

- [ ] T020 [US1] Implement `build_extraction_tool() -> dict` and the raw-parse path in `katas/015_self_correction/extractor.py` that calls the Anthropic Messages API with a tool bound to `InvoiceExtraction.model_json_schema()` minus `conflict_detected` (the model never authors that field) and returns the parsed `InvoiceExtraction` (FR-001, FR-002).
- [ ] T021 [US1] Implement `compute_calculation_trace(line_items) -> CalculationTrace` in `katas/015_self_correction/validator.py` emitting one entry per line item with the running sum (FR-007).
- [ ] T022 [US1] Wire the `model_validator` from T009 to attach a `CalculationTrace` to each `InvoiceExtraction` at validation time so the trace travels with every record (FR-007, SC-003).
- [ ] T023 [US1] Implement step defs for `[TS-001]` (consistent invoice → `stated_total` equals literal, `calculated_total` equals sum, `conflict_detected=false`) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T024 [US1] Implement step defs for `[TS-002]` (rounding-only diff within tolerance → both totals verbatim, `conflict_detected=false`, tolerance persisted) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T025 [US1] Implement step defs for `[TS-003]` (successful extraction attaches per-line trace with one entry per line item and running sum) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T026 [US1] Implement step defs for `[TS-004]` (record validates against `contracts/invoice-extraction.schema.json` and carries `stated_total`, `calculated_total`, `conflict_detected`) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T027 [US1] Implement step defs for `[TS-005]` (Scenario Outline: `calculated_total` equals signed sum across `all positive amounts`, `mixed positive and credit amounts`, `duplicate identical line items`, `fractional-quantity amounts`; all with `conflict_detected=false`) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.

**Checkpoint**: US1 MVP complete. `pytest tests/katas/015_self_correction -v -k "US-001 or test_validator_resum or test_tolerance_is_logged or test_calculation_trace_shape"` passes against recorded fixtures. The dual-total emission and cross-audit happy path are demonstrable.

---

## Phase 4: User Story 2 — Conflicting Invoice Routes to Human Review (P2)

**Goal**: When line items sum to a value different from the stated total beyond tolerance, `conflict_detected=true` is set, both totals survive unchanged, the record is written to `runs/<session-id>/review-queue.jsonl`, and the downstream "clean" consumer never sees it.

**Independent Test**: Feed the `line_sum_mismatch.json` fixture; assert `conflict_detected=true`, the record appears in the review queue exactly once, both totals are preserved, and the clean-stream consumer does not receive the record.

### Tests for User Story 2

- [ ] T028 [P] [US2] Register the `conflicting_invoice_routes_to_review.feature` scenarios in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` via `pytest-bdd` `scenarios(...)`.
- [ ] T029 [P] [US2] Author unit test `tests/katas/015_self_correction/unit/test_review_queue_completeness.py` that runs the full fixture corpus and asserts set-equality between records whose `conflict_detected=true` and entries in `runs/<session-id>/review-queue.jsonl` — zero leakage either direction (FR-005, SC-004). Covers `[TS-009]`.
- [ ] T030 [P] [US2] Author unit test `tests/katas/015_self_correction/unit/test_conflict_detected_integrity.py` asserting that when a payload arrives with model-emitted `conflict_detected=false` while totals disagree beyond tolerance, pydantic raises `ValidationError` (FR-003, FR-004). Covers `[TS-016]` at unit level.

### Implementation for User Story 2

- [ ] T031 [US2] Implement append-only JSONL writer `append_review_entry(session_dir, entry)` in `katas/015_self_correction/review_queue.py` writing to `runs/<session-id>/review-queue.jsonl`, creating the directory if missing (FR-005).
- [ ] T032 [US2] Implement `record_extraction(extraction, session_dir)` in `katas/015_self_correction/review_queue.py` that always appends to `extractions.jsonl` and additionally routes conflicted records to the review queue via `ConflictRecord` + `ReviewQueueEntry`, blocking them from the downstream clean consumer (FR-005, SC-004).
- [ ] T033 [US2] Implement step defs for `[TS-006]` (line-sum mismatch beyond tolerance → `conflict_detected=true`, record appended to review queue, NOT returned to clean consumer) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T034 [US2] Implement step defs for `[TS-007]` (on conflict, both totals preserved unchanged; neither field replaced by the other) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T035 [US2] Implement step defs for `[TS-008]` (conflict record exposes full per-line calculation trace so a reviewer pinpoints the discrepancy without re-running extraction) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T036 [US2] Implement step defs for `[TS-009]` (corpus run with N flagged records → queue has exactly N entries matching flagged `invoice_ids`; zero leakage to clean stream) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T037 [US2] Implement step defs for `[TS-010]` (invoice with stated total but no line items → `conflict_detected=true`, `calculated_total` NOT silently coerced to zero, record routed to review queue) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` (FR-009).
- [ ] T038 [US2] Implement step defs for `[TS-011]` (Scenario Outline: defects `non-numeric amount "TBD"`, `non-numeric amount "see attached"`, `a currency different from the invoice`, `mixed currencies across line items` → `conflict_detected=true`, no silent zero-coercion, routed to review queue) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` (FR-009).
- [ ] T039 [US2] Implement step defs for `[TS-012]` (review queue entry validates against `contracts/review-queue-entry.schema.json` and its `conflict_record_id` resolves to a record validating against `contracts/conflict-record.schema.json`) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.

**Checkpoint**: US2 complete. Conflicts are detected mechanically, both totals survive, and the review queue is complete with zero leakage. `pytest tests/katas/015_self_correction -v -k "US-002 or test_review_queue_completeness or test_conflict_detected_integrity"` passes.

---

## Phase 5: User Story 3 — Neither Total Is Ever Silently Overwritten (P3)

**Goal**: Under every input condition (consistent, conflicting, rounding-only, degenerate, long, signed), `stated_total` and `calculated_total` travel as distinct fields through every sink; the model cannot forge `conflict_detected`; no assignment to either total appears outside the initial parser.

**Independent Test**: Replay the full fixture corpus end-to-end; assert for every record that both totals are distinct and match their respective truth sources; assert the AST lint blocks any new assignment to `stated_total` or `calculated_total` outside `extractor.py`; assert the `model_validator` rejects forged `conflict_detected=false`.

### Tests for User Story 3

- [ ] T040 [P] [US3] Register the `totals_never_silently_overwritten.feature` scenarios in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` via `pytest-bdd` `scenarios(...)`.
- [ ] T041 [P] [US3] Author AST-level lint `tests/katas/015_self_correction/lint/test_no_silent_overwrite.py` that walks the AST of every module under `katas/015_self_correction/` and fails if any `Assign` / `AugAssign` targets `.stated_total` or `.calculated_total` outside the initial parse function in `extractor.py` (FR-006, SC-002). Covers `[TS-017]`.
- [ ] T042 [P] [US3] Author lint `tests/katas/015_self_correction/lint/test_no_float_money.py` that walks `InvoiceExtraction`, `LineItem`, `ConflictRecord`, and `CalculationTrace` annotations and fails if any money field is typed as `float` (Research D-002/D-005 — Decimal discipline).
- [ ] T043 [P] [US3] Author unit test `tests/katas/015_self_correction/unit/test_sign_preservation.py` asserting credits / refunds / discounts retain their sign in `calculated_total` and are not flipped or dropped (FR-010). Covers `[TS-018]`.

### Implementation for User Story 3

- [ ] T044 [US3] Implement step defs for `[TS-013]` (every record in the replay corpus carries distinct `stated_total` and `calculated_total`; zero records have one field substituted by the other) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` (SC-002).
- [ ] T045 [US3] Implement step defs for `[TS-014]` (on conflict, both totals remain distinct in `extractions.jsonl` AND the review queue; no transformation rewrites one field to the other) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T046 [US3] Implement step defs for `[TS-015]` (consistent invoices still emit both fields as separate JSON fields even though they agree) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T047 [US3] Implement step defs for `[TS-016]` (model-emitted `conflict_detected=false` with disagreeing arithmetic → `ValidationError`; flag cannot be forged) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` (FR-003, FR-004).
- [ ] T048 [US3] Implement step defs for `[TS-017]` backed by the AST lint in T041 — reference the lint test and assert any new assignment to `stated_total` / `calculated_total` outside the parser blocks the build (FR-006, SC-002) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.
- [ ] T049 [US3] Implement step defs for `[TS-018]` (credit / refund / discount lines keep their sign in `calculated_total`; signs are NOT flipped or dropped) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` (FR-010).
- [ ] T050 [US3] Implement step defs for `[TS-019]` (`very_long_invoice.json` with ≥ 50 line items → calculation trace contains one entry per line; no summarized subset substitutes) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py` (FR-007).
- [ ] T051 [US3] Implement step defs for `[TS-020]` (persisted line items validate against `contracts/line-item.schema.json`; each line carries its extracted amount and contribution to the running sum) in `tests/katas/015_self_correction/step_defs/test_self_correction_steps.py`.

**Checkpoint**: US3 complete. All 20 `@TS-NNN` scenarios green; AST lint and Decimal-discipline lint are wired into the test run; the kata passes end-to-end against recorded fixtures.

---

## Final Phase: Polish & Cross-Cutting Concerns

### Runner & CLI

- [ ] T052 Implement CLI entrypoint in `katas/015_self_correction/runner.py` exposing `python -m katas.015_self_correction.runner --input <path> --out runs/<session-id>/`, driving extraction → validation → audit log + review queue routing per `quickstart.md`.

### Documentation (Principle VIII — Mandatory)

- [ ] T053 [P] Author `katas/015_self_correction/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — numeric self-audit, dual-total emission, independent recomputation in pydantic `model_validator`, mechanical conflict flag, single-pass cross-audit (no infinite loops), review-queue routing, AST silent-overwrite gate, pydantic forgery gate — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (`models` → `extractor` → `validator` → `review_queue` → `client` → `runner`) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — dual-total-cross-audit, validator-over-prose-check, single-pass-bounded-retry, escalate-not-retry on conflict — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (II Schema-First, V Test-First, VI Human-in-the-Loop, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — retry budget (single-pass cross-audit — conflicts are escalated to human review, never retried silently); divergence detection mechanism (`abs(stated_total - calculated_total) > tolerance_cents/100` computed inside the pydantic `model_validator`, not on prose) (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T055 [P] Add module-level docstrings to `katas/015_self_correction/models.py`, `extractor.py`, `validator.py`, `review_queue.py`, `client.py`, and `runner.py` explaining each file's role in the self-correction loop (schema source-of-truth, raw parse seam, re-sum + forgery gate, append-only review sink, recorded client, CLI orchestration).
- [ ] T056 [P] Add *why*-comments on `build_extraction_tool`, the `InvoiceExtraction` `model_validator`, `compute_calculation_trace`, `append_review_entry`, `record_extraction`, and the AST lint walker — each tying to its FR-XXX / SC-XXX anchor and to Principle VII (Provenance & Self-Audit) / Principle VIII (Mandatory Documentation).
- [ ] T057 [P] Verify `specs/015-self-correction/quickstart.md` — confirm every section (Install, recorded run, LIVE_API corpus run, scenario → spec mapping table, Kata Completion Standards checklist) matches the implemented layout and fixture filenames.
- [ ] T058 Run quickstart validation: execute `pytest tests/katas/015_self_correction -v` from repo root and confirm every `@TS-NNN` scenario, unit test, and lint test passes; capture output.

### Standard Polish

- [ ] T059 [P] Confirm `katas/015_self_correction/` has no imports outside `anthropic`, `pydantic`, `decimal`, `datetime`, `uuid`, `json`, `pathlib`, stdlib (no extraneous deps per `plan.md` Complexity Tracking).
- [ ] T060 [P] Run `ruff check katas/015_self_correction tests/katas/015_self_correction` and fix any findings.
- [ ] T061 [P] Run `mypy katas/015_self_correction` (if mypy is configured in `pyproject.toml`) and fix any findings; `Decimal` annotations and the `conflict_detected` derivation must type-check cleanly.
- [ ] T062 Regenerate the dashboard: `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` (per project rule `dashboard-refresh`).

---

## Dependencies & Execution Order

- **Setup (T001–T005)** must complete before Foundational.
- **Foundational (T006–T015)** blocks every user-story phase. `T006`→`T007`→`T008`→`T009`→`T010`→`T011` are sequential (same file, `models.py`). `T012`, `T013`, `T014`, `T015` may run in parallel with each other once `T006–T011` are done.
- **US1 (T016–T027)** depends on Foundational only.
- **US2 (T028–T039)** depends on Foundational and reuses the extractor + validator from US1 (`T020`, `T022`).
- **US3 (T040–T051)** depends on Foundational, the `model_validator` from `T009`, the extractor seam from `T020`, and the review queue writer from `T031`.
- **Polish (T052–T062)** runs last. `T058` depends on every test having been authored.

## Parallel Opportunities

- `[P]` markers above. Notably:
  - T004 and T005 in Setup.
  - T012, T013, T014, T015 in Foundational (after models are in place).
  - T016, T017, T018, T019 in US1 tests.
  - T028, T029, T030 in US2 tests (different files).
  - T040, T041, T042, T043 in US3 tests (different files).
  - T053, T055, T056, T057, T059, T060, T061 in the final Polish phase.
- Within a story, step-def tasks (T023–T027, T033–T039, T044–T051) all write to the same file (`test_self_correction_steps.py`) and are therefore **sequential**, not parallel.

## Implementation Strategy (MVP)

1. Land Setup + Foundational (T001–T015). `.feature` files are copied verbatim and lock the assertion integrity anchor; the `model_validator` forgery gate lands in T009.
2. Land US1 (T016–T027) for the P1 MVP slice: dual-total emission + independent recomputation + calculation trace on the happy path. This is the earliest demoable point.
3. Land US2 (T028–T039) to close the silent-trust anti-pattern: mechanical conflict detection, review-queue routing, clean-stream blocking, and schema conformance for queue entries.
4. Land US3 (T040–T051) to close the silent-overwrite anti-pattern: AST lint, Decimal discipline, sign preservation, and long-invoice full-trace guarantees.
5. Polish (T052–T062): CLI, documentation (Principle VIII), quickstart validation, dashboard refresh.

## Notes

- Every `@TS-NNN` scenario in `tests/features/*.feature` has at least one implementation task citing its TS ID; see T023–T027 (US1: TS-001..TS-005), T033–T039 (US2: TS-006..TS-012), T044–T051 (US3: TS-013..TS-020).
- Traceability uses individual IDs (`[TS-006]`, `[TS-009]`), never ranges — per the rule at the top of this file.
- `.feature` files are treated as read-only per `assertion-integrity.md`. If requirements change, re-run `/iikit-04-testify`; do not edit scenarios by hand.
- The kata performs exactly ONE cross-audit pass per invoice — no retry loops on the extraction, no silent pass on disagreement. Conflicts escalate to human review; retries are explicitly out of scope per `plan.md` Complexity Tracking.
- ALL money fields MUST be `Decimal`. The `test_no_float_money.py` lint (T042) is the enforcement seam.
- Recorded-response mode is the default (`LIVE_API` unset). CI never calls the live API.
