# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Contract Validation of Hook Boundary Payloads
  Every object crossing the PreToolUse boundary or written to the audit log must validate against its declared JSON schema under contracts/.

  @TS-016 @US-002 @FR-002 @contract
  Scenario: ToolCallPayload instances validate against the tool-call-payload schema
    Given a ToolCallPayload object produced by the agent
    When the object is validated against contracts/tool-call-payload.schema.json
    Then the object passes schema validation
    And the tool_name equals "process_refund"
    And the currency equals "USD"

  @TS-017 @US-002 @FR-010 @contract
  Scenario: HookVerdict instances validate against the hook-verdict schema
    Given a HookVerdict emitted by the PreToolUseHook
    When the object is validated against contracts/hook-verdict.schema.json
    Then the object passes schema validation
    And on reject the reason_code and offending_field are non-null
    And on allow the reason_code and offending_field are null

  @TS-018 @US-002 @FR-003 @FR-005 @SC-003 @contract
  Scenario: StructuredError instances validate against the structured-error schema
    Given a StructuredError returned into the model context on a reject verdict
    When the object is validated against contracts/structured-error.schema.json
    Then the object passes schema validation
    And the verdict equals "reject"
    And on reason_code "policy_breach" the policy_id and policy_snapshot_version are non-null
    And on reason_code "schema_violation" or "hook_failure" the policy_id and policy_snapshot_version are null

  @TS-019 @US-003 @FR-011 @contract
  Scenario: PolicyConfig instances validate against the policy-config schema
    Given a PolicyConfig loaded from config/policy.json
    When the object is validated against contracts/policy-config.schema.json
    Then the object passes schema validation
    And the comparison_stance equals "strict_less_than"
    And the max_refund is a decimal-safe numeric string

  @TS-020 @US-002 @FR-007 @FR-009 @contract
  Scenario: EscalationEvent instances validate against the escalation-event schema
    Given an EscalationEvent written to the audit log on a policy_breach or hook_failure reject
    When the object is validated against contracts/escalation-event.schema.json
    Then the object passes schema validation
    And the kind equals "escalation"
    And the actions_taken list is empty
    And the rejected_payload_digest is a 64-character lowercase hex SHA-256

  @TS-021 @US-001 @FR-013 @contract
  Scenario: All five hook boundary schemas are published under contracts/
    Given the feature contracts directory
    When the directory is inspected
    Then it contains tool-call-payload.schema.json
    And it contains hook-verdict.schema.json
    And it contains structured-error.schema.json
    And it contains policy-config.schema.json
    And it contains escalation-event.schema.json

  @TS-022 @US-002 @FR-002 @FR-003 @validation
  Scenario: ToolCallPayload rejects non-positive amounts via the data-model invariant
    Given a ToolCallPayload candidate with amount less than or equal to zero
    When the pydantic validator runs
    Then construction fails with a ValidationError on the amount field

  @TS-023 @US-003 @FR-011 @validation
  Scenario: PolicyConfig is frozen and reloaded per invocation
    Given a PolicyConfig instance is loaded for an invocation
    When the in-process instance is inspected after the verdict is produced
    Then the instance is frozen and cannot be mutated
    And the next invocation reloads a fresh PolicyConfig from configuration
