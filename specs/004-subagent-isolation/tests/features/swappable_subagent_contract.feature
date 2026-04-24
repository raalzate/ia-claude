# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Swappable Subagent via Typed Handoff Contract
  A subagent implementation can be replaced without coordinator change as long as the Handoff Contract is preserved, and contract violations surface as terminal errors.

  Background:
    Given a working coordinator and subagent set completing a reference task end-to-end
    And a declared HandoffContract pairing a SubtaskPayload schema with a SubagentResult schema
    And no changes to the coordinator's code, prompt, or configuration are permitted during the swap

  @TS-013 @FR-008 @SC-003 @P3 @acceptance
  Scenario: Swap a subagent implementation that honors the same contract
    Given one subagent is replaced by a different implementation that honors the same HandoffContract
    When the same reference task is rerun
    Then the coordinator completes the task without any change to its own code
    And the coordinator completes the task without any change to its own prompt
    And the coordinator completes the task without any change to its own configuration
    And the final output validates against the declared SubagentResult schema

  @TS-014 @FR-003 @FR-004 @SC-002 @P3 @acceptance
  Scenario: Swapped subagent output violating the contract surfaces a terminal error
    Given a swapped subagent returns output that violates the HandoffContract
    When the coordinator receives the result
    Then the coordinator surfaces a terminal schema-validation error
    And the coordinator does not silently proceed with a coerced value

  @TS-015 @FR-003 @FR-004 @SC-002 @P3 @validation
  Scenario: Malformed JSON from subagent is a terminal error with no silent fallback
    Given a subagent returns a string that is not parseable JSON
    When the coordinator attempts to consume the result
    Then the coordinator raises a terminal schema-validation error
    And the coordinator does not apply a text-based or best-effort fallback

  @TS-016 @FR-003 @SC-002 @P3 @contract
  Scenario: Extra fields in subagent result are rejected under extra="forbid"
    Given a subagent returns a result containing a field not declared in the SubagentResult schema
    When the coordinator validates the result
    Then validation fails under the schema's extra="forbid" policy
    And the extra field is not absorbed into coordinator state

  @TS-017 @FR-004 @SC-002 @P3 @validation
  Scenario Outline: Terminal validation errors are surfaced with labeled reasons
    Given a subagent returns output classified as "<violation>"
    When the coordinator validates the result
    Then the coordinator raises a terminal validation error
    And the error reason is labeled "<reason>"

    Examples:
      | violation                  | reason                        |
      | non_parseable_json         | schema_violation              |
      | missing_required_field     | schema_violation              |
      | extra_undeclared_field     | schema_violation              |
      | task_id_mismatch           | schema_violation              |

  @TS-018 @FR-008 @SC-003 @P3 @acceptance
  Scenario: Coordinator depends only on the typed contract, not subagent internals
    Given a stub subagent implementation wired through the same TaskSpawner seam
    When the coordinator runs the reference task against the stub
    Then the coordinator's observable behavior is identical to the default implementation
    And no coordinator code path references subagent-internal state
