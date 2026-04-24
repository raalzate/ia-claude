# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Isolate Fragment And Reprocess Failing Items
  Partial batch failures are isolated into a failure bucket keyed by custom_id, fragmented into smaller pieces, and reprocessed in bounded rounds without rerunning the whole batch.

  Background:
    Given a completed batch whose per-item results are available via the recorded client
    And a FailureBucket collector keyed by custom_id
    And a declared max_recovery_rounds bound for reprocessing

  @TS-011 @FR-004 @FR-007 @SC-003 @P3 @acceptance
  Scenario: Only failing custom_ids are isolated; successful items are left untouched
    Given a completed batch in which a minority of items returned result.type "errored"
    When the practitioner triggers recovery
    Then only the failing custom_ids are collected into the failure bucket
    And successful items are not re-submitted
    And every submitted custom_id is accounted as succeeded, failed, or timed out

  @TS-012 @FR-005 @P3 @acceptance
  Scenario: Failing items are fragmented and resubmitted as a follow-up batch
    Given items present in the failure bucket
    When recovery runs
    Then each failing source is fragmented into smaller pieces
    And a new batch is submitted containing only those fragments

  @TS-013 @FR-003 @FR-005 @SC-004 @P3 @acceptance
  Scenario: Fragment responses are stitched back to the original source custom_id on convergence
    Given a reprocessing batch that completes successfully
    When the fragment results are merged back
    Then each fragment response is stitched to its original source custom_id
    And the corpus ends in a fully resolved state within the declared max_recovery_rounds

  @TS-014 @FR-004 @FR-007 @SC-003 @P3 @acceptance
  Scenario: All-fail batch is surfaced as a distinct condition with full custom_id isolation
    Given a completed batch in which every item returned result.type "errored"
    When the failure bucket is produced
    Then the failure bucket equals the entire submitted set of custom_ids
    And the all-fail condition is surfaced as a distinct terminal state rather than a silent success

  @TS-015 @FR-007 @FR-010 @P3 @acceptance
  Scenario: Batch window exceeded is surfaced as explicit timeout without synchronous retry
    Given a batch whose declared turnaround window has elapsed before results are available
    When the batch lifecycle is inspected
    Then an explicit timeout terminal state is surfaced
    And the workload is not silently converted into a synchronous retry
    And every submitted custom_id is accounted as timed out

  @TS-016 @FR-005 @SC-004 @P3 @acceptance
  Scenario: Recovery rounds are bounded and remaining items are marked unrecoverable
    Given a failure bucket whose items still fail after max_recovery_rounds fragmentation attempts
    When the recovery loop exits
    Then remaining items are marked "unrecoverable"
    And no further batch submission is attempted
    And the run terminates without an infinite loop

  @TS-017 @FR-004 @SC-003 @P3 @contract
  Scenario: FailureBucket payload conforms to the failure-bucket JSON schema
    Given a FailureBucket produced after a completed batch
    When the payload is validated against contracts/failure-bucket.schema.json
    Then the payload passes schema validation
    And every entry is keyed by a custom_id from the original submission
