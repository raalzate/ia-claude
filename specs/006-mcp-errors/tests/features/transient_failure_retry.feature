# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Transient Failure with Successful Retry
  Retryable MCP failures must be resolved locally via structured metadata within a declared retry budget.

  Background:
    Given an MCP server exposes a tool registered under a known identifier
    And the agent declares a retry budget with max_attempts of 3
    And the agent has an empty structured error log

  @TS-001 @FR-001 @FR-002 @SC-001 @P1 @acceptance
  Scenario: Transient failure response carries full structured error payload
    Given the tool is configured to fail transiently on its first invocation
    When the agent invokes the tool
    Then the MCP response has isError equal to true
    And the response carries an errorCategory of "transient"
    And the response carries isRetryable equal to true
    And the response carries a non-empty explanation detail

  @TS-002 @FR-004 @FR-005 @SC-003 @P1 @acceptance
  Scenario: Retryable failure within budget is retried and succeeds
    Given the tool fails transiently on its first invocation and succeeds on retry
    When the agent processes the structured error
    Then the agent decides a recovery action of "retry"
    And the subsequent invocation returns isError equal to false
    And the final result is surfaced to the practitioner

  @TS-003 @FR-006 @SC-001 @P1 @acceptance
  Scenario: Retried-success run records both attempts with full metadata
    Given a transient failure was retried and resolved successfully
    When the practitioner inspects the structured error log
    Then the log contains one record for the failed attempt with errorCategory and isRetryable
    And the log contains one record for the successful attempt with outcome "retried_success"
    And every record carries tool identity, attempt index, and timestamp

  @TS-004 @FR-005 @P1 @acceptance
  Scenario: Retry budget decrements per attempt and is threaded through calls
    Given a retry budget with max_attempts of 3 and elapsed_attempts of 0
    When the agent consumes one retry
    Then the returned budget reports elapsed_attempts of 1
    And the returned budget reports remaining of 2
    And the original budget object is not mutated

  @TS-005 @FR-004 @FR-005 @P1 @contract
  Scenario Outline: Retryable categories branch to retry when budget remains
    Given a structured error with errorCategory "<category>" and isRetryable true
    And the retry budget has remaining attempts greater than 0
    When the policy decides a recovery action
    Then the action is "retry"
    And a next_call is constructed with attempt incremented by 1

    Examples:
      | category  |
      | transient |
      | quota     |
