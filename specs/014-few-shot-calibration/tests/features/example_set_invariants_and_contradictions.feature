# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001 @US-002
Feature: Example Set Invariants and Contradiction Detection
  An example set is a named, versioned collection of 2 to 4 pairs. Size
  violations and silent contradictions MUST fail closed before any run executes.

  Background:
    Given a pydantic-enforced ExampleSet schema
    And a registered calibration task with a declared output schema
    And a contradiction detector using canonical input normalization

  @TS-012 @FR-006 @US-001 @P1 @contract
  Scenario Outline: Example sets outside the 2 to 4 pair envelope are rejected at construction
    When the practitioner attempts to construct an example set with <pair_count> pairs
    Then construction fails with a size-envelope validation error
    And no calibrated run is executed

    Examples:
      | pair_count |
      | 0          |
      | 1          |
      | 5          |
      | 7          |

  @TS-013 @FR-006 @US-001 @P1 @contract
  Scenario Outline: Example sets inside the 2 to 4 pair envelope are accepted at construction
    When the practitioner constructs an example set with <pair_count> pairs
    Then construction succeeds
    And the set is assigned a stable set id

    Examples:
      | pair_count |
      | 2          |
      | 3          |
      | 4          |

  @TS-014 @FR-005 @SC-003 @US-002 @P1 @contract
  Scenario: Contradictory example set fails closed before any API call
    Given an example set whose pairs map similar inputs to incompatible outputs
    When the practitioner attempts to run calibration with the contradictory set
    Then the runner raises a ContradictoryExamplesError
    And no API call is issued for the run
    And zero silently-contradictory example sets are accepted across the run history

  @TS-015 @FR-005 @SC-003 @US-002 @P1 @validation
  Scenario: Contradiction detection uses canonical normalization of inputs
    Given two pairs whose inputs differ only by whitespace and letter case
    And the two pairs disagree on a same-field output value
    When the example set is constructed
    Then the contradiction detector flags the set as contradictory
    And construction fails with a contradictory-set validation error
