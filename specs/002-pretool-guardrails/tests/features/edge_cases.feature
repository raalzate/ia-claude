# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Edge Cases for Schema Violations, Boundary, and Fail-Closed Behavior
  Malformed payloads, boundary amounts, extra fields, hook internal failures, and concurrent policy updates must all produce deterministic, structured, fail-closed outcomes with zero external API calls.

  @TS-012 @US-002 @FR-002 @FR-003 @FR-005 @FR-006 @SC-002 @SC-003 @P2 @acceptance
  Scenario Outline: Malformed refund payloads are rejected as schema violations before any API call
    Given a refund payload with "<defect>"
    When the PreToolUse hook evaluates the refund invocation
    Then the hook emits a verdict with value "reject"
    And the verdict reason_code is "schema_violation"
    And the StructuredError reason_code is "schema_violation"
    And the StructuredError field identifies the offending input path
    And zero refund API calls are observed for the invocation correlation_id
    And no EscalationEvent is emitted for the invocation

    Examples:
      | defect                                   |
      | missing amount field                     |
      | non-numeric amount "five hundred"        |
      | boolean amount true                      |
      | negative amount -100                     |
      | zero amount                              |
      | extra unexpected field "note_extra"      |

  @TS-013 @US-002 @FR-002 @P2 @acceptance
  Scenario: Amount exactly at the policy limit is rejected under the declared strict-less-than stance
    Given a configured refund policy with limit L and comparison_stance "strict_less_than"
    And a schema-valid refund payload whose amount equals L exactly
    When the PreToolUse hook evaluates the refund invocation
    Then the hook emits a verdict with value "reject"
    And the verdict reason_code is "policy_breach"

  @TS-014 @US-002 @FR-012 @SC-002 @SC-003 @P2 @acceptance
  Scenario: Hook internal exception fails closed with a distinct reason code
    Given the policy configuration file is unreadable or corrupted
    When the PreToolUse hook attempts to evaluate a refund invocation
    Then the hook emits a verdict with value "reject"
    And the verdict reason_code is "hook_failure"
    And the StructuredError reason_code is "hook_failure"
    And zero refund API calls are observed for the invocation correlation_id
    And an EscalationEvent is emitted with escalation_reason "hook_failure"

  @TS-015 @US-002 @FR-009 @FR-010 @P2 @acceptance
  Scenario: Concurrent policy update mid-invocation pins evaluation to a single snapshot
    Given a refund invocation begins under policy_snapshot_version V1
    And the policy file is updated to policy_snapshot_version V2 before the hook completes
    When the PreToolUse hook evaluates the refund invocation
    Then the verdict records exactly one policy_snapshot_version
    And the EscalationEvent or audit record cites the same policy_snapshot_version as the verdict
