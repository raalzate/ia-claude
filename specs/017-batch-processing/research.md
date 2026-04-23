# Phase 0 Research: Mass Processing with Messages Batch API

## Decisions

### D-001 — Classifier thresholds

- **Decision**: `WorkloadClassifier` emits `batchable` iff ALL: `is_blocking ==
  False` AND `latency_budget_seconds >= 86400` AND `item_count >= 50` AND
  `expected_cost_usd >= 0.50`. Otherwise `synchronous`. Thresholds are a
  `ClassifierPolicy` pydantic model — adjustable, NOT hardcoded.
- **Rationale**: Anthropic batch API has a ~24h SLA; below 50 items / <$0.50
  the overhead of batch management dominates savings. Thresholds must be
  explicit and auditable (FR-001).
- **Alternatives**: Machine-learned classifier — rejected (opaque; kata's
  point is explicit rules).

### D-002 — custom_id is the correlation anchor

- **Decision**: `BatchedItem.custom_id` MUST be a URL-safe non-empty string,
  unique within a job. Pydantic validator enforces uniqueness pre-submit.
- **Rationale**: FR-003 + SC-003 (100% correlation). Duplicate custom_ids
  silently shadow each other on retrieval — the kata's defense is pre-submit
  rejection.
- **Alternatives**: Server-generated ids + client mapping table — rejected
  (needs extra state; defeats batch simplicity).

### D-003 — Failure-bucket fragmentation strategy

- **Decision**: On `errored | expired` items, the `FailureBucket` splits the
  failed set in half and resubmits each half as a child batch. Up to
  `MAX_FRAGMENTATION_ROUNDS = 4` (documented). Items still failing after the
  cap are tagged `permanently_failed` and surfaced to the caller.
- **Rationale**: Simple, deterministic; halving is empirically enough for
  most context-window / rate-limit failures. Bounded attempts avoid infinite
  loops (SC-004).

### D-004 — Cost baseline calibration corpus

- **Decision**: `tests/katas/017_batch_processing/fixtures/calibration_corpus.json`
  contains 100 recorded synchronous requests with their token usage. The
  harness computes expected synchronous cost from these plus the batch cost
  (50% list discount + batch processing fee model) and asserts reduction
  ≥ 50% on this corpus (SC-001). The corpus is frozen to keep the SC-001
  assertion stable across model-price changes.
- **Rationale**: Pricing drifts; freezing the baseline keeps the pedagogy
  valid. Research note instructs re-freezing when pricing table changes
  materially.

### D-005 — Retrieve via polling, not webhooks

- **Decision**: Use `client.messages.batches.retrieve(id)` in a bounded-backoff
  loop (1 min → 5 min → 15 min), capped at the job's declared window. No
  webhook listener.
- **Rationale**: Workshop simplicity; webhooks require a public endpoint.
- **Alternatives**: Webhook — deferred.

### D-006 — Results stream consumed once, not replayed

- **Decision**: `client.messages.batches.results(id)` is iterated exactly
  once; each `BatchedResult` is persisted to
  `runs/<job-id>/results/<custom_id>.json` for replay. Re-consuming the
  stream is forbidden (SDK contract). Tests assert persistence is complete
  by checking: `ls results/ | wc -l == len(submitted custom_ids)`.
- **Rationale**: Persisting once + reading local copies afterwards is
  simpler than re-fetching and avoids SDK gotchas.

## Tessl Tiles

`tessl search batch` — no applicable tile. None installed.

## Unknowns

None. Pricing assumption in D-004 documented as review trigger.
