# Kata 17 — Quickstart

## What you'll build

A `WorkloadClassifier` that decides sync vs. batch by declared thresholds; a
`BatchJob` that guarantees unique `custom_id`s; a `ResponseMapper` that fails
loud on orphans; a `FailureBucket` that fragments + retries bounded rounds;
a cost-delta harness proving ≥50% savings on the frozen calibration corpus.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/017_batch_processing -v
```

Asserts:
- Classifier verdicts for each fixture profile.
- Duplicate custom_id rejected pre-submit.
- ResponseMapper raises `MissingResultError` on orphan.
- FailureBucket converges within `MAX_FRAGMENTATION_ROUNDS=4` or surfaces
  `permanently_failed` items.
- Cost harness on calibration_corpus.json reports ≥50% reduction.

## Run a dry batch submission

```bash
LIVE_API=1 python -m katas.017_batch_processing.submit \
  --corpus tests/katas/017_batch_processing/fixtures/small_corpus.json \
  --dry-run
```

Skips the actual API call; prints the planned batch shape + unique-id report.

## Run a tiny real batch

```bash
LIVE_API=1 python -m katas.017_batch_processing.submit \
  --corpus tests/katas/017_batch_processing/fixtures/tiny_live_corpus.json
```

Polls with backoff; persists each `BatchedResult` to
`runs/<job-id>/results/<custom_id>.json`.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Batch path cheaper | US1, SC-001 | `calibration_corpus.json` |
| All items succeed | US1, FR-003 | `all_succeed.json` |
| Duplicate custom_id rejected | Edge #3 | `dup_custom_ids.json` |
| Mixed pass/fail items | US3 | `mixed_results.json` |
| All-fail batch | Edge #1 | `all_fail.json` |
| Orphan result raises | FR-006, SC-003 | `orphan_result.json` |
| Tiny workload routed sync | Edge #4 | `tiny_workload_profile.json` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Sync-when-batchable anti-pattern defended by classifier verdict test.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- Where did the cost delta shrink the most — at small batch sizes, at high
  failure rates, or at aggressive fragmentation?
- What would break if you raised `MAX_FRAGMENTATION_ROUNDS` to 10?
