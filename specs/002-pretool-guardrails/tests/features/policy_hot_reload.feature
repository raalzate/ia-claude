# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Policy Change Takes Effect Without Retraining or Prompt Tuning
  A change to the policy configuration must take effect on the next invocation without any model retraining, prompt edit, or redeployment.

  @TS-009 @US-003 @FR-011 @SC-004 @P3 @acceptance
  Scenario: Amount allowed under L1 is rejected after the limit is lowered to L2
    Given a policy limit L1 and an amount A with A strictly less than L1
    When the PreToolUse hook evaluates the refund invocation under limit L1
    Then the hook emits a verdict with value "allow"
    When the policy limit is updated from L1 to L2 with L2 strictly less than A strictly less than L1
    And the PreToolUse hook evaluates the same refund invocation under limit L2
    Then the hook emits a verdict with value "reject"
    And the verdict reason_code is "policy_breach"
    And the StructuredError cites the updated limit L2 and the new policy_snapshot_version
    And the EscalationEvent references the new policy_snapshot_version

  @TS-010 @US-003 @FR-008 @FR-011 @P3 @acceptance
  Scenario: No model, prompt, or schema change is required for the new limit to be enforced
    Given a policy change from L1 to L2 is persisted to the policy configuration
    When the next refund invocation is evaluated
    Then the hook enforces limit L2 without any edit to the system prompt
    And the hook enforces limit L2 without any edit to the tool schema
    And the hook enforces limit L2 without any model redeployment

  @TS-011 @US-003 @FR-011 @SC-004 @P3 @acceptance
  Scenario: Policy change takes effect within one invocation of persistence
    Given a policy limit L1 is persisted
    When the policy file is updated to limit L2
    And one subsequent refund invocation is evaluated
    Then the verdict is computed against limit L2
    And no intermediate invocation observes a stale limit L1
