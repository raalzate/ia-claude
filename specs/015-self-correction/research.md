# Phase 0 Research: Critical Evaluation & Self-Correction

## Decisions

### D-001 — Use the official `anthropic` Python SDK for extraction

- **Decision**: Call `anthropic.Anthropic().messages.create(...)` with a
  structured-output tool schema whose parameters mirror `InvoiceExtraction`
  (minus `conflict_detected`). The model returns line items + a stated total;
  our code alone sets the flag.
- **Rationale**: The kata's point is that the model MUST NOT be trusted to
  self-report whether its own sum matches the stated total. Using the SDK
  with a structured tool call gives us typed content blocks to feed into
  pydantic, but the conflict decision is locally computed.
- **Alternatives considered**:
  - *Ask the model "is there a conflict?" in prose and grep the answer.*
    Rejected — direct violation of Principle I and the entire kata premise.
  - *Trust the model to set `conflict_detected` itself.* Rejected — that is
    the anti-pattern FR-003's integrity gate is designed to forbid.

### D-002 — `decimal.Decimal` for every money amount

- **Decision**: `LineItem.amount`, `InvoiceExtraction.stated_total`,
  `InvoiceExtraction.calculated_total`, and `InvoiceExtraction.tolerance_cents`
  are all `Decimal` (tolerance expressed as integer cents but carried as
  `Decimal` internally for comparison). JSON contracts serialize `Decimal`
  as **string**, not number, so replay from the event log does not re-enter
  floating-point representation.
- **Rationale**: Money is the canonical anti-float domain. A 0.01 rounding
  drift silently creating or masking a conflict would defeat both SC-001 and
  SC-002. `Decimal` gives exact arithmetic; pydantic v2 handles it natively.
- **Alternatives considered**:
  - *`float`.* Rejected — binary floats cannot exactly represent most
    decimal cent values; the rounding-only-diff fixture would become flaky.
  - *Integer cents only.* Rejected for ergonomics: sources often quote three
    decimal places (tax lines); keeping `Decimal` preserves precision while
    allowing `tolerance_cents` to be the human-facing control knob.

### D-003 — Tolerance is a declared, persisted integer-cents value

- **Decision**: `InvoiceExtraction.tolerance_cents: int = 1` (one cent) is the
  default. It is emitted on every extraction record (FR-008) and compared as
  `abs(stated_total - calculated_total) > (tolerance_cents / Decimal(100))`.
- **Rationale**: Rounding drift across many line items on sub-cent tax
  amounts is legitimate; transcription errors are not. One cent is the
  minimum credible operational tolerance for real invoices and keeps the
  rounding-only-diff fixture from tripping a false positive (Edge:
  rounding-only discrepancies). The value is DECLARED and LOGGED so an
  auditor can reconstruct exactly which threshold flagged or cleared a
  record.
- **Alternatives considered**:
  - *No tolerance (exact equality).* Rejected — real invoices with N sub-cent
    tax lines routinely exhibit sub-cent rounding drift; zero tolerance would
    mass-flag legitimate documents and drown the review queue.
  - *Percentage tolerance (e.g. 0.01%).* Rejected — percentage tolerance
    scales with invoice magnitude, which means small invoices get a tolerance
    narrower than their own rounding unit. Absolute-cents is correct here.

### D-004 — Append-only JSONL review queue, separate from extractions log

- **Decision**: Every extraction is appended to
  `runs/<session-id>/extractions.jsonl`. Every extraction where
  `conflict_detected=true` is ALSO appended to
  `runs/<session-id>/review-queue.jsonl` as a `ReviewTask` record (itself a
  schema-validated pydantic model). A completeness test asserts set-equality
  between flagged extractions and queue entries (SC-004).
- **Rationale**: Two files rather than one flagged field because SC-004 is
  about **routing**, not just labelling. A separate queue file lets
  downstream "clean" consumers read `extractions.jsonl` WHERE
  `conflict_detected=false` and NEVER accidentally open the queue; the
  reviewer tool reads only `review-queue.jsonl`. Both files are append-only
  JSONL so replay and completeness checks are trivial.
- **Alternatives considered**:
  - *Single log with `is_conflict` column.* Rejected — puts the responsibility
    for filtering on every downstream reader; one buggy reader leaks a
    flagged record into "clean" consumption, violating FR-005.
  - *SQLite / external queue (Redis etc.).* Rejected — infra overhead for a
    kata; JSONL is inspectable with `jq` and grep.

### D-005 — AST gates for silent-overwrite and float-money

- **Decision**: Two lint tests parse the kata source with the stdlib `ast`
  module and fail the build on either of:
  1. Any `Assign` or `AugAssign` whose target is `stated_total` or
     `calculated_total` attribute access, occurring outside the single
     designated parse function in `extractor.py` (FR-006, SC-002).
  2. Any literal or annotation referencing `float` on a money-bearing field
     in `models.py` (Research D-002).
- **Rationale**: Principle I demands machine-checkable defenses; "remember not
  to overwrite the totals" is exactly the maintenance-drift surface that
  silently re-emerges during refactors. An AST lint fails closed the first
  time someone re-introduces the anti-pattern, teaching SC-002 at CI level.
- **Alternatives considered**:
  - *Code review only.* Rejected — drift is inevitable on a teaching repo
    across 20 katas; the whole point of the kata is the automated gate.
  - *Ruff/Flake8 custom rule.* Deferred — the `ast` test is enough for MVP
    and stays self-contained in the tests tree.

### D-006 — Post-extraction pydantic validator is the integrity author

- **Decision**: `InvoiceExtraction` defines a
  `model_validator(mode="after")` that (a) re-sums `line_items` into
  `calculated_total`, (b) compares `|stated_total - calculated_total|`
  against `tolerance`, and (c) sets `conflict_detected` from that comparison.
  If the incoming payload claims `conflict_detected=False` while the totals
  disagree beyond tolerance, the validator raises `ValidationError`.
- **Rationale**: FR-003 / FR-004 must be enforced at the schema boundary,
  not by polite convention. Making the flag computed-not-accepted closes the
  "model said everything's fine" failure mode. A failing `ValidationError`
  is the loud failure Principle II demands.
- **Alternatives considered**:
  - *Compute the flag in a post-processing step outside the model.* Rejected
    — nothing would stop a caller from constructing the model with a
    self-reported flag and bypassing the check. Keeping it on the model
    means every path that materializes an `InvoiceExtraction` is covered.

### D-007 — Recorded fixtures over live API for tests

- **Decision**: Fixtures under `tests/katas/015_self_correction/fixtures/`
  (consistent-invoice, line-sum-mismatch, missing-line-items,
  non-numeric-amounts, currency-mismatch, rounding-only-diff,
  very-long-invoice) are fed through a `RecordedClient`. Live SDK calls are
  gated by `LIVE_API=1` and excluded from the default test run.
- **Rationale**: Determinism and offline reproducibility of a numeric-audit
  kata. The tests verify the CONTRACT (dual totals, flag, queue routing,
  trace), not model quality. A fixture is the correct artefact.
- **Alternatives considered**:
  - *Always call the live API.* Rejected — flaky CI, API quota burn, and
    non-determinism on a kata whose whole point is deterministic audit.

### D-008 — One source_page_ref per line item for provenance

- **Decision**: `LineItem.source_page_ref: str` is required. The
  `CalculationTrace` persists each line item's amount, source page, and
  running sum at that step.
- **Rationale**: Principle VII demands factual claims preserve a machine-
  readable source link. For a human reviewer, "the sum doesn't match"
  without per-line-item page references is useless; SC-003 specifically
  requires the reviewer locate the discrepancy WITHOUT re-running the
  extraction.
- **Alternatives considered**:
  - *One page ref for the whole invoice.* Rejected — defeats SC-003 on any
    multi-page invoice.

## Tessl Tiles

`tessl search invoice-extraction` and `tessl search numeric-self-audit` (run
2026-04-23) returned no tiles targeting pydantic-validated numeric
reconciliation or structured-extraction cross-audit. Closest hits were
unrelated accounting domain skills. **No tiles installed for this feature.**

Follow-up: if a community tile for pydantic `Decimal` money patterns or
Anthropic structured-output-with-validation appears later, revisit at
`/iikit-07-implement` time. No eval scores recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION from the spec (there were 0) is resolved by
the decisions above. Open design questions (e.g. multi-currency conversion,
reviewer assignment policy) are explicitly out of scope per plan's
Complexity Tracking.
