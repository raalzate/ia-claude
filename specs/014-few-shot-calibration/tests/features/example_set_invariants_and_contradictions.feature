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

  @TS-016 @FR-006 @US-001 @P1 @validation
  Scenario: Leakage flagger marks an example pair whose input appears verbatim in the canonical corpus
    Given a registered calibration task whose canonical_corpus contains a specific input string
    And an example set carrying a pair whose input equals that canonical input byte-for-byte
    When the example set is registered with the calibration runner
    Then a LeakageFinding is logged for that pair
    And the finding carries pair_id, set_id, and leakage_source equal to "canonical_corpus_input"
    And the set remains registered with status "flagged" rather than rejected

  @TS-017 @FR-006 @US-001 @P1 @acceptance
  Scenario: Leakage flagger treats pair output that echoes the canonical expected output as flagged, not fatal
    Given a pair whose output equals the canonical expected output for a corpus input byte-for-byte
    When the example set is registered
    Then a LeakageFinding is logged with leakage_source equal to "canonical_corpus_output"
    And the CalibrationReport records leakage_findings_count at or above 1
    And the calibration run proceeds to completion

  @TS-018 @FR-006 @US-001 @P1 @validation
  Scenario: Leakage detector uses the same canonical normalization as the contradiction detector
    Given a pair whose input differs from a canonical corpus input only by whitespace and letter case
    When the example set is registered
    Then the leakage flagger reports the pair under leakage_source equal to "canonical_corpus_input"
    And both detectors agree on the canonical_key used to match the pair
