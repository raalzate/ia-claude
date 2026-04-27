# Implementation Plan: Critical Evaluation & Self-Correction

**Branch**: `015-self-correction` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/015-self-correction/spec.md`

## Summary

Build an invoice-extraction kata that forces the model to cross-audit its own
arithmetic. Every extraction output carries BOTH a `stated_total` (the literal
figure read from the document) AND a `calculated_total` (the independent sum
of parsed line items); a post-extraction validator re-computes the sum inside
the pydantic model, compares it against `stated_total` under a declared
`tolerance_cents`, and sets `conflict_detected` mechanically. Any record with
`conflict_detected=true` is routed to `runs/<session-id>/review-queue.jsonl`
and is BLOCKED from the downstream "clean" path. A schema invariant plus an
AST-level silent-overwrite gate guarantee that neither total is ever replaced
by the other after the initial parse. Delivered under Constitution v1.3.0,
Principles II (Schema-Enforced Boundaries, NN), VII (Provenance & Self-Audit),
and VIII (Mandatory Documentation, NN).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — sole structured-extraction surface
  (Messages API with tool/JSON-schema output).
- `pydantic` v2 — schema enforcement for `LineItem`, `InvoiceExtraction`,
  `ConflictRecord`, `ReviewTask`. Post-validator re-sums line items and sets
  `conflict_detected` mechanically (Principle II).
- `decimal.Decimal` (stdlib) — every money amount. Rationale captured in
  Research D-002 and Research D-003; pydantic v2 serializes `Decimal` as
  string in the JSON contracts to avoid float re-entry on replay.
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).
**Storage**: Local filesystem only. Two append-only JSONL streams per run:
`runs/<session-id>/extractions.jsonl` (every extraction, clean or conflicted)
and `runs/<session-id>/review-queue.jsonl` (conflicts only; SC-004). The
per-line-item `CalculationTrace` is embedded on the extraction record so
audit replay needs only the extraction file (FR-007).
**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit + lint. Fixtures under `tests/katas/015_self_correction/fixtures/` feed
a `RecordedClient` so the default run is offline and deterministic; live SDK
calls are gated by `LIVE_API=1`.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.
**Project Type**: Single project — kata module at
`katas/015_self_correction/` with tests at `tests/katas/015_self_correction/`.
**Performance Goals**: Not latency-bound. The long-invoice fixture
(≥ 50 line items) must complete its full line-item walk under 5 s locally
against the recorded client (FR-007, Edge "Very long invoices").
**Constraints**:
- ALL money fields MUST be `Decimal`. Any `float` in a money path is a lint
  failure (see Research D-005).
- `conflict_detected` MUST NOT be writable by the model. It is computed by a
  pydantic `model_validator(mode="after")` and any attempt to set it to
  `False` while `abs(stated_total - calculated_total) > tolerance` must
  raise `ValidationError` (FR-003, FR-004, integrity gate).
- NO assignment to `extraction.stated_total` or `extraction.calculated_total`
  is permitted anywhere outside the initial parse function. Enforced by an
  AST lint test (see Research D-005) — this is the silent-overwrite gate
  covering FR-006 and SC-002.
- Every conflicted record MUST appear in the review-queue file; a test walks
  the corpus and asserts set-equality between flagged records and queue
  entries (SC-004, FR-005).
**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test
code; one README; fixture corpus ≤ 10 recorded invoices covering
consistent, line-sum-mismatch, missing-line-items, non-numeric-amounts,
currency-mismatch, rounding-only-diff, and very-long-invoice shapes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | `conflict_detected` is computed from the numeric comparison of two `Decimal` fields — never inferred from the model's prose. No regex-on-prose appears in the conflict path. |
| II. Schema-Enforced Boundaries (NN) | `LineItem`, `InvoiceExtraction`, `ConflictRecord`, `ReviewTask` are pydantic v2 models with `Decimal` money fields. The post-extraction validator re-sums line items and rejects any attempt by the model to assert `conflict_detected=False` while totals disagree beyond tolerance (FR-003 integrity check). |
| III. Context Economy | Not load-bearing here. Calculation trace is kept structured (one JSON object per line) rather than rephrased prose, so logs stay compact for long invoices. |
| IV. Subagent Isolation | Not applicable — one extraction pass per invoice; no subagent. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` will run before any production code. `tasks.md` will reference test IDs produced by testify. Each fixture corresponds to a scenario table entry in `quickstart.md`. |
| VI. Human-in-the-Loop | The review queue IS the escalation target. No conflict is auto-resolved; no conflict is silently downgraded. |
| VII. Provenance & Self-Audit | Every line item carries a `source_page_ref`; the per-line-item calculation trace is persisted on every extraction (FR-007). Dual-total emission with conflict flag is a direct instance of the "numeric output cross-checked against any stated value in source" clause. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function carries a *why* comment tied to the kata objective (dual-total audit, silent-overwrite defense). A single `notebook.ipynb` produced at `/iikit-07-implement` is the Principle VIII deliverable: it explains the kata, results, every Claude architecture concept exercised, the architecture walkthrough, applied patterns + principles, practitioner recommendations, the contract details, run cells, and the reflection. No separate README.md. |

**Result:** PASS. Proceed to Phase 0 research (see [`research.md`](./research.md)).

## Project Structure

### Documentation (this feature)

```text
specs/015-self-correction/
  plan.md              # this file
  research.md          # Phase 0 (decisions D-001..N incl. Decimal + tolerance)
  data-model.md        # Phase 1 (LineItem, InvoiceExtraction, TotalsPair, ConflictFlag, ReviewTask, CalculationTrace)
  quickstart.md        # Phase 1 (install, fixture run, scenario→spec map, Kata Completion Standards checklist)
  contracts/           # Phase 1 (JSON schemas, $id kata-015)
    line-item.schema.json
    invoice-extraction.schema.json
    conflict-record.schema.json
    review-queue-entry.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # Phase 1 output of /iikit-03-checklist
  # (kata narrative lives in katas/.../notebook.ipynb — no spec-side README)
```

### Source Code (repository root)

```text
katas/
  015_self_correction/
    __init__.py
    models.py          # pydantic v2: LineItem, InvoiceExtraction, ConflictRecord, ReviewTask, CalculationTrace
    extractor.py       # calls Anthropic Messages API; returns raw parse; DOES NOT set conflict_detected
    validator.py       # pydantic post-validator: re-sums line items, compares under tolerance, sets conflict_detected
    review_queue.py    # append-only JSONL writer for conflicts (runs/<session-id>/review-queue.jsonl)
    client.py          # thin injectable Anthropic client wrapper (RecordedClient for offline tests)
    runner.py          # CLI entrypoint: `python -m katas.015_self_correction.runner`
    notebook.ipynb       # Principle VIII deliverable — kata narrative + Claude architecture certification concepts (written during /iikit-07)

tests/
  katas/
    015_self_correction/
      conftest.py      # fixture loader, tolerance default, RecordedClient wiring
      features/        # Gherkin files produced by /iikit-04-testify
        self_correction.feature
      step_defs/
        test_self_correction_steps.py
      unit/
        test_validator_resum.py             # FR-002, FR-004
        test_conflict_detected_integrity.py # FR-003 (model cannot lie about flag)
        test_review_queue_completeness.py   # FR-005, SC-004
        test_calculation_trace_shape.py     # FR-007, SC-003
        test_tolerance_is_logged.py         # FR-008
        test_sign_preservation.py           # FR-010
      lint/
        test_no_silent_overwrite.py         # FR-006, SC-002: AST — no assignment to stated_total / calculated_total outside initial parse
        test_no_float_money.py              # Decimal discipline (Research D-002)
      fixtures/
        consistent_invoice.json             # US1 happy path
        line_sum_mismatch.json              # US2 core anti-pattern
        missing_line_items.json             # Edge: cannot populate calculated_total
        non_numeric_amounts.json            # Edge: "TBD" / "see attached"
        currency_mismatch.json              # Edge: mixed currencies
        rounding_only_diff.json             # within tolerance → NO conflict
        very_long_invoice.json              # ≥ 50 line items
```

**Structure Decision**: Single-project layout consistent with Kata 1
(`katas/NNN_<slug>/` + mirrored `tests/katas/NNN_<slug>/`). Runs land in
`runs/<session-id>/` (gitignored). Separating `extractor.py` (parse only)
from `validator.py` (re-sum + flag) is deliberate: it is the seam the
AST silent-overwrite lint rides on. Only `extractor.py` is allowed to
assign `stated_total` or `calculated_total`.

## Architecture

```
┌────────────────────┐
│ Extraction Runner  │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│   Invoice Parser   │───────│Integrity Validator │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Messages API  │ │  Review Queue  │ │Invoice Audit L…│
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Extraction Runner` is the kata entry point; `Invoice Parser` owns the core control flow
for this kata's objective; `Integrity Validator` is the primary collaborator/policy reference;
`Messages API`, `Review Queue`, and `Invoice Audit Log` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified.**

_No violations._ Intentionally out of scope: OCR, PDF rendering,
multi-currency conversion, ML-based line-item segmentation, automatic
reviewer assignment, retry budgets on extraction, multi-pass self-critique
beyond the arithmetic cross-audit. None are required by the spec and each
would dilute the kata's single teaching point (numeric self-audit).
