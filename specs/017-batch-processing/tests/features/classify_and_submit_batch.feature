# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Classify And Submit Async-Tolerant Workload via Batch API
  Latency-tolerant, non-user-facing workloads are routed through the Message Batches API with unique custom_ids so every response can be correlated back to its source item.

  Background:
    Given an injectable batch client that records submissions and returns recorded results
    And a pre-submit BatchJob validator that rejects duplicate custom_ids
    And a WorkloadClassifier configured with declared batchable-vs-synchronous thresholds

  @TS-001 @FR-001 @FR-002 @SC-002 @P1 @acceptance
  Scenario: Async-tolerant workload is classified batchable and submitted with unique custom_ids
    Given a corpus of offline audit documents declared as non-user-facing and tolerating a multi-hour turnaround
    When the practitioner classifies the workload and submits it through the batch pathway
    Then the classifier verdict is "batchable"
    And a single batch job is produced containing every item from the corpus
    And every batched item carries a unique custom_id

  @TS-002 @FR-003 @SC-002 @P1 @acceptance
  Scenario: Completed batch results are correlated back to source items by custom_id
    Given a submitted batch job that has completed within its declared window
    When the practitioner retrieves the results
    Then every response is paired back to its originating source item through the matching custom_id
    And no response is orphaned and no submitted source is left unanswered

  @TS-003 @FR-001 @FR-008 @P1 @acceptance
  Scenario: Blocking user-facing workload is refused by the batch pathway
    Given a workload flagged as blocking and user-facing
    When the practitioner runs classification
    Then the classifier verdict is "synchronous"
    And the system refuses to route the workload through the batch pathway
    And the workload is directed to the synchronous pathway instead

  @TS-004 @FR-009 @P1 @acceptance
  Scenario: Duplicate custom_ids are rejected before any SDK call is made
    Given a batch submission whose items contain at least two entries sharing the same custom_id
    When the BatchJob is constructed
    Then the pre-submit validator raises a duplicate-custom_id rejection
    And no call is made against the Message Batches API

  @TS-005 @FR-001 @P1 @validation
  Scenario Outline: Classifier verdict follows declared thresholds
    Given a workload with is_blocking "<is_blocking>" and latency_budget_seconds "<latency_budget>" and item_count "<items>"
    When the classifier evaluates the workload
    Then the verdict is "<verdict>"

    Examples:
      | is_blocking | latency_budget | items | verdict      |
      | false       | 86400          | 1000  | batchable    |
      | true        | 5              | 1000  | synchronous  |
      | false       | 2              | 1000  | synchronous  |
      | false       | 86400          | 2     | synchronous  |

  @TS-006 @FR-002 @FR-003 @SC-002 @P1 @contract
  Scenario: Submitted BatchJob payload conforms to the batch-job JSON schema
    Given a constructed BatchJob for a batchable corpus
    When the payload is validated against contracts/batch-job.schema.json
    Then the payload passes schema validation
    And every item entry carries a custom_id field unique within the job
