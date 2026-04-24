# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Anti-Pattern Defense and Measured Delta Against Zero-Shot Prompt Tweaking
  The kata defends against silent zero-shot on subjective tasks and records a
  measurable delta between the anti-pattern approach and calibrated few-shot.

  Background:
    Given an identical edge-case input set used by both the zero-shot and few-shot arms
    And a calibration task flagged as subjective or format-sensitive
    And a registry containing a calibrated example set of 2 to 4 pairs

  @TS-005 @FR-007 @US-002 @P2 @validation
  Scenario: Zero-shot execution on a subjective task requires explicit anti-pattern acknowledgement
    When the practitioner invokes a zero-shot run on the subjective task without acknowledgement
    Then the runner halts before any API call is made
    And the halt reason identifies the documented anti-pattern

  @TS-006 @FR-007 @US-002 @P2 @validation
  Scenario: Explicit acknowledgement permits a zero-shot run to execute as the anti-pattern control
    When the practitioner invokes a zero-shot run with "acknowledge_zero_shot=True"
    Then the runner proceeds and records a zero-shot calibration report
    And the report is labeled as the defended anti-pattern control

  @TS-007 @FR-004 @SC-001 @US-002 @P2 @acceptance
  Scenario: Both arms are recorded side by side with the computed delta
    Given a completed zero-shot run on the identical input set
    And a completed few-shot run on the identical input set
    When the practitioner inspects the calibration artifact
    Then both inconsistency rates are recorded side by side
    And the single computed delta between the two rates is recorded on the artifact

  @TS-008 @FR-007 @US-002 @P2 @acceptance
  Scenario: Successive zero-shot prompt tweaks are documented as the defended anti-pattern
    Given a zero-shot run that attempts to fix format issues via successive prompt tweaks
    When the practitioner inspects the outcome
    Then the inconsistency pattern is recorded as the defended anti-pattern
    And the artifact cross-references the calibrated few-shot result as the corrective control
