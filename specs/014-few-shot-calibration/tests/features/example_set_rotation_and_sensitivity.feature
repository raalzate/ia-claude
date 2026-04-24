# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Example Set Rotation and Sensitivity to Example Quality
  The practitioner rotates the active example set and observes that example
  quality, not count, is the driver of calibrated output quality.

  Background:
    Given an edge-case corpus of informal-measure inputs
    And an example set registry containing at least two distinct sets of size 2 to 4
    And a calibration task flagged as subjective or format-sensitive

  @TS-009 @FR-002 @FR-003 @SC-004 @US-003 @P3 @acceptance
  Scenario Outline: Each rotated example set is stamped onto its calibration run
    When the practitioner runs the corpus with example set "<set_id>"
    Then the calibration report records the active example set id "<set_id>"
    And the report records the measured inconsistency rate for that set

    Examples:
      | set_id              |
      | calibrated_primary  |
      | calibrated_alternate|

  @TS-010 @FR-004 @SC-001 @US-003 @P3 @acceptance
  Scenario: Comparing two rotated runs documents sensitivity to example quality
    Given a completed calibration run using example set "calibrated_primary"
    And a completed calibration run using example set "calibrated_alternate"
    When the practitioner compares the two runs on the same corpus
    Then the sensitivity to example quality is documented on the comparison artifact
    And both runs reference the same corpus id so results are directly comparable

  @TS-011 @FR-002 @US-003 @P3 @validation
  Scenario: Example set coverage is validated before the set is used in a calibrated run
    When the practitioner loads an example set lacking coverage of the declared edge-case distribution
    Then the runner refuses to execute the calibrated run
    And the refusal reason identifies missing edge-case coverage
