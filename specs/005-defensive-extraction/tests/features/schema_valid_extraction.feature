# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Well-Formed Source Produces Schema-Valid Record
  A well-formed source document yields a typed ExtractedRecord delivered via a schema-bound, forced tool call.

  Background:
    Given a declared extraction schema whose required fields are all guaranteed present in the source
    And an Anthropic client configured with the schema-bound extraction tool
    And the extraction tool is invoked with tool_choice={"type": "any"}

  @TS-001 @FR-001 @FR-002 @SC-002 @US-001 @P1 @acceptance
  Scenario: Schema-bound tool call returns a schema-valid record
    Given a source document that contains every guaranteed field
    When the practitioner runs extraction
    Then the returned record validates against the extraction schema with zero validation errors
    And the null rate on required fields of the returned record is zero

  @TS-002 @FR-002 @SC-002 @US-001 @P1 @contract
  Scenario: Response is delivered as a tool call, not free text
    Given a source document with all required fields present
    When the model is invoked
    Then the response content block has type "tool_use"
    And the tool_use block name equals the declared extraction tool name
    And no free-text message block is consumed as the extraction payload

  @TS-003 @FR-003 @SC-002 @US-001 @P1 @acceptance
  Scenario: Every required field is non-null and of the declared type
    Given a valid extraction result
    When it is passed to schema validation
    Then every required field has a non-null value
    And every required field matches its declared JSON Schema type

  @TS-004 @FR-010 @US-001 @P1 @contract
  Scenario: Extractor refuses keys outside the declared schema
    Given a model response that attempts to return an additional key not declared in the schema
    When the extractor validates the tool-use payload
    Then validation fails with an "extra_forbidden" error
    And no extracted record is returned to the caller

  @TS-005 @FR-006 @SC-002 @US-001 @P1 @acceptance
  Scenario: Missing required field fails validation rather than being coerced
    Given a source document that omits a field declared as required
    When extraction runs
    Then schema validation fails with a missing-required-field error
    And no record with the required field coerced to null or a default is emitted

  @TS-006 @FR-006 @SC-002 @US-001 @P1 @acceptance
  Scenario: Empty source fails validation with no fabricated defaults
    Given an empty source document
    When extraction runs
    Then schema validation fails on at least one required field
    And no record of fabricated default values is emitted
