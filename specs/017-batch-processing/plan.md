# Implementation Plan: Mass Processing with Messages Batch API

**Branch**: `017-batch-processing` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/017-batch-processing/spec.md`

## Summary

Build a Python kata module that routes latency-tolerant, non-user-facing workloads
through Anthropic's Message Batches API (`client.messages.batches.create`,
`.retrieve`, `.results`) instead of paying full synchronous rate. A
`WorkloadClassifier` emits a typed `batchable | synchronous` verdict from declared
criteria (`is_blocking`, `latency_budget_seconds`, `item_count`, `expected_cost_usd`);
a pydantic `BatchJob` guarantees unique `custom_id`s pre-submit (duplicates are
rejected, not silently overwritten); a `ResponseMapper` reconstructs every
`custom_id → response` binding (orphan/missing custom_ids raise `MissingResultError`
— FR-006, FR-007, SC-003); a `FailureBucket` isolates `errored | expired` items,
fragments them, and resubmits in bounded rounds until convergence (FR-004, FR-005,
SC-004); a cost-delta harness records a synchronous baseline for a calibration
corpus and asserts the batch-pathway cost reduction meets the declared ≥50% target
(SC-001). Delivered under Constitution v1.3.0 Principles II (NN),
III, and VIII (NN).

## Technical Context

**Language/Version**: Python 3.11+.
**Primary Dependencies**:

- `anthropic` (official Claude SDK) — exclusive source of batch lifecycle signals.
  Uses `client.messages.batches.create(requests=[...])`,
  `client.messages.batches.retrieve(id)` (for `processing_status` /
  `request_counts`), and `client.messages.batches.results(id)` (streaming JSONL
  of per-item results keyed by `custom_id`). Status drives FR-010 window timeout
  and FR-007 accounting; results drive FR-003 correlation and FR-004 bucketing.
- `pydantic` v2 — schema enforcement for `WorkloadProfile`, `BatchedItem`,
  `BatchJob`, `BatchedResult`, `ResponseMapping`, `FailureBucket` (Principle II).
  A model validator on `BatchJob.items` rejects duplicate `custom_id`s (FR-009)
  before any SDK call is made.
- `pytest` + `pytest-bdd` — BDD runner for the Gherkin scenarios produced by
  `/iikit-04-testify`; unit tests for classifier thresholds, mapper guarantees,
  and fragmentation invariants.

**Storage**: Local filesystem only. Per-run artifacts under
`runs/<job_id>/`: `submission.json` (the pre-submit `BatchJob`), `results.jsonl`
(one line per `BatchedResult`, mirrored from `batches.results()`),
`failure_bucket.json` (isolated items after each round), `cost_delta.json`
(sync-baseline vs batch totals for SC-001). No database.

**Testing**: pytest + pytest-bdd for acceptance; pytest for units. Fixtures under
`tests/katas/017_batch_processing/fixtures/` are recorded JSON snapshots of the
batch lifecycle and results stream, served through a `RecordedBatchClient` stub
so the default test run is offline and deterministic. Live SDK calls are gated
behind `LIVE_API=1` and target a tiny corpus (~5 items) to keep quota usage
trivial — the quickstart documents the invocation.

**Target Platform**: Developer local (macOS/Linux) and GitHub Actions CI (Linux).
No server deployment.

**Project Type**: Single project. Kata module at
`katas/017_batch_processing/`; tests mirror the path at
`tests/katas/017_batch_processing/`.

**Performance Goals**: Not latency-bound. Acceptance suite against recorded
fixtures completes in under 10 seconds locally. The classifier decision itself
is O(1) against the declared thresholds.

**Constraints**:

- Every `custom_id` submitted MUST terminate in an accounted state
  (`succeeded`, `errored`, `expired`). Silent drops are a spec violation
  (FR-007, SC-003) and the test suite fails closed if the mapper can't
  account for one.
- Classification happens BEFORE any batch call; blocking workloads MUST NOT
  reach the batch pathway (FR-001, FR-008).
- Duplicate `custom_id` submissions MUST be rejected pre-submit — the SDK
  itself also rejects duplicates, but the kata catches them earlier with a
  pydantic validator so the failure is local and debuggable (FR-009).
- Fragmentation rounds are bounded by a declared `max_recovery_rounds` (default
  3). Exceeding the bound marks remaining items `unrecoverable` — never an
  infinite loop (SC-004).
- Network surface lives behind an injectable client (`BatchClient` protocol) so
  tests swap a `RecordedBatchClient` for the real SDK.

**Scale/Scope**: One kata, ~450–600 LOC implementation + comparable test code.
One `README.md` (written during `/iikit-07-implement`). Calibration corpus:
~50 items for the offline cost-delta demonstration; live-API dry-run corpus:
5 items.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Classification and batch lifecycle branch on typed fields (`WorkloadProfile`, `batch.processing_status`, `result.type`) — never on free-text. Timeout is decided by the structured `expires_at` vs wall clock, not by model prose. |
| II. Schema-Enforced Boundaries (NN) | Every boundary — workload profile in, batch request out, per-item result in, failure bucket out — is a pydantic v2 model mirrored by a JSON Schema under `contracts/`. Invalid payloads raise; duplicate `custom_id` is a validator rejection, not a runtime surprise. |
| III. Context Economy | The batch pathway is itself a context-economy instrument: latency-tolerant bulk work is off-loaded from the chat-context window to an async queue, which is exactly the workshop lesson. Submission payloads are constructed once and not retained in any chat turn. |
| IV. Subagent Isolation | Not load-bearing for this kata (no sub-agents). The classifier and the mapper are plain functions, not agents. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before production code per Constitution §Development Workflow. Acceptance scenarios will cover the objective (cost-reduced batch path with preserved correlation) and the anti-pattern (synchronous execution of latency-tolerant work; silent drop of failed items). |
| VI. Human-in-the-Loop | Classification verdict `synchronous` on a small-batch workload (edge case #4) surfaces a typed "no cost benefit" escalation instead of silently running a no-win batch. |
| VII. Provenance & Self-Audit | `cost_delta.json` records sync-baseline tokens + cost, batch tokens + cost, and the computed reduction % with its source model ids and batch ids — so SC-001 is auditable from the artifact alone. `results.jsonl` is the replayable audit log for every `custom_id`. |
| VIII. Mandatory Documentation (NN) | Per-kata `README.md` will be written during `/iikit-07-implement` covering objective, walkthrough, anti-pattern defense (synchronous-for-async-work), run instructions, reflection. Every non-trivial function / validator will carry a *why* comment tied to the FR it defends (e.g. the duplicate-`custom_id` validator's docstring names FR-009 + edge case #3). |

**Result:** PASS. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/017-batch-processing/
  plan.md              # this file
  research.md          # Phase 0 output (decisions D-001..N + classifier thresholds + Tessl note)
  data-model.md        # Phase 1 output (Workload, BatchJob, BatchedItem, ResponseMapping, FailureBucket)
  quickstart.md        # Phase 1 output (install, fixture run, LIVE_API dry-run, scenario→spec map, Kata Completion checklist)
  contracts/           # Phase 1 output (JSON Schemas, $id kata-017)
    workload-profile.schema.json
    batch-item.schema.json
    batch-job.schema.json
    batched-result.schema.json
    failure-bucket.schema.json
  tasks.md             # (generated by /iikit-05-tasks — NOT created here)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01-specify)
  README.md            # Principle VIII deliverable (produced at /iikit-07-implement)
```

### Source Code (repository root)

```text
katas/
  017_batch_processing/
    __init__.py
    classifier.py          # WorkloadClassifier: batchable | synchronous verdict
    batch_job.py           # BatchJob construction + pre-submit duplicate-custom_id validator
    client.py              # Injectable BatchClient (real SDK adapter + RecordedBatchClient stub)
    mapper.py              # ResponseMapper: batches.results() → custom_id→response mapping; MissingResultError
    failure_bucket.py      # FailureBucket isolation + fragmentation + bounded re-submit
    cost_delta.py          # Sync-baseline harness + batch cost totaliser + reduction assertion (SC-001)
    models.py              # pydantic v2: WorkloadProfile, BatchedItem, BatchJob, BatchedResult, ResponseMapping, FailureBucket
    runner.py              # CLI entrypoint: python -m katas.017_batch_processing.runner --corpus ...
    README.md              # kata narrative (written during /iikit-07-implement)

tests/
  katas/
    017_batch_processing/
      conftest.py
      features/            # Gherkin files produced by /iikit-04-testify
        batch_processing.feature
      step_defs/
        test_batch_processing_steps.py
      unit/
        test_classifier_thresholds.py
        test_duplicate_custom_id_rejected.py
        test_mapper_no_silent_drop.py
        test_failure_bucket_fragments.py
        test_cost_delta_target.py
      fixtures/
        all_succeed.json          # every item returns result.type=succeeded
        all_fail.json              # every item result.type=errored (edge: all-fail)
        mixed.json                 # majority succeed, minority errored
        duplicate_custom_id.json   # pre-submit rejection fixture (no SDK call made)
        very_small_batch.json      # item_count below cost-benefit threshold → verdict=synchronous
        window_exceeded.json       # batch.processing_status=canceled/expired past expires_at (FR-010)
```

**Structure Decision**: Single-project kata layout matching kata-001's pattern —
one package under `katas/017_batch_processing/`, tests mirrored under
`tests/katas/017_batch_processing/`. Runs (including `submission.json`,
`results.jsonl`, `cost_delta.json`, `failure_bucket.json`) are written to
`runs/<job_id>/` and are gitignored. Keeps the kata independently buildable and
assertion-integrity-hashable, consistent with FDD vertical delivery per kata.

## Architecture

```
┌────────────────────┐
│Workload Classifier │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  Batch Submitter   │───────│    Batches API     │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Response Mapper │ │ Failure Bucket │ │  Cost Report   │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Workload Classifier` is the kata entry point; `Batch Submitter` owns the core control flow
for this kata's objective; `Batches API` is the primary collaborator/policy reference;
`Response Mapper`, `Failure Bucket`, and `Cost Report` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

_No violations._ Deliberately out of scope for this kata:

- Retry policy on SDK transport errors — tested via fixture, not implemented
  (keep the kata focused on the batch-lifecycle control flow).
- Cross-account cost normalisation — the cost-delta harness reports per-model,
  per-run figures; fleet-level cost management belongs to a later feature.
- Concurrent multi-batch submission — one batch per run is sufficient to
  demonstrate the anti-pattern and its defense.
