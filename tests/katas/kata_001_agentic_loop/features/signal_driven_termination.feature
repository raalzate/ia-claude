# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Signal-Driven Loop Termination
  Agent loop branches exclusively on structured stop_reason metadata — never on response prose.

  Background:
    Given an initialized agent session with at least one registered tool

  @TS-001 @FR-001 @FR-003 @SC-001 @P1 @acceptance
  Scenario: Terminal end_turn signal halts loop and records cause
    When the session completes a turn whose structured stop signal is "end_turn"
    Then the loop halts and returns the final response
    And the event log records "stop_reason=end_turn" as the sole termination cause

  @TS-002 @FR-001 @FR-002 @SC-005 @P1 @acceptance
  Scenario: tool_use signal dispatches tool and continues loop
    When the session returns "stop_reason=tool_use" for the current turn
    Then the designated tool is invoked programmatically
    And the tool result is appended to conversation history
    And a new iteration begins without any termination decision

  @TS-003 @FR-001 @FR-010 @P1 @acceptance
  Scenario: Alternating tool_use and end_turn signals drive trajectory
    When the session runs a multi-turn interaction alternating "tool_use" and "end_turn" signals
    Then the sequence of structured stop signals in the event log fully explains the loop trajectory
    And no event log entry references response text content

  @TS-004 @FR-006 @SC-006 @P1 @acceptance
  Scenario: max_tokens stop signal halts with distinct reason
    When the session completes a turn whose structured stop signal is "max_tokens"
    Then the loop halts within one iteration
    And the event log records a termination reason tying the halt to "max_tokens"

  @TS-005 @FR-006 @SC-006 @P1 @acceptance
  Scenario: Absent stop signal halts as protocol violation
    When the session returns a response with no stop signal field
    Then the loop halts with a protocol-violation termination reason
    And no text-pattern fallback is attempted

  @TS-006 @FR-006 @SC-006 @P1 @acceptance
  Scenario: Unrecognized stop signal halts with unhandled-signal reason
    When the session returns a stop signal value the loop does not explicitly handle
    Then the loop halts within one iteration
    And the event log labels the termination as "unhandled stop signal"
