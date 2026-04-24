# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Baseline Comparison Against the Monolithic Anti-Pattern
  Demonstrate that chained decomposition produces measurably deeper finding coverage than a
  single monolithic prompt on the same corpus, making the anti-pattern's cost empirical.

  @TS-006 @FR-001 @P2 @acceptance
  Scenario: Monolithic baseline run produces a single artifact for comparison
    Given the same 15-file corpus used by the chained run
    When the practitioner runs the baseline monolithic prompt asking for both local and integration analysis
    Then the baseline output is captured as a single artifact at "runs/<task_id>/baseline.json"
    And the baseline artifact is not decomposed into per-stage files

  @TS-007 @FR-003 @SC-001 @P2 @validation
  Scenario: Chain exhibits the declared finding-coverage delta over the baseline
    Given a chained-run artifact set on the 15-file corpus
    And a baseline monolithic-run artifact on the same corpus
    When a delta comparison of distinct-issue counts is performed
    Then the chain's finding coverage exceeds the baseline by at least 25 percent

  @TS-008 @FR-003 @FR-006 @P2 @acceptance
  Scenario: Delta report classifies findings by originating mode
    Given both chained and baseline artifacts are loaded
    When the delta report is produced
    Then every finding is labeled with its originating mode of "chain" or "baseline"
    And findings unique to the chain are enumerated separately from findings unique to the baseline

  @TS-009 @FR-003 @SC-002 @P2 @validation
  Scenario Outline: Each stage prompt stays under its declared token budget
    Given the chain is executed on the "<corpus>" fixture
    When the prompt for stage "<stage>" is assembled and tokenized
    Then the measured token count is less than or equal to the stage's declared max_prompt_tokens
    And no StageBudgetExceeded exception is raised for that stage

    Examples:
      | corpus            | stage                    |
      | corpus_15_files   | PerFileAnalysisStage     |
      | corpus_15_files   | IntegrationAnalysisStage |

  @TS-010 @FR-003 @SC-002 @P2 @acceptance
  Scenario: Oversized assembled prompt halts chain with StageBudgetExceeded
    Given an oversize_per_file_report fixture whose aggregated bundle exceeds the integration stage budget
    When the chain assembles the integration stage prompt
    Then a StageBudgetExceeded exception is raised before any SDK call is issued
    And the exception carries stage_index, stage_name, declared_budget, measured_tokens, and overflow fields
    And the chain halts without producing a FinalReport
