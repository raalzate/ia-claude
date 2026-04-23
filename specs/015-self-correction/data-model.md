# Phase 1 Data Model: Critical Evaluation & Self-Correction

All entities implemented as pydantic v2 models at
`katas/015_self_correction/models.py`. Monetary amounts use `Decimal` to avoid
floating-point drift — rationale in research.md.

## LineItem

One row in an invoice.

| Field | Type | Notes |
|-------|------|-------|
| `sku` | `str \| None` | Not always present; null-tolerant per Principle II. |
| `description` | `str` | Required. |
| `quantity` | `Decimal` (≥ 0) | Supports fractional quantities (e.g. 1.5 kg). |
| `unit_price` | `Decimal` (≥ 0) | |
| `line_total` | `Decimal` | MUST equal `quantity * unit_price` within 1-cent tolerance; validator enforces. |
| `source_page` | `int \| None` | Audit trail for FR-005. |

## InvoiceExtraction

The top-level extraction artifact. Holds both stated and calculated totals.

| Field | Type | Notes |
|-------|------|-------|
| `invoice_id` | `str` | |
| `currency` | `str` (ISO 4217) | Captured once; line items must match. |
| `stated_total` | `Decimal` | Literal total from the document (FR-001). |
| `calculated_total` | `Decimal` | Sum of `line_items[*].line_total`, computed in a `model_validator`. NOT provided by the model — always derived. |
| `line_items` | `list[LineItem]` | At least one required. |
| `tolerance_cents` | `int` (default 1) | Delta under which totals are treated as equal. |
| `conflict_detected` | `bool` | Derived — NEVER trusted from model output. |

**Critical invariants**
- A `model_validator` recomputes `calculated_total` from `line_items` and sets
  `conflict_detected = abs(stated_total - calculated_total) > tolerance`.
- If the model's emitted JSON sets `conflict_detected=false` while the derived
  value is `true`, pydantic raises `IntegrityViolation` — FR-003.
- Neither `stated_total` nor `calculated_total` is reassigned after initial
  validation — an AST test asserts no assignment to those fields anywhere
  outside the initial parser (FR-004, SC-002).

## TotalsPair (view helper, not serialized)

A small dataclass-style pair `(stated, calculated)` used by the `ReviewQueue`
rendering — makes audit diffs legible.

## ConflictRecord

Persisted per invoice where `conflict_detected=true`.

| Field | Type | Notes |
|-------|------|-------|
| `record_id` | `str` (UUID4) | |
| `invoice_id` | `str` | FK. |
| `stated_total` | `Decimal` | Frozen at detection. |
| `calculated_total` | `Decimal` | Frozen at detection. |
| `delta` | `Decimal` | Signed (stated - calculated). |
| `line_items_snapshot` | `list[LineItem]` | For human review without re-running extraction. |
| `detected_at` | `datetime` | UTC. |

## ReviewQueueEntry

A handoff to a human reviewer, persisted JSONL-style.

| Field | Type | Notes |
|-------|------|-------|
| `entry_id` | `str` (UUID4) | |
| `conflict_record_id` | `str` | FK. |
| `priority` | `Literal["low", "medium", "high"]` | Heuristic: delta magnitude buckets. |
| `status` | `Literal["pending", "in_review", "resolved"]` | |
| `resolution_note` | `str \| None` | Filled when status=resolved. |

## Relationships

```
InvoiceExtraction
  ├── LineItem (1..N)
  └── ConflictRecord (0..1 — exists iff conflict_detected=true)
        └── ReviewQueueEntry (1..1 — emitted for every ConflictRecord)
```

**Why this shape**: `conflict_detected` is a derived property — by making it
un-forgeable (raises on model-emitted mismatch) we operationalize the kata's
core principle: the self-correction step has teeth, not intent.
