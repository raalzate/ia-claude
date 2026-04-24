# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Baseline vs. Normalized Run Demonstrates Anti-Pattern Defense
  Toggling the hook off reproduces the anti-pattern (raw legacy payload injected into context); toggling it on produces measurable token and misinterpretation reductions.

  Background:
    Given the same fixture legacy payload is replayed across two runs
    And run A has the PostToolUse hook disabled (baseline, anti-pattern)
    And run B has the PostToolUse hook enabled (normalized)

  @TS-010 @FR-004 @SC-002 @US-002 @P2 @acceptance
  Scenario: Baseline run leaks raw legacy markup into conversation history
    When run A completes
    Then the tool-response message appended in run A contains the raw legacy markup block verbatim
    And run A is labeled as the documented anti-pattern

  @TS-011 @FR-004 @FR-006 @SC-002 @US-002 @P2 @acceptance
  Scenario: Normalized run contains only the clean JSON object
    When run B completes
    Then the tool-response message appended in run B is a NormalizedPayload instance
    And no raw legacy markup appears in any message of run B

  @TS-012 @SC-001 @US-002 @P2 @acceptance
  Scenario: Normalized tool-response token count is substantially lower than baseline
    When both runs complete against the fixture corpus
    Then the tool-response token count in run B is no more than 30% of the tool-response token count in run A
    And the reduction holds on average across the representative sample of legacy payloads

  @TS-013 @US-002 @P2 @acceptance
  Scenario: Normalized run records fewer downstream model misinterpretations
    Given both runs execute the identical downstream task against the same payload
    When downstream misinterpretation events are counted in each run
    Then run B records strictly fewer misinterpretation events than run A

  @TS-014 @FR-005 @SC-004 @US-002 @P2 @acceptance
  Scenario: Audit trail retains the original payload for both runs
    When run A and run B complete
    Then the audit log contains the original tool payload byte-for-byte for each run
    And the SHA-256 digest of the stored raw bytes matches the SHA-256 of the source fixture for each run

  @TS-015 @FR-005 @SC-004 @US-002 @P2 @acceptance
  Scenario Outline: Audit trail survives every payload class
    Given a fixture payload of kind "<payload_kind>"
    When the hook processes it in run B
    Then exactly one AuditRecord is written for that tool_use_id
    And the AuditRecord preserves the raw bytes byte-for-byte recoverable
    And the AuditRecord is written before the normalized message is appended to conversation history

    Examples:
      | payload_kind       |
      | happy_path         |
      | malformed_markup   |
      | unknown_code       |
      | empty_response     |
      | oversized_payload  |
      | nested_blocks      |
