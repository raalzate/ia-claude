# Phase 1 Data Model: Mass Processing with Messages Batch API

Pydantic v2 models at `katas/017_batch_processing/models.py`.

## WorkloadProfile

Input to `WorkloadClassifier`.

| Field | Type | Notes |
|-------|------|-------|
| `is_blocking` | `bool` | True → user-facing → NEVER batchable. |
| `latency_budget_seconds` | `int` (≥ 0) | Async tolerance window. |
| `item_count` | `int` (≥ 1) | Total items to process. |
| `expected_cost_usd` | `Decimal` | Back-of-envelope sync cost. |

Emits: `Literal["batchable", "synchronous"]`.

## BatchedItem

One item in a batch.

| Field | Type | Notes |
|-------|------|-------|
| `custom_id` | `str` (pattern URL-safe, length 1–128) | Unique within a `BatchJob`. Pydantic root-validator enforces uniqueness. |
| `request` | `dict[str, Any]` | `MessageCreateParams`-compatible; validated against Anthropic's batch request schema. |

## BatchJob

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | `str` | Anthropic's batch id after submission; pre-submit this is `None` or a local UUID4 draft id. |
| `items` | `list[BatchedItem]` (minlen 1) | Uniqueness enforced across custom_ids. |
| `submitted_at` | `datetime \| None` | None pre-submit. |
| `processing_status` | `Literal["draft", "in_progress", "ended", "canceled"] \| None` | Mirrors SDK `processing_status`. |

## BatchedResult

| Field | Type | Notes |
|-------|------|-------|
| `custom_id` | `str` | Correlates back to `BatchedItem`. |
| `result_type` | `Literal["succeeded", "errored", "expired", "canceled"]` | Mirrors SDK result envelope. |
| `response` | `dict \| None` | Present iff `result_type == "succeeded"`. |
| `error_code` | `str \| None` | Present iff non-success. |
| `error_message` | `str \| None` | Present iff non-success. |

**Invariant**: `result_type == "succeeded"` ↔ `response is not None`. Validator enforces.

## ResponseMapping

| Field | Type | Notes |
|-------|------|-------|
| `by_custom_id` | `dict[str, BatchedResult]` | 100% coverage — missing ids raise `MissingResultError`. |
| `missing` | `list[str]` | Sanity — should always be empty in success. |
| `errored` | `list[str]` | Subset routed to FailureBucket. |

## FailureBucket

| Field | Type | Notes |
|-------|------|-------|
| `round` | `int` (≥ 1) | 1 = first reprocess round. |
| `items` | `list[BatchedItem]` | Failed items to retry. |
| `parent_job_id` | `str` | Originating job. |
| `max_rounds` | `int` (default 4) | Cap (research D-003). |

Terminal state for items still failing after `max_rounds` = `permanently_failed`.

## CostReport

| Field | Type | Notes |
|-------|------|-------|
| `calibration_corpus_id` | `str` | Pinned corpus (research D-004). |
| `sync_cost_usd` | `Decimal` | Computed from recorded usage. |
| `batch_cost_usd` | `Decimal` | Observed batch cost. |
| `reduction_pct` | `Decimal` | `(sync - batch) / sync`. |

**Assertion**: `reduction_pct >= 0.50` on the frozen corpus (SC-001).

## Relationships

```
WorkloadProfile → verdict
BatchJob
  ├── BatchedItem (1..N, unique custom_ids)
  └── BatchedResult (1..N, covered by ResponseMapping)
        → FailureBucket (only errored/expired)
```
