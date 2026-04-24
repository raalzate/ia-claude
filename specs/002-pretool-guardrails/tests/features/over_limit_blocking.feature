# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Over-Limit Refund Is Blocked Pre-API by Deterministic Logic
  An amount strictly above the configured policy limit must be rejected at the PreToolUse boundary with a structured error, zero external API calls, an escalation event, and a deterministic verdict independent of system-prompt content.

  Background:
    Given a configured refund policy with limit L
    And a schema-valid refund payload whose amount is strictly greater than L

  @TS-003 @US-002 @FR-001 @FR-004 @FR-006 @SC-001 @SC-002 @P2 @acceptance
  Scenario: Over-limit refund yields a reject verdict before any external API call
    When the PreToolUse hook evaluates the refund invocation
    Then the hook emits a verdict with value "reject"
    And the verdict reason_code is "policy_breach"
    And zero refund API calls are observed for the invocation correlation_id

  @TS-004 @US-002 @FR-003 @FR-005 @SC-003 @P2 @acceptance
  Scenario: Rejected invocation delivers a structured error into the model's next context window
    When the PreToolUse hook rejects the over-limit invocation
    Then the model's next context window receives a StructuredError object
    And the StructuredError carries reason_code "policy_breach"
    And the StructuredError identifies the offending field as "amount"
    And the StructuredError cites the policy_id and policy_snapshot_version that was breached
    And the StructuredError carries a non-empty escalation_pathway
    And no free-text apology is returned via the tool channel

  @TS-005 @US-002 @FR-007 @P2 @acceptance
  Scenario: Policy-breach rejection emits an escalation event with zero actions taken
    When the PreToolUse hook rejects the over-limit invocation
    Then an EscalationEvent is appended to the audit log
    And the EscalationEvent has escalation_reason "policy_breach"
    And the EscalationEvent actions_taken list is empty
    And the EscalationEvent routing_target equals the policy escalation_pathway
    And the EscalationEvent references the same correlation_id as the verdict

  @TS-006 @US-002 @FR-010 @SC-001 @P2 @acceptance
  Scenario: Retrying the same over-limit payload yields an identical verdict
    When the PreToolUse hook evaluates the over-limit invocation twice with the same policy snapshot
    Then both verdicts are equal in every field except evaluated_at
    And both verdicts carry reason_code "policy_breach"

  @TS-007 @US-002 @FR-008 @P2 @acceptance
  Scenario: Enforcement holds when the system prompt contains no limit text
    Given a system prompt that does not mention any dollar limit
    When the PreToolUse hook evaluates the over-limit invocation
    Then the hook emits a verdict with value "reject"
    And no numeric literal matching the policy max_refund appears in the system prompt module

  @TS-008 @US-002 @FR-009 @P2 @acceptance
  Scenario: Rejection is recorded in the audit log with full traceability
    When the PreToolUse hook rejects the over-limit invocation
    Then the audit log contains a verdict record with the invocation correlation_id
    And the record carries a timestamp, policy_id, policy_snapshot_version, offending_field, and offending_value
    And the record ties to both the StructuredError and the EscalationEvent via the correlation_id
