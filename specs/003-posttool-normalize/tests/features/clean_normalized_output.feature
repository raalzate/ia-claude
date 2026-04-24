# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Clean Minimal JSON Replaces Raw Legacy Output
  PostToolUse hook intercepts legacy payloads and attaches only a minimal, schema-conformant JSON object to conversation history — the model never observes raw legacy markup or arcane codes.

  Background:
    Given an agent session wired to the legacy data source
    And the PostToolUse normalization hook is enabled
    And a StatusMapping that resolves every known arcane status code is loaded

  @TS-001 @FR-001 @FR-006 @US-001 @P1 @acceptance
  Scenario: Hook intercepts every legacy tool response before it reaches the model
    When the practitioner triggers a tool call against the legacy data source
    Then the PostToolUse hook runs before the response is appended to conversation history
    And the message appended to conversation history is the normalized JSON produced by the hook

  @TS-002 @FR-002 @FR-004 @SC-002 @US-001 @P1 @acceptance
  Scenario: Normalized JSON carries no legacy markup characters
    Given a tool response containing heterogeneous legacy markup blocks
    When the hook normalizes the response
    Then every string field in the appended message is free of the characters "<", ">", and CDATA sentinels
    And the appended message validates against the NormalizedPayload schema

  @TS-003 @FR-003 @SC-003 @US-001 @P1 @acceptance
  Scenario: Recognized status codes resolve to human-readable labels
    Given a tool response whose status code is present in the StatusMapping
    When the hook normalizes the response
    Then the status.code field carries the mapped human-readable label
    And the status.raw field is null

  @TS-004 @FR-003 @SC-003 @US-001 @P1 @acceptance
  Scenario: Unknown status codes surface as explicit "unknown" markers
    Given a tool response whose status code is absent from the StatusMapping
    When the hook normalizes the response
    Then the status.code field is exactly the literal "unknown"
    And the status.raw field carries the original arcane code verbatim
    And no guessed or fabricated label appears anywhere in the appended message

  @TS-005 @FR-004 @SC-002 @US-001 @P1 @acceptance
  Scenario: Raw legacy block never appears in conversation history
    Given a tool response containing a raw legacy markup block
    When the practitioner inspects the conversation history after the tool call
    Then no raw legacy block from the source is present in any appended message
    And every appended tool-response message is a NormalizedPayload instance

  @TS-006 @FR-007 @FR-004 @US-001 @P1 @acceptance
  Scenario Outline: Edge-case payloads normalize without leaking raw content
    Given a tool response classified as "<payload_kind>"
    When the hook processes the response
    Then the hook does not crash
    And the appended message is a schema-conformant NormalizedPayload with parse_status "<expected_parse_status>"
    And no "<", ">", or CDATA sentinel appears in any string field of the appended message

    Examples:
      | payload_kind       | expected_parse_status |
      | malformed_markup   | degraded              |
      | empty_response     | empty                 |
      | unknown_code       | ok                    |
      | oversized_payload  | ok                    |
      | nested_blocks      | ok                    |

  @TS-007 @FR-007 @US-001 @P1 @acceptance
  Scenario: Nested legacy blocks are flattened and every embedded code is resolved
    Given a tool response with legacy blocks embedded inside other legacy blocks
    And the response carries multiple status codes across the nesting
    When the hook normalizes the response
    Then the appended message has a flat or shallow content object
    And every resolvable code is replaced by its human-readable label
    And no nested legacy markup is re-emitted anywhere in the appended message
