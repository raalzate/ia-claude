# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Observable Event Log for Deterministic Reproduction
  Event log alone must be sufficient to reconstruct loop trajectory — iteration, branch, tool, termination cause.

  @TS-020 @FR-005 @SC-003 @P3 @acceptance
  Scenario: Every iteration produces a structured event-log entry
    Given a completed kata run
    When the event log is inspected
    Then each iteration has an entry recording iteration index, structured stop signal, branch taken, and tool name when applicable
    And the terminal iteration entry records the termination cause

  @TS-021 @FR-009 @SC-007 @P3 @acceptance
  Scenario: Two runs against the same fixture yield byte-identical stop-signal and branch sequences
    Given two independent runs of the kata against the same recorded session fixture
    When their event logs are compared
    Then the sequence of stop signals is identical across both runs
    And the sequence of branch decisions is identical across both runs

  @TS-022 @FR-009 @SC-008 @P3 @acceptance
  Scenario: Loop trajectory is reconstructible from event log alone
    Given a completed event log
    When a reviewer reconstructs the loop's behavior from the log
    Then the termination cause is identified without consulting model text
    And the number of tool invocations is identified without consulting model text
    And the iteration count is identified without consulting model text

  @TS-023 @FR-005 @FR-009 @P3 @contract
  Scenario: Event-log records conform to the declared JSON schema
    Given an event-log JSONL file produced by a run
    When each record is validated against contracts/event-log-record.schema.json
    Then every record passes schema validation
    And every record carries iteration_index, stop_signal, branch_taken fields
