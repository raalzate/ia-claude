# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Schema Extension Propagates Across Escalations
  Extending the handoff schema with a new required field must force every subsequent escalation to include it, without changes to agent prompt logic.

  @TS-018 @FR-010 @SC-001 @US-003 @P3 @acceptance
  Scenario: Updated schema enforces severity on new escalations
    Given the handoff schema is updated to require severity
    When an escalation fires after the update
    Then the resulting payload must include a valid severity value
    And payloads without severity are rejected by the validator

  @TS-019 @FR-010 @SC-001 @US-003 @P3 @acceptance
  Scenario: Legacy escalation path without severity is rejected
    Given a legacy escalation path that does not emit severity
    When it attempts to hand off under the updated schema
    Then the system surfaces a schema validation failure
    And no incomplete payload is silently delivered to the operator queue

  @TS-020 @FR-010 @US-003 @P3 @contract
  Scenario: Agent prompt text is not modified to satisfy schema extension
    Given the handoff schema is extended to require severity
    When the agent is re-run against the original prompt template
    Then no change is made to the agent prompt logic
    And the schema is the single source of truth for required fields

  @TS-021 @FR-010 @SC-001 @US-003 @P3 @acceptance
  Scenario Outline: Severity literal accepts declared values and rejects others
    Given the handoff schema requires severity as a closed literal
    When a payload with severity "<value>" is validated
    Then the validation outcome is "<outcome>"

    Examples:
      | value     | outcome  |
      | low       | accepted |
      | medium    | accepted |
      | high      | accepted |
      | critical  | accepted |
      | urgent    | rejected |
      |           | rejected |

  @TS-022 @FR-012 @US-003 @P3 @validation
  Scenario: Documentation describes preconditions, schema, and anti-pattern
    Given the kata README is published under Principle VIII
    When a reviewer inspects the documentation
    Then the escalation preconditions are described
    And the handoff schema fields are described
    And the anti-pattern being defended is described

  @TS-023 @FR-009 @SC-004 @US-003 @P3 @validation
  Scenario: Every escalation id is traceable end-to-end in the audit log
    Given a run that emits at least one escalation
    When the audit log and operator queue are joined by escalation_id
    Then every escalation_id links session, precondition, payload, and queue-file path
    And a single query reconstructs the full handoff chain
