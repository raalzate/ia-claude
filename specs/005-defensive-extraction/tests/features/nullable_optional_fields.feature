# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Missing Optional Fields Return Null, Not Fabrications
  Optional fields absent from the source must return as null via nullable unions — never a plausible-sounding invented value.

  Background:
    Given an extraction schema whose optional fields are declared as nullable union types
    And a labeled fixture whose null_map records which optional fields are absent from the source
    And the extractor is configured to reject bare str types for optional fields

  @TS-007 @FR-004 @FR-007 @SC-004 @US-002 @P2 @acceptance
  Scenario: Absent optional field is returned as null
    Given a source document that omits an optional field
    When extraction runs
    Then that field is returned as null in the extracted record
    And the returned value is not the string "unknown" or any free-form guess

  @TS-008 @FR-004 @US-002 @P2 @validation
  Scenario: Schema lint rejects optional fields declared as bare str
    Given the pydantic ExtractedRecord model is loaded
    When the schema-lint walker inspects every optional field
    Then every non-required field's annotation is a union that includes NoneType
    And no optional field is annotated as a bare str without a narrower type

  @TS-009 @FR-004 @US-002 @P2 @contract
  Scenario Outline: Nullable optional JSON Schema types permit null
    Given the generated JSON Schema of the ExtractedRecord
    When the "<field>" property type is inspected
    Then its JSON Schema type array includes "null"
    And its JSON Schema type array includes "<declared_type>"

    Examples:
      | field          | declared_type |
      | nickname       | string        |
      | location       | string        |
      | status_details | string        |

  @TS-010 @FR-007 @SC-001 @US-002 @P2 @acceptance
  Scenario: No fabrication across a labeled corpus of absent optionals
    Given the labeled fixture corpus for kata-005
    When extraction is run against every fixture
    Then for every fixture, every field marked absent in its null_map is returned as null
    And the total fabrication count across the corpus is zero

  @TS-011 @FR-007 @SC-004 @US-002 @P2 @acceptance
  Scenario: Null rate on absent optionals meets the 99% threshold
    Given the labeled fixture corpus for kata-005
    When the FabricationMetric is computed for every fixture
    Then the mean null_rate across the corpus is at least 0.99
