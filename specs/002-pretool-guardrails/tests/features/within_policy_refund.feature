# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Refund Within Policy Proceeds Untouched
  A schema-valid refund whose amount is strictly below the configured policy limit must pass the PreToolUse hook and reach the external refund API exactly once, unmodified.

  @TS-001 @US-001 @FR-001 @FR-002 @P1 @acceptance
  Scenario: In-policy refund is allowed and reaches the external API exactly once
    Given a configured refund policy with a positive max_refund limit
    And a schema-valid refund payload whose amount is strictly below the policy limit
    When the PreToolUse hook evaluates the refund invocation
    Then the hook emits a verdict with value "allow"
    And the external refund API receives exactly one call with the original payload
    And the audit log records exactly one refund_api_call entry for the correlation_id

  @TS-002 @US-001 @FR-001 @P1 @acceptance
  Scenario: Success outcome is derived from the real API response, not a hook-synthesized stub
    Given a schema-valid in-policy refund request
    And the external refund API stub is configured to respond successfully
    When the PreToolUse hook allows the invocation and the stub responds
    Then the agent surfaces a success outcome derived from the real API response
    And the success outcome is not synthesized by the hook layer
