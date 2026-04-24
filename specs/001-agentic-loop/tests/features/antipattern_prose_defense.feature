# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Anti-Pattern Defense Against Prose Completion Phrases
  Decoy completion phrases in model prose must NOT trigger early termination — only structured signals can.

  @TS-010 @FR-004 @SC-004 @P2 @acceptance
  Scenario: Decoy "task complete" text with tool_use signal does not terminate
    Given a fixture response whose text body contains "task complete"
    And the structured stop signal of that response is "tool_use"
    When the loop processes the response
    Then the tool-use branch executes
    And the loop continues rather than terminating

  @TS-011 @FR-004 @SC-004 @P2 @acceptance
  Scenario Outline: Decoy completion phrases with non-terminal signal do not halt loop
    Given a fixture response whose text body contains "<decoy>"
    And the structured stop signal of that response is "<signal>"
    When the loop processes the response
    Then the loop continues iterating
    And the event log shows zero early exits attributable to text matching

    Examples:
      | decoy          | signal   |
      | task complete  | tool_use |
      | we are done    | tool_use |
      | finished       | tool_use |
      | all done       | tool_use |

  @TS-012 @FR-004 @SC-002 @P2 @acceptance
  Scenario: Termination decision references only structured metadata
    Given any loop iteration has completed
    When the termination decision record is inspected
    Then it references only structured stop metadata
    And it contains no field derived from regex or substring operation on response text

  @TS-013 @FR-007 @P2 @acceptance
  Scenario: Tool invocation failure is captured as structured result and loop continues
    Given the current turn has "stop_reason=tool_use"
    When the tool invocation raises or returns a structured error
    Then the failure is recorded as a structured tool-result entry in conversation history
    And the event log records the failure
    And the loop continues under signal-driven rules without text inspection

  @TS-014 @FR-008 @P2 @acceptance
  Scenario: Malformed tool_use payload halts with unhandled-tool-use reason
    Given a response carries "stop_reason=tool_use"
    And the tool_use block is missing required fields or references an unknown tool
    When the loop processes the response
    Then the loop halts with an "unhandled tool-use" termination reason
    And no heuristic recovery or text-based fallback is attempted
