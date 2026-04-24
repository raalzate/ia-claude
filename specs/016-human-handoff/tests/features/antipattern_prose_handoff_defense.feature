# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Schema Rejects Prose-Only and Raw-Transcript Handoffs
  The schema layer must reject prose-only handoffs and raw-transcript dumps, forcing the agent back onto the structured contract.

  Background:
    Given the escalate_to_human tool is registered with the HandoffPayload schema
    And the operator queue accepts only OperatorQueueEntry records
    And a separate plain-text write_handoff_note tool is registered only under the anti-pattern fixture

  @TS-012 @FR-006 @FR-008 @SC-002 @US-002 @P2 @acceptance
  Scenario: Output missing a required field is rejected and not delivered
    Given an escalation trigger has fired
    When the agent emits an output lacking one or more required handoff fields
    Then the schema validator rejects the output
    And no handoff is delivered to the operator queue
    And the audit log records the rejection with reason "schema validation failed"

  @TS-013 @FR-007 @FR-008 @SC-002 @US-002 @P2 @acceptance
  Scenario: Raw-transcript handoff is refused
    Given a practitioner prompt requesting a raw-transcript handoff
    When the escalation is processed
    Then the system does not deliver the raw transcript as the handoff artifact
    And the result is either a structured payload or a validation failure

  @TS-014 @FR-008 @SC-002 @US-002 @P2 @acceptance
  Scenario: Prose-only handoff via plain-text tool is rejected
    Given the anti-pattern fixture registers the plain-text write_handoff_note tool
    When the agent attempts a prose-only handoff via write_handoff_note
    Then the validator rejects the attempt
    And no record is written to the operator queue
    And the event log marks the attempt as an anti-pattern rejection

  @TS-015 @FR-007 @US-002 @P2 @contract
  Scenario: issue_summary field enforces a 500-character cap
    Given a candidate handoff payload whose issue_summary exceeds 500 characters
    When the payload is validated
    Then the validator rejects the payload on the issue_summary length constraint
    And no entry is written under runs/handoffs/

  @TS-016 @FR-006 @SC-001 @US-002 @P2 @acceptance
  Scenario: Operator queue contains only schema-valid payloads
    Given a run that includes at least one schema-invalid escalation attempt
    When runs/handoffs/ is inspected after the run
    Then every file under runs/handoffs/ passes HandoffPayload validation
    And zero files contain raw-transcript fields

  @TS-017 @FR-007 @FR-008 @SC-002 @US-002 @P2 @acceptance
  Scenario Outline: Anti-pattern handoff shapes are rejected
    Given an escalation attempt whose output shape is "<shape>"
    When the validator evaluates the output
    Then the output is rejected
    And no OperatorQueueEntry is written

    Examples:
      | shape                         |
      | prose-only-narrative          |
      | raw-transcript-dump           |
      | missing-customer-id           |
      | missing-issue-summary         |
      | missing-actions-taken         |
      | missing-escalation-reason     |
