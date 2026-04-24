# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Calibrated Few-Shot vs Zero-Shot Baseline on an Edge-Case Corpus
  A practitioner measures the consistency delta between a zero-shot baseline run
  and a calibrated few-shot run on the same edge-case corpus.

  Background:
    Given an edge-case corpus of informal-measure inputs
    And a calibration task flagged as subjective or format-sensitive
    And an example set registry containing a calibrated set of 3 input/output pairs

  @TS-001 @FR-001 @FR-004 @SC-001 @US-001 @P1 @acceptance
  Scenario: Zero-shot baseline run records the inconsistency rate for the corpus
    When the practitioner executes a zero-shot run with explicit anti-pattern acknowledgement
    Then the system records a baseline inconsistency rate for the corpus
    And the calibration report stamps the reserved example set id "zero_shot"

  @TS-002 @FR-001 @FR-004 @SC-001 @US-001 @P1 @acceptance
  Scenario: Calibrated few-shot run records post-calibration rate and delta against baseline
    Given a recorded zero-shot baseline inconsistency rate for the corpus
    When the practitioner executes a few-shot run using the calibrated example set on the same corpus
    Then the system records a post-calibration inconsistency rate
    And the calibration report records the delta against the zero-shot baseline
    And the relative reduction in inconsistency is at least 40 percent

  @TS-003 @FR-003 @SC-004 @US-001 @P1 @acceptance
  Scenario: Active example set is identifiable per run from the logs
    When the practitioner executes a few-shot run with the calibrated example set
    And the practitioner inspects the calibration report
    Then the report stamps the active example set id onto the run
    And the active example set id is retrievable for 100 percent of recorded runs

  @TS-004 @FR-001 @SC-002 @US-001 @P1 @validation
  Scenario: Every calibrated output validates against the declared task output schema
    When the practitioner executes a few-shot run using the calibrated example set
    Then 100 percent of calibrated outputs validate against the declared task schema
    And schema-invalid outputs count toward the inconsistency rate rather than being silently accepted
