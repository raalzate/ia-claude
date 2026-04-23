# Feature Specification: Mass Processing with Messages Batch API

**Feature Branch**: `017-batch-processing`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 17 — Reduce capital expenditure on offline audit operations that do not require real-time responses by routing latency-tolerant workloads through the Message Batches API, preserving request/response correlation via a binding `custom_id` and handling partial failures through isolation and fragmentation."

## User Stories *(mandatory)*

### User Story 1 - Classify and submit an async-tolerant workload via the batch API (Priority: P1)

A practitioner inspects an incoming workload (thousands of documents from a nightly/weekly audit), determines that it is not user-facing and tolerates a multi-hour turnaround, assigns a unique `custom_id` to each item, submits the collection as a single asynchronous batch job, and later receives the results with every response reunited with its original source via the same `custom_id`.

**Why this priority**: This is the core MVP. Without the classify-and-submit path plus correlation, there is no batch-processing feature at all — every downstream story assumes a batch has been submitted and its results can be mapped back.

**Independent Test**: Can be fully tested by feeding a corpus of offline audit items, classifying the workload as async-tolerant, submitting it as a single batch with `custom_id`s, and verifying that the returned responses can be 100% correlated back to their source items.

**Acceptance Scenarios**:

1. **Given** a corpus of offline audit documents declared as non-user-facing and tolerating a multi-hour turnaround, **When** the practitioner classifies the workload and submits it through the batch pathway, **Then** the system produces a single batch job containing every item, each carrying a unique `custom_id`.
2. **Given** a submitted batch job that has completed within its declared window, **When** the practitioner retrieves the results, **Then** every response is paired back to its originating source item through the matching `custom_id` with no ambiguity.
3. **Given** a workload flagged as blocking (user-facing chat), **When** the practitioner runs classification, **Then** the system refuses to route it through the batch pathway and directs it to the synchronous pathway instead.

---

### User Story 2 - Demonstrate cost reduction vs. synchronous baseline (Priority: P2)

A practitioner runs the same offline audit corpus twice — once through the synchronous pathway and once through the batch pathway — and confirms that the batch pathway achieves the declared cost-reduction target, defending against the anti-pattern of paying full synchronous rate for latency-tolerant work.

**Why this priority**: The economic justification is the reason the feature exists. Without a measured comparison, the practitioner cannot prove the anti-pattern has been neutralized.

**Independent Test**: Can be fully tested by processing an identical corpus through both pathways, recording per-request cost, and asserting that the batch-pathway total cost is at least the target percentage lower than the synchronous baseline.

**Acceptance Scenarios**:

1. **Given** an identical corpus processed through both the synchronous pathway and the batch pathway, **When** totals are compared, **Then** the batch-pathway total cost is ≥ 50% lower than the synchronous total.
2. **Given** a workload that was mistakenly processed synchronously despite being async-tolerant, **When** the comparison report is produced, **Then** the report explicitly flags the missed-savings anti-pattern and quantifies the avoidable spend.

---

### User Story 3 - Isolate, fragment, and reprocess failing items (Priority: P3)

A practitioner injects items that will deliberately fail (e.g. inputs that exceed the context limit) into a batch; the system isolates those `custom_id`s into a failure bucket, fragments their source data into smaller pieces, and reprocesses only the failing subset without re-running the whole batch.

**Why this priority**: Partial-failure recovery hardens the feature for real-world corpora but is not required to prove the core value. It builds on P1 and P2.

**Independent Test**: Can be fully tested by submitting a batch that contains a known-failing minority of items, verifying that successful items are retained, that only the failing `custom_id`s are collected into a failure bucket, that their source data is fragmented, and that a follow-up batch processes only those fragments.

**Acceptance Scenarios**:

1. **Given** a completed batch in which a minority of items failed (e.g. context-limit errors), **When** the practitioner triggers recovery, **Then** only the failing `custom_id`s are collected into a failure bucket and successful items are left untouched.
2. **Given** items in the failure bucket, **When** recovery runs, **Then** each failing source is fragmented into smaller pieces and a new batch is submitted containing only those fragments.
3. **Given** the reprocessing batch completes, **When** results are merged back, **Then** fragment responses are stitched to their original source `custom_id` and the corpus ends in a fully resolved state.

---

### Edge Cases

- **All items fail**: Every item in a batch returns a failure. The failure bucket equals the entire batch; the system must surface this as a distinct condition (not a silent success) and still preserve per-item `custom_id` isolation for reprocessing.
- **Batch window exceeded**: The declared turnaround window elapses before results are available. The system must surface an explicit timeout state and must not silently convert the workload into a synchronous retry.
- **Duplicate `custom_id`s**: Two or more items share the same `custom_id`. The system must reject the submission (or otherwise refuse to lose correlation) rather than accept an ambiguous mapping.
- **Very small batch (no cost benefit)**: A workload is classified as async-tolerant but contains so few items that routing through the batch pathway yields no meaningful savings. The system must flag this as a degenerate case so the practitioner can decide rather than silently assume savings.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST classify each incoming workload as either batchable (async-tolerant, non-user-facing) or synchronous (blocking, user-facing) according to declared criteria before any submission decision is made.
- **FR-002**: System MUST assign a unique `custom_id` to every item included in a batch submission.
- **FR-003**: System MUST map every returned response back to its originating source item via the same `custom_id` used at submission.
- **FR-004**: System MUST isolate items that failed within a batch into a dedicated failure bucket keyed by `custom_id`, without discarding successful items.
- **FR-005**: System MUST support fragmenting a failing source item into smaller pieces and resubmitting only those pieces as a follow-up batch.
- **FR-006**: System MUST report the cost of a batch-pathway run against a synchronous baseline for the same workload and surface the percentage saved.
- **FR-007**: System MUST NOT silently drop items — every submitted `custom_id` MUST be accounted for as succeeded, failed, or timed out.
- **FR-008**: System MUST refuse to route a workload classified as blocking/user-facing through the batch pathway.
- **FR-009**: System MUST reject batch submissions that contain duplicate `custom_id`s.
- **FR-010**: System MUST surface an explicit terminal state when the declared batch turnaround window is exceeded.

### Key Entities

- **Workload**: A collection of items submitted together for processing. Carries a classification (batchable vs. synchronous) and a declared turnaround tolerance.
- **Batch Job**: A single asynchronous submission to the Message Batches API representing one Workload; has lifecycle states (submitted, in-progress, completed, timed-out).
- **Batched Item**: A single unit of work inside a Batch Job, uniquely identified by `custom_id` and linked to exactly one source artifact.
- **Response Mapping**: The binding between a returned response and its originating Batched Item via `custom_id`; guarantees no response is orphaned and no source is unanswered.
- **Failure Bucket**: The subset of Batched Items whose processing failed; serves as the input set for fragmentation and re-submission, distinct from the successful results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cost reduction of the batch-pathway run vs. the synchronous baseline for an identical corpus is ≥ 50%.
- **SC-002**: 100% of responses returned by a completed batch are correlated to a submitted `custom_id` (no orphaned responses, no unanswered sources).
- **SC-003**: 0 items are silently dropped across the test corpus — every submitted `custom_id` terminates in an accounted state (succeeded, failed, or timed out).
- **SC-004**: Failed-item reprocessing via isolation and fragmentation converges (all items either succeed or are explicitly declared unrecoverable) within N rounds of re-submission for the test corpus.
