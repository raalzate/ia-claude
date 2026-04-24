# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Direct Writes During Plan Mode Are Blocked
  Any write, edit, or delete capability invoked while in Plan Mode MUST be refused, leave the disk unchanged, and be logged with mode, target, and timestamp.

  Background:
    Given a session currently in "plan" mode
    And the WriteTools registry contains "edit_file" and "write_file"
    And a writable scratch target path is available on disk

  @TS-007 @FR-002 @SC-001 @US-002 @P2 @acceptance
  Scenario Outline: Write-class tool invocation in Plan Mode raises WriteAttemptedInPlanMode
    When the agent attempts to invoke "<write_tool>" against a target path
    Then a WriteAttemptedInPlanMode exception is raised
    And the target file on disk is not modified
    And the exception carries mode equal to "plan"
    And the exception carries attempted_tool equal to "<write_tool>"

    Examples:
      | write_tool  |
      | edit_file   |
      | write_file  |

  @TS-008 @FR-002 @SC-001 @US-002 @P2 @validation
  Scenario: Write tools are structurally absent from the SDK tools payload in Plan Mode
    When the session builds its tools payload for "messages.create"
    Then the payload contains zero members of the WriteTools registry
    And the session mode asserted alongside the payload is "plan"

  @TS-009 @FR-007 @US-002 @P2 @acceptance
  Scenario: Blocked write attempt is recorded in the event log
    Given a WriteAttemptedInPlanMode exception has been raised
    When the session handles the exception
    Then an entry is appended to "runs/<session-id>/events.jsonl"
    And the entry records the attempted tool name
    And the entry records the attempted target path
    And the entry records the current mode as "plan"
    And the entry records a UTC timestamp

  @TS-010 @FR-002 @SC-001 @US-002 @P2 @acceptance
  Scenario: Zero writes observed across the Plan Mode test corpus
    Given every fixture in the Plan Mode corpus has been executed
    When the filesystem diff for each run is inspected
    Then the count of files modified during "plan" mode across all runs equals 0
