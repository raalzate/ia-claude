# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Structured Error Log Inspection and Classification
  Every MCP attempt must be observable by structured fields alone — no free-text parsing required.

  Background:
    Given a completed workshop session containing at least one transient failure
    And the session contains at least one validation failure
    And the structured error log is written as append-only JSONL

  @TS-014 @FR-006 @SC-001 @P3 @acceptance
  Scenario: Each log entry exposes category, retryability, detail, and outcome
    When the practitioner opens the structured error log
    Then every failure entry carries an errorCategory field
    And every failure entry carries an isRetryable field
    And every failure entry carries a detail field
    And every entry carries an outcome drawn from the closed set {success, retried_success, retried_exhausted, escalated, aborted}

  @TS-015 @FR-006 @P3 @acceptance
  Scenario: Log entries are groupable by category and retryability without text parsing
    Given the structured error log has been loaded
    When the practitioner filters entries by errorCategory
    Then the count of entries per category is derivable from structured fields alone
    And the count of entries per isRetryable flag is derivable from structured fields alone
    And no aggregation step reads the detail field

  @TS-016 @FR-006 @P3 @contract
  Scenario: Log records conform to the ErrorLogRecord schema
    Given a JSONL error log produced by a run
    When each record is validated against the ErrorLogRecord model
    Then every record passes schema validation
    And every record carries session_id, call_id, attempt, and tool_name

  @TS-017 @FR-006 @P3 @acceptance
  Scenario: Records for the same call_id form a time-ordered recovery chain
    Given a call_id that experienced two failed attempts before succeeding
    When the records for that call_id are extracted
    Then the records are ordered by ascending timestamp
    And exactly one record has outcome "retried_success"
    And the preceding records carry the failure metadata that motivated the retries

  @TS-018 @FR-006 @P3 @acceptance
  Scenario: Chained tool failures are logged independently per call
    Given a single agent turn triggered three tool calls with mixed failure categories
    When the error log is inspected
    Then each tool call is represented by its own record chain
    And no record collapses multiple call_ids into a single generic message
    And each chain independently resolves to its own outcome
