# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Ambiguous Values Route to Escape Enum
  Ambiguous, contradictory, or out-of-enum source values must route to the declared escape option and populate the paired details field.

  Background:
    Given an extraction schema whose enumerated fields declare "other" and "unclear" as escape options
    And each enumerated field has a paired details field capable of capturing the raw observed value
    And a labeled ambiguity fixture set for kata-005

  @TS-012 @FR-005 @SC-003 @US-003 @P3 @acceptance
  Scenario: Value outside the enumerated set routes to "other" with details populated
    Given a source whose enumerated value does not appear in the declared enum
    When extraction runs
    Then the enumerated field is set to "other"
    And the paired details field is a non-empty string capturing the observed raw value

  @TS-013 @FR-005 @SC-003 @US-003 @P3 @acceptance
  Scenario: Contradictory source statements route to the escape option with the contradiction preserved
    Given a source with contradictory statements about an enumerated field
    When extraction runs
    Then the escape option is selected for that field
    And the paired details field captures both contradictory values verbatim or summarized

  @TS-014 @FR-005 @US-003 @P3 @acceptance
  Scenario: Mixed-language ambiguity routes to escape with a language note
    Given a source document that mixes languages for an enumerated field value
    When extraction runs
    Then the enumerated field is set to the escape option
    And the paired details field notes the language mix

  @TS-015 @FR-005 @SC-003 @US-003 @P3 @acceptance
  Scenario: Entire ambiguous corpus routes through the escape enum
    Given the labeled ambiguity fixture set
    When extraction is run against every ambiguous fixture
    Then 100% of enumerated fields flagged ambiguous resolve to an escape option
    And zero enumerated fields flagged ambiguous resolve to a concrete enumerated value

  @TS-016 @FR-005 @US-003 @P3 @contract
  Scenario: AmbiguityMarker pairing is enforced by the model validator
    Given an extracted record whose enumerated field is set to an escape option
    When the pydantic model validator runs in mode "after"
    Then the paired details field must be a non-empty string
    And a missing or empty details value raises a validation error

  @TS-017 @FR-008 @US-003 @P3 @acceptance
  Scenario: Validation failures surface field path and reason to the caller
    Given a model output that fails schema validation
    When the extractor raises its validation error
    Then the error payload names the offending field path
    And the error payload states the reason for the failure

  @TS-018 @FR-009 @US-003 @P3 @validation
  Scenario: Schema documentation declares required, optional, and escape semantics
    Given the SchemaDefinition snapshot for the extraction tool
    When its documentation fields are inspected
    Then required_fields and optional_fields are each declared
    And escape_options enumerates the escape values for every enumerated field
