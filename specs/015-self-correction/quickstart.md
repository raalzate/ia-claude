# Kata 15 — Quickstart

## What you'll build

An invoice-extraction pipeline that forces the model to emit BOTH a literal
`stated_total` and a derived `calculated_total` (summed by a pydantic
validator, not by the model). When they disagree beyond 1-cent tolerance,
`conflict_detected=true` is set automatically and the record is written to a
human-review queue. The model CANNOT forge `conflict_detected=false` — the
validator raises if it tries.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/015_self_correction -v
```

Asserts:
- consistent-invoice → `conflict_detected=false`, empty review queue.
- mismatch-invoice → `conflict_detected=true`, one `ReviewQueueEntry` with
  matching `conflict_record_id`.
- forged-consistency attempt (model emits `conflict_detected=false` when totals
  disagree) → pydantic `IntegrityViolation`.
- No assignment to `stated_total` or `calculated_total` outside the parser —
  AST-lint test (FR-004, SC-002).
- Rounding-only delta (within tolerance) → no conflict.

## Run against a PDF/text corpus

```bash
LIVE_API=1 python -m katas.015_self_correction.extract \
  --input tests/katas/015_self_correction/fixtures/invoices/ \
  --out runs/$(uuidgen)/extractions/
```

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Consistent totals, no conflict | US1, SC-001 | `consistent_invoice.txt` |
| Line-sum mismatch raises conflict | US2, SC-002 | `line_sum_mismatch.txt` |
| No silent overwrite of either total | US3, FR-004 | AST lint |
| Missing line items halt | Edge #1 | `missing_line_items.txt` |
| Currency mismatch across items | Edge #3 | `currency_mismatch.txt` |
| Rounding-only delta ignored | Edge #4 | `rounding_only.txt` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Silent-trust anti-pattern defended by integrity validator + AST lint.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- Did the integrity validator ever flag a genuine rounding-only discrepancy
  that the tolerance couldn't absorb? What did you learn about the tolerance?
- Where else in an extraction pipeline would you apply the same
  "derive, don't trust" pattern?
