# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Swap the Review Prompt Without Touching CI Glue
  The review prompt template lives separately from the CI workflow and annotation mapper so it can be edited independently without touching pipeline code.

  @TS-012 @FR-007 @P3 @acceptance
  Scenario: Prompt template lives outside the workflow definition
    Given the prompt template file "katas/013_headless_ci_review/review_prompt.md" exists
    When the CI workflow ".github/workflows/ci-review.yml" is inspected
    Then the workflow references the prompt template by file path
    And the workflow YAML does not inline the prompt body

  @TS-013 @FR-007 @P3 @acceptance
  Scenario: Editing only the prompt changes the next run's behavior
    Given a practitioner replaces the contents of "katas/013_headless_ci_review/review_prompt.md" with a new objective
    And no change is made to the workflow YAML or the mapper source
    When the CI job is re-run on an unchanged pull request
    Then the Claude Code CLI is invoked with the new prompt
    And annotations reflect the new review objective

  @TS-014 @FR-002 @FR-007 @SC-001 @P3 @acceptance
  Scenario: New prompt still produces schema-valid output
    Given a new prompt template has been deployed
    When the reviewer runs under that prompt
    Then its output still validates against the CLIOutputEnvelope schema
    And the validate_review_output step exits zero
