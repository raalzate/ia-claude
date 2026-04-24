# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Cost Reduction vs Synchronous Baseline
  The batch pathway must demonstrate measurable cost reduction against the synchronous baseline for the same corpus, defending against the anti-pattern of paying full synchronous rate for latency-tolerant work.

  @TS-007 @FR-006 @SC-001 @P2 @acceptance
  Scenario: Batch pathway cost is at least 50% lower than synchronous baseline for identical corpus
    Given an identical corpus processed through both the synchronous pathway and the batch pathway
    When the cost-delta harness compares the totals
    Then the batch-pathway total cost is at least 50 percent lower than the synchronous total
    And the reduction percentage is recorded in cost_delta.json

  @TS-008 @FR-006 @P2 @acceptance
  Scenario: Missed-savings anti-pattern is flagged when async-tolerant work ran synchronously
    Given a workload that was mistakenly processed synchronously despite being async-tolerant
    When the comparison report is produced
    Then the report explicitly flags the missed-savings anti-pattern
    And the report quantifies the avoidable spend for that workload

  @TS-009 @FR-001 @FR-006 @P2 @acceptance
  Scenario: Very small batch is flagged as a degenerate no-cost-benefit case
    Given a workload classified as async-tolerant but whose item_count is below the cost-benefit threshold
    When the practitioner evaluates the routing decision
    Then the system surfaces a "no cost benefit" escalation to the practitioner
    And the system does not silently assume cost savings

  @TS-010 @FR-006 @SC-001 @P2 @contract
  Scenario: cost_delta.json record conforms to the declared schema
    Given a completed cost-delta run for a calibration corpus
    When the cost_delta.json record is inspected
    Then it records the synchronous baseline total cost
    And it records the batch pathway total cost
    And it records the computed reduction percentage with source model ids and batch ids
