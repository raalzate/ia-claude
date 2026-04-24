# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Validation Failure Routes to Escalation
  Non-retryable MCP failures must bypass retries and emit a typed escalation payload — never a generic failure string.

  Background:
    Given an MCP server exposes a tool registered under a known identifier
    And the agent declares a retry budget with max_attempts of 3
    And an escalation sink is declared in policy

  @TS-006 @FR-002 @FR-004 @SC-004 @P2 @acceptance
  Scenario: Validation failure returns non-retryable structured error
    Given a tool call whose input violates the tool's validation rules
    When the agent invokes the tool
    Then the MCP response has isError equal to true
    And the response carries an errorCategory of "validation"
    And the response carries isRetryable equal to false

  @TS-007 @FR-004 @SC-004 @P2 @acceptance
  Scenario: Non-retryable failure performs zero retries
    Given a structured error with isRetryable equal to false
    When the agent processes the error
    Then zero additional attempts are executed against the same tool call
    And the escalation trigger records attempts_taken equal to 1

  @TS-008 @FR-004 @FR-008 @SC-004 @P2 @acceptance
  Scenario: Escalation trigger is typed and names the policy sink
    Given a non-retryable failure has been processed
    When the escalation trigger is inspected
    Then the trigger references the originating call_id
    And the trigger carries a closed-set reason of "non_retryable_category"
    And the trigger names the declared escalation_sink
    And the trigger embeds the triggering StructuredError

  @TS-009 @FR-003 @SC-002 @P2 @validation
  Scenario: No generic failure string crosses the MCP response boundary
    Given the agent has processed a non-retryable failure
    When the agent transcript and tool-response log are scanned
    Then no occurrence of "Operation failed" appears in the agent context
    And no occurrence of "Something went wrong" appears in the agent context
    And no occurrence of a bare "Error" completion string appears in the agent context

  @TS-010 @FR-007 @P2 @acceptance
  Scenario: Transport-level failure synthesizes a conformant structured error
    Given the transport drops the connection before the MCP server responds
    When the agent observes the transport failure
    Then a structured error is synthesized locally with errorCategory "transport"
    And the synthesized error is valid under the structured-error schema
    And no raw exception string is surfaced to the agent context

  @TS-011 @FR-007 @P2 @acceptance
  Scenario: Non-conformant server payload is classified as schema_violation
    Given the MCP server returns isError true but omits isRetryable
    When the agent validates the response
    Then a structured error is synthesized with errorCategory "schema_violation"
    And the synthesized error has isRetryable equal to false
    And no fallback to a generic failure string occurs

  @TS-012 @FR-005 @FR-008 @SC-004 @P2 @acceptance
  Scenario: Retry budget exhaustion routes to escalation with budget_exhausted reason
    Given a retryable failure recurs until the retry budget is exhausted
    When the agent detects the exhausted budget
    Then the recovery action is "escalate"
    And the escalation trigger carries a reason of "budget_exhausted"
    And the outcome recorded in the log is "retried_exhausted"

  @TS-013 @FR-004 @P2 @contract
  Scenario Outline: Non-retryable categories always escalate on first attempt
    Given a structured error with errorCategory "<category>" and isRetryable false
    When the policy decides a recovery action
    Then the action is "escalate"
    And zero retries are executed
    And the escalation trigger attempts_taken equals 1

    Examples:
      | category         |
      | validation       |
      | auth             |
      | schema_violation |
