# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Escalation Suspends Chat and Emits Schema-Valid Handoff Payload
  When a declared escalation precondition fires, the agent suspends further conversational text generation and emits a strictly typed JSON handoff payload via the escalate_to_human tool.

  Background:
    Given an initialized agent session with the escalate_to_human tool registered
    And the handoff schema declares customer_id, issue_summary, actions_taken, and escalation_reason as required fields
    And an operator queue sink at runs/handoffs/

  @TS-001 @FR-001 @FR-003 @FR-004 @SC-001 @US-001 @P1 @acceptance
  Scenario: Financial-limit precondition triggers schema-valid handoff
    Given a configured escalation precondition that an operation exceeds a declared financial limit
    When the practitioner submits a request that crosses the limit
    Then the agent invokes escalate_to_human exactly once
    And the emitted payload contains customer_id, issue_summary, actions_taken, and escalation_reason
    And the payload validates against the declared handoff schema

  @TS-002 @FR-001 @FR-002 @SC-001 @US-001 @P1 @acceptance
  Scenario: Agent suspends conversational output after escalation fires
    Given a configured escalation precondition has been tripped
    When the agent handles the turn
    Then further conversational text generation is suspended for the remainder of the turn
    And any subsequent messages.create call raises SessionSuspendedError
    And zero bytes of conversational text are emitted after the trigger

  @TS-003 @FR-001 @FR-003 @FR-009 @SC-004 @US-001 @P1 @acceptance
  Scenario: Policy classifier on aggressive demand routes payload with traceable id
    Given a policy classifier flags an aggressive customer demand
    When the classifier fires during the turn
    Then the agent invokes escalate_to_human exactly once
    And the payload is delivered to the operator queue with a traceable escalation_id
    And the audit log records the escalation_id linking session, precondition, and payload

  @TS-004 @FR-004 @FR-005 @US-001 @P1 @contract
  Scenario: actions_taken is a structured list not free-form prose
    Given an escalation has been triggered after the agent took prior actions
    When the handoff payload is constructed
    Then actions_taken is a list of ActionRecord entries with step_id, action_type, description, outcome, and timestamp
    And actions_taken is not a free-form text blob

  @TS-005 @FR-003 @FR-004 @US-001 @P1 @contract
  Scenario: escalate_to_human input_schema is the HandoffPayload schema
    Given the escalate_to_human tool is registered with the SDK
    When the tool definition is inspected
    Then the tool input_schema matches contracts/handoff-payload.schema.json
    And customer_id, issue_summary, actions_taken, and escalation_reason are declared required

  @TS-006 @FR-009 @FR-011 @SC-004 @US-001 @P1 @acceptance
  Scenario: Repeated escalations in a single session produce distinct traceable ids
    Given a session that triggers two separate escalations
    When both escalations are processed
    Then each escalation produces a distinct escalation_id
    And two distinct files exist under runs/handoffs/ one per escalation_id
    And the audit log records both escalation_ids without collapsing them

  @TS-007 @FR-001 @FR-005 @US-001 @P1 @acceptance
  Scenario: Escalation mid-tool-call reflects only completed steps in actions_taken
    Given the agent is partway through a multi-step tool invocation
    When the escalation precondition fires before the step completes
    Then the in-flight tool call is terminated or cleanly finalized
    And actions_taken reflects only completed steps
    And no partial step is recorded as completed

  @TS-008 @FR-004 @US-001 @P1 @acceptance
  Scenario: Unknown customer_id is handled with an explicit sentinel
    Given a session where customer_id has not been bound
    When an escalation fires
    Then the payload sets customer_id to the explicit sentinel "unknown"
    And the payload is not emitted with an empty or null customer_id

  @TS-009 @FR-004 @FR-005 @US-001 @P1 @acceptance
  Scenario: Empty actions_taken list validates when escalation fires before any action
    Given a session in which the agent has taken no prior actions
    When an escalation fires
    Then the payload validates with an empty actions_taken list
    And escalation_reason explains the zero-action trigger

  @TS-010 @FR-002 @US-001 @P1 @acceptance
  Scenario: Partial assistant message is suppressed from handoff payload
    Given the agent is generating a partial assistant message
    When the escalation precondition fires mid-generation
    Then the partial conversational output is suppressed from the handoff payload
    And the partial conversational output is not delivered to the end user

  @TS-011 @FR-001 @FR-009 @US-001 @P1 @acceptance
  Scenario Outline: Each declared escalation precondition class triggers the handoff path
    Given a configured escalation precondition of class "<reason_code>"
    When the precondition fires
    Then the agent invokes escalate_to_human exactly once
    And the payload escalation_reason equals "<reason_code>"
    And the audit log records the precondition class that fired

    Examples:
      | reason_code               |
      | policy-breach             |
      | out-of-policy-demand      |
      | operational-limit         |
      | unresolved-after-retries  |
      | explicit-user-request     |
